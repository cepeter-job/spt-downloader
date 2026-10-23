# Pagination, benchmark logging, and JSON-hybrid default implementation plan

**Historical outcome:** delivered through [PR #41](https://github.com/cepeter-job/spt-downloader/pull/41), merge `2b034635b01ac8c139d2c64126ba433ceee6f762`. Head `bee47c70245e9858d56bdbfdf6257ed11eb5d684` passed run `39208386402` with 3,135 Windows cases and 442 overlapping portable cases. Package `12166329252` and its embedded resources were verified. The guarded generic paginator, source/timing diagnostics and desktop default were implemented; the unchecked steps below preserve the original planning state and are not a current missing-feature list. No paired live benchmark was performed by that historical slice. The later [matched PPh21 benchmark](../reports/2026-10-23-json-period-and-benchmark.md) records the selected December 2025 Normal result. Native traversal parity and broader acceptance are tracked by the [approved completion design](../specs/2026-10-23-json-mode-completion-design.md).

> Execute with the existing parent-led workflow and independent source/review checks. Product execution remains GitHub-runner-only.

**Goal:** Repair the generic read-only paginator's unsafe dependence on pointer actionability, expose privacy-safe per-record benchmark attribution, and default new desktop settings to JSON-hybrid without overriding saved DOM.
**Architecture:** Keep existing collectors, custody gates, adapters, fallback and diagnostics. Add bounded read-only paginator handling and scoped timing/enumerated metadata, not a second export path. Preserve low-level/CLI default contracts unless explicitly required by the desktop setting.
**Spec:** User approved timeout repair, benchmark logging and JSON-hybrid default after the diagnostic log audit. Actual timeout root cause on the live page is not established; synthetic regressions must distinguish a supported UI-interception case from unsupported controls.
**Constraints:** No local product imports/tests/fixtures/builds/EXE, live Coretax access, credentials, private data commits, CI edits, automatic merge/install or output overwrite. Preserve source identities, totals, cancellation and PARTIAL semantics.

## Review focus
- Disabled, hidden, ambiguous/nested or detached paginator controls must not trigger an arbitrary action; no-advance remains PARTIAL.
- Stop and fatal source/auth contradictions must remain fatal and observable, not become successful fallback.
- Missing/invalid configuration selects the new default; an explicitly saved DOM choice remains DOM.
- Telemetry must not expose URLs, labels, IDs, payloads, raw adapter reasons or exception text, including adversarial object values.
- Native success, DOM fallback, explicit DOM and checkpoint reuse must have different attributable records; overlapping timers must not be summed as independent work.

## Task 1 — Regression contracts (RED on GitHub)
- [ ] Add browser paginator synthetic interception/disabled/no-advance/cancellation cases after reading existing fixture contract.
- [ ] Add actual diagnostic-output tests for requested/used mode, anon ordinal, safe taxonomy, stage durations and collector native/fallback/DOM/error/reuse behavior.
- [ ] Add configuration/UI default and saved-choice tests; preserve CLI/library explicit DOM compatibility.
- [ ] Commit tests/plan only, create a draft PR, read back exact head and obtain expected failing runner node evidence before production edits.

## Task 2 — Minimal production changes
- [ ] Change only inspected paginator actions; keep state-change/repeated-page/source-total checks. Never click arbitrary buttons or bypass disabled/hidden controls.
- [ ] Extend existing diagnostics with context-scoped safe ordinal/tax/mode and timing helper, preserving optional/best-effort behavior and existing schema.
- [ ] Instrument selected-record wall time, list restore, View open, JSON observation/projection and source decision; retain legacy DOM span and add result counts only when known.
- [ ] Set desktop settings fallback/default to json-first; update real source/frozen GUI self-test expectation and help text. No migration that silently overrides saved DOM.

## Task 3 — Exact-head verification and review
- [ ] Verify synthetic fixtures/AST/static diff locally without execution; obtain actual GREEN on Windows full suite, portable subset, browser tests and frozen package in existing GitHub workflows.
- [ ] Verify RED successor nodes, new native/fallback/privacy cases, source/frozen self-test and artifact hashes/embedded source against exact tested tree.
- [ ] Independent review of candidate diff; resolve actual findings and update docs/PR from evidence. Do not call a benchmark speedup measured without paired runs.

## Task 4 — Deliver
- [ ] Report verified PR/build, new default semantics and remaining live-acceptance boundary. Merge, copying/replacing installed package, saved local preference changes and live benchmarking require their own instruction.
