# Native JSON readiness implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. The user approved autonomous planning and implementation on 2026-10-23. Product execution remains GitHub-runner-only.

**Goal:** Give corporate, PPN, PPh21 and Unifikasi native observers the current owned-panel readiness and guarded read-only pagination behavior.

**Architecture:** Reuse `_wait_tab_panel` and `_click_table_paginator` from `coretax_browser`; keep native component, href, duplicate-target, source identity and getter-trap checks. A small `_native_panel` helper in `coretax_corporate` is shared by the native observers that already import its traversal helpers. No new worker module or public API.

**Tech Stack:** Existing Python stdlib, Playwright, pytest and Microsoft Edge synthetic fixtures; existing GitHub Windows/portable/build workflows.

**Spec:** `docs/superpowers/specs/2026-10-23-json-mode-completion-design.md`, section 4.

## Global constraints

- Start from `413c440b725baafece976fcad2914c1d2a4eb826`; preserve the approved full-program design and all private data.
- All product imports, pytest, browser/native/Tk fixtures, builds, self-tests and EXE execution run on GitHub runners.
- DOM business-value reads, guessed endpoints/actions, general POST access and silent COMPLETE remain prohibited.
- Keep whole-record DOM fallback for unsupported coverage; identity/privacy/authorization contradictions and Stop remain fatal/cancelled.
- Do not change workflows, dependencies, templates, installed packages, settings or LICENSE.
- This is the first independently testable slice. Corporate semantic projection, PPN choice, dated references and live acceptance retain separate tasks under the approved design.

## Review focus

- A tab's binding disappears after it was inspected: never adopt another visible form.
- A caption/index changes while readiness is pending: never relabel another panel.
- A duplicate/nested/foreign or CSS-hidden target exists: preserve native rejection.
- Pointer interception masks a real paginator: click only the inspected owned enabled control.
- Reset/no-advance/page-limit/Stop: never emit additional requests or grant coverage.

### Task 1: Native panel identity

**Files:** create `tests/test_native_panel_readiness.py`; modify `coretax_browser.py`, `coretax_corporate.py`, `coretax_masa_observer.py`, `coretax_pph21_observer.py`.

**Interfaces:** `_wait_tab_panel(view, tab, caption, check_cancel, *, initial_panel_id=None)` preserves pre-click binding knowledge; `_native_panel(page, view, tab, caption, record, check_cancel)` returns the ready owned panel or `None` for unsupported native structure. Existing observers retain their return and exception contracts.

- [ ] Write `test_native_observer_follows_current_binding`, parametrized over corporate/PPN/Unifikasi/PPh21. Rebind after the first real post-click `aria-controls` read; the old target remains hidden. Assert complete structural catalogs, one click per intended tab, no unexpected requests and no native business-value reads.
- [ ] Write `test_native_observer_rejects_invalid_rebinding` for hidden/foreign/duplicate targets, missing controlled binding and reordered caption. Assert `None`, no wrong-form observation and no unsafe action.
- [ ] Write `test_native_observer_stop_during_rebinding_propagates`. Assert `CaptureCancelled` and no later tab/grid traversal.
- [ ] Commit tests only, push this feature branch, create a draft PR, and read exact-head GitHub RED failures. Expected: valid rebinding fails on the old observers; negative/safety fixture checks execute without skips.
- [ ] Implement the shared helper and wire all four families. Validate inspected href before click and current href/direct ownership/duplicate target after readiness. Preserve initial controlled identity through binding gaps. Keep the same readiness deadline and one click.
- [ ] Read exact-head GitHub results. Expected: all new panel cases and existing native getter/identity/ownership cases pass. Record head, tested tree, run, artifact and node outcomes in the ledger.

### Task 2: Guarded native grid traversal

**Files:** create `tests/test_native_grid_pagination.py`; modify `coretax_corporate.py`.

**Interfaces:** preserve `_turn_grid(page, table, max_pages, check_cancel) -> bool`. It reads paginator state only, uses the actual table owner handle with `_click_table_paginator`, rejects unsupported/no-advance traversal and propagates cancellation.

- [ ] Write `test_native_grid_uses_inspected_controls_under_pointer_interception` for initial first/later pages. Independently prove ordinary pointer clicks are intercepted; assert full native traversal and expected click count.
- [ ] Write `test_native_grid_refuses_hidden_disabled_ambiguous_and_foreign_controls`. Assert no forbidden click, `False` for enabled but unavailable controls, and legitimate end-of-list semantics for disabled controls.
- [ ] Write `test_native_grid_stalled_reset_does_not_click_repeatedly`, `test_native_grid_budget_does_not_open_an_extra_page`, and `test_native_grid_stop_prevents_next_request`. Assert one stalled action, no beyond-budget action and propagated Stop.
- [ ] Obtain runner RED for new failures before editing production; preserve Task 1 results.
- [ ] Implement minimal guarded traversal; reset and forward movement each require a changed paginator marker within the existing bounded wait. Preserve repeated-state detection, page limits and handle cleanup.
- [ ] Obtain GREEN on the full existing Windows suite and portable subset. Do not sum overlapping suite counts or label synthetic browser execution as live acceptance.

### Task 3: Evidence, documentation and independent review

**Files:** create `docs/superpowers/reports/2026-10-23-native-json-readiness.md`; update current code-map/architecture guidance only where behavior changes.

**Interfaces:** consume exact PR head/merge tree and runner artifacts; produce a reviewable PR and a scope-specific evidence report. The approved remaining JSON program stays open.

- [ ] Read back JUnit, package and bootstrap artifacts by exact run/attempt/artifact ID; verify digest/manifest/build identity/embedded worker resources against the tested tree. Expected: all required gates pass and all new RED nodes have passing successors.
- [ ] Request one fresh-context whole-branch source review per executing-plans. Fix concrete findings through new runner RED/GREEN evidence where behavior changes.
- [ ] Update the report and PR description with final behavior, evidence coordinates and remaining live/other-program boundaries. Do not merge, install or imply live acceptance from this slice.
- [ ] Record completion in the plan-scoped ignored ledger, then continue the corporate source/projection work under its own concrete plan.
