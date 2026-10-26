# Automatic MPN companion workbook for SPT jobs

Status: approved by the operator on 26 October 2026, including the supplied
resume template. Implementation and runner verification follow the plan.
Baseline inspected: `main` at `1d3999f026d4ed82ad6c31eff9272ecb4540717d`.

## Intent and agreed requirements

Every full, live SPT scraping job also collects the same taxpayer's Accounting
transactions and exports a separate MPN workbook for the requested SPT tax year.
The operator explicitly chose the tax period/year, rather than the payment's
calendar year. A payment made in a later calendar year can therefore qualify.

Use the observed XHR `list` and `listdetail` for JSON scraping. Include only
detail rows whose source `Amount` is strictly negative. Preserve its sign and
source value. In DOM mode, prefer a complete DOM capture; use JSON if DOM cannot
capture the same owned detail completely. Do not guess missing values.

## Approach

The proposed implementation is a dedicated Accounting collector called by the
existing SPT job, with a separate MPN data/proof contract and workbook renderer.
This implements the operator's requested automatic companion output and keeps
the existing native SPT admission rules confined to SPT.

A separate manually launched MPN tool would add work to each download and does
not meet the automatic-job requirement. Expanding the generic SPT observer to
accept Accounting would conflate endpoint, identity and publication contracts.
Neither is proposed. The collector remains a separate module within the same
owned browser/job, rather than introducing a second worker process or GUI.

Builder recommendation: collect MPN after SPT details, before closing the
browser. Publish the verified SPT and MPN outputs together. A recoverable MPN
capture failure keeps valid SPT results available but makes the overall job
PARTIAL. Stop cancels the job; known safety/identity contradictions remain fatal.

## Observed source contract, 26 October 2026

Manual, authorized browser inspection reached the literal same-origin route
`/accounting/id-ID/balancesheet/<taxpayer-id>`. The displayed taxpayer identity
must match the independently verified SPT job. No real taxpayer identifiers or
transaction records are included in this document.

Loaded script response bodies inspected:

| Asset | SHA-256 |
| --- | --- |
| `/accounting/id-ID/main.fedea3c4d025195e.js` | `7a76f131ac13b124087c4c968154d0f73c26a92069dc8d6dd59791f908d4bdf1` |
| `/accounting/id-ID/vendor.5900c4ddec796b87.js` | `b876e4421e8d8caa81b98928f23e672e5da7069fa7ab30ab14318b5f3726af5c` |

Both grids issue read-only application POSTs, not GETs:

| Exact path | Identity and request fields | Successful response |
| --- | --- | --- |
| `/accounting/api/taxpayeraccounting/list` | `TaxpayerAggregateIdentifier`, `First`, `Rows`, `SortField=PostingDate`, `SortOrder=-1`, `Filters`, `LanguageId` | `IsSuccessful=true`, `Payload.TotalRecords`, `Payload.Data`, `Payload.Index` |
| `/accounting/api/taxpayeraccounting/listdetail` | selected parent `RecordId`, `First`, `Rows`, `SortField=TransactionDate`, `SortOrder=-1`, `Filters`, `LanguageId` | same envelope; each detail carries `RecordId`, `HeaderRecordId`, `PeriodCode`, `Amount` |

The inspected requests used literal `LanguageId=en-US` despite the id-ID page.
Do not infer or silently rewrite it from the URL. The page separately loaded
the exact id-ID reference GET for the ordered types
`ACCOUNTING_TYPE,ACCOUNTING_TYPE_DETAIL,REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT,PERIOD`.
Catalog use must retain actual response custody, locale and version evidence;
do not force-fetch a missing catalog or read Angular/business cache state.

The owner is `acc-balance-sheet-light`, with its list under
`acc-balance-sheet-light-grid` / `ui-grid` / `p-table`. The inspected `pi-list`
action is source-bound to `ViewButton`, titled `Detail Transaksi`; its dialog
loads `listdetail` using the selected header's `RecordId`. Do not substitute
the `pi-eye`, reference-link, print, export, reconciliation or other actions.

The nine detail columns, in order, are TransactionDate, PostingDate,
TransactionNumber, AccountingTypeCode, AccountingTypeDetailCode, CurrencyAmount,
HeaderExchangeRate, Amount and ReferenceNumber. The Amount column is labelled
`Jumlah`. A complete two-row sample matched DOM amounts to JSON amounts and
contained one negative row. Both sample `HeaderRecordId` values matched the
selected parent. This is limited manual protocol evidence, not product tests
or proof that all parents and children always share one period/year.

## Scope and completeness

The first search silently adds a last-month TransactionDate filter. Merely
clearing the date widget can reapply that filter. A subsequent inspected Cari
action produced a request without TransactionDate. Clearing the period dropdown
removed its PeriodCode filter. Selecting ShowZeroValue=Yes and searching also
removed the Amount-not-zero header filter. The observed remaining filter was
`IsCancelled equals "0"`: non-cancelled transactions. Retain that boundary;
cancelled transactions are outside this proposed workbook's declared scope.

Verify actual outgoing request filters before accepting inventory coverage.
Do not use an annual-only PeriodCode filter as evidence for every month in a
tax year. The loaded PERIOD catalog contains monthly, annual, cross-year and
legacy irregular codes; do not assume it is thirteen entries per year.

Proposed completeness-first strategy: enumerate the complete non-cancelled
header list without date, amount, tax-type or period restrictions, then inspect
each distinct header's complete detail inventory. Filter on the detail's own
validated PeriodCode and negative Amount. No invariant currently proves that
an out-of-year header cannot contain an in-year allocation. A header-year-only
optimization therefore needs separate source evidence before adoption.

This strategy can add substantial requests; no elapsed-time improvement is
claimed. Use only offered bounded page sizes (the inspected list offers
10/25/50), a sequential owned browser flow, Stop checks, deadlines, response
and byte budgets, and explicit PARTIAL on a cap. Never parallelize the shared
browser or manufacture pagination requests. Full original response values stay
private; export only qualifying selected-year detail rows and their required
parent context.

For the initial supported period subset, require an exact eight-ASCII-digit
MM-MM-YYYY source code with valid month components and the job's four-digit
year component. Ordinary same-year ranges require matching source-catalog
meaning; cross-year, malformed, missing or ambiguous period meanings must not
be guessed. A negative row whose year cannot be established keeps MPN PARTIAL
and is retained as unresolved private evidence. Positively established other
years can be excluded without changing their source values.

Retain original ids and source order. Repeated transport occurrences of the
same detail id may be coalesced only after their full supported typed content
and header binding match, with occurrences retained. Distinct detail ids remain
distinct even when all visible values match. Conflicting identity/content is
not a successful retry or a reason to fall back.

## DOM, JSON and custody

In either mode, bind observed requests to this job's verified taxpayer, exact
Accounting route, main frame, committed navigation and current attempt. Bind
details to their inspected parent action and exact HeaderRecordId. Reject
stale/foreign pages, unsuccessful responses, changed inventories and identity
contradictions before fallback. Account for pending responses at final drain.

DOM mode reads only the owned visible table, verifies the complete nine-column
structure and paginator, and removes responsive duplicate labels. It can use
observed JSON for identity, pagination, hidden PeriodCode/CurrencyCode metadata
and exact numeric validation. This metadata enrichment is explicit provenance,
not an inference from the parent's period or currency. The verified request,
parent HeaderRecordId, source-bound page ordering, row count and full supported
visible row projection must establish a unique ordered binding to the original
detail records; do not match only on a transaction number or visible amount.

Builder decision after independent review: DOM success requires comparisons of
all captured Amount, CurrencyAmount and HeaderExchangeRate values against their
original JSON numeric lexemes using exact decimal arithmetic. A two-decimal
display is not proof that the source has only two decimal places. Preserve
JSON lexemes/typed provenance even when the visible values match. Dates and
classification captions retain their observed DOM text and original JSON
provenance separately; do not silently interpret a caption as an identifier.
Unavailable required metadata, an ambiguous row binding, an incomplete DOM
projection or any loss of monetary/exchange-rate precision requires whole-detail
JSON fallback. Missing required fields in JSON cannot be repaired by a parent
or guessed from a caption; the detail remains unsupported/PARTIAL.

If a detail DOM attempt is unsupported or incomplete, replace that whole detail
capture with a verified JSON attempt; never splice partial pages or turn a
failed capture into a successful empty result. JSON-first mode uses
the verified list/listdetail payloads directly. Neither mode may replay arbitrary
POSTs, generate remote documents, navigate other taxpayers or broaden login
and financial-document permissions.

Store durable, versioned MPN capture/provenance checkpoints in the private job
directory, bound to NPWP, taxpayer id, year, source mode, inventory and attempt.
Never store authentication material or request headers. Apply privacy, body-size,
path, hash and response-count checks before accepting evidence. Checkpoints
contain no inferred payments. Reuse requires complete scope and byte checks.

Builder recommendation: this first feature adds the MPN workbook, not a new
public Accounting JSON archive. Existing published SPT JSON remains unchanged.
Raw Accounting envelopes can include other years and excluded positive rows;
do not copy them into selected SPT JSON publication namespaces. The private
MPN checkpoint remains available for recovery and verification.

## Workbook and job integration

Write `MPN_<year>.xlsx` in the same final folder as resume.xlsx and the selected
SPT workbooks. The primary sheet contains qualifying negative detail rows, with
their literal period code, observed caption when proven, transaction/posting
dates, transaction number, accounting classifications, currency, currency
amount, header exchange rate, Amount, detail reference and parent reference.
Keep parent/detail ids and source provenance available in the workbook proof.
Parent and detail references must be distinguished; do not invent an NTPN or
KJS binding for a field that is absent or belongs to another owner.

Use text cells for identifiers, periods, dates and references. Preserve leading
zeroes and protect text from formula interpretation. Monetary Excel numbers
need strict source-format and precision validation; unsafe values stay literal,
visible and unresolved rather than rounded. Preserve fractional source amounts
and their signs. Do not apply corporate zero-decimal presentation to MPN.

An Audit sheet reports year/filter scope, source method and fallback, list and
detail coverage, qualified/excluded/unresolved counts and COMPLETE/PARTIAL.
A verified empty result creates an empty MPN table with truthful zero coverage
counts. A failed scan must not claim that no payments exist. resume.xlsx gains
an MPN link/status without treating MPN rows as SPT records or changing SPT
model grouping, counts, source metadata, existing formatting or PDF links.

New full live CLI and desktop jobs declare MPN as required before collection.
Overall COMPLETE requires the existing SPT gates plus complete MPN capture,
verified workbook publication and owned cleanup. Preserve separate component
statuses. Run MPN even when a valid submitted SPT inventory is empty. Explicit
Stop or selection cancellation does not start a later MPN stage.

Inventory-only remains an explicitly limited SPT-list operation. Offline export
does not invent or remotely fetch missing MPN. Old checkpoints/workbooks retain
their existing declared scope and do not certify MPN coverage. A full live resume
can add the new MPN stage using the current verified taxpayer/year.

Add MPN to the declared output set, independent workbook scope proof, physical
readback, overwrite consent, existing-output reconciliation, staging, rollback
and process-death recovery. Preserve unrelated existing SPT workbooks and JSON.
Update worker progress and the explicit WORKER_FILES allowlist without importing
Playwright/openpyxl into the GUI. Update AGENTS.md for the actual new boundaries.

## Operator-provided resume template

On 26 October the operator supplied `resume shouldbe.xlsx` from Downloads as
the required presentation reference for generated `resume.xlsx`. This is a
direct template choice, not an MPN data source. The file is 18,174 bytes with
SHA-256 `5335be67adfd604ca02bb284ae9dcf98fe4830cc951a7a9b72040f7a6904b280`.
Read-only ZIP/XML inspection passed archive CRC checks. The original remains
outside Git and must not be edited or uploaded as a live-data CI fixture.

The three visible sheets are Ringkasan, Daftar SPT and Audit. Preserve their
names, order, approved static captions, fonts, borders, fills, column widths,
merged regions, row dimensions, print configuration and the summary chart's
presentation. This replaces the current generated administration layout; it
does not change the separate SPT-form templates or capture eligibility.

Observed layout anchors:

| Sheet | Reference layout | Dynamic content |
| --- | --- | --- |
| Ringkasan | A1:H18; merges A1:H1 and B11:H11; chart anchored D13 | NPWP B2, year B3, taxpayer B4, year basis B5, overall status B6, SPT count B7, captured count B8, start time B9; type-count header A13:B13 and body from row 14; mapping status below that body |
| Daftar SPT | A1:K8; merges A1:K1 and A2:K2; SPTIndex table A4:K8 | Regenerate the title, every source row from row 5 and all hyperlinks; resize the table to actual inventory |
| Audit | A1:F11; first audit header at row 3; freeze A4 | Inventory/errors below row 3, followed by the dedicated mapping-count header and mapping audit; append required PDF/JSON/MPN evidence without dropping unresolved counts |

The reference Ringkasan/Daftar SPT have no frozen pane. Keep Audit's frozen
pane and its repeated print rows 1:3, with Daftar SPT repeated print rows 1:4.
All sheets use the inspected landscape/paper settings. Expand print areas and
relevant table/chart ranges when content grows. The reference contains no cell
formulas; do not introduce formulas merely to implement existing run counts.

The summary chart currently references A14:A17 / B14:B17, with B13 as the
series title. Rebuild its data references and caches from actual verified
counts; never preserve the example's cached counts or invent absent tax types.
Grow/move the mapping-status row with the actual count table. Place the MPN
status and relative workbook link directly below that row, reusing adjacent
styles. Expand the print area accordingly without overlaying the chart.

The source file contains real operational values and four example SPT rows.
Use a sanitized presentation resource, not the unmodified supplied workbook.
Remove source identity/year/timestamps/counts/statuses, data rows, old source and
workbook hyperlinks, unused shared strings, chart caches, private document
properties and opaque printerSettings material. Preserve safe page-setup
attributes while removing the printer-specific binary/relationship. The clean
resource may contain only reviewed static captions, styles, geometry and empty
dynamic slots. Verify every retained OOXML part and relationship, not just
visible cells, before committing it. Synthetic runner tests must verify that
no source sample reappears in zero-, one- or many-record exports.

Existing helpers currently read NPWP/year/basis/status from the old summary
coordinates, including status B8. Centralize the new layout binding and update
writer, verifier and publication readers together. Keep explicit support for
the old layout only when its complete known header/proof contract matches;
never guess scope from a convenient cell or silently rewrite old workbooks.
Proof, NPWP-as-text, year and completeness checks must remain independent of
appearance. Dynamic counts, mapping summaries and relative links remain truthful.

## Verification and remaining builder work

Product imports, fixtures, pytest, builds, source/frozen self-tests and EXE
execution remain GitHub-runner-only. Local work is limited to source/AST and
artifact/hash/metadata checks. Synthetic fixtures must contain invented ids,
names and transactions; never commit live browser responses or taxpayer data.

Behavior tests must cover late-year payments for the selected tax period,
negative/zero/positive and fractional amounts, missing/ambiguous periods,
duplicate ids versus distinct identical rows, cross-parent identity, stale and
failed responses, default date reapplication, zero-valued headers, all pages,
DOM success/whole-detail JSON fallback, caps and Stop. Integration tests must
cover CLI/desktop entry points, no-SPT inventory, legacy/offline scope, required
MPN completeness, workbook proof, existing-output consent, rollback/recovery
and current SPT Excel/JSON/PDF preservation. Add independent saved-workbook
checks for the supplied resume layout, dynamic table/chart/print ranges, old
layout compatibility and sample-data sanitization. Read back exact CI artifacts.

The builder chooses internal schemas/helper names, bounded budgets, test split,
safe parser reuse and concrete progress percentages. Before merging, review
the preceding PRs merged by other sessions, including the current list
restoration behavior, and reverify the latest main baseline and interactions.

Manual page/source inspection above does not establish a completed feature,
tested application or delivered EXE. Operator approval authorizes implementing
the described feature and reference template.

Independent builder check identified hidden period/currency metadata and DOM
rounding as the two material gaps. The explicit metadata-enrichment and exact
numeric-comparison rules above resolve both without changing the operator's
requested DOM-first/JSON-fallback behavior.
