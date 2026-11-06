import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from research.upgrade_manuscript import check_sections, compact_evidence, reconcile_experiment, verify_analysis_sources,parse_json_object,load_references


class UpgradeManuscriptTests(unittest.TestCase):
    def test_new_study_does_not_inherit_old_external_not_run_annotation(self):
        with TemporaryDirectory() as d:
            ref=next(r for r in load_references(Path(d)) if r['key']=='longmemeval')
            self.assertNotIn('not evaluated here',ref['finding'])
            self.assertIn('evaluated here',ref['finding'])

    def test_markdown_json_envelope_is_accepted_without_extracting_arbitrary_prose(self):
        self.assertEqual(parse_json_object('```json\n{"text":"English prose."}\n```'),{'text':'English prose.'})
        with self.assertRaises(ValueError):parse_json_object('Untrusted prefix {"text":"fragment"}')
        with self.assertRaises(ValueError):parse_json_object('[]')

    def test_analysis_cannot_describe_an_older_result_ledger(self):
        from research.artifacts import file_digest
        with TemporaryDirectory() as d:
            p=Path(d)
            for n in ('grid.json','dataset.json','results.jsonl','judgments.jsonl','calls.jsonl'):(p/n).write_text('[]')
            analysis={'source_hashes':{n:file_digest(p/n) for n in ('grid.json','dataset.json','results.jsonl','judgments.jsonl','calls.jsonl')}}
            verify_analysis_sources(p,analysis)
            (p/'results.jsonl').write_text('changed')
            with self.assertRaises(ValueError):verify_analysis_sources(p,analysis)

    def test_writer_rejects_stale_totals_pending_and_unmerged_segments(self):
        with TemporaryDirectory() as d:
            p=Path(d);(p/'run_state.json').write_text('{"status":"complete","active_workers":0}')
            (p/'requests.jsonl').write_text('{"id":"a"}\n')
            (p/'calls.jsonl').write_text(json.dumps({'id':'a','usage':{'input_tokens':10,'output_tokens':2,'total_tokens':12}})+'\n')
            summary={'completed':0,'resources':{'total_calls':1,'total_tokens':11}}
            with self.assertRaises(ValueError):reconcile_experiment(p,summary)
            summary['resources']['total_tokens']=12
            self.assertEqual(reconcile_experiment(p,summary),12)
            (p/'run_state.json').write_text('{"status":"complete","active_workers":1}')
            with self.assertRaises(ValueError):reconcile_experiment(p,summary)
            (p/'run_state.json').write_text('{"status":"complete","active_workers":0}')
            (p/'segments/w').mkdir(parents=True)
            (p/'segments/w/requests.jsonl').write_text('{"id":"unmerged"}\n')
            with self.assertRaises(ValueError):reconcile_experiment(p,summary)
            (p/'segments/w/requests.jsonl').write_text('')
            (p/'requests.jsonl').write_text('{"id":"a"}\n{"id":"pending"}\n')
            with self.assertRaises(ValueError):reconcile_experiment(p,summary)

    def test_measured_numbers_and_unknown_references_do_not_enter_free_prose(self):
        sections={k:'Cautious evidence-based prose.' for k in ('abstract','introduction','related_work','methods','discussion','conclusion')}
        self.assertFalse(check_sections(sections,{'temporal'}))
        sections['methods']='We use all-MiniLM-L6-v2 and BM25 as retrieval components.'
        self.assertFalse(check_sections(sections,{'temporal'}))
        sections['abstract']='We achieved 99 percent [made_up].'
        self.assertTrue(check_sections(sections,{'temporal'}))

    def test_compact_evidence_preserves_partial_completion_and_cohorts(self):
        summary={'evaluation_complete':False,'completed':10,'planned':30,'methods':[
          {'kind':'external','cohort':'external_matched','phase':'external','reader':'baseline','repeat':0,'model':'m','policy':'hybrid','budget':1024,'tasks':4,'planned_tasks':9,'exact_correct':1,'exact_accuracy':.25,'judge_correct':2,'judge_scored':4,'judge_accuracy':.5,'actual_total_tokens':100}],
          'resources':{'total_tokens':100},'limitations':['not official']}
        evidence=compact_evidence(summary,{})
        self.assertFalse(evidence['evaluation_complete'])
        self.assertEqual(evidence['completed'],10)
        self.assertEqual(evidence['comparisons'][0]['cohort'],'external_matched')


if __name__=='__main__':unittest.main()
