# Isolated launcher candidate operator instructions

This is an unsigned investigation candidate, **not a production runtime upgrade**.
Reader qualification has failed or remains blocked. Do not replace the distributed
launcher, adopt this runtime, merge the candidate, or publish a release based on
successful build/self-test results. The [adoption audit](../../docs/audits/2026-10-22-tk-accessibility-candidate.md)
separates behavior, accessibility, display and custody evidence.

## Scope and execution

All product imports, pytest, native/Tk/browser probes, builds and EXE execution run
only on GitHub Windows runners. Local work is limited to source/AST review and
artifact hash/metadata inspection. Use only the supplied synthetic fixtures; do
not provide accounts, taxpayer records, browser profiles, saved captures or real
outputs. Signing and owner live acceptance are deferred.

The normal worker/CLI remains managed CPython 3.14.8 x64/GIL, uv 0.13.4, unchanged
locks and the reviewed main `WORKER_FILES` allowlist (43 resources). The launcher candidate uses matching source-built
CPython 3.14.8, `_tkinter`, Tcl/Tk 9.1.0. Native source revisions and archive hashes
are pinned in `sources.json`; the qualified runtime is artifact `12400037968`,
run `39718421643`, attempt 1. `inventory.json` SHA-256 is
`9758f2a63e8815952ca91178a9c20397f4292ad2aca8bfbff0feeb3c87b80239`.

After the full main integration, historical artifacts do not qualify the combined tree. Packaging now retains build-info and an actual native/worker SBOM, and exact artifact readback also runs main's packaged managed-worker bootstrap, reuse and owned cancellation checks.

## Runner procedure

1. Use `.github/workflows/launcher-candidate.yml` on the isolated candidate branch.
   Record the exact head, tree, run and attempt. Native builds are opt-in through
   `build_native`; routine qualification reuses the pinned native artifact.
2. The inventory job verifies candidate bytes and runs the focused contracts with
   `locks/test.txt`. Packaging uses `locks/build.txt`, records all declared members
   and runs source/frozen self-tests. Readback downloads the application by the
   upload step's exact artifact ID and verifies its complete manifest before
   executing it outside the checkout. The finite `regression` scenario runs actual
   Settings decisions/password clearing, selection/overwrite consent, stale/Stop
   handling, terminal UI eligibility and native owned cleanup in source, frozen
   and exact-readback frozen processes. Reports retain booleans and candidate
   identity, not password values. Full controller/output safety is also exercised
   by the candidate Windows suite.
3. Independent jobs run the complete Windows suite under the candidate, portable
   tests under managed CPython, the locked dependency audit, and actual managed
   worker bootstrap/reuse. Failures in reader qualification must not suppress
   these independent observations. A passed dependency audit covers the locked
   Python packages; it is not a vulnerability audit of all custom native sources.
4. Performance runs the unchanged `ui_delivery_performance.py` observer twice on
   one runner: reviewed UI baseline `cfa30a41e1106b8b0565c44b46da6b4ffdba0b4d`
   versus the current clean checkout under managed Python, then the same pair
   under candidate Python. Keep raw samples, payload hashes, interpreter/native
   identities and environment. Each pair requires equal Tcl/Tk. Compare equivalent
   operations across pairs separately and retain the below-100-ms settled-opening
   target; an observer exit of zero alone does not prove that target.
5. The display observer records real modes, work areas, geometry, High Contrast
   state and restoration. Inspect its screenshots and report. A large resolution
   is not proof of actual 200% scale. Hosted single-monitor observations cannot
   establish movement between distinct-DPI monitors. Missing suitable hardware is
   BLOCKED; never fabricate monitor metadata, alter registry scaling or force a
   minimum window size beyond the actual work area. Use a suitable authorized
   GitHub Windows runner for the outstanding gates.
6. NVDA/Narrator before-Tk and late-activation reports remain independent per
   reader and source/frozen mode. The password gate precedes other reader claims.
   A synthetic masked-entry behavioral check does not establish provider secrecy,
   typing echo, reader copy or speech navigation safety. Preserve sanitized phase,
   failure and owned cleanup records when initialization fails.
7. Inspect a normal production-mode build from the current source for exclusion
   of all `scripts.launcher_candidate` modules in both CArchive and PYZ. The
   diagnostic job retains inspection/self-test reports, not a release EXE.
8. Download every final artifact by exact ID, compare ZIP SHA-256 with the API
   digest, verify manifest file sets and hashes, and match head/tree/run/attempt.
   Upload success or an artifact filename containing a commit is insufficient.
   Retain evidence outside the repository; never commit generated ZIP/EXE/PDF,
   captures, credentials or private logs.

## Interpreting results

Use PASSED only for the measured behavior and exact artifact. FAILED identifies
an observed incompatibility or acceptance failure. BLOCKED means the required
facility or prerequisite was not established. Do not convert failed provider
startup into a missing-facility pass. Preserve failure evidence even when a later
harness correction obtains more complete observations.

Two controlled native builds already exist (`12400030052` and `12400037968`).
They use matching pinned inputs and recorded toolchain, but their bytes differ.
The audit explains measured PE timestamps/debug paths and the limits of that
comparison. Do not call the runtime byte-reproducible or suppress new warnings.

A fresh whole-change review and a separate adoption decision are still required.
The candidate draft PR is for review and recovery; normal distribution remains
unchanged. Keep the recovery worktree and SDD reports.

The shared `tests/` collection contains 3925 combined tests. The candidate-only
native behavioral case is explicitly invoked from
`scripts/launcher_candidate/test_native_regression.py` in the required inventory
and package checks. Its six assertions are unchanged; it has no skip condition.
The candidate's normal two-shard suite must satisfy the same complete-outcome
gate as production. Qualification therefore records shared coverage and the
separate mandatory native case, without counting a production skip as coverage.
Pushes coalesce only this candidate workflow/branch; manual native build runs
retain separate run identities. Normal production workflow concurrency is intact.
