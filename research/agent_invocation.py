"""Exact-message research adapter using a real fresh openJiuwen ReActAgent."""
import importlib.util
import logging
from pathlib import Path
import uuid

# SDK imports otherwise initialize verbose tracing. Suppress before importing.
logging.disable(logging.CRITICAL)

from research.model_gateway import InvocationContractError

ROOT = Path(__file__).resolve().parents[1]
RAIL_PATH = ROOT / 'upstream/jiuwenswarm/agents/harness/common/rails/frozen_messages_rail.py'
_rail_module = None


def load_rail():
    global _rail_module
    if _rail_module is None:
        spec = importlib.util.spec_from_file_location('research_frozen_messages_rail', RAIL_PATH)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _rail_module = module
    return _rail_module


def build_agent(config, messages, max_tokens, on_response):
    """Construct (fresh agent, rail) without registration or network invocation."""
    module = load_rail()
    prepared = module.validate_messages(messages)
    if prepared[-1]['role'] != 'user':
        raise ValueError('Invocation must end with the prepared user question')
    if type(max_tokens) is not int or max_tokens <= 0:
        raise ValueError('max_tokens must be a positive integer')
    if not callable(on_response):
        raise ValueError('on_response must be callable')
    from openjiuwen.core.foundation.llm import ModelClientConfig, ModelRequestConfig
    from openjiuwen.core.single_agent.agents.react_agent import ReActAgent, ReActAgentConfig
    from openjiuwen.core.single_agent.schema.agent_card import AgentCard

    def observed(response, actual_messages):
        metadata = getattr(response, 'usage_metadata', None)
        usage = metadata.model_dump() if hasattr(metadata, 'model_dump') else metadata
        # Persist billable output and raw usage before any post-response check.
        on_response(response.content, usage, actual_messages)

    rail = module.FrozenMessagesRail(prepared, on_response=observed)
    client = ModelClientConfig(client_provider=config['provider'], api_base=config['api_base'],
                               api_key=config['api_key'], timeout=120, max_retries=0)
    settings = ModelRequestConfig(model=config['model'], temperature=0, top_p=1,
                                  max_tokens=max_tokens, extra_body={'thinking': {'type': 'disabled'}})
    agent = ReActAgent(AgentCard(id=uuid.uuid4().hex, name='FrozenMessagesAgent',
                                description='Single-response exact-message evidence adapter.'))
    agent.configure(ReActAgentConfig(model_name=config['model'], model_client_config=client,
                                     model_config_obj=settings, max_iterations=1, prompt_template=[]))
    return agent, rail


async def invoke_agent(config, messages, max_tokens, on_response):
    """Invoke fresh, tool-free ReActAgent; callback(output, usage, actual_messages).

    The callback is synchronous so the gateway can durably record a response
    before downstream agent assembly. Missing/invalid usage is preserved for
    the gateway's fail-closed unknown-spend handling, never fabricated.
    """
    agent, rail = build_agent(config, messages, max_tokens, on_response)
    module = load_rail()
    try:
        await agent.register_rail(rail)
        await agent.invoke({'query': rail.messages[-1]['content'], 'conversation_id': uuid.uuid4().hex})
    except module.FrozenMessagesError as exc:
        raise InvocationContractError(str(exc)) from exc
    if (len(rail.responses) != 1 or rail.model_inputs != [rail.messages]
            or rail.transport_call_count != 1 or rail.transport_messages != rail.messages):
        raise InvocationContractError('Expected one response from exact captured prepared transport messages')
    return rail.responses[0].content
