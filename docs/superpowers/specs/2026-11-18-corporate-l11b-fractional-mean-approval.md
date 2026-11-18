# Corporate L11-B: approved representation for saved fractional means

Status: **operator-approved representation permission, scoped to the bounded
subset below.** Live acceptance of any real record remains pending.

Date: 2026-11-18. Supersedes nothing; it extends the existing L11-B restricted
boundary without widening any other form.

## Approval

Approver: **@cepeter** (repository owner, non-author of the `Hermes Agent`
commits). Recorded approval comment:
<https://github.com/cepeter-job/spt-downloader/pull/287#issuecomment-6967477161>.

## Approval basis

The operator instructed that the real ordinary submitted target must be served
rather than refused: its saved row means are computed fractional averages
(`sum/12`) and its DER is therefore fractional, while the manual marker is
literal boolean `true`. The instruction was to prioritise safe
source/Number/framework semantics for that ordinary profile instead of a
speculative manual-false scope, and to preserve the raw Average/DER operands,
stored-object totals, null-cost custody and the visible header PARTIAL. The same
authorization permitted recording the verified L11-B boundary in `AGENTS.md`.

## What is approved

- A saved row `Average` is a **computed mean**, not a rupiah control, and may be
  projected only inside a bounded binary64-exact subset:
  - at most fifteen coefficient digits after `normalize()`;
  - `Decimal(str(float(x))) == x` (finite round-trip through the JS Number
    shortest decimal form);
  - `abs(x) <= _MAX_INTEGER` and no signed zero;
  - an integral value keeps the exact integer operand shape.
- The worksheet cell keeps the reviewed zero-digit `DecimalPipe` display
  rounding already used for these columns. The **raw** Decimal is retained as
  the DER operand and as typed custody evidence, never re-rounded.
- A DER ratio that is not exactly binary (`denominator not in (1, 2, 4)`, zero
  debt, or out of bound) is reported `der_exact=false` and left **unqualified**.
  It is not rounded into a supported operand, not fabricated, and does not
  refuse the whole form.
- Zero capital with non-zero debt remains fatal: an infinite ratio has no
  representation and must not be invented.

## What is NOT approved

- No header/question control projection; those stay PARTIAL.
- No complete L11-B worksheet claim: `projection_complete=False` and the Audit
  note remain mandatory.
- No change to `corporate-l11b-v1` restricted semantics.
- No live-acceptance claim from green synthetic tests.

## Enforcement

`coretax_corporate_projection._l11b_average` implements the subset;
`project_l11b_hydrated` keeps raw operands and reports `der_exact`;
`_apply_l11b` surfaces `der_exact` in the projection report. Tests:
`tests/test_corporate_l11b_hydrated.py::test_real_fractional_saved_averages_and_der_are_admitted_and_stay_partial`
and `::test_fractional_average_outside_the_binary64_subset_still_refuses`.
