# Framework module calls

- `openjiuwen.core.single_agent.agents.react_agent.ReActAgent`: one answering call for each task/policy, no tools, max_iterations=1.
- `ReActAgentConfig`, `AgentCard`, `register_rail`: construct and register the source extension on a fresh agent.
- `openjiuwen.core.single_agent.rail.base.AgentRail`: implemented by the new JiuwenSwarm `ContextBudgetRail`.
- `before_invoke`: inject selected history into the current task's query; persistent tool-message histories are not modified.
- `after_model_call`: record response and usage; the runner verifies selected context reached the model and exactly one answer call was instrumented.
- `openjiuwen.core.foundation.llm.Model`, `ModelClientConfig`, `ModelRequestConfig`: summary calls and evidence-bound manuscript drafting.

The runner loads the added JiuwenSwarm files directly from `upstream` to avoid installing the development branch's different dependencies over the user's app. This is source-extension validation on openJiuwen, not a test of the complete desktop or Swarm assembly. The source package also exports the new rail for installation-based use.
