# PPN native JSON: unchanged-percentage balance + NORMAL carry-forward choice

Baseline main: 9b0cfd3 (PR #201 merge).

## Live evidence

Latest live run (build 42361235682, job e70aa06b, 2026-11-09 02:01-02:05 UTC):

- PPh21 ordinal 1: `native_verified`.
- Unifikasi ordinal 2: `native_verified`.
- PPN ordinal 3: `dom` / `adapter_ineligible`,
  reason `unverified_ppn_final_balance_lifecycle`. No `masa.observer_gate`
  (observer passed); capture 121/121 complete.

Captured PPN primary has no `BasedOnType` key (→ `None`) and
`InputTaxPercentageGoods`/`InputTaxPercentageServices` at the reset
defaults (90/0). That is the second `_ppn_vat_balance` refusal branch.
The stored `VATUnderOrOverPaid.VAT` balance EQUALS the formula
`floor(Output − Deposited − Input − Collector)` computed from the component
leaves, and the output/input component sums reconcile (booleans only; no
values recorded).

PPN chunk JS (640.7ac2145c88285ca5.js, live probe):

- Init patches `BasedOnType=BasisOmzet` for non-normal VAT with an early
  period, then calls `onChangeBasedOnType()` unconditionally.
- `onChangeBasedOnType()` first patches percentages to 90/0, then overrides
  only for `BasedOnType==BasedOnOmzet` (80/80 or 70/60 by date) or
  `==BasedOnActivities` (90) with a later date.
- `InputTaxPercentageGoods/Services.valueChanges` (DistinctUntilChanged)
  drive `calculateInputTaxDeliveriesOfGoodsVAT` /
  `calculateInputTaxRenderOfServicesVAT` → `calculateInputTaxTotalVAT` →
  `calculateVATIsUnderOrOverPaid()`, which patches `VATIsUnderOrOverPaid`
  with `floor(SelfCollected − Deposited − CalculatedInput − Collector)`.
  When percentages are already 90/0 the patch emits nothing, so the stored
  Prefill balance is final.
- `onchangeVATIsUnderOrOverPaid()`: `Model==Normal && VATIsUnderOrOverPaid<0`
  (overpaid: input credit exceeds output) takes the first branch with
  `isCarryForwardDisabled=false`; the else branch patches `AskedTo=null`
  and disables the choice. Live AskedTo is carry-forward
  (`CARRY_FORWARD`), model is NORMAL, balance is overpaid.

## Fix

1. **Balance (unchanged-percentage stored path):** in `_ppn_vat_balance`,
   with `basis is None` and percentages at 90/0, do not raise immediately.
   Compute the component balance as today (with the existing reconciliation
   checks), then read the stored `VATUnderOrOverPaid.VAT` and require its
   decimal to equal the computed floor. Agreement returns the computed
   value (stored == computed, live-verified). Mismatch or missing stored
   still raises `unverified_ppn_final_balance_lifecycle`. `basis is not
   None` still raises unconditionally. The changed-percentage path (formula
   overwrites stored) is unchanged and still ignores stored.
2. **AskedTo (NORMAL overpaid carry-forward):** in `project_ppn_asked_to`,
   for `model=='NORMAL'` with an integral negative (overpaid) balance and
   `choice=='CARRY_FORWARD'`, return the choice with the balance
   contributing evidence (`rule=normal_carry_forward_overpaid`).
   Non-negative NORMAL still returns `None/not_overpaid_clear`; other
   choices (fast/forward) still refuse with
   `unverified_ppn_normal_choice_lifecycle` (facility/calendar paths for
   NORMAL are not reviewed here).

## What does not change

- `TABLE`/observer contract, diagnostics events/enums, and PPN
  facility/calendar blockers for AMENDMENT and for NORMAL fast/forward
  choices. No values, offsets, identities, or payloads are recorded.

## Tests (CI-only; RED by source)

- `test_ppn_json_vat_balance`: unchanged percentages with agreeing stored
  balance now project (was raise); disagreeing stored still raises.
  `basis` present still raises.
- `test_ppn_json_choice_guards`: NORMAL overpaid + carry-forward returns
  the choice; non-negative NORMAL still clears to `None`.
