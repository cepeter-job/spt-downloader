# Automatic MPN and supplied resume template Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a verified negative-payment MPN companion to each full live SPT job and generate resume.xlsx using the operator's supplied presentation.

**Architecture:** A separate pure MPN adapter, owned Accounting browser collector and workbook renderer feed the existing CLI/desktop publication pipeline. Shared resume layout bindings keep physical proof and legacy readers consistent. Existing SPT observers, native admission, form templates and JSON/PDF custody remain independent.

**Tech Stack:** Existing pinned Python/Playwright/openpyxl, standard-library Decimal/JSON/ZIP/XML; Windows GitHub runner for all product execution.

**Spec:** `docs/superpowers/specs/2026-10-26-mpn-job-design.md` (approved 26 October).

## Global Constraints

- Product imports, fixtures, pytest, builds and EXE/self-test execution are GitHub-runner-only; local source/AST and package/hash inspection only.
- Only observed same-taxpayer Accounting `list`/`listdetail` UI POSTs are admitted. No guessed/replayed API POST, remote export, print, reconciliation or reference actions.
- Scope by the detail's validated literal tax period/year, and retain strictly negative Amount without changing signs, precision, identifiers or source order.
- DOM uses verified JSON only for identity/hidden metadata and exact numeric validation; unsupported/incomplete/rounded detail capture falls back as a whole detail.
- Stop wins; safety/identity contradictions are fatal; incomplete MPN makes a required full job PARTIAL without deleting verified SPT output.
- Keep raw MPN evidence private; publish MPN workbook only. Preserve SPT JSON publication and PDF consent/recovery.
- Preserve LICENSE and current main/preceding PR contracts; update AGENTS.md for shipped changes.

## Review Focus

1. Old summary coordinates must not accidentally validate the new template or another taxpayer; test both complete header maps and reject mixed layouts.
2. Out-of-year parents and zero-valued headers can own qualifying detail rows; inspect every unfiltered non-cancelled header and test cross-year allocation.
3. A superficially complete DOM display may round source decimals; compare all three monetary/rate columns to numeric lexemes and test fractional mismatch.
4. A late response or failed HTML/JSON page must never certify a new navigation/detail attempt; test request-object ownership and terminal failure before fallback.
5. Existing MPN workbooks and old SPT/JSON/PDF files must survive consent rejection, interrupted replacement and legacy export; test physical proof and rollback.

## Files and interfaces

- `coretax_mpn.py`: pure decoding, qualification, canonical rows, required-run declarations and byte-custody validation. No browser/openpyxl import.
- `coretax_mpn_browser.py`: owned UI navigation/observer, unfiltered inventory, whole-detail capture/fallback, durable private evidence and cancellation.
- `coretax_mpn_export.py`: MPN workbook writing/physical proof, filename and resume MPN link/status declaration.
- `coretax_resume_layout.py` and `resources/resume_format.xlsx`: sanitized reference layout, strict old/new scope bindings and administration-sheet presentation.
- `coretax.py`, `coretax_exporter.py`, `spt_desktop/output.py`: declared workbook set, exact scope/readback, preserved-folder index and publication integration.
- `spt_desktop/worker.py`, `events.py`, `runtime.py`, diagnostics/protocol where needed: required capture stage, bounded progress, explicit module/resource allowlist.
- `tests/test_mpn.py`, `test_mpn_browser.py`, `test_mpn_publication.py`, `test_resume_template.py`: synthetic behavior/ownership/layout/recovery tests; update existing old-coordinate assertions only where the approved output changed.

### Task 1: Pure payment contract and source custody

**Files:** Create `coretax_mpn.py`, `tests/test_mpn.py`.

**Interfaces:**
- `decode_mpn(raw: bytes) -> dict` rejects duplicate keys, nonfinite numbers, secrets and oversized/unsafe bodies; numeric literals retain a marker until canonical projection.
- `project_payment(header: dict, detail: dict, *, year: int, catalog=None) -> dict | None` returns a canonical negative in-year payment, excludes proved nonqualifying rows, raises `MpnUnsupported` for unsupported inputs and `MpnSafetyError` for contradictions.
- Canonical payment keys: record_id, header_id, period_code, period_label, transaction_date, posting_date, transaction_number, accounting_type, accounting_detail, currency, currency_amount, exchange_rate, amount, reference, parent_reference, revenue_code, source. Monetary values are original numeric lexemes; original response hashes/provenance remain separate.
- `require_mpn(run, detail_source)`, `validate_mpn(run)`, `mpn_filename(run)` and `mpn_custody(run, folder)` own version/scope/completeness/evidence bounds. A missing MPN key remains legacy scope; a required but missing/partial capture cannot certify COMPLETE.

- [x] Write qualification tests for own-year versus parent/payment year, negative/zero/positive, fractional/unsafe precision, duplicate/foreign identities, malformed period and secret/duplicate-key JSON.
- [x] Commit tests before implementation and run through the unmodified GitHub workflow; confirm the missing adapter fails as expected.
- [x] Implement the pure adapter and private held-reader/hash validation, with bounded raw-evidence paths and fixed safe errors.
- [x] Runner verification: `python -m pytest tests/test_mpn.py -q` through GitHub Actions; expected all cases pass.
- [x] Commit the verified contract and record exact runner evidence in the execution ledger.

### Task 2: Owned Accounting capture

**Files:** Create `coretax_mpn_browser.py`, `tests/test_mpn_browser.py`; update worker/CLI and progress interfaces in Task 4.

**Interfaces:** `collect_mpn(page, run, folder, *, detail_source='dom', max_pages=1000, on_progress=None, check_cancel=None) -> dict` updates run['mpn'] and overall completeness; `on_progress(done, total, qualified)` contains counts only. The collector derives taxpayer id from the unique verified submitted-list source, including empty SPT inventories.

- [x] Write synthetic browser tests: literal route/source ownership, stale request objects, successful/failed response envelopes, all-page traversal, source-year cross-allocation, missing month-filter removal and zero-header coverage.
- [x] Observe failing runner cases before adding their behavior.
- [x] Implement exact route/owner/loaded-source checks; attach observer before navigation; bind committed main-frame request objects and at most 128 pending requests; release request references on response/failure/close.
- [x] Configure the inspected ShowZeroValue=Yes, non-cancelled scope and subsequent Cari action; reject any unexpected date/amount/period restriction rather than claiming full coverage. Select the largest offered page size at most 50.
- [x] Traverse owned paginator pages sequentially. Before each pi-list action verify its selected row against the current list response; own the one Detail Transaksi dialog and original response bytes. Capture all detail pages before filtering negatives by the detail year.
- [x] Test and implement exact DOM monetary comparison, hidden-metadata binding and whole-detail JSON fallback. Verify Stop before every action/read, bounded final drain and failure/cap truthfulness.
- [x] Save exclusive attempt evidence/checkpoints in private mpn/ paths; never log raw URLs, bodies, identities or headers. Runner browser fixtures must use synthetic data only.
- [x] Runner verification: `python -m pytest tests/test_mpn_browser.py -q`; expected all ownership/fallback/cancellation cases pass.
- [x] Commit the collector and record exact runner evidence.

### Task 3: Reference resume and MPN workbook proofs

**Files:** Create `coretax_resume_layout.py`, `resources/resume_format.xlsx`, `coretax_mpn_export.py`, `tests/test_resume_template.py`; modify `coretax_exporter.py`.

**Interfaces:**
- `summary_scope(workbook) -> dict` accepts only the complete operator-v1 or known legacy labels/coordinates and provides npwp, year, basis, complete, record_count without guessing.
- `apply_resume_layout(workbook, run)` applies the approved presentation and dynamic counts/chart/table/print ranges after data mapping, without changing SPT-form sheets.
- `export_mpn_workbook(run, path)`, `read_mpn_proof(workbook)` and `verify_mpn_workbook(run, path)` separate MPN scope/ordered rows/audit from SPT record proofs.
- `resume_mpn_declaration(run)` / `read_resume_mpn(workbook)` carry a bounded MPN link/status/scope declaration without duplicating raw Accounting JSON into resume.

- [x] Add failing tests for B2/B3/B5/B6 bindings, the three approved sheets, Audit row-3 header, print/freeze/merge/width preservation and dynamic SPTIndex/chart ranges.
- [x] Add MPN export tests for literal identifiers, signed fractional numbers, unsafe precision text/unresolved audit, relative links and independent physical proof tampering.
- [x] Sanitize the reference through standalone OOXML package processing outside product imports: remove operational values/links/shared strings/chart caches/private metadata/printer binary while preserving approved safe styles/geometry. Verify all retained parts before Git; never commit the original private workbook.
- [x] Implement layout/proof helpers and invoke them only for administrative sheets; keep existing form renderers/filenames/model grouping unchanged. Explicitly support old administrative layout on reads without rewriting retained workbooks.
- [x] Runner verification: `python -m pytest tests/test_resume_template.py tests/test_mpn.py -q`; expected passing round-trip layout/proof cases and no sample values in zero/one/many-record exports.
- [x] Commit sanitized resource and verified renderer changes.

### Task 4: Full-job and publication integration

**Files:** Modify `coretax.py`, `coretax_exporter.py`, `spt_desktop/worker.py`, `events.py`, `output.py`, `runtime.py`; create `tests/test_mpn_publication.py`, extend existing entry/lifecycle tests.

**Interfaces:** A full live job declares MPN required, captures after SPT details before closing the browser, and gates overall COMPLETE on both captures plus publication/cleanup. Inventory-only and offline legacy export retain their declared limited scopes. MPN names/proofs never enter workbook_groups as SPT records.

- [x] Add runner failures for desktop/CLI orchestration, valid empty SPT inventory, MPN partial with preserved SPT, Stop, inventory-only/offline behavior and required-MPN completeness rejection.
- [x] Extend declared workbook names and verification to MPN, including existing-folder physical proofs, refreshed resume references, consent snapshots and file replacement/recovery. Preserve earlier unselected SPT/JSON/PDF bytes.
- [x] Add MPN progress and allowlisted worker/resource files; preserve GUI dependency/process boundaries and current build identity contracts.
- [x] Add scope/consent/collision/rollback/death-recovery tests for existing MPN alongside SPT; update only actual approved new-layout assertions in old tests. Keep separate legacy fixtures for old coordinates.
- [ ] Runner verification: full unmodified workflow; expected every Windows shard, portable suite, packaging, frozen self-tests, audit and aggregate checks pass.
- [x] Commit integration, tests and actual AGENTS.md/docs boundaries.

### Task 5: Review, artifact verification and integration

**Files:** Documentation/report and any reproduced substantive review fixes.

- [x] Fetch latest main; review preceding merged PRs and their actual changed functions/tests, especially PR115 committed-list restoration. Reconcile interactions without weakening existing checks.
- [ ] Run a fresh independent whole-branch review using requesting-code-review; fix reproduced important issues with runner RED/GREEN evidence. Record scope/rulings and exact commits.
- [ ] Verify final PR head/tested merge tree and read back exact run/attempt/artifact: manifests, hashes, WORKER_FILES/resources, source/frozen tests, package/bootstrap cleanup evidence and no private artifacts.
- [ ] Update PR title/body around final behavior and validation, attach it to this task, and carry it to merge readiness under the user's authorized PR workflow. If merging, recheck latest main/preceding PR and verify the resulting main build before reporting a usable EXE.

## Execution notes

Execution stays inline in this existing isolated worktree. Operator approval
authorizes implementing the design; plan bookkeeping adds no new permission
request. An independent reviewer is reserved for whole-branch verification.
Because local execution is prohibited, runner RED/GREEN checks may batch tightly
coupled interfaces into a single source/test checkpoint; record that ruling and
all observed failures/results in the ledger, never claim an unrun test passed.
