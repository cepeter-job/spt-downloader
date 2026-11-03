# Native driver trust implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) tracking.

**Goal:** Make owned Windows APIRequestContext use already trusted system CAs without weakening verification.

**Architecture:** A stdlib-only manager wrapper defaults one Node startup variable during __enter__, restores it, and delegates cleanup. Both CLI and desktop keep their existing local factory names and lifecycle contracts.

**Tech Stack:** Python 3.14.8, pinned Playwright/Node, native Windows certificate fixture on hosted runners.

**Spec:** `docs/superpowers/specs/2026-11-03-native-driver-trust-design.md`.

## Global constraints

- No TLS bypass, OS/machine environment change, proxy change, extra catalog GET, endpoint/locale expansion or admission relaxation.
- Preserve explicit environment values, Stop, cleanup, original factory patch points and GUI import separation.
- Product tests/imports/builds run only on GitHub runners; local evidence is source/AST/Git/hash and generic no-HTTP TLS diagnostics.

## Review focus

- __enter__ raises after acquisition: restore environment and retain CLI's contained cleanup.
- Explicit opt-in/opt-out and caller updates: preserve them exactly.
- Nested/concurrent starts: serialize temporary defaults and avoid losing system trust mid-start.
- Real TLS validation: native trusted root succeeds while untrusted defaults and hostname mismatch fail.
- Packaged worker: new stdlib owner must be embedded and hash-verified without GUI dependency changes.

### Task 1: Startup wrapper and integration

**Files:** new `coretax_transport.py`, `coretax.py`, `spt_desktop/worker.py`, `spt_desktop/runtime.py`, `tests/test_driver_system_trust.py`, `tests/test_driver_system_trust_tls.py`.

**Interfaces:** `system_ca_manager(manager)` returns a context manager whose entry temporarily defaults NODE_USE_SYSTEM_CA only on Windows; exit delegates to the original manager.

- [ ] Write unit/entrypoint and real synthetic TLS regressions. Observe runner RED before implementation.
- [ ] Implement the wrapper and both integrations; add the explicit worker resource.
- [ ] Observe GREEN including CLI partial-initialization cleanup, desktop outcomes, native TLS, explicit overrides and hostname rejection.

### Task 2: Review and release

**Files:** AGENTS.md and verification report; no permanent workflow change.

- [ ] Document the supported Windows driver-startup trust boundary.
- [ ] Remove the temporary runner probe and obtain independent review; fix material findings with regressions.
- [ ] Refresh main and preceding merged functions/tests/contracts; require full exact-head CI, then merge under existing authorization.
- [ ] Verify exact merged-main tests/package/bootstrap/resources/IDs/hashes, deliver seven-file package plus ZIP to both established Downloads locations, read back hashes and clean the merged branch.
- [ ] Continue L3-B live investigation independently; never claim its timeout fixed from TLS or package evidence.
