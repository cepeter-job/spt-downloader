# DevOps Audit Repairs Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development to implement and independently review the bounded work below. Track observed runner evidence before marking verification complete.

**Goal:** Close the repository-addressable findings from the 22 October DevOps audit in one reviewable PR, with exact-head Windows, portable, dependency, package and security checks passing.

**Architecture:** Reuse existing checkpoint/path/process primitives. Keep selection recovery, temporary profile ownership, publication restart recovery and build identity in focused modules. Promotion consumes an already verified trusted-main artifact; it does not rebuild the executable.

**Tech Stack:** CPython 3.14.8 x64/GIL, stdlib/Tkinter, Playwright, openpyxl, uv, PyInstaller, GitHub-hosted Windows/Linux runners.

**Spec:** [2026-10-22 DevOps audit](../../audits/2026-10-22-devops-audit.md). The owner authorized all fixes through a merge-ready PR. Merging and publishing a production release are outside this task.

## Global Constraints

- Pytest, product imports, native/Tk/browser fixtures, self-tests, builds and EXE execution run only on GitHub runners. Local source/AST checks are not execution evidence.
- Retain strict required checks, full Windows inventory, two isolated Windows shards, portable coverage, package readback and trusted-main provenance.
- Never use live taxpayer data, credentials or portal accounts. Preserve existing data, unselected outputs, explicit overwrite consent, active profiles and unresolved recovery.
- Preserve exact identifiers, selected order, scope and capture mode across recovery. Stop wins over completion and process events.
- No invented certificates, zero-alert claims, endpoint compliance or live acceptance. External prerequisites remain explicit in the closure record.

## Review Focus

- Disk-full or replacement failure during Stop preserves the previous valid checkpoint and a terminal cancellation outcome.
- Process death bypasses Python cleanup; inactive owned profiles are reclaimable while active, unrelated and reparse-point targets remain untouched.
- Selected desktop continuation never expands to unselected records or changes capture mode, including legacy folders without a durable manifest.
- Publication recovery refuses redirected paths and post-crash concurrent edits; all pre-existing bytes remain recoverable after a killed process.
- Packaging and promotion bind exact SHA/run/attempt/artifact bytes; no PATH/config override, unexpected skip, docs supersession or mutable checksum can silently remove that guarantee.

## 1. Recovery and temporary profile lifecycle — F1/F2

**Files:** `spt_desktop/worker.py`, `auth.py`, `controller.py`, new `profile_lifecycle.py`; `tests/test_desktop_recovery_lifecycle.py`, `test_desktop_profile_lifecycle.py`.

**Interfaces:** `temporary_profile(root, kind)` owns a validated temporary session directory and a held lease; `reap_profiles(root)` inspects only owned inactive entries. Cancellation uses the existing atomic JSON checkpoint primitive.

- [ ] Add behavior tests for partial write, ENOSPC, replacement failure, cancelled terminal delivery, ordinary profile cleanup, actual process death, active leases, malformed ownership and redirected paths.
- [ ] Observe the regression tests fail on the unchanged implementation in GitHub Actions.
- [ ] Implement bounded lifecycle reconciliation before setup and after owned process termination; keep cleanup outside the UI thread.
- [ ] Verify native Windows tests plus the complete existing workflow; record exact commit/run.

## 2. Durable selection and publication recovery — F6/F8

**Files:** new `coretax_resume.py`, `spt_desktop/publication_recovery.py`; `coretax.py`, `spt_desktop/output.py`; new selection/publication tests and accurate synthetic inventory helper.

**Interfaces:** `persist_selection(run, folder, *, detail_source='dom')` writes a guarded atomic manifest bound to the original inventory. `load_resume_inventory(folder, *, detail_source=None)` returns `(selected_run, effective_detail_source)`. `recover_publication(source, downloads)` performs explicit guarded restoration from the private durable journal and is repeatable.

- [ ] Test non-prefix/prefix/reordered selections, changed inventory/mode, legacy desktop rejection and persistence before first detail.
- [ ] Test actual child-process death after displacement, installation and index installation; verify durable private journal, exact old bytes, repeatability and preservation of concurrent/unrelated data.
- [ ] Observe runner failures, then implement write-ahead publication records and explicit recovery with conservative identity/path/hash validation.
- [ ] Document recovery invocation and retained evidence; prove the changed behavior on Windows without any real taxpayer inputs.

## 3. Deterministic packaged worker — F3/F7

**Files:** `spt_desktop/runtime.py`, `spt_gui.py`, `build_desktop.py`, `scripts/ci_runtime.py`; runtime/frozen-entry regression tests.

**Interfaces:** bootstrap environment disables uv configuration discovery and unrelated policy overrides while preserving reviewed proxy/CA settings. Packaged mode chooses its bundled pinned uv. The explicit account-free runtime self-test exercises the downloaded EXE with a fresh runner-owned workspace.

- [ ] Test bundled-tool preference, environment/config contamination, legitimate network settings, missing bundle failure and packaged smoke report identity.
- [ ] Observe runner failures, then implement the isolated bootstrap and actual EXE cold/reuse/owned-cancellation path.
- [ ] Update the explicit worker-file allowlist for new recovery/lifecycle/build modules and optional build metadata.
- [ ] Bind smoke evidence to the downloaded artifact, SHA, run, attempt and executable digest; retain source and frozen GUI checks.

## 4. CI, package identity and release promotion — F4/F5 and maturity controls

**Files:** workflow files; `scripts/ci_route.py`, `ci_tests.py`, `ci_artifact.py`, release tooling and tests.

**Interfaces:** seven-file distribution includes the five existing payload files plus `build-info.json` and `distribution-sbom.json`. Build metadata has `schema=1`, full 40-hex `commit`, decimal-string `run_id`, positive integer `run_attempt`. Promotion accepts only a successful trusted-main run and exact verified artifact, with explicit version and dry validation before publication.

- [ ] Test running/pending code→docs preservation, unexpected skip rejection, immutable platform uv digests, artifact payload identity and untrusted/mismatched promotion inputs.
- [ ] Observe runner failures, then implement policy without relaxing required checks or reducing inventory.
- [ ] Generate component inventory with honest audit-coverage boundaries and immutable build identity; include both in checksum/provenance contracts.
- [ ] Verify promotion preparation and rollback procedure using synthetic/existing verified artifacts; do not publish a release during PR preparation.

## 5. Diagnostics, operations guidance and integration

**Files:** new `spt_desktop/build_info.py`, diagnostics, `SECURITY.md`, release/recovery/maintenance docs and audit closure record.

**Interfaces:** build identity reads a bounded strict metadata file from the resource root; unknown source identity is explicit and cannot be supplied through arbitrary environment values. Diagnostics include only public immutable build coordinates.

- [ ] Test validated build coordinates and rejection of malformed/private metadata before implementation.
- [ ] Add a concrete private-disclosure procedure, notification ownership guidance and safe private-storage inventory/maintenance instructions that preserve active jobs and unresolved recovery.
- [ ] Update superseded recovery/distribution statements and list external certificate, administrative-security, endpoint and live-acceptance prerequisites honestly.
- [ ] Review the complete diff independently, repair findings, obtain exact-head required checks and inspect the resulting package by artifact ID.
- [ ] Mark the PR ready only after all blocking review findings and required checks are resolved; report remaining external prerequisites without presenting them as fixed.

## Execution record

Baseline: `d402b98a1a534f761e60500fc1cc17f367461298`, main run `39629732190`; Windows 3,596 passed, portable overlapping subset 568 passed, zero skips. Implementation, runner regression evidence and final acceptance are recorded in the PR and closure report as they become available.
