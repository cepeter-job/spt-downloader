# JSON L3 and MPN Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Remove the source-proven L3 layout blocker and bounded DOM/MPN action overhead.
**Architecture:** Extend only the existing observers/cursor/action helper. Retain all original capture and publication gates.
**Tech Stack:** Python, Playwright, synthetic Edge fixtures, GitHub-hosted Windows CI.
**Spec:** docs/superpowers/specs/2026-11-03-json-l3-mpn-repair.md

## Global Constraints

- Keep the 250-row DOM cap, 180-second table budget and native ten-row requests.
- No DOM business input/checked/body/footer values in native observation.
- Stop and sticky safety failures outrank timeouts; actual clicks occur once.
- Product execution is runner-only. No private capture data enters Git or artifacts.
- Preserve latest main PR175 selection semantics and PR174 driver trust.

## Review Focus

- Changed standalone ancestry or controls must refuse without reading values.
- A layout change between observer passes must not retain native eligibility.
- Long loading overlays must allow Stop and cannot refresh the browser deadline.
- Clear-date dispatch after a successful trial must still check current ownership.
- A late response or snapshot cannot certify rows or empty MPN inventory.

### Task 1: Source-proven third L3 table

**Files:** coretax_corporate.py, coretax_corporate_projection.py, tests/test_json_l3_mpn_repair.py, AGENTS.md.
**Interfaces:** existing _observe_l3 projection; optional standalone_layout='overseas-controls-v1' marker, validated by _apply_l3.

- [x] Add synthetic actual-shaped third-table fixture and negative ownership/header/control/extra variants; assert native eligibility, replay and no business reads.
- [x] Watch the positive test fail on the unmodified baseline on a hosted runner.
- [x] Validate exact standalone structure on both passes and its optional replay marker; preserve two-table compatibility.
- [x] Run focused L3 observer/native/projection/fallback tests and commit the bounded fix.

### Task 2: One-shot Clear date dispatch budget

**Files:** coretax_mpn_ui.py, tests/test_json_l3_mpn_repair.py.
**Interfaces:** _click_ready(clear, actual_timeout_ms=5000, capture_requests=True), still bounded by preparation_deadline.

- [x] Add a dispatch-delay regression that requires more than1000ms but only one actual click; retain fatal/Stop and remaining-deadline cases.
- [x] Observe the delayed-click regression fail on a hosted runner.
- [x] Use the existing5000ms action budget for this inspected action only.
- [x] Run MPN transaction-date, review and capture browser tests and commit.

### Task 3: Owned DOM wait/snapshot RPC

**Files:** coretax_browser.py, tests/test_json_l3_mpn_repair.py, AGENTS.md.
**Interfaces:** TABLE_VERIFIED_JS may return pending only for a cursor; generic replies are unchanged.

- [x] Test that advanced250-cap pages use no separate wait_idle RPC while preserving real loading/settling, rows and one click per page; cover pending/expiry/Stop/owner replacement.
- [x] Observe the no-separate-RPC test fail on a hosted runner.
- [ ] Combine bounded idle waits with the original same-owner snapshot and retain pending attempts within the unchanged deadline.
- [ ] Run cursor/page-size/timing/identity regressions and full exact-head CI.
- [ ] Request one independent whole-branch review, address important findings, review preceding other-session merges, then merge and verify merged-main CI.
