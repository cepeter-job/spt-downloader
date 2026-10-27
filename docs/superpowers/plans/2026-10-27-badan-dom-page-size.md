# Corporate DOM page-size implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the observed corporate L3-B DOM fallback pagination cost.

**Architecture:** Preserve the shared DOM paginator and its completeness checks.
Supply a larger bounded limit only after existing corporate structure proof.

**Tech Stack:** Python, Playwright/Edge, pytest, existing GitHub Windows CI.

**Spec:** `docs/superpowers/specs/2026-10-27-badan-dom-page-size-design.md`

## Global Constraints

- Only selected PPh Badan, exact L3 and reviewed L3-B ownership may use 500.
- Choose actual visible options; all other callers retain 100.
- Preserve Stop, row/duplicate/footer/count proofs and existing deadlines.
- No MPN/PDF/native eligibility/layout/dependency/CI policy changes.
- Product execution is GitHub-runner-only; commit synthetic evidence only.

## Review Focus

- Missing or foreign form/component/group must retain the 100 cap.
- A displayed size above 500 must never be chosen by this branch.
- Missing 500 must select an available smaller option; selected maximum avoids reload.
- Page caps, Stop and source-count mismatches must never become successful capture.
- Other tax types and ordinary capture_table callers must keep their existing behavior.

### Task 1: Bounded L3-B optimization

**Files:** `coretax_browser.py`, `tests/test_corporate_dom_page_size.py`, `AGENTS.md`.

**Interfaces:** Add keyword-only `max_page_size=100` to `maximize_page_size`
and `capture_table`. In `capture_detail`, pass 500 only when the selected
corporate record and existing exact L3-B structure match the spec; otherwise 100.
Return schemas and all native admission contracts remain unchanged.

- [ ] Add real synthetic Edge regression tests for 4,654 rows, all review-focus
  conditions, unchanged raw values/footer, and independent missing-PDF PARTIAL.
- [ ] Push tests first and observe the intended failure in existing Windows CI.
- [ ] Implement the bounded option policy and document its boundary in AGENTS.md.
- [ ] Run full unchanged CI on the exact candidate; inspect collection/outcomes.
- [ ] Obtain one fresh whole-branch review and resolve substantive findings.
- [ ] Review latest main and preceding merged PR interactions before integration.

Local execution restriction supersedes generic skill test commands. Keep a
private evidence ledger outside tracked files, linking exact commits/runs. The
operator's bounded bug-fix instruction and pinned source evidence determine this
implementation; no new product-design approval round is required.
