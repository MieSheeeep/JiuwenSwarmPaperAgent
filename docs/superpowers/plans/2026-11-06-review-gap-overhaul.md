# Review-gap overhaul

User explicitly requested a comprehensive implementation and empirical attempt addressing all review weaknesses, rather than another small isolated experiment. This extends the approved workbench/research architecture; original submitted outputs remain immutable.

## Deliverables

- [x] Registered semantic dense and BM25+dense hybrid retrieval, recorded local embedding model identity, latency and cost; current and alternative atomic-group packers with explicit objectives and actual tokenizer rechecks. Independent selectors never see gold labels.
- [x] Official-source external benchmark ingestion and protocol: cleaned LongMemEval, pinned dataset checksum, deterministic stratification, original free-text interface, evidence recall and answer evaluation with judge provenance. No fabricated bitemporal metadata or official-comparable score.
- [x] Fresh multi-seed controlled tasks, expanded packing stress cases, repeat/model dimensions, baseline/conflict-aware/reflection readers, common context/output budgets, durable request accounting, resume validation and complete planned-grid status. Retain old frozen modules/hashes.
- [x] Attempt bounded live experiments using configured model(s), model catalogue discovery and the user-approved shared 3,000,000-token ceiling for this new round, including experiment answers, judges, revisions and writing. The earlier 300,000-token draft was superseded by the user's explicit selection. No unbounded calls; unknown spend halts. Distinguish CPU-only full retrieval analysis from paid answer subset and model repetitions.
- [x] Evidence-linked claims, chapter-level writing plans, review-response tracking and revision suggestions; references verified against curated primary sources. No novelty claim granted by code integration.
- [x] Workbench overview of each review gap, implementations, actual measurements, pending constraints and linked reports. Export fresh report/paper only when supported; old scores never inherited.
- [x] Independent tests/review, regression/build/browser verification, resource/portability documentation and actual framework contribution patch update if upstream source is changed.

## Ownership

Retrieval task owns research/advanced_retrieval.py, tests/test_advanced_retrieval.py, optional requirements-research-upgrade.txt and docs/retrieval_upgrade.md. Benchmark task owns research/external_benchmark.py, tests/test_external_benchmark.py, sources/external_benchmarks/ ignored downloads and docs/external_benchmark_protocol.md. Evidence-writing task owns research/claim_revision.py, tests/test_claim_revision.py and docs/claim_revision_protocol.md. Root integrates a separate research/review_upgrade.py runner and analysis, workbench APIs/UI and verification. Core six previously frozen research/framework files are left unchanged so old results remain independently recomputable.

## Evidence rules

Implemented mechanisms do not demonstrate novelty, significance, external validity or higher review score by themselves. Backbones must be actually available/configured; repeated calls are not independent model seeds when the provider exposes no sampling seed. Budget/model/data/code identity freezes precede paid calls. Synthetic and external metrics are separated. Unavailable/unrun/failed/unknown conditions remain visible. Review-suggested references are treated as unverified until checked at primary sources.

## Completion record

All registered answer conditions and adapted judgments completed. See docs/research_upgrade_release_20261106.md for evidence, negative findings and remaining limitations. Historical unknown provider usage remains null under explicit conservative holds; new external review is submitted, not scored yet. Implementation/checklist completion does not mean reviewer acceptance, originality certification, official benchmark equivalence, or competition upload.
