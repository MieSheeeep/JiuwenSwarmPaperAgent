# Original LongMemEval external benchmark protocol

This adapter uses the **original 500-question LongMemEval_S cleaned release**. It is an external corpus, distinct from this repository's synthetic memory tasks and from LongMemEval-V2. The [official repository](https://github.com/xiaowu0162/LongMemEval) identifies the [cleaned Hugging Face dataset](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned), its September 2025 cleaning, six question types, and the `_abs` abstention suffix. Its official answer evaluation calls a semantic model judge. The local implementation does not make model calls.

## Pinned source and reproducibility

The actual source is `sources/external_benchmarks/longmemeval_s_cleaned.json`, 277,383,467 bytes, downloaded from [HF revision 98d7416c24c778c2fee6e6f3006e7a073259d48f](https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned/tree/98d7416c24c778c2fee6e6f3006e7a073259d48f). SHA256:

```
d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442
```

`source_manifest.json` records the resolved download URL, revision, actual checksum, byte count, instance count and retrieval timestamp. `huggingface_metadata.json` preserves the unauthenticated HF API response, including the MIT license tag. Downloading this public file needs no credentials. Raw data and generated copies are local cache artifacts; no source dataset content is generated or substituted.

```python
from research.external_benchmark import prepare_external
prepare_external('outputs/external_full500',
                 'sources/external_benchmarks/longmemeval_s_cleaned.json',
                 n=500, seed=20261106)
```

This writes `tasks.json`, `manifest.json`, and full-source `corpus_statistics.json`. The manifest includes source and task-file SHA256, selected IDs, seed, and selection rule. Reusing the directory verifies all three files byte for byte; a changed source, selection, missing file, or altered artifact raises `ValueError`. A new experimental freeze must use a new directory. This is application-enforced immutability, not an operating-system write lock.

## Adapter interfaces and leakage boundary

`load_longmemeval(path) -> list[dict]` returns tasks with `id`, `family`, `question`, string `gold`, `question_date`, `sessions` (each exactly `id`, `date`, `text`), `gold_session_ids`, and `source_question_type`. Family is `abstention` for `_abs` IDs; otherwise it is the original question type. The source's 32 integer answers become decimal strings. Source session order and original date strings are preserved. Thirteen tasks have a repeated source session ID: both occurrences are retained, so an ID selection includes both. Retrieval can assign separate occurrence/chunk identifiers while retaining source session IDs for recall.

Only turn role and content become session text. `has_answer`, gold answers, answer-session annotations and question family are never appended to retrieval text or model messages. Natural conversation text can of course contain the answer itself; that is the benchmark evidence. Frozen task files contain gold for scoring and must not be serialized wholesale into model input.

`build_external_messages(task, selected_session_ids=None)` returns system/user messages with selected source session ID/date headers, role-prefixed text, question date, and question. `None` includes all sessions; `[]` includes no sessions. Unknown IDs raise. Dates are source conversation dates, not invented fact-validity intervals. Whole-session messages can exceed model context limits; a retrieval runner must pack chunks under its declared budget and preserve source headers. The adapter does not silently truncate or claim a model-token budget.

`stratified_sample(tasks, n, seed)` uses proportional largest-remainder allocation across families and deterministic seeded shuffles of sorted IDs. Small samples can omit small strata; report realized counts. Input permutation does not change the sample. `disjoint_dev_test(tasks, n_dev, n_test, seed=20261106)` samples dev first and test proportionally from the remaining IDs, returning `(dev, test)`. These are local research splits, not official train/test partitions. Freeze both ID sets before tuning; the original benchmark is public and cannot establish absence of training contamination.

`evaluate_answer(gold, response)` returns `exact_normalized`, `proxy_token_f1`, and `needs_semantic_judge=True`. Normalization case-folds, strips ASCII punctuation and English articles, and collapses whitespace. F1 is multiset whitespace-token overlap. These are **local lexical proxies, never official LongMemEval answer accuracy**. They do not establish semantic correctness, particularly for abstention, preferences, paraphrases, dates or numerical equivalence. No official judge score exists until the separately authorized official semantic evaluation is actually run.

`evidence_recall(selected_session_ids, gold_session_ids)` returns unique-source-session recall; duplicate selected IDs do not improve it. An empty gold set returns `None` (undefined denominator). Retain original session IDs when retrieving chunks. This measures selected evidence sessions, not answer correctness or turn-level coverage. The source has 1–6 annotated evidence sessions even for abstention tasks; abstention alone does not mean empty annotated evidence.

`corpus_statistics(tasks)` computes instance/family/source-type counts and min/median/mean/nearest-rank p95/max/total lengths in sessions, whitespace words and Unicode characters. Lengths include role prefixes, exclude source headers, and are not tokenizer counts. `sha256_file(path)` streams the file checksum.

## Actual full500 offline audit

The preserved machine-readable report is `sources/external_benchmarks/full500_statistics.json`. Across 500 tasks there are **23,867 session occurrences**, **39,460,075 whitespace words**, and **246,973,909 Unicode characters** of role-prefixed history text. Session count per task is 38–62 (median 48; mean 47.734). History words per task range from 73,436 to 82,731 (median 79,088.5; p95 81,094). The corpus has 948 annotated evidence-session references (median 2 per task).

| Local stratum | Tasks |
| --- | ---: |
| Abstention | 30 |
| Knowledge update | 72 |
| Multi-session | 121 |
| Single-session assistant | 56 |
| Single-session preference | 30 |
| Single-session user | 64 |
| Temporal reasoning | 127 |

Original source question-type counts, before separating abstention: knowledge-update 78, multi-session 133, single-session-assistant 56, single-session-preference 30, single-session-user 70, temporal-reasoning 133. The 13 repeated source IDs are reported explicitly rather than removed. No retrieval rankings, embeddings, answer generation, API calls to model providers, or semantic judging were used to produce this audit.

Validation: `python -m unittest discover -s tests -p test_external_benchmark.py` checks schema, numeric gold handling, missing/malformed data, duplicate occurrence preservation, annotation isolation, deterministic proportional sampling, disjoint splits, checksums, freeze refusal, lexical proxies and evidence recall.
