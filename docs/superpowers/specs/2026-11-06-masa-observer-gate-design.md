# Masa observer gate diagnostic (Unifikasi / PPN)

Baseline main: 2879b52690ca4359f0883afd7503fba7475f3a92 (PR #198 merge).

## Evidence

Live test on the PR #198 build (main 2879b526, COMPLETE run):
- PPh 21/26: `detail.source=native_verified` ✅ (JSON-first works)
- Unifikasi: `forms_unavailable` (digest pin OK — no `build.unfamiliar_build`)
- PPN: `adapter_ineligible` (cursor wrapped up)

The Masa observer returns bare `None` from ~15 distinct gates with no
diagnostic, so the specific refusal can't be attributed. PPh21 got this
treatment in PR #193; Masa was the remaining gap.

## Design

`_gate(name)` helper in `coretax_masa_observer` records
`masa.observer_gate` with a fixed enum: `unsupported_tax`, `build_digest`
(mirror of build.unfamiliar_build — both fire), `tab_set`, `tab_disabled`,
`panel`, `form_root`, `fields`, `grid_structure`, `table_shape`, `total`,
`reference`, `catalog`, `evaluation_error`. Every `return None` in
`observe_masa_forms` maps to one gate. Behavior unchanged: still fails
closed to DOM; the refusal becomes attributable.

PPN's adapter_ineligible is a downstream projection refusal (post-observe),
not an observer gate; it stays covered by existing adapter diagnostics.
If PPN adapter refusals recur, they get their own allowlisted reason.

## Verification

Fixture-defect tests pin the recorded gate per defect (as with PPh21).
Live rerun: `masa.observer_gate` names the Unifikasi gate.
