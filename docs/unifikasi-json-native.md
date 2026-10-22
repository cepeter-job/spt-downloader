# Unifikasi native JSON: reviewed public-source ledger

The four-form/five-grid implementation was merged in [PR #40](https://github.com/cepeter-job/spt-downloader/pull/40), merge `af3f1bf60198cc007055825b82ed8b11b02f2905`. Final head `f338f4d3063aaa425a79ff5a780cec4c3f180515` passed run `39198343837`: 3,103 Windows cases and 442 portable cases, reported separately because they overlap. Package artifact `12163381601` was read back with its manifest, frozen metadata and 37 embedded resources checked against the identical tested tree. These are historical runner/package results, not current-build live acceptance.

Native observation, reference custody, projection and connected synthetic Edge-to-Excel already exist. Dated reference branches and later acceptance remain bounded by the [approved completion design](superpowers/specs/2026-10-23-json-mode-completion-design.md); unsupported cases continue to fall back explicitly.

This is static evidence, not live acceptance. Offsets are character offsets in
UTF-8-decoded public JavaScript. No taxpayer response is included.

## Immutable sources

| Public asset | Bytes | SHA-256 |
|---|---:|---|
| `main.cccfdb820c20596c.js` | 4357138 | `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd` |
| `693.4de61c6eb2000c7e.js` | 63187 | `2694fdda5c23b7d5f0eefe0cf0a0c55caa0fe29acc590363f34684ed90188fe0` |

Both hashes were recomputed over existing public-asset copies using stdlib;
no browser profile, login state, credential or live endpoint was accessed.

## Identity and lifecycle

- Main offset 2978937: WithholdingTax enum literal `ICT_WT`.
- Main offset 2978050: ReturnSheetType.WithholdingTaxReturn literal `ICT_WTR`.
- Chunk 693 offset 455: read prefill endpoint
  `/prefillreturnsheet/withholding-tax`; its initial lifecycle request carries
  `RecordId` and `OnManualClick`.
- Chunk 693 around 45800: `mainFormData` receives `Payload`; `FormData` is parsed;
  `ReturnSheetStatusCode` controls `isStatusSubmitted`.
- Chunk 693 offset 49999: `checkImpersonating` does not assign `declarationBy`
  for Submitted/WaitingForPayment/Rejected/SigningInProgress. On the reviewed
  submitted branch the uninitialized parent value is consumed as `?? 0` by
  child `DeclarationBy` at 6366. Do not read claims or extend to draft lifecycle.
- Chunk 693 around 5900: child `getDataFromMainForm` binds `TaxPeriodCode`,
  `TaxIdentificationNumber`, `FullName <- Name`, `Address`, `PhoneNumber`,
  `StatementSignature`, and nested `Signer.StatementTIN/StatementFullName`.
  Null/missing signer values depend on claims and remain unsupported; empty
  strings are explicit source values, not missing values.
- Chunk 693 around 5750: child `ngOnChanges` guards its disable/checkbox-true
  patch with `null != this.getDataFromMainForm()`. The getter has no return, so
  JavaScript loose inequality yields false and the patch is unreachable. The
  initial `MyCheckBox=false` / `isChecked=false` ngModel remains false on fresh
  read-only observation; only the ngModelChange handler can later assign it.
  Never infer a checked declaration from SUBMITTED alone. Runner tests exercise
  this returnless-getter guard; MDN inequality documents `null != undefined` as
  false: https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Operators/Inequality

- Submission status is taken from INNER `FormData.SubmitInProgressStatus` and
  `FormData.ReturnSheetStatusCode`, not blindly from the outer prefill object.

## Reference catalogs

The chunk imports main module 99529 as `o`. Main re-exports module 66267 via
`kt` at offset 2770717.

| Consumer | Public binding | Main definition |
|---|---|---|
| TaxCertificate | chunk 693 `o.GiU.ReferenceDataTypeName`, offsets 15228/21844/24839/32508/35164 | 2970100: `EBUPOT_TAX_CERTIFICATE` |
| PaymentMethod | chunk 693 `o.kTH.ReferenceDataTypeName`, offsets 22035/25069 | 2876341: `EBUPOT_PAYMENT_METHOD` |
| list-ii-sp TaxObject | chunk 693 `o.CNx.ReferenceDataTypeName`, offset 31992 | around 2970941: `EBUPOTSP_TAX_OBJECT` |
| list-ii-cy TaxObject | chunk 693 `o.$i5.ReferenceDataTypeName`, offset 34655 | around 2970852: `EBUPOTCY_TAX_OBJECT` |
| TaxPeriodCode dropdown | chunk 693 `RshPeriodEnum=o.ZGR`, around 4900 | main 2975068: `PERIOD` |

- Main 3013125: existing read-only reference service constructs
  `/currentreferencedata/${language}/${types.join(",")}` and performs GET.
  Bind the exact origin, id-ID, ordered catalog types and GET/no-body; do not
  capture general reference traffic or permit other tax families implicitly.
- Main 3017141: `getActiveReferenceDataValue` chooses the first explicit null/
  empty ValidTo, otherwise a clock-dependent future/latest version. A single
  candidate is stable; unresolved multiple dated versions must stay unsupported.
- A later grid/card `refLookup` at 3120724 selects the first Code/value. Do not
  assume this later renderer is the reviewed table body consumer. Existing
  PPh21 behavior is the starting point, not proof that both consumers agree.
- For PERIOD dropdown labels, conservatively require unique codes; do not read
  selected DOM label/value to resolve duplicate catalog versions.

## Coverage boundaries

Four form hosts and five paginated appendix grids are already listed in
`coretax_masa_bindings.FORMS`. Induk's `IncomeTaxes` is a prefill tree, not an
invented sixth grid endpoint. Preserve reported footer fields independently of
row sums, explicit empty response counts, source provenance, and old negative
cases. Final CI and connected-capture evidence must be recorded separately.
