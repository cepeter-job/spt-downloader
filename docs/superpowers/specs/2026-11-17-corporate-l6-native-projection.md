# L6 native projection: reviewed whole-rupiah subset

## Scope and evidence

This is the design/review record for PR #271, not proof of application-owned
live acceptance. The source is the decompressed corporate chunk
`525.32c49782948fc5ef.js`, SHA-256
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`, equal to
the existing reviewed build-pin resource. No portal bytes or private records
are committed here. The destination is the existing approved workbook L6
sheet, cells B2:B8; no resource/template changes are needed.

The pinned L6 component reads the primary `FiscalYearIncomeTax` root. Its
`setFormData` and `getFormData` map controls as follows:

| Template row | Payload key | Component control |
| --- | --- | --- |
| 2 | IncomeAsTheBasisOfInstallment | BasisIncomeOfInstallment |
| 3 | FiscalLossCompensation | FiscalLossCompensation |
| 4 | TaxableIncome | TaxableIncome |
| 5 | IncomeTaxPayable | IncomeTaxPayable |
| 6 | TaxCreditWitheld | OtherTaxCreditWitheld |
| 7 | IncomeTaxSelfpaid | IncomeTaxMustBeSelfpaid |
| 8 | FollowingFiscalYear | FiscalYearIncomeTaxInstallment |

Three additional payload keys are non-displayed edit markers:
`IncomeAsTheBasisOfInstallmentEdited`, `IncomeTaxPayableEdited`, and
`TaxCreditWitheldEdited`. They are validated as JSON booleans and retained as
typed original provenance, not fabricated worksheet values.

## Admission and presentation

- Only ICT_RCIT is reviewed. Its owner initializes both fraction limits to
  zero and uses the explicit Indonesian number locale. The currency-dependent
  alternative is deliberately unsupported.
- Require the exact ten-key root and nonnegative integral JSON number tokens
  within the existing 15-digit limit. Refuse fractional values rather than
  rounding them into a different submitted amount. Preserve token spellings
  in provenance; worksheet text is the reviewed whole-rupiah representation.
- Require an actual configured CIT digest, not merely a well-formed hash.
  Keep the existing single-source build-pin loader; add no duplicated digest.
- Require the same captured route, exact declared root, no unrelated grid or
  dependency, and matching submitted status/model. Identity and privacy
  checks still run upstream; none becomes a recoverable fallback.
- The observer adds only the versioned projection descriptor to the already
  inspected L6 owner. No new endpoint, page-property probe, business-value
  read, RPC, timeout, or click is introduced.
- The current conservative subset additionally requires two exact stored
  fixed points: taxable income is the nonnegative basis-minus-loss result,
  and self-paid tax is the nonnegative payable-minus-credit result. The
  frontend calculation callback is DRAFT-only, so these checks must not be
  described as evidence that a callback ran on a submitted SPT. A submitted
  record outside these fixed points remains unsupported.
- FollowingFiscalYear is copied, not recomputed from months. There is no
  claim that a new division/rounding calculation occurred.

The generic table is replaced only after all seven values pass. Raw capture
bytes remain unchanged under existing custody, and all ten original controls
are retained in projection provenance with response sequence/container/path.
No values or blocks of other forms may be dropped as a consequence. The
whole-record dump gate remains authoritative for other unprojected forms.

## Verification and limits

Tests cover field/caption order, immutable source/bindings, both fixed-point
refusals, null/wrong-typed/unknown/missing controls, fraction/precision limits,
edit-marker type and provenance, configured-build mismatch, route/lifecycle
refusals, adapter coverage and the seven numeric worksheet cells.

Execution is GitHub-runner-only. Local source/AST inspection is not a runtime
pass. The original PR head passed hosted Windows/portable/package checks;
any follow-up head requires fresh CI before consolidation. Private DOM/source
parity and application-owned live acceptance remain unverified.
