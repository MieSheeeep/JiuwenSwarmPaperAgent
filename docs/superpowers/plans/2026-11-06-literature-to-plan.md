# Literature-to-plan implementation plan

Goal: implement the user-approved research front end and connect supported designs to existing execution.

Architecture: independent source acquisition, validated stage schemas, and a bounded CLI controller; ModelGateway remains the only model transport. Local Markdown skills are versioned inputs. Existing experiment code and historical outputs remain untouched except an opt-in handoff argument.

- [x] Write failing tests for official feed parsing, source/quote checks, unsupported novelty assertions, complete experiment protocols, artifact integrity and handoff compatibility.
- [x] Add research/literature.py for cached official arXiv search, bounded HTML full-text reading and explicit abstract-only fallback. Record failures and hashes.
- [x] Add research/skills/{literature_review,question_formulation,experiment_design}.md and research/discovery.py for three bounded model stages, closest-work search, durable artifacts, readable report and resume checks.
- [x] Add opt-in research.orchestrator --discovery-dir: validate that the designed protocol exactly matches the registered structured-memory-v1 experiment, then preserve the actual ResearchBrief/ExperimentPlan instead of substituting hardcoded research.
- [x] Add a read-only workbench discovery endpoint and page using existing UI conventions. No browser action starts paid experiments.
- [x] Run targeted and regression tests, build frontend, exercise an official-source + live-model demonstration within the frozen 60k / three-call ceiling, inspect outputs and document limitations.

Tests run via `.venv/Scripts/python.exe -m unittest discover -s tests -p test_discovery*.py -v`. Full regression uses unittest discovery; frontend uses npm run build. Each task is executed inline, preserving other uncommitted work.

Implementation evidence: 18 focused tests pass; initial full regression passed 205 tests before the final added checks. Three real model calls used 34,531 actual tokens. The third response was revalidated offline after correcting the accepted closest-work source set. A generated plan is implementation-required, so no new experiment was executed. Frontend build and real-browser desktop/390px/320px checks pass. Final full regression is recorded in docs/literature_to_plan.md.

Final regression: 211 tests passed after all changes. No new scientific performance claim or review score was produced.
