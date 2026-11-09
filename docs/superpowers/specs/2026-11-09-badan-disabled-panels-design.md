# Disabled-panel binding for Corporate native JSON

Date: 2026-11-09
Baseline: `main` @ `92d062d` (PR #206 merge, run `42595786607`).
Status: implemented design, pending live rerun for `native_verified`.

## Evidence (live, CORP detail, job `4baa80a8…`, build `42595786607`)

- Observer succeeded; json_observe 595s. json_project 20s → audit `reason` =
  `unmapped_corporate_source_subtree,unverified_corporate_l4_footer`.
- Offline replay on the 572 captured responses (manifest responses + paths =
  all FORMS roots) passes `_corporate_primary`, footer reconciliation, and
  every per-group grid cover.
- One pointer omission anywhere in FORMS reproduces
  `unmapped_corporate_source_subtree` — evidence requires every FORMS root.
- Missing root keys of disabled panels produce no evidence rows; null-valued
  FORMS roots do (`/L1bFormData`, `/CalculationFacilitiesIncomeTaxRateReduction`).
  Both are null in this live, disabled-tab taxpayer.
  The L4 footer reason was a cascade: `primary_source` is None when the
  primary raised, so the footer check refused for the same root cause.

## Behavior today

`observe_forms` skips each `p-disabled` tab entirely, declaring neither its
JSON path nor grids. For object-valued roots this fails closed (correct).
For null-valued roots, the adapter still owes a pointer for the inert null
row — so a fully consistent disabled non-applicable form blocks the whole
SPT from `native_verified`.

## Change

1. Observer: a disabled FORMS tab still declares a *path-only* binding
   (`paths: [[root]]`, `disabled: True`, no grids/responses/dependencies —
   nothing inspected, nothing carried).
2. Adapter (`_corporate_bindings`): a disabled form's paths are registered
   with `section['disabled'] = True`.
3. Adapter (`_corporate_primary`): a disabled declared path requires the root
   value to be exactly `null` or missing (inert empty panel) — any
   non-null root makes the structure unproven and refuses with the fixed
   reason `unverified_corporate_disabled_panel`, row included.

Deliberately not changed: grids/projections on disabled panels (only the
path is declared), enabled-panel DOM proof, null allowlist policy (the
31-key reviewed list is untouched — disabled-panel roots are bound,
not omitted).

## Risks

- A disabled panel with a live object would be newly admitted if the observer
  binding were wrongly produced; gate 3 refuses it, and the observer adds
  no grids, so only the null row can pass.
- Absent (DeclarationTransactionRelatedParties) behavior unchanged.

## Tests

- Adapter: disabled+null passes; disabled+object refuses
  `unverified_corporate_disabled_panel`; disabled+absent passes.
- Observer: synthetic tabs (Induk enabled + L1-B disabled) via FakePage tabs —
  disabled binding declared, no panel access for it.
