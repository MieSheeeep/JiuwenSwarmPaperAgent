"""Offline contract tests for the opt-in structured memory selector."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'upstream/jiuwenswarm/agents/harness/common/versioned_memory.py'

def load_memory():
    spec = importlib.util.spec_from_file_location('isolated_versioned_memory', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def record(id, attribute='color', value='red', valid=1, observed=1, operation='set'):
    return dict(id=id, entity='item', attribute=attribute, value=value,
                valid_at=valid, observed_at=observed, operation=operation)

class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(SOURCE.exists(), 'standalone memory module must exist')
        self.memory = load_memory()
        self.query = dict(entity='item', attributes=['color', 'size'], as_of=5, known_at=10)

    def select(self, records, policy='versioned', budget=10000):
        return self.memory.select_records(records, self.query, policy, budget, len)

    def test_late_old_fact_does_not_replace_current_value(self):
        result = self.select([record('new', valid=4, observed=4), record('old', value='blue', valid=2, observed=9)])
        self.assertEqual(result['record_ids'], ['new'])
        self.assertEqual(json.loads(result['text'])['id'], 'new')

    def test_both_historical_and_known_at_cutoffs(self):
        result = self.select([record('ok'), record('future', valid=6), record('unknown', valid=4, observed=11)])
        self.assertEqual(result['record_ids'], ['ok'])

    def test_conflicts_preserve_all_tied_evidence(self):
        records = [record('a', valid=4), record('b', value='blue', valid=4, observed=5), record('s', 'size', 'L', 2, 3)]
        result = self.select(records)
        self.assertEqual(set(result['record_ids']), {'a', 'b', 's'})
        self.assertEqual(result['conflicts'], ['color'])
        self.assertNotIn('gold', result)

    def test_tombstone_and_partial_update_preserve_provenance(self):
        records = [record('a'), record('s', 'size', 'L'), record('d', valid=3, operation='delete')]
        self.assertEqual(set(self.select(records)['record_ids']), {'s', 'd'})

    def test_conflict_group_is_atomic_and_attribute_coverage_wins(self):
        records = [record('a', valid=4), record('b', value='blue', valid=4), record('s', 'size', 'L')]
        size = len(json.dumps(records[2], ensure_ascii=False, sort_keys=True, separators=(',', ':')))
        result = self.select(records, budget=size)
        self.assertEqual(result['record_ids'], ['s'])
        self.assertLessEqual(result['proxy_tokens'], size)

    def test_all_policies_use_same_joined_text_counter_and_do_not_mutate(self):
        records = [record('a'), record('b', value='blue', valid=2)]
        before = json.dumps(records)
        for policy in ('full', 'recent', 'lexical', 'bm25', 'versioned', 'no_time', 'no_conflict'):
            result = self.select(records, policy, 1)
            self.assertEqual(result['proxy_tokens'], len(result['text']))
            if policy != 'full':
                self.assertLessEqual(result['proxy_tokens'], 1)
        self.assertEqual(before, json.dumps(records))

    def test_recent_is_contiguous_suffix(self):
        records = [record('small'), record('large', value='x' * 1000)]
        self.assertEqual(self.select(records, 'recent', 200)['record_ids'], [])

    def test_ablations_change_only_the_intended_time_and_conflict_rules(self):
        records = [record('a', valid=4, observed=2), record('b', value='blue', valid=4, observed=3), record('future', valid=8, observed=4), record('unknown', valid=9, observed=11)]
        self.assertEqual(self.select(records, 'no_time')['record_ids'], ['future'])
        self.assertEqual(self.select(records, 'no_conflict')['record_ids'], ['b'])

    def test_store_roundtrip_and_duplicate_rejection(self):
        tmp = ROOT / 'runtime/test_tmp'
        tmp.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=tmp) as directory:
            store = self.memory.VersionedMemoryStore([record('a')])
            store.append(record('b', valid=2))
            path = Path(directory) / 'memory.jsonl'
            store.save(path)
            loaded = self.memory.VersionedMemoryStore.load(path)
            self.assertEqual(loaded.records, store.records)
            with self.assertRaises(ValueError):
                loaded.append(record('a'))

    def test_reject_invalid_contract(self):
        with self.assertRaises(ValueError):
            self.select([record('x'), record('x')])
        with self.assertRaises(ValueError):
            self.select([record('x')], 'unknown')
        with self.assertRaises(ValueError):
            self.select([record('x')], budget=-1)

    def test_retrieval_ranks_query_overlap_and_bm25_frequency(self):
        records = [record('irrelevant', attribute='noise', value='other'),
                   record('match', attribute='noise', value='color color color')]
        budget = len(json.dumps(records[1], ensure_ascii=False, sort_keys=True, separators=(',', ':')))
        for policy in ('lexical', 'bm25'):
            self.assertEqual(self.select(records, policy, budget)['record_ids'], ['match'])

    def test_evaluation_annotations_never_enter_selected_source_text(self):
        annotated = {**record('source'), 'gold': 'secret answer', 'gold_evidence': ['hidden']}
        result = self.select([annotated], 'full')
        self.assertNotIn('secret answer', result['text'])
        self.assertNotIn('gold', result['text'])

class RailTests(unittest.TestCase):
    def test_rail_injects_metadata_and_records_and_observes_response(self):
        from unittest.mock import patch
        path = SOURCE.parent / 'rails/versioned_memory_rail.py'
        self.assertTrue(path.exists(), 'opt-in rail must exist')
        base = types.ModuleType('openjiuwen.core.single_agent.rail.base')
        base.AgentRail = type('AgentRail', (), {})
        with patch.dict(sys.modules, {'openjiuwen.core.single_agent.rail.base': base}):
            spec = importlib.util.spec_from_file_location('isolated_memory_rail', path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        query = dict(entity='item', attributes=['color'], as_of=5, known_at=10)
        calls = []
        rail = module.VersionedMemoryRail([record('a')], query, 'Which color?', 'versioned', 1000, len,
                                         selector=load_memory().select_records,
                                         on_response=lambda response, messages: calls.append((response, messages)))
        inputs = SimpleNamespace(query='old', response=None, messages=[])
        ctx = SimpleNamespace(inputs=inputs)
        # These hooks have no suspension point. Drive them directly to avoid
        # Windows event-loop socket creation in an offline sandbox.
        with self.assertRaises(StopIteration):
            rail.before_invoke(ctx).send(None)
        self.assertIn('Which color?', inputs.query)
        self.assertIn('"known_at":10', inputs.query)
        self.assertIn('"id":"a"', inputs.query)
        self.assertEqual(rail.selection['record_ids'], ['a'])
        inputs.response = {'content': '{"color":"red"}'}
        inputs.messages = [{'role': 'user', 'content': inputs.query}]
        with self.assertRaises(StopIteration):
            rail.after_model_call(ctx).send(None)
        self.assertEqual(calls[0][0], inputs.response)
        self.assertEqual(calls[0][1], inputs.messages)

if __name__ == '__main__':
    unittest.main()
