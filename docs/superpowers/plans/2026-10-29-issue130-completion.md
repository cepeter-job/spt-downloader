# Issue 130 completion implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, with one fresh whole-branch reviewer per focused PR.

**Goal:** Deliver all seven remaining issue 130 workstreams with repeatable evidence.
**Architecture:** Keep production ownership intact. Separate source maintenance,
locked static gates and representative coverage integration into focused PRs.
**Tech Stack:** CPython 3.14.8, pinned uv/Ruff/coverage, pinned mypy and Bandit.
**Spec:** ../specs/2026-10-29-issue130-completion.md

## Global constraints

- Product execution only on GitHub runners; synthetic fixtures only.
- Preserve Stop, PARTIAL, privacy, custody, source pins and worker allowlist.
- Retain all existing full Windows/portable/build/security gates and test inventory.
- Recheck current main, preceding other-session PRs and exact-head review/CI before merging.

## Review focus

- Arbitrary exception messages and hostile string conversion cannot enter public/checkpoint diagnostics.
- Recovery/finally faults and Stop preserve original outcomes and last verified bytes.
- AST metrics distinguish nested scopes and actual production scope; no stale totals.
- Static-gate exclusions are narrow and do not mask new instances of accepted risks.
- Coverage cannot pass with a missing shard, missing module or portable-only evidence.

### Task 1: Integrate existing CLI recovery

- [ ] Preserve #139 while updating #138 to current main; independently review its changed functions and tests.
- [ ] Require fresh full CI on the integrated head and verify merge tree before merging.

### Task 2: Source safety and maintainability

- [ ] Inventory catches, public API, complexity and skip sites with exact definitions/revision.
- [ ] Add a raw-error/Stop synthetic regression first; observe RED on a runner.
- [ ] Fix demonstrated detail-error disclosure, retain justified fail-closed containment.
- [ ] Extract a cohesive complex boundary preserving API/monkeypatch semantics and existing negative tests.
- [ ] Improve substantial public API contracts; replace obsolete runtime-absence skip with ordinary RED behavior.
- [ ] Add docs/test-graveyard.md with owner/removal criteria for every remaining site.
- [ ] Require focused GREEN and complete unchanged Windows inventory, fresh review and full CI before merge.

### Task 3: Locked typing and security gates

- [ ] Run pinned mypy/Bandit baselines on runners; retain findings and measured overhead.
- [ ] Add strict useful stdlib module typing and behavior-neutral annotations; no blanket Any/suppression.
- [ ] Triage every production Bandit result; narrow source-local exceptions or exact reviewed baseline entries.
- [ ] Add hash-locked quality tooling and CI gates; prove new unsafe code/type failures are rejected.
- [ ] Verify lock freshness, full tests/build, fresh review and actual main integration.

### Task 4: Representative coverage and closure

Use `scripts.coverage_ratchet.evaluate(report, policy, changed=None)` for exact
integer line/branch/module/diff floors and fail closed on missing/malformed data.
`check_windows_inputs` delegates to the existing complete inventory validator;
`data_files` requires exact serial or two-shard source slots. CI combines only
those held run/commit/attempt-bound Windows artifacts before package/build,
with the same `.coveragerc` source/branch/omit policy. Parent Windows execution
covers real native/Tk/Edge fixtures and in-process worker logic; isolated managed
worker/bootstrap subprocesses and browser JavaScript are explicitly unmeasured.
Choose conservative floors only after the representative runner baseline.

- [ ] Instrument both Windows shards and retain per-shard branch data/reports without relaxing inventory gates.
- [ ] Combine only the complete Windows union; establish measured module line/branch floors.
- [ ] Add gate behavior tests first for missing shard/module, malformed report and regression; observe RED then GREEN on runners.
- [ ] Document enumerated critical security behaviors and their actual synthetic tests; distinguish line/branch/module/diff metrics.
- [ ] Review/merge exact tested tree, verify final main package/bootstrap/test union and copy latest artifact set to Downloads.
- [ ] Update issue 130 checklist/closure only from final evidence; preserve explicit residual limitations.
