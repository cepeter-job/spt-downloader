# L11-B recovery: restricted and bounded hydrated native profiles

## Status and scope

Implementation candidate only; no merge or live acceptance is authorized.
Local verification is AST/source/data inspection only. Runtime, exporter and
observer tests belong exclusively to GitHub Actions.

The restricted v1 findings below are retained as history, not superseded by a
claim that every lifecycle is now supported. The additive hydrated-v2 profile
and its independent proof requirements are documented separately below.

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

## Hydrated-v2 extension design (source review; verification pending)

This additive profile does not replace or widen the restricted v1 proof. It
requires all three positive loaded provider pins, the existing manifest-owned
fresh submitted SPA lifetime, explicit null predecessor, preceding enabled
Induk and exact owned conditional table structure on two reads. No new
transport or business-value probe is introduced. Missing optional lifetime
preserves v1, not v2 permission. The protected contract remains the restricted
one until the parent obtains the separately approved contract update.

Additional independently hashed source: vendor.c32c4ee39d966e30.js is 2525901
bytes, SHA-256 `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`,
exactly the configured pin. Vendor hook registration near 1254655 orders initial
ngOnChanges before ngOnInit; FormGroup patchValue near 1386500 emits per control,
and disable near 1381593 emits every child even if already disabled. Therefore
one must NOT assume subscriptions existed during the first OnChanges.

The ordinary fresh SPA parent is the additional lifecycle premise: near
2637923 it starts showAttachment11b=true, and its template near 2727k eagerly
instantiates this child (no lazy content template). Its ngOnInit subscribes the
asynchronous original primary HTTP response. The initial synchronous child
creation/OnInit completes before that response callback hydrates the parent.
The child subscribes its three scalar controls in ngOnInit. Upon original
formData hydration, setFormData patches the controls and ngOnChanges then
unconditionally disables the submitted FormGroup. The last three-control
emissions recompute Ebitda = (commercial + depreciation) + income-tax, excluding
borrowing cost; disable also replaces the temporarily patched saved quarter.
A later parent L1 EBITDA callback re-enters OnChanges but manual true/numeric1
excludes the auto overwrite; submitted excludes the income-tax overwrite.
Parent onCallbackForm(L11BForm) only stores the emitted DTO and changes L11-C
visibility: it does not replace l11bFormData. The delayed DER callback changes
only the ratio control. This profile does not authorize reused/history/late
independently mounted children or infer initialization from a quiet timer.

V2 additionally reconciles the captured quarter with floor(derived Ebitda/4),
so both the saved-quarter hydration write and final callback write agree.
All consumed scalars/months/Average operands and EVERY ordered intermediate
must be integral within fifteen digits; signed zero, coercive strings,
null/default scalars and fractional means stay unsupported. A model View row
Average is a literal DTO value: getGrid1DataMap/getGrid2DataMap copy it; V_
getters near 212800 sum those saved averages in original row order. Neither
sum/12 nor the editor's populated-month denominator is used. Captured DTO
footer/ratio controls are overwritten and retained as unused typed custody,
not reconciled as if they were the submitted renderer's inputs. Null and []
bodies independently produce zero getters with their original typed provenance.

Part II exists iff borrowingCost > hydratedQuarter OR hydratedEbitda <= 0.
The observer must bind the exact grid1/grid2/grid3 set for that condition,
including headers, footer spans, groups and ui-grid-offline/p-table ownership.
Hidden Part II retains its original rows in custody but emits no fake tables.
DER operands are the exact unrounded model Average sums. The bounded new ratio
subset is nonzero operands and an exactly representable quarter-unit ratio
(denominator 1, 2 or 4 and fifteen-digit coefficient at two decimals), or both
zero (source N/A; the existing workbook DER availability rule leaves formulas
unqualified rather than inventing a zero ratio).
Repeating ratios, fractional means and debt-zero/capital-nonzero remain
unsupported rather than altering existing DOM DER behavior or template geometry.

The six scalar controls and all three populated blocks can be emitted by this
profile, but header/question template omissions remain unapproved. Keep
projection_complete=False and visible `unprojected_l11b_header_question` Audit
reason, original dump/metadata, sequence/container/path and duplicate order.
No approved resource, template geometry, CI or AGENTS changes are made.

## Remaining proof and acceptance gaps

Full L11-B still needs approved header/question mapping, auto/manual-false and
null/default scalar lifecycle profiles, broader fractional Average/DER precision
and any source profile outside the bounded fresh submitted branch above.
The protected AGENTS update for v2 is deliberately left to the parent owner;
this worker is not authorized to edit it. Hosted synthetic coverage and the
exact-head results below do not certify application-owned live acceptance.

The initial protected `AGENTS.md` edit was denied and was not retried under
that denial. The operator later explicitly renewed approval for the verified
L9/L11-B boundaries. This branch now records the restricted L11-B contract in
`AGENTS.md`; no runtime code, admission gate or live-acceptance scope changed.
