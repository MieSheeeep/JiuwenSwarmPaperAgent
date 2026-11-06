import asyncio
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.artifacts import save_json
from research.discovery import discover, load_bundle, PLAN_EXAMPLE, STAGES
from test_discovery import corpus, notes


class Client:
    def search(self, query, limit): return corpus()
    def read(self, paper): return paper


class Gateway:
    def __init__(self, bad_quote=False): self.calls = []; self.bad_quote = bad_quote
    def totals(self): return {'api_calls': len(self.calls), 'known_api_tokens': len(self.calls) * 100}
    async def call(self, messages, tag, max_tokens):
        self.calls.append(tag)
        if tag.endswith(STAGES[0]):
            result = notes()
            if self.bad_quote: result['papers'][0]['evidence'][0]['quote'] = 'hallucination'
        elif tag.endswith(STAGES[1]):
            result = {'candidates': [{'id': 'g1', 'question': 'Question', 'hypothesis': 'Hypothesis',
                'motivation': 'Motivation', 'source_ids': ['p1', 'p2'], 'novelty_status': 'unverified',
                'falsification': 'No improvement', 'verification_query': 'all:memory'}], 'selected_id': 'g1'}
        else: result = copy.deepcopy(PLAN_EXAMPLE)
        return {'output': json.dumps(result)}


class FlowTests(unittest.TestCase):
    def run_flow(self, directory, gateway, topic='Memory'):
        return asyncio.run(discover(directory, topic=topic, query='all:memory', max_total_tokens=60000,
            config={'model': 'fake', 'provider': 'OpenAI', 'api_base': 'https://example.invalid'},
            count_tokens=len, client=Client(), gateway=gateway))

    def test_chain_uses_three_skills_then_resumes_without_calls(self):
        with TemporaryDirectory() as temp:
            gateway = Gateway(); bundle = self.run_flow(temp, gateway)
            self.assertEqual(gateway.calls, ['discovery/' + stage for stage in STAGES])
            self.assertEqual(bundle['handoff']['status'], 'implementation_required')
            self.assertFalse(bundle['handoff']['experiments_executed'])
            again = Gateway(); self.run_flow(temp, again)
            self.assertEqual(again.calls, [])
            self.assertEqual(load_bundle(temp)['experiment_design'], bundle['experiment_design'])

    def test_changed_artifacts_and_inputs_block_resume(self):
        with TemporaryDirectory() as temp:
            self.run_flow(temp, Gateway())
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.run_flow(temp, Gateway(), topic='Different')
            path = Path(temp) / 'sources.json'
            path.write_text('[]', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.run_flow(temp, Gateway())

    def test_missing_hash_inventory_is_not_a_valid_completed_design(self):
        with TemporaryDirectory() as temp:
            self.run_flow(temp, Gateway())
            path = Path(temp) / 'state.json'
            state = json.loads(path.read_text(encoding='utf-8')); state['artifact_hashes'].pop('sources.json')
            save_json(path, state)
            with self.assertRaisesRegex(ValueError, 'inventory'): load_bundle(temp)

    def test_workbench_view_excludes_source_chunks_and_private_transport(self):
        from workbench.data import Repository
        from workbench.discovery import payload
        with TemporaryDirectory() as temp:
            directory = Path(temp)/'output/discovery_test'
            self.run_flow(directory, Gateway())
            (directory/'calls.jsonl').write_text('PRIVATE_TRANSPORT', encoding='utf-8')
            rows = payload(Repository(temp))
            self.assertEqual(len(rows), 1)
            self.assertNotIn('chunks', rows[0]['bundle']['sources'][0])
            self.assertNotIn('PRIVATE_TRANSPORT', json.dumps(rows))

    def test_hallucinated_quote_stops_before_question_generation(self):
        with TemporaryDirectory() as temp:
            gateway = Gateway(bad_quote=True)
            with self.assertRaisesRegex(ValueError, 'quotation'): self.run_flow(temp, gateway)
            self.assertEqual(len(gateway.calls), 1)
            state = json.loads((Path(temp) / 'state.json').read_text(encoding='utf-8'))
            self.assertEqual(state['status'], 'stopped')
            self.assertFalse((Path(temp) / 'handoff.json').exists())


if __name__ == '__main__': unittest.main()
