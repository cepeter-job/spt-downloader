# MPN Source Custody Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Prevent nonqualifying source observations from causing MPN ownership failures and require positive empty-inventory evidence.

**Architecture:** Keep the existing observer and UI lifecycle. Narrow request admission, preserve later identity checks, and emit bounded first-refusal diagnostics. Restore the positive original-response completion contract weakened by PR123.

**Tech Stack:** Python standard library, Playwright, pytest, existing GitHub Windows/portable workflows.

**Spec:** `docs/superpowers/specs/2026-10-27-mpn-source-custody.md`

## Global Constraints

- All product tests, imports, browser fixtures and builds run on GitHub runners.
- No real taxpayer data, URLs containing identifiers, credentials or captured bodies in Git or CI artifacts.
- Preserve fatal identity/privacy/snapshot checks, Stop, exact source pins and source byte custody.
- No CI changes or dependency/worker-allowlist expansion.
- COMPLETE empty inventories require an owned original zero-row response.

## Review Focus

- A fetch of a pinned script cannot prove script execution or fail an otherwise supported capture.
- Non-GET reference traffic must be ignored before response/body access.
- An admitted request whose identity changes remains fatal, even after a later unsupported observation.
- First-refusal diagnostics must not leak arbitrary messages or material and must not retain exceptions.
- No yielded inventory pages must remain PARTIAL while a genuine empty response stays COMPLETE.

### Task 1: Source admission, first rejection and positive empty proof

**Files:** `coretax_mpn_ui.py`, `coretax_mpn_browser.py`, `coretax_mpn.py`, `spt_desktop/diagnostics.py`, `AGENTS.md`; tests in `tests/test_mpn_source_custody.py`, `tests/test_mpn_capture_protocol.py`, `tests/test_mpn_capture_browser.py`, `tests/test_diagnostics.py`.

**Interfaces:** Existing AccountingUI callbacks and collect_mpn contracts; new fixed `mpn.source_rejected` event and source-stage enum only.

- [ ] Add synthetic protocol, browser, completion and privacy regression tests; push tests-only branch and read exact runner RED evidence.
- [ ] Narrow source admission, retain admitted request identity, make refusals sticky and record first safe rejection. Refuse absent inventory evidence while preserving owned zero responses. Update AGENTS boundaries.
- [ ] Read exact runner GREEN inventories/results and unchanged production self-tests/package evidence.
- [ ] Obtain one fresh whole-branch review, address material findings and rerun exact-head gates if changed.
- [ ] Review latest main and preceding other-session PR, merge expected head, verify actual-main run/package and copy the complete package plus ZIP/receipt to Downloads.
