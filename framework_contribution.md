# JiuwenSwarm source contribution

Base source commit: `f0a69728c96b5961d993449f1a901cbd2f4dac5b`.
Local branch: `baseline/context-budget`.

Added a pure whole-record context selector, an opt-in `ContextBudgetRail`, and an export in the existing rails package. The selector supports full history, a contiguous recent suffix, and exact project-ID lexical retrieval. Summary injection is optional via a caller-provided async function. The rail captures actual model responses for traceability and does not change default app behavior.

The experiment driver loads these exact source files and registers the rail on openJiuwen ReActAgent. Unit tests cover strict joined-text budgets, chronology, exact project-ID matching, partial updates, invalid policies, and answer scoring; a real API smoke run and 96 task/policy trials verify integration.

Patch: `output/framework_contribution.patch`. No PR has been published. This local baseline package is not yet a complete competition submission: it has no Stanford Agentic Reviewer access token and has not undergone official reproduction review.
