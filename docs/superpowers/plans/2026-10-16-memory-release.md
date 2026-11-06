# Versioned Memory Research Release Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development for isolated implementation tasks, then independent spec and code review. Preserve pre-existing edits in upstream and baseline. User has approved docs/research_system_v2_design.md and requested completion.

**Goal:** Ship a reproducible, bounded research release with a JiuwenSwarm memory feature, matched-budget comparisons/ablations, evidence-bound manuscript, resource ledger and contribution patch.

**Architecture:** Structured fact records are an explicit input assumption, not an oracle extraction result. Selection runs in an opt-in openJiuwen Rail. Experiment plans freeze dev/test seeds and selection mechanisms before paid evaluation. All model calls pass through one durable, bounded gateway. Model prose cannot alter measured tables; external evaluation remains separate from internal checks.

**Tech Stack:** Python 3.12, standard library memory/benchmark modules; installed openJiuwen ReActAgent/Model via existing private model config; existing tiktoken proxy and LaTeX template. No copied third-party source.

## Shared interface frozen before implementation

Record fields: id:str, entity:str, attribute:str, value:JSON scalar, valid_at:int, observed_at:int, operation:'set'|'delete'. IDs unique. Query: entity:str, attributes:list[str], as_of:int, known_at:int. A fact is visible when both valid_at<=as_of and observed_at<=known_at. For each attribute use maximal valid_at; equal valid_at with different values or set/delete is unresolved and should yield null. Delete also yields null. Equal values from distinct IDs may be redundant evidence. Generated records are one valid source format; no claim of free-text extraction.

`select_records(records, query, policy, budget, count_tokens)` returns text:str (JSONL records), record_ids:list[str], proxy_tokens:int; may add conflicts metadata. Policies: full, recent (contiguous suffix), lexical (token overlap including query terms), bm25 (real BM25 ranking), versioned, no_time (ablation ignores valid_at cutoff/order but still obeys observed cutoff), no_conflict (ablation resolves equal-valid-time conflict by observed order). All bounded policies count the joined serialized record text with the same supplied counter. Full is an unbounded reference. No gold, hidden oracle identifiers or inferred final answers in selector.

### Task 1: Framework memory extension (isolated owner)

- [x] Add failing tests for late observation of old facts, historical cutoff, known-at cutoff, same-time conflicts, tombstones, partial updates, tight budget and save/load.
- [x] Implement upstream/jiuwenswarm/agents/harness/common/versioned_memory.py and rails/versioned_memory_rail.py; standalone stdlib module exports VersionedMemoryStore and select_records. Add README/doc and root tests/test_versioned_memory.py. Export new Rail without changing existing baseline behavior.
- [x] Verify with offline tests and later a real ReActAgent call; no paid calls in this task. Keep original history and provenance, never fabricate answer evidence.

### Task 2: Dataset, scoring and analysis (isolated owner)

- [x] Implement research/memory_dataset.py and research/memory_analysis.py, plus tests/test_memory_dataset.py. Deterministic six families: static, late-arriving stale facts, historical query, conflict, deletion/no-answer, paraphrased question with distractors. Split seeds disjoint and no heldout tuning.
- [x] Export generate_tasks(n_per_family=2, seeds=(...), split='test') -> list[dict]. Task keys: id, split, seed, family, records, query, question, gold (attribute->value|null), gold_evidence (attribute->list[record IDs]), stale_values. Gold computed by a separate reference oracle, not importing the selector.
- [x] Export score_memory_answer(text,task,selected_ids=()) -> exact, field_accuracy, stale_fields, supported_fields, nonnull_fields, refusal_correct, evidence_recall. Answers requested as plain attribute->value JSON. Metrics clearly distinguish evidence available in context from model-provided citations.
- [x] Analyze saved task-policy-budget results/calls offline with paired comparisons, descriptive intervals and failure counts; do not infer significance or use model self-scores.

### Task 3: Bounded runtime, plan and orchestrator (primary owner)

- [x] Add failing budget tests; research/model_gateway.py records reservations before invoking, actual usage after responses, unknown spend blocks continuation. No SDK retries hidden from ledger; explicit retry at most once and only when pre-response failure is known not billed, otherwise stop.
- [x] research/memory_run.py runs a fixed grid on fresh ReActAgents with the new source Rail; model credentials resolved by existing config, not printed/saved. Selection evaluated offline first; paid grid awaits the user's token cap. Save plan, dataset and code hashes before calls, results atomically, failures and provider usage durably. Recovered calls reuse exact invocation fingerprints, never double-call after postprocessing failure.
- [x] research/orchestrator.py writes ResearchBrief and ExperimentPlan, coordinates run/analyze/write/check; execution config explicitly includes token cap, calls cap and wall clock. No arbitrary code generation/execution.

### Task 4: Paper and delivery

- [x] research/memory_paper.py uses evidence first: methods/results before introduction/abstract. Save original model prose, reviewed prose, references and evidence snapshots; measured tables and resources inserted programmatically. Numeric prose and references checked; one bounded revision for unsupported claims, otherwise omit free prose and use transparent fallback.
- [x] Generate Markdown and ICLR-template LaTeX/PDF; verify compilation and inspect PDF. Produce resource report for experiment plus all write/review calls, patch including new framework files, design/module docs and deterministic reproduction commands. Respect existing submission format but do not upload/claim official submission automatically.
- [x] Independently review spec compliance and code quality; full regression suite, negative tests, actual run/resume/reanalysis and artifact consistency. Record external Stanford/paper-agent scores as pending until those services actually run; never label local checks as official scores.

## Completion limits

Finite implementation/research release is the deliverable. Budget exhaustion, unavailable credentials, API/provider errors, external service authentication or unavailable official-site access are explicit recorded terminal conditions, not fabricated successful assessments. Source patch and local package can be prepared regardless of external publishing availability. No claim of scientific novelty without evidence against closest methods; versioned/bitemporal state is established prior art.

2026-10-16 release update: Stanford external review returned 4.5/10 for the exact frozen PDF; raw review archived. Separate paper-agent score and competition upload remain pending. No extra paid experiments were started after this review.
