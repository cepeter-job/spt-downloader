# L10-C native projection: source inventory and proof blocker

Status: **BLOCKED proposal; not a native implementation or acceptance record.**
The per-form request permits an explicit proof blocker. This record does not
remove L10-C's audit dump, change admission, or certify the Corporate fan-out.
Base inspected: `f5e40a2a4e02f0b03dcec6126a6416b5e10b3bbe`.

## Reviewed inputs

Local read-only inspection used the original saved job JSON, stdlib ZIP/XML
inspection of the approved workbook, and decoded public JavaScript. No product
module, pytest, browser fixture, application runtime, build, or live request ran
locally. No private source bytes, identities, amounts, files, or routes are
included here.

The actual bytes were independently SHA-256 checked against the configured
`resources/build-pins.json` entries, not merely checked for 64-hex shape:

| Provider | SHA-256 |
| --- | --- |
| `525.32c49782948fc5ef.js` | `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153` |
| `main.bed1449c3647a8ca.js` | `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44` |

These local source matches establish what was read, **not** that a particular
application capture loaded either provider. A future native observer must still
prove configured positive pins against its actual loaded providers, exact
selected submitted route, owned enabled structure, and relevant lifecycle.
Neither an arbitrary SHA nor a caller-supplied well-formed digest is permission.

## Source inventory before implementation

### Parent and child lifecycle

The pinned parent passes `l10cFormData` to `rshshr-citr-l10c-form`, obtains it
from `formData.L10cFormData`, and binds `outputCallback` to
`onCallbackForm("L10CForm", value)`. The callback patches the parent form's
`L10CForm` control. It has no L10-C-specific switch arm; that fact must not be
mistaken for absence of the common callback write.

The child `T_` implements:

- `ngOnChanges`: update main-header controls; when `formData` changes, call
  `setFormData` and retain `oldFormData`; disable the form when submitted.
- `setFormData`: map nonempty `ListTaxHavenCountry` through `setGrid1DataMap`,
  otherwise set the grid to null; then patch `Question` from
  `DeterminationOfTransactionQuestion ?? "0"`.
- `setGrid1DataMap` and `getGrid1DataMap`: exactly
  `NameOfTransactionPartner`, `TypeOfTransaction`, `CountryCode`,
  `TransactionValue`. They are not reference-label renderers.
- `getFormData`: map current grid values back, or return a null body;
  return `TotalTransactionValue: 0` unconditionally; return the question as
  `Boolean(Number(Question ?? 0))`.
- `attachValueChanges`: every form change emits `getFormData()` through
  `outputCallback`. `setGridValue` first patches the grid control and then
  assigns `l10cFormData.Grid1Data`.

Thus the returned total is neither a captured display total nor a reconciled
body sum. Intermediate callback values also are not original response data.
The disabled submitted form and common callback must be covered in hosted
lifecycle/no-late-overwrite tests, not replaced with a quiet timer or an
assumption based on key names.

### Exact grid, representations, and footer

The pinned `pn.CitrL10CGrid1Columns` declares Action, RowNumber, String,
Dropdown, Dropdown, Number. The submitted grid hides Action. Its five business
headers match the approved sheet exactly:

| Worksheet | Header | Original row field | Representation proof/status |
| --- | --- | --- | --- |
| A | `NO.` | none | UI row numbering; preserve order/duplicates and prove paginator numbering before populated admission. |
| B | `NAMA MITRA TRANSAKSI` | `NameOfTransactionPartner` | String interpolation, not a numeric/name coercion. |
| C | `Jenis Transaksi` | `TypeOfTransaction` | Dropdown reference label, **not the stored code**. |
| D | `NEGARA` | `CountryCode` | Dropdown reference label, **not the stored code**. |
| E | `NILAI TRANSAKSI (RUPIAH)` | `TransactionValue` | `Number` body consumer; not the separate `NumberInteger` consumer. Do not guess a zero-fraction rounding rule from the workbook format. |

In the reviewed MAIN export chain, CIT's `R.j_F` resolves through MAIN's
`j_` export to `_i.ReferenceDataTypeName = "TRANSACTION_TYPE"`; `R.gD1`
is the country reference. The reviewed `ui-grid-offline-body` Dropdown branch
uses the asynchronous `codeDescAsync` consumer with `inputColumn.ReferenceKey`.
The edit widgets independently specify `optionLabelName="CodeDescription"`
and `optionValueName="Code"`. Copying either stored code into C/D would produce
the wrong representation even though the source field name matches.

The L10-C grid passes only options, columns, and data into `ui-grid-offline`;
it does not bind `totalrow` or `multiTotalRow`. The same-record saved DOM oracle
has exactly those five headers, zero body rows, no footer rows, and
`footer_spans=[]`. `TotalTransactionValue` must not manufacture a footer.
The row edit dialog and Add/Save/Delete controls are not navigation authority.

### Non-table controls and approved resource

`resources/corporate_format.xlsx`, sheet `L10-C`, declares only:

- row 1: the existing tax-haven transaction heading;
- row 2 A:E: the five headers above;
- row 3 A:E: one reserved empty body slot;
- no merged ranges and no question/header-value slots.

`coretax_badan_template.BLOCKS['l10-c'] == [(2, 3, 3)]` agrees. The approved
resource remains unchanged. The rendered form separately has disabled
`PeriodYear`/`CollectorTin` header inputs and a `Question` radio pair with string
values `"1"`/`"0"` and static captions `Ya`/`Tidak`. The payload's question is
not thereby proved to be the displayed string/caption: `setFormData` and
`getFormData` use different representations, and the framework's checked/value
comparison still needs its pinned consumer proof. No new question row, omission
approval, or forced COMPLETE mapping is invented here.

## Application-owned evidence and the bounded gap

The newest saved native capture was inspected by allowlisted structural facts:

- L10-C has no projected fields, one audit dump table, and mapping
  `complete=False`, `unmapped_tables=1`, `unmapped_rows=3`.
- `L10cFormData` has exactly `ListTaxHavenCountry`, `TotalTransactionValue`,
  `DeterminationOfTransactionQuestion`; their type classes are respectively
  null, JSON number, and boolean. This is not evidence for populated rows.
- A same-record saved DOM oracle exists and has the table structure described
  above plus the two header controls and a Question control. Those controls
  are unresolved under the current approved worksheet; they must not disappear
  from completeness/custody accounting.
- The exact newest capture and its manifest each enumerate 572 URL-bearing
  response descriptors. None is a singleton `TRANSACTION_TYPE` catalog packet.
  The existing `CORPORATE_REFERENCE_REQUESTS` registry contains no such kind.

Absence from retained admitted packets does **not** prove that the portal never
requested it or that browser cache held it. It proves only that the available
native custody cannot supply that original catalog to a populated projector.
There is no populated same-record L10-C oracle in the evidence inspected here.

## Explicit blockers and next decision

1. **Populated C/D label proof:** the request/capture binding for the reviewed
   transaction reference and its actual original bytes, selected version/order,
   missing-code behavior, and final cache/response lifecycle are not established
   in the available retained capture. A code-as-label implementation, invented
   endpoint response, cache read, or forced catalog GET is not an alternative.
   Country must retain its independent existing original-packet proof too.
2. **Question representation/lifecycle proof:** the boolean/raw/string-radio
   boundary is not fully proved by the CIT source alone. Do not infer the
   affirmative branch from an empty-grid DOM oracle, read checked state in the
   native observer, or advertise the question as mapped into a nonexistent slot.
3. **Scope/acceptance:** an empty-only table could be a separately explicit
   fail-closed subset, with controls and original total retained as unresolved
   evidence and mapping remaining PARTIAL. It would not establish populated
   native L10-C or full worksheet completeness. This record does not silently
   substitute that subset for the requested general form.

Before implementation, review whether the next deliverable is (a) a deliberately
empty-only, honestly PARTIAL subset or (b) populated support after original
reference and framework-consumer evidence is available. Both preserve the
approved worksheet and all source bytes. No additional API traffic is proposed.
Any later catalog admission must be separately source/ownership reviewed, not
introduced by guessing from this identifier inventory.

## Required hosted verification after the proof gap is resolved

Write tests before implementation and execute only on GitHub runners. Bind all
results to the exact pushed head; do not count routed docs checks as product
verification. At minimum cover:

- absent/empty/wrong/malformed/unconfigured pins, including arbitrary valid
  64-hex strings; wrong route, model/status, ownership, disabled/detached form,
  missing/malformed lifetime and late source/callback changes;
- exact row shape, null/empty distinction, duplicate/order retention, numbering,
  literal text and unsafe numeric types/precision; no invented footer;
- actual original label packets, absent/malformed/contradictory catalogs,
  foreign/repeated sequences, duplicate versions, and code/label distinction;
- setFormData/getFormData/common-parent-callback behavior, submitted disabling,
  and proof that a later callback cannot overwrite the exported source values;
- immutable original evidence and explicit provenance for nondisplayed fields;
- adapter dispatch plus observer-produced proof, not a disconnected helper;
- actual saved/reopened workbook A:E values, row growth, E accounting format,
  unchanged resource bytes, and truthful PARTIAL mapping for unresolved controls.

No implementation tests or saved native workbook are claimed by this proposal.
No merge, closure, or Corporate consolidation is authorized by its existence.
