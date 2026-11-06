import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
import asyncio
from unittest.mock import patch
from research.artifacts import digest
from research.model_gateway import ModelGateway
from research.review_upgrade import _row_summary

from research.review_upgrade import build_dataset, freeze_protocol, synthetic_messages, paired_intervals, execute_grid


class UpgradeTests(unittest.TestCase):
    def test_unrun_conditions_are_not_erased_from_method_denominators(self):
        common={'kind':'external','split':'test','model':'m','policy':'hybrid','packer':'rank_first','reader':'baseline','budget':1024,'repeat':0,'cohort':'external_matched','phase':'external'}
        rows=[{**common,'task_id':'a','status':'ok','score':{'exact':True}}, {**common,'task_id':'b','status':'not_run'}]
        method=_row_summary(rows)[0]
        self.assertEqual(method['tasks'],1)
        self.assertEqual(method['planned_tasks'],2)
        self.assertEqual(method['missing_or_failed'],1)
    def test_fresh_multiseed_dataset_and_packing_stress(self):
        tasks=build_dataset()
        self.assertGreaterEqual(len(tasks),90)
        self.assertTrue(any(t['family']=='packing_stress' for t in tasks))
        dev={t['source_seed'] for t in tasks if t['split']=='dev'}
        heldout={t['source_seed'] for t in tasks if t['split']=='test'}
        self.assertFalse(dev & heldout)

    def test_prompts_do_not_receive_gold(self):
        task=build_dataset()[0]
        task['gold']={'secret':'NEVER_INCLUDE_GOLD_SENTINEL'}
        for reader in ('baseline','conflict_aware','reflection'):
            messages=synthetic_messages(task,'records',reader)
            self.assertNotIn('NEVER_INCLUDE_GOLD_SENTINEL',json.dumps(messages))

    def test_protocol_cannot_mutate_after_freeze(self):
        with TemporaryDirectory() as d:
            freeze_protocol(Path(d),models=['test-model'],token_limit=300000)
            with self.assertRaises(ValueError): freeze_protocol(Path(d),models=['different-model'],token_limit=300000)

    def test_paired_analysis_clusters_repeated_tasks(self):
        rows=[]
        for task in ('a','b','c'):
            for repeat in range(3):
                for reader in ('baseline','conflict_aware'):
                    rows.append({'task_id':task,'repeat':repeat,'model':'m','policy':'versioned','packer':'smaller_first','reader':reader,'budget':256,'split':'test','kind':'synthetic','status':'ok','score':{'exact':reader=='conflict_aware'}})
        result=paired_intervals(rows)
        self.assertTrue(result)
        self.assertEqual(result[0]['task_clusters'],3)

    def test_real_gateway_mock_transport_resumes_without_double_call(self):
        task=build_dataset()[0]
        item={'id':'test-row','kind':'synthetic','task_id':task['id'],'family':task['family'],'split':task['split'],
              'model':'m','policy':'full','packer':'rank_first','reader':'baseline','budget':256,'repeat':0,'phase':'test','cohort':'test'}
        original=ModelGateway.call;transport_calls=[]
        async def simulated(gateway,messages,tag,max_tokens=256,invoke=None):
            async def transport(record):
                transport_calls.append(tag);answer=json.dumps(task['gold'])
                record(answer,{'input_tokens':10,'output_tokens':2,'total_tokens':12},messages)
                return answer
            return await original(gateway,messages,tag,max_tokens,invoke=transport)
        with TemporaryDirectory() as temporary:
            directory=Path(temporary)
            config={'model':'m','provider':'mock','api_base':'https://example.test','api_key':'never-save-this'}
            protocol,_=freeze_protocol(directory,models=['m'],token_limit=300000,provider='mock',endpoint_hash=digest(config['api_base']))
            async def run():return await execute_grid(directory,protocol,[task],[],[item],config=config,count_tokens=lambda t:len(t)//4,tokenizer=None,encoder=None)
            with patch('research.review_upgrade.ModelGateway.call',new=simulated):
                self.assertTrue(asyncio.run(run())['evaluation_complete'])
                self.assertTrue(asyncio.run(run())['evaluation_complete'])
                self.assertEqual(len(transport_calls),1)
                calls=directory/'calls.jsonl';row=json.loads(calls.read_text());row['messages'][0]['content']='changed'
                calls.write_text(json.dumps(row)+'\n')
                with self.assertRaises(ValueError):asyncio.run(run())
                self.assertEqual(len(transport_calls),1)
            self.assertNotIn('never-save-this',''.join(p.read_text() for p in directory.glob('*.json*')))


if __name__=='__main__':unittest.main()
