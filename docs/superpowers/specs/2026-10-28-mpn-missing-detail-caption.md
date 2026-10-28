# Missing Accounting detail caption

The normal job reaches parent2470, then correctly refuses a rendered/source
identity mismatch. A separate owned unfiltered-list probe reaches the identical
original parent without detail actions. At0/100/500ms all six other identity
columns match; only Detail Jenis Pencatatan is blank. Its nonempty literal
AccountingTypeDetailCode is absent from the same-attempt original catalog.

The pinned main source's codeDescAsync pipe calls getReferenceDataDescription;
getActiveReferenceDataValue uses strict Code equality and returns null for zero
matches. The ordinary ui-grid reference template interpolates that description
without a raw-code fallback. The accounting column has no forceShowData/l3bcit
override. This supports a blank display only for a proved absent detail code.

Retain an optional complete original-code inventory separately from eligible
labels. Malformed/non-string code entries make that group's absence proof
unavailable. A present code never becomes absent merely because its description,
locale or ValidTo is ineligible. Existing default catalog readers stay unchanged.

Only ACCOUNTING_TYPE_DETAIL and a nonempty literal source code may use the new
blank projection after original catalog custody/freeze. Recompute all peer
projections before independent uniqueness; different missing codes may collide
as blank. Retain reference/numeric ambiguity refusal and fatal known mismatch.
Preserve raw codes, labels, bytes, output schema, pins, requests, Stop, budgets,
Document and capture/publication gates. Other missing labels retain existing
behavior; no cache read, extra GET or replay clock is introduced.

Normal live validation subsequently exposed a separate timeout after the single
close action had returned: the inspected dialog remained visible beyond the
existing one-second hidden wait. Give that visibility completion one bounded
five-second wait. Keep the single close click, owned Document/route and response
checks unchanged. Reconcile Stop and callback source/observer refusals after
both successful and exceptional waits; a still-visible dialog stays PARTIAL.
Delayed-hide browser regressions must prove a 1500 ms close succeeds, a 5500 ms
close refuses, and callback Stop/source failures cannot become success.
