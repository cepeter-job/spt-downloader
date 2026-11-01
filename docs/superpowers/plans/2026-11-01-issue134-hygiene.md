# Issue 134 Hygiene Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline; request one fresh whole-branch review before merge.

**Goal:** Finish approved metadata policy, reviewed import cleanup, incremental lint and contributor navigation under issue134.

**Architecture:** Keep the EXE/commit/run distribution contract and all runtime owners. Make tooling and export intent explicit without moving guards or helpers.

**Tech Stack:** Python3.14.8, pinned Ruff0.17.2, existing hash-locked CI.

**Spec:** `docs/superpowers/specs/2026-11-01-issue134-hygiene-design.md`.

## Constraints and review focus

- Product/test/browser/Tk/build/EXE execution is GitHub-runner-only.
- Preserve fixture registration, import order and public compatibility names.
- Keep pytest/mypy values, `.coveragerc`, dependency locks, worker resources and build identity unchanged.
- Audit zip/callback findings without modifying source custody or control flow.
- Review exact-head full test inventories and artifact bytes; synthetic proof is not live acceptance.

## Task 1: Tooling and navigation

- [ ] Remove only build-system/project tables from pyproject; preserve tool tables.
- [ ] Document EXE identity policy in CI/release guidance and link it from contributor setup.
- [ ] Add AGENTS navigation and replace only current worker-count claims.

## Task 2: Import/lint audit

- [ ] Read every baseline F401 binding and preserve fixtures/compatibility exports explicitly.
- [ ] Remove reviewed dead imports without Ruff autofix or unrelated formatting.
- [ ] Record all Bugbear dispositions; enable only reviewed incremental rules.
- [ ] Observe candidate F401/current-gate GREEN and actual negative-probe rejections on a runner.

## Task 3: Review and delivery

- [ ] Commit only source/docs/config and create a focused PR.
- [ ] Fresh independent review, then exact-head full CI and artifact readback.
- [ ] Review preceding merged PR/latest main; merge the verified expected head.
- [ ] Reconcile issue134, including stale PR146 integration status and remaining conditional work.

The reversible tooling/doc/import cleanup uses real lint characterization and
existing behavior suites, not new tests that assert configuration source text.
