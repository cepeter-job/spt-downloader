# L3-B Renderer Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate renderer execution from existing cursor RPC wall timings before choosing a corporate DOM performance fix.

**Architecture:** Add optional function-local numeric timings to the two existing successful cursor replies. Forward them through the existing privacy-filtered page event, without changing captured data or control decisions.

**Tech Stack:** Python 3.14.8, Playwright 1.64.1, JavaScript performance.now, pytest and hosted Windows Edge fixtures.

**Spec:** [L3-B renderer timing prerequisite](../specs/2026-11-01-l3-renderer-diagnostics-design.md).

## Global Constraints

- Keep <=250 L3-B, generic <=100 and the original 180-second cooperative deadline.
- Keep owner/Document/URL/full-state checks, Stop, max_pages, one inspected Next and PARTIAL.
- Preserve rows, duplicates, footer, source totals, packed data and output metadata.
- No new requests, native admission, catalog/cache access, label normalization or PDF/MPN changes.
- Product imports, tests, browser fixtures and packages execute only on GitHub runners.
- Design/plan review precedes implementation; the user approved both on 1 November 2026.

## Review Focus

- A slow dispatch must not be reported as synchronous renderer work.
- An invalid or absent timing must not alter accepted rows or capture status.
- Refused/expired/cancelled RPCs must not become accepted timing events or repeat a click.
- Generic non-cursor callers and legacy event readers must retain their existing shapes.
- New numeric fields must not admit secrets, non-finite numbers, bools or coercible objects.

---

### Task 1: Optional cursor timings with privacy-safe forwarding

**Files:**
- Modify: `coretax_browser.py` cursor expressions and accepted `table.page_timing` event.
- Modify: `spt_desktop/diagnostics.py` numeric field allowlist.
- Test: `tests/test_corporate_dom_cursor.py`.
- Test: `tests/test_diagnostics.py`.
- Modify: `AGENTS.md` to record the actual diagnostic scope and interpretation.

**Interfaces:**
- Consumes: `TABLE_CURSOR_ADVANCE_JS(cursor, options)` and `TABLE_VERIFIED_JS(owner, cursor)` existing successful result dictionaries; existing wall timers.
- Produces: optional internal `renderer_ms` only on successful cursor replies; optional event fields `table_advance_renderer_ms` and `table_dom_renderer_ms`.
- Preserves: every other status/result shape and the JSON decoded capture data.

- [x] **Write failing hosted tests.** Add `test_cursor_reports_renderer_duration_separately_from_pre_rpc_delay` using the real browser fixture plus a controlled host delay at the existing RPC boundary. Assert unchanged 601 ordered rows/three pages/two moves, the two finite nonnegative renderer durations on advanced events, and the artificial wall-only delay remaining outside renderer duration.
- [x] **Write the synchronous-work test.** Add `test_cursor_renderer_duration_includes_synchronous_click_work` with a synthetic inspected Next handler that burns a bounded 30 ms before its ordinary draw. Require renderer advance duration >=30 ms, unchanged moves/rows and the existing 180-second deadline.
- [x] **Write the omission/privacy tests.** Assert the two fields follow the exact current numeric bounds/rounding, dropping None, strings, bools, NaN, infinities, negatives, above-bound values and coercible objects without invoking coercion. Capture data and status must remain unchanged when timings are missing.
- [x] **Verify RED on GitHub.** Push tests-only head and inspect hosted failure evidence; failures must concern the missing optional timings, while baseline capture/refusal tests remain intact. No local product execution.
- [x] **Implement minimal optional timings.** Measure only within the existing two synchronous cursor functions. Add the internal field only after the existing successful branch has produced its result. Keep original decisions and exceptions unchanged, and forward optional values only with accepted advanced pages.
- [x] **Update AGENTS.md.** State that renderer durations are a diagnostic subset of wall timings; no queue-only inference, new admission, capture completion or measured speedup follows.
- [ ] **Verify GREEN on GitHub.** Run the new tests plus existing cursor, page-size, owner/atomic-snapshot, Stop, timeout, diagnostic privacy and full required CI checks. Confirm unchanged projection expressions and generic path by source diff and hosted regressions.
- [ ] **Commit the reviewed final implementation.** Include only synthetic tests/source/docs; no live providers, captures, profiles or private evidence.

### Task 2: Review, merge and diagnostic-package delivery

**Files:**
- Update this plan's checkboxes and an evidence report with verified run/head/tree identities.

**Interfaces:**
- Consumes: Task 1 exact-head hosted GREEN and a fresh whole-branch review.
- Produces: reviewed PR, verified merged-main diagnostic package in Downloads, and a precise request for the next operator-run live test.

- [ ] Refresh origin/main, inspect preceding other-session merges and interactions with the candidate; preserve PR163 MPN changes.
- [ ] Complete a fresh whole-branch review; resolve findings and rerun exact-head evidence after any code change.
- [ ] Create/attach the PR and merge only after required exact-head CI and review pass.
- [ ] Match the main push run/attempt/artifact to the actual merged commit, inspect manifests and source/frozen evidence, and verify complete package hashes after copying to both authorized Downloads folders. Preserve older packages and delete only this merged branch.
- [ ] Report that this is a diagnostic prerequisite, not a proved timeout fix. Ask for the next authorized operator-run scrape, then analyze its renderer/wall timings before another behavior change.

## Self-review

All proposed code belongs to one small instrumentation unit. Review-focus cases
are pinned above. No task changes page-size policy, readiness, identity, requests,
mapping or publication. Hosted instrumentation and package tests cannot establish
live worker performance or full Coretax acceptance. Execution recommendation:
native implementation with a fresh whole-branch reviewer after plan review.
