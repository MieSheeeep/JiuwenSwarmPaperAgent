# Reviewer-suggested related work: primary-source audit

Checked 6 November 2026. The eight labels in `submission/memory-20261016-review.txt:43-60` resolve to seven distinct primary-source papers. All eight identities are verified at the bibliographic and abstract level; no label remains unverified or ambiguous after matching the review's descriptions. This does not independently verify the authors' performance claims, establish priority, or complete an empirical comparison. The machine-readable companion is `sources/review_related_work_20261106.json`. No reviewer framework was implemented or executed in this audit.

## Manuscript-ready related-work paragraphs

Conflict-aware RAG includes explicit mechanisms beyond retaining contradictory records. EvidentialRAG converts claim support into probabilistic evidence and preserves unresolved disagreement as uncertainty that controls answering and abstention. ArbGraph extracts atomic claims and propagates credibility through a graph of support and contradiction before generation. These mechanisms address evidence arbitration, whereas our structured selector exposes admissible records and preserves conflict groups under a context budget. Conflict-preserving packing alone therefore does not establish calibrated uncertainty, successful arbitration, or improved answer accuracy. [Hossain et al., 2026](https://arxiv.org/abs/2607.10491); [Niu et al., 2026](https://arxiv.org/abs/2604.18362).

Wang et al. introduce both RAMDocs, a dataset combining ambiguity, misinformation and noise, and MADAM-RAG, a method that uses multi-agent debate and aggregation to handle conflicting retrieved evidence. RAMDocs is a benchmark resource rather than a separate paper or a temporal database. A local conflict-aware reader prompt should not be labeled a reproduction of MADAM-RAG. Evaluation on the authors' dataset and faithful implementation of their debate protocol remain distinct requirements; neither follows from our synthetic experiments. [Wang et al., 2025](https://arxiv.org/abs/2504.13079).

Memory orchestration also studies bounded context construction. MemFlow routes queries to specialized memory tiers and constructs tier-dependent evidence contexts, with optional validation and retry. Verifiable Memory learns a unified memory-operation policy with local and global verifier signals during training. GraphMemory, introduced in *Decoupling Memory from Context*, stores reusable strategies as a graph and retrieves relevant subgraphs under a bounded retrieval policy. These works motivate comparisons of context budgets, retrieval behavior and total operating cost. Our selector offers a narrower structured-record component; we have not reproduced these systems or established superiority over them. [Chen et al., 2026](https://arxiv.org/abs/2605.03312); [Sun et al., 2026](https://arxiv.org/abs/2608.03137); [Farhat et al., 2026](https://arxiv.org/abs/2610.02687).

EHR-RAG combines event- and time-aware hybrid retrieval with iterative retrieval and factual/counterfactual evidence paths for structured longitudinal clinical prediction. It provides a relevant example of temporal retrieval in another domain. Our valid-time and observation-time filtering could be investigated as a component within such pipelines, but the present evidence does not establish cross-domain or clinical effectiveness, and temporal awareness should not be equated with bitemporal semantics. [Cao et al., 2026](https://arxiv.org/abs/2601.21340).

The added dense baseline uses a pretrained sentence encoder from the MiniLM family. The foundational MiniLM paper describes self-attention distillation, while the actual encoder is the quantized ONNX export `Xenova/all-MiniLM-L6-v2`, pinned to revision `751bff37182d3f1213fa05d7196b954e230abad9`. Its model card identifies `sentence-transformers/all-MiniLM-L6-v2` as the source sentence encoder. The local hybrid combines dense and BM25 ranks through established reciprocal rank fusion (RRF), using equal weights and k=60. These are implemented retrieval components, not replications of the original training or evaluation studies. [Wang et al., 2020](https://arxiv.org/abs/2002.10957); [pinned ONNX model card](https://huggingface.co/Xenova/all-MiniLM-L6-v2/blob/751bff37182d3f1213fa05d7196b954e230abad9/README.md); [Cormack et al., 2009](https://doi.org/10.1145/1571941.1572114).

## Identity and comparison notes

| Reviewer label | Verified identity | Comparison boundary |
| --- | --- | --- |
| EvidentialRAG | Hossain, Shayoni and Mridha (2026), arXiv:2607.10491 | Evidential fusion and uncertainty routing; not implemented |
| ArbGraph | Niu, Wang, Ren, Fang and Zhao (2026), arXiv:2604.18362 | Claim graph and iterative arbitration; not implemented |
| MemFlow | Chen, Li and Wang (2026), arXiv:2605.03312 | Intent-driven memory orchestration; not implemented |
| Verifiable Memory | Sun, Wang, Li and Chen (2026), arXiv:2608.03137 | Learned memory policy, training-time verifiers; not implemented |
| GraphMemory | Farhat, Desmond and Kyrillidis (2026), arXiv:2610.02687 | Strategy graph and bounded subgraph retrieval; not implemented |
| RAMDocs | Wang, Prasad, Stengel-Eskin and Bansal (2025), arXiv:2504.13079 | Dataset; no completed local benchmark claimed |
| MADAM-RAG | Same paper as RAMDocs | Multi-agent generation method; not implemented |
| EHR-RAG | Cao, Chen and Guo (2026), arXiv:2601.21340 | Structured longitudinal clinical pipeline; not implemented |

MemFlow has unrelated namesakes in optical flow, video generation and systems memory. Here the review's explicit memory-orchestration description identifies the Chen et al. paper. GraphMemory is a system name inside the Farhat et al. paper, not the paper title; the graph-memory survey and G-Memory should not be silently substituted. RAMDocs and MADAM-RAG require one bibliographic reference, while retaining separate dataset/method discussion.

## Foundational component references and local evidence

MiniLM's exact reference is Wenhui Wang, Furu Wei, Li Dong, Hangbo Bao, Nan Yang and Ming Zhou (2020), *MiniLM: Deep Self-Attention Distillation for Task-Agnostic Compression of Pre-Trained Transformers*, arXiv:2002.10957, DOI `10.48550/arXiv.2002.10957`. The primary record verifies that identity; it does not identify our exact fine-tuned sentence-embedding weights. [Primary paper](https://arxiv.org/abs/2002.10957).

The sentence-transformers model card identifies `nreimers/MiniLM-L6-H384-uncased` as its pretrained base and describes contrastive sentence-pair fine-tuning. That base card describes a six-layer model retaining alternate layers from a twelve-layer MiniLM. The `v2` suffix in `all-MiniLM-L6-v2` should not be treated as proof that the distinct MiniLMv2 paper is its identity. [Sentence encoder card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2); [pretrained base card](https://huggingface.co/nreimers/MiniLM-L6-H384-uncased).

RRF's exact reference is Gordon V. Cormack, Charles L. A. Clarke and Stefan Buettcher (2009), *Reciprocal rank fusion outperforms condorcet and individual rank learning methods*, SIGIR 2009, pp. 758-759, DOI `10.1145/1571941.1572114`. The author-affiliated Google Research record confirms authors, venue, year and pages; publisher search metadata confirms the DOI. Direct ACM fetching returned HTTP 403. [Author-affiliated record](https://research.google/pubs/reciprocal-rank-fusion-outperforms-condorcet-and-individual-rank-learning-methods/); [publisher DOI](https://doi.org/10.1145/1571941.1572114).

Inspection of `research/advanced_retrieval.py` shows pinned model repository/revision/file hashes, CPU ONNX inference, attention-mask mean pooling, L2 normalization, a 256-token limit, and a hybrid branch summing `1/(60+rank)` for one-based ranks from BM25 and dense lists. The registry's two `implemented: true` entries refer only to those components. This source inspection did not run embeddings, generate answers, measure performance, or certify a prior experiment's model identity.

## Remaining evidence gaps

Source identities and appropriately scoped comparisons are now available. Empirical head-to-head results, faithful baseline implementations, RAMDocs ingestion/evaluation, uncertainty calibration, and cross-domain clinical transfer remain unestablished by this literature audit. No original manuscript reference list, frozen experiment file, or historical result was changed.
