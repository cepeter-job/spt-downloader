# MPN Transaction Date Clear Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one fresh whole-branch review before integration.

**Goal:** Remove the inspected initial TransactionDate filter before accepting MPN inventory.

**Architecture:** Keep AccountingUI.open's two Searches and strict source-query predicate. Add one owned date-clear preparation action, preserving the legacy period branch and all identity/Stop/source gates.

**Tech Stack:** Python3.14.8, Playwright1.64.1, existing hosted Windows CI.

**Spec:** [Owned date-clear boundary](../specs/2026-11-02-mpn-transaction-date-design.md).

## Global constraints and review focus

- Product tests/imports/build/EXE run only on GitHub runners; local source/AST/Git/JSON/hash inspection only.
- Keep45-second preparation, maximum2 Searches, unchanged unfiltered predicate and PARTIAL gates.
- Never persist real scope, captured source/request material or business values.
- Test duplicate owner with one button, foreign lookalike, delayed/disabled action,
  stale immediate response and callback-pumped Stop/source failures.

## Task 1: Reproduce and repair owned date preparation

**Files:** coretax_mpn_ui.py; coretax_mpn_browser.py;
tests/test_mpn_capture_browser.py; new tests/test_mpn_transaction_date_clear.py,
tests/test_mpn_date_review.py and tests/test_mpn_action_custody.py; AGENTS.md.

**Interface:** AccountingUI._clear_initial_transaction_date(snapshot, grid) returns
True only after its one actual owned click and owned clear-response wait; False for an inapplicable source rule
or absent legacy calendar. Unsupported present structure raises MpnUnsupported.
AccountingUI.open invokes it only between its first and second Search.

- [x] Extend the synthetic portal with the actual date-container/control shape and sticky dates that only the right clear action removes; retain all existing fixture defaults.
- [x] Add whole-capture tests for complete/empty success, wrong/missing/duplicate/hidden/disabled controls, unchanged filters and one-clear/two-Search custody.
- [x] Commit tests-only and read hosted RED, including the expected date-clear failure.
- [x] Implement the minimal source-query/owned-control binding and document its supported boundary in AGENTS.md.
- [ ] Run hosted GREEN/full CI; reconcile exact SHA/tree/run/attempt and retained baseline inventory.
- [x] Commit verified implementation and record evidence (final focused GREEN52 cases; full CI pending).
- [x] Reproduce all four review findings with six failing hosted regressions.
- [ ] Verify repaired action-request custody, table ownership, bounded metadata
  and fatal click-exception reconciliation on hosted focused and full CI.

## Task 2: Review, integrate and validate delivery

- [x] Fresh whole-branch review; handle findings with behavior tests (four findings, corrected RED6/GREEN52, targeted source follow-up closed all four).
- [ ] Review latest main/preceding other-session merges and revalidate interactions.
- [ ] Integrate after exact-head checks; verify exact merged-main package and deliver it.
- [ ] Operator-run build-matched live test: strict unfiltered request and complete original inventory/detail evidence, or explicit remaining failure. Do not mark live acceptance complete from synthetic proof.
