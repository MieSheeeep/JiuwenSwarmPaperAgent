import asyncio
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT / 'runtime/test_tmp'
TEMP.mkdir(parents=True, exist_ok=True)


class GatewayTests(unittest.TestCase):
    def gateway(self, directory, cap=5000):
        from research.model_gateway import ModelGateway
        return ModelGateway({'model': 'fake', 'provider': 'OpenAI', 'api_base': 'https://example.invalid',
                             'api_key': 'never-save-me'}, directory,
                            max_total_tokens=cap, max_calls=5, wall_seconds=60,
                            count_tokens=lambda text: len(text.split()))

    def test_real_usage_is_durable_and_exact_request_resumes(self):
        with TemporaryDirectory(dir=TEMP) as directory:
            async def invoke(record):
                record('answer', {'input_tokens': 20, 'output_tokens': 5, 'total_tokens': 25}, [])
                return 'answer'
            gateway = self.gateway(directory)
            row = asyncio.run(gateway.call([{'role': 'user', 'content': 'hi'}], 'task/policy/answer', 20, invoke))
            self.assertEqual(row['usage']['total_tokens'], 25)
            async def forbidden(record):
                self.fail('cached response must not invoke a model')
            recovered = self.gateway(directory)
            same = asyncio.run(recovered.call([{'role': 'user', 'content': 'hi'}], 'task/policy/answer', 20, forbidden))
            self.assertEqual(same['id'], row['id'])
            self.assertNotIn('never-save-me', ''.join(p.read_text() for p in Path(directory).glob('*.jsonl')))

    def test_no_call_when_token_reservation_exceeds_cap(self):
        from research.model_gateway import BudgetExceeded
        with TemporaryDirectory(dir=TEMP) as directory:
            async def forbidden(record):
                self.fail('budget must be checked before invocation')
            with self.assertRaises(BudgetExceeded):
                asyncio.run(self.gateway(directory, cap=1).call([], 'x', 20, forbidden))

    def test_unknown_billable_attempt_blocks_future_calls_and_restart(self):
        from research.model_gateway import UnknownSpend
        with TemporaryDirectory(dir=TEMP) as directory:
            async def failed(record):
                raise TimeoutError('may have reached provider')
            gateway = self.gateway(directory)
            with self.assertRaises(UnknownSpend):
                asyncio.run(gateway.call([], 'first', 20, failed))
            with self.assertRaises(UnknownSpend):
                asyncio.run(self.gateway(directory).call([], 'second', 20, failed))
            self.assertEqual(len((Path(directory) / 'requests.jsonl').read_text().splitlines()), 1)

    def test_response_survives_agent_postprocessing_failure(self):
        with TemporaryDirectory(dir=TEMP) as directory:
            async def broken_after_response(record):
                record('saved', {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12}, [])
                raise RuntimeError('agent postprocessing error')
            gateway = self.gateway(directory)
            row = asyncio.run(gateway.call([], 'task', 20, broken_after_response))
            self.assertEqual(row['output'], 'saved')
            self.assertEqual(len(gateway.calls), 1)

    def test_pending_request_after_crash_blocks_new_spend(self):
        from research.model_gateway import UnknownSpend
        with TemporaryDirectory(dir=TEMP) as directory:
            (Path(directory) / 'requests.jsonl').write_text(json.dumps({'id': 'pending'}) + '\n')
            gateway = self.gateway(directory)
            with self.assertRaises(UnknownSpend):
                asyncio.run(gateway.call([], 'new', 20))

    def test_missing_usage_never_counts_as_zero(self):
        from research.model_gateway import UnknownSpend
        with TemporaryDirectory(dir=TEMP) as directory:
            async def unknown(record):
                record('answer', None, [])
                return 'answer'
            with self.assertRaises(UnknownSpend):
                asyncio.run(self.gateway(directory).call([], 'first', 20, unknown))

    def test_experiment_contract_failure_is_not_postprocessing_success(self):
        from research.model_gateway import InvocationContractError
        with TemporaryDirectory(dir=TEMP) as directory:
            async def invalid(record):
                record('saved', {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12}, [])
                raise InvocationContractError('context mismatch')
            with self.assertRaises(InvocationContractError):
                asyncio.run(self.gateway(directory).call([], 'task', 20, invalid))
            with self.assertRaises(InvocationContractError):
                asyncio.run(self.gateway(directory).call([], 'task', 20, invalid))

    def test_restart_does_not_reset_wall_clock_allowance(self):
        from research.model_gateway import BudgetExceeded
        from datetime import datetime, timezone, timedelta
        with TemporaryDirectory(dir=TEMP) as directory:
            gateway = self.gateway(directory)
            async def invoke(record):
                record('ok', {'input_tokens': 1, 'output_tokens': 1, 'total_tokens': 2}, [])
            asyncio.run(gateway.call([], 'first', 20, invoke))
            path = Path(directory) / 'requests.jsonl'
            row = json.loads(path.read_text().strip())
            row['created_at'] = (datetime.now(timezone.utc) - timedelta(seconds=120)).isoformat()
            path.write_text(json.dumps(row) + '\n')
            with self.assertRaises(BudgetExceeded):
                asyncio.run(self.gateway(directory).call([], 'second', 20, invoke))

    def test_multiple_responses_are_accounted_and_fail_closed(self):
        from research.model_gateway import InvocationContractError, UnknownSpend
        with TemporaryDirectory(dir=TEMP) as directory:
            async def duplicate(record):
                usage = {'input_tokens': 10, 'output_tokens': 2, 'total_tokens': 12}
                record('first', usage, [])
                record('second', usage, [])
            gateway = self.gateway(directory)
            with self.assertRaises(InvocationContractError):
                asyncio.run(gateway.call([], 'first', 20, duplicate))
            self.assertEqual(gateway.totals()['known_api_tokens'], 24)
            self.assertTrue(gateway.totals()['unknown_spend_ids'])
            with self.assertRaises(UnknownSpend):
                asyncio.run(self.gateway(directory).call([], 'next', 20, duplicate))

    def test_malformed_usage_is_preserved_as_unknown_not_zero(self):
        from research.model_gateway import UnknownSpend
        with TemporaryDirectory(dir=TEMP) as directory:
            async def malformed(record):
                record('answer', {'input_tokens': 10}, [])
            gateway = self.gateway(directory)
            with self.assertRaises(UnknownSpend):
                asyncio.run(gateway.call([], 'first', 20, malformed))
            self.assertIsNone(gateway.calls[0]['usage'])
            self.assertEqual(gateway.calls[0]['raw_usage'], {'input_tokens': 10})


if __name__ == '__main__':
    unittest.main()
def test_jsonl_preserves_unicode_line_separators_in_source_text(tmp_path):
    from research.model_gateway import append_durable, read_jsonl
    path=tmp_path/'calls.jsonl'
    row={'output':'PDF passage\u2028next line\u2029paragraph\u0085continued','usage':{'total_tokens':3}}
    append_durable(path,row)
    assert read_jsonl(path)==[row]
