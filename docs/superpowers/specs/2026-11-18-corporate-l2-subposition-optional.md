# Corporate L2: SubPosition is optional shareholder metadata

Status: implementation candidate. Live acceptance of the real record remains
pending; this records the fix for the `unsupported_corporate_l2_owner_row`
fallback observed on a real submitted corporate SPT.

Date: 2026-11-18. Extends
[L2 native quarantine](2026-11-17-l2-native-quarantine.md) without widening any
other form.

## Live evidence

Local job `baae8d60f8b843e7852901904233735e` (PPh Badan, Normal, SUBMITTED) fell
back to DOM with `detail_source.reason = unsupported_corporate_l2_owner_row`
(category `adapter_ineligible`).

The captured primary `CurrentFormData.ListOfOwnership` carries six
`ListOfShareholders` rows whose keys are exactly:

`Name, Address, CountryCode, TIN, Position, PaidInCapital,
PaidInCapitalPercentage, Dividend, ValidFrom, ValidTo`

No row contains `SubPosition`.

## Root cause

`project_l2_owner` treated `SubPosition` as a **required** shareholder row key
(`required = {*columns[0], 'SubPosition'}`). The live portal omits it, so the
row-shape guard `required <= set(source)` failed and refused the whole owner
block.

The L2 quarantine spec already states `SubPosition` is "copied but unused" row
metadata: it is never projected into a column and only emitted as
`unused-subposition` provenance when present.

## Fix

`SubPosition` moves from the required set to the optional set for shareholder
rows:

- `required = set(columns[block])`
- `optional = {'SubPosition', 'ValidFrom', 'ValidTo'}` for block A,
  `{'IsEditable'}` for block B.

A present `SubPosition` is still emitted as `unused-subposition` provenance; an
absent one is simply skipped. Affiliate rows are unchanged.

## What does not change

- The approved A/B columns, ordered-total getters, null-default rules, country
  and position label binding, and every other form.
- Whole-record DOM fallback for genuinely unsupported profiles; privacy,
  authorization and identity contradictions remain fatal.

## Verification

`tests/test_corporate_l2_owner.py` adds a regression test that a shareholder
row omitting `SubPosition` still projects (one body row, no `SubPosition`
provenance). The existing `SubPosition`-present test still asserts the
`unused-subposition` provenance.
