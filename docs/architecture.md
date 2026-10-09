# Baseline architecture

The experiment is an opt-in extension of the checked-out JiuwenSwarm source, exercised on the installed openJiuwen ReActAgent. It does not replace or modify the user's desktop installation or private model settings.

1. `baseline/dataset.py` generates deterministic synthetic static histories and ground truth.
2. `context_budget.py` in the JiuwenSwarm source selects whole records, accepting a caller-supplied token counter.
3. `ContextBudgetRail.before_invoke` assembles selected history plus the question. Ground truth is never passed to this rail or the model.
4. `baseline/runtime.py` registers the source rail on a fresh openJiuwen ReActAgent, calls the locally configured model, and records model input/output and API usage from `after_model_call`.
5. `baseline/analyze.py` scores saved outputs, aggregates all calls including summaries, and draws result figures.
6. `baseline/paper.py` uses openJiuwen Model to draft prose from a fixed evidence bundle, then inserts measured tables and verified reference metadata into an ICLR 2026 template. The original model prose is retained; reviewed prose is stored separately.

All answering agents are isolated. There are no tools, persistent-memory evaluation, trained retrieval model, or real multi-turn environment. The 512-token selection budget uses cl100k_base as a proxy; actual resource totals use API-reported usage.
