# Corporate L2: shortest round-trip browser number, not binary64 exactness

Status: implementation candidate. Live acceptance of the real record remains
pending; this records the fix for the `inexact_corporate_l2_browser_number`
fallback observed on a real submitted corporate SPT.

Date: 2026-11-18. Extends
[L2 native quarantine](2026-11-17-l2-native-quarantine.md) and
[L2 SubPosition optional](2026-11-18-corporate-l2-subposition-optional.md).

## Live evidence

Local job `2ce7ad8f1e044c49994606f8f9cb69ca` (PPh Badan, Normal, SUBMITTED) fell
back to DOM with `detail_source.reason = inexact_corporate_l2_browser_number`
after the earlier Induk and L2 `SubPosition` fixes cleared.

All nine `ListOfInvestments` (`InvestmentList`) affiliate rows carry
`DebtInterest = 2.9`. `2.9` is not exactly representable in binary64, so
`_l2_exact`'s `Fraction.from_float(float(value)) == Fraction(value)` check
refused the whole owner block.

## Root cause

`_l2_exact` demanded **binary64 exactness**. But the browser parses the JSON
number token to a double and DecimalPipe renders that double's **shortest
round-trip repr**; the value need only round-trip, not be binary-exact. `2.9`
renders exactly as `2,9`, yet the old check rejected it.

## Fix

Replace the binary-exactness comparison with a shortest-round-trip comparison:

```python
number = float(value)
if Decimal(repr(number)) != Decimal(value):
    raise _UnsupportedMetadata('inexact_corporate_l2_browser_number')
```

`Decimal` equality is numeric, so `Decimal('5.8') == Decimal('5.8000')` holds;
the `.4f`-formatted reduced totals and integer year tokens still pass. The
existing guards (token grammar with no exponent, at most `digits` fraction
digits, at most fifteen significant digits, signed-zero and `_MAX_INTEGER`
bounds) are unchanged and remain the primary fail-closed wall. Within those
bounds the round-trip check is a retained safety belt.

## What does not change

- The approved A/B columns, ordered-total getters, null-default rules, label
  binding and every other form.
- `unsupported_corporate_l2_number` and `unsafe_corporate_l2_number` remains for
  format/precision/signed-zero violations (e.g. `0.0625` lacks digits, 16-digit
  integers, 5-decimal percentages).
- Whole-record DOM fallback for genuinely unsupported profiles.

## Verification

`tests/test_corporate_l2_owner.py`:
- `test_affiliate_fractional_rate_is_not_refused_for_binary_inexactness`
  (parametrized `2.9`/`0.1`/`4.38`) projects these rates.
- The refusal test drops `0.1` and `4.38` (now valid) while keeping the
  digit/format/type refusal cases.
