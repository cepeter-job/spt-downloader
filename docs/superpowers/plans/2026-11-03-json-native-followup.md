# JSON native follow-up implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, with
> tests-first verification on GitHub runners.

**Goal:** Remove evidenced JSON native blockers without changing MPN.
**Architecture:** Keep the existing closed transport and whole-record adapter.
Add bounded observer diagnostics and consistent catalog overlap handling;
review the pinned visibility lifecycle before defining any alternate binding.
**Tech Stack:** Python, Playwright synthetic Edge fixtures, GitHub Windows CI.
**Spec:** docs/superpowers/specs/2026-11-03-json-native-followup.md

## Global constraints

- No MPN behavior, CI policy, dependencies or template resource changes.
- No private captures or taxpayer values in Git or runner artifacts.
- Product imports, tests, browser/Tk fixtures and builds run on GitHub runners.
- Preserve source pins, original bytes, identity/Stop, precision and PARTIAL.

## Review focus

Matching overlaps must preserve provenance; contradictory catalogs remain fatal.
Failed secondary responses and omitted sequence declarations cannot be hidden.
Unknown explicit proof markers and coercive flags remain unsupported.
Legacy strict lifecycle proofs remain readable.
Native admission does not grant mapping, PDF or whole-job completion.

### Task 1: L11-A catalogs and refusal diagnostics

**Files:** coretax_corporate.py, coretax_corporate_projection.py,
spt_desktop/diagnostics.py, tests/l11a_observer_fixture.py,
tests/test_corporate_l11a_native.py, tests/test_corporate_l11a_observer.py.
**Interfaces:** `_observe_l11a(..., *, reason_out=None)` fills one fixed reason;
its proof binds each observed admitted catalog route and exact sequence set.

- [ ] Add synthetic matching singleton/pair overlap and fixed-reason tests;
      preserve contradictory overlap and original-byte immutability assertions.
- [ ] Push tests-only PR and read the intended runner failures before code.
- [ ] Bind all reviewed routes; validate exact per-route sequence custody and
      identical typed per-kind snapshots; retain source provenance for overlaps.
- [ ] Implement fixed L11-A refusal reasons and privacy-schema coverage.
- [ ] Read exact-head runner GREEN and update architecture/AGENTS boundaries.

### Task 2: Source-bound lifecycle and observation cost

**Files:** existing corporate observer/projector and their synthetic tests;
docs/superpowers/reports/2026-11-03-json-native-followup.md.
**Interfaces:** Preserve existing proof readers; an alternate branch, if proved,
uses an explicit optional marker and requires the same loaded source pins,
owned enabled form, preceding Induk and current source/lifetime gates.

- [ ] Hash-check the pinned source and record exact parent/Induk flag assignments.
- [ ] Add runner regression tests for the proved branch and contradictory/unknown
      cases, or document the specific missing proof without broadening admission.
- [ ] Implement only the proved branch after intended runner RED.
- [ ] Evaluate early eligibility only after its source/safety ordering is proved;
      preserve final drain and whole-record fallback.
- [ ] Review complete diff, run full exact-tree CI, review intervening main PRs
      before merge and verify the merged package if delivered.
