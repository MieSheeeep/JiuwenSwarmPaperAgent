import copy,json,tempfile,unittest
from pathlib import Path
import research.external_benchmark as eb


def row(i='q1',family='knowledge-update'):
 return dict(question_id=i,question_type=family,question='What changed?',answer='SECRET GOLD',question_date='2023/06/01',haystack_session_ids=['s1','s2'],haystack_dates=['2023/01/01','2023/05/01'],haystack_sessions=[[dict(role='user',content='Old detail',has_answer=False)],[dict(role='assistant',content='New detail',has_answer=True)]],answer_session_ids=['s2'])

class ExternalBenchmarkTests(unittest.TestCase):
 def source(self,p,rows):
  p.write_text(json.dumps(rows),encoding='utf-8'); return p
 def test_schema_and_no_annotation_leaks(self):
  with tempfile.TemporaryDirectory() as td:
   task=eb.load_longmemeval(self.source(Path(td)/'source.json',[row()]))[0]
  self.assertEqual(task['gold'],'SECRET GOLD'); self.assertEqual(task['gold_session_ids'],['s2'])
  self.assertEqual(task['sessions'][1],dict(id='s2',date='2023/05/01',text='assistant: New detail'))
  messages=eb.build_external_messages(task,['s2']); encoded=json.dumps(messages)
  self.assertNotIn('SECRET GOLD',encoded); self.assertNotIn('has_answer',encoded); self.assertNotIn('valid_at',encoded)
  self.assertIn('s2',encoded); self.assertIn('2023/05/01',encoded); self.assertIn(task['question'],encoded)
 def test_reject_malformed_missing_and_duplicate(self):
  with tempfile.TemporaryDirectory() as td:
   p=Path(td)/'x.json'
   for bad in [dict(question_id='x'),dict(row(),haystack_dates=[]),dict(row(),answer_session_ids=['missing']),dict(row(),answer=None),dict(row(),haystack_sessions=[[{'role':'user'}],[]])]:
    with self.subTest(bad=bad),self.assertRaises(ValueError): eb.load_longmemeval(self.source(p,[bad]))
   with self.assertRaises(ValueError): eb.load_longmemeval(self.source(p,[row(),row()]))
   with self.assertRaises(FileNotFoundError): eb.load_longmemeval(Path(td)/'missing')
 def test_deterministic_proportional_stratification_and_split(self):
  tasks=[dict(id=f'{f}{i}',family=f) for f,n in [('a',60),('b',30),('abstention',10)] for i in range(n)]
  selected=eb.stratified_sample(tasks,20,7)
  self.assertEqual(selected,eb.stratified_sample(list(reversed(tasks)),20,7))
  self.assertEqual({f:sum(x['family']==f for x in selected) for f in ('a','b','abstention')},dict(a=12,b=6,abstention=2))
  dev,test=eb.disjoint_dev_test(tasks,20,30,7)
  self.assertEqual((len(dev),len(test)),(20,30)); self.assertFalse({x['id'] for x in dev}&{x['id'] for x in test})
  with self.assertRaises(ValueError): eb.stratified_sample(tasks,101,0)
 def test_proxy_scores_and_recall(self):
  self.assertEqual(eb.evaluate_answer('The RED, car!','red car')['exact_normalized'],1)
  self.assertAlmostEqual(eb.evaluate_answer('red car','red truck')['proxy_token_f1'],.5)
  self.assertTrue(eb.evaluate_answer('a','a')['needs_semantic_judge'])
  self.assertEqual(eb.evidence_recall(['s1','s1'],['s1','s2']),.5)
  self.assertIsNone(eb.evidence_recall([],[]))
 def test_frozen_checksum_refuses_changes(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); p=self.source(root/'source.json',[row(),row('q2','temporal-reasoning')]); out=root/'run'
   result=eb.prepare_external(out,p,n=2,seed=3)
   self.assertEqual(result['source_sha256'],eb.sha256_file(p)); self.assertEqual(len(json.loads((out/'tasks.json').read_text())),2)
   self.assertEqual(result,eb.prepare_external(out,p,n=2,seed=3))
   (out/'tasks.json').write_text('[]')
   with self.assertRaises(ValueError): eb.prepare_external(out,p,n=2,seed=3)
 def test_wrong_source_provenance_and_changed_source_refused(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); p=self.source(root/'source.json',[row()])
   provenance=root/'source_manifest.json'; provenance.write_text(json.dumps(dict(sha256='wrong')))
   with self.assertRaises(ValueError): eb.prepare_external(root/'run',p,n=1)
   provenance.unlink(); eb.prepare_external(root/'run',p,n=1)
   self.source(p,[dict(row(),answer='changed')])
   with self.assertRaises(ValueError): eb.prepare_external(root/'run',p,n=1)
 def test_custom_compatible_source_is_never_certified_original(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td); source=self.source(root/'custom.json',[row()])
   manifest=eb.prepare_external(root/'unverified',source,n=1)
   self.assertEqual(manifest['benchmark'],'LongMemEval-compatible custom/unverified')
   self.assertFalse(manifest['original_source_verified'])
   # Matching a caller-written provenance hash/revision does not certify data.
   (root/'source_manifest.json').write_text(json.dumps(dict(
    dataset='xiaowu0162/longmemeval-cleaned',
    revision='98d7416c24c778c2fee6e6f3006e7a073259d48f',sha256=eb.sha256_file(source))))
   manifest=eb.prepare_external(root/'claimed_original',source,n=1)
   self.assertEqual(manifest['benchmark'],'LongMemEval-compatible custom/unverified')
   self.assertFalse(manifest['original_source_verified'])
 def test_actual_pinned_source_remains_verified_original(self):
  source=Path(__file__).resolve().parents[1]/'sources/external_benchmarks/longmemeval_s_cleaned.json'
  if not source.is_file(): self.skipTest('pinned public source not downloaded')
  with tempfile.TemporaryDirectory() as td:
   manifest=eb.prepare_external(Path(td)/'run',source,n=0)
  self.assertEqual(manifest['benchmark'],'LongMemEval original cleaned')
  self.assertTrue(manifest['original_source_verified'])
 def test_unknown_selected_id_rejected(self):
  with self.assertRaises(ValueError): eb.build_external_messages(dict(sessions=[],question='q'),['missing'])
 def test_source_duplicate_session_ids_preserved_as_repeated_occurrences(self):
  entry=row(); entry['haystack_session_ids']=['s2','s2']
  with tempfile.TemporaryDirectory() as td:
   tasks=eb.load_longmemeval(self.source(Path(td)/'x.json',[entry]))
  self.assertEqual([s['id'] for s in tasks[0]['sessions']],['s2','s2'])
  self.assertEqual(eb.corpus_statistics(tasks)['tasks_with_repeated_session_ids'],1)
 def test_numeric_source_gold_becomes_string(self):
  with tempfile.TemporaryDirectory() as td:
   tasks=eb.load_longmemeval(self.source(Path(td)/'x.json',[dict(row(),answer=3)]))
  self.assertEqual(tasks[0]['gold'],'3')
 def test_stats_include_full_corpus_lengths(self):
  with tempfile.TemporaryDirectory() as td:
   tasks=eb.load_longmemeval(self.source(Path(td)/'x.json',[row(),row('q_abs')]))
  stats=eb.corpus_statistics(tasks)
  self.assertEqual(stats['instances'],2); self.assertEqual(stats['families'],{'knowledge-update':1,'abstention':1})
  self.assertEqual(stats['sessions_per_task']['min'],2); self.assertGreater(stats['history_words_per_task']['max'],0)

if __name__=='__main__': unittest.main()
