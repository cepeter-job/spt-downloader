# CLI failure recovery implementation plan

> Use superpowers:executing-plans inline; obtain a fresh whole-branch review.

**Goal:** Start issue134 with reliable CLI failure/Stop outcomes and checkpoints.
**Architecture:** Preserve save_output and capture modules. Put owned resources
in an ExitStack with active-error preservation; checkpoint-only failure recovery.
**Tech Stack:** CPython3.14.8, pytest, existing atomic checkpoint and diagnostics.
**Spec:** ../specs/2026-10-28-cli-failure-recovery.md

## Global constraints

- All product execution/tests/builds on GitHub runners only.
- Preserve literal scope, PARTIAL, privacy, Stop, ownership and publication gates.
- No changes to required CI gates, locks, worker allowlist or MPN verification.
- Review preceding other-session PR137 and latest main before integration.

## Review focus

- Startup fails before run/context/page exist: error1 with owned cleanup only.
- Existing run.json and workbook set: failed recovery leaves old bytes intact.
- Second interruption during teardown: Stop must not become ordinary error1.
- Closed or reused pages/contexts: no external context close, no repeated action.
- Failure during cleanup after normal export: never report successful CLI exit.

## Task 1: Reproduce and fix CLI failure recovery

Files: coretax.py; tests/test_cli_failure_recovery.py; AGENTS.md.
Interfaces: _main(argv) keeps existing integer exit codes; save_output unchanged.

- [ ] Add behavior tests of _main with synthetic I/O/browser boundaries and real
  checkpoint bytes; expected exit1/130, no error-handler publication, complete=False,
  preserved sentinels, safe diagnostics and every owned resource cleanup.
- [ ] Run tests on a temporary branch-only diagnostic workflow; verify failures
  caused by current save_output/cleanup behavior before writing production code.
- [ ] Add _cli_cleanup, page-close and failure-checkpoint helpers in coretax.py;
  move live execution under their ownership without changing successful export.
- [ ] Run focused runner GREEN and existing output/MPN-flow tests; add the actual
  CLI failure contract to AGENTS.md and operator troubleshooting documentation.
- [ ] Remove temporary diagnostic workflow, run full unmodified PR CI/package,
  review original response/MPN/publication interactions and obtain fresh review.
- [ ] Link verified PR/results to issue134; keep the issue open for later phases.

## Task 2: Record corrected audit recommendations

- [ ] Add a short source-linked follow-up to the audit documentation, preserving
  original historical evidence. Distinguish eager/lazy/package imports, remaining
  recovery dependencies, version fallback, monkeypatch ownership and unmeasured
  timing. Do not claim the absent attachment docs were edited or merged.
- [ ] Index it in docs/README.md and identify deferred issue134 work explicitly.

No claim of live/Excel acceptance, no issue-wide closure and no unrelated cleanup.
