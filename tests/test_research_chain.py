"""Adversarial checks for the offline experiment-to-manuscript chain."""
import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from baseline.dataset import score_answer

TEST_TEMP = Path(__file__).resolve().parents[1] / 'runtime' / 'test_tmp'
TEST_TEMP.mkdir(parents=True, exist_ok=True)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def fixture(root):
    root.mkdir(parents=True, exist_ok=True)
    gold = {'port': 8080, 'timeout': 20, 'owner': 'alex'}
    tasks = [{'id': f'task-{i}', 'gold': gold, 'family': 'lookup', 'position': 'early'}
             for i in range(2)]
    text = json.dumps(tasks, ensure_ascii=False, indent=2)
    (root / 'dataset.json').write_text(text, encoding='utf-8')
    dump(root / 'manifest.json', {'tasks': 2, 'policies': ['full', 'retrieve'],
         'model': 'fixture-model', 'seed': 1,
         'dataset_sha256': hashlib.sha256(text.encode()).hexdigest(),
         'history_budget_proxy_tokens': 512, 'tokenizer_proxy': 'cl100k_base'})
    rows, calls = [], []
    for task in tasks:
        for policy in ['full', 'retrieve']:
            answer = json.dumps(gold)
            call_id = task['id'] + '-' + policy
            rows.append({'task_id': task['id'], 'policy': policy, 'status': 'ok',
                         'answer': answer, 'score': score_answer(answer, gold),
                         'call_ids': [call_id], 'elapsed_seconds': 0.5})
            calls.append({'id': call_id, 'tag': task['id'] + '/' + policy + '/answer',
                          'status': 'ok', 'output': answer, 'model': 'fixture-model',
                          'usage': {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12}})
    for name, records in [('results.jsonl', rows), ('calls.jsonl', calls)]:
        (root / name).write_text('\n'.join(json.dumps(r) for r in records), encoding='utf-8')
    # Intentionally wrong old summary: import must derive metrics from raw files.
    dump(root / 'summary.json', {'total_api_tokens': 99999})
    return root


def edit_records(root, name, edit):
    path = root / name
    records = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]
    edit(records)
    path.write_text('\n'.join(json.dumps(r) for r in records), encoding='utf-8')


class FixtureMixin:
    def setUp(self):
        self.temp = TemporaryDirectory(dir=TEST_TEMP)
        self.addCleanup(self.temp.cleanup)
        self.source = fixture(Path(self.temp.name) / 'source')


class EvidenceTests(FixtureMixin, unittest.TestCase):
    def test_recomputes_metrics_and_binds_raw_file_hashes(self):
        from research.evidence import import_baseline
        run, evidence = import_baseline(self.source)
        self.assertEqual(evidence['payload']['total_api_tokens'], 48)
        self.assertEqual(evidence['payload']['metrics'][0]['exact_accuracy'], 1)
        self.assertEqual(evidence['parent_ids'], [run['artifact_id']])
        self.assertEqual(run['payload']['source_files']['dataset.json'],
                         hashlib.sha256((self.source / 'dataset.json').read_bytes()).hexdigest())
        self.assertEqual(run['payload']['origin'], 'historical_baseline')

    def test_dataset_edit_without_matching_digest_is_rejected(self):
        from research.evidence import import_baseline
        data = json.loads((self.source / 'dataset.json').read_text())
        data[0]['gold']['port'] = 9000
        dump(self.source / 'dataset.json', data)
        with self.assertRaisesRegex(ValueError, 'dataset.*digest'):
            import_baseline(self.source)

    def test_missing_task_policy_pair_is_rejected(self):
        from research.evidence import import_baseline
        edit_records(self.source, 'results.jsonl', lambda rows: rows.pop())
        with self.assertRaisesRegex(ValueError, 'task-policy'):
            import_baseline(self.source)

    def test_forged_score_is_rejected(self):
        from research.evidence import import_baseline
        edit_records(self.source, 'results.jsonl', lambda rows: rows[0]['score'].update(exact=False))
        with self.assertRaisesRegex(ValueError, 'score'):
            import_baseline(self.source)

    def test_cross_task_call_associations_are_rejected_even_with_same_outputs(self):
        from research.evidence import import_baseline
        def swap(rows):
            rows[0]['call_ids'], rows[2]['call_ids'] = rows[2]['call_ids'], rows[0]['call_ids']
        edit_records(self.source, 'results.jsonl', swap)
        with self.assertRaisesRegex(ValueError, 'association'):
            import_baseline(self.source)

    def test_unknown_usage_is_not_zero_cost(self):
        from research.evidence import import_baseline
        edit_records(self.source, 'calls.jsonl', lambda calls: calls[0].update(usage=None))
        with self.assertRaisesRegex(ValueError, 'usage'):
            import_baseline(self.source)

    def test_answer_must_match_the_logged_response(self):
        from research.evidence import import_baseline
        edit_records(self.source, 'calls.jsonl', lambda calls: calls[0].update(output='{}'))
        with self.assertRaisesRegex(ValueError, 'answer.*response'):
            import_baseline(self.source)

    def test_null_answer_is_an_actionable_validation_error(self):
        from research.evidence import import_baseline
        edit_records(self.source, 'results.jsonl', lambda rows: rows[0].update(answer=None))
        with self.assertRaisesRegex(ValueError, 'result.*answer'):
            import_baseline(self.source)

    def test_scalar_manifest_is_an_actionable_validation_error(self):
        from research.evidence import import_baseline
        dump(self.source / 'manifest.json', None)
        with self.assertRaisesRegex(ValueError, 'manifest'):
            import_baseline(self.source)

    def test_malformed_task_record_is_an_actionable_validation_error(self):
        from research.evidence import import_baseline
        tasks = [None]
        text = json.dumps(tasks, indent=2)
        (self.source / 'dataset.json').write_text(text, encoding='utf-8')
        manifest = json.loads((self.source / 'manifest.json').read_text())
        manifest.update(dataset_sha256=hashlib.sha256(text.encode()).hexdigest(), tasks=1)
        dump(self.source / 'manifest.json', manifest)
        with self.assertRaisesRegex(ValueError, 'task'):
            import_baseline(self.source)

    def test_modified_artifact_is_rejected(self):
        from research.artifacts import validate_artifact
        from research.evidence import import_baseline
        _, evidence = import_baseline(self.source)
        evidence['payload']['total_api_tokens'] = 999
        with self.assertRaisesRegex(ValueError, 'hash'):
            validate_artifact(evidence)


class ManuscriptTests(FixtureMixin, unittest.TestCase):
    def test_clean_manuscript_has_measured_claims_and_passes(self):
        from research.evidence import import_baseline
        from research.writer import build_manuscript, render_markdown
        from research.reviewer import review_manuscript
        _, evidence = import_baseline(self.source)
        manuscript = build_manuscript(evidence)
        self.assertTrue(review_manuscript(manuscript, evidence)['payload']['passed'])
        self.assertIn('historical', render_markdown(manuscript))
        self.assertTrue(manuscript['payload']['claims'])

    def test_consistently_forged_claim_still_fails_evidence_check(self):
        from research.artifacts import create_artifact
        from research.evidence import import_baseline
        from research.writer import build_manuscript
        from research.reviewer import review_manuscript
        _, evidence = import_baseline(self.source)
        good = build_manuscript(evidence)
        payload = copy.deepcopy(good['payload'])
        payload['claims'][0]['value'] = 999
        payload['claims'][0]['statement'] = 'full: tasks = 999.'
        altered = create_artifact('ManuscriptBundle', payload, good['parent_ids'])
        review = review_manuscript(altered, evidence)
        self.assertFalse(review['payload']['passed'])
        self.assertIn('claim_value', [i['code'] for i in review['payload']['issues']])

    def test_unregistered_prose_is_not_silently_certified(self):
        from research.artifacts import create_artifact
        from research.evidence import import_baseline
        from research.writer import build_manuscript
        from research.reviewer import review_manuscript
        _, evidence = import_baseline(self.source)
        good = build_manuscript(evidence)
        payload = copy.deepcopy(good['payload'])
        payload['sections'][0]['text'] += ' Real-world accuracy is 99%.'
        altered = create_artifact('ManuscriptBundle', payload, good['parent_ids'])
        self.assertFalse(review_manuscript(altered, evidence)['payload']['passed'])


class PipelineTests(unittest.TestCase):
    def test_malformed_checkpoint_is_rebuilt(self):
        from research.pipeline import run_pipeline
        with TemporaryDirectory(dir=TEST_TEMP) as directory:
            root = Path(directory)
            source = fixture(root / 'source')
            out = root / 'output'
            run_pipeline(source, out)
            dump(out / 'state.json', ['invalid', 'checkpoint'])
            self.assertFalse(run_pipeline(source, out)['resumed'])

    def test_resume_checks_output_integrity_and_rebuilds_corruption(self):
        from research.pipeline import run_pipeline
        with TemporaryDirectory(dir=TEST_TEMP) as directory:
            root = Path(directory)
            source = fixture(root / 'source')
            out = root / 'output'
            first = run_pipeline(source, out)
            self.assertFalse(first['resumed'])
            before = (out / 'evidence.json').stat().st_mtime_ns
            self.assertTrue(run_pipeline(source, out)['resumed'])
            self.assertEqual(before, (out / 'evidence.json').stat().st_mtime_ns)
            data = json.loads((out / 'evidence.json').read_text())
            data['payload']['total_api_tokens'] = 123
            dump(out / 'evidence.json', data)
            self.assertFalse(run_pipeline(source, out)['resumed'])
            self.assertEqual(json.loads((out / 'evidence.json').read_text())['payload']['total_api_tokens'], 48)
            (out / 'paper.md').write_text('Invented accuracy: 99%', encoding='utf-8')
            self.assertFalse(run_pipeline(source, out)['resumed'])

    def test_changed_valid_source_invalidates_cache(self):
        from research.pipeline import run_pipeline
        with TemporaryDirectory(dir=TEST_TEMP) as directory:
            root = Path(directory)
            source = fixture(root / 'source')
            out = root / 'output'
            first = run_pipeline(source, out)
            edit_records(source, 'calls.jsonl', lambda calls: calls[0]['usage'].update(
                input_tokens=20, total_tokens=22))
            second = run_pipeline(source, out)
            self.assertFalse(second['resumed'])
            self.assertNotEqual(first['fingerprint'], second['fingerprint'])
            self.assertEqual(json.loads((out / 'evidence.json').read_text())['payload']['total_api_tokens'], 58)

    def test_invalid_changed_source_cannot_reuse_success_checkpoint(self):
        from research.pipeline import run_pipeline
        with TemporaryDirectory(dir=TEST_TEMP) as directory:
            root = Path(directory)
            source = fixture(root / 'source')
            out = root / 'output'
            run_pipeline(source, out)
            edit_records(source, 'results.jsonl', lambda rows: rows.pop())
            with self.assertRaises(ValueError):
                run_pipeline(source, out)
            self.assertEqual(json.loads((out / 'state.json').read_text())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
