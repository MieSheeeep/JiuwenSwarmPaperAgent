import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

TEMP = Path(__file__).resolve().parents[1] / 'runtime/test_tmp'
TEMP.mkdir(parents=True, exist_ok=True)


class ReleaseTests(unittest.TestCase):
    def test_plan_has_disjoint_split_fixed_grid_and_no_labels_in_requests(self):
        from research.memory_run import prepare_run, answer_messages
        with TemporaryDirectory(dir=TEMP) as directory:
            manifest, tasks = prepare_run(Path(directory), max_total_tokens=300000)
            self.assertTrue(manifest['grid'])
            self.assertEqual(sum(t['split'] == 'dev' for t in tasks), 6)
            self.assertEqual(sum(t['split'] == 'test' for t in tasks), 24)
            self.assertTrue({t['seed'] for t in tasks if t['split']=='dev'}.isdisjoint(
                {t['seed'] for t in tasks if t['split']=='test'}))
            context = answer_messages(tasks[0], '')
            self.assertNotIn('gold_evidence', json.dumps(context))
            self.assertNotIn('stale_values', json.dumps(context))
            original = (Path(directory) / 'manifest.json').read_bytes()
            prepare_run(Path(directory), max_total_tokens=300000)
            self.assertEqual(original, (Path(directory) / 'manifest.json').read_bytes())

    def test_changed_protocol_cannot_resume_in_existing_directory(self):
        from research.memory_run import prepare_run
        with TemporaryDirectory(dir=TEMP) as directory:
            prepare_run(Path(directory), max_total_tokens=300000)
            with self.assertRaisesRegex(ValueError, 'different|changed'):
                prepare_run(Path(directory), max_total_tokens=400000)

    def test_provider_change_cannot_mix_run_conditions(self):
        from research.memory_run import prepare_run
        with TemporaryDirectory(dir=TEMP) as directory:
            prepare_run(Path(directory), max_total_tokens=300000, model='same', provider='A', endpoint_hash='one')
            with self.assertRaisesRegex(ValueError, 'different|changed'):
                prepare_run(Path(directory), max_total_tokens=300000, model='same', provider='B', endpoint_hash='two')

    def test_stopped_grid_explicitly_records_unattempted_results(self):
        from research.memory_run import prepare_run, finalize_stopped_grid
        from research.memory_analysis import analyze_memory
        with TemporaryDirectory(dir=TEMP) as directory:
            root = Path(directory)
            manifest, tasks = prepare_run(root, max_total_tokens=300000)
            finalize_stopped_grid(root, manifest, tasks, [], [], 'budget_exhausted')
            rows = [json.loads(line) for line in (root/'results.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), len(manifest['grid']))
            self.assertTrue(all(r['status']=='not_run' and r['call_ids']==[] for r in rows))
            summary = analyze_memory(root)
            self.assertEqual(summary['resources']['total_calls'], 0)


if __name__ == '__main__':
    unittest.main()
