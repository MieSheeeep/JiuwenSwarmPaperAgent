import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from research.artifacts import save_json
from research.discovery import load_bundle
from research.discovery_revalidate import revalidate_capture
from test_discovery import corpus, notes
from test_discovery_flow import Gateway
import asyncio


class RevalidationTests(unittest.TestCase):
    def test_revalidate_saved_responses_without_network_or_model(self):
        with TemporaryDirectory() as temp:
            source = Path(temp) / 'source'; source.mkdir(); target = Path(temp) / 'target'
            save_json(source/'manifest.json', {'topic': 'Memory', 'skill_hashes': {}})
            save_json(source/'sources.json', corpus())
            save_json(source/'closest_work.json', {'status': 'retrieved_not_exhaustive', 'papers': []})
            gateway = Gateway(); calls = []
            for stage in ('literature_review', 'question_formulation', 'experiment_design'):
                response = asyncio.run(gateway.call([], 'discovery/' + stage, 100))
                calls.append({'id': stage, 'tag': 'discovery/' + stage, 'status': 'ok',
                    'usage': {'input_tokens': 80, 'output_tokens': 20, 'total_tokens': 100}, **response})
            (source/'calls.jsonl').write_text('\n'.join(json.dumps(c) for c in calls), encoding='utf-8')
            before = (source/'calls.jsonl').read_bytes()
            revalidate_capture(source, target)
            self.assertEqual(load_bundle(target)['handoff']['status'], 'implementation_required')
            state = json.loads((target/'state.json').read_text(encoding='utf-8'))
            self.assertEqual(state['resources']['known_api_tokens'], 300)
            self.assertEqual(state['new_model_calls'], 0)
            self.assertEqual((source/'calls.jsonl').read_bytes(), before)
            with self.assertRaises(ValueError): revalidate_capture(source, target)


if __name__ == '__main__': unittest.main()
