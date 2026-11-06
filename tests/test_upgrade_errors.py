import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.upgrade_errors import analyze_errors


class UpgradeErrorTests(unittest.TestCase):
    def test_missing_and_external_are_not_synthetic_failures(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            grid=[dict(id=str(i),kind=kind,task_id='same',phase='mechanism',cohort='test',model=model,
                       reader='baseline',policy='versioned',packer='smaller_first',budget=256,repeat=0)
                  for i,(kind,model) in enumerate([('synthetic','flash'),('synthetic','pro'),('external','flash')])]
            (p/'grid.json').write_text(json.dumps(grid))
            (p/'dataset.json').write_text(json.dumps([{'id':'same','family':'conflict','gold':{'x':None},'question':'a\u2028b','gold_evidence':{'x':['r1','r2']}}]))
            row={**grid[0],'status':'ok','answer':'{}','selected_ids':['r1','r2'],
                 'score':{'exact':False,'evidence_recall':1.0}}
            (p/'results.jsonl').write_text(json.dumps(row,ensure_ascii=False)+'\n',encoding='utf-8')
            r=analyze_errors(p)
            self.assertEqual(r['overview']['expected_rows'],2)
            self.assertEqual(r['overview']['missing_rows'],1)
            self.assertEqual(r['overview']['complete_evidence_errors'],1)
            self.assertEqual(r['overview']['scored_rows'],1)
            self.assertEqual(r['cases'][0]['missing_evidence_ids'],[])
            self.assertEqual(r['excluded_external_rows'],1)

    def test_duplicate_result_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d)
            (p/'dataset.json').write_text('[]');(p/'grid.json').write_text('[]')
            (p/'results.jsonl').write_text('{"id":"a"}\n{"id":"a"}\n')
            with self.assertRaises(ValueError):analyze_errors(p)
