# Submitted Masa listing JSON Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Execute inline under the user's existing autonomous authorization.

**Goal:** Preserve native submitted metadata for supported mixed Masa/corporate pages.

**Architecture:** Extend the current six-caption binding in `coretax_browser.py`; retain `adapt_inventory_page` as the safety and rendering gate. Unknown pages retain whole-page DOM fallback.

**Tech Stack:** Python, Playwright, pytest; existing GitHub Actions only.

**Spec:** `docs/superpowers/specs/2026-10-26-masa-listing-json-design.md`

## Global Constraints

- All product execution stays on GitHub runners.
- No private record is a test fixture.
- Retain original bytes, source fields, record IDs, literal model/period and pagination.
- Do not modify detail projectors, catalog access, request permissions, export layout, publication guards, CI, dependencies, resources or worker packaging.

## Review Focus

- An unsupported row must not hide a later known identity/period contradiction.
- Same-model reordered families must be rejected, not rebound by position alone.
- Literal period codes must retain leading zeroes and remain scoped by the existing inventory filter.
- Embedded controls must not contribute a value/checked state to reference captions.
- One unsupported page must not discard native evidence from other supported pages.

### Task 1: Supported mixed-page binding

**Files:** modify `coretax_browser.py`, extend `tests/test_json_inventory.py`, add `tests/test_masa_listing_json.py`, update `AGENTS.md`.

**Interfaces:** consume the existing bound response and six-column reference result; preserve `_inventory_metadata`'s signature and adapter result. No new worker module.

- [ ] Write synthetic real-browser tests for the four known pairs, twelve months, literal/caption periods, mixed pagination, identity/caption contradictions, unknown/null/range fallback, control exclusion and Stop.
- [ ] Commit tests/design/plan only; open draft PR and inspect runner RED. New supported Masa cases must fail for missing admission, not fixture or collection errors.
- [ ] Replace the corporate-only admission with reviewed pair/period validation. Scan all reference rows for contradictions before returning an unsupported result; preserve all existing safety, custody and rendering behavior.
- [ ] Remove controls from reference clones without inspecting their values; refuse body spans/layout ambiguity.
- [ ] Record the exact supported boundary in `AGENTS.md` and commit implementation.
- [ ] Inspect runner GREEN for the new suite, complete Windows/portable regression suites and unchanged packaging gates.

### Task 2: Review, integration and delivery

**Files:** evidence report under `docs/superpowers/reports/`; private audit stays outside Git.

**Interfaces:** consumes exact head/tree/run/artifact evidence from Task 1; produces a reviewed PR and verified latest-main package.

- [ ] Request one fresh whole-branch review; address material findings with tests.
- [ ] Review the preceding other-session merge and latest main, then satisfy exact latest-base CI/ruleset gates and merge under existing authorization.
- [ ] Read back the exact main build/package and deliver the complete versioned package to Downloads, verifying hashes and identity without local execution.
- [ ] Report the job audit, terminal ERROR distinction, implemented listing scope, remaining unsupported detail branches and runner-only acceptance limits.
