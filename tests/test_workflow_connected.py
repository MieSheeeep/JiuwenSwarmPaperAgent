import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from research.artifacts import save_json, atomic_write, file_digest
from research.workflow import Workflow
from research.workflow.profile import ConnectedProfile


class Sources:
    def search(self,query,limit):
        return [{'id':'s1','title':'First source','url':'https://example.org/1'},
                {'id':'s2','title':'Second source','url':'https://example.org/2'}]

    def read(self,paper):
        return {**paper,'reading_scope':'fixture','chunks':[{'text':'Offline source fixture.'}]}


class ConnectedTests(unittest.TestCase):
    def test_all_real_stage_handlers_connect_with_injected_transports(self):
        async def check(root):
            dataset=root/'data.json'
            save_json(dataset,[{'id':split,'question':'Which city hosts lab X?','answer':'Paris','split':split,
                'passages':[{'id':'p0','title':'Lab X','text':'Lab X is in Paris.'},
                            {'id':'p1','title':'Other','text':'Unrelated information.'}]} for split in ('dev','test')])
            w=Workflow.create(root/'project','QA study',constraints={'dataset_path':str(dataset),'literature_query':'all:retrieval'})
            sent=[]
            async def model(messages,context,tag):
                sent.append((tag,messages))
                if tag.startswith(('dev/','test/')):
                    request=json.loads(messages[-1]['content'])
                    self.assertNotIn('answer',request)
                    self.assertEqual(set(request),{'question','documents'})
                    value={'answer':'Paris','sufficient':True}
                elif tag=='literature/compare':value={'comparison':'fixture','limitations':['offline']}
                elif tag=='question/propose':value={'question':'Does retrieval help?','hypothesis':'Maybe',
                    'source_ids':['s1','s2'],'falsification':'No gain'}
                elif tag=='design/propose_method':value={'name':'generated_select','budget':2,
                    'description':'Fixture selection','motivation':'Offline integration'}
                elif tag.startswith('implementation/code/'):value={
                    'source':'def select(question, passages, budget):\n    return [p["id"] for p in passages[:budget]]',
                    'explanation':'Offline fixture method'}
                elif tag=='writing/outline':value={'outline':['Methods','Results'],'limitations':['offline']}
                elif tag=='writing/draft':value={'title':'Offline integration fixture',
                    'sections':[{'heading':h,'text':'Offline fixture paragraph. '*65} for h in
                        ['Abstract','Introduction','Related Work','Methods','Experimental Setup','Results','Discussion','Limitations','Conclusion','Reproducibility']],
                    'references':[{'id':'s1','title':'First source','url':'https://example.org/1'}]}
                elif tag=='review/cold/meta':value={'decision':'accept','issues':[],'adjudications':[]}
                elif tag.startswith('review/cold/'):value={'findings':[]}
                else:raise AssertionError(tag)
                return {'id':str(len(sent)),'output':json.dumps(value),'usage':{'total_tokens':5}}
            def compile_fixture(manuscript):
                # Explicit fake compiler: this validates wiring, not a PDF or scientific outcome.
                target=w.directory/'fixture.txt';atomic_write(target,manuscript['title'])
                return {'files':{'fixture.txt':file_digest(target)},'checks':{'compiled':True},'fixture':True}
            profile=ConnectedProfile(w.directory,model=model,client=Sources(),compiler=compile_fixture,
                                     releaser=lambda root,value:{'fixture':True})
            result=await w.run(profile.registry())
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['usage']['calls'],len(sent))
            self.assertEqual(w.artifact('experiment')['payload']['protocol_hash'],w.state['stages']['design']['sha256'])
            self.assertTrue(w.artifact('analysis')['payload']['metrics'])
            draft=next(messages for tag,messages in sent if tag=='writing/draft')
            self.assertIn('Prepare Conference Manuscripts',draft[0]['content'])
            self.assertIn('authoritative_facts',draft[1]['content'])
            self.assertEqual(w.artifact('review')['payload']['decision'],'accept')
            skill_tags={json.loads(p.read_text())['tag'] for p in (w.directory/'skill_usage').glob('*.json')}
            self.assertIn('writing/draft',skill_tags)
            self.assertIn('review/cold/meta',skill_tags)
            call_ids={json.loads(p.read_text())['call_id'] for p in (w.directory/'skill_calls').glob('*.json')}
            self.assertEqual(len(call_ids),len(skill_tags))
            before=len(sent)
            await Workflow(w.directory).run(profile.registry())
            self.assertEqual(before,len(sent))
        with tempfile.TemporaryDirectory() as d:asyncio.run(check(Path(d)))

    def test_failed_pilot_cannot_be_bypassed_by_resume(self):
        from test_workflow_framework import registry,output
        async def check(root):
            w=Workflow.create(root/'project','topic')
            r=registry()
            from research.workflow import StageResult
            r.handlers['pilot']=lambda c:StageResult({'passed':False,'diagnostics':['invalid response']})
            await w.run(r)
            w.resume()
            result=await w.run(r)
            self.assertEqual(result['status'],'needs_input')
            self.assertEqual(result['next_stage'],'experiment')
        with tempfile.TemporaryDirectory() as d:asyncio.run(check(Path(d)))


if __name__=='__main__':unittest.main()
