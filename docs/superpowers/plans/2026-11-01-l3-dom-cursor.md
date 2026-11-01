# Bounded L3-B DOM Cursor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce repeated RPC/state-transfer overhead in L3-B without losing capture checks.

**Architecture:** A private browser handle retains exact page states and the
original owner. The existing Python capture loop keeps data validation and
completion authority; only the 250-cap path uses the cursor.

**Tech Stack:** Python, synchronous Playwright, DOM JavaScript, hosted Edge tests.

**Spec:** `docs/superpowers/specs/2026-11-01-l3-dom-cursor.md`

## Global Constraints

- Preserve CELL_JS, GROUP_JS and TABLE_JS projection semantics.
- Preserve the existing 250 cap, 180-second table deadline and max_pages.
- Preserve Stop, ordered duplicate rows, footer once and source-count checks.
- Preserve original paginator visibility/ownership/disabled checks and one click.
- Refuse replaced owner/Document/URL, ambiguous table and repeated full state.
- Preserve PARTIAL on uncertain action/read, timeout or exhausted budget.
- Retain the generic <=100 path and all native, mapping, PDF and MPN gates.
- Bind a conservative browser-side deadline once; never refresh it per page.
- Run product tests/builds only on GitHub runners; commit synthetic data only.

## Review Focus

- A delayed queued command must not click after the original table budget.
- Repeated full row state must fail even when paginator labels look plausible.
- A detached or replaced owner must never be substituted by a new locator.
- A Stop raised while an RPC pumps callbacks must prevent another action.
- Cursor cleanup must not mask an original cancellation or capture failure.

### Task 1: Retain exact page-state comparisons in the browser

**Files:** Modify `coretax_browser.py`, `AGENTS.md` and existing timeout tests;
create `tests/test_corporate_dom_cursor.py`.

**Interfaces:** Consume the unchanged capture_table signature and original
TABLE_JS/STATE_JS. Produce private cursor init/advance/poll expressions and an
optional cursor argument to TABLE_VERIFIED_JS; default callers retain `{data,state}`.

- [ ] Add real-browser regression proving 601 ordered duplicate/zero rows,
  three verified pages, two clicks and zero raw-state responses on the 250 path.
- [ ] Add repeat-state, delayed-command, ownership, Stop and cleanup cases;
  observe regression RED on a tests-only GitHub head before production edits.
- [ ] Implement the private cursor, shared guarded-click expression and
  conservative once-bound browser deadline; dispose resources on all exits.
- [ ] Preserve timeout injection coverage for both legacy and cursor polls.
- [ ] Update AGENTS.md with the actual narrow supported boundary.
- [ ] Verify hosted full suite, inventory/coverage/quality gates and package.
- [ ] Obtain one fresh whole-branch review; fix material findings with RED/GREEN.
- [ ] Review current main/preceding other-session merges, merge exact green head,
  then verify and deliver the merged-main package to Downloads.

Live acceptance remains separate: report only observed performance, and retain
PARTIAL if the complete selected return cannot finish under the original budget.
