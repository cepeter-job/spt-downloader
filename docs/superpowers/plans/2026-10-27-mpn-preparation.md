# MPN Preparation Repair Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepare the actual Accounting UI in the correct order under positive Document ownership.

**Architecture:** Keep Accounting separate. Retain a value-free Document handle and attempt token in its observer. Use original inspected controls and responses with bounded readiness waits in AccountingUI.

**Tech Stack:** Python, Playwright, pytest, existing GitHub Windows/portable workflows.

**Spec:** `docs/superpowers/specs/2026-10-27-mpn-preparation.md`

## Global Constraints

- The direct user local exception covers diagnosis/validation of this same job only.
- Runner-only regression tests/builds; no private records, credentials or URLs in Git/diagnostics.
- Keep route/source/identity contradictions fatal, source pins and empty-inventory proof intact.
- Preserve latest main PR129 corporate DOM pagination and all prior outputs/checkpoints.

## Review Focus

- Same URL reloads must fail even during initial Document acquisition.
- Reset/close and RPC-pumped refusals cannot attach a stale handle to a new attempt.
- Stop/source/observer failure interrupts readiness before another action.
- First-search grid absence is normal; missing or duplicate mounted grids remain unsupported.
- Delayed options require waiting, never another trigger click or guessed selection.
- Session callbacks are accepted only before capture; never reset a rejected capture into success.

### Task 1: Owned preparation regression and repair

**Files:** `coretax_mpn_browser.py`, `coretax_mpn_ui.py`, `tests/test_mpn_browser.py`, `tests/test_mpn_document_readiness.py`, `tests/test_mpn_capture_browser.py`, `AGENTS.md`.

- [ ] Add protocol and real synthetic browser regressions and read runner RED.
- [ ] Adapt retained Document/attempt custody; refuse second document requests and sticky state before UI actions.
- [ ] Add separate bounded session preparation using only the observed roots/auth-callback and selected ledger; start fresh navigation/request custody afterward.
- [ ] Correct Cari/grid ordering and bounded readiness with unchanged source/filter gates.
- [ ] Read runner GREEN, exact test inventories/package proof; independently review final branch.
- [ ] Validate the same actual job in a new private folder under the granted local exception.
- [ ] Review preceding other-session merge/latest main before merging; deliver exact merged-main package with verified hashes.
