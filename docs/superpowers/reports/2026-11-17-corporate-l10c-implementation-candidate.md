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

## Follow-through: independent C-owned lifetime transport (not full completion)

The observer now calls `_observe_l10c_history` for an enabled L10-C with the
source-proven header/radio/grid structure. It binds the same actual form, grid,
table, tab and panel twice through `DetailJsonCapture.bind_l10c_structure` and
samples the C-owned capability. This is custody-only; it does **not** replace
that form's dump with a worksheet or dispatch `project_l10c`.

`_L10C_HISTORY` is armed on the original Document before inspected View. Its
independent relevant-structure budget retains the unique original corporate
root, current Induk host, C child, offline-grid/p-table/table chain and the two
header/two radio control identities. It never reads an input value, checked
state, Angular instance or table body/footer content. A remount, detach/reinsert,
transient disable/re-enable, replaced header/radio or Induk host remains a sticky
contradiction even if the final selectors look unchanged. Ordinary row churn
and a tab's presentation-only highlight change do not assert a new child.

The closed `corporate_l10c_lifetime` schema is manifest-owned, binds the exact
attempt/record/list/detail route and is validated by live iteration, held
`checkpoint_bodies`, and the adapter's absence-inclusive event fingerprints.
Descriptor overrides (even equal ones), malformed/null facts, missing parent
custody and mixed attempts remain fatal. Cleanup retains newly acquired handles
before the post-RPC Stop check. The C-only final sample is the last browser RPC
inside the existing late-response fence; Stop cannot seal a manifest.

**Combined history is deliberately not claimed.** If a C fact was already
offered and L7 or L8 history is requested, drain marks the attempt incomplete
with `unsupported-child-history-combination` rather than moving the stale-child
window to another sequential sampler or dropping a required fact. An unavailable
C capability that was never offered does not disable a valid legacy sibling.
The B owner's reviewed joint final-snapshot interface must be integrated by the
parent before that combination can be admitted. No competing shared registry
was created and no sibling worktree was edited.

### Exact remaining dependencies / bounded parent request

- Supply an already retained public VENDOR artifact matching configured SHA-256
  `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`, or authorize
  a narrowly scoped acquisition through the existing loaded-script mechanism.
  Independent local discovery found the exact CIT/MAIN bytes but no matching
  VENDOR artifact. No portal request or browser-cache read was made. Without
  the exact provider bytes, the source-bound default Number, radio bool/string
  comparison and paginator context cannot be truthfully called framework-proven.
- Integrate the parent's reviewed shared passive catalog producer (exact
  TRANSACTION_TYPE/COUNTRY_CODE request classes, original sequence sets,
  provider/order/version and final clock custody). This branch does not add a
  TRANSACTION_TYPE registry entry, force a GET or fabricate label evidence.
- Integrate the parent's reviewed B-owned final joint snapshot. C offers
  `bind_l10c_structure(...)`, `observe_l10c_lifetime(...)`, `_L10C_HISTORY` and
  `_capture_l10c_lifetime`; the shared owner must retain C and every already
  requested sibling through the same final browser RPC and end-clock boundary.
- Bounded layout question: may PeriodYear, CollectorTin and Question remain
  explicitly unresolved original controls with mapping PARTIAL and the existing
  Audit note, while only approved A:E body rows are projected? Or is a separately
  approved resource/layout change required? Nothing here approves omission or
  creates a row/sheet. The default remains honest PARTIAL.

The full populated observer -> capture -> semantic adapter -> held replay ->
saved/reopened native workbook acceptance case is **still missing**, not green
by quarantine. Existing pure saved/reopened candidate tests and the new lifetime
protocol/browser tests must not be relabelled as that end-to-end proof. No
protected AGENTS.md/resource/runtime/workflow changes, catalog transport changes,
active portal traffic, merges, or design-PR changes were made.
