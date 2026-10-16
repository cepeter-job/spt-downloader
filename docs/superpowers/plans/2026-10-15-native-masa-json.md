# Native Masa JSON Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans (recommended here) or superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Export PPN and PPh Unifikasi from verified native responses with DOM-equivalent approved workbook layouts.

**Architecture:** A pure Masa adapter consumes capture packets and value-free observed form bindings. A separate browser observer performs read-only form/page traversal and verifies public build hashes. Existing browser dispatch chooses corporate/Masa adapters without changing DOM fallback or publication safety.

**Tech Stack:** Existing Python, Playwright, openpyxl and GitHub Actions; no new dependency.

**Spec:** `docs/superpowers/specs/2026-10-15-native-masa-json.md`

## Global Constraints
- DOM may supply navigation/labels/structure, never tax values to a native adapter result.
- Match only observed UI requests. Preserve identity/auth/privacy fail-closed checks independently of eligibility.
- Tests, imports, synthetic fixtures, builds and EXE checks are GitHub-runner-only; no CI changes merely to obtain GREEN.
- Only synthetic fixtures enter Git. Keep private evidence outside the repo; preserve unrelated untracked work and original downloads.
- Merge requires native `used=json` plus parity for both tax types, exact-SHA CI and independent review.

## Review Focus
- Conflicting identities hidden behind unknown build or missing fields: Task 1 negative checks must still raise.
- Empty/duplicate/multipage grids: Task 2 retains duplicate rows and requires exact offset coverage and totals.
- PPN initialization overrides and Normal/amendment display differences: Task 2 pins explicit paths and ordering.
- Unifikasi hierarchical rows and misspelled footer key: Task 2 preserves independent row/footer values.
- UI-only claims/declarations and lookup labels: Tasks 2/3 reject unbound dependencies rather than relabel DOM values as JSON.

## Task 1: Packet and identity contract
**Files:** Create `coretax_masa_json.py`, `tests/test_masa_json_adapter.py`, `tests/masa_json_fixtures.py`.

**Interfaces:** `adapt_masa_detail(bodies, *, record, scope, observed_forms) -> dict` returns the existing adapter keys `eligible`, `reason`, `sections`, `coverage`, `provenance`. `check_masa_request_identities(observations, record, scope) -> None` raises `JsonSafetyError` on explicit known-source contradictions. Both remain independent of browser state. Reuse existing packet/privacy primitives only after checking that their corporate-specific assumptions do not bypass Masa identity checks.

- [ ] Write synthetic tests for both observed prefill shapes: wrong TIN, taxpayer ID, record/aggregate ID, year, month/period and model; combine each conflict with missing coverage and unknown build. Assert `JsonSafetyError`, not fallback. Missing evidence alone yields `eligible is False`.
- [ ] Write tests for unauthorized status, secret payload/request, malformed nested FormData, duplicate conflicting packets and foreign frame/attempt binding. Fixtures derive keys from reviewed public bindings, never real values.
- [ ] Push test-only RED commit and inspect the exact GitHub run failure. Expected missing adapter/guard assertions; repair collection/fixture failures before implementation.
- [ ] Implement only the packet/identity gate; read all known identity evidence before returning unsupported eligibility. Do not force corporate tax codes onto Masa.
- [ ] Verify runner GREEN for safety tests and existing suite; commit explicit files only.

## Task 2: Response-to-form projection
**Files:** Create `coretax_masa_bindings.py`; extend `coretax_masa_json.py`, `tests/test_masa_json_adapter.py`; create `tests/test_masa_json_templates.py`.

**Interfaces:** `coretax_masa_bindings.py` owns explicit build hashes, tax-specific form/control/path/grid definitions, not a generic schema engine. Adapter consumes observer dictionaries with `name`, value-free `fields` (`field`, `label`, `group`, `column_label`), and `tables` (`headers`, `group`, verified request bindings/page offsets/totals). Missing field/path/formatter is unsupported, never guessed. Output uses existing section `fields` and `tables` contracts; provenance retains response/path/raw value for transformations.

- [ ] Complete the public-source mapping ledger for each visible control/grid and final post-initialization value, including enum/date/number renderers. Confirm exact native type/model metadata from listing and public enums. No unresolved mapping is marked supported.
- [ ] Add `test_ppn_export_override_uses_a1_total`: synthetic source paths deliberately disagree; output equals the later A1 total, with that path in provenance. Add null-versus-zero, signed decimals and Normal/amendment tests. Assert DOM-like labels only, values from JSON.
- [ ] Add `test_unifikasi_tree_and_footer_have_independent_government_keys`: deliberately different row/footer amounts; preserve hierarchy and each value. Add populated fixtures for all five grids based on component definitions, including duplicates and zero-row cases.
- [ ] Add offset-gap/overlap/changed-total/page-limit/filter tests; compare assembled counts, never deduplicate identical rows. Add template tests with populated PPN A2/B2 growth and Unifikasi totals, styles/merges and raw-evidence retention.
- [ ] Observe runner RED, implement explicit projections, then verify runner GREEN and commit. Unsupported claim-dependent values must remain explicit rather than filled from current-user claims or DOM.

## Task 3: Browser traversal, dispatch and packaging
**Files:** Create `coretax_masa_observer.py`, `tests/test_masa_json_observer.py`; modify `coretax_browser.py`, `spt_desktop/runtime.py`, `tests/test_json_hybrid_native.py`.

**Interfaces:** `observe_masa_forms(page, record, scope, capture, *, max_pages, check_cancel) -> list[dict] | None` returns the Task 2 value-free binding shape only after verifying the appropriate public build and inspected tab/pagination coverage. Request checks run before/after observation/drain. `_hybrid_detail` dispatches by exact selected tax type; native result uses `reason='verified_native_masa_source'`, existing corporate behavior is unchanged.

- [ ] Add routed synthetic browser tests for all observed tabs (PPN INDUK/A-1/A-2/B-1/B-2/B-3/C; Unifikasi INDUK/DAFTAR-I/DAFTAR-II/LAMPIRAN-I), wrapped panels and accordion nesting. Only top-level tabs are clicked; unrelated links/buttons never execute.
- [ ] Add delayed prefill, pagination resets, cancellation, 401/403, unknown build, extra/missing form and request-identity contradiction tests. Use deliberately poisoned DOM input amounts: a native result must ignore them and use synthetic response amounts.
- [ ] Observe runner RED, implement traversal and dispatch, and add only the new modules to `WORKER_FILES`. Do not change captured values or capture guards to obtain eligibility.
- [ ] Verify full Windows/portable CI and source/frozen tests on the exact commit; inspect staged diff for privacy, commit and push.

## Task 4: Local acceptance and release gate
**Files:** Update `docs/masa-template-repair.md` with sanitized findings only. Private acceptance drivers/reports remain outside Git.

- [ ] Run authorized local DOM and native JSON acceptance on PPN January, populated PPN February and Unifikasi January using fresh job folders, exact source SHA and no overwrite. Require every native case to report `used=json`; preserve original hashes.
- [ ] Audit exact workbook cell parity, templates/row growth, all observed forms and per-grid counts. Compare raw source/provenance separately from display formatting. Any mismatch becomes a synthetic runner regression before fixing it.
- [ ] Obtain independent whole-branch review including identity fallbacks, projection coverage and packaging/privacy; resolve blockers and rerun exact-SHA CI.
- [ ] Verify remote PR head/tree and merge only when all gates pass. Sync main without deleting unrelated work.
- [ ] Download exact successful main-build Windows artifact; verify run/commit/artifact ID, archive contents and checksum. Deliver ZIP plus concise verified results; do not call intentional overwrite-decline CANCELLED a published COMPLETE run.

## Execution choice
Recommended: parent-led native execution with independent final review. Safety, observer and projection interfaces are tightly coupled; the parent already holds private evidence and must integrate the acceptance findings. Public-source investigations can remain parallel. Review this plan before product implementation; the design approval itself is already complete.
