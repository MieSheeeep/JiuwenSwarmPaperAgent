import asyncio
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest


class ResponseLoggingTests(unittest.TestCase):
    def test_response_hook_saves_usage_before_postprocessing(self):
        from baseline.runtime import ModelRuntime
        response = SimpleNamespace(content='{}', finish_reason='stop',
            usage_metadata=SimpleNamespace(model_dump=lambda: {'input_tokens': 5, 'output_tokens': 2}))
        with TemporaryDirectory() as directory:
            runtime = ModelRuntime({'model': 'test'}, directory)
            rail = runtime.rail_module.ContextBudgetRail([], 'question', 'full', 10,
                len, runtime.policy.select_history,
                on_response=lambda r, m: runtime.record_response(r, m, 'task/full/answer', 0.1))
            asyncio.run(rail.after_model_call(SimpleNamespace(inputs=SimpleNamespace(
                response=response, messages=[{'role': 'user', 'content': 'history'}]))))
            # Simulate no result being written: a fresh runtime must recover the
            # successful billable response independently of agent postprocessing.
            recovered = ModelRuntime({'model': 'test'}, directory)
            self.assertEqual(len(recovered.calls), 1)
            self.assertEqual(recovered.calls[0]['usage']['input_tokens'], 5)
            self.assertEqual(recovered.calls[0]['messages'][0]['content'], 'history')


if __name__ == '__main__':
    unittest.main()
