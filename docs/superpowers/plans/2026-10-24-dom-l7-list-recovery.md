# DOM L7 and list recovery implementation plan

> **For agentic workers:** Use superpowers:executing-plans for this small repair;
> use one fresh whole-branch reviewer before integration.

**Goal:** Export the verified literal-period L7 table and recover one missing
submitted-list response without weakening source custody.

**Architecture:** Retain the current exporter/renderer. Add an exact annual
period alternative and a distinct list-response timeout with a one-retry helper.

**Tech stack:** Existing Python/openpyxl/Playwright; unchanged locked runtime.

**Spec:** `docs/superpowers/specs/2026-10-24-dom-l7-list-recovery-design.md`.

## Global constraints

All product tests/imports, browser fixtures and packages are GitHub-runner-only.
No private data, CI/resource change, authentication broadening or new Induk
destinations. Preserve original values, selected record and PARTIAL gates.
The CI-discovered dependency maintenance is limited to audit filelock4.2.1 and
build setuptools84.1.0 plus their uv0.13.4 universal hashes. Runtime/test locks
and strict dependency audit/freshness checks stay unchanged.

## Review focus

1. A stale response cannot satisfy the retry: require actual post-commit request
   custody, including old-document work started while replacement is pending.
2. Identity/route changes during the first wait cannot be hidden by navigation.
3. Stop between timeout and retry prevents the second navigation and capture.
4. A restored response missing the selected record cannot authorize View.
5. Literal monthly/partial-year codes or conflicting year headers stay unmapped.
6. Owned HTTP errors and explicit unsuccessful JSON without rows are terminal,
   independent of successful-envelope shape or later traffic.

### Task 1: Pin regressions before implementation

Files: `tests/test_corporate_l7_period_export.py`,
`tests/test_list_restore_recovery.py`.

- [ ] Add saved/reopened L7 exports with exact literal annual periods, zero rows,
  captured totals, original filenames/metadata, final compaction and unchanged
  source snapshots. Add conflicting/malformed/monthly/partial-year refusals and
  a capture-PARTIAL preservation case.
- [ ] Add public collect_details protocol cases for first-missing/second-valid,
  persistent missing, fresh marker, changed route/identity, unsuccessful response,
  Stop, a missing selected row and existing filter safety failure.
- [ ] Push tests/docs only; read expected RED from the actual runner jobs.

### Task 2: Minimal repair and green validation

Files: `coretax_badan_template.py`, `coretax_browser.py`, `AGENTS.md`.
CI maintenance: `requirements-audit.txt`, `requirements-build.txt`,
`locks/audit.txt`, `locks/build.txt`.

Interfaces: keep `_current_l7_header(sheet, sections, period)` and public
`collect_details` unchanged; `ListObserver.wait(after, timeout=45)` raises a
RuntimeError subtype only for absent fresh responses. A private helper returns
the verified response after at most two navigations, retaining each new marker.

- [ ] Implement exact annual code binding with the same captured-header checks.
- [ ] Implement the typed timeout and bounded same-owner restoration retry.
- [ ] Record actual supported boundaries in AGENTS, run local AST/diff checks,
  then push and read full Windows/portable CI and exact package identities.
- [ ] Resolve final-review findings with runner RED for late old-document
  responses and HTML/empty-payload failures, then implement bounded document and
  request custody plus terminal error classification. Protocol fixtures model
  real commit/request/response ordering; isolated real Edge cases remain active.

### Task 3: Review and integrate

- [ ] Review all latest preceding other-session changes and candidate interaction.
- [ ] Dispatch one fresh whole-branch reviewer; address important findings through
  runner RED-to-GREEN and repeat the full suite only when necessary.
- [ ] Verify exact latest-main merge tree/checks, merge with expected-head lease,
  verify actual main CI and preserve recovery evidence. Remove only this merged
  branch. Read back and deliver the actual-main package to both Downloads.
