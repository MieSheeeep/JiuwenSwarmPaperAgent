# Research Workbench Implementation Plan

**Goal:** Deliver the approved Chinese local workbench with English academic artifacts.

**Architecture:** React reads a read-only Python API; Python serves the production bundle and explicit artifact downloads on loopback. No paid jobs or arbitrary path access.

**Tech Stack:** React, TypeScript, Vite, lucide-react; Python standard library and unittest.

## Task 1: Read-only data service

- [x] Write `tests/test_workbench.py`: assert current-run discovery, missing-data reporting, exact usage accounting, and HTTP traversal/secret-file rejection. Run `.venv/Scripts/python -m unittest discover -s tests -p test_workbench.py -v` before implementation; expect missing module.
- [x] Implement `workbench/data.py` with `Repository(root).runs()`, `overview(run_id)`, `cases(run_id)`, `artifacts(run_id)`, `artifact_path(run_id, artifact_id)`. Read only registered local manifests and allowlisted artifacts. Return numeric missing values as null.
- [x] Implement `workbench/server.py`: GET `/api/runs`, `/api/runs/{id}`, `/api/runs/{id}/cases`, `/api/runs/{id}/files/{artifact}`; static production assets; structured 404/503 errors. Bind 127.0.0.1, reject unexpected Host and Origin. Run the above tests until passing.

## Task 2: Workbench interface

- [x] Create `frontend/package.json`, Vite/TypeScript config, index, React entry and API types. `npm install`; commit only dependency lock, not node_modules.
- [x] Implement shared shell and overview, experiment table/detail dialog, paper/review, resources/downloads. Filters operate on actual API results; use browser URL hash for navigable pages. Use real SVG bars, accessible form labels, empty/loading/error states, responsive layout and reduced-motion support.
- [x] Run `npm run build` for TypeScript and Vite production validation. Serve production with `.venv/Scripts/python -m workbench.server`.

## Task 3: Verification and delivery

- [x] Verify actual API totals and PDF byte identity, file download, no secret access, responsive rendering and navigation/filter/detail behavior in browser. Fix any failures before completion.
- [x] Add startup and development instructions to `frontend/README.md` and root README. Provide `scripts/start_workbench.ps1` for foreground startup. Run regression tests and `git diff --check`; report tested results and local URL.

## Verification record — 2026-11-06

- Production TypeScript/Vite build passed.
- Full Python regression: 77 tests passed, including 8 workbench tests.
- Edge browser: 4 end-to-end tests passed (actual artifacts, filters/detail/download, mobile/keyboard, error/empty states, missing-results retry).
- Independent code review: three P2 issues fixed with regression checks; follow-up found no remaining P1/P2.
- Both direct server and one-command PowerShell startup responded. The primary server remains on 127.0.0.1:8765; the secondary startup smoke-test server was stopped.
- Original reviewed PDF hash unchanged: a959d2acf3544dbb5ef4df0c16ac0eeb2210e98c0ceb831183c5f4bdf9ad8903. Actual ledger unchanged at 369 calls and 240721 tokens; this feature made no model calls.
- git diff --check passed. Existing research working files retained; no merge, publication or competition upload performed.
