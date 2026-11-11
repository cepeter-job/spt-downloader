# PR #235 L7 and DOM L3 integration plan

> **For agentic workers:** Use superpowers:executing-plans with isolated worktree and test-driven development. Native/product test execution occurs only on GitHub-hosted runners.

**Goal:** Finish the accepted strict L7 raw-negative candidate and add privacy-safe initial DOM loading diagnostics without changing existing capture outcomes.

**Architecture:** Keep the L7 observer, manifest-owned history and projection independent from DOM fallback. Bind a single existing table owner when preparing that table; use a finite best-effort diagnostic scope and a browser-engine-limited structural probe only when needed. All original clicks, timeouts, source admission, Stop and publication behavior remain unchanged.

**Tech Stack:** CPython 3.14 production, Playwright 1.64.1 Edge/Chromium, existing diagnostic allowlist, pytest on hosted Windows CI.

**Spec:** `docs/superpowers/specs/2026-11-11-badan-live-followup-design.md` (PR #233, closed unmerged reference).

## Global constraints

- Never access account/financial field values or log raw URLs, request bodies, taxpayer IDs, document names, credentials, or response payloads.
- New diagnostic observers are passive, bounded and removed on every exit. Disabled logging installs no listeners and runs no additional structural RPC.
- Preserve actual size/First controls, 45-second overlay wait, 180-second table budget, original exception, Stop, cursor and PARTIAL semantics; no retries or speculative fix.
- Structural probe executes under Chromium `Runtime.evaluate` browser-engine `timeout<=1000` and the table's remaining budget; timeout/unsupported driver yields `unavailable`, never success.
- Strict L7 negative proof remains additive, with three loaded pins and manifest-owned continuous L7 lifetime; old nonnegative admission is unchanged.
- Do not execute product imports, browser fixtures or pytest locally. Use static AST/source checks locally and hosted exact-head CI/CodeQL, peer review and package/readback gates.

## Review focus

- Foreign loading overlay or global BlockUI should not be mislabelled as the held table.
- A detached/reinserted original table owner must not be replaced by a lookalike.
- Stop or table timeout must preserve the original exception even if diagnostics fail.
- Overflow/unavailable request or DOM observations must not masquerade as `none`.
- Diagnostics OFF must have zero added request listeners/structural calls; retained handles must be released after PARTIAL.

### Task 1: Lock the RED tests and diagnostic schema

**Files:** `tests/test_capture_failure_privacy.py`, `tests/test_diagnostics.py`, `spt_desktop/diagnostics.py`

- [ ] Confirm hosted shard-1 RED on the exact missing `table.initial_loading` event; no unrelated test failures.
- [ ] Add a fixed enum schema for stage, loading scope/first match, availability, and bounded numeric/request counts.
- [ ] Add synthetic tests for missing/untrusted fields, foreign/global loading categories, disabled instrumentation and owner changes.
- [ ] Run exact-head hosted tests and inspect JUnit; stage is complete only when missing behavior fails with a specific assertion.

### Task 2: Implement bounded initial-loading observer

**Files:** `coretax_browser.py`, optional small diagnostic helper, `tests/test_capture_failure_privacy.py`

- [ ] Hold one original table owner and Document across the preparation interval; never search for a replacement.
- [ ] Observe original request-object lifecycle passively in a bounded set with no raw metadata persisted or logged.
- [ ] Record fixed preparation/size/First stages and durations without changing actual actions.
- [ ] On original First idle timeout, emit an allowlisted category from a Chromium engine-limited structural probe or `unavailable`, then re-raise the same exception object.
- [ ] Release CDP session, request listeners and temporary owner anchors on all exits; fail-closed diagnostic operations never mask Stop.
- [ ] Confirm hosted GREEN for targeted synthetic cases, plus same wait/click/PARTIAL outcomes.

### Task 3: Integration and acceptance

**Files:** `AGENTS.md`, `docs/diagnostik.md`, this plan, PR #235 metadata.

- [ ] Document additive L7 contract, optional lifetime/legacy nonnegative behavior, and DOM diagnostics timing limitations.
- [ ] Review latest merged `main` changes and resolve conflicts without force-push.
- [ ] Run complete hosted exact-head selected CI (all four Windows shards, portable, CodeQL, security and package provenance/readback/bootstrap).
- [ ] Request independent review; fix blocking comments with tests and rerun exact-head CI.
- [ ] Keep PR draft/unmerged until code CI and review gates pass. A separately authorized exact-build live run is still required for native/live acceptance.
