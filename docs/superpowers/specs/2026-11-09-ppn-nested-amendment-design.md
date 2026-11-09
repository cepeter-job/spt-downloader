# PPN nested-amendment branch (NORMAL inert totals)

Baseline main: f5eb1ca (PR #202 merge).

## Live evidence

Latest live run (build 42551494946, job 5feae992, 2026-11-09 03:23-03:26 UTC,
PPN-only selection):

- PPN: `dom` / `adapter_ineligible`,
  reason `unverified_ppn_nested_amendment_branch`. Observer passed (no
  `masa.observer_gate`); capture 121/121 complete.
- The prior `unverified_ppn_final_balance_lifecycle` blocker is gone.

Captured primary (booleans only; no values recorded):

- Outer `ReturnSheetModel` is NORMAL; nested
  `A1FormListOfExportTaxableGoodsOrServices.ReturnSheetModel` is NORMAL.
- Conditional-binding roots (`VATAndSTLGUnderOfOverPaidDueToAmmendment`,
  `VATAndSTLGUnderOrOverPaidOnAmmended`,
  `VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended`) are
  present as dicts with all-null leaves. The LC-bound root is absent as
  required for the LC branch.

`_project_ppn_collection` currently requires `model=='AMENDMENT'` and
`nested=='AMENDMENT'` for any `conditional=True` control, so it refuses
before projecting. Existing tests cover only `AMENDMENT` (plus an
`AMENDMENT`/`NORMAL` mismatch refusal); the NORMAL inert path is untested.

## Fix

In `_project_ppn_collection`, branch the nested check by `model`:

- `NORMAL`: require `nested == 'NORMAL'` (mismatch or missing still
  refuses with `unverified_ppn_nested_amendment_branch`). Root-bound
  conditional controls additionally require the present root dict with a
  null leaf (the only live-proven inert shape); non-null, missing or
  malformed also refuses. They then project via the existing direct stored
  path (`null` → `0`, rule `direct_final_path` instead of
  `nested_amendment_stored`, since no amendment subscription owns them).
  The LC-bound (`root=None`) controls return `0` only when the prior leaf
  is null (`rule=normal_inert_amendment_zero`); a non-null prior still
  refuses. AMENDMENT behaviour is unchanged.

## What does not change

- Observer/`TABLE` contracts, diagnostics, and AMENDMENT facility/calendar
  blockers. A NORMAL filing with `nested == 'AMENDMENT'` still refuses.

## Tests (CI-only; RED by source)

- NORMAL + nested NORMAL + null leaves projects `0` (root-bound and
  LC-bound). NORMAL + nested AMENDMENT (mismatch) still refuses.
  AMENDMENT + nested NORMAL still refuses (existing).
