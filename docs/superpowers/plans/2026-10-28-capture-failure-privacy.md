# Capture failure privacy implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Repair PR132 without losing safe diagnostics or exposing failure text.

**Architecture:** Reuse the existing diagnostic sanitizer and capture boundaries.
Map failure types to three fixed checkpoint messages; logging remains optional.

**Tech Stack:** CPython 3.14.8 GIL, Playwright, pytest, existing locked Windows CI.

**Spec:** docs/superpowers/specs/2026-10-28-capture-failure-privacy.md

## Global constraints

- Preserve Stop, source/filter identity, PARTIAL and PDF gates.
- No taxpayer data, exception text, arbitrary class names or new dependencies.
- All product regression execution is GitHub-runner-only.
- Preserve PR132's independent workbook differential styles and current main.

## Review focus

- Unknown dynamically named exceptions must remain Error in serialized logs.
- Logging OFF and unavailable home/workspace must not change CLI outcome.
- Timeout probe failure must retain the original timeout category and recovery.
- Filter/catalog refusals must remain PARTIAL with no unauthorized actions.
- Cancellation must propagate without becoming a partial capture.

### Task 1: Repair capture and diagnostic failure boundaries

**Files:** coretax_browser.py, coretax_json_capture.py,
spt_desktop/diagnostics.py, AGENTS.md; tests/test_capture_failure_privacy.py,
tests/test_capture_exception_safety.py and existing financial/panel/inventory tests.

**Interfaces:** capture_detail and collect_inventory keep their return shapes.
DiagnosticLog.record(error=exception) retains the existing closed type/frame
projection. Fixed failure messages replace arbitrary exception strings.

- [ ] Add real synthetic capture/privacy regressions: RuntimeError with private
  message, unknown private class, TimeoutError with private message, and Stop.
  Assert PARTIAL, later appendix recovery, no private message/class in logs or
  error records, safe exception type/owned frame, and no financial request.
- [ ] Observe runner RED against unchanged PR132 production. Existing run
  40647941127 already proves two diagnostic-root and twelve capture-contract
  failures; new tests must independently expose the lost sanitized error proof.
- [ ] Restore best-effort diagnostic root fallback and sanitized error records;
  use a single type-based fixed-message helper at existing capture catches.
  Remove unused driver import and unbounded error_type field. Update policy
  comments/AGENTS and test assertions for the deliberate fixed-message contract.
- [ ] Verify focused Windows GREEN, then full exact-head CI/inventories/package.
- [ ] Get one fresh whole-branch source review; fix Important findings with
  runner RED/GREEN, inspect review threads and latest preceding merged PR.
- [ ] Merge only the verified current head, verify actual main-push package,
  and deliver the complete versioned package to Downloads.

MPN ambiguous-parent investigation is a separate subsequent behavior boundary;
it must not be hidden inside this diagnostic repair.
