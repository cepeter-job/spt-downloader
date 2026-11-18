# Corporate passive reference catalogs: source proof and closed producer

## Decision and authorization

The full-native parallel follow-through explicitly authorizes building the shared
passive catalog producer, not making reference API requests. Implement only the
source-proven singleton no-checksum id-ID transport classes below. This does not
approve a bulk/checksum alias, cache access, a new business request, a form's
population/lifecycle admission, a layout omission, merge, or live acceptance.
Protected AGENTS changes remain a separate parent-owned approval deliverable.

## Independently rehashed public source

Cached `z525.js` (3,334,844 bytes) SHA-256:
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
Cached `l10a-main.js` (4,467,267 bytes) SHA-256:
`ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
Both exactly equal their URLs' configured `resources/build-pins.json` pins on
fresh origin/main `f5e40a2a4e02f0b03dcec6126a6416b5e10b3bbe`.
These are source evidence, not proof that a live attempt loaded those providers.
No vendor bytes were found in the reviewed scratch inventory; reuse the existing
reviewed vendor/order mechanism, without claiming a fresh vendor source review.

Offsets below are decoded Unicode character positions, not byte positions.

- CIT L10-A near 9590–11133 declares ordinary `ReferenceDataType` columns for
  Country, RelationshipCode, TypeOfTransaction, PricingMethod. L10-C near 59312
  declares ordinary country/transaction dropdowns. MAIN export chain resolves
  the types: `Ri` RELATIONSHIP_TYPE at 2996487, `_i` TRANSACTION_TYPE at 3001619,
  `ui` PRICING_METHOD at 2995698; COUNTRY_CODE is already reviewed/admitted.
- MAIN ordinary grid `Bi`/`ki` -> `Qi` near 4223200–4224600 and offline dropdown
  near 3882118 -> codeDescAsync near 4318550 -> getReferenceDataDescription at
  3036628. This is not the distinct l3bcit raw-code fallback.
- `getReferenceDataDescription` calls `getSingleReferenceData` and selects
  CodeDescription through strict Code equality and getActiveReferenceDataValue.
- `getSingleReferenceData` at 3038044 waits for bulk loading, then asks the
  application cache. On an ordinary cache miss it calls exactly
  `internalLoadBulkReferenceData([{referenceType:P,checksum:null}])` near 3039734.
  Its district/subdistrict special branch does not cover these four types.
- `internalLoadBulkReferenceData` near 3042005 chooses selected language or
  configured localization, excludes those special types and cached entries,
  maps a null checksum to the unadorned referenceType and joins its list with
  commas. It emits `http.get` at the referencedata gateway's
  `/currentreferencedata/${P}/${lt.join(",")}`, observing the response body.
  Therefore a naturally emitted singleton cache-miss request with language
  id-ID is exactly the existing origin plus
  `/referencedata/api/currentreferencedata/id-ID/` plus ONE literal type.
  No query, body, trailing slash, checksum suffix, encoded spelling, alternate
  language or multi-type list is proved/admitted by this extension.
- MAIN cache add ordering near 3026747 and active-version selector near 3037080
  are the existing consumer rules, not new implementations. Reuse
  `_project_corporate_catalog`, `_reference_consumer_order` and
  `_select_reference_version`, preserving original indices, duplicates,
  ParameterData, active selection and same-attempt capture-clock bounds.

## Original A/C extension (historical scope)

Keep COUNTRY_CODE and all existing L3/L11-A transports unchanged. Add only
singleton GET/no-body id-ID RELATIONSHIP_TYPE, TRANSACTION_TYPE, PRICING_METHOD
to `CORPORATE_REFERENCE_REQUESTS`, only for ICT_RCIT/ICT_RCITR. Expose a
four-type `CORPORATE_L10_REFERENCE_URLS` inventory for A/C consumers. Do not add
speculative L2/L4/L9/Induk types; those need exact source proof coordinated by
parent. TRANSACTION_TYPE is shared A/C; there must not be parallel adapters.

The paragraph above records PR285's original A/C scope, not permission for L4.
PR275's separately reviewed CI-repair extension integrates exact PR285 source
head27f1fab and adds only the two independently source-proven L4 singleton types
in a separate `CORPORATE_L4_REFERENCE_URLS` inventory. The original four-type
L10 inventory and consumers are unchanged. See
[the L4 source chain and transport tests](2026-11-17-corporate-l4-projection.md#ci-repair-reviewed-shared-dependency-and-closed-l4-extension)
for the extra enum-module hop, active submitted consumers, measured cache-miss
transport and no-body/alias refusal tests. This extension reuses this same
producer/binder/order/version/clock mechanism; it grants no other form types.

## Coordinated L4/L2/L9/Induk extension (current source contract)

The A/C-only exclusion above is historical, not a prohibition on this separately
source-reviewed parent-authorized extension. On November 17, 2026 the owner
independently rehashed both decoded cached files again: the byte sizes and SHA-256
values above exactly match the owned `resources/build-pins.json` and main
`d23e3edad19a11e810dfa39460957d7d2fa6bf46`. No asset/API fetch, live navigation,
cache/storage read, or product execution was used for source review.

### Active consumer -> export/module -> exact type

CIT module38525 imports `R=ye(90521)` at character260. MAIN module90521
re-exports the directly defined related-person class and imports `$t=T(66267)`
at2790264 for the enum barrel; module66267 starts2985543. These hops matter:
a similarly named exported symbol or enum string alone is not transport proof.

| Consumer | CIT decoded character positions | MAIN resolved export chain and type |
| --- | --- | --- |
| L4 A OBJEK PAJAK | IE.initColumn near2311785, `TaxObjectCode` description at2312267 | module90521 `hbR->$t.hb`2737084 -> module66267 `hb->Oi`2986693 -> Oi at3001212: TAX_OBJECT_CODE |
| L4 B JENIS PENGHASILAN | E1.L4Grid2Columns near2309730, literal reference key2310017 | literal INCOME_EXCLUDED_FROM_TAX_FOR_CIT, not a guessed enum |
| L2 Jabatan | w1 constructor2198300+, ngOnChanges2199342, getFullPosition2199986 | module90521 `_Xg->di`2735305 -> di.ReferenceDataTypeName2929809: RELATED_PERSON_TYPE |
| L9 tangible asset group | pI.initColumn near2480150, reference2480750 | module90521 `GOc->$t.GO`2736964 -> module66267 `GO->Me`2986623 -> Me2992466: TANGIBLE_ASSET |
| L9 buildings group | SI.initColumn near2484144 | `B7E->$t.B7`2736086 -> `B7->Mt`2986034 -> Mt2991655: GROUP_OF_BUILDINGS |
| L9 intangible group | MI.initColumn near2488138 | `dBq->$t.dB`2736184 -> `dB->At`2986104 -> At2992553: INTANGIBLE_ASSET |
| L9 commercial method | each grid, first reference2481618 | `ONl->$t.ON`2735755 -> `ON->P`2985809 -> P2989033: COMMERCIAL_METHOD |
| L9 fiscal method | each grid, first reference2481729 | `Da4->$t.D`2735950 -> `D->nt`2985945 -> nt2990905: FISCAL_METHOD |
| Induk TaxRate | Ec constructor2778983+, createTaxRatType2787626, options2929409 | `U37->$t.U3`2735741 -> `U3->we`2985799 -> we2988860: CIT_TAX_RATE |

L4 and L9 use MAIN's ordinary grid Bi/ki/Qi (4223302+) -> module66805
codeDescAsync (4318500+) -> getReferenceDataDescription3036628. L4 B uses the
offline W/U/yt/Re chain3882118+. Neither is the l3bcit raw-code fallback.
L9 setShowAttachment9 near2705882 calls five SEPARATE getSingleReferenceData
operations (asset, commercial, fiscal, buildings, intangible) in Promise.all;
this does not prove a five-type batch. Its grids skip automatic preloading.

L2 getFullPosition's second argument is UNUSED. It reads getSingleReferenceData
and uses the FIRST ORDERED `.find(row=>row.Code==Position)`, not
getActiveReferenceDataValue and not RELATED_PERSON_SUBTYPE. The supported string
code subset has no loose-coercion ambiguity. The single projector must label
this selection `reviewed-related-person-first-ordered-code-match`, preserve raw
indices and duplicate evidence, and retain `requires_vendor=True` for duplicates.
The current L2 consumer separately refuses duplicates; do not turn a provider
extension into permission for a wider L2 duplicate/version profile. Country
continues to use its existing active-version consumer and captured clock.

Induk createTaxRatType sorts the returned rows by parseInt(Code.substring(3,4))
then MUTATES CodeDescription with a numeric prefix. This producer exposes only
original catalog labels/paths via the existing ordinary projector; it does not
claim to reproduce that mutable options/prefix lifecycle or readonly selection.
The Induk owner must prove it separately; CIT_TAX_RATE registration is not D11
rendering/native permission and may not route a mutable label through a false
country-equivalent rule.

### Same reviewed transport and ordinary cache-order proof

For every row above, the active call reaches MAIN getSingleReferenceData3038044.
Its two regional special cases are not any of these types. Its ordinary cache
miss passes exactly `[{referenceType:P,checksum:null}]` to
internalLoadBulkReferenceData3042005, then retrieves the newly cached Details.
The builder selects the user's language (fallback is en-US, NOT assumed id-ID),
removes cache hits, maps null checksums to literal type strings, joins the list,
and calls no-body http.get. MAIN environment module91137 `referencedata` at
2729356 is `reference-data`; baseGatewayWebApiUrl2731578 strips hyphens to
`/referencedata/api`. Only an observed exact id-ID singleton URL ending in ONE
literal reviewed type is admitted. No batch/checksum/alias/getdescription route,
POST, body, alternate language or forced cache miss follows from this proof.

MAIN cache.add3028350+ invokes applyReferenceDataOrderBy3026413 unless the type
is BUSINESS_CLASSIFICATION (`D.VW`), AUDIT_OPINION (`D.lA`) or MONTH (local te).
None of the nine added types is exceptional, PERIOD or ECONOMIC_CODE. Reuse
`_reference_consumer_order` description/first-raw-ParameterData DisplayIndex
ordering before grouping. Ordinary L4/L9 version selection remains the existing
`_select_reference_version` over the same captured interval; no replay clock.
RELATED_PERSON_TYPE instead uses its distinct first-find rule above. The full
original snapshots, metadata, numeric lexemes, duplicates/order and both held
readers stay unchanged; neither labels nor original bytes are mutated here.
The projector additionally returns `raw_catalog` (a deep copy of the complete
typed original catalog, including unused metadata) and its original
`catalog_index`. These are source inputs, not a claim of rendered options or
new native permission. Raw response bytes remain separately authoritative.

### Reconcile PR275 without importing its form

PR275/aac8fa88d5936b3d805e9028859198b19e5c5a61 already contains PR285/27f1fab and
adds exactly `CORPORATE_L4_REFERENCE_URLS` with TAX_OBJECT_CODE and
INCOME_EXCLUDED_FROM_TAX_FOR_CIT. This branch reproduces those precise shared
registry/order/projector/no-body facts, independently reviewed above. It does
NOT merge unrelated L4 form/grid/footer code merely for constants. Parent later
retains one L4 map/one registry/one projector/one producer during integration.

Keep closed inventories separate: existing L10 A/C four types UNCHANGED; L4 the
two types above; L2 COUNTRY_CODE+RELATED_PERSON_TYPE; L9 exactly its five types;
Induk CIT_TAX_RATE only. All singleton entries share CORPORATE_REFERENCE_REQUESTS.
Generic observer/binder APIs accept caller-supplied closed reviewed kinds; form
consumers must continue enforcing their own inventory rather than inheriting the
whole registry. Existing L3 and L11-A inventories and the one ordered L11-A pair
are unchanged. RELATED_PERSON_SUBTYPE remains unregistered.

### Tests first / hosted-only verification

`test_corporate_shared_dependency_catalogs.py` specifies all nine natural
singletons, full original-byte/native custody, both held readers, negative
aliases/bulk/checksum/query/lang/method/body/tax/sheet/frame/tab/resource, explicit
no-body descriptor facts, full-snapshot/attempt/clock/language contradictions,
ordinary DisplayIndex/version/clock behavior and distinct Position first-find.
Shared binder tests check complete sequences and earliest original selection.
The existing actual SPA -> provider -> capture -> adapter -> both held readers
-> saved/reopened workbook vertical now emits all nine additional types from its
synthetic application, without registry injection or product API acquisition.
Existing provider tests preserve positive pins, absence-inclusive facts,
descriptor overrides, Stop, unavailable hash/Document contradictions and final
late-response fences. Runtime RED/GREEN must come from GitHub, not local AST.

Executed RED: source/test head `f6fdd5ce757ca7b21a5d8a836148dc78c91c4ed6`, Build
`44060475696` attempt1, PR merge build `8c4f8d5789731c4f353bf8374d9814775197311b`.
All four original Windows JUnit reports and all five collection inventories were
matched programmatically: 8,850 passed, 29 failures, zero errors/skips; portable
789 passed. Exactly 28 failures are the new missing registry/type/order/binder
positives and one is the expanded real-SPA producer vertical. Existing shared
transport/binder/provider negatives pass. The missing dependencies, not a
weakened safety gate or a fixture error, explain the RED. Complete raw-catalog
copy isolation assertions and exact offset corrections were committed before
production edits. Final exact-head hosted results are independently recorded in
PR285's read-back body and the run-isolated integration handoff; this historical
RED is never reused as GREEN or as application-owned live acceptance.

The existing capture owns original request objects, main-frame/context/selected
record, bytes/hash/sequence, privacy/budgets, failed/pending responses, full raw
snapshots and final drain. The new producer adds an optional manifest-owned
`corporate_reference_providers` fact, acquired once only in the existing owned
same-Document submitted SPA lifetime. It uses only the existing bounded
loaded-script hash reader and its strict script-provider predicate for all
three configured CIT/MAIN/VENDOR pins. Positive 64-hex exact configured pins are
mandatory; unloaded, missing, malformed or mismatched providers never authorize
labels. Cached source bytes are not a substitute.

Both live-held and checkpoint-held readers must independently validate this
fact against original attempt/record/source/detail and inject it uniformly into
all packet contexts. Descriptor overrides are forbidden; malformed, mixed,
missing-on-one, contradictory attempts and missing parent lifetime are fatal.
Absence remains compatible with legacy captures and grants no new catalog use.
The final drain publishes the optional fact only with its final parent lifetime
and original capture clock; no new final browser RPC or child-history sampler
is introduced. Existing final pending/seen fences, Stop and child-history
contracts remain in force; coordination with other child-history work belongs
to parent, not sequential sampling added here.

A shared binding helper consumes the existing `reference_packets` dictionary:
require exact endpoint/method/complete positive unique sequence set, every bound
packet successful, matching primary attempt/route/clock/provider/lifetime, and
choose minimum original sequence, never iterator/descriptor order. It then calls
the existing catalog projector. Return lookups, selected typed paths and original
source event for form workers; retain all original raw metadata/order as custody.
Missing catalogs remain unsupported; no code-as-label, blank substitution,
forced GET, cache/storage read or quiet-timer substitute.

## Test-first and evidence boundary

Tests precede production edits. Hosted tests must exercise populated descriptions
with duplicate codes/order/version, capture/held/checkpoint bytes, both override
refusals, positive pins and failures, transport aliases, changed snapshots,
mixed attempts/clock, final-drain late responses and Stop. Reopened workbook
coverage uses an existing populated source-proven consumer; A/C form completion
is independently owned and must not be manufactured by a synthetic test adapter.
Local checks are source/AST/git/data-only; runtime evidence is GitHub-runner-only.

No original live TRANSACTION_TYPE packet is currently available in the reviewed
capture. After producer readiness, parent must request one fresh application-owned
operator capture of the ordinary submitted populated record. Retain only naturally
emitted admitted packets; if cache-only or another transport occurs, report that
bounded attempt unresolved. Synthetic GREEN is not original live-packet availability,
form completeness, mapping COMPLETE, financial-PDF completion or operator acceptance.
