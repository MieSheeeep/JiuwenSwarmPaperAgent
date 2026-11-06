import json
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from workbench.data import Repository
from workbench.upgrade import payload,file_path


class WorkbenchUpgradeTests(unittest.TestCase):
    def test_empty_project_still_has_explicit_unrun_state(self):
        with TemporaryDirectory() as d:
            result=payload(Repository(d))
            self.assertEqual(result['score'],None)
            self.assertEqual(len(result['gaps']),10)
            self.assertEqual(result['summary'],{})

    def test_live_ledgers_override_stale_counter_without_exposing_messages(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'output/review_upgrade_20261106';p.mkdir(parents=True)
            (p/'summary.json').write_text('{"completed":0}')
            (p/'calls.jsonl').write_text(json.dumps({'id':'a','messages':[{'content':'PRIVATE_TEXT_SENTINEL'}],'usage':{'total_tokens':15}})+'\n')
            (p/'requests.jsonl').write_text('{"id":"a"}\n')
            (p/'results.jsonl').write_text('{"id":"r"}\n')
            result=payload(Repository(d))
            self.assertEqual(result['summary']['completed'],1)
            self.assertEqual(result['summary']['resources']['total_tokens'],15)
            self.assertNotIn('PRIVATE_TEXT_SENTINEL',json.dumps(result))

    def test_unsafe_report_filename_rejected(self):
        with TemporaryDirectory() as d:
            with self.assertRaises(KeyError):file_path(Repository(d),'../config.local/config.yaml')

    def test_pdf_from_stale_evidence_is_not_exposed(self):
        with TemporaryDirectory() as d:
            p=Path(d)/'output/review_upgrade_20261106';(p/'paper').mkdir(parents=True)
            for name,data in [('summary.json',b'{}'),('analysis.json',b'{}'),('paper/paper.pdf',b'pdf')]:
                (p/name).write_bytes(data)
            h=lambda name:hashlib.sha256((p/name).read_bytes()).hexdigest()
            (p/'paper/writing_status.json').write_text(json.dumps({'status':'succeeded','paper_sha256':h('paper/paper.pdf'),
                'source_summary_sha256':h('summary.json'),'source_analysis_sha256':h('analysis.json')}))
            self.assertEqual(file_path(Repository(d),'paper.pdf'),(p/'paper/paper.pdf').resolve())
            (p/'summary.json').write_text('{"updated":true}')
            with self.assertRaises(KeyError):file_path(Repository(d),'paper.pdf')


if __name__=='__main__':unittest.main()
