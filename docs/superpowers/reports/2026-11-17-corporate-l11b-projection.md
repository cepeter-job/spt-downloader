# L11-B recovery: restricted native projection

## Status and scope

Implementation candidate only; no merge or live acceptance is authorized.
Local verification is AST/source/data inspection only. Runtime, exporter and
observer tests belong exclusively to GitHub Actions.

The recovered commit dd9ca30 attempted six scalar controls, both conditional
Part II tables, DER reconciliation and Part III. Review found that this was
not justified by the source lifecycle. This candidate deliberately narrows to
four stable, non-null scalar controls and the unconditional Part III grid.
The section, saved workbook mapping and resume Audit remain explicitly PARTIAL
with `unprojected_l11b_lifecycle`; omitted source leaves remain in custody.

## Reviewed source identity

The local public 525 bundle hashes to
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`, exactly the
reviewed `525.32c49782948fc5ef.js` entry in `resources/build-pins.json`.
Offsets below are zero-based decoded-text positions, not private values.
The grid renderer's reviewed main bundle is
`main.bed1449c3647a8ca.js`, SHA-256
`ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
Both observer and adapter require exact positive approved pins; an arbitrary
64-hex digest, missing/missing pair or foreign route does not qualify.

## Source trace and safety corrections

- Near 2647k, `fillForm` sets the submitted flag from ReturnSheetStatusCode,
  parses CurrentFormData and PreviousFormData; `mapFormData` near 2651k assigns
  the current L11BFormData directly. The L11-B input/output binding near 2624k
  connects that current form and `onCallbackForm('L11BForm', ...)`.
- Near 287k, the actual owner constructs six monetary controls. `ngOnChanges`
  calls `setFormData`, disables on submitted, and has two other overwrite arms.
  IncomeTaxExpense overwrites only when not submitted. The first two controls
  may be overwritten from `dataEbitdaOnL11B` even on submitted when the manual
  marker compares equal to zero. Admit only literal true or numeric token 1;
  strings, false, null, and numeric zero remain unsupported.
- Near 289k, `calculateEbitda` sums the first three controls (NOT borrowing
  cost), while `setFormData` near 293k does not patch saved Ebitda. Patch/disable
  emissions and parent callback order therefore matter. Neither saved Ebitda
  nor saved Ebitda25 is certified. Scalar nulls default to zero in hydration;
  this restricted branch refuses nulls instead of copying blank or inventing
  a default without full lifecycle proof.
- Near 295k, `setGridValue` maps DTO rows into model arrays and recomputes
  totals; a delayed callback assigns the ratio. Near 305k, Part II is
  conditional on hydrated EBITDA/quarter. Do not infer its visibility from
  stored controls. Its tables and DER remain unprojected.
- Near 258k, the equity EDIT dialog counts non-null/non-empty months and
  computes an ordered sum divided by that populated count. This does NOT prove
  the read-only View recomputes row means. The recovered two-decimal formatting
  would also change a repeating mean before Excel DER divided it. No month
  mean, floating-point identity, null ratio or fractional-average normalization
  is admitted by this candidate.
- Near 291k, `getGrid3DataMap` maps the five exact BorrowingCosts keys. Near
  308k the Part III table is unconditional. Near 215k the model's
  TotalBorrowingCosts getter reduces each of four columns in source order;
  near 231k its footer displays those model totals. Only genuine string names
  and nonnegative integral numeric tokens are supported. Every operand and
  ordered partial sum is bounded to 15 digits, avoiding binary64 rounding.
  Explicit null/empty arrays produce the getter's zero footer with original
  empty-array/null provenance; missing keys and wrong types refuse.
- `getFormData` refers to `n.TotalBorrowingCosts`, but the FormGroup has no
  such control: JSON omits undefined. A present DTO alias (even null) is
  unreviewed and refuses. No guessed alternate DTO spelling is added.

## Custody and completeness

Retain the original dump, all metadata, omitted source controls, raw response
bytes, duplicate row order, original paths, response sequence and container.
Append only the reviewed Part III table. The four literal controls have their
own typed source provenance plus the manual-marker predicate evidence.
The exporter must not report COMPLETE even if all emitted slots mapped.
Existing DOM DER availability, formulas and unmapped counts are unchanged.
No live endpoint, capture authorization, native gate or CI configuration is
broadened. The main asset reader is the existing loaded-script-only reader.

## Remaining proof and acceptance gaps

Full L11-B still needs an independently proved initial/final EBITDA lifecycle,
conditional Part II structure and exact numeric representations/means for its
saved body/footer averages. Auto/manual-false forms currently fall back.
This is not a complete native L11-B implementation or taxpayer acceptance.
Synthetic Actions tests cover projection/refusals, exact proof production,
adapter custody and saved workbook/resume PARTIAL readback.

The requested protected AGENTS.md update was denied by the approval boundary;
it remains unchanged. This report records the actual implementation boundary
but is not a substitute for that outstanding protected-contract deliverable.
