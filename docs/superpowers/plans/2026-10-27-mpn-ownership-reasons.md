# MPN Ownership Reasons Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Identify the precise failed MPN source ownership check without changing acceptance.

**Architecture:** Retain the existing first-refusal event and six guards. Add one closed enum reason, preserving short-circuit order and sticky fatal behavior.

**Tech Stack:** Python, pytest, existing GitHub Windows/portable workflows.

**Spec:** `docs/superpowers/specs/2026-10-27-mpn-ownership-reasons.md`

## Global Constraints

- Product execution, tests and builds remain GitHub-runner-only.
- No private captured data or request values in source, logs, tests or CI artifacts.
- No new source pins, requests, browser privileges or weakened guards.
- Preserve existing private captures and the original job's ERROR/PARTIAL state.

## Review Focus

- Each of the six predicates remains fatal before any response/body access.
- Multiple contradictions preserve the first check and first refusal event.
- Non-ownership failures do not inherit a stale reason.
- Malformed diagnostic values cannot stringify or disclose private material.
- Supported request byte proof and genuine empty-inventory proof remain unchanged.

### Task 1: Bounded refusal reason

**Files:** `coretax_mpn_ui.py`, `spt_desktop/diagnostics.py`, `AGENTS.md`, `tests/test_mpn_source_custody.py`, `tests/test_diagnostics.py`.

**Interface:** Optional fixed `mpn_ownership_reason` on the existing `mpn.source_rejected` event.

- [ ] Add six predicate-specific synthetic regressions, precedence/first-refusal cases and diagnostic privacy cases; read runner RED evidence.
- [ ] Add the closed reason enum and preserve all guards/evaluation order; document the supported boundary.
- [ ] Read exact-head runner GREEN, test inventory and package provenance.
- [ ] Obtain one fresh whole-branch review. Review latest main and preceding other-session changes before any merge.
- [ ] Deliver exact-build package and state explicitly that live root-cause resolution remains unverified until a new authorized run identifies the failed predicate.
