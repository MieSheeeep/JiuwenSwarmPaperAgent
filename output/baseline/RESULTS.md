# Baseline results

Model: `deepseek-flash`. Tasks: 24; deterministic seed: 20261008.

| Method | Correct | Exact accuracy | API tokens including summary | Mean seconds |
|---|---:|---:|---:|---:|
| full | 24/24 | 100.0% | 74,665 | 0.71 |
| recent | 6/24 | 25.0% | 15,283 | 0.72 |
| retrieve | 24/24 | 100.0% | 4,212 | 0.68 |
| retrieve_summary | 24/24 | 100.0% | 7,608 | 1.43 |

These are actual API-backed results, not a competition score.
The full-history method is an unbounded reference. Recent and retrieval methods share a 512 cl100k_base-token history budget; this tokenizer is a proxy, not DeepSeek billing.
Retrieval explicitly matches the project identifier in the question and retains updates in chronological order. This easy lexical structure favors retrieval; it is not an evaluation of semantic retrieval.
Summary performs one extra model call on retrieved records; all its input/output tokens are included. The returned summary is capped at 256 proxy tokens.
One run per case, one model, synthetic data, no real tool execution, no held-out generalization test, and no assertion of new scientific novelty.
