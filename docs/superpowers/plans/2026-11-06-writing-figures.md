# Writing and Figure Studio Implementation Plan

**Goal:** Implement the user-approved error analysis, follow-up experiment plan, English manuscript revisions/compilation and integrated figure skills.

**Architecture:** Preserve the reviewed release. Save new immutable revisions in output/workbench/{run}/revisions, with English sections, safely generated LaTeX, explicit evidence hashes, versioned PDF/figures and job logs. Registered local figure executors implement publication rules; external image generation is a separately marked optional provider.

**Scope:** English plain-text section editing; generated read-only LaTeX preview; no arbitrary TeX execution, shell entry, uploaded scripts, new paid model calls, invented benchmark results or automatic review-score reuse. PDF compile uses fixed arguments, no shell escape, no dependency installer, finite timeout and local asset allowlist. Draft PDF has explicit unreviewed revision labeling.

## Tasks

- [x] Offline error analysis: add research/error_analysis.py, tests and generated English case/family report plus source-backed next-experiment plan. Count retrieval-insufficiency vs answer-errors descriptively, without claiming causal explanations. LongMemEval official source: https://github.com/xiaowu0162/LongMemEval . No benchmark calls in this task.
- [x] Add failing workbench revision tests: original immutability, content validation, optimistic concurrency, unknown revision/path/figure rejection, edited prose escaping, job/compile failures. Implement revision store and registered chart/architecture renderers with artifact hashes and rule provenance.
- [x] Add guarded JSON mutation endpoints and asynchronous bounded jobs, downloads for explicit revision assets, error analysis GET. Preserve existing read-only routes and protect writes with same-origin checks, JSON content type and per-server token.
- [x] Add Chinese writing/figure studio page: select sections/revisions, save, compare text changes, preview generated LaTeX, generate figures, compile and poll logs, display separate original/draft PDF status. Figures use English labels, true fixed-split data, PDF/SVG/PNG and editable architecture source.
- [x] Validate unit/regression suites, build, browser edit/save/compile/figure flows and PDF rendering. Independently review code; document skill integration and limitations, local startup and exact verification results.

## Verification — 2026-11-06

91 Python tests passed. Production TypeScript/Vite build passed. Five Edge browser scenarios passed, including real revision save, dirty navigation protection, one transient polling failure and successful two-pass PDF compilation. Independent review findings corrected; follow-up found no remaining P1/P2. Original reviewed PDF remains byte-identical. Final LaTeX pass has no undefined references or overfull warnings. External AI schematics remains explicitly unavailable; no new model calls.
