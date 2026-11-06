# Independent retrieval upgrade

`research/advanced_retrieval.py` provides opt-in local pretrained dense retrieval,
BM25, equal-weight BM25+dense reciprocal rank fusion (RRF k=60), and atomic-group
packing. It imports the original frozen source module read-only for validation
and serialization; it does not alter previously reported experiments.

## Interface and reproduction

```python
from research.advanced_retrieval import DenseEncoder, rank_texts, select_records

# First installation only; subsequent construction is offline by default.
encoder = DenseEncoder(download=True, threads=4)
ranking = rank_texts(texts, question, method='hybrid', encoder=encoder)
result = select_records(records, query, policy='dense', budget=256,
                        count_tokens=count_tokens, encoder=encoder,
                        packer='rank_first')
```

`DenseEncoder.encode(list[str])` returns normalized 384-dimensional vectors.
`identity` records the model, immutable repository revision, SHA256 for every
downloaded file, runtime/version, CPU threads, pooling, maximum length, batch size,
truncation, download bytes, zero remote embedding calls and zero generation
tokens. Timings are separate mutable observations: `load_seconds`, cumulative
`encode_seconds`, and `encoded_text_count` for cache misses. Per-instance embeddings
are cached by SHA256 of UTF-8 text. The caller must reuse an encoder to benefit.

The pinned model is `Xenova/all-MiniLM-L6-v2` revision
`751bff37182d3f1213fa05d7196b954e230abad9`. Its quantized ONNX weight SHA256 is
`afdb6f1a0e45b715d0bb9b11772f032c399babd23bfc31fed1c170afc848bdb1`.
The ignored model directory is
`sources/model_cache/all-MiniLM-L6-v2/751bff37182d3f1213fa05d7196b954e230abad9/`;
`identity.json` captures complete file hashes and `smoke.json` captures an actual
local inference run. `requirements-research-upgrade.txt` pins the tested CPU
environment. PyTorch and fastembed are unnecessary: the implementation directly
uses ONNX Runtime and Hugging Face tokenizers. Missing files or checksum mismatch
raise `DenseUnavailable`; dense retrieval never silently becomes lexical.

Inference uses batches of 16, at most 4 intra-operation CPU threads, 1
inter-operation thread, attention-mask mean pooling and L2 normalization. Inputs
are truncated at 256 wordpiece tokens. Long free-text sessions therefore have
an explicit truncation limitation; chunking and aggregation would be a different
retrieval protocol. Quantization is also part of model identity.

`rank_texts` returns `(source_index, score)` pairs. Dense scores are cosine
similarities; BM25 uses k1=1.5, b=.75, distinct casefolded regex word query terms,
and positive Robertson IDF; hybrid scores sum `1/(60+rank)` from each full ranking.
All ties use source index. Its query is free text; structured `select_records`
uses only allowlisted entity, requested attributes and optional query.question.

## Packing objectives and limitations

`select_records` returns `text`, `record_ids`, `proxy_tokens`, `conflicts`, and
metadata. Policies are `bm25`, `dense`, `hybrid`, and `versioned`. Baselines rank
all serialized source records without temporal filtering and give each record
unit atomicity. No gold values, answer labels, annotated evidence, or generated
dataset family can enter ranking or utility. Extra record fields are stripped
using the frozen module's allowlist. Supplied queries must have the original
entity/attribute/integer cutoff schema.

The versioned policy preserves original bitemporal maximal-group semantics:
filter queried entity/attributes by valid_at <= as_of and observed_at <= known_at,
then keep all visible records at maximal valid_at per attribute. Different
values or set/delete operations at the same valid time remain one indivisible
group. `conflicts` reports all visible unresolved groups, including those omitted
for lack of space, matching the original interface. Deletion records stay raw.

| Packer | Deterministic objective/heuristic |
| --- | --- |
| `rank_first` | Greedily admit entire groups in input retrieval order, checking actual joined tokens after every candidate. Use for retrieval-quality arms. |
| `smaller_first` | Greedily admit standalone-smallest groups first, stable input-order ties. Current versioned baseline; unit utility represents attribute coverage. |
| `utility_dp` | Exact 0/1 dynamic program maximizing sum of declared nonnegative group utilities under the additive token surrogate below. |
| `diverse` | Sort groups by descending utility, then stable round-robin among attributes/aspects, checking actual joined tokens for each candidate. |

For baseline policies DP utilities are reciprocal retrieval ranks, never gold
relevance. Versioned utilities are one per latest attribute group. Therefore
`utility_dp` for versioned maximizes covered groups only under its surrogate.
Smaller-first on baseline policies deliberately orders by cost and is unsuitable
as the main measure of retrieval ranking quality.

For group cost `tokens(group.text) + tokens(newline)`, DP has capacity
`budget + tokens(newline)`. It maintains sparse exact-cost states and keeps the
earlier state on equal utility, then chooses the smallest cost among final
equal-utility states. It is independently compared against exhaustive subsets
of a tiny instance across 25 capacities in the unit suite.

Tokenizers are not additive: merging text around a separator can change BPE
boundaries. The implementation recounts the **complete joined text**, drops
whole final groups if necessary, and rechecks after restoring versioned source
order. Metadata explicitly reports objective before/after actual recheck,
additive surrogate cost, dropped groups, actual proxy tokens and
`actual_tokenizer_optimality_claim=false`. Exact DP surrogate optimality is not
actual-tokenizer optimality. Recheck dropping also need not optimize actual
utility. For arbitrary nonadditive tokenizers, even cost-greedy coverage is not
a global optimality guarantee. The context budget covers selected source text;
system/query/output tokens are separately the runner's responsibility.

## Measured smoke and tests

Actual CPU pretrained inference was performed on 2026-11-06, without model
generation or remote embedding services. For query “A doctor provided medical
care.” the physician/hospital sentence scored .807063, the mechanic/engine
sentence .346610, and the farmer/vegetables sentence .121418. Dense retrieved the
physician first while BM25 retrieved the mechanic sentence due to the term “a”.
RRF tied physician and mechanic, resolving to physician by source index. This
small smoke establishes a functioning pretrained path, not external validity
or an aggregate superiority claim. The saved run took about .029 seconds for
4 unique texts and .786 seconds to load the cached model on this machine;
latencies are machine-specific and exclude first download time (~26 seconds).

Run `.venv/Scripts/python.exe -m unittest tests.test_advanced_retrieval -v`.
Ten tests passed, including an actual pretrained synonym/cache smoke (skipped
only when weights are absent), exact RRF arithmetic, gold-field exclusion,
versioned temporal/conflict atomicity, explicit unavailable error, ranking-driven
admission, aspect diversity, exhaustive DP comparison and a deliberately
nonadditive tokenizer that forces an atomic actual-budget repair.

Primary sources: the [pinned ONNX model repository](https://huggingface.co/Xenova/all-MiniLM-L6-v2/tree/751bff37182d3f1213fa05d7196b954e230abad9),
[model usage and pooling example](https://huggingface.co/Xenova/all-MiniLM-L6-v2),
and [ONNX Runtime Python API](https://onnxruntime.ai/docs/api/python/api_summary.html).
The implementation claims engineering integration, not retrieval-method novelty.
