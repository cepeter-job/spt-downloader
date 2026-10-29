# Tooling ownership implementation plan

> **For agentic workers:** Use superpowers:executing-plans for this bounded task.

**Goal:** Finish issue #130 item 2 by removing incomplete coverage duplication.
**Architecture:** `.coveragerc` owns coverage; `pyproject.toml` owns pytest
defaults/project metadata; `ruff.toml` owns lint. No product or CI gate changes.
**Tech Stack:** Python 3.14.8, pinned coverage 7.17.0, pytest and Ruff toolchain.
**Spec:** `docs/superpowers/specs/2026-10-29-tooling-ownership-design.md`.

## Global constraints

- Product imports, tests and tool execution run only on GitHub runners.
- Keep `${RUNNER_TEMP?}/.coverage-portable`, branch policy and fail_under=0.
- Preserve full Windows/portable/build/security gates and hash-locked tools.
- Preserve other sessions' changes and the primary checkout/private artifacts.

## Review focus

Review missing RUNNER_TEMP refusal, coverage auto-discovery versus explicit
selection, pytest defaults, Ruff hook/config compatibility, and unrelated
project metadata. The runner probe exercises the first two; semantic TOML and
unchanged-file hashes plus existing suites cover the remaining boundaries.

## Task 1: One owner per tool

- [ ] Remove only `[tool.coverage.*]` from `pyproject.toml`; document ownership
  in AGENTS.md, docs/pengembangan.md and the quality audit follow-up.
- [ ] Run a branch-only diagnostic probe on a GitHub runner against the original
  base and candidate. Expected: identical effective coverage policy/data path,
  explicit missing-environment refusal, unchanged noncoverage TOML and lint/CI
  bytes; historical TOML lacks the runner data path, while candidate TOML has no
  repository coverage policy and selects upstream defaults when explicitly used.
- [ ] Verify exact-head full Windows/portable CI, inventory union and packaged
  artifact evidence. Expected: no failures/errors/skips or lost cases.
- [ ] Obtain one fresh whole-branch review; handle material findings and review
  preceding other-session merges/current main before guarded integration.
- [ ] Merge, update issue130 item2 and related issue134 configuration checkbox,
  and deliver the verified main artifact while retaining only the latest
  application package in Downloads under the user's cleanup preference.

Configuration removal is deliberately verified by real runner parity evidence
and existing behavior suites rather than a new permanent source-text test.
