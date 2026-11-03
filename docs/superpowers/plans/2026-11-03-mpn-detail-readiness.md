# MPN Detail Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans task-by-task. Steps use checkbox (`- [ ]`) tracking.

**Goal:** Diagnose the MPN detail readiness refusal without changing capture eligibility.

**Architecture:** Reuse existing readiness observations, add closed diagnostic fields, and retain all existing control flow and deadlines.

**Tech Stack:** Python3.14.8, Playwright, synthetic Edge fixtures and GitHub-hosted CI.

**Spec:** `docs/superpowers/specs/2026-11-03-mpn-detail-readiness-design.md`.

## Global Constraints

- Product imports, tests, fixtures and builds run only on GitHub runners.
- No selector, deadline, action, request, source pin, TLS, privacy or publication relaxation.
- Only fixed categories and bounded numeric timing; no new DOM reads for diagnostics.

## Review Focus

- A visible final observation may still miss the shared deadline: preserve refusal.
- Pending Document identity must not acquire a new DOM probe for logging.
- Callback-pumped Stop/safety must outrank readiness diagnostics.
- Unknown field values and numeric subclasses must not be coerced into logs.
- JSON-first must retain the same dialog/grid ownership gate and PARTIAL result.

### Task1: Diagnostic evidence and regression coverage

**Files:** `tests/test_mpn_detail_readiness.py`, `tests/test_mpn_detail_readiness_browser.py`, `coretax_mpn_ui.py`, `spt_desktop/diagnostics.py`.

**Interfaces:** Existing `_ready_one(selector, *, deadline=None)` signature remains unchanged; a fixed event describes only its own detail-readiness ambiguity/deadline refusals.

- [ ] Write unit tests for refusal state, stage, timing, privacy and unchanged reads/Stop; add real synthetic capture regressions for missing/hidden grid ancestry in both source modes.
- [ ] Use an isolated temporary runner workflow to observe the expected missing-event RED on unmodified production.
- [ ] Add the finite event/schema and emit from already observed state at the original refusal points; identify the three existing detail waits.
- [ ] Observe hosted GREEN, including existing MPN custody, reference and diagnostics tests.

### Task2: Review, full validation and merge

**Files:** `AGENTS.md`, `docs/diagnostik.md`, verification report; remove temporary workflow.

- [ ] Document supported diagnostic boundaries and record runner evidence.
- [ ] Obtain independent whole-branch review and resolve material findings with regressions.
- [ ] Run unchanged full PR CI; inspect exact commit/tree/run/attempt checks and review threads.
- [ ] Refresh latest main and review the preceding other-session merged PR and its affected functions/tests/contracts.
- [ ] Merge the reviewed tested tree and verify the resulting main identity/checks. Report synthetic versus live limits.

## Execution rulings

- The user requested continuation through merge after the diagnostic next step; execute inline without another design or merge permission round.
- The current evidence supports diagnostics only. Do not claim a live scraper fix or modify unproved readiness behavior.
