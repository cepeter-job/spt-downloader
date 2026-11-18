# L10-B: source mapping and unapproved output destination

> **Historical design record (superseded):** Preserved verbatim from PR #277 with this archival note. The original observations and provider pins describe the November 17, 2026 inspected baseline, not authority for later loaded builds. Implementation is tracked in PR #282 and consolidated in PR #287. This document does not authorize new transport, worksheet mapping, admission, or merge. For L10-B, the approved outcome remains non-display custody with no L10-B/L10-D worksheet.


Status: **PROPOSAL — IMPLEMENTATION BLOCKED**. This is a docs-only per-form
proposal, not a native projector, template approval, or functional-green form.
It must not count as completed L10-B implementation in a consolidated native
Corporate PR. No merge is requested by this investigation.

## 1. Decision and exact approval blocker

There is no approved L10-B output destination on inspected baseline
`f5e40a2a4e02f0b03dcec6126a6416b5e10b3bbe` (`origin/main` when this worktree
was created). The gap is **both a missing layout and an explicit exclusion**:

- `resources/corporate_format.xlsx` has exactly twelve reference sheets:
  L1-D, L2, L3, L4, L6, L7, L9, L10-A, L10-C, L11-A, L11-B and L11-C.
  Its SHA-256 is
  `47770d95a613ed496c8f121cbe39f41ea17947855e709ab0f931adbe9ca58ab0`.
  There is no L10-B reference sheet.
- `coretax_badan_template.py:FORMS` declares those same twelve sheets.
  `template_workbook` adds only the separately approved Induk/L8 references;
  neither `BLOCKS` nor `render_template_form` has an L10-B layout.
- `AGENTS.md`, under **Corporate presentation exceptions**, explicitly excludes
  literal L10-B/L10-D from new Corporate workbooks while preserving checkpoints
  and historical physical-proof/index namespaces. This is not merely an
  unimplemented fallback. PR #51 records the explicit presentation approval;
  `docs/arsitektur.md` repeats the boundary.
- `coretax_exporter.py:_display_sections` applies that exclusion **before**
  `record_forms`, sheet naming, `workbook_proof`, and `_export_form_workbook`.
  Thus `render_form`, although available for generic forms, is not an approved
  way to make L10-B appear. Bypassing the filter would change the output contract.
  The generic Corporate branch also supplies no L10-B template mapping report;
  a sheet merely being writable would not prove mapping completeness.
- `tests/test_corporate_presentation.py` protects the new-workbook omission,
  unchanged checkpoints, non-Corporate exceptions and historical L10-B links.
  These tests must not be removed or weakened to obtain a native result.

**Approval needed:** explicitly supersede the L10-B-only new-workbook exclusion,
choose an approved destination/layout (the candidate below or an operator
reference), and approve its field/label/answer/completeness contract. Leave
L10-D excluded. A later implementation must update the protected `AGENTS.md`
contract through its normal approval path, plus architecture documentation and
focused regressions. Approval of this investigation alone is not that approval.

This PR changes no product code, resource, pin, gate, tests or policy. Current
L10-B output behavior is unchanged.

## 2. Public source evidence and reproducibility

The inspected file is the already supplied, decompressed public bundle
`C:/Users/kpp096/AppData/Local/hermes/cache/scratch/z525.js`, **3,334,844 bytes**.
It matches the existing `resources/build-pins.json` entry for
`/returnsheets/id-ID/525.32c49782948fc5ef.js`:

```text
SHA-256 500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153
```

Offsets below are zero-based UTF-8 byte offsets in those exact bytes, with
half-open ranges. They identify source, not taxpayer data or new allowlist pins.
Do not accept any other digest as equivalent.

| Evidence | Offset / range | Source anchor |
| --- | --- | --- |
| Complete L10-B component | `[38762, 59253)` | `Li=(()=>{class l` through `}),l})()` |
| Payload-to-control mapping | `40474` | `setFormData(){` inside that component |
| Reverse control mapping | `42461` | `getFormData(){` inside that component |
| Header owner | `43352` | `getDataFromMainForm(){` |
| Visible captions and radio attributes | `43899` | `consts:function()` |
| Parent child-input binding | `2622937` | `function jm(l,s)` |
| Current root assignment | `2651156` | `this.l10bFormData=this.formData?.L10bFormData` |
| Induk callback | `2695011` | `onCallbackForm(t,_)` |
| Attachment visibility setter | `2705414` | `setShowAttachment10abc(t)` |

The component slice has SHA-256
`ee72397a60b0f529525bd518a4612b61ff96b6636a694f67ad9aa4a14e2a2766`.
A source/data-only inventory checked all fifteen forward/reverse mapping pairs,
all thirty radio declarations and the reference workbook sheet inventory.
It parsed Python AST and workbook ZIP metadata without importing product modules
or executing the public JavaScript. The public bundle is not copied into this PR.
These measurements establish static source correspondence, **not observed DOM
state, current application custody, runtime parity or live acceptance**.

## 3. Exact source-to-control mapping

The owning host is `rshshr-citr-l10b-form`; the registry entry in
`coretax_corporate.py:FORMS` binds **`L10bFormData`**, not `L10BFormData`.
The parent parses `Payload.CurrentFormData`, assigns that root to `l10bFormData`,
and passes it as the child's `formData`. `mainFormData` is instead the parent's
`baseFormData` (the outer **Payload**, not `CurrentFormData.MainFormData`).

Each row below is an explicit mapping in `setFormData`, reversed in
`getFormData`. Visible captions come from the component template, **not** from
English control names or legacy `ariaLabel` descriptions. For example,
`PricingMethodology` visibly asks about **Dokumen Induk**, not a methodology.
No guessed aliases or code-to-label catalogs are needed or permitted.

| Payload leaf under `L10bFormData` | DOM `formControlName` | Visible prompt in source order |
| --- | --- | --- |
| `Question1a` | `OwnershipStructure` | Transaksi dengan pihak yang memiliki hubungan istimewa karena kepemilikan saham/penyertaan |
| `Question1b` | `OrganizationStructure` | Transaksi dengan pihak yang memiliki hubungan istimewa karena penguasaan |
| `Question1c` | `PersonalAspects` | Transaksi dengan pihak yang memiliki hubungan istimewa karena hubungan keluarga |
| `Question1d` | `DetailedDescription` | Transaksi yang dilakukan antarpihak yang tidak memiliki hubungan istimewa tetapi Pihak Afiliasi dari salah satu atau kedua pihak yang bertransaksi tersebut menentukan lawan transaksi dan harga transaksi. |
| `Question2a` | `TaxpayerTransactionWRP` | berdasarkan keadaan yang sebenarnya. |
| `Question2b` | `TaxpayerTransactionWC` | pada saat Penentuan Harga Transfer dan/ atau saat terjadinya Transaksi yang Dipengaruhi Hubungan Istimewa. |
| `Question2c` | `TaxpayerActAsParty` | sesuai dengan: |
| `Question3a` | `CharacteristicsOfProducts` | a. nilai peredaran bruto tahun pajak sebelumnya dalam satu tahun pajak lebih dari Rp50.000.000.000,00 (lima puluh miliar rupiah); |
| `Question3b` | `FunctionalAnalysis` | b. nilai Transaksi Afiliasi tahun pajak sebelumnya dalam satu tahun pajak lebih dari Rp20.000.000.000,00 (dua puluh miliar rupiah) untuk transaksi barang berwujud; |
| `Question3c` | `EconomicConditions` | c. nilai Transaksi Afiliasi tahun pajak sebelumnya dalam satu tahun pajak: lebih dari Rp5.000.000.000,00 (lima miliar rupiah) untuk masing-masing penyediaan jasa, pembayaran bunga, pemanfaatan barang tidak berwujud, atau Transaksi Afiliasi lainnya; |
| `Question3d` | `TermsOfTransaction` | d. Pihak Afiliasi yang berada di negara atau yurisdiksi dengan tarif pajak penghasilan lebih rendah daripada tarif pajak penghasilan |
| `Question3e` | `TaxpayerBusinessStrategy` | e. Grup Usaha dengan peredaran bruto konsolidasi paling sedikit Rp11.000.000.000.000,00 (sebelas triliun rupiah)  pada tahun pajak sebelumnya |
| `Question4a` | `PricingMethodology` | Dokumen Induk |
| `Question4b` | `ComparativeData` | Dokumen Lokal |
| `Question4c` | `ApplicationOfTransfer` | Laporan per Negara |

There are **15 question controls / 30 radio options**, plus two disabled header
inputs: `PeriodYear` with caption `Tahun Pajak`, and `CollectorTin` with caption
`Nomor Identitas WP`. `getDataFromMainForm` fills them from outer `Payload.PeriodYear`
and `Payload.TIN`, respectively. Neither header is returned as part of the
fifteen-question `getFormData` object. Do not substitute `MainFormData.Tin`,
`TaxYear`, `TaxPeriodYear` or a listing caption merely because it looks similar.

### Answer representation is not a raw field copy

Every question is patched as `JSON.stringify(sourceQuestion)` when the source
is non-null; the source repeats the same non-null predicate twice. Null or an
absent leaf patches null. Each `p-radioButton` has the literal **string** value
`"false"` with caption `Tidak`, or `"true"` with caption `Ya`.
Consequently the proposed boolean-only render rule is explicit:

- literal JSON boolean `false` -> control string `"false"` -> `Tidak`;
- literal JSON boolean `true` -> control string `"true"` -> `Ya`.

This is a source-backed representation rule, not permission for general truthy
conversion. Numeric 0/1, strings `"true"`/`"false"`, objects and arrays must not be
coerced to these answers. A missing/null leaf is **not** `Tidak`; the first
proposed implementation subset below refuses it. Preserve the original typed
boolean and its exact source path independently of the displayed caption.

## 4. Candidate minimal layout — NOT approved or implemented

Candidate destination: one observed-only sheet named `L10-B`, with two columns:
source statement/prompt and its source-projected answer. No invented table,
amount column, totals, DER calculation, accounting format, question renumbering
or numeric analysis. Styles, dimensions and final coordinates require review;
this text is not an approved template.

Keep the following source order and context rather than displaying isolated
fragments or the misleading English control names:

1. Title: `PERNYATAAN TERKAIT TRANSAKSI YANG DIPENGARUHI HUBUNGAN ISTIMEWA`.
   `HEADER`, then the two header captions and their qualified outer-source values.
2. `1. Mengenai Hubungan Istimewa`, followed by
   `Bahwasanya kami telah menerapkan Prinsip Kewajaran dan Kelaziman Usaha`,
   then Question1a..Question1d using the table's literal prompts.
3. `2. Mengenai transaksi`, followed by that same full statement,
   then Question2a..Question2c. Retain both subordinate labels for Question2c:
   `- tahapan penerapan Prinsip Kewajaran dan Kelaziman Usaha; dan` and
   `- tahapan pendahuluan dalam hal terdapat Transaksi Yang Dipengaruhi Hubungan Istimewa tertentu.`
   The source has a nonbreaking space before `tertentu`; retain the source
   text rather than silently replacing this with an unrelated caption.
4. `3. Mengenai Dokumentasi Penerapan Prinsip Kewajaran dan Kelaziman Usaha`,
   `Bahwasanya kami memiliki`, then Question3a..Question3e.
5. `4. Mengenai Dokumen Penentuan Harga Transfer`,
   `Bahwasanya kami telah menyelenggarakan:`, then Question4a..Question4c.

Only a qualified answer uses `Ya`/`Tidak`. Static prompts containing rupiah
thresholds are captions, **not captured monetary amounts**. Do not parse them
into analysis columns or infer a taxpayer's threshold/category from the answer.
Do not collapse an all-false form as empty: false is fifteen real source answers.

An operator may instead provide an approved reference layout. Reconcile every
slot to this source mapping before implementing; neither copying L10-A/L10-C
geometry nor invoking the generic renderer constitutes that approval.

## 5. Proposed finite native boundary after approval

This section is an implementation acceptance target, **not current admission**.
Start with a current-only submitted ordinary Rupiah `ICT_RCIT/ICT_RCITR`, literal
Normal/NORMAL, non-history selected `?view=true` route, with preceding observed
Induk and the existing fresh capture-owned Document/component lifetime.
Require original `PreviousFormData` and `LastSubmittedFormData` explicitly null.
No predecessor/amendment/oil-and-gas/USD branch is proved by this proposal.

The source initializes `showAttachment10abc` false, sets it from outer
`IsTransactionWithRelated` in `fillForm`, and sets it again from the Induk
`MainForm` callback. Its setter uses loose `1 == value` / `0 == value`; this is
**not** permission to accept every coercible encoding. The initial proposed
subset requires explicit JSON numeric one on both outer and current Induk
`IsTransactionWithRelated`, plus the actual original enabled L10-B tab/panel/form
before and after observation. Missing, null, contradictory or differently typed
flags stay unsupported. Do not infer visibility from the saved root alone, or
borrow a sibling form's lifecycle proof. Current source is not evidence that
this callback/branch ran in an owned live attempt.

Require a present `L10bFormData` object with **exactly** the fifteen keys above,
each a literal JSON boolean. Unknown/missing/extra/case-changed keys, duplicate
JSON keys, null roots/leaves, partial objects and numeric/string encodings are
not in the proposed subset. Disabled/absent panels retain the existing separate
null-only evidence rules; no object root may be discarded as inert. Header
binding must separately prove the exact outer `TIN` identity and `PeriodYear`
against selected scope, using their original types/lexemes. Never render an
unqualified header or borrow an alias to complete a sheet.

A future structure-only observer must verify the unique original host, tab and
panel, the two header control identities/captions, all fifteen named radio pairs
and literal option attributes/captions, their local prompt/section ownership,
and absence of extra business controls/tables. It must read **no selected,
checked, input-value or Angular business state**. Static source declaration
alone cannot manufacture observed field labels, grouping or visibility.

Keep positive exact loaded-provider digest equality against reviewed pins,
matching literal route/selected return, original same-attempt primary response,
manifest ownership, privacy/identity contradictions, Stop priority, budgets and
final drain. A boolean/text-only render rule needs no new locale/timezone probe,
reference lookup, endpoint, network acquisition, preload or timer. Any framework
radio-selection behavior relied on by implementation still needs its reviewed
provider/parity proof; the 525 hash is not an arbitrary substitute for it.

Retain original evidence leaves/dump and typed source provenance for every
answer/header: response sequence, `Payload` versus parsed `CurrentFormData`
container, exact leaf path and explicit render rule. A later projector must be
wired through both `observe_forms` and `apply_projections`, with held replay
preserving the same custody. No detached pure helper alone grants native use.

The existing `has_audit_dump_tables` gate must stay fail-closed for unprojected
sections, including L10-B. Adding placeholder fields, stripping the dump,
removing a section or exempting an excluded sheet is not a projector. Keeping
only a subset of questions must keep mapping explicitly incomplete through the
existing `projection_complete` / `derived_complete` reporting path, with a
visible fixed reason and truthful unresolved counts. A native capture flag or
absence of an L10-B mapping report is never a mapping-complete result.

## 6. Proof gaps and later acceptance

No same-record DOM oracle, actual private L10-B payload or owned live radio
structure was inspected in this source-only investigation. Thus header encoding,
actual extracted labels/group metadata and runtime radio parity remain proof
gaps, separate from the output-approval blocker. No taxpayer values, private
captures, screenshots or generated workbook were added to this PR.

After explicit output approval, a separate implementation PR must have
GitHub-runner-only regressions covering:

- all fifteen source-to-control mappings and exact captions/context; false/true
  parity, all-false preservation, ordered output and original typed provenance;
- missing/extra/mistyped keys, unsupported flags/models/predecessors, wrong route,
  missing/wrong pins, foreign/duplicate/changed owners and late custody failures;
- observer -> adapter -> held replay -> saved/reopened workbook/report behavior,
  without weakening dump refusal or using placeholder fields;
- approved L10-B visibility, only observed forms, unchanged L10-D exclusion,
  checkpoint preservation and historical proof/index links;
- qualified headers, exact slot coverage, truthful incomplete reporting and full
  exact-head Windows/security/package gates.

Application-owned, build-matched live acceptance is a later operator step.
Capture coverage, native eligibility, template mapping, PDF completion and whole
job completion remain independent. Do not consolidate L10-B as functionally
green until its approved implementation and those relevant gates actually pass.

## 7. Verification of this proposal

Performed locally: pinned public-source hashing, forward/reverse mapping and
radio-attribute enumeration, read-only approved-workbook inventory, Python
AST/source inspection and diff checks. **No local product imports, pytest,
JavaScript/browser fixtures, builds, self-tests, EXE or live traffic.**

Only this Markdown design record is changed. Repository docs-only Actions may
route product tests/package jobs to `skipped`; a green docs gate is validation
of this proposal's routing, not L10-B implementation or runtime verification.
Current status remains **IMPLEMENTATION BLOCKED** regardless of docs CI color.
