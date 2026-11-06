import logging
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

logging.disable(logging.CRITICAL)

from research import agent_invocation as invocation

MESSAGES = [{'role': 'system', 'content': 'Use exact evidence.\n'},
            {'role': 'user', 'content': 'First question'},
            {'role': 'assistant', 'content': 'Initial answer'},
            {'role': 'user', 'content': 'Reflect on that answer.'}]
CONFIG = {'provider': 'OpenAI', 'api_base': 'https://example.invalid/v1',
          'api_key': 'offline-test-key', 'model': 'offline-test-model'}


class AgentInvocationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_sdk_transport_receives_exact_reflection_messages_once(self):
        from openjiuwen.core.foundation.llm import Model
        from openjiuwen.core.foundation.llm.schema.message import AssistantMessage
        from openjiuwen.core.foundation.llm.schema.message import UsageMetadata
        calls, saved = [], []
        async def fake_transport(self, *args, **kwargs):
            messages = kwargs.get('messages', args[0] if args else None)
            calls.append(invocation.load_rail().canonical_messages(messages))
            return AssistantMessage(content='Answer', usage_metadata=UsageMetadata(
                input_tokens=30, output_tokens=3, total_tokens=33))
        with patch.object(Model, 'invoke', fake_transport):
            result = await invocation.invoke_agent(CONFIG, MESSAGES, 32,
                lambda output, usage, messages: saved.append((output, usage, messages)))
        self.assertEqual(calls, [MESSAGES])
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0][0], 'Answer')
        self.assertEqual({k: saved[0][1][k] for k in ('input_tokens', 'output_tokens', 'total_tokens')},
                         {'input_tokens': 30, 'output_tokens': 3, 'total_tokens': 33})
        self.assertEqual(saved[0][2], MESSAGES)
        self.assertEqual(result, 'Answer')

    async def test_rail_restores_context_after_exception_and_limits_calls(self):
        module = invocation.load_rail()
        rail = module.FrozenMessagesRail(MESSAGES)
        original = SimpleNamespace(session_id=lambda: 's')
        ctx = SimpleNamespace(context=original, inputs=SimpleNamespace(messages=[], tools=['unwanted'], response=None))
        await rail.before_model_call(ctx)
        self.assertIsNot(ctx.context, original)
        window = await ctx.context.get_context_window(system_messages=['injected'], tools=['tool'])
        self.assertEqual(module.canonical_messages(window.get_messages()), MESSAGES)
        self.assertEqual(window.get_tools(), [])
        await rail.on_model_exception(ctx)
        self.assertIs(ctx.context, original)
        with self.assertRaises(module.FrozenMessagesError):
            await rail.before_model_call(ctx)

    async def test_callback_captures_actual_inputs_before_mismatch_failure(self):
        module = invocation.load_rail()
        saved = []
        rail = module.FrozenMessagesRail(MESSAGES, on_response=lambda r, m: saved.append((r, m)))
        original = SimpleNamespace()
        ctx = SimpleNamespace(context=original, inputs=SimpleNamespace(messages=[], tools=None, response=None))
        await rail.before_model_call(ctx)
        ctx.inputs.messages = [{'role': 'user', 'content': 'changed'}]
        ctx.inputs.response = SimpleNamespace(content='paid answer')
        with self.assertRaises(module.FrozenMessagesError):
            await rail.after_model_call(ctx)
        self.assertEqual(saved[0][1], [{'role': 'user', 'content': 'changed'}])
        self.assertIs(ctx.context, original)

    async def test_transport_guard_rejects_changed_messages_and_tools_before_call(self):
        module = invocation.load_rail()
        transport = SimpleNamespace(invoke=AsyncMock())
        rail = module.FrozenMessagesRail(MESSAGES)
        checked = module._CheckedModel(transport, rail)
        for kwargs in ({'messages': [{'role': 'user', 'content': 'changed'}]},
                       {'messages': MESSAGES, 'tools': ['unexpected tool']}):
            with self.assertRaises(module.FrozenMessagesError):
                await checked.invoke(**kwargs)
        transport.invoke.assert_not_called()
        transport.invoke.return_value = 'response'
        self.assertEqual(await checked.invoke(messages=MESSAGES), 'response')
        with self.assertRaises(module.FrozenMessagesError):
            await checked.invoke(messages=MESSAGES)
        self.assertEqual(transport.invoke.call_count, 1)

    async def test_absent_usage_stays_unknown_and_second_response_is_refused(self):
        from openjiuwen.core.foundation.llm import Model
        from openjiuwen.core.foundation.llm.schema.message import AssistantMessage
        saved = []
        with patch.object(Model, 'invoke', AsyncMock(return_value=AssistantMessage(content='No usage'))):
            await invocation.invoke_agent(CONFIG, MESSAGES, 32,
                lambda output, usage, messages: saved.append((output, usage, messages)))
        self.assertEqual(saved, [('No usage', None, MESSAGES)])
        module = invocation.load_rail()
        rail = module.FrozenMessagesRail(MESSAGES)
        original = SimpleNamespace()
        ctx = SimpleNamespace(context=original, inputs=SimpleNamespace(messages=MESSAGES, tools=None,
                                                                       response=SimpleNamespace(content='once')))
        await rail.after_model_call(ctx)
        with self.assertRaises(module.FrozenMessagesError):
            await rail.after_model_call(ctx)
        self.assertEqual(len(rail.responses), 1)

    async def test_fresh_agent_construction_and_fake_agent_invocation(self):
        agent, rail = invocation.build_agent(CONFIG, MESSAGES, 32, lambda *args: None)
        self.assertEqual(agent._config.max_iterations, 1)
        self.assertEqual(agent._config.model_config_obj.max_tokens, 32)
        self.assertEqual(agent._config.model_client_config.max_retries, 0)
        agent2, _ = invocation.build_agent(CONFIG, MESSAGES, 32, lambda *args: None)
        self.assertIsNot(agent, agent2)
        self.assertNotEqual(agent.card.id, agent2.card.id)

    async def test_actual_sdk_error_restores_context_and_never_calls_callback(self):
        from openjiuwen.core.foundation.llm import Model
        agent, rail = invocation.build_agent(CONFIG, MESSAGES, 32, lambda *args: self.fail('No response'))
        await agent.register_rail(rail)
        with patch.object(Model, 'invoke', AsyncMock(side_effect=RuntimeError('offline transport failure'))):
            try:
                await agent.invoke({'query': MESSAGES[-1]['content'], 'conversation_id': 'offline-failure'})
            except Exception:
                pass
        self.assertEqual(rail.responses, [])
        self.assertIsNone(rail._original_context)
        self.assertEqual(rail.model_call_count, 1)

    def test_invalid_messages_rejected_without_sdk_or_transport(self):
        for messages in ([], [{'role': 'tool', 'content': 'x'}], [{'role': 'user', 'content': 'x', 'name': 'extra'}]):
            with self.assertRaises(ValueError):
                invocation.build_agent(CONFIG, messages, 32, lambda *args: None)
        with self.assertRaises(ValueError):
            invocation.build_agent(CONFIG, MESSAGES, 0, lambda *args: None)


if __name__ == '__main__':
    unittest.main()
