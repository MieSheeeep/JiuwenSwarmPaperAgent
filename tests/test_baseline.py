import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'upstream/jiuwenswarm/agents/harness/common/context_budget.py'


class BaselineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('context_budget', MODULE)
        cls.policy = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.policy)

    def test_recent_keeps_complete_latest_records_under_budget(self):
        rows = ['old words here', 'middle words here', 'latest words here']
        result = self.policy.select_history(rows, 'project P12', 'recent', 6, lambda s: len(s.split()))
        self.assertEqual(result, rows[1:])

    def test_retrieval_keeps_updates_in_chronological_order(self):
        rows = ['project P12 port=1', 'project P13 port=9', 'project P12 timeout=8']
        result = self.policy.select_history(rows, 'Final settings for project P12?', 'retrieve', 20, lambda s: len(s.split()))
        self.assertEqual(result, [rows[0], rows[2]])

    def test_budget_applies_to_joined_text(self):
        rows = ['project P12 ' + 'a ' * 20, 'project P12 b']
        result = self.policy.select_history(rows, 'project P12', 'retrieve', 5, lambda s: len(s.split()))
        self.assertLessEqual(len('\n'.join(result).split()), 5)
        self.assertEqual(result, [rows[1]])

    def test_project_substring_is_not_a_match(self):
        result = self.policy.select_history(['project P120 port=9'], 'project P12', 'retrieve', 50, lambda s: len(s.split()))
        self.assertEqual(result, [])

    def test_invalid_budget_and_policy_fail(self):
        with self.assertRaises(ValueError):
            self.policy.select_history([], 'project P12', 'recent', 0, len)
        with self.assertRaises(ValueError):
            self.policy.select_history([], 'project P12', 'oracle', 50, len)

    def test_scoring_requires_valid_fields_and_does_not_extract_arbitrary_numbers(self):
        from baseline.dataset import score_answer
        gold = {'port': 8041, 'timeout': 31, 'owner': 'alex'}
        self.assertTrue(score_answer('{"port":8041,"timeout":31,"owner":"alex"}', gold)['exact'])
        self.assertFalse(score_answer('I think 8041, 31, alex', gold)['exact'])
        self.assertFalse(score_answer('{"port":true,"timeout":31,"owner":"alex"}', gold)['exact'])

    def test_dataset_gold_is_independent_and_revision_aware(self):
        from baseline.dataset import generate_tasks, infer_gold, task_payload
        tasks = generate_tasks(24, 20261008)
        self.assertEqual(len(tasks), 24)
        self.assertEqual(len({t['id'] for t in tasks}), 24)
        for task in tasks:
            self.assertEqual(infer_gold(task['history'], task['project']), task['gold'])
            self.assertNotIn('gold', task_payload(task))
        self.assertEqual({t['family'] for t in tasks}, {'lookup', 'revision', 'partial'})

    def test_partial_updates_preserve_other_fields(self):
        from baseline.dataset import infer_gold
        history = ['project P12 port=8080 timeout=20 owner=alex',
                   'project P120 port=9999 timeout=99 owner=blair',
                   'project P12 timeout=35', 'project P12 owner=casey']
        self.assertEqual(infer_gold(history, 'P12'),
                         {'port':8080,'timeout':35,'owner':'casey'})


if __name__ == '__main__':
    unittest.main()
