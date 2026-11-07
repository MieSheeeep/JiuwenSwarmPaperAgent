import asyncio
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from research.workflow.skillpack import SkillPack
from research.workflow.cold_review import cold_review


class SkillTests(unittest.TestCase):
    def test_actual_resources_are_verified_and_recorded_in_model_prompt(self):
        with tempfile.TemporaryDirectory() as d:
            pack = SkillPack()
            prompt = pack.instructions('writing/draft', Path(d))
            self.assertIn('Prepare Conference Manuscripts', prompt)
            self.assertIn('Return JSON', prompt)
            record = next((Path(d)/'skill_usage').glob('*.json'))
            usage = json.loads(record.read_text(encoding='utf-8'))
            self.assertEqual(usage['commit'], pack.manifest['commit'])
            self.assertGreater(len(usage['files']), 1)
            self.assertEqual(pack.instructions('test/x/method/0', Path(d)), '')
            with self.assertRaises(ValueError):
                pack.read('../private.txt')

    def test_modified_upstream_resource_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)/'pack'
            shutil.copytree(SkillPack().root, root)
            path = root/'skills/prepare-conference-manuscripts/SKILL.md'
            path.write_text('changed', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'integrity'):
                SkillPack(root).instructions('writing/draft', Path(d)/'project')

    def test_cold_panel_excludes_author_history_and_executes_saved_answer_artifact(self):
        async def run(root):
            seen = []
            async def ask(role, data, tag):
                seen.append((tag, data))
                self.assertNotIn('PRIVATE_AUTHOR_HISTORY', json.dumps(data))
                if tag == 'review/cold/meta':
                    return {'decision':'accept', 'issues':[], 'adjudications':[]}
                return {'findings':[]}
            material = {'manuscript':{'title':'Negative result', 'sections':[], 'author_notes':'PRIVATE_AUTHOR_HISTORY'},
                'author_history':'PRIVATE_AUTHOR_HISTORY',
                'design':{'methods':['m'], 'split':{'dev':[], 'test':['t']}},
                'results':[{'task_id':'t','method':'m','answer':'Paris','em':1.0,'f1':1.0,
                            'documents':2,'tokens':7}],
                'metrics':{'m':{'n':1,'exact':1.0,'f1':1.0,'mean_documents':2.0,'provider_tokens':7}},
                'dataset':[{'id':'t','split':'test','answer':'Paris'}]}
            result = await cold_review(root, material, ask)
            self.assertEqual(result['decision'], 'accept')
            self.assertEqual(len(seen), 6)
            report = json.loads((root/result['round']/'execution.json').read_text())
            self.assertEqual(report['exit_code'], 0)
            self.assertIn('saved-answer', report['scope'])
            self.assertIn('verified', report['stdout'])
            manifest = json.loads((root/result['round']/'isolation.json').read_text())
            self.assertIn('artifact/replay.py', manifest['files'])
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root/'author_history.txt').write_text('PRIVATE_AUTHOR_HISTORY')
            asyncio.run(run(root))

    def test_meta_review_must_adjudicate_every_finding(self):
        from research.workflow.cold_review import validate_adjudication
        reports = [{'findings':[{'id':'claim-1','severity':'major','issue':'Unsupported superiority'}]}]
        with self.assertRaises(ValueError):
            validate_adjudication({'decision':'accept','issues':[],'adjudications':[]}, reports)
        with self.assertRaises(ValueError):
            validate_adjudication({'decision':'accept','issues':[], 'adjudications':[
                {'id':'claim-1','status':'confirmed','reason':'Evidence absent','repair':'Narrow claim','cost':'sentence'}]}, reports)

    def test_released_scorer_matches_edge_cases_and_rejects_changed_scores(self):
        from research.workflow.qa_metrics import score
        from research.workflow import replay_review
        cases=[('', ''), ('noanswer x', 'noanswer'), ('Yes', 'yes'),
               ('The Paris!', 'Paris'), ('a cat cat', 'cat'), ('Berlin', 'Paris')]
        rows=[];dataset=[]
        for i,(prediction,gold) in enumerate(cases):
            exact,f1=score(prediction,gold)
            dataset.append({'id':str(i),'split':'test','answer':gold})
            rows.append({'task_id':str(i),'method':'m','answer':prediction,'em':exact,'f1':f1,'documents':2,'tokens':7})
        material={'design':{'methods':['m'],'split':{'test':[t['id'] for t in dataset]}},
            'dataset':dataset,'results':rows,'metrics':{'m':{'n':len(rows),
                'exact':sum(r['em'] for r in rows)/len(rows),'f1':sum(r['f1'] for r in rows)/len(rows),
                'mean_documents':2.0,'provider_tokens':7*len(rows)}}}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            shutil.copy2(replay_review.__file__,path/'replay.py')
            (path/'evidence.json').write_text(json.dumps(material),encoding='utf-8')
            def run():
                return subprocess.run([sys.executable,'-I','replay.py'],cwd=path,capture_output=True,text=True,timeout=30)
            result=run()
            self.assertEqual(result.returncode,0,result.stderr)
            material['results'][0]['em']=0.123
            (path/'evidence.json').write_text(json.dumps(material),encoding='utf-8')
            self.assertNotEqual(run().returncode,0)


if __name__ == '__main__':
    unittest.main()
