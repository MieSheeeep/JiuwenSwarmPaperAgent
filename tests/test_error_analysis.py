import importlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class ErrorAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.run = Path(self.temp.name) / 'run'
        self.run.mkdir()
        self.tasks = [dict(id='case-a', split='test', family='conflict', question='Who owns it?',
                           gold={'owner': None}, gold_evidence={'owner': ['r1', 'r2']},
                           query={'entity': 'e', 'attributes': ['owner']}, records=[
                               {'id': 'r1', 'entity': 'e', 'value': 'a'},
                               {'id': 'r2', 'entity': 'e', 'value': 'b'}])]
        self.rows = [self.row('versioned', False, 1), self.row('no_conflict', False, 1),
                     self.row('recent', False, .5), self.row('full', True, 1)]
        self.grid = [{k: r[k] for k in ('task_id', 'policy', 'budget')} for r in self.rows]

    def row(self, policy, exact, recall):
        return dict(task_id='case-a', policy=policy, budget=256, status='ok',
                    answer='{"owner":"a"}', selected_ids=['r1', 'r2'] if recall == 1 else ['r1'],
                    score=dict(exact=exact, evidence_recall=recall))

    def analyze(self):
        for name, data in [('dataset.json', self.tasks), ('manifest.json', {'grid': self.grid})]:
            (self.run / name).write_text(json.dumps(data), encoding='utf-8')
        (self.run / 'results.jsonl').write_text('\n'.join(json.dumps(r) for r in self.rows), encoding='utf-8')
        module = importlib.import_module('research.error_analysis')
        return module.analyze_errors(self.run)

    def test_descriptive_counts_pair_ties_and_case_details(self):
        report = self.analyze()
        self.assertEqual(report['overview']['retrieval_insufficient_errors'], 1)
        self.assertEqual(report['overview']['complete_evidence_errors'], 2)
        self.assertEqual(report['overview']['exact_correct'], 1)
        self.assertEqual(len(report['groups']), 4)
        pair = report['comparisons'][0]
        self.assertEqual(pair['both_wrong'], 1)
        self.assertEqual(pair['exact_ties'], 1)
        self.assertEqual(pair['selected_ids_equal'], 1)
        case = next(c for c in report['cases'] if c['policy'] == 'recent')
        self.assertEqual(case['question'], 'Who owns it?')
        self.assertEqual(case['response'], '{"owner":"a"}')
        self.assertEqual(case['gold'], {'owner': None})
        self.assertEqual(case['missing_evidence_ids'], ['r2'])
        self.assertEqual(report, self.analyze())

    def test_missing_failed_and_invalid_scores_are_never_answer_errors(self):
        self.rows[0]['status'] = 'provider_error'
        self.rows[1]['score']['exact'] = 'false'
        self.rows.pop()
        report = self.analyze()
        self.assertEqual(report['overview']['missing_rows'], 1)
        self.assertEqual(report['overview']['failed_rows'], 1)
        self.assertEqual(report['overview']['invalid_score_rows'], 1)
        self.assertEqual(report['overview']['scored_rows'], 1)
        self.assertEqual(report['overview']['exact_errors'], 1)
        self.assertEqual({c['category'] for c in report['cases']},
                         {'missing_result', 'failed_result', 'invalid_score', 'retrieval_insufficient_error'})

    def test_rejects_duplicate_or_unplanned_results(self):
        self.rows.append(self.rows[0])
        with self.assertRaisesRegex(ValueError, 'Duplicate result'):
            self.analyze()
        self.rows[-1] = self.row('unknown', False, 1)
        with self.assertRaisesRegex(ValueError, 'outside manifest'):
            self.analyze()

    def test_invalid_recall_does_not_become_complete_evidence(self):
        self.rows[0]['score']['evidence_recall'] = float('nan')
        report = self.analyze()
        self.assertEqual(report['overview']['invalid_score_rows'], 1)
        self.assertEqual(report['overview']['complete_evidence_errors'], 1)

    def test_null_or_missing_scores_are_explicit_and_json_safe(self):
        self.rows[0]['score'] = None
        del self.rows[1]['score']
        report = self.analyze()
        self.assertEqual(report['overview']['invalid_score_rows'], 2)
        json.dumps(report, allow_nan=False)

    def test_dataset_metadata_mismatch_is_rejected(self):
        self.rows[0]['family'] = 'static'
        with self.assertRaisesRegex(ValueError, 'family differs'):
            self.analyze()

    def test_cli_writes_english_artifacts_without_changing_inputs(self):
        self.analyze()
        before = {p.name: p.read_bytes() for p in self.run.iterdir()}
        out = Path(self.temp.name) / 'analysis'
        subprocess.run([sys.executable, '-m', 'research.error_analysis', '--run-dir', str(self.run),
                        '--output', str(out)], check=True, capture_output=True)
        report = json.loads((out / 'error_analysis.json').read_text(encoding='utf-8'))
        self.assertEqual(report['overview']['expected_rows'], 4)
        self.assertIn('Descriptive error analysis', (out / 'ERROR_ANALYSIS.md').read_text(encoding='utf-8'))
        plan = json.loads((out / 'next_experiment_plan.json').read_text(encoding='utf-8'))
        self.assertEqual(plan['status'], 'proposed_not_run')
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.run.iterdir()})
        blocked = subprocess.run([sys.executable, '-m', 'research.error_analysis', '--run-dir', str(self.run),
                                  '--output', str(self.run)], capture_output=True)
        self.assertNotEqual(blocked.returncode, 0)


if __name__ == '__main__':
    unittest.main()
