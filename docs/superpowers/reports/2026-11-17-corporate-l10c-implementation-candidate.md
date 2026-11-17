# L10-C implementation candidate and remaining admission blocker

Status: **populated pure projector implemented; native admission still BLOCKED**.
This implementation follows the full-populated scope decision after the separate
[docs-only proposal in PR #276](https://github.com/cepeter-job/spt-downloader/pull/276).
It does not replace that decision with empty-only support and does not complete
native L10-C. PR #276 remains separate and unchanged.

## Implemented boundary

`coretax_corporate_projection.project_l10c` transforms the exact four-column
original body plus its row numbering into the five approved worksheet columns.
It preserves literal partner names, source order and duplicate occurrences.
Transaction/country codes require independently supplied description inputs;
missing/blank/nonstring descriptions refuse rather than exporting a code.
Those inputs are **not** native catalog evidence. No observer or adapter
capability calls this pure candidate yet, so arbitrary labels or digests cannot
turn it into native permission.

`TransactionValue` follows the MAIN offline-body **Number** branch, not
NumberInteger or the online-grid `numberformat_ignoreprec` formatter. The
candidate accepts null as blank and only finite, exact-binary JSON numbers
within fifteen significant digits, absolute value at most 999999999999999,
and at most three normalized fractional digits. It never rounds a candidate.
For example the synthetic exact fraction 1234.125 becomes `1.234,125`, not
`1.234`. Numeric strings, booleans, signed zero, unsafe precision and wider
fractional/rounding profiles refuse. This bounded transformation is not a
loaded-framework or application-owned display-parity proof.

The source getter's `TotalTransactionValue` is retained as typed nondisplayed
provenance. It does not create a footer or a sum, and a nonzero stored total is
not silently replaced by the getter's constant zero. Question remains typed
unresolved evidence: no boolean-to-`Ya`/`Tidak` conversion and no claimed radio
selection. Its boolean support is local, not a widened shared Masa scalar rule.
Literal null and an empty body list remain distinguishable in provenance.

The candidate marks `projection_complete=False` and carries three unresolved
control identities (PeriodYear, CollectorTin, Question). L10-C's existing
renderer now counts those identities once and carries the fixed
`unprojected_l10c_controls` reason into mapping and the resume Audit. The approved
A:E layout, reserved empty accounting slot and resource bytes are unchanged.
The L10-C body parser alone accepts the reviewed default Number consumer's
three fractional digits; every other form and all footer parsers retain their
existing two-digit grammar. The stored safe value is never rounded to the
zero-decimal accounting display.
No new worksheet/question row or omission approval is implied.

## Source observations for shared infrastructure coordination

Source-only read against configured pins was repeated independently:

- CIT `525.32c49782948fc5ef.js`:
  `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
- MAIN `main.bed1449c3647a8ca.js`:
  `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
- Unchanged approved resource SHA-256:
  `47770d95a613ed496c8f121cbe39f41ea17947855e709ab0f931adbe9ca58ab0`.

The following offsets are **decoded character offsets**, not byte offsets:

- CIT 59312: `CitrL10CGrid1Columns`, `TRANSACTION_TYPE` and country
  reference keys, Number column and child `rsh-citr-l10c-grid1`.
- CIT 69597 onwards: child constructor, initial change handler, body mapping,
  question patch, getter, disabled state and common output emission.
- CIT 2623320: `Qm` passes **baseFormData** as the child's mainFormData and
  l10cFormData as formData, with `onCallbackForm("L10CForm", value)`.
- CIT 2651207: original `formData.L10cFormData` assignment.
- CIT 2695011: common parent callback patches `[t]` before its switch. The
  MainForm arm calls `setShowAttachment10abc(_.IsTransactionWithRelated)`.
- CIT 2705414: only the source's numeric-equivalent 1 enables the L10-A/B/C
  group; zero disables it and patches all three parent controls to null.
- MAIN 3879597: offline-body Number uses the `number` pipe without an explicit
  precision argument; NumberInteger is a distinct `1.0-0` branch.
- MAIN 3882118 and 4318830: ordinary Dropdown goes through codeDescAsync to
  `getReferenceDataDescription` with ReferenceKey, not raw-code fallback.
- MAIN 3036628: reference description selects the active code/version.
- MAIN 3038044: getSingleReferenceData first waits for active bulk loading,
  then reads its application cache; a cache miss calls internalLoadBulkReferenceData
  with one type and null checksum. That source permits a naturally emitted
  exact no-checksum singleton GET, but does not prove that this capture saw it.
- MAIN 3042005: internalLoadBulkReferenceData builds its language/type
  GET from a list, including optional checksum suffixes. Re-find the symbol
  before implementing a request matcher; a generic identifier does not
  authorize all batch/checksum variants.
- MAIN 4175512: offline grid emits `rowIndex+1`. The framework's paginator
  rowIndex semantics still need independently pinned/hosted proof; the pure
  candidate does not claim an observed multi-page numbering contract.

The transaction reference catalog is a common L10-A/L10-C dependency. Its
same-attempt passive packet/provider/order/version custody should have one
coordinated owner; this independent tree intentionally does not edit that
shared capture registry, response parser or manifest protocol.

## What still blocks full native support

1. No original TRANSACTION_TYPE packet is available in the reviewed retained
   capture. Its absence does not prove no portal request occurred. No cache
   read, forced GET, guessed batch URL, fabricated catalog or code-as-label
   fallback is permitted.
2. A native descriptor needs exact source-proven request classes and original
   sequence sets, typed catalog/version/order provenance, positive configured
   **loaded** CIT/MAIN/framework provider pins, and all final-drain/clock checks.
   Source-byte matching offline is not loaded-provider custody.
3. Require the selected submitted current Rupiah route, preceding observed
   Induk, current IsTransactionWithRelated choice and exact owned enabled
   form/grid/offline/p-table structure. A stable parent root alone does not prove
   an uninterrupted child. The descriptor and any stronger manifest lifetime
   must be checked independently during live and held replay; no descriptor
   overrides, mixed attempts, child remount or late overwrite are admitted.
4. Prove setFormData/getFormData/submitted-disable/common-parent callback and
   no-late-overwrite behavior against the same lifecycle, not a different
   synthetic source shape. The radio bool/string checked/value consumer and
   actual paginator numbering still require framework proof.
5. The approved sheet has no question/header slots. Keep those identities and
   their typed raw controls unresolved and mapping PARTIAL unless a separate
   layout/omission decision is approved. Native/source coverage alone is not
   mapping COMPLETE or financial-PDF/job acceptance.

## Exact bounded operator request after coordinated passive capture exists

Have the operator select **one already-authorized, submitted ordinary-Rupiah
SPT known to contain populated L10-C**, in one fresh application-owned,
Service-Worker-blocked context. Perform the normal inspected View/Induk/L10-C
read only. Retain the original same-attempt id-ID COUNTRY_CODE and
TRANSACTION_TYPE response packets if the application naturally emits the
reviewed exact request forms, with original response bytes, request method/no
body, request-object ownership, sequences, attempt/selected-record/Document
binding, loaded-provider digests and final-drain/clock custody. Keep all private
bytes local. Return only value-free counts/presence/type/pin-match summaries.

Do not issue a reference GET, read browser storage/cache, open edit controls,
clear caches in an existing context, reuse another record's catalogs, or try
alternate language/checksum/batch forms to make the run pass. If no admissible
original packet appears, record that bounded attempt as unresolved and stop.
A separately authorized same-record populated DOM capture is also needed for
row/description/number/radio comparison; never print taxpayer values.

## Verification status

Tests were written before their production changes. Local RED was established
by source/AST: `project_l10c` did not exist, and the L10-C renderer did not
consume `projection_complete`. No pytest, product import, fixture, build or EXE
ran locally. Runtime claims must be filled from exact-head Actions evidence.

The new hosted tests cover populated duplicates, literal strings and differing
code/label representations, exact fractional numbers versus integer rendering,
null/empty distinction, closed row/root shapes, missing/unsafe labels and
numbers, nondisplayed total/question evidence, saved/reopened approved workbooks
and resume PARTIAL notes, and actual hybrid DOM fallback without invented
catalog requests. They do **not** establish an admitted populated native packet,
owned child history, callback parity, or application-owned live acceptance.
