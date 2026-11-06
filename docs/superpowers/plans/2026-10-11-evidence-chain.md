# Evidence Chain Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline with the user's execution authorization. Track tasks below; preserve existing baseline files and user changes.

**Goal:** Turn the saved baseline into a hashed run artifact, independently checked evidence, and an offline manuscript with machine-verifiable claim links.

**Architecture:** A standard-library research package validates raw results against dataset labels and API logs. Immutable JSON artifacts carry parent references; a deterministic writer inserts measured figures as text, and a reviewer checks claim values against the evidence. A CLI resumes only when input fingerprints and output integrity agree.

**Tech Stack:** Python 3.12 standard library, unittest; existing baseline.dataset scoring, no model calls or new dependencies.

This milestone implements historical RunManifest, EvidenceBundle, ManuscriptBundle and ReviewDecision, plus their local storage. ResearchBrief, ExperimentPlan, live gateway, experiment generation and the new memory mechanism remain later milestones in the approved design.

### Task 1: Integrity and evidence

Files: research/contracts.py, research/artifacts.py, research/evidence.py; tests/test_research_chain.py.

- [x] Add tests for dataset digest mismatch, missing/duplicate task-policy pairs, incorrect saved score, cross-task call association and missing usage.
- [x] Run `.venv/Scripts/python -m unittest discover -s tests -p test_research_chain.py -v`; observe missing research implementation.
- [x] Implement canonical JSON digest, artifact validation and atomic persistence; import dataset/manifest/results/calls, independently recompute scores and method metrics.
- [x] Verify tests pass. Importer's public signature: `import_baseline(source: Path) -> tuple[dict, dict]` (run artifact, evidence artifact). Errors are ValueError with actionable messages.

### Task 2: Manuscript and checker

Files: research/writer.py, research/reviewer.py; same test file.

- [x] Add a corruption test: alter a claim value and its rendered text together; checker must still reject based on evidence.
- [x] Add an unlinked numeric prose test; checker must reject a manuscript section not produced from registered claims.
- [x] Implement `build_manuscript(evidence)` and `review_manuscript(manuscript, evidence)`. Generated manuscript explicitly labels historical synthetic pilot and uses measured counts, accuracy, all-call usage. References and arbitrary old prose are not silently imported as verified evidence.
- [x] Verify clean manuscript passes and edited manuscripts fail. Output is Markdown with statement-to-metric links, not a new scientific contribution claim.

### Task 3: Resumable offline CLI

Files: research/pipeline.py, research/__main__.py, research/README.md; same test file.

- [x] Add tests: unchanged input resumes without rewriting artifacts; changed source invalidates cache; edited output forces rebuild; invalid source records failed stage rather than using stale success.
- [x] Implement `run_pipeline(source, output)` and `python -m research import-baseline --source output/baseline --output output/research_v2`. A pipeline state fingerprint covers source bytes and local implementation bytes. Output bundle includes run, evidence, manuscript, review, paper.md and state.json.
- [x] Run full `unittest discover -s tests -v`, execute CLI on the actual saved run, then execute again to verify resume. Verify source files are untouched and raw-file hashes match evidence.
- [x] Document reproduction, outputs, precise check coverage and remaining limitations. Mark completed plan steps after fresh verification; no paid inference in this milestone.
