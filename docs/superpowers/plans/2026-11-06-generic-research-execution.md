# Generic Research Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a safe registered-adapter experiment loop so a literature-derived question can produce reproducible results and a paper draft without executing arbitrary model code.

**Architecture:** A frozen `adaptive-qa-v1` protocol generates a deterministic multi-hop QA dataset, chooses contexts with three audited policies, invokes the existing durable ModelGateway, and emits a result-bound paper draft. Discovery accepts only this adapter or the existing structured-memory adapter.

**Tech Stack:** Python 3, unittest, existing `research.model_gateway`, JSON artifacts, optional pdflatex.

---

### Task 1: Define and validate the registered protocol

**Files:**
- Create: `research/experiment_protocol.py`
- Test: `tests/test_generic_research.py`

- [ ] Write tests for a valid adaptive plan, rejection of unknown adapters, and rejection of shell commands.
- [ ] Run `python -m unittest tests.test_generic_research -v`; confirm the new imports/behavior fail.
- [ ] Implement the adapter registry, exact protocol constants, plan validation, and result hash helper.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Build a deterministic multi-hop QA adapter

**Files:**
- Create: `research/qa_dataset.py`
- Modify: `research/experiment_protocol.py`
- Test: `tests/test_generic_research.py`

- [ ] Add a fixed-seed dataset generator with two-hop support passages and distractors.
- [ ] Add context selection for `single_pass`, `fixed_two`, and `adaptive_stop`.
- [ ] Add strict answer normalization/scoring and tests for reproducibility and adaptive evidence coverage.
- [ ] Run the focused tests.

### Task 3: Run the generic experiment with durable accounting

**Files:**
- Create: `research/generic_runner.py`
- Test: `tests/test_generic_research.py`

- [ ] Write an offline invoke stub test checking result rows contain context hash, call IDs, and score fields.
- [ ] Run it red.
- [ ] Implement bounded execution, per-call JSON prompts, ledger reuse, stopped-state handling, and aggregate summary.
- [ ] Run focused tests and the existing model gateway tests.

### Task 4: Generate a result-bound paper draft and connect discovery

**Files:**
- Create: `research/generic_paper.py`
- Modify: `research/discovery.py`
- Test: `tests/test_generic_research.py`, `tests/test_discovery.py`

- [ ] Test that paper numbers are recomputed from result rows and that discovery accepts the registered adapter.
- [ ] Run tests red.
- [ ] Implement Markdown/LaTeX-safe draft generation and `adaptive-qa-v1` discovery handoff artifacts.
- [ ] Run focused and full regression tests.

### Task 5: Execute and document a real small run

**Files:**
- Create: `docs/generic_research_run_20261106.md`
- Create: `output/generic_qa_run_20261106/` (generated, selected artifacts only)

- [ ] Run the 12-task/3-method offline verification.
- [ ] Run one bounded DeepSeek-backed experiment if the configured API is available; otherwise preserve the explicit stopped state.
- [ ] Record commands, hashes, resource totals, and limitations without claiming external review or general scientific novelty.
