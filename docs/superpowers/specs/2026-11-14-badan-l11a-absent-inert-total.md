# L11-A: absent recap total for an inert section

Date: 2026-11-14
Status: implemented with the narrow inert guard below.
Baseline: main `e84a67e` (L7 chain fixes #256–#259 landed).

## Live evidence (build `e84a67e`, job `fb4e8295`)

The L7 optional proof now succeeds (no `corporate.l7_*_gate` events,
`corporate_l7_lifetime` present with all literal-True facts). The next refusal
is `unsupported_corporate_l11a_source_shape` from `project_l11a`.

Value-free inspection of the captured payload (`corporate-income` response):

| Fact | Value |
| --- | --- |
| `Payload.CurrentFormData.L11AFormData` | present, keys exactly `{Facilities, Recapitulation}` |
| `Facilities` | literal `null` |
| `Recapitulation` keys | 11 of the pinned 12; **`TotalAmountofCosts` absent** |
| All six cost fields | literal `null` |
| L11-A page endpoints | exactly `l11a-table-{1,2,3,5}-grid` |

So the section is inert (no facilities, no amounts) and the live build omits the
recap total key entirely.

## Rule

`project_l11a` accepts `Recapitulation` with the pinned key set minus
`TotalAmountofCosts` **only when** `Facilities` is exactly `null` and every
`_L11A_COSTS` value is exactly `null`. The projected total is blank with the
explicit provenance rule `absent-inert-zero-total`, and the ordered cost sum
must still be zero.

A missing total with any numeric cost, any non-null `Facilities`, or any other
key drift still refuses (`unsupported_corporate_l11a_missing_total` /
`unsupported_corporate_l11a_source_shape`). Nothing is clamped or invented.

## Tests

`tests/test_corporate_l11a_projection.py`:
inert shape projects a blank total with the rule; missing total with a numeric
cost refuses; missing total with facilities refuses. Existing L11-A contracts
stay unchanged when the key is present.

## Follow-up: Jakarta-offset decree dates (live `5ac6574`)

The next live gate is `unsupported_corporate_l3_date`: both L11-A decree dates
are encoded as `YYYY-MM-DDT07:00:00+07:00` (Jakarta midnight expressed as
07:00 with a +07:00 offset), which the generic date helper refuses.

Rule: for `DateOfDecree*` fields, accept exactly that literal shape and render
the calendar date as `dd-mm-YYYY` with rule
`literal-date-jakarta-0700-offset`. Any other time or offset still refuses.
