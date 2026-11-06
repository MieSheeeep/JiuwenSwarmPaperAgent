# Evidence-linked claim and revision protocol

This offline workflow links writing and review responses to saved artifacts. It does not call a model, award a new review score, overwrite the submitted paper, or infer scientific novelty from code. The saved reviewer text is `submission/memory-20261016-review.txt`; its whole-file SHA-256 identifies the critique used in the response worklist. All ten weaknesses remain open until their stated evidence requirements receive human assessment.

Run from the repository root:

```powershell
python -m research.claim_revision --run-dir output/memory_live_20261016 --sections output/paper/reviewed_sections.json --output output/claim_revision_20261106
```

For the new run, set `--run-dir output/review_upgrade_20261106` and choose a fresh output directory. An absent summary produces an explicit missing-evidence state and no measurements; no historical score or run is silently substituted. An incomplete run can still produce a ledger for completed cells, but the ledger does not describe the grid as complete.

## Interfaces and evidence schema

`build_claim_ledger(run_dir, sections=None) -> dict` reads only the selected `summary.json`, the saved review, and a fixed list of public research/artifact files. It returns `claims`, `unsupported_claims`, `chapter_plan`, `review_response_matrix`, reference whitelist, missing evidence and validation scope. A chapter plan connects each relevant review weakness to concrete revision actions and evidence still needed. Related implementation artifacts are linked by hash but never count as empirical closure. Historical and external results remain distinct through the selected run and each condition's `kind`, split, policy, packer, model, reader, task seed, repeat and budget. External exact match is labeled a normalized proxy, never an official benchmark judge score.

`make_evidence_ref(path, locator, kind='metric')` returns a typed reference:

```json
{"kind":"metric","source":"/absolute/run/summary.json","source_hash":"sha256-of-exact-bytes","locator":"/methods/0/exact_correct"}
```

Kinds are `metric`, `artifact`, `review` and `source`. Metric locators are nonempty RFC 6901 JSON pointers. Whole-file artifact references use an empty locator. References are resolved against freshly read bytes on every validation; altered sources fail their hash check. Configuration, secret, credential, environment and token filename components are rejected. Only use public experiment summaries and sanitized artifacts as evidence.

`validate_claim(claim, evidence) -> list[str]` checks a deliberately strict syntax. Each claim has `id`, `type` (`measured`, `qualitative`, `limitation`), `text`, and `evidence_refs`. A measured claim also has numeric `value` and `operation`: `identity` takes one metric locator; `ratio` and `difference` take two in order; `sum` takes one or more. Operands must be finite numbers. Values are recomputed with tight floating-point tolerance from the located fields, rather than trusting the summary's accuracy scalar. The builder emits exact accuracy, micro field accuracy and evidence recall only when their underlying count pairs exist. A stale or tampered accuracy scalar remains an unsupported claim. The summary may provide additional explicit `measured_claims` subject to the same rules.

Numbers belong in structured `value`/`condition` fields, not claim prose. Digits and percentages in prose fail validation, apart from recognized method identifiers and citation keys. Citations use `[temporal]` or grouped keys such as `[memgpt, amem]`; only the existing curated `research.memory_paper.REFERENCES` whitelist is accepted. Reviewer-suggested references are not automatically promoted. Strength/novelty/review-outcome phrases trigger human review. These checks certify neither literature entailment nor the semantic truth of free text. Qualitative prose can pass these mechanical checks without establishing factual correctness. The `evidence` argument is reserved; local references always resolve real files, never caller-supplied cached numbers.

`apply_revision(sections, updates, reason, evidence_refs) -> RevisionRecord` requires existing chapter names, a reason, valid evidence and mechanically acceptable replacement prose. The input mapping remains unchanged. The returned frozen dataclass includes deeply immutable sections, before/after changes, reason, evidence refs, UTC time and a SHA-256 record identity. Each changed chapter retains its exact evidence and reason. Numbers should be rendered separately from the measured ledger, rather than pasted into prose. A human must assess whether cited evidence actually supports each wording change before publication.

## Outputs and limits

The CLI writes English `claim_ledger.json`, `chapter_plan.json` and `reviewer_response.md`. The response is a worklist with current open status, proposed action, evidence requirements and hashed artifacts for each weakness: limited novelty, small synthetic evaluation, semantic baseline, external benchmark, multiple models/repeats, packer heuristic, conflict-reader tie, recent/full errors, proxy/billing distinction and interface portability. The historical review score is deliberately null; acceptance and reviewer satisfaction are never predicted.

The current generated output uses the original saved summary as a clearly identified historical evidence example. It does not imply that new experiments are complete. Source hashes identify the saved summary; they do not independently certify its upstream measurements. Original-run analysis and provenance checks remain responsible for recomputing those measurements from task/call ledgers. Claim validation recomputes reported ratios from summary counts, then flags unsupported prose separately. Tests cover number/hash tampering, stale summary ratios, citation rejection, unsupported novelty, absent-run isolation, condition dimensions and immutable revision traceability.
