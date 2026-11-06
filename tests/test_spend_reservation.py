import asyncio
from datetime import datetime,timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from research.artifacts import digest
from research.model_gateway import BudgetExceeded
from research.spend_reservation import ReservedSpendGateway,load_reserves


class SpendReservationTests(unittest.TestCase):
    def fixture(self,p):
        request={'id':'failed','fingerprint':'prior','tag':'prior/answer','reserved_tokens':1200,
                 'created_at':datetime.now(timezone.utc).isoformat()}
        call={'id':'failed','fingerprint':'prior','status':'unknown','usage':None,'output':'','error_type':'FrameworkError'}
        (p/'requests.jsonl').write_text(json.dumps(request)+'\n');(p/'calls.jsonl').write_text(json.dumps(call)+'\n')
        registry={'schema_version':1,'mode':'conservative_reservation_not_actual_usage','authorization':'Explicit continuation',
                  'entries':[{'id':'failed','request_sha256':digest(request),'call_sha256':digest(call),'reserved_tokens':10000,'reason':'unknown transport'}]}
        (p/'admission_reserves.json').write_text(json.dumps(registry))
        return registry

    def gateway(self,p,cap):
        return ReservedSpendGateway({'model':'fake','provider':'OpenAI','api_base':'https://invalid','api_key':'never-save'},p,
                 max_total_tokens=cap,max_calls=20,wall_seconds=600,count_tokens=lambda s:len(s.split()))

    def test_hold_is_charged_to_admission_without_fabricating_usage(self):
        with TemporaryDirectory() as d:
            p=Path(d);self.fixture(p);g=self.gateway(p,12000)
            async def invoke(record):record('answer',{'input_tokens':20,'output_tokens':5,'total_tokens':25},[])
            asyncio.run(g.call([{'role':'user','content':'hi'}],'new/answer',20,invoke))
            totals=g.totals()
            self.assertEqual(totals['known_api_tokens'],25)
            self.assertEqual(totals['reserved_unknown_tokens'],10000)
            self.assertEqual(totals['admission_total_tokens'],10025)
            self.assertEqual(totals['unknown_spend_ids'],[])
            self.assertEqual(totals['unresolved_usage_ids'],['failed'])
            self.assertIsNone(g.calls[0]['usage'])

    def test_hold_prevents_call_when_actual_usage_alone_would_admit(self):
        with TemporaryDirectory() as d:
            p=Path(d);self.fixture(p);g=self.gateway(p,10500)
            async def forbidden(record):self.fail('Must not spend')
            with self.assertRaises(BudgetExceeded):asyncio.run(g.call([], 'new/answer',20,forbidden))

    def test_changed_or_reduced_reservation_is_rejected(self):
        with TemporaryDirectory() as d:
            p=Path(d);registry=self.fixture(p)
            registry['entries'][0]['reserved_tokens']=0
            (p/'admission_reserves.json').write_text(json.dumps(registry))
            with self.assertRaises(ValueError):load_reserves(p)
            registry['entries'][0]['reserved_tokens']=10000
            registry['entries'][0]['call_sha256']='tampered'
            (p/'admission_reserves.json').write_text(json.dumps(registry))
            with self.assertRaises(ValueError):load_reserves(p)
