# Selected SPT and period workbook Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement all ten requested downloader revisions with scoped exports, explicit user selection/overwrite consent, safe PDF handling, and verifiable Windows behavior.

**Architecture:** Extend existing exporter, browser capture, and desktop worker flows. Use pure workbook layout helpers for both export and verification. Keep new interactive requests job-bound, preserve origin/provenance checks and cancellation, and never import browser/Excel libraries into the GUI process.

**Tech Stack:** Synced to main e99464a: production CPython 3.11.17/GIL, uv 0.12.22, stdlib Tkinter, Playwright 1.63.0, openpyxl 3.1.5, pytest 9.1.1 and hashed locks. Python 3.14.8 remains the repository candidate profile. No new production dependency.

**Spec:** docs/superpowers/specs/2026-10-12-period-selection-layout-design.md

**Publication slice:** At the user's request, create a PR from synced main e99464a containing Task1 only. Tasks2–5 remain pending. RED selection/overwrite tests and temporary reviewer probes stay local and are not part of the proposed PR tree. Production validation uses isolated CPython3.11.17 and hashed locks/test.txt, not the older application venv.

## Global Constraints

- Exact NPWP/source identifiers, source values and duplicate rows; clearly synthetic tests only.
- Folders: `SPT Masa 21`, `SPT Masa Unifikasi`, `SPT Masa PPN`; one workbook per source period, Normal/Pembetulan in separate sheets.
- Corporate forms become individual sheets; only inspected existing financial-statement PDFs may be downloaded.
- Exact strings: `jalankan proses sedot di background`; `Hasil Sedot berada di folder Downloads Windows`; `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`.
- No unsafe auth relaxation, guessed remote actions, private data commits, default overwrite, or UI-thread browser work.
- No commit/push until separately approved.

## Review Focus

- Two raw periods or tax names that sanitize to the same Windows path must fail before writing.
- Normal/amendment forms with long identical captions must retain unique Excel names and exact resume links.
- Invalid, duplicate, stale or cross-job selection replies must never capture unintended records.
- A locked/replaced/symlinked destination during consent or publication must preserve previous results/recovery.
- HTML, foreign-origin redirects, expired sessions and cancelled PDF downloads must not be presented as valid PDFs or COMPLETE.

---

### Task 1: Workbook layout and analysis-friendly forms

**Files:** coretax_exporter.py; coretax.py; tests/test_split_output.py; tests/test_exporter.py; new tests/test_period_layout.py.

**Interfaces:** Add `workbook_groups(run) -> dict[str, list[dict]]` for relative XLSX paths and `record_sheet_titles(ordinal, record) -> list[str]` for per-form detail sheets. `detail_sheet_title(ordinal, record)` returns the first target. Preserve `export_split_workbooks(run, folder) -> dict[str, Path]`; verifier consumes the same layout helpers without trusting the generated files.

- [x] Write/run failing tests for January/February/PPN separate files, same-period amendments, corporate Induk/L1-D sheets, Windows collisions, raw text/duplicates, tables and links.
- [x] Implement helpers and update exporter/verification/nested staging scope; keep workbook field/table data unmerged and filterable, with validated numeric analysis columns where source formatting is supported.
- [x] Run exporter/output safety tests; all new cases pass and retained scope/rollback checks still hold.

### Task 2: Selected-only capture and overwrite dialogue

**Files:** spt_desktop/app.py; controller.py; worker.py; events.py; output.py; coretax.py; new tests/test_desktop_selection.py; test_desktop_output.py; test_desktop_worker.py.

**Interfaces:** Worker inventory-ready and overwrite-required requests carry a job ID and private job-local JSON payload; GUI reads only the owned job payload. Controller sends job-bound confirmed record IDs or an overwrite decision. Publisher keeps `publish_workbooks(...)` and gains explicit overwrite consent; default remains deny.

- [ ] Write/run failing tests for selected-only details, empty choice, wrong/duplicate IDs, cross-job replies, stop while waiting, decline/approve overwrite and untouched nonselected files.
- [ ] Add bounded request/reply handling and a main-thread selection dialogue; filter inventory before detail capture and record selection scope. Stage verified selected files; validate existing workbook scope before replacement and retain rollback.
- [ ] Run desktop lifecycle, worker, selection, output and optimized-mode safety suites.

### Task 3: Existing financial-statement PDF capture

**Files:** new coretax_attachments.py; coretax_browser.py; exporter link rendering; worker output manifest; spt_desktop/runtime.py explicit WORKER_FILES; new tests/test_financial_attachments.py.

**Interfaces:** `download_financial_attachments(page, record, folder, check_cancel=None) -> list[dict]` stores validated local PDFs and returns label/relative_path/status/bytes/hash metadata. Browser integrates before closing the inspected corporate detail page. The publisher includes only declared validated PDFs alongside XLSX outputs.

- [ ] Write/run failing local synthetic browser/HTTP tests for observed hrefs, unavailable controls, foreign origin/redirect/HTML, size cap, cancellation and output paths.
- [ ] Implement GET-only validated existing-link downloads; never infer remote URLs or click generation/submit controls. Preserve PARTIAL for unsupported available controls/failures.
- [ ] Verify PDF bytes/hash and relative workbook links and update runtime resource allowlist/build tests.

### Task 4: Authentication recognition and UI copy

**Files:** spt_desktop/auth.py; app.py; spt_gui.py; build_desktop.py; authentication/branding/gui tests.

**Interfaces:** Preserve `_login_fields`, control binding, exact origins and saved-credential ownership. Add sanitized reason diagnostics and condition-based readiness only where evidence supports them; no credential data in diagnostics.

- [ ] Write/run failing synthetic fixtures for asynchronous form readiness and known supported captions/fields while retaining rejection of challenges/extra fields/unsafe actions.
- [ ] Apply narrow recognition fix supported by evidence and exact approved UI strings; update source/frozen self-test assertions.
- [ ] Run complete auth/binding/cancellation and GUI suites. Keep live portal recognition explicitly unverified until inspected.

### Task 5: Acceptance, independent review and artifact

**Files:** AGENTS.md output contract; README.md; test expectations; build artifact outside repo; acceptance report.

- [ ] Reconcile all ten user requirements to executed tests; update old output documentation only within the new approved contract.
- [ ] Run full pytest with unique Hermes scratch basetemp; inspect synthetic XLSX files with excel-workbench and verify every link/file count.
- [ ] Obtain independent code/security review and fix high-priority findings with regression tests.
- [ ] Build Windows executable outside repo, run source and frozen GUI self-tests, verify real artifact checksum and privacy-safe resources; deliver MEDIA path and live-test limitations.
- [ ] Present diff and proposed scoped conventional commit messages only if commit/push is requested; obtain confirmation before executing.
