import asyncio
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from research.discovery import MEMORY_PROTOCOL, PLAN_EXAMPLE, research_artifacts
from research.discovery_revalidate import revalidate_capture
from research.artifacts import save_json
from research import orchestrator
from test_discovery import corpus
from test_discovery_flow import Gateway


class HandoffTests(unittest.TestCase):
    def test_unsupported_design_stops_before_model_configuration(self):
        with TemporaryDirectory() as temp:
            with patch('research.discovery.research_artifacts', side_effect=ValueError('new implementation required')):
                with patch('baseline.runtime.read_model_config') as read:
                    with self.assertRaises(ValueError):
                        asyncio.run(orchestrator.execute(Path(temp)/'run', Path(temp)/'paper', 60000, discovery_dir='design'))
                    read.assert_not_called()

    def test_registered_handoff_keeps_real_question_and_experiment(self):
        with TemporaryDirectory() as temp:
            source = Path(temp)/'source'; source.mkdir(); output = Path(temp)/'derived'
            save_json(source/'manifest.json', {'topic': 'Actual question', 'skill_hashes': {}})
            save_json(source/'sources.json', corpus())
            save_json(source/'closest_work.json', {'status': 'retrieved_not_exhaustive', 'papers': []})
            gateway = Gateway(); calls = []
            for stage in ('literature_review', 'question_formulation', 'experiment_design'):
                result = asyncio.run(gateway.call([], 'discovery/'+stage, 100))
                if stage == 'experiment_design':
                    plan = json.loads(result['output']); plan['adapter'] = 'structured-memory-v1'
                    plan['protocol'] = copy.deepcopy(MEMORY_PROTOCOL); plan['cost_controls']['max_calls'] = 700
                    result['output'] = json.dumps(plan)
                calls.append({'id': stage, 'tag': 'discovery/'+stage, 'status': 'ok',
                    'usage': {'input_tokens': 80, 'output_tokens': 20, 'total_tokens': 100}, **result})
            (source/'calls.jsonl').write_text('\n'.join(json.dumps(c) for c in calls),encoding='utf-8')
            revalidate_capture(source, output)
            brief, experiment = research_artifacts(output)
            self.assertEqual(brief['payload']['hypothesis'], 'Hypothesis')
            self.assertEqual(experiment['payload']['protocol'], MEMORY_PROTOCOL)
            self.assertEqual(experiment['parent_ids'], [brief['artifact_id']])


if __name__ == '__main__': unittest.main()
