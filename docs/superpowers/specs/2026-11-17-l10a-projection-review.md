# L10-A PR #272 — representation review and closed scope

## Status / decision

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
authorize consolidation. No new catalog admission was added.
