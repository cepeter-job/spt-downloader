# Corporate Induk submitted v3: value-gated inactive projection

Status: implementation candidate. Live acceptance of the real record remains
pending; this records the fix for the `adapter_ineligible` fallback observed on
a real submitted corporate SPT.

Date: 2026-11-18. Extends
[Induk populated submitted controls](2026-11-17-induk-submitted-controls.md)
without widening any other form.

## Live evidence

Local job `e12d7da7f997407cbc18d598089d283f` (PPh Badan, Normal, SUBMITTED)
fell back to DOM with `detail_source.reason =
unsupported_corporate_induk_inactive_profile` (category `adapter_ineligible`).

The captured primary `CurrentFormData.MainFormData` is a real-income record:

- `IsIncomeSubject = 1`, `TotalIncomeSubject = 1068935.0`
- `IsIncomeExcluded = 1`, `TotalIncomeExcluded = 0.0`
- `IsIncomeTaxDeduction = 0`, `TotalIncomeTaxDeduction = 0.0`
- `UnderpaymentIncomeDueAmended = null`
- `NetIncomeBeforeTax = -9093013897.0`, `IsIncomeUnder = 0`, `IsIncomeSolely = null`

It is **not** the original no-activity fixed point.

## Root cause

`_observe_induk_submitted` claims `corporate-induk-submitted-v3` from structure
alone: the four inactive amount/radio controls are present and disabled. A
submitted `?view=true` render disables every control, so v3 is claimed for
**every** submitted corporate record, not only the frozen inactive one.

The projection then treated the v3 claim as permission to emit the inactive
slots and required the exact fixed point, raising
`unsupported_corporate_induk_inactive_profile` for any real-income record. The
whole record therefore fell back to DOM.

## Fix

The v3 structural claim is no longer permission to emit the inactive slots.
`_induk_inactive_profile(main)` decides from the original values:

- the three selectors and the three amounts are original `_CorporateNumber`
  zero tokens, and
- `UnderpaymentIncomeDueAmended` is an explicit `null`.

When the fixed point holds, the four inactive slots are emitted (22 fields).
When it does not, the normal submitted projection is used (18 fields) and the
inactive slots stay unprojected. The projection report records
`inactive_profile: true|false`. The v3 binding still requires the four extra
control names, so a malformed v3 proof is refused as before.

## What does not change

- v2 behaviour, the eight submitted amount slots, identity slots, the negative
  main reset predicate, and every other form.
- `projection_complete=False` / `unprojected_induk_captions` and the PARTIAL
  template mapping.
- Whole-record DOM fallback for genuinely unsupported profiles; privacy,
  authorization and identity contradictions remain fatal.

## Verification

`tests/test_corporate_induk_inactive.py` keeps the fixed-point acceptance and
now asserts that a v3 claim with a non-fixed-point value, an absent inactive
control, or a non-null amendment difference keeps the normal 18-slot
projection. A live-shaped regression test reproduces the real negative-main
record above and asserts native eligibility with `inactive_profile=False`.
