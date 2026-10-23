# Period Restoration and Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permit a source-proven late period label without changing inventory evidence, and publish same-ID/different-period exports without changing previous files.

**Architecture:** Keep verification in `coretax_browser.py` before View. Extend existing physical workbook inspection in `spt_desktop/output.py` so a validated period filename conflict uses the existing new-folder publication path. Keep duplicate-ID rejection in the exporter.

**Tech Stack:** Existing Python 3.14.8 GIL, synchronous Playwright/Edge, openpyxl and native Windows publication guards; no new dependencies.

**Spec:** [Period metadata contract](../../period-metadata-conflict.md), plus repository `AGENTS.md`. User has authorized implementation, PR merge and artifact delivery; independent review is read-only, implementation stays inline.

## Global Constraints

- Product execution, pytest, browser fixtures and packaging run only on GitHub runners.
- Commit source, documentation and clearly synthetic tests only.
- Preserve literal inventory metadata, occurrences, old exports and exact relative links.
- Never bypass login, CAPTCHA, MFA, source identity checks, Stop or overwrite consent.
- Keep incomplete captures and financial downloads explicitly PARTIAL.
- Do not change workflows, locks, worker allowlist or LICENSE.

## Review Focus

- A valid catalog must not hide a contradictory or absent current API period code.
- Changed restored model/receipt must be rejected independently of saved-occurrence consistency.
- A legacy multi-occurrence checkpoint without proof must not gain fresh submitted-only authority.
- Stop after catalog observation must prevent View and snapshot publication.
- A separate period folder must retain valid old PDF bytes and reject corrupted prior PDF evidence.

## Task 1: Prove late labels before View

**Files:** Modify `coretax_browser.py`, `tests/test_json_inventory.py`; create `tests/test_late_period_restoration.py`; update the period contract.

**Interfaces:** Add `_verify_restored_metadata(page, run, record, current_meta, api_record, folder, ordinal, check_cancel) -> None`. Consume existing `read_period_catalog(page)` and `prove_period_equivalence(left, right, catalog, year)`. Return normally only after exact metadata checks or a source-bound period proof; otherwise raise before View.

- [x] Add synthetic code-to-label transition and invalid catalog/current metadata/API/legacy/cancellation cases. Preserve inventory bytes and assert no archive navigation or private diagnostic values.
- [x] Observe intended failures on the test-only GitHub PR run; distinguish failures from fixture or collection errors. Run `39885260515`: six expected failures, zero errors/skips.
- [x] Check other metadata first. For a changed period, require current API code plus either the same saved semantic proof or one matching submitted-only source occurrence. Save fresh proof/catalog privately with exclusive filenames and cancellation barriers.
- [ ] Run the existing full GitHub Windows suite and portable subset; inspect failures and exact counts. Existing legacy alias rejection tests must also pass.
- [ ] Commit production changes with synthetic tests and the documented contract.

## Task 2: Preserve same-ID period export history

**Files:** Modify `spt_desktop/output.py`; create `tests/test_period_identity_publication.py`; update `docs/arsitektur.md`.

**Interfaces:** Extend private `_workbook_scope(run, path, relative)` result with physical proof record identities. `_inspect` returns a deterministic `period_identity_conflict` flag after complete validation. `existing_outputs(run, downloads)` returns `None` for that flag, reusing guarded fresh-folder publication. Public signatures and strict exporter duplicate-ID rules stay unchanged.

- [x] Add successful captured/partial/new-PDF migrations, corrupted prior scope/PDF rejection, exact file/link/status preservation and same-period overwrite consent regressions.
- [x] Observe intended publication failures on the test-only GitHub PR run.
- [x] Reject duplicate old physical IDs and changed tax/model for one ID. Classify only a same-ID, same-tax/model, different literal-period physical filename as a separate-folder condition.
- [x] Validate all old COMPLETE PDF declarations before returning the separate-folder decision. Preserve existing directory guards, fingerprint checks and the final race reinspection.
- [ ] Require the full GitHub run, source/frozen self-tests and exact candidate artifact readback to pass. Obtain independent read-only implementation review and resolve significant findings.
- [ ] Merge the verified up-to-date PR to `main`; require the exact main run, distribution/bootstrap manifests and attestations. Copy the verified main ZIP to the authorized Downloads destination and verify its hash. Archive only this managed worktree and delete its merged branch, preserving other work and recovery state.

Local AST and diff checks are syntax/privacy checks only. GitHub fixture results do not establish live Coretax/Excel acceptance.
