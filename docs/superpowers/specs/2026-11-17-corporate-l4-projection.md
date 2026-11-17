# Corporate L4: empty legacy and source-bound populated follow-through

> Sections below through the historical remaining gap describe the earlier
> empty-only head. The populated follow-through is recorded at the end; earlier
> green is not populated-native acceptance.

## Scope and source evidence

PR #275 is a draft correctness candidate, not full L4/native acceptance.
The reviewed configured CIT bundle is `525.32c49782948fc5ef.js`, SHA-256
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
The source-only review also checked the configured MAIN bytes
`main.bed1449c3647a8ca.js`, SHA-256
`ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
These are public frontend identities, not taxpayer data. Digests remain owned
by `resources/build-pins.json`; no second production pin is introduced.

The CIT `IE.initColumn()` submitted grid uses these actual bindings:

| Approved block A column | Rendered source | This candidate |
| --- | --- | --- |
| NPWP PEMOTONG/PEMUNGUT | `TIN` | No populated rows admitted |
| NAMA PEMOTONG/PEMUNGUT | `Name` | No populated rows admitted |
| KODE OBJEK PAJAK | `TaxObjectCode` | No populated rows admitted |
| OBJEK PAJAK | **`TaxObjectCode` + `ReferenceDataType`** | Unbound catalog; refuse |
| DASAR PENGENAAN PAJAK (Rupiah) | `TaxBase`, fraction 0 | Explicit captured zero only |
| TINGKAT (%) | `TaxRate`, fraction 2 | No populated rows admitted |
| PPH FINAL TERUTANG (Rupiah) | `IncomeTax`, fraction 0 | Explicit captured zero only |

The similarly named `E1.L4Grid1Columns` and row-edit dialog are NOT the active
submitted grid renderer. Copying saved `TaxObject` into OBJEK PAJAK is wrong.
The edit callback's `Math.round(base * (rate / 100))` is not a universal stored
row invariant either: the parent has a self-paid-tax insertion with zero base
and separately supplied tax. The former draft's Decimal reconstruction is
removed rather than claiming those fractional binary operations are exact.

Block B is `rsh-citr-l4-grid2` / `ui-grid-offline`. The pinned
`W1.setGrid2DataMap` maps source `TaxObjectCode` to displayed `Code`;
`TypeOfIncome` requires `INCOME_EXCLUDED_FROM_TAX_FOR_CIT` labels.
`IncomeSource` is literal and `GrossIncome` is a Number2 body column. Neither
catalog has original-byte admission/binding in this PR. Both populated blocks
therefore remain on the existing **whole-record DOM fallback**, including all
duplicate rows. No label code is exported as prose, no blank row substitutes
for original data, and no partial form is called complete.

## Supported subset

Only an original empty A inventory (`Data=[]`, numeric `TotalRecords=0`, null
`Index`) plus empty/null B and explicit original numeric-zero totals can
project. Accept the observed five-key root or that exact root plus numeric-zero
`TotalTaxBaseUsd` (the pinned current owner's six-key output). Unknown keys,
missing/null/string/boolean/nonzero/unsafe totals, signed zero, unsupported
currency, malformed packets and altered request bindings refuse. Missing USD
base is preserved as absence, never invented as an original leaf.

The loaded CIT proof must equal the actual reviewed configured digest, not
merely have a SHA-shaped string. Preserve submitted/model/selected annual
period/record/route checks and every existing packet/snapshot/Stop gate.
No new catalog request, endpoint, timer, browser property or dependency is added.
Zero formatting has no locale-dependent separator, so no new locale/timezone
RPC is necessary. The pure helper still refuses non-id-ID callers.

The observer binds both exact grid/host/p-table/table owners before and after
pagination, reading headers and physical tFoot spans only, never business cell
or control values. CIT/MAIN source review establishes the actual empty footer
layouts: A `[4,1,1,1]` (TOTAL, base, blank rate, tax), B `[1,3,1]` (blank row
number, JUMLAH, gross). MAIN's grid spacing default is false; no spacer is
fabricated. The approved worksheet merges A4:D4 and A10:D10 are preserved.
Each zero footer is emitted, including B's previously omitted JUMLAH amount.

## Custody and completion

Root evidence uses its original primary response sequence, container
`Payload/CurrentFormData` and full root path. Footer evidence uses each declared
footer response's own sequence, `Payload` container and actual `TaxBase` /
`IncomeTax` / USD paths, never fabricated root-total paths. Grid evidence retains
`TotalRecords`, original empty `Data`, null `Index` and original response sequence.
Same-request repeats retain first accepted packet custody; changed bytes remain
fatal under the existing adapter snapshot checks. Every declared footer is
validated, including the two reviewed request shapes.

All validation precedes section replacement. On either populated block, source
bytes and caller metadata remain untouched, `_UnsupportedMetadata` supplies an
explicit reference-label refusal, and the collector falls back as a whole record.
Legacy path-only L4 bindings retain all dump leaves, fail the unchanged native
dump gate, and stay unresolved/PARTIAL in mapping. No dummy `fields` exploits the
gate, and no exporter capture flag is changed to hide an omitted projection.
A completely proved empty L4 may map complete; that says nothing about other
forms, financial PDFs, job status or application-owned live acceptance.

## Verification and remaining work

The initial run 44016436431, head `5f637b9`, failed the L4 workbook test in
Windows shard-0 job 133815489822: it falsely set `capture_complete=True` while
emitting a deliberately incomplete B table. The aggregate package/gate failure
was downstream, not a routing defect. Routing/coverage policy is unchanged.
Test-first follow-up head `3454fb9` pins conservative two-block semantics;
all runtime execution is GitHub-runner-only. Local checks are AST/source,
workbook XML data, public JS bytes and git diffs only. The previous PR body's
claim of a local pytest-free product runner was not valid verification and is
not relied on.

Hosted regressions cover exact-pin refusal, both original empty encodings,
malformed/nonzero totals, reference-dependent populated rows and duplicates,
untouched custody on refusal, both rendered owners, request/packet sets,
original source paths/sequences, legacy mapping partiality and a saved/reopened
workbook with numeric E4/G4/E10 totals. Full exact-head CI is required separately.

**Remaining gap:** populated block A and/or B still needs separately reviewed
same-attempt reference catalogs, rendering and held-replay proof. No complete
populated-L4 implementation or live tax acceptance is claimed. AGENTS.md,
resources, the native dump gate and CI configuration remain unchanged under
the delegated scope. No merge, closure or consolidation is authorized here.

## Populated follow-through: separate source contract

`corporate-l4-populated-v2` is additive; v1 remains empty-only. Test-first
head047135d specifies populated pure rendering against the empty implementation.
All execution is hosted-only; source/AST is not runtime acceptance. Run44033205877
at047135d produced actual hosted RED: four downloaded original Windows JUnit
artifacts contain33 distinct new L4 cases,33 failures, zero errors/skips, each
because the old function lacks the populated labels interface. This was verified
from the runner artifacts, not a local product runner.

Independent rehash of scratch z525.js and l10a-main.js matched the configured
CIT/MAIN digests above. CIT IE.initColumn (near char2310261) -> MAIN hbR/Oi
(near char3001170) proves A's catalog type is **TAX_OBJECT_CODE**. The active
ui-grid Bi -> ki -> Qi -> codeDescAsync -> getReferenceDataDescription path is
not the l3bcit/raw-code fallback. Saved TaxObject remains unused typed metadata.
MAIN Ka's **checkIsString includes null**; A null numeric body cells therefore
render blank before the numberformat_ignoreprec pipe. The bounded candidate
accepts safe nonnegative integral monetary numeric tokens and 0..100 rate
points with at most two decimal places, never numeric strings/booleans or the
editor's base*rate formula. Parent self-paid zero-base/nonzero-tax stays valid.
Read-only ZIP/XML review confirms the approved L4 F3 rate cell is General;
it retains the rendered percentage-point text, not L2's separately approved
Excel percentage-fraction contract. Monetary Excel cells preserve stored values
under the existing zero-decimal accounting presentation; no resource is edited.

W1.setGrid2DataMap preserves TaxObjectCode as Code, TypeOfIncome as the catalog
code, IncomeSource and GrossIncome. pE/ui-grid-offline uses the actual E1 B
columns and MAIN W -> U -> yt -> Re description consumer for
**INCOME_EXCLUDED_FROM_TAX_FOR_CIT**. GrossIncome is Number2 (Et,
`number:1.2-2:id`); null is blank. E1.Grid2TotalRow is map/reduce without an
initializer, while getFormData stores TotalRowGrid2??0. A singleton null total
is blank on the grid but stored zero; later null additions contribute zero.
The Number footer uses DecimalPipe's default 0..3 fractional digits. The bounded
candidate requires binary-exact <=2-place operands and exact ordered sums within
15 digits, and reconciles the stored TotalGrossIncome. Other fractions retain
fallback; Decimal arithmetic is not claimed universally JavaScript-exact.

A footer is copied only from each declared original footer response and its
actual Payload paths after stored-total reconciliation, never derived from row
sums. Every duplicate A/B row and source metadata is preserved. A page-local
Data coordinates, all TotalRecords/Index fields, primary-root paths, original
catalog/detail indices and selected-label provenance keep their own original
sequence/container. All validation precedes either table replacement.

Shared producer needs are exactly naturally emitted no-body xhr/fetch singleton
id-ID GETs for TAX_OBJECT_CODE and INCOME_EXCLUDED_FROM_TAX_FOR_CIT. MAIN
getSingleReferenceData cache miss -> internalLoadBulkReferenceData constructs
these no-checksum singletons. No arbitrary bulk/checksum/maintenance/description
route or active acquisition follows. The shared owner alone changes transport
admission/type recognition. This form reuses CORPORATE_REFERENCE_REQUESTS,
reference_packets, _project_corporate_catalog, _reference_consumer_order and
_select_reference_version. Exact successful sequence sets and minimum original
sequence, cache order/version operands and original attempt clock are retained.
No catalog bytes or labels are synthesized.

The v2 native proof additionally requires exact positive loaded CIT/MAIN/VENDOR
pins, id-ID/Asia/Jakarta, Normal ICT_RCIT/ICT_RCITR, explicit null previous/last
submitted owners, preceding Induk, original manifest component lifetime and the
literal selected submitted ?view=true route. The observer retains both actual
table/host/p-table/form owners before/after A pagination, including headers and
footer spans, plus owned enabled tab/form binding. It never reads business
cells, controls, Angular state or caches. Missing shared producer/catalog proof
keeps whole-record DOM fallback. Packet contradictions, history/route changes,
Stop and final-drain/held-replay custody remain independent.

Hosted acceptance must include populated A+B across two A pages, duplicate
labels/rows, self-paid independent tax, exact number/rate/null/precision types,
malformed metadata, missing/failed/mixed references, lifecycle and total refusals,
then real observer -> capture -> adapter -> held replay -> saved/reopened workbook.
No template/resource/CI/native dump-gate/AGENTS change is part of this work.
Fresh exact-head full CI, shared-producer integration, protected contract and
operator live acceptance remain separately reportable until actually verified.
