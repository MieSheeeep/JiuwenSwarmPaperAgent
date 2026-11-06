import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from workbench.data import Repository
from workbench.server import make_server


class WorkbenchTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.run = self.root/'output/memory_live_20261016'
        self.run.mkdir(parents=True)
        self.write('manifest.json', {'schema_version': 2, 'model': 'test-model', 'grid': [{}, {}]})
        self.write('summary.json', {'methods': [], 'evaluation_complete': True, 'resources': {'total_calls': 3, 'total_tokens': 123}})
        self.write('dataset.json', [{'id': 'a', 'gold': {'answer': 1}, 'question': 'Q'}])
        self.write('results.jsonl', {'task_id': 'a', 'policy': 'versioned', 'status': 'ok', 'answer': '{}', 'scores': {'exact': False}})
        self.repo = Repository(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def write(self, name, value):
        (self.run/name).write_text(json.dumps(value), encoding='utf-8')

    def test_reads_real_totals_without_guessing_scores(self):
        self.assertEqual(self.repo.runs()[0]['id'], self.run.name)
        data = self.repo.overview(self.run.name)
        self.assertEqual(data['resources']['end_to_end']['total_tokens'], 123)
        self.assertIsNone(data['review']['score'])
        self.assertFalse(data['availability']['paper'])

    def test_missing_summary_is_explicit(self):
        (self.run/'summary.json').unlink()
        data = self.repo.overview(self.run.name)
        self.assertFalse(data['availability']['summary'])
        self.assertIsNone(data['resources']['end_to_end'].get('total_tokens'))

    def test_cases_join_only_registered_dataset(self):
        data = self.repo.cases(self.run.name)
        self.assertEqual(data[0]['task']['question'], 'Q')
        self.assertEqual(len(data), 1)

    def test_malformed_manifest_does_not_hide_other_runs(self):
        bad = self.root/'output/memory_live_broken'
        bad.mkdir()
        (bad/'manifest.json').write_text('[]', encoding='utf-8')
        self.assertEqual([r['id'] for r in self.repo.runs()], [self.run.name])

    def test_invalid_resource_schema_is_rejected(self):
        paper = self.root/'output/memory_paper_20261016'
        paper.mkdir()
        (paper/'resources.json').write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): self.repo.overview(self.run.name)

    def test_missing_results_reports_missing_artifact(self):
        (self.run/'results.jsonl').unlink()
        with self.assertRaises(FileNotFoundError): self.repo.cases(self.run.name)

    def test_unknown_run_and_secret_artifacts_rejected(self):
        for run in ['../config.local', 'missing', 'memory_live_20261016/..']:
            with self.assertRaises(KeyError): self.repo.overview(run)
        with self.assertRaises(KeyError): self.repo.artifact_path(self.run.name, 'token')

    def test_http_routes_and_traversal(self):
        server = make_server(self.repo, port=0)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with urlopen(base+'/api/runs') as response:
                self.assertEqual(json.load(response)[0]['id'], self.run.name)
            for path in ['/api/runs/../config', '/.env', '/api/runs/memory_live_20261016/files/token', '/assets/../../README.md']:
                with self.assertRaises(HTTPError) as caught: urlopen(base+path)
                self.assertEqual(caught.exception.code, 404)
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base+'/api/runs', headers={'Origin': 'https://untrusted.example'}))
            self.assertEqual(caught.exception.code, 403)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__': unittest.main()
