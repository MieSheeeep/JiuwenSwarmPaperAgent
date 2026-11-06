import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from research.experiment_protocol import ADAPTIVE_QA_PROTOCOL, validate_experiment_plan
from research.qa_dataset import generate_qa_tasks, select_context, score_answer
from research.generic_runner import run_experiment
from research.generic_paper import write_paper


def plan():
    return {
        'adapter': 'adaptive-qa-v1',
        'protocol': dict(ADAPTIVE_QA_PROTOCOL),
        'candidate_id': 'qa-stop',
        'source_ids': ['p1', 'p2'],
        'data_split': {'train': 0, 'test': 12, 'seed': 20261106},
        'baselines': ['single_pass', 'fixed_two_passages'],
        'methods': ['single_pass', 'fixed_two_passages', 'adaptive_stop'],
        'metrics': ['exact_accuracy', 'evidence_recall', 'context_passages', 'provider_tokens'],
        'falsification': 'adaptive_stop does not improve exact accuracy at lower context cost',
        'cost_controls': {'max_total_tokens': 20000, 'max_calls': 36},
        'analysis': 'paired task-level comparison',
        'ablations': ['remove adaptive stopping'],
    }


class GenericResearchTests(unittest.TestCase):
    def test_registered_plan_is_valid_and_unknown_or_shell_plan_is_rejected(self):
        validate_experiment_plan(plan())
        bad = dict(plan(), adapter='unknown-v1')
        with self.assertRaises(ValueError):
            validate_experiment_plan(bad)
        bad = dict(plan(), commands=['python -c "print(1)"'])
        with self.assertRaises(ValueError):
            validate_experiment_plan(bad)

    def test_dataset_and_adaptive_context_are_deterministic(self):
        tasks = generate_qa_tasks(n=12, seed=20261106)
        self.assertEqual(tasks, generate_qa_tasks(n=12, seed=20261106))
        self.assertEqual(len(tasks), 12)
        for task in tasks:
            one = select_context(task, 'single_pass')
            two = select_context(task, 'fixed_two_passages')
            adaptive = select_context(task, 'adaptive_stop')
            self.assertEqual(len(one['passages']), 1)
            self.assertEqual(len(two['passages']), 2)
            self.assertGreaterEqual(len(adaptive['passages']), 2)
            self.assertEqual(adaptive['evidence_recall'], 1.0)
            self.assertTrue(score_answer(task['gold'], task)['exact'])

    def test_runner_records_bound_context_and_scores(self):
        async def invoke_stub(on_response):
            on_response(json.dumps({'answer': 'City-0'}),
                        {'input_tokens': 10, 'output_tokens': 4, 'total_tokens': 14},
                        [])

        async def run():
            with tempfile.TemporaryDirectory() as directory:
                result = await run_experiment(Path(directory), plan(),
                                              invoke=invoke_stub, max_tasks=1,
                                              count_tokens=lambda text: len(text))
                self.assertEqual(result['status'], 'completed')
                row = json.loads((Path(directory) / 'results.jsonl').read_text().splitlines()[0])
                self.assertIn('context_sha256', row)
                self.assertIn('call_ids', row)
                self.assertIn('score', row)
                self.assertEqual(result['methods'], plan()['methods'])

        asyncio.run(run())

    def test_paper_recomputes_numbers_from_result_rows(self):
        async def invoke_stub(on_response):
            on_response(json.dumps({'answer': 'City-0'}),
                        {'input_tokens': 2, 'output_tokens': 2, 'total_tokens': 4}, [])

        async def run():
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                await run_experiment(root / 'run', plan(), invoke=invoke_stub, max_tasks=1,
                                     count_tokens=lambda text: len(text))
                paper = write_paper(root / 'run', root / 'paper')
                text = (root / 'paper' / 'paper.md').read_text(encoding='utf-8')
                self.assertIn('single_pass', text)
                self.assertIn('0.00', text)
                self.assertIn('Related work', text)
                self.assertIn('Experimental setup', text)
                self.assertIn('Error analysis', text)
                self.assertIn('Appendix: Reproducibility', text)
                self.assertEqual(paper['status'], 'written')

        asyncio.run(run())


if __name__ == '__main__':
    unittest.main()
