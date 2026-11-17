# L9 twelve-grid projection inventory and source proof

Status: implementation in progress; **not full-form or live acceptance**.
The existing recap-only contract/report remains the historical recovery boundary.
No resource, protected AGENTS, transport registry or catalog adapter change is
part of this form-owned work.

## Independently verified providers

Read-only local source review on 2026-11-17 independently measured:

- `z525.js` (served `525.32c49782948fc5ef.js`):
  `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
- `l10a-main.js` (`main.bed1449c3647a8ca.js`):
  `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
- `l10a-reviewed-vendor.js` (`vendor.c32c4ee39d966e30.js`):
  `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`.

All equal the configured `resources/build-pins.json` digests. Cached public
bytes are source evidence, not loaded-provider or live-capture custody.
Offsets below are character offsets in the decoded hash-matched providers.

## Approved destination inventory

Read `resources/corporate_format.xlsx` as ZIP/XML without saving it; resolve
sheet relationship `L9` to `xl/worksheets/sheet8.xml` (sheet order is not a file
number). Each block has A:I columns, a separate TOTAL row merging A:G and a
numeric H destination. No new destination, caption, resource edit or omission
approval is inferred.

| Grid index / owner | Request GroupType | Outer / inner structural caption | Reference header / body / footer rows | Custom footer source |
|---|---|---|---|---|
| 1 / grid1 | Group 1 | HARTA BERWUJUD / KELOMPOK 1 | 4 / 5:187 / 188 | TotalTable1 |
| 2 / grid1 | Group 2 | HARTA BERWUJUD / KELOMPOK 2 | 192 / 193 / 194 | TotalTable2 |
| 3 / grid1 | Group 3 | HARTA BERWUJUD / KELOMPOK 3 | 198 / 199 / 200 | TotalTable3 |
| 4 / grid1 | Group 4 | HARTA BERWUJUD / KELOMPOK 4 | 204 / 205 / 206 | TotalTable4 |
| 5 / grid1 | Other Group | HARTA BERWUJUD / KELOMPOK LAINNYA | 210 / 211 / 212 | TotalTable5 |
| 6 / grid2 | Permanent | BANGUNAN / PERMANEN | 216 / 217 / 218 | TotalTable6 |
| 7 / grid2 | Non-permanent | BANGUNAN / TIDAK PERMANEN | 222 / 223 / 224 | TotalTable7 |
| 8 / grid3 | Group 1 | HARTA TIDAK BERWUJUD / KELOMPOK 1 | 231 / 232 / 233 | TotalTable8 |
| 9 / grid3 | Group 2 | HARTA TIDAK BERWUJUD / KELOMPOK 2 | 237 / 238 / 239 | TotalTable9 |
| 10 / grid3 | Group 3 | HARTA TIDAK BERWUJUD / KELOMPOK 3 | 243 / 244 / 245 | TotalTable10 |
| 11 / grid3 | Group 4 | HARTA TIDAK BERWUJUD / KELOMPOK 4 | 249 / 250 / 251 | TotalTable11 |
| 12 / grid3 | Other Group | HARTA TIDAK BERWUJUD / KELOMPOK LAINNYA | 255 / 256 / 257 | TotalTable12 |

`grid1/2/3` abbreviate exact components `rshshr-citr-l9-form-grid1/2/3`.
Legacy literal LAINNYA remains an independently approved structural alias, not
an inferred order binding. Each family uses its already observed exact
`l9-table-{1,2,3}-grid` request with literal GroupType, not row index identity.

## Every column's active submitted renderer

CIT `pI`, `SI`, `MI` initGrid/initColumn (~2480150, 2484144, 2488138) declare
selected ReturnSheetRecordId + GroupType. `isStatusSubmitted` suppresses the
checkbox and action columns. The pinned submitted set has exactly nine cells:

| Approved column | Original Data-row member | Active representation |
|---|---|---|
| A KODE HARTA | GroupAssetType | literal string; **not CodeOfAsset** |
| B KELOMPOK/JENIS HARTA | GroupAssetType | ordinary bound catalog description |
| C BULAN/TAHUN PEROLEHAN | MonthYearAcquisition | ui-grid dateFormat MM-yyyy |
| D BIAYA PEROLEHAN (Rp) | AcquisitionPrice | numeric body fraction0 |
| E NILAI SISA BUKU FISKAL PADA AWAL TAHUN (Rp) | RemainingBeginningValue | numeric body fraction0 |
| F METODE ... / KOMERSIAL | MethodCommercial | COMMERCIAL_METHOD description |
| G METODE ... / FISKAL | MethodFiscal | FISCAL_METHOD description |
| H PENYUSUTAN/AMORTISASI FISKAL TAHUN INI (Rp) | FiscalYearValue | numeric body fraction0 |
| I KETERANGAN | Notes | literal text |

Grid1 asset labels require TANGIBLE_ASSET, grid2 GROUP_OF_BUILDINGS, grid3
INTANGIBLE_ASSET. MAIN exports GOc->$t.GO->Me, B7E->$t.B7->Mt,
dBq->$t.dB->At, ONl->$t.ON->P, Da4->$t.D->nt (~2988970, 2990841,
2991591, 2992466, 2992553). These enums identify consumers, not permissions.
MAIN ordinary ui-grid `Bi -> ki -> Qi -> codeDescAsync` (~4223302..4224800)
uses getReferenceDataDescription; the l3bcit raw-code fallback is not selected.
CIT setShowAttachment9 (~2705882) preloads five singleton getSingleReferenceData
calls in Promise.all on loadFirst; each grid skipLoadingReferenceData=true.
Reuse the separately owned shared producer and existing full-catalog
order/version/attempt-clock helper. Never invent a batch, cache read or fetch.

MAIN (~2732302) fixes angularDefaultMonthYearFormat=`MM-yyyy`; the active date
cell calls ui-grid.formatDate (~4226304), which maps MM-yyyy -> MM-YYYY and
calls dayjs (~4298924), not Angular DatePipe and not editor validation. The
bounded current profile accepts calendar-valid date-only/naive midnight,
Jakarta-midnight +07:00 or UTC-midnight encodings in 1970..2100; a UTC date
advances to Jakarta 07:00 and keeps its month. Other times/offsets refuse.
Literal null renders blank; absence/type drift remains distinct and refused.

MAIN numeric body `Ka` (~4224244) uses numberformat_ignoreprec with fraction0;
its implementation (~4032080) calls DecimalPipe `1.0-0`, with Indonesian format,
noFraction=false. Editor constraints are not renderer proof. Preserve original
numeric lexemes; restrict to genuine finite nonnegative number tokens with
safe precision, no signed zero and a proven whole-number rounding result.
USD and unsafe fractional branches remain unsupported, not coerced to Rupiah.

## Original custody and lifecycle

A read-only local existing application capture was inspected only for keys,
type classes and predicates: 30 L9 grid response packets / 184 Data rows. Each
had exact `{Data,Index,TotalRecords}` envelope; each row had eight displayed
members plus `GroupType,CodeOfAsset,RecordId,Index,Action`. Every original
CodeOfAsset and Action was null, Index a safe nonnegative integer, RecordId a
string, GroupType equal to its original request. Every acquisition date used
Jakarta-midnight encoding. Monetary fractions were present, so an integer-only
grid implementation would not cover that original populated profile. No private
value, identity, request, response body or captured file is committed.

Retain the original typed envelopes and rows, metadata, duplicates, page-local
Data index, absolute offset and original event sequence/hash/attempt. Never
reconstruct values from flattened custody tables or use Index for numbering.

CIT ~2545100 initializes nonmigrated stored totals, then calls patchFooterGrid
for all twelve. patchFooterData (~2549400) returns the current stored
`[{Label:'TOTAL',FiscalYearValue:TotalTableN??0}]`. This is the displayed custom
footer, **not a sum of displayed rows**. updateFooterGrid's footerCit POST is
an edit/refresh lifecycle, not an extra request for the initial submitted read.
Retain the source's literal TotalTableN; reconcile source calculations and bound
ordered operands instead of replacing it with rounded row sums. The shared
grid's empty tFoot spacer remains `[]`; TOTAL spans are [7,1,1].

Use a separately versioned details proof with positive configured loaded CIT,
MAIN and VENDOR providers, exact id-ID/Asia/Jakarta, selected submitted
`?view=true` route, preceding Induk, current-only Normal, explicit nonmigration,
original component lifetime and independently inspected before/after grid,
ui-grid/p-table/form/groups/headers/footer structure. No DOM values or checked
state, new active calls, protection edit or generic gate bypass.

For each unproved grid keep its name and refusal reason; native dump gate must
still force whole-record fallback. Full-form acceptance requires actual all-grid
projection and mapping, original passive catalog custody and hosted observer ->
adapter -> held -> saved/reopened workbook evidence on the integrated head.
