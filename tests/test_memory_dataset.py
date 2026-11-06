import json
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from research.memory_dataset import generate_tasks, reference_gold, score_memory_answer
from research.memory_analysis import analyze_memory
from research.artifacts import digest


class DatasetTests(unittest.TestCase):
    def test_deterministic_disjoint_realistic_tasks(self):
        tasks = generate_tasks()
        self.assertEqual(tasks, generate_tasks())
        self.assertEqual(len(tasks), 12)
        self.assertEqual(len({t['family'] for t in tasks}), 6)
        self.assertFalse({t['id'] for t in tasks} & {t['id'] for t in generate_tasks(split='dev')})
        self.assertFalse({t['seed'] for t in tasks} & {t['seed'] for t in generate_tasks(split='dev')})
        for task in tasks:
            self.assertGreaterEqual(len(task['records']), 30)
            self.assertEqual([r['observed_at'] for r in task['records']],
                             sorted(r['observed_at'] for r in task['records']))
            for record in task['records']:
                self.assertRegex(record['id'], r'^r\d{3}$')
                self.assertNotIn(task['family'], record['id'])
                self.assertNotIn(task['split'], record['id'])
            gold, evidence = reference_gold(task['records'], task['query'])
            self.assertEqual((gold, evidence), (task['gold'], task['gold_evidence']))
            self.assertIn('JSON', task['question'])
            score = score_memory_answer(json.dumps(gold), task, [r['id'] for r in task['records']])
            self.assertTrue(score['exact'])
            self.assertEqual(score['evidence_recall'], 1)

    def test_reference_bitemporal_conflict_and_delete(self):
        def r(i, value, valid, observed, op='set'):
            return dict(id=i, entity='e', attribute='a', value=value, valid_at=valid,
                        observed_at=observed, operation=op)
        q = dict(entity='e', attributes=['a', 'absent'], as_of=5, known_at=9)
        records = [r('old', 'old', 1, 8), r('new', 'new', 5, 5), r('future', 'later', 8, 8)]
        self.assertEqual(reference_gold(records, q), ({'a': 'new', 'absent': None}, {'a': ['new'], 'absent': []}))
        records.append(r('conflict', 'other', 5, 6))
        self.assertEqual(reference_gold(records, q)[1]['a'], ['conflict', 'new'])
        self.assertIsNone(reference_gold(records, q)[0]['a'])
        records.append(r('delete', None, 6, 7, 'delete'))
        q['as_of'] = 6
        self.assertEqual(reference_gold(records, q)[1]['a'], ['delete'])
        q['known_at'] = 4
        self.assertEqual(reference_gold(records, q)[1]['a'], [])

    def test_scores_context_support_and_strict_json(self):
        task = dict(gold={'a': 'new', 'b': None}, gold_evidence={'a': ['x', 'y'], 'b': ['z']},
                    stale_values={'a': ['old'], 'b': [None, 'deleted']})
        score = score_memory_answer('{"a":"new","b":null}', task, ['x'])
        self.assertEqual(score['supported_fields'], 0)
        self.assertEqual(score['evidence_recall'], 1/3)
        self.assertEqual(score['stale_fields'], 0)
        self.assertEqual(score['refusal_correct'], 1)
        self.assertEqual(score_memory_answer('{"a":"old","b":"deleted"}', task)['stale_fields'], 2)
        self.assertFalse(score_memory_answer('not json', task)['exact'])
        self.assertFalse(score_memory_answer('{"a":"new"}', task)['exact'])
        self.assertFalse(score_memory_answer('{"a":"new","b":null,"extra":1}', task)['exact'])


class AnalysisTests(unittest.TestCase):
    def fixture(self, directory):
        task = generate_tasks(n_per_family=1)[0]
        (directory/'dataset.json').write_text(json.dumps([task]))
        (directory/'manifest.json').write_text(json.dumps({'grid': [dict(task_id=task['id'], policy='full', budget=100)]}))
        result = dict(task_id=task['id'], policy='full', budget=100, answer=json.dumps(task['gold']),
                      selected_ids=[r['id'] for r in task['records']], proxy_tokens=80, status='ok',
                      call_ids=['c1'], elapsed_seconds=1.5)
        call = dict(id='c1', tag='experiment', model='test', output=result['answer'],
                    usage=dict(input_tokens=10, output_tokens=5, total_tokens=15), status='ok', fingerprint='f1')
        (directory/'results.jsonl').write_text(json.dumps(result)+'\n')
        (directory/'calls.jsonl').write_text(json.dumps(call)+'\n')
        return result, call

    def test_dataset_and_optional_result_hashes_are_checked(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            manifest = json.loads((path/'manifest.json').read_text())
            manifest['dataset_sha256'] = 'changed'
            (path/'manifest.json').write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'Dataset hash'):
                analyze_memory(path)
            manifest['dataset_sha256'] = digest(json.loads((path/'dataset.json').read_text()))
            (path/'manifest.json').write_text(json.dumps(manifest))
            result['result_hash'] = 'changed'
            (path/'results.jsonl').write_text(json.dumps(result)+'\n')
            with self.assertRaisesRegex(ValueError, 'Result hash'):
                analyze_memory(path)

    def test_call_tag_cannot_be_swapped_with_identical_answer(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            call['tag'] = 'different-task/full/100/answer'
            (path/'calls.jsonl').write_text(json.dumps(call)+'\n')
            with self.assertRaisesRegex(ValueError, 'tag'):
                analyze_memory(path)

    def test_live_reanalysis_binds_context_selection_request_and_output(self):
        from research.memory_run import code_hashes, answer_messages, load_source, MEMORY_PATH
        from research.model_gateway import invocation_fingerprint
        class Encoder:
            def encode(self, text):
                return list(text)
            def decode(self, tokens):
                return ''.join(tokens)
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            task = json.loads((path/'dataset.json').read_text())[0]
            memory = load_source(MEMORY_PATH, 'test_analysis_memory')
            selection = memory.select_records(task['records'], {**task['query'], 'question': task['question']}, 'full', 100, len)
            result.update(context_text=selection['text'], selected_ids=selection['record_ids'], proxy_tokens=len(selection['text']))
            result['result_hash'] = digest(result)
            call.update(tag=f"{task['id']}/full/100/answer", messages=answer_messages(task, result['context_text']))
            call['fingerprint'] = invocation_fingerprint(call['messages'], call['tag'], 160, 'test', 'offline', 'offline-endpoint')
            request = dict(id=call['id'], fingerprint=call['fingerprint'], tag=call['tag'], messages_hash=digest(call['messages']))
            manifest = json.loads((path/'manifest.json').read_text())
            manifest.update(schema_version=2, protocol='structured-bitemporal-memory-v1', model='test',
                            provider='offline', endpoint_hash='offline-endpoint', answer_max_tokens=160, summary_max_tokens=256,
                            dataset_sha256=digest([task]), code_hashes=code_hashes())
            (path/'manifest.json').write_text(json.dumps(manifest))
            (path/'results.jsonl').write_text(json.dumps(result)+'\n')
            (path/'calls.jsonl').write_text(json.dumps(call)+'\n')
            (path/'requests.jsonl').write_text(json.dumps(request)+'\n')
            with patch('research.memory_analysis._get_encoder', return_value=Encoder()):
                self.assertTrue(analyze_memory(path)['evaluation_complete'])
                original_fingerprint = call['fingerprint']
                call['fingerprint'] = request['fingerprint'] = 'matching-but-not-the-frozen-invocation'
                (path/'calls.jsonl').write_text(json.dumps(call)+'\n')
                (path/'requests.jsonl').write_text(json.dumps(request)+'\n')
                with self.assertRaisesRegex(ValueError, 'Invocation fingerprint'):
                    analyze_memory(path)
                call['fingerprint'] = request['fingerprint'] = original_fingerprint
                (path/'calls.jsonl').write_text(json.dumps(call)+'\n')
                (path/'requests.jsonl').write_text(json.dumps(request)+'\n')
                # Rehashing cannot legitimize a fabricated context or token count.
                result['proxy_tokens'] += 1
                result['result_hash'] = digest({k: v for k, v in result.items() if k != 'result_hash'})
                (path/'results.jsonl').write_text(json.dumps(result)+'\n')
                with self.assertRaisesRegex(ValueError, 'proxy'):
                    analyze_memory(path)
                result['proxy_tokens'] -= 1
                result['selected_ids'] = result['selected_ids'][:-1]
                result['result_hash'] = digest({k: v for k, v in result.items() if k != 'result_hash'})
                (path/'results.jsonl').write_text(json.dumps(result)+'\n')
                with self.assertRaisesRegex(ValueError, 'Selected IDs'):
                    analyze_memory(path)
                result['selected_ids'] = selection['record_ids']
                result['result_hash'] = digest({k: v for k, v in result.items() if k != 'result_hash'})
                (path/'results.jsonl').write_text(json.dumps(result)+'\n')
                call['messages'][-1]['content'] = 'fabricated context'
                (path/'calls.jsonl').write_text(json.dumps(call)+'\n')
                with self.assertRaisesRegex(ValueError, 'Actual answer messages'):
                    analyze_memory(path)
                # A stopped row is analyzable, but never a complete evaluation.
                result.update(status='not_run', answer='', call_ids=[], context_text='', selected_ids=[], proxy_tokens=0)
                result['result_hash'] = digest({k: v for k, v in result.items() if k != 'result_hash'})
                (path/'results.jsonl').write_text(json.dumps(result)+'\n')
                self.assertFalse(analyze_memory(path)['evaluation_complete'])

    def test_instrumentation_errors_mark_spend_and_evaluation_incomplete(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            event = {'id': 'bad-invocation', 'spend_uncertain': True}
            (path/'invocation_errors.jsonl').write_text(json.dumps(event)+'\n')
            summary = analyze_memory(path)
            self.assertEqual(summary['resources']['instrumentation_error_ids'], ['bad-invocation'])
            self.assertFalse(summary['resources']['spend_complete'])
            self.assertFalse(summary['evaluation_complete'])

    def test_analysis_recomputes_and_accounts_unknown_spend(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            summary = analyze_memory(path)
            self.assertEqual(summary['methods'][0]['exact_accuracy'], 1)
            self.assertEqual(summary['resources']['total_tokens'], 15)
            self.assertEqual(summary['resources']['unknown_usage_calls'], 0)
            call.update(id='failed', usage=None, status='unknown', fingerprint='f2')
            with (path/'calls.jsonl').open('a') as f:
                f.write(json.dumps(call)+'\n')
            summary = analyze_memory(path)
            self.assertEqual(summary['resources']['unknown_usage_calls'], 1)
            self.assertFalse(summary['resources']['spend_complete'])
            self.assertFalse(summary['evaluation_complete'])
            self.assertTrue((path/'summary.json').exists())

    def test_pending_request_and_summary_source_context_are_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            result['context_is_summary'] = True
            (path/'results.jsonl').write_text(json.dumps(result)+'\n')
            (path/'requests.jsonl').write_text(json.dumps({'id': 'c1', 'fingerprint': 'f1'})+'\n'+json.dumps({'id': 'pending'})+'\n')
            summary = analyze_memory(path)
            self.assertEqual(summary['methods'][0]['summary_context_tasks'], 1)
            self.assertEqual(summary['resources']['pending_request_ids'], ['pending'])
            self.assertFalse(summary['resources']['spend_complete'])

    def test_analysis_rejects_incomplete_duplicate_and_wrong_call_associations(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            (path/'results.jsonl').write_text('')
            with self.assertRaises(ValueError):
                analyze_memory(path)
            (path/'results.jsonl').write_text((json.dumps(result)+'\n')*2)
            with self.assertRaisesRegex(ValueError, 'Duplicate result'):
                analyze_memory(path)
            result['call_ids'] = ['missing']
            (path/'results.jsonl').write_text(json.dumps(result)+'\n')
            with self.assertRaisesRegex(ValueError, 'association'):
                analyze_memory(path)

    def test_analysis_rejects_answer_changed_from_provider_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            result['answer'] = '{}'
            (path/'results.jsonl').write_text(json.dumps(result)+'\n')
            with self.assertRaises(ValueError):
                analyze_memory(path)

    def test_analysis_pairs_same_split_tasks_and_preserves_raw_files(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            result, call = self.fixture(path)
            second = dict(result, policy='recent', answer='{}', call_ids=['c2'])
            second_call = dict(call, id='c2', output='{}', fingerprint='f2')
            manifest = {'grid': [{k: r[k] for k in ('task_id', 'policy', 'budget')} for r in (result, second)]}
            (path/'manifest.json').write_text(json.dumps(manifest))
            (path/'results.jsonl').write_text('\n'.join(map(json.dumps, (result, second)))+'\n')
            (path/'calls.jsonl').write_text('\n'.join(map(json.dumps, (call, second_call)))+'\n')
            raw = {p.name: p.read_bytes() for p in path.iterdir()}
            summary = analyze_memory(path)
            pair = summary['paired_comparisons'][0]
            self.assertEqual(pair['n'], 1)
            self.assertEqual(abs(pair['mean']), 1)
            self.assertIsNone(pair['descriptive_normal_interval_95'])
            self.assertEqual(raw, {name: (path/name).read_bytes() for name in raw})


if __name__ == '__main__':
    unittest.main()
