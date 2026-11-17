# Induk populated submitted controls: bounded follow-through

Status: implementation candidate, not full Induk completion. New isolated branch
from main f5e40a2; #269 is the identity baseline, #283 remains a separate open
contract-only PR. No AGENTS/resource/layout changes or merge authorization.

## Independently verified source

Local review bytes (not loaded-provider/live evidence), SHA-256:

- `z525.js`, 3334844 bytes: `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`
- `l10a-main.js`, 4467267 bytes: `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`
- decoded `vendor.c32c4ee39d966e30.js`, 2525901 bytes:
  `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`

All three equal resources/build-pins.json. Vendor was obtained as a static
JavaScript source read, not a business/reference API request or portal navigation.
Its HTTP representation was Brotli; only decoded JavaScript bytes match the pin.
Offsets below are zero-based Unicode character offsets in decoded pinned source.
No private source bytes or taxpayer values are committed.

## Submitted execution and representation proof

525 `fillForm` (2647688) assigns `isMigrated=t.IsMigrated`, sets `isStatusSubmitted=true`
for SUBMITTED, parses CurrentFormData, and maps MainFormData into the main-form
input. Main renderer supplies parent's status/model/IsRupiah to that child.
Main component Ec starts at 2778983. Main `ngOnChanges` calls `setFormData`
(2791437), then `getDataFromBaseForm`, `setAmendmentData` and disabled-form
handling (2842137). `setFormData` patches each exact named control; this is not
an editor callback. The v2 branch additionally requires all eight base-overwritten
identity controls to equal the original outer owner with the same literal type;
it retains both owners instead of exporting a stale main-header copy.

PrimeNG InputNumber in VENDOR: `writeValue` (2147458) stores the control;
`formattedValue` (2147283) calls `formatValue`; `formatValue` (2136668)
uses Intl.NumberFormat(locale,getOptions). Constructor at 2133494 proves
allowEmpty=true, format=true and grouping=true. Null renders blank with allowEmpty;
Rupiah main initializes minFraction=maxFraction=0 (Ec constructor), and its
active renderer (2924000..2937000) passes locale Indonesia and those bounds.
This slice accepts only original numeric tokens, finite integral absolute value
<=999999999999999, excluding signed zero; it does not emulate coercion, floating
rounding, unsupported numeric strings or non-integral money. Explicit null stays
separate from absence and follows only the exact setter default described below.

## Complete approved-slot inventory

Ten identity slots stay literal under v1; preserve leading zeros and original
number-token versus JSON-string provenance. Header identity has a separate
base-form overwrite caveat in #283; this slice does not broaden that contract.

The remaining seventeen declarations are inventoried individually:

| Approved slot | Actual control / submitted path | Candidate disposition |
| --- | --- | --- |
| C question 2 (blank name, full radio caption) | **TotalIncomeSubject**, not IsIncomeSubject; active p-inputNumber after the radio pair, constants 2874... | unresolved: async L4 footer and callback completion |
| C question 3 (blank name, full radio caption) | **TotalIncomeExcluded**, not IsIncomeExcluded | unresolved: L4 child overwrites; exact fixed-point/lifetime needed |
| D4 | NetIncomeBeforeTax | emit nonnegative integral captured control; CalculateNetIncomeBeforeTax exits when submitted; prefillBy0FromIsIncomeSolely cannot change nonnegative value |
| D7 | FiscalNetIncomeAfterTax | unresolved: CalculateFiscalNetIncomeAfterTax always patches `net-reduction-vocational`; child overwrites and emission order matter |
| D9 | TaxableIncome | unresolved: debounced CalculateTaxableIncome, carry/child history; do not copy stored total |
| D12 | IncomeTaxInAYear | emit captured control (null->blank); CalculateIncomeTaxInAYear computes but explicitly skips its write when submitted |
| E13 full question | **TotalIncomeTaxOverseas**, not IsIncomeTaxOverseas | emit captured control (null->blank); both getDataFromBaseForm L3 write and onChangeIsIncomeTaxOverseas are gated !isStatusSubmitted |
| E14 | InstallmentOfIncome | emit captured control, explicit null->0 in setFormData; caculateLPN preserves current value/default, never derives a different amount |
| E15 | NoticeOfCollection | emit captured control, explicit null->0 in setFormData; no later submitted writer |
| E16 full question | **TotalIncomeTaxDeduction**, not IsIncomeTaxDeduction | unresolved: CalculateTotalIncomeTaxDeduction/L13C callback; not a saved-final alias |
| F17a | UnderpaymentIncomeTax | emit captured control (null->blank); CalculateUnderpaymentIncomeTax returns immediately when submitted |
| F17b full question | **TotalApprovalInstallment**, not IsApprovalInstallment | emit captured control, explicit null->0 in setFormData; onChangeApprovalLetter is click-only and both active radio controls are disabled; valueChanges only enables/disables |
| F17c | IncomeTaxMustPaid | emit captured control (null->blank); CalculateIncomeTaxMustPaid returns immediately when submitted |
| Ganti SPT sebelumnya | ReplacementPrevious checkbox, conditionally rendered using model/previous/show flags | unresolved: exact visibility/presentation not an amount or guessed boolean string |
| F18a + Ganti caption | UnderpaymentIncomeInAmended plus conditional checkbox/previous lifecycle | unresolved: do not invent omission permission for NORMAL |
| F18b | UnderpaymentIncomeDueAmended | unresolved: normal callback clears to null; conditional presentation still needs full proof |
| D11 | TaxRate options CodeDescription, not raw TaxRate code | unresolved pending shared CIT_TAX_RATE original catalog custody |

525 calculation functions at 2832800..2838000 prove submitted returns, not that
editor-only arithmetic ran. This candidate deliberately never recomputes D12,
F17a or F17c: submitted values need not equal editing formulas. It preserves the
stored originals and typed evidence, including non-reconciling synthetic finals.
Only eight additional approved **amount** slots are implemented; nine remain
unresolved. Neither a captured radio code nor a same-named source leaf proves an
approved blank-name amount slot.

## Capability and native wiring

Additive `corporate-induk-submitted-v2` replaces v1 proof only when the existing
owned component protocol is available, all three **positive exact configured**
loaded-script pins match, id-ID/Asia/Jakarta are observed, and the eight unique
visible p-inputNumber hosts have their exact formControlName/id/mode/input
structure inside the owned Induk. Require disabled actual input nodes, the
read-only approval amount, and the two disabled IsApprovalInstallment radio
inputs: static submitted renderer bindings, not an assumption that an editor
click callback ran. Carry their ordered binding names as `controls`.
This is a structural selector read, not a value or checked-state read. Reuse the existing
bounded script readers, no new network route, storage read or business value read.
No optional proof means unchanged identity-only v1. Supplied malformed v2 refuses.
Adapter separately requires the exact selected submitted ?view=true route,
ICT_RCIT/ICT_RCITR, Normal/NORMAL on both owners, explicit IsMigrated=false,
explicit null PreviousFormData/LastSubmittedFormData, original component lifetime
and all eight present source controls. This slice does not support amendments,
Dollar/oil-and-gas, migrated or absent/unsafe operands. Existing whole-record
fallback, fatal source contradictions, Stop and final drain/held custody remain.

Raw dump stays as custody, never a sheet. projection_complete=False and
unprojected_induk_captions remain visible via derived_complete/reason and Audit.
No omission contract, layout expansion, generic dump exemption, new catalog adapter
or transport allowlist is introduced. The existing unrelated-unprojected gate stays.

## Shared catalog dependency (parent coordination)

Shared owner only: Induk TaxRate uses MAIN enum CIT_TAX_RATE (2988860) and 525
createTaxRatType (2787631): getSingleReferenceData(CIT_TAX_RATE), stable numeric
sort by parseInt(Code.substring(3,4)), then displayed CodeDescription is prefixed
with `${Code.substring(3,4)}.`. Approved template later removes that numeric prefix.
MAIN getSingleReferenceData at 3038044 can return a cache hit with **no request**;
its missing-cache path calls internalLoadBulkReferenceData at 3042005 with
`[{referenceType:'CIT_TAX_RATE', checksum:null}]`. The reviewed generic builder
then yields the no-body id-ID singleton GET ending
`/referencedata/api/currentreferencedata/id-ID/CIT_TAX_RATE` (no checksum, no pair
or bulk inference). This is source review, not proof that the request naturally
occurred in an owned attempt. Do not force it. Check the exact cache-copy/label
mutation lifecycle too: createTaxRatType mutates CodeDescription in the returned
objects; original bytes alone must not be assumed to prove a single-prefix render.
Require same-attempt original reference bytes, original typed rows/indices,
consumer ordering/version/clock and exact successful bound sequence before using
labels. Use _project_corporate_catalog/_reference_consumer_order/
_select_reference_version, not a sibling registry. This enum name alone is **not**
permission for an endpoint; the shared owner must independently review the exact
naturally emitted transport. Until integrated, TaxRate remains visibly unresolved.

## Verification plan

Tests first, GitHub runners only. Source-only RED is labeled until hosted output.
One populated adapter slice, then actual owned observer -> capture -> adapter ->
held replay -> saved/reopened workbook, never empty-only completion. Exercise
exact numeric/string/null/absence/negative-zero/precision/profile/pins/lifecycle,
submitted stored-final vs editing-formula distinction, proof overrides, Stop,
changed lifetime/attempts and truthful PARTIAL mapping. Exact-head full CI required;
no prior SHA green or synthetic test establishes live operator acceptance.
