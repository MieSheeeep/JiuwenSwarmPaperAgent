import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from research.artifacts import atomic_write, file_digest
from research.workflow import Workflow, Registry, StageResult, STAGES
from research.workflow.agents import AgentExecutor


def output(context):
    w=Workflow(context.directory)
    payload={
        'literature':{'sources':[{'id':'s1','title':'Fixture source','url':'https://example.org','reading_scope':'fixture'}],'comparison':'fixture','limitations':['offline fixture']},
        'question':{'question':'Fixture?','hypothesis':'Fixture','source_ids':['s1'],'falsification':'null'},
        'design':{'dataset':'fixture','split':{'dev':1,'test':1},'methods':['fixture'],'metrics':['exact'],'budget':{},'acceptance':'report all'},
        'implementation':{'adapter':'offline-fixture','version':'1','capabilities':['fixture']},
        'pilot':{'passed':True,'diagnostics':['offline']},
        'experiment':{'results':[],'protocol_hash':w.state['stages']['design'].get('sha256'),'resources':{'calls':0}},
        'analysis':{'metrics':{},'claims':[],'limitations':['offline fixture']},
        'writing':{'title':'Fixture','sections':[{'heading':'Abstract','text':'Offline fixture, not a real paper.'}],
                   'evidence_hash':w.state['stages']['analysis'].get('sha256'),'references':['s1']},
        'review':{'decision':'accept','issues':[]},
        'export':{'files':{},'checks':{'offline_fixture':True}},
    }[context.stage]
    if context.stage=='export':
        atomic_write(context.directory/'fixture.txt','offline workflow fixture')
        payload['files']={'fixture.txt':file_digest(context.directory/'fixture.txt')}
    return StageResult(payload)


def registry():
    result=Registry()
    for s in STAGES[1:]:result.stage(s,output)
    return result


class WorkflowTests(unittest.TestCase):
    def test_complete_offline_chain_and_resume_without_reexecution(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow.create(Path(d)/'project','arbitrary topic')
            result=asyncio.run(w.run(registry()))
            self.assertEqual(result['status'],'completed')
            again=Workflow(w.directory)
            self.assertEqual(asyncio.run(again.run(Registry()))['status'],'completed')
            self.assertEqual(result['usage'],{'calls':0,'tokens':0})
            self.assertEqual(len(list((w.directory/'artifacts').glob('*.json'))),len(STAGES))

    def test_review_routes_back_to_writing_and_preserves_old_versions(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow.create(Path(d)/'project','topic');r=registry();calls=[]
            def review(c):
                calls.append(1)
                return StageResult({'decision':'revise','target':'writing','issues':['clarify']}) if len(calls)==1 else output(c)
            r.handlers['review']=review
            self.assertEqual(asyncio.run(w.run(r))['status'],'completed')
            self.assertEqual(w.state['revisions'],1)
            self.assertEqual(w.state['stages']['writing']['attempts'],2)
            self.assertEqual(len(w.state['feedback']),1)

    def test_tampering_stops_resume(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow.create(Path(d)/'project','topic')
            path=w.directory/w.state['stages']['topic']['artifact']
            atomic_write(path,'{}')
            with self.assertRaisesRegex(ValueError,'integrity'):
                asyncio.run(w.run(registry()))

    def test_failed_executor_requires_accounting_before_resume(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow.create(Path(d)/'project','topic');r=registry()
            def fail(c):raise RuntimeError('transport interrupted')
            r.handlers['literature']=fail
            self.assertEqual(asyncio.run(w.run(r))['status'],'needs_input')
            w.resume()
            self.assertTrue(asyncio.run(w.run(registry()))['interrupted'])
            w.reconcile(usage={'calls':1,'tokens':50},note='provider ledger checked')
            self.assertEqual(asyncio.run(w.run(registry()))['status'],'completed')
            self.assertEqual(w.status()['usage']['tokens'],50)

    def test_missing_executor_and_pause_are_explicit(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow.create(Path(d)/'project','topic')
            self.assertEqual(asyncio.run(w.run(Registry()))['status'],'needs_input')
            w.resume();w.pause()
            self.assertEqual(asyncio.run(w.run(registry()))['status'],'paused')
            self.assertEqual(w.next_stage(),'literature')

    def test_tool_loop_uses_registered_tool_without_network(self):
        with tempfile.TemporaryDirectory() as d:
            w=Workflow.create(Path(d)/'project','topic');seen=[]
            async def model(messages,context,step):
                seen.append(messages)
                value=({'action':'tool','name':'search','arguments':{'query':'topic'}} if step==0 else
                       {'action':'final','payload':output(context).payload})
                return {'output':json.dumps(value),'usage':{'total_tokens':3}}
            r=Registry().tool('search',lambda query:{'query':query,'fixture':True})
            r.stage('literature',AgentExecutor(model,tools=['search']))
            result=asyncio.run(w.run(r,until='literature'))
            self.assertEqual(result['next_stage'],'question')
            self.assertEqual(result['usage'],{'calls':2,'tokens':6})
            self.assertIn('tool_result',seen[-1][-2]['content'])


if __name__=='__main__':unittest.main()
