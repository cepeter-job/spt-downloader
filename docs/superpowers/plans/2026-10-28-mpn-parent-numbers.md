# Accounting parent numeric binding implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Resolve the observed repeated-parent blocker with exact visible integer proof.

**Architecture:** Add one pure numeric binding helper in coretax_mpn.py and call
it only from the existing ambiguous seven-column/reference branch in
AccountingUI._bind_header. Keep the original action and all custody checks.

**Tech Stack:** CPython 3.14.8 GIL, Decimal, Playwright, locked Windows pytest CI.

**Spec:** docs/superpowers/specs/2026-10-28-mpn-parent-numbers.md

## Global constraints

- Original source pins, source bytes/lexemes and output schema unchanged.
- Only five inspected number cells, exact integral values within fifteen digits.
- All matching peers must reconcile; same numeric tuples remain unsupported.
- Known contradictions stay fatal, Stop stays cancellation, limits stay PARTIAL.
- Synthetic tests/builds run only on GitHub runners; preserve original private job.

## Review focus

- Fractional, unsafe-precision, numeric-string and missing values refuse actions.
- Equivalent numeric lexemes and signed zero cannot manufacture uniqueness.
- Changed or reordered visible amounts are fatal before a detail request.
- Legacy unique captions do not acquire a new numeric dependency.
- Callback-pumped refusal/Stop retains existing final action fences.

### Task 1: Add bounded parent numeric identity

**Files:** coretax_mpn.py, coretax_mpn_ui.py, AGENTS.md,
tests/test_mpn_parent_numbers.py, tests/test_mpn_capture_browser.py.

**Interfaces:** parent_numeric_binding(row, header) returns five Decimal values
or None for unsupported proof, raises MpnSafetyError for a recognized mismatch.
AccountingUI._bind_header consumes this only for still-repeated reference peers.

- [ ] Add pure tests for literal safe integers/zeros/negative values, unsupported
  fractions/strings/precision/missing/malformed display and fatal mismatches.
- [ ] Add real synthetic full collector tests: same metadata/reference with
  distinct integral amounts completes; equal/rounded/unsafe amounts stays
  PARTIAL with no action; changed/reordered visible values remain fatal.
- [ ] Run unchanged production with new tests on a runner and observe RED.
- [ ] Implement the helper and bounded peer binding, retain all legacy gates,
  and document the actual narrow boundary in AGENTS.md.
- [ ] Verify focused GREEN and full exact-head suite/package, get one fresh
  source review and reconcile Important findings with runner RED/GREEN.
- [ ] Review preceding merged PR132 and latest main, merge verified candidate,
  deliver actual main artifact and validate the same private job under the
  existing operator-authorized local exception. Keep any remaining limit or
  unsupported branch explicitly PARTIAL.

### Task 2: Preserve owned detail replies across post-action driver waits

The next live probe proved click completion followed by an implicit navigation
wait timeout. Runner regressions must reproduce the driver boundary and fatal
callback precedence before implementation. Use the existing _observer_call for
the single inspected open/close clicks with no_wait_after=True and for the
hidden-dialog wait. A separately reproduced actual-dispatch timeout increases
only the two inspected detail clicks to five seconds; retain single actions,
the one-second hidden wait, and all explicit ownership/response/
readiness gates. Verify focused GREEN and refresh full exact-head CI, then rerun
the same-job owned diagnostic before claiming live acceptance.
