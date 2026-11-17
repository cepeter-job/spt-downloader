# L10-A PR #272 — populated consumer and representation review

## Current populated implementation candidate (17 November 2026)

The current follow-through adds `corporate-l10a-populated-v1`, while retaining
`corporate-l10a-empty-v1`. It consumes the single shared passive-catalog producer
from PR #285 at `27f1fab48e4516d935f14b7729c09e79c1c645f4`; no competing
transport registry, catalog adapter, clock/version selector or active request
was introduced by the A consumer. The two actual HEADER controls are also
retained canonically. Mapping deliberately remains PARTIAL: the approved clean
template has no slots for them and its reviewed omission counts stay unresolved.
The exact shared snapshot was merged into this
owned branch for combined hosted verification, not merged to main. Parent owns
consolidation and the independently approved populated AGENTS contract.

**Verification pending:** the new candidate must pass exact-head hosted checks.
No locally executed product tests, imports, browser fixtures or builds are
claimed. Cached source review is not a live provider proof. The old correction
and its green empty-only results below are historical, not populated acceptance.

## Historical empty-only correction / decision

**Source correction verified; contract follow-up requires fresh checks.** The user renewed explicit
edit authorization on 17 November 2026: “Izinkan perbaikan L10-A lengkap; tetap DOM
selama mapping belum terbukti”. This supersedes the earlier withdrawn edit
approval for L10-A code, tests and documentation, including commit/push to #272.
It does not authorize merge, closure, consolidation, new portal calls or CI
bypass. The historical red head was superseded by corrected head `cf3fa8f`,
verified green on run `44022810638`. The later approved `AGENTS.md` follow-up
must receive its own exact-head checks. Populated proof gaps below are not
complete merely because implementation is authorized.

The implemented correction narrows the unsafe candidate on `feat/native-l10a`;
it does not authorize merge or consolidation. Admit **only a genuinely empty,
completely captured L10-A grid**, with an absent/null/empty-object/empty-array
declared source root. Every populated branch should remain unsupported and use
whole-record DOM fallback until its representation is proved. A future exact-head
green would be synthetic implementation evidence, not live acceptance or
completion of populated L10-A projection. Resolve the gaps below before claiming
all corporate forms are ready for consolidation.

## Root cause of the existing CI failure

Run 44015289602, shard-3 job 133811688577, failed only
`test_the_grid_binding_must_be_the_single_reviewed_page_set`. The fixture changes
the binding endpoint but still supplies the old endpoint's packet. The adapter
correctly records `unbound_corporate_source_response` and
`incomplete_corporate_grid_source` **before** calling semantic projection.
Preserve that order. Test the early refusal and separately align packet and
binding to exercise the later reviewed-endpoint guard.

## Source proof (public JavaScript only)

The saved 525 source matches the approved `resources/build-pins.json` digest
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
A read-only public MAIN fetch, decompressed before hashing, matches
`ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
No captured taxpayer packets, browser state or private values are uploaded.
Offsets below are decoded Unicode string positions, not byte offsets.

- 525 near 9590–11133: the `l10a-grid` constructor binds the selected
  `ReturnSheetRecordId`; `initColumn()` declares the nine worksheet columns.
  `Country`, `RelationshipCode`, `TypeOfTransaction`, and `PricingMethod` have
  `ReferenceDataType`. `ReasonPricingMethod` is ordinary text, not a reference.
- MAIN module 29844 starts at 4200959. Near 4223200–4224600, `Bi`/`ki` selects
  `Qi` for ordinary reference cells. `Qi` calls `codeDescAsync`, **without** the
  raw-value fallback used by the distinct `l3bcit` branch. Near 4318550 the pipe
  delegates to `getReferenceDataDescription`; at 3036628 the service returns
  the active candidate's `CodeDescription`, not the code. Literal source codes
  therefore cannot stand in for the displayed labels. This includes unresolved
  or null codes: without original catalogs, do not infer their rendered value.
- 525 near 10400: `TransactionValue` has `type:number,fraction:0`; the separate
  edit validator's `greaterThanEquals(0)` does not prove rendering. MAIN `Ka`
  near 4224244 calls `numberformat_ignoreprec`; its implementation near 4032100
  uses DecimalPipe with `1.0-0` for this branch. MAIN environment near 2733767
  has `noFractionNumber:0` and Indonesian formatting. The original candidate's
  trim-to-two-decimals rule is wrong. The pipe coalesces null to zero (`ne??0`),
  not blank; its caller bypasses number formatting for strings. Rounding,
  signed-zero/precision and currency branches still need bounded regressions
  before population admission. No numeric population branch is admitted.
- 525 at 2651119 reads `DeclarationTransactionRelatedParties` via optional
  chaining. Its L10-A child owns only the two MainFormData header controls; rows
  are fetched by the independent grid. Absence can coexist with an empty grid,
  but a nonempty root cannot be silently discarded. In particular `[{}]` and
  `{'Body': []}` are nonempty roots despite producing only one empty leaf row.
- The parent binds `IsRupiah` to route tax type near 2642470 and passes it to
  L10-A near 2622578. Require the exact selected ordinary Rupiah submitted
  `?view=true` route, matching lifecycle and preceding observed Induk.

## Correction / invariants

- Use a distinct `corporate-l10a-empty-v1` capability. Recheck a positive
  64-hex CIT digest against the reviewed loader pin, not arbitrary SHA shape.
  No new asset fetch, locale probe, reference route or request permission.
- Require one reviewed grid and its exact seven-field ten-row id-ID first-page
  request. Existing original-packet safety, count, contiguity, snapshot and
  completeness checks run first. A nonempty table refuses before any conversion.
- Retain source-root presence separately from null and retain the original
  container/type/path/primary sequence for present inert roots. No fabricated
  body rows, zero amounts or catalog labels. Keep original event/hash custody.
- Bind the empty grid to the earliest successful **exact-query** response
  sequence, not iterator position or an event sharing only its First offset.
- Preserve the approved workbook resource and all other form, mapping, financial
  PDF, Stop, held-custody and publication gates.

## Populated mapping inventory / shared catalog blocker

The same hash-matched MAIN export chain was traced, not guessed from field
names: 525 module 38525 imports module 90521 as `R`; MAIN re-exports its reference
types through the `$t` module (exports near 2986403–2986742).

| Worksheet column | Original key | Actual pinned consumer / dependency |
| --- | --- | --- |
| A Nama | Name | ordinary text interpolation |
| B NPWP/TIN | TIN | ordinary text interpolation; preserve leading zeros |
| C Negara | Country | `R.cFA` → COUNTRY_CODE → active CodeDescription |
| D Bentuk hubungan | RelationshipCode | `R.RmG` → `$t.Rm` → Ri → RELATIONSHIP_TYPE (2996487) |
| E Kegiatan Usaha | BusinessActivity | ordinary text interpolation |
| F Jenis Transaksi | TypeOfTransaction | `R.j_F` → `$t.j_` → _i → TRANSACTION_TYPE (3001555) |
| G Nilai transaksi | TransactionValue | numberformat_ignoreprec → DecimalPipe 1.0-0, null coalesces to zero inside the pipe; no two-decimal rule |
| H Metode | PricingMethod | `R.bLv` → `$t.bL` → ui → PRICING_METHOD (2995698) |
| I Alasan | ReasonPricingMethod | ordinary text interpolation, NOT a reference column |

The active selector at MAIN 3036628 onward first filters strict Code equality,
then chooses the first explicit null/empty ValidTo, otherwise first future
ValidTo, otherwise greatest valid ValidFrom, otherwise first candidate. Existing
`_project_corporate_catalog`, `_reference_consumer_order` and
`_select_reference_version` own the conservative order/version/attempt-clock
subset. Reuse them rather than creating a parallel adapter. Provider pin,
locale, full typed snapshot, exact successful sequence set, stable source
version and lifetime must be bound before any label is emitted.

**Transport blocker:** `CORPORATE_REFERENCE_REQUESTS` admits COUNTRY_CODE but
not RELATIONSHIP_TYPE, TRANSACTION_TYPE or PRICING_METHOD. The original capture
has no admitted TRANSACTION_TYPE bytes (also recorded independently in L10-C
proof PR #276). MAIN 3038180–3044700 can use cache or a dynamically constructed
ordinary GET, with locale and optional checksum/bulk choices. An enum name is
not evidence that any specific endpoint combination was inspected. This change
adds NO catalog URL, network permission, forced fetch, browser-cache read or new
reference adapter. Shared L10-A/L10-C follow-up needs one reviewed exact
TRANSACTION_TYPE transport plus original same-attempt bytes; L10-A additionally
needs the other two types. A populated row with null reference codes still
requires its consumer/catalog proof; blanks cannot be inferred from codes.

No populated branch is implemented or certified in this correction. The nine
source bindings above are a proof inventory, not filled-workbook acceptance.

## Gaps before populated L10-A / consolidation

1. Original same-attempt catalogs for all four reference types, with reviewed
   endpoint/type/locale/ordering/version/clock custody and their exact loaded
   consumer/provider pins. Do not force a fetch or invent labels.
2. Independently proved integral numeric representation, precision/sign/null
   cases and Rupiah-vs-USD selection; fractional input and unsafe rounding remain
   unsupported unless separately reviewed from the actual consumer.
3. Positive populated observer → adapter → held replay → reopened-workbook
   regressions with page-local source coordinates and duplicates preserved.
4. Application-owned build-matched native acceptance, truthful per-form mapping,
   and independent financial-PDF/capture completion. Empty-grid green is not
   populated-form acceptance.

## Verification boundary

Local verification is source/AST/data-only. No product imports, pytest, browser,
Tk, build, EXE or adapter smoke execution is permitted locally. The old PR body
claimed a local adapter smoke run; that is historical worker output and is not
verification performed or endorsed by this correction. Runner evidence will be
reported against the pushed exact head; leave this PR open and unmerged.

## Implemented correction and approved protected contract

- Tests were changed first. Source-only RED confirmed the new capability and
  exact original-packet selector were absent; no local execution is claimed.
- Removed raw-code and two-decimal populated projection, including flattened
  row reconstruction. Only `corporate-l10a-empty-v1` can emit a semantic table.
- Recheck configured positive CIT pin, exact submitted Rupiah View route,
  preceding Induk and manifest-validated component lifetime. Bind the exact
  first ten-row request and earliest successful original response sequence.
- Original decoded roots are checked before replacement; retain typed empty
  Data/count/Index, root presence/type/value and both original sequences.
  Every populated row, including duplicates or empty row objects, refuses
  without conversion; original event/hash custody and raw packets remain.
- Preserved early unbound-packet/count refusal; an independently aligned packet
  tests the later semantic endpoint guard. Added adapter/source-query/observer
  and saved/reopened empty-workbook regressions, for execution on runners only.
- The initial protected `AGENTS.md` edit was denied and was not retried under
  that denial. The user later explicitly renewed approval for the restricted
  #272 contract. `AGENTS.md` now records the verified empty-grid-only boundary,
  preserved original custody and populated whole-record DOM fallback. This
  follow-up changes documentation only, not runtime admission or merge scope.

Runner verification is tracked against the corrected pushed head in PR #272.
Historical correction run 44020711219 on `5fb70c7a7e1295fe4e2d160c4e2196b1db87c1bb`
passed portable, dependency audit and three Windows shards; shard-2 exposed one
test expecting fallback for a legacy-route component lifetime, which the earlier
packet decoder correctly rejects as fatal. The regression now preserves that
fatal gate and separately exercises the semantic route defense directly, since
a valid legacy-route lifetime cannot pass the decoder. No production safety gate
was changed to address that test. Corrected source head
`cf3fa8f9ec3d3c9b844a3bf3f66e59b2258383f2` subsequently passed exact-head Build
run `44022810638` and all current PR checks. That green verifies the source
correction, not a later documentation head; the approved contract follow-up
must receive its own fresh checks, recorded in the PR body.

Empty-only GREEN will not complete populated support, live native acceptance or
authorize consolidation. No new catalog admission was added by that correction.

## Populated numeric proof: caller precedes pipe

Independently decoded the already cached Brotli vendor asset (no portal fetch).
Its 2,525,901 decoded bytes hash to the configured VENDOR pin
`6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`.
CIT and MAIN were independently rehashed again and match the configured pins
above. VENDOR contains Angular version literal 14.1.0 at character 1273538.

The earlier sentence that inferred a displayed zero from the pipe's nullish
coalescing was incomplete. MAIN's actual `checkIsString` at 4279802 returns true
for **null as well as non-time strings**. `Ka` at 4224197 therefore passes null
straight to interpolation; the rendered cell is blank and the pipe is not
called. Direct invocation of `numberformat_ignoreprec(null,0)` does yield zero,
but that is not this active grid call. Preserve this distinction in tests and
provenance. MAIN's time regex at 4258633 recognizes an initial HH:mm; those
strings do not receive ordinary string bypass and remain unsupported here.

The precise public source excerpts and their individual hashes/character ranges
are retained in `tests/fixtures/corporate_l10a_renderer.json`. Hosted Edge tests
execute the measured DecimalPipe class (VENDOR 1214520..1218199), digit grammar,
number-style/symbol selectors and original Indonesian locale data, together with
the unmodified application pipe constructor (MAIN 4031960..4032226), active
`Ka` and `checkIsString`. Only Angular registration/locale-lookup/template-
instruction plumbing is synthetic; the numeric algorithm is not rewritten as
an alleged framework oracle. No production code or snippets are executed locally.

Supported numeric tokens must be finite, within fifteen integral digits and
exactly representable by the Number that JSON.parse consumes; compare the
original Decimal to Decimal.from_float without dropping its lexeme. DecimalPipe
1.0-0 rounds a binary-exact half away from zero, suppresses a rounded negative
zero and groups with Indonesian full stops. Assertions specify 1234.5 -> 1.235,
-1234.5 -> -1.235, -0/-0.25 -> 0. Literal non-time strings bypass formatting,
including `1234.50` and literal `-0`; null remains blank. Non-binary-exact 0.1,
underflow, unsafe magnitudes and time-shaped strings remain unsupported rather
than guessing rounded source intent. Framework boundary cases explicitly show
why 0.49999999999999999 and 9007199254740993 cannot be treated as exact source
numbers. USD/oil-and-gas routes remain unsupported; the captured route and exact
Rupiah header, not edit validators or a two-decimal shortcut, select this subset.

## Submitted lifecycle and original online row ownership

CIT 2646500..2649900: `mapPrefillData` assigns original outer baseFormData,
then `fillForm` sets submitted state, parses CurrentFormData/PreviousFormData and
calls `mapFormData`. An amendment's LastSubmittedFormData is applied only when
not submitted or on the history route. The literal submitted selected View
route excludes both branches. The new consumer requires SUBMITTED, the selected
literal model/type, preceding Induk, valid explicit PreviousFormData encoding,
and both outer/current numeric-one IsTransactionWithRelated. It retains those
original predicates separately under Payload and CurrentFormData paths.
`setShowAttachment10abc` at 2705414 and the Induk callback at 2695879 both use
that flag; contradictory/missing/boolean/string flags remain unsupported.

CIT 2622578 passes recordId, outer baseFormData, saved child formData, submitted
state and route-derived IsRupiah to L10-A. Child `ngOnChanges` at 27800..29350
only remembers old formData and fills the two header controls from main data;
it does **not** replace the online grid's rows with a saved child-body alias.
The grid's `initGrid` near 9590 binds ReturnSheetRecordId; its original online
Data/TotalRecords/Index packet, not the inert saved root, owns every body row.
The declared root still must be absent/null/[]/{} so no unrelated source subtree
is discarded; presence/type/container/primary sequence remain explicit.

MAIN 4270400..4274000: the ordinary HTTP callback selects Payload.Data (the
separate Result-only schema stays unsupported), calls `initializeGrid` and
assigns that original row array to gridModel.Data. The reviewed nine columns
have no RowNumber, ParameterData or localizationLookup mutation. Closed row
schema excludes those keys and every unsupported extra. Submitted initColumn
omits checkbox/actions; edit/upload/delete refresh callbacks are not part of
this branch. Reference cells resolve through the already reviewed ordinary
asynchronous consumer, never raw-code fallback. No later value-changing callback
for an admitted row is inferred or polled. Changed original snapshots, mixed
attempts/clock/provider facts, new late responses, privacy/identity contradictions
and Stop retain their existing stronger gate precedence.

The observer checks enabled tab/panel/form and the exact form/grid/ui-grid/
p-table/table ownership, all nine captions and no footer before/after the owned
pagination. It reads no input, checked state, tbody or footer business value.
The shared provider fact and its three configured positive digests stay on the
manifest, not response descriptors. Final capture/held readers remain the shared
producer's responsibility; this A consumer adds no final child sampler or
sequential L7/B-history graft.

## Header controls and truthful mapping

CIT 34450..37600 declares two ordinary `input[type=text][pInputText]` controls,
PeriodYear and CollectorTin, with the exact Tahun Pajak / Nomor Identitas WP
captions. Its setter reads **outer** baseFormData.PeriodYear and baseFormData.TIN,
not current MainFormData.TaxYear/Tin. Require present original year-number and
TIN-string operands; retain both typed Payload paths plus their control
identities and literal text values. Observer custody includes those two exact
form-owned input structures without reading either value or checked state.

The approved clean L10-A template has the nine body slots, but intentionally no
destination slots for these two controls. Existing reviewed presentation rules
omit them visually while retaining unresolved counts. A populated consumer must
not drop its two fields to claim COMPLETE. The section therefore retains both
canonical fields and `projection_complete=False`, with
`projection_reason=l10a_header_slots_omitted`; the template reports
`derived_complete=False`, that exact reason, two unmapped/reviewed-redundant
fields and a visible Audit sentence. A literal unsupported Excel monetary
string adds its own unresolved row/table count. No template/resource change or
blank/zero placeholder is used to repair the gap. The separately approved legacy
empty-v1 contract is not reinterpreted by this populated correction.

## Native wiring and acceptance matrix

- Reuse `corporate_reference_bindings` and
  `bind_corporate_reference_catalogs` from the single shared owner. Require all
  four original singleton catalogs, exact complete successful sequence sets,
  attempt/route/lifetime/clock/provider equality, full typed snapshots,
  consumer ordering and active version selection. Duplicate catalog codes select
  the original Details index, not source iterator order. Null/absent codes can
  render blank only after those complete original catalogs prove the lookup.
- Retain the `grid_packets` keyword on `apply_projections`. Select each original
  page by its exact seven-field id-ID First/Rows10 query and minimum successful
  sequence, preserving page-local Data coordinates and global destination rows.
  Complete ordered multi-page inventories retain duplicate occurrences, typed
  count/Index controls and raw row identifiers. Other form dispatch is unchanged.
- Hosted tests cover positive populated original adapter, reversed event order,
  12-row owned SPA observer -> capture -> adapter -> both held representations
  -> saved/reopened approved L10-A workbook, descriptions different from codes,
  duplicate catalog codes and body rows, null/numeric/string boundaries, strict
  malformed source/proof inputs, original predicate custody and one-shot Stop.
  Existing empty/query/minimum-sequence/fatal-decoder tests remain unchanged.
- No resources, protected AGENTS or CI files were changed. The current protected
  contract still records EMPTY-ONLY. Parent must separately review/approve the
  actual populated contract before merge/consolidation; this report does not
  substitute for it. All full exact-head CI results are pending until recorded
  against the new combined head in the PR body.
- Original live same-attempt catalogs and application-owned build-matched native
  acceptance remain operator-owned. Request one bounded ordinary submitted
  populated capture only after producer readiness; cache-only or unsupported
  natural transports remain whole-record DOM fallback. Synthetic tests never
  establish live acceptance, other-form mapping, financial PDFs or job COMPLETE.
