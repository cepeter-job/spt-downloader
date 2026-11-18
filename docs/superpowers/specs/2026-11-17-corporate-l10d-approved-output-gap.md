# Corporate L10-D: proven source, unapproved output destination

Status: **DECIDED — the operator confirmed on 2026-11-18 that L10-D's original
decision is non-display. L10-D therefore keeps fail-closed original custody and
gains no worksheet, no projection and no native admission. This record stays as
the evidence for that decision.**

Original status line (unchanged proposal text follows): **design proposal only;
L10-D native output is not implemented or accepted**.
Date: 2026-11-17. Inspected baseline: `f5e40a2a4e02f0b03dcec6126a6416b5e10b3bbe`
(`origin/main`, including #267). This is an independent per-form deliverable,
not permission to merge or consolidate the other native-form PRs.

## Decision and approval blocker

Keep the existing fail-closed behavior. Do not add a projection, dummy `fields`,
new worksheet, resource edit, endpoint, or exception to the dump gate in this PR.

L10-D is not merely missing a projector: its **intentional presentation exclusion**
must be resolved first. [AGENTS.md](../../../AGENTS.md), under corporate
presentation exceptions, excludes literal L10-B/L10-D only from new workbooks;
[the architecture contract](../../arsitektur.md#kontrak-excel-dan-transaksi-publikasi)
and #51 record that approval. `coretax_exporter._display_sections` implements it.
The operator-approved `corporate_format.xlsx` contains no L10-D sheet, and
`coretax_badan_template.FORMS` / `BLOCKS` have no L10-D destination. Induk/L8's
separately approved source-defined layouts do not grant approval for L10-D.

**Required decision:** explicitly approve replacing L10-D's display exclusion,
and approve either a sanitized L10-D reference sheet or a complete source-defined
layout. That decision must specify all fourteen displayed controls below,
section/label ownership, checkbox representation, date representation, header
identity handling, styles/merges, mapping completeness and historical-proof
compatibility. Alternatively, explicitly keep the exclusion and review a distinct
non-display semantic/custody contract before any native eligibility change.
Existing exclusion alone is not permission to ignore a dump at capture time.

This proposal supplies the source inventory for that decision; it does not claim
that its mapping table is an approved Excel template. Functional completion
remains blocked even if this documentation PR's CI is green.

## Reproducible evidence and its limits

Only existing local public frontend source, repository source/AST, read-only
workbook data and GitHub PR metadata were inspected. No Coretax API, browser
session, Angular state, business input/checked state, local product import,
pytest, native/Tk fixture, self-test, export, build or EXE was executed.
No private capture, workbook output or taxpayer value belongs in this PR.

| Evidence | Measured identity |
| --- | --- |
| Decompressed corporate chunk `525.32c49782948fc5ef.js` (cached as `z525.js`) | SHA-256 `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`, 3,334,844 bytes |
| Cached `main.bed1449c3647a8ca.js` | SHA-256 `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`, 4,467,267 bytes |
| Approved `resources/corporate_format.xlsx` | SHA-256 `47770d95a613ed496c8f121cbe39f41ea17947855e709ab0f931adbe9ca58ab0` |

Both JavaScript hashes equal the corresponding entries in
[`resources/build-pins.json`](../../../resources/build-pins.json). Matching
cached bytes prove the source version inspected, **not** that a live document
loaded or consumed it. No pin was changed.

The reference sheet inventory, read with openpyxl without saving, is exactly:
`L1-D`, `L2`, `L3`, `L4`, `L6`, `L7`, `L9`, `L10-A`, `L10-C`, `L11-A`,
`L11-B`, `L11-C`.

Source anchors below use zero-based character offsets in UTF-8-decoded source,
not byte offsets. Reproduce them only after checking the entire file hash:

- Corporate L10-D component `let et=...`: `[77075, 91502)`;
  `ngOnChanges`: 77870, `setFormData`: 78253, `getFormData`: 79101,
  `getDataFromMainForm`: 79904, static constants: 80997, template: 87168.
- Parent `Km` renders `rshshr-citr-l10d-form`, binds `mainFormData` to
  `baseFormData`, and `formData` to `l10dFormData`; its selector occurs at 2623773.
  `mapPrefillData` assigns `baseFormData = t.Payload` at 2646914;
  `mapFormData` reads `this.formData?.L10dFormData` at 2651281.
- Parent `setShowAttachment10d` is at 2705579; the final conditional template
  references `showAttachment10d` at 2734706.
- MAIN module `83146` starts at 4318875; the exact selector
  `selectors:[["ui-input-date"]]` occurs at 4324340. Do not substitute the
  different `ui-input-date-2` implementation. Environment
  `primengDefaultDateFormat:"dd-mm-yy"` is at 2733473.

## Exact source-to-control inventory

Title: `IKHTISAR DOKUMEN INDUK DAN DOKUMEN LOKAL`.
The current source object is parsed from `Payload.CurrentFormData`, then its
case-sensitive `L10dFormData` is passed unchanged into the child.
`coretax_corporate.FORMS['L10-D']` declares that same root and selector.

The twelve child output keys are **exactly ten checklist keys and two dates**.
`getFormData()` does not emit `CollectorTin` or `PeriodYear`; those two disabled
header controls come from the parent's **outer Payload**, not an assumed alias
in `CurrentFormData.MainFormData`.

The following are literal static captions from the pinned child template, not
translations invented from property names. The section names here describe
visual source headings; they are not asserted legacy extractor `group` values.

| Owner / visual section | Payload source | Child control | Literal displayed caption |
| --- | --- | --- | --- |
| HEADER | `Payload.PeriodYear` | `PeriodYear` | Tahun Pajak |
| HEADER | `Payload.TIN` | `CollectorTin` | Nomor Identitas WP |
| I. IKHTISAR DOKUMEN INDUK | `CurrentFormData.L10dFormData.MasterDocumentary1` | `MasterDocumentary1` | Struktur dan bagan kepemilikan grup usaha serta negara atau yurisdiksi masing-masing anggota grup usaha |
| I. IKHTISAR DOKUMEN INDUK | `CurrentFormData.L10dFormData.MasterDocumentary2` | `MasterDocumentary2` | Kegiatan usaha yang dilakukan oleh grup usaha |
| I. IKHTISAR DOKUMEN INDUK | `CurrentFormData.L10dFormData.MasterDocumentary3` | `MasterDocumentary3` | Harta tidak berwujud yang dimiliki grup usaha |
| I. IKHTISAR DOKUMEN INDUK | `CurrentFormData.L10dFormData.MasterDocumentary4` | `MasterDocumentary4` | Aktivitas pembiayaan dan keuangan dalam grup usaha |
| I. IKHTISAR DOKUMEN INDUK | `CurrentFormData.L10dFormData.MasterDocumentary5` | `MasterDocumentary5` | Laporan keuangan konsolidasi entitas induk dan informasi perpajakan terkait transaksi afiliasi |
| II. IKHTISAR DOKUMEN LOKAL | `CurrentFormData.L10dFormData.LocalDocumentary1` | `LocalDocumentary1` | Identitas dan kegiatan usaha yang dilakukan Wajib Pajak |
| II. IKHTISAR DOKUMEN LOKAL | `CurrentFormData.L10dFormData.LocalDocumentary2` | `LocalDocumentary2` | Informasi transaksi afiliasi dan transaksi independen yang dilakukan Wajib Pajak |
| II. IKHTISAR DOKUMEN LOKAL | `CurrentFormData.L10dFormData.LocalDocumentary3` | `LocalDocumentary3` | Penerapan prinsip kewajaran dan kelaziman usaha |
| II. IKHTISAR DOKUMEN LOKAL | `CurrentFormData.L10dFormData.LocalDocumentary4` | `LocalDocumentary4` | Informasi Keuangan Wajib Pajak |
| II. IKHTISAR DOKUMEN LOKAL | `CurrentFormData.L10dFormData.LocalDocumentary5` | `LocalDocumentary5` | Peristiwa-peristiwa/kejadian-kejadian/fakta-fakta non keuangan yang mempengaruhi pembentukan harga atau tingkat laba |
| III. PERNYATAAN PENYELENGGARAAN DAN PENYEDIAAN DOKUMEN INDUK DAN DOKUMEN LOKAL | `CurrentFormData.L10dFormData.MasterDocumentAvailableDate` | `MasterDocumentAvailableDate` | 1. Dokumen Induk telah tersedia pada tanggal: |
| III. PERNYATAAN PENYELENGGARAAN DAN PENYEDIAAN DOKUMEN INDUK DAN DOKUMEN LOKAL | `CurrentFormData.L10dFormData.LocalDocumentAvailableDate`, guarded by `MasterDocumentAvailableDate` | `LocalDocumentAvailableDate` | 2. Dokumen Lokal telah tersedia pada tanggal: |

### Checklist and date rules are not raw-leaf equivalence

- Each checklist control starts as `false`; `setFormData` uses its own
  `this.formData.<key> ?? false`. The template binds a binary `p-checkbox`,
  with matching literal `name`, `formControlName`, `id`, `inputId` and `label for`.
  Missing, null, false, zero and a string are not interchangeable source facts.
  A conservative first implementation should admit explicit JSON booleans only
  until any coercive/default branches have their own reviewed proof. Never
  silently normalize numbers or strings to booleans or manufacture missing leaves.
- Existing DOM `FIELDS_JS` writes `String(e.checked)` for a checkbox, not an
  invented `Ya`/`Tidak` caption. This is source inspection of the legacy
  renderer, not authorization for native observers to read checked state.
- `MasterDocumentAvailableDate` is patched with
  `master ? new Date(master) : null`. **Local date is also guarded by master**:
  `LocalDocumentAvailableDate: this.formData.MasterDocumentAvailableDate ?
  new Date(this.formData.LocalDocumentAvailableDate) : null`.
  Thus a present local date need not display, and a truthy master with an absent,
  null or invalid local value cannot be mapped by a naive date copy. Preserve
  this source behavior; do not silently fix the apparent cross-field defect.
- Both actual `ui-input-date` hosts bind the form group, their exact `controlName`,
  `maxDate=today`, and `_env.primengDefaultDateFormat`. MAIN's module 83146 passes
  the group control to `p-calendar` (`dataType='date'`, default format `dd-mm-yy`).
  Its separate no-group and user-action conversion paths are not proof that an
  initial group-bound patch runs those conversions. A date needs the actual
  `new Date` / local calendar / framework rendering proof, strict accepted source
  syntax and id-ID/Asia/Jakarta context. Do not borrow L3/L11-A date allowances,
  slice an ISO string or use the replay machine's timezone/clock.
- No grid, footer, amount, percentage or reference-catalog lookup occurs in this
  child component. Its captions are static. There is no basis for a new L10-D
  API or catalog fetch, numeric rounding, optional numeric-analysis substitute,
  or locale guess. Source validation methods are not capture-completeness proof.

`GROUP_JS` recognizes headings such as `.p-panel-title`, not arbitrary `<b>`
labels. The visual I/II/III headings in this template are bold labels, so their
strings must not be asserted as captured `group` metadata without a hosted,
faithful rendered fixture. Exact checkbox/date label association and the full
fourteen-control structural inventory also remain to be exercised there.

## Lifecycle and custody: established source, remaining proof

The inspected parent parses `CurrentFormData` and `PreviousFormData`, calls
`mapFormData`, and enables L10-D from `IsObligationTransferPricing` through
`setShowAttachment10d`. It later repeats attachment selection in the Induk
`onCallbackForm('MainForm', ...)` path. Its setter uses loose `1 == value` and
`0 == value`; the latter disables the attachment and patches `L10DForm:null`.
The child change hook sets header data, patches a changed `formData`, and then
disables the form when `isStatusSubmitted` is true. `getRawValue()` retains
those disabled controls for the child's callback.

The frontend's `isStatusSubmitted` is **broader than SUBMITTED**: `fillForm`
also sets it for waiting-for-payment, rejected, signing-in-progress, canceled,
history and from-core contexts. It is not an admission fact on its own.

A future implementation must separately prove:

1. Exact selected `SPT Dilaporkan` identity, literal ordinary corporate tax/model,
   `Payload.ReturnSheetStatusCode == 'SUBMITTED'`, matching selected/payload model,
   and exact selected current non-history route. Initially require the inspected
   literal `?view=true` route, no alternative query/fragment/identity spelling.
2. Positive valid 64-hex **equality**, not presence or `None == None`, for each
   loaded provider whose source semantics it consumes: corporate chunk, MAIN's
   actual date helper/environment, and the reviewed framework bytes for the
   checkbox/calendar branch. Cached hashes do not supply loaded-provider proof.
   Use existing reviewed pins; do not add unused proof keys or probe business state.
3. Fresh owned component lifetime, preceding selected Induk, and stable enabled
   L10-D tab/panel/form/control ownership through final drain and held replay.
   The outer flag's initial value alone cannot certify the final Induk callback.
   Prove the exact supported outer/current flag profile before admitting it;
   distinguish absent, null, numeric1, boolean and contradictory values.
4. Explicit valid predecessor encoding and a reviewed no-prior branch first;
   amendments/history and unproved asynchronous/default/date profiles stay
   unsupported. No timer or quiet-period heuristic can establish finality.
5. Original typed per-leaf provenance including overwritten/guarded operands,
   response sequence, actual container and path: header sources belong to
   `['Payload']`; child keys to `['Payload', 'CurrentFormData']`. Preserve numeric
   lexemes for the header year, literal identity text, raw originals and absence
   facts separately. Never replace the guarded local date's original source.

These are outstanding implementation requirements, not observed live facts.
No same-record active L10-D DOM/native parity oracle or submitted lifecycle
acceptance was established by this investigation. Inert/disabled/null evidence
must not be extrapolated into active-form support.

## Why the existing generic renderer does not close the gap

`coretax_exporter.render_form` can print arbitrary captured fields/tables into
`Bagian / Field / Nilai sumber / Nilai numerik (opsional)`. However:

- `_display_sections` removes corporate L10-D **before** `record_forms`, title
  planning and `_export_form_workbook` choose any renderer. This is an explicit
  approved display policy, not an accidental missing dispatch branch.
- The corporate template has neither a destination nor approved bindings for
  L10-D. The generic branch supplies no corporate per-form mapping report (its
  explicit incomplete-report branch is PPN-only). It cannot stand in for
  reviewed fourteen-control mapping/completeness semantics.
- `coretax_corporate.observe_forms` currently binds L10-D's root only; there is
  no L10-D semantic `projection` producer or `apply_projections` branch.
  Source capture coverage is not worksheet projection.
- `coretax_json.has_audit_dump_tables` refuses a section with the exact generic
  dump headers and no `fields`; `coretax_browser.capture_detail_hybrid` applies
  that gate before choosing native output. It inspects all decoded sections,
  not presentation-filtered sections. Keep that whole-record DOM fallback.
  The existing projected-fields exception is not permission to emit one
  placeholder/checkbox while discarding eleven child controls and two headers.

Therefore a generic destination is a possible **new approval choice**, not a
proven already-approved output path. No implementation is justified by its
mere availability. The existing display exclusion, null/disabled binding rules,
all raw capture/proof namespaces and legacy physical-sheet readback remain intact.

## Approval and implementation acceptance checklist

- [ ] Operator approves explicit output policy and complete layout/type contract;
      only then review any protected AGENTS.md/resource change separately.
- [ ] Prove active submitted field ownership, final Induk selection and full
      date/checkbox representation against the exact pinned providers.
- [ ] Add synthetic Actions tests for all ten true/false checklist controls,
      header ownership/identity/year, strict types, unknown/missing keys and the
      cross-field date guard (master absent/null/empty versus present; local
      absent/null/valid/invalid; unsupported offsets/timezones).
- [ ] Add observer/adapter/held-reader tests for wrong/missing pins, route/status/
      model/flag contradictions, predecessor encodings, duplicate/foreign labels,
      changed ownership, detach/reinsert, Stop and late replies. Never read values
      in the native structure observer or grant a new endpoint.
- [ ] Exercise real dispatch and all fourteen controls, retain typed original
      custody evidence and truthful unresolved/partial reports; save/reopen the
      approved destination and verify physical proof, old excluded-form links
      and preservation of the source checkpoint. No tiny-subset gate bypass.
- [ ] Preserve existing `tests/test_corporate_native_dump_gate.py`,
      `tests/test_corporate_presentation.py` and affected observer/adapter/export
      regressions. All product tests, self-tests, packaging and artifact readback
      run on GitHub runners at the exact implementation head/merge tree.
- [ ] Obtain separate application-owned, build-matched operator live acceptance;
      native source, mapping, PDFs and complete publication remain distinct gates.

For **this docs-only proposal**, verify the sole Markdown diff and unchanged
protected/resource bytes, open the individual PR, and inspect its actual
Actions route/checks. Docs-mode skipped product tests/package jobs are expected
and must be reported as skipped, not functional verification. Do not merge,
close, or consolidate this proposal or other form PRs as part of this task.
