# Development instructions

Before merging a PR, review the preceding PR merged by another session and its
interaction with the current change. Understand the affected functions and
repository contracts, and verify the latest `main` baseline before merging.
Update this file when a significant change alters behavior, architecture, output
contracts or verification requirements.

This repository is the development home for the read-only Coretax SPT downloader. Keep changes small, explicit and covered by behavior tests.

Panduan kontributor bahasa Indonesia: mulai dari [docs/README.md](docs/README.md), lalu baca [setup dan pengujian](docs/pengembangan.md), [kontrak arsitektur](docs/arsitektur.md), dan [CI/rilis](docs/ci-dan-rilis.md). CLI dan desktop dikembangkan bersama pada `main` melalui PR.

## Change and merge discipline

- Tool configuration has one owner per policy: pytest defaults/project metadata
  use `pyproject.toml`, lint uses `ruff.toml`, and coverage uses `.coveragerc`.
  Keep CI's explicit `--rcfile=.coveragerc`, required `RUNNER_TEMP` data path,
  branch settings and existing thresholds/omissions. Do not recreate an
  incomplete alternate coverage policy in TOML.
- Understand the existing functions and repository contracts before changing behavior.
- Before merging a PR, review preceding PRs merged by other sessions and the latest `main`. Read their changed functions, tests and contracts, preserve their changes, and verify interactions with the candidate being merged.
- Update this `AGENTS.md` when making significant behavior or architecture changes, recording the actual supported boundaries rather than inferring new permissions.

## Data and access safety

- Commit source, documentation and clearly synthetic tests only. Never commit real taxpayer identifiers/records, captured JSON, Excel/PDF outputs, cookies, credentials, browser profiles or local virtual environments.
- Preserve NPWP, year, return identifiers and source values exactly. Use only authorized browser access; never bypass login, CAPTCHA, MFA or taxpayer permissions.
- Click only inspected read-only navigation/View controls. Never guess row actions or submit/cancel returns, generate remote documents, or send emails.
- Stop requests take precedence over running capture. Delayed process notifications must not restart a stopped job. Keep limited or failed runs explicitly PARTIAL.
- Do not fabricate missing tax data, simulate live API output, or create files for tax types absent from the captured scope.
- New live inventories collect only the inspected same-taxpayer SPT Dilaporkan list. Do not scan archived or other status lists, reinterpret old all-status checkpoints as submitted-only evidence, or certify a missing/ambiguous submitted link as an empty inventory.

## Native JSON boundaries

Submitted-list JSON metadata supports the reviewed `ICT_RCIT/ICT_RCITR`,
`VAT_VAT/VAT_VATR`, `ICT_WIT/ICT_WITR` and `ICT_WT/ICT_WTR` pairs, including mixed
pages. Bind the six current reference/model captions without reading control
values or checked state; require flat unspanned rows. Corporate periods remain
January-to-December; Masa periods require the same valid month at both ends of
the eight ASCII digit code and a nonzero year. Accept its exact literal code or
reviewed Indonesian caption without normalizing metadata. Unknown pairs,
monthly ranges, null codes and unproved layouts retain whole-page DOM fallback.
Known contradictory pairs, reordered known family captions, period/model
conflicts and conflicting captions for one code remain fatal, including after
an earlier unsupported row. Check source-only known pairs before layout fallback.
Unreviewed period text is unsupported; recognizable different literal codes or
reviewed month/year captions remain fatal. The exact literal period and its
reviewed caption may coexist for one code; retain each row's observed display
and reject other conflicting captions after collecting the page's bound aliases.
Preserve original bytes, source fields, selected
scope, pagination, Stop and all detail/export/publication gates.

Native observers read navigation and inspected structure, never business input values, checked state or table body/footer values. Follow the current owned tab binding through one bounded panel wait; keep paginator ownership, page limits and Stop checks. A safely unsupported native attempt falls back as a whole record. Privacy, authorization, known identity contradictions and changed snapshots remain fatal; Stop remains cancellation.

Native listing period binding accepts the exact literal source code or its already reviewed exact caption, after source custody, month bounds and scope-year checks. Preserve inventory/checkpoint metadata without normalization. Corporate annual codes must still be January-to-December. Monthly ranges remain unsupported. Primary-source period codes must also equal a selected literal code even when listing evidence is unavailable; a different code/year is a contradiction, never a caption repair or a successful DOM fallback.

The L7 corporate semantic branch has its own source-proven boundary. Require both loaded corporate/main source pins, the literal selected submitted/non-history route, explicitly present valid `PreviousFormData` encoding, current source and a current-year body row. Preserve duplicate rows, literal year/model strings and raw source provenance. Only the first matching current-year zero profit may use the stable nonnegative captured Induk amount. Require exact integral operands and every ordered partial sum within the 15-digit bound; copy each captured total only after reconciliation. Empty/no-current-year, prior-only, unknown, unsafe-precision and unsupported currency branches remain unsupported. Legacy evidence-leaf bindings remain readable and do not certify template mapping. See [L7 and consolidated verification](docs/superpowers/reports/2026-10-23-corporate-l7-semantic.md).

Every PPN primary, including Normal, must explicitly bind ReturnSheetStatusCode=SUBMITTED before projection or fallback; missing status is ineligible and contradictory status is fatal. PPN AskedTo is a final-lifecycle projection, not a raw field copy. Negative submitted amendments may preserve a choice only when the facility null-write is excluded and calendar assignment is blocked across both initial and final export stages, by the source invoice/uncollected quartet predicate, or by a stable inactive capture-owned interval bound to outer PeriodYear. With calendar blocked, a proven facility null-write clears only the supported raw null/FAST_REFUND/CARRY_FORWARD branch. Exact source facility codes are AS.09-01/AS.09-02. Nonnegative FORWARD_REFUND requires a proved post-raw distinct clear event and stays unsupported. The narrow Normal nonnegative branch additionally reconciles captured output/input operands to the four/six ordered component sums before deriving its final balance; reject missing/mismatched components and unsafe operands/intermediates. Normal choice inputs are integral within fifteen digits. The shared final-balance amount helper retains only binary-exact direct fractions and exact intermediate arithmetic within that bound. Preserve all contributing source paths; do not use stale stored balances, a replay clock, or DOM checked state. Active-calendar, Normal-negative and other unproved branches use whole-record fallback.

For clock-dependent grid catalogs, use only the interval sampled by the same owned capture attempt and require one source version throughout that interval. Preserve optional metadata for old captures; never use the replay machine's clock to resolve missing evidence. Final sampling must retain earlier pending-response counts and refuse late replies as COMPLETE. Native eligibility, mapping, capture/PDF completion and final publication remain separate gates.

The separate L11-C semantic branch requires loaded corporate/main/vendor pins, the exact submitted ordinary-rupiah route, valid parent encodings, one observed offline table and all sixteen exact headers/footer spans. Preserve source rows, duplicates, literal text, distinct Number/Number2 formats and original date strings. Accept only present exact integral monetary inputs and ordered sums within fifteen digits; reconcile all six captured totals before copying them. Explicit empty null/[] bodies need six captured numeric zeros. Dates are limited to validated date-only/UTC millisecond syntax in 1970..2100 (plus the normalized year0001 blank sentinel), under id-ID/Asia/Jakarta. Country descriptions require actual same-attempt original bytes for the exact no-body id-ID COUNTRY_CODE GET, bound sequences and the reviewed stable version selector. Never force a catalog fetch or read browser cache/business state. The capture admits this GET only for verified ICT_RCIT/ICT_RCITR; unused admitted catalogs retain full safety/clock/snapshot checks and raw provenance without breaking L7/legacy leaves. Missing labels, cache-only visits and other unproved branches use whole-record fallback. Other forms, mapping and financial-PDF completion retain independent gates.

## Output contract

Resume administration uses the approved sanitized `resources/resume_format.xlsx`
presentation: Ringkasan identity/year/basis/status/counts are B2/B3/B5/B6/B7:B8,
type counts start at row14 and move the mapping summary below actual types;
Daftar SPT keeps header row4 with dynamic SPTIndex rows and original links;
Audit has inventory header row3 and freeze A4, followed by dedicated mapping
and PDF headers. Rebuild chart ranges from actual counts at D13; never retain
reference data, cached counts, links, private document properties or opaque
printer settings. Shared `summary_scope` admits only the complete operator or
legacy label/header maps. Keep old workbooks readable without rewriting them;
new coordinates must be used consistently by scope verification/publication.
These presentation changes do not alter form templates or capture completion.

Resume row/column dimensions must belong to the destination worksheet. Copy
geometry separately from workbook-local style IDs and register styled dimensions
through their actual style components; unstyled columns must remain unstyled.
Verify saved/reopened column and row defaults as well as cell borders, including
explicit borders on all six cells of MPN audit message rows with blank counts.
Use the loaded approved Audit body styles even when no SPT audit body exists.
Do not repair excessive borders by applying formatting to entire columns or by
rewriting existing private workbooks during normal export.

Full live CLI/desktop jobs additionally require a separate owned Accounting MPN
capture after SPT details and before browser cleanup, including valid empty SPT
inventories. Inventory-only and offline legacy exports do not acquire MPN scope.
The inspected same-taxpayer list/listdetail UI reads remain separate from SPT
native admission. Enumerate the unfiltered non-cancelled parents, including zero
amounts and other parent years, then qualify strictly negative original detail
Amounts by the detail's literal tax period/year. Never substitute payment date
or parent year. Same-year ranges need the exact captured PERIOD meaning;
cross-year/malformed/missing meanings remain unresolved. Only original same-
attempt id-ID reference bytes with unique codes and explicit null ValidTo supply
labels; no cache clock/version selection or extra catalog fetch is admitted.
Keep loaded Accounting main/vendor pins, committed request-object ownership,
owned pagination, Stop, terminal failures, source/privacy budgets and final drain.
DOM needs complete ordered visible binding and exact decimal validation of all
three amounts/rate; otherwise replace the whole detail with verified JSON.

MPN_<year>.xlsx has its own physical scope/ordered-row proof and Audit; it never
enters SPT workbook_groups, tax-type counts or model grouping. Keep original
numeric lexemes in proof and unsafe Excel numbers literal with a presentation
audit. Required MPN partial/failure keeps the full job PARTIAL. Publish the
verified workbook and resume link/status under existing consent, collision,
rollback and process-death recovery; preserve unselected existing workbooks.
Original Accounting JSON stays under private mpn/<attempt>/ only, outside public
SPT JSON namespaces. Bind every page to its exact query and scope, reconcile
qualified rows against original held bytes, pin ordinary directories and deny
write/delete sharing during publication. Bounds are 4096 responses, 20MiB per
body, 256MiB raw evidence and 10000/10MiB canonical rows; a reached capture cap
stays PARTIAL. New MPN/resume modules and the sanitized resource belong only to
the explicit worker allowlist; GUI dependencies and native SPT gates are intact.

MPN physical verification reads the fixed header and bounded ordered body in
one worksheet stream and the fixed Audit scope in one bounded stream, including
read-only workbooks. Keep exact dimensions, every value/literal type, empty
normalization, precision, scope, provenance, evidence and status checks. Refuse
missing/extra iterator rows. Do not return to per-cell read-only XML rescans or
treat streaming as new capture, completion or publication permission.

The pure current-only L11-A helper grants no native admission or dispatch.
Require explicit null predecessor, four complete normalized endpoint inventories,
current Facilities/Recapitulation, exact five-table headers with no footers and
independently bound labels. Preserve literal source Index/identifiers/year and
original typed provenance. Null cost inputs stay blank while contributing zero
only to the ordered six-cost calculation; check every intermediate and clamp
only the final sum before reconciling the reported total.
Negative-zero cost operands remain unsupported across their numeric lexemes;
the input control's signed-zero display has not been projected by this helper.
Preserve ordinary PartnerName text despite its source numeric annotation. Keep all twelve IV.B
controls canonical and unresolved because the approved template has no slots;
do not alter facility text or approved accounting ranges to manufacture mapping.
Native observation, catalog/packet custody, predecessors, Induk/PDF and live
acceptance retain independent gates.

The pure L3 projector alone grants no native observation, transport or dispatch.
Its bounded Rupiah branch
requires explicit current data, complete normalized B pages, the actual captured
footer payload and independently bound labels. Use active B IncomeTax and plural
WithholdingSlipsNumber/Date fields, page-local row numbers, exact A/B footer spans
and safe ordered integral arithmetic. Final B footers use captured footer data
and model overseas-credit operands, never a sum of B rows or stale saved totals.
Preserve original numeric lexemes, overwritten/unused control provenance and the
two standalone field values even though their template mappings remain unresolved.
Offline A admits an empty date as blank under its explicit null conversion;
active B admits null as blank but refuses empty-string dates in the bounded subset.
The approved resource and independent native/Induk/PDF gates remain unchanged.

Native L3 separately requires the exact submitted Rupiah `?view=true` route,
preceding Induk, valid explicit predecessor encoding, positive fresh owned SPA
lifetime and numeric1 outer/current IsIncomeTaxOverseas flags. Require all three
loaded script providers/pins, both exact grid/ui-grid/p-table/form ancestries,
groups, headers and footer spans; read no DOM business values. Turn only the
owned B paginator. Bind exact observed ten-row Language/LanguageId id-ID,
WithholdingSlipsDate/SortOrder1/empty-filter requests and the selected-ID-only
footer dependency. Retain decoded original page/footer payloads internally with
their event provenance; never reconstruct them from rendered leaf rows. Admit
only the four inspected singleton COUNTRY_CODE/CURRENCY/FOREIGN_INCOME_TYPE_CIT/
TAX_TYPE_BY_OTHER_PARTIES GETs, with exact bound sequences and reviewed cache
ordering/version provenance. Do not fetch missing catalogs. Known B/footer
identity or changed snapshots and catalog locale/snapshot contradictions remain
fatal before fallback even without a semantic binding. Generic corporate grids
retain their existing Index contract. Final drain/Stop, JSON custody, unresolved
fields, Induk/PDF/live and whole-run completion remain independent gates.

JSON-hybrid output retains only selected capture manifests and accepted original response bytes under `json/<SPT name>/<ordinal>/<attempt>/` inside the final SPT output folder, for CLI and desktop publication. New exports declare `json_output_layout=tax-kind-v1` and use the fixed names `PPh Badan`, `SPT PPh 21`, `SPT PPh Unifikasi`, `PPN` (unknown literal types use `SPT Lainnya`); retain the original ordinal for record isolation. Missing layout keeps legacy `json/<ordinal>/<attempt>/` readers compatible; reject unknown explicit layouts. Offline reexport reads the source layout and writes the new layout without deleting legacy evidence. Check existing selected paths in both layouts before replacement; duplicate private evidence cannot be hidden across tax namespaces. Keep private `returns/json/` checkpoints compatible; published manifests preserve their original bytes/references and are evidence, not standalone resumable jobs. Declare JSON separately from workbook filenames. Verify scope, record, attempt, privacy, budgets and hashes before copying from held readers, and verify staging/final bytes. Include JSON in consent snapshots, cancellation rollback and process-death recovery. Preserve earlier unselected JSON and reject changed selected evidence or case/reparse aliases. Never copy arbitrary job JSON, credentials, headers, profiles or unrelated attempts. Copying evidence does not certify capture completion or native eligibility; DOM-only jobs create no JSON directory.

`resume.xlsx` contains the global summary/index/audit. Every observed tax type gets a separate workbook per literal source period/year and literal `Model SPT`: Normal, Pembetulan 1, Pembetulan 2 and subsequent amendments must never share one workbook. Periodic types remain under `SPT Masa 21`, `SPT Masa Unifikasi` and `SPT Masa PPN`. Badan uses `SPT_Badan_<period>_<model>.xlsx`; periodic and other type filenames likewise include source period and model. Each workbook contains all observed form-only sheets for its own model. Use simple form names and minimal numeric suffixes only for workbook-local collisions; preserve raw period/model strings and leading zeroes in metadata and physical proof, never group by a display-normalized amendment label. Validate old combined exports before choosing a new final folder; do not silently rewrite or delete old combined workbooks or their PDFs. Preserve the entire folder hierarchy and exact relative links; reject case-insensitive path collisions and verify NPWP/year/basis before replacing outputs. Keep raw source values and duplicates in checkpoints; numeric analysis columns are optional. PPN verified monetary slots use native Excel numbers under strict id-ID syntax and a 15-digit precision guard; period/year, identifiers and invoice columns remain literal text. Malformed or unsafe-precision monetary strings remain text rather than being guessed or rounded. PPh Pasal 21/26 uses the approved sanitized user template for observed Induk/L-IA/L-IB/L-II/L-III forms: preserve cell styles, number formats, merges, dimensions and page layout; grow data rows by copying their original styles. For these observed PPh21 forms, omit the redundant raw/extra-source display block; preserve the entire unchanged checkpoint and report unsupported or ambiguous bindings as unresolved/PARTIAL in the resume mapping audit. Unsupported PPh21 forms continue through the generic renderer. PPN and PPh Unifikasi likewise use the approved clean layouts for observed reference forms only; bind multi-level headers and repeated labels to their visible group, never guess JSON aliases. For PPN, omit the redundant extra/unmapped block from exported forms; keep source captures unchanged and report unresolved bindings in the resume mapping audit. Its observed Period display supplies the month/year header, and Status Penyampaian is not displayed. Other Masa forms retain explicit raw source evidence below the form for incomplete tables unless an approved presentation exception applies. Never ship sample taxpayer values or reference defaults (including a compensation choice) from reference templates.

Financial PDFs are limited to ordinary inspected read-only links or the reviewed existing-document POST exposed by the FinancialStatement grid on the verified selected corporate Induk. POST support requires a verified Service-Worker-blocked owned context, matching loaded source pins, an inspected bound Unduh control, exact same-origin download route, final selected taxpayer identity and a single authenticated request; capture and abort the application request before one bounded stream replay. Do not broaden general POST permissions, guess document identifiers or retain authentication headers in diagnostics/checkpoints. Preserve explicit record/scope declarations, size/signature/hash checks, byte custody, cancellation and relative links; metadata alone is not a downloaded PDF. Publish only declared COMPLETE PDFs, never unrelated files in the job folder. Unsupported controls and failed downloads remain PARTIAL; do not invent API endpoints or remote generation actions. See docs/pdf-keuangan-post.md for the reviewed source contract.

Tab-panel readiness uses one shared 30-second deadline. Each locator read gets at most 1000 ms and the remaining budget, checks Stop first, and must not authorize capture after the final read exceeds the deadline. Keep caption/current control binding, controlled-binding history, unique owning view and actual visibility checks. One separate 1000 ms value-free timeout probe is diagnostic evidence only; it cannot authorize capture or a PDF request.

Corporate DOM capture may select an actually visible numeric page-size option
up to 500 only for a selected `PPh Badan` record, exact `L3` tab and the existing
structure observer's exact `rshshr-citr-l3-grid2` owner with sole group
`B. PPh YANG DIPOTONG/DIPUNGUT PIHAK LAIN`. All other DOM tables, inventory
callers and native observers retain their existing limits. Never synthesize a
size or request; absent larger options keep the available smaller choice and
an already selected maximum causes no reload. Preserve Stop, page limits,
owned pagination, progress checks, row order/duplicates, footer-once capture
and source-count reconciliation. This optimization grants no native eligibility
or capture/PDF/job completion and adds no output metadata fields.

Initial detail-list restoration may repeat its same inspected list navigation
once only for `ListResponseTimeout`, the absent-fresh-response RuntimeError
subtype. Keep each existing 60-second navigation/45-second response bound, a new
sequence marker, Stop checks and the same filter. Recheck authorized taxpayer
and exact list path/query after navigation and around retry; fragments are not
request identity. Never retry navigation errors, unsuccessful responses, known
identity/filter/safety contradictions, detail/View actions or financial POSTs.
All paginator, metadata and selected-record checks still precede View. A second
missing response stays PARTIAL; production panel readiness remains 30 seconds.
For restoration and its subsequent grid waits, require an observed main-frame
commit to that literal list route before admitting actual grid request objects.
Reset admission before each navigation; pre-commit/old-attempt requests and their
late responses cannot satisfy a new marker. Require the selected request
taxpayer, keep at most 128 pending owned grid requests, release references on
response/failure/close, and reject overflow or another main-frame Document.
Retain the first committed Document with a value-free identity handle. Router
replaceState/pushState/fragment notifications are allowed only while the same
actual Document and original authorized path/query remain current. A temporary
route/query/taxpayer contradiction remains fatal after returning to the source.
Veto subsequent main-frame document requests even while the first handle is
being acquired. Keep bounded post-commit grid-request custody during acquisition
but never authorize wait/View before identity is proved. Missing/unreadable
identity stays refused; Stop surrounds identity probes. Dispose handles before
retry and on failure/close. Do not read business values or relax old-request,
fresh-marker, pending-budget, timeout-only retry or selected-record checks.
An identity RPC may remain pending after navigation returns. Only the response
wait may tolerate that pending state, inside its existing deadline and with
Stop/route/request/filter/terminal-error checks intact. Identity expiry or late
completion is a nonretryable ownership refusal; an absent response with identity
already proved retains the timeout-only retry. Keep acquisition pending through
validation and bind its returned handle to an attempt token. Close/reset must
invalidate late callbacks without replacing a newer handle or pending flag.
Recheck the token after validation RPCs before callback failure mutation, also
for repeated notifications. Retire the acquisition deadline after timely
validation; the existing independently bounded loading-overlay wait remains.
Recheck retained identity, attempt, route and refusal state after the RPC, then
reread filter errors. Check every reused record and metadata result, and check
again after JSON preparation immediately before clicking the held inspected
View element. Release that element without masking Stop or an original failure.
The authorized View may navigate the same tab; subsequent detail checks retain
their existing selected-record and lifecycle gates.
Owned HTTP failures are terminal even for HTML; explicit unsuccessful JSON is
terminal before successful-row parsing and cannot be cleared by later traffic.
Keep only fixed failure state, with no new request material in diagnostics.

Accounting source admission requires post-commit main-frame GET script requests
for the exact reviewed providers, or GET xhr/fetch requests for the exact reviewed
reference route. Nonqualifying asset/catalog observations establish no proof and
do not enter source-response custody. Retain admitted URL and resource kind and
reject later ownership changes before reading bytes. Safety refusals are sticky;
later unsupported traffic cannot clear them. Record only the first source refusal
as `mpn.source_rejected`, with a fixed `mpn_source_stage` and sanitized error frames;
never retain an exception, traceback, URL, header or body for deferred logging.
A COMPLETE empty MPN capture requires its owned original zero-row inventory
response and final drain. An iterator yielding no pages remains PARTIAL, and a
capture attempt cannot omit original inventory evidence even when headers are zero.
These rules grant no new source pins, requests, locale or native admission.

Accounting first completes a separate bounded session-preparation navigation
before constructing any capture observer. Only the literal selected ledger,
query-free origin root and `/accounting/id-ID/` root, and exact same-origin
`/accounting/id-ID/auth-callback` path are admitted during preparation; every
fragment, foreign route/origin or selected-identity contradiction stays fatal
after returning. Never read or retain callback queries, tokens or browser
storage. Recheck Stop, refusal, literal ledger and the original 60-second
deadline after readiness reads, and remove the listener on every exit. Begin a
fresh literal navigation and request custody afterward; preparation bytes,
scripts, catalogs and grid responses grant no capture proof or completion.
This is session initialization, never a retry/reset of a rejected capture.

Owned Accounting capture retains the first committed actual Document through a
value-free handle and attempt token. Same-literal-route router notifications
require that identical Document; new main-frame Document requests, temporary
route/query/fragment changes, unreadable identity and late acquisition remain
fatal. Pending identity may only hold bounded request objects inside the
existing deadline; defer source reads until identity is proved. Reset/close
invalidates late callbacks and releases handles. Sticky observer failures stop
UI preparation before another action. The shared 45-second UI-preparation
deadline covers owned component/control/grid readiness and searches. Wait for
zero matching controls to become unique/visible, reject duplicates, and retry
only value-free actionability probes; each actual inspected click occurs once.
The real list grid is created by the first Cari, so bind it only after that
owned original response. Retain at most the existing second Cari to remove
default dates/period filters and require the exact unfiltered non-cancelled
query. Source pins, genuine-empty inventory, Stop, budgets and final drain
remain independent completion gates.

After selecting either inspected Accounting preparation dropdown option, wait
for its visible panel to close before the next action. Use value-free structure
and the same shared 45-second deadline, with retained Document, Stop and sticky
source/observer checks before and after each bounded RPC. Multiple panels stay
unsupported; a stuck panel stays PARTIAL. Never repeat an option click, add a
fixed settling sleep, read a selected value or extend preparation's deadline.

Accounting grid requests preserve either reviewed literal `en-US` or `id-ID`
LanguageId. Bind one language throughout the owned attempt and held original
query reconciliation; a change between known languages is fatal, unknown codes
remain unsupported. The reference GET stays strictly id-ID. Retain the already
verified initial page size and owned pagination instead of changing its optional
picker. The pinned read-only detail action may use the exact source-named
`button#ViewButton[type=button]` with `.pi-list` and no HTML title; retain the
legacy exact Detail Transaksi title branch and reject contradictory action
metadata. Bind the selected row first, and require the unique visible Detail
Transaksi dialog/title/grid within one five-second readiness deadline.

The original admitted reference response may finish before the first parent
binding, including after initial UI preparation. Wait at most five seconds for
already owned pending sources before freezing that binding; never fetch a
missing catalog or use browser cache. Retain its original bytes once in private
evidence even if they were unavailable at open. Changed snapshots stay fatal;
first catalogs arriving after binding stay unsupported. Preserve the earlier
pending-reply latch at final sampling, including valid empty inventories.
Sticky source/observer safety failures outrank transport failures and deadlines.
Recoverable grid failures preserve Document custody for classification but admit
no more evidence/actions. After the final Document RPC, recheck local Stop/source/
observer state before every actual action; no callback-pumped refusal may be
masked as a successful click or a new identity contradiction.

The same fatal-state reconciliation applies when observer RPCs/waits raise;
never demote a callback-pumped source safety refusal to recoverable PARTIAL.
After final provider reads and retained-Document validation, recheck local flags,
original pending latch, current pending objects and both sampling sequences.
Freeze admitted catalogs before reading the parent DOM snapshot used for
identity. Parent binding includes the observed accounting type/detail captions
from those same original catalogs (literal codes remain a bound fallback), plus
the existing currency/KAP/KJS/period/transaction columns. Repeated projections
may use the additional Referensi caption only through the pinned helper's
present-string ReferenceType branch with populated classification codes. Start
from literal ReferenceNumber, apply its exact reviewed tax-type/Replacement
caption and TaxNotice/Adjustment-AIP overrides; never copy the raw Reference
link field, follow that link or guess another source alias. Require every
matching peer's caption and a unique selected-record match. Still-identical or
unproved captions remain unsupported; original source fields stay unchanged.

The ordinary Accounting parent detail-caption column may bind blank for a
nonempty literal AccountingTypeDetailCode only when the complete same-attempt
original ACCOUNTING_TYPE_DETAIL code inventory proves that code absent. Retain
all original codes separately from eligible null-ValidTo labels; malformed or
non-string code entries leave absence unproved, and present ineligible codes
never become absent. Default catalog readers remain unchanged. Recompute every
peer's projected caption before uniqueness/reference/numeric binding, so missing
codes that both display blank cannot manufacture identity. Other columns and
fallbacks retain their boundaries; preserve raw metadata/bytes, source/catalog
custody, Document, Stop and all independent completion/publication gates.

The inspected detail dialog may render below a direct body-level
`.p-dialog-mask.p-component-overlay` wrapper. Require the unique selected
`p-dialog#isShowDetail` host, no visible role=dialog before clicking, the owned
selected-parent response, exactly one new visible dialog, the exact Detail
Transaksi host/title with matching aria-labelledby/title id, and its unique
grid. Keep the legacy descendant dialog branch. No pre-existing/ambiguous
overlay, foreign caption or absent title binding authorizes a detail action.

Accounting detail open/close clicks each occur once within a five-second
action bound and no implicit driver navigation wait. Explicit owned-response,
retained Document/route, five-second dialog readiness and hidden-dialog checks
remain required; the single hidden-dialog wait has a five-second bound. Reconcile
Stop and callback-pumped source/observer refusals
after both clicks and the hidden wait, including RPC exceptions. Never retry a
completed or uncertain click or admit a new main-frame Document through this
wait policy.

If the existing seven-column parent identity and supported original Referensi
caption still repeat, the five inspected list number cells may supply a final
bounded identity. Bind CurrencyAmount/CurrencyAmountLeft/ExchangeRate/Amount/
AmountLeft at cells7..11 for every matching peer in the same ordered snapshot.
Require original numeric literals, exact finite integers within fifteen digits
and exact strict id-ID DOM equality. Missing, fractional, unsafe or malformed
proof stays unsupported; known differing values/row order remain fatal. One
RecordId alone must have the selected numeric tuple; equivalent lexemes and
signed zero never manufacture uniqueness. This grants only the already
inspected detail action, adds no source/request or output metadata, and retains
Document/Stop/final-action fences and independent completion/publication gates.
Validate every participating peer's original taxpayer/cancellation ownership
before caption or numeric fallback. Latch unsupported numeric fields/peers while
still checking every independently supported value and visible binding; an
earlier unsupported field/peer cannot hide a later known contradiction.

Accounting original null-Index/full-page totals may declare the bounded
`frontier-v1` continuation contract: the first total must be Rows+1 and every
continuation total First+Rows+1. Bind identical queries, page sizes and languages,
contiguous offsets and previous frontier=next First+1. Only an original nonempty
terminal page with total=First+row count closes it, including a full terminal
page. A promised continuation followed by an empty page contradicts that proof.
Missing/non-null Index, arbitrary total changes, gaps, changed identities/content,
pending replies and reached caps remain refused/PARTIAL. Derive each list or
parent-detail mode from its first original response; persist literal totals and
an explicit per-page descriptor, never a fabricated final count. Missing mode
retains legacy `fixed-v1` exact-total semantics. Held readers independently
reconcile eligibility, mode consistency, every transition and terminal counts;
unknown/mixed descriptors are fatal. These rules admit no extra route or request
and do not relax selected taxpayer, source pins, privacy or publication gates.

MPN source ownership refusals additionally report only the first failed fixed
`mpn_ownership_reason`: navigation, frame, method, page_route, request_url or
resource_kind, in the existing short-circuit order. Keep the original first
refusal event and sticky fatal escalation. Other source stages omit the reason;
never log the compared values or infer a live repair from the new diagnostic.

The approved L7 year header accepts only the exact literal annual `0112YYYY`
source code or the existing exact `Januari - Desember YYYY` caption, reconciled
with the single captured table's complete header set. Monthly/partial-year and
malformed periods do not qualify. Preserve the literal period/model and captured
body/footer values; footer ownership, accounting and PARTIAL gates are unchanged.

The inspected submitted corporate financial-POST detail also supports exactly the literal read-only query `view=true`. Reject duplicate/additional/encoded query variants, fragments and changed complete document URLs. Legacy corporate routes remain query-free. Preserve every existing request/body/authentication/source/selected-identity gate. Financial guard diagnostics expose only allowlisted module/function/line frames, never exception text, request URLs, headers or bodies.

The financial route callback records its first rejection immediately as
`pdf.request_rejected`, with only a fixed `pdf_guard` stage and sanitized error
frames. Later invalid-state checks must not replace that originating evidence.
Do not retain an exception/traceback or request material for later logging.
Stage values and safe frame lines diagnose existing checks; they grant no new
request permissions and do not certify a downloaded PDF.

The temporary captured Authorization value has a finite 65536-character budget,
including its token-type prefix; the earlier 8192-character limit rejected valid
larger interceptor headers. Missing, empty, unsafe and over-budget values remain
unsupported. Preserve the exact captured value through the same one-request
replay; never construct a credential, drop authentication or broaden POST scope.
An accepted envelope may log only `pdf.request_captured` with the fixed
`authorization_budget` category `within_8k`/`above_8k`, without a raw value or
exact length. This category confirms transport-budget diagnosis, not credential
validity, replay, native eligibility, PDF completion or publication.

Corporate presentation exceptions: `resources/corporate_format.xlsx` is the approved sanitized default for its twelve reference appendices; copy only observed forms and do not fabricate an Induk layout. Exclude only literal L10-B/L10-D from new corporate workbooks, never from checkpoints or retained physical proof/index namespaces. Repeated corporate table headers require observed owner/group metadata, not financial values or source order. Keep ambiguous content visible and mapping counts truthful, except the explicitly approved clean L6/L7/L10-A/L10-C presentation: omit their raw appendices while retaining checkpoints and unresolved audit counts. L6 B2:B8 and writable L7 C1:I13 cells use rupiah accounting; preserve merged labels. Corporate footer mapping preserves literal account codes, inspected colspan/label ownership and captured totals, including all three L3 footer rows and the final L1-D total at reference row 101. All observed approved Unifikasi reference forms, including Induk, omit redundant raw display appendices while retaining checkpoints and unresolved counts; DAFTAR-I rates use numeric percentage fractions and preserve the blank spacer. Preserve the blank separator before BPNR and exactly one empty row before the LAMPIRAN-I total, following observed body rows. PPN A-2 cell B15 uses centered alignment. These display rules do not relax capture completion or native eligibility gates.

Additional approved corporate presentation rules: L2/L3/L4/L11-A/L11-B also omit redundant raw display appendices while preserving checkpoints and truthful unresolved counts. Apply the user-approved accounting ranges and L2 percentage formats without converting identifiers, dates, job titles or headings. Verified percentage points become Excel fractions under strict id-ID and precision checks. In the verified L1-D balance-sheet owner, the exact subtraction caption `Dikurangi: Akumulasi penyusutan aset tetap dan inventaris` displays a safely parsed amount as negative absolute value; retain its literal source value in checkpoints. L9 accepts the observed `KELOMPOK LAINNYA` caption only with its inspected component/outer-group ownership; never infer missing legacy ownership from table order. L11-B DER references the uniquely bound captured debt/capital average totals, follows inserted rows, and divides only valid numeric inputs with nonzero capital. Missing/unsafe/zero operands remain unqualified without invented zero results or fabricated unmapped-source counts. Preserve the requested DER labels and merges.

Latest approved corporate clean presentation: Induk now uses the operator-approved two-column layout and L8 the approved three-column table, with only static captions/styles in source. This supersedes the earlier generic-Induk restriction. Induk/L1-D/L8/L9 also omit redundant raw display appendices, retaining checkpoints and truthful unresolved counts. Compact only known template body ranges to populated captured rows (zero and False are content); keep one body slot for an empty table, intentional separators, headers, captured totals, merges and styles. Map before compaction and move verified DER references with both removed and inserted rows. L1-D omits its first three title/identity rows plus the empty row before its first header; metadata remains in checkpoint/proof. All corporate accounting defaults to zero decimal places, including existing reference accounting cells and newly bound monetary cells; retain exact stored numeric values without rounding. DER ratios and percentage displays keep their existing two-decimal formats. These are presentation exceptions only; native eligibility and capture/PDF completion gates are unchanged.

Owned L8 DOM capture records raw body cells, colspans and rowspans atomically under the exact `rshshr-citr-l8-form` / `rsh-citr-l8-form-grid1` owner and observed group. Single-page `[1,2]` heading cells may merge B:C; ordinary cells and footer remain three columns. Reject contradictory/missing span proof, foreign ownership and unsupported rowspans; never pad legacy two-cell rows or infer their columns from labels/positions. Preserve raw captures and unresolved counts. The approved Induk presentation uses populated C/D/E/F section headings and one blank separator after identity, safe numeric monetary slots with zero-decimal accounting, literal identity/choice fields, the tariff caption without its numeric choice prefix, and the reviewed title/borders/width. L6/L8 use the approved thin borders. Resume Audit gives mapping counts a dedicated field/table/row header without changing inventory headings, existing row markers, PDF links or completion semantics.

The reviewed Induk C-section binds its two additional monetary amounts only by
the exact group, blank field name and full captured question caption, separately
from the similarly named radio choices. Keep duplicate/foreign/unsafe bindings
unresolved. Only populated groups receive section headings; the C heading is
unbordered and D/E/F headings use horizontal rules. Keep the approved tariff
position at the end, first captured L9 total bold, and the empty L10-C monetary
body slot in zero-decimal accounting. Reviewed L2/L3/L6/L8/L9/L10-A omissions add
`reviewed_redundant_fields`/`reviewed_redundant_tables` counts to mapping reports
and an Audit note; those counts remain included in unmapped totals and never
promote COMPLETE. New DOM business-field capture excludes actual paginator
descendants. Never classify legacy unnamed values as paginator proof. The three
reviewed-but-unqualified L11-B unnamed controls retain their unresolved counts
until informative source evidence is available; preserve DER availability gates.
Recovery fixtures use a two-second synthetic budget with a slow healthy read,
failed middle panel, later-panel recovery and Stop propagation. Production's
shared 30-second readiness deadline and diagnostic budget are unchanged.

MPN published proof also retains qualified-row original response hashes and
page-local indices, including duplicate occurrences, without private paths or
raw bodies. Reconcile those bindings against held original pages. COMPLETE
requires exact occurrence/coverage reconciliation; PARTIAL may retain only a
proved processed prefix when a capture budget stops processing. Audit reports
requested mode, qualified DOM/JSON rows, excluded/unresolved/duplicate detail
counts separately, plus held details not yet processed at a partial budget.
Preserve absent legacy counters as blank rather than guessing.
Accounting's route owner may mount after DOMContentLoaded: wait inside one
45-second Stop-aware deadline before requiring uniqueness/visibility. Unsupported
detail DOM shape/readiness uses the complete owned JSON detail inventory; dialog,
paginator, source and identity contradictions retain their independent gates.

## Issue #143 diagnostics boundary

Corporate native refusals may emit only the finite observer-stage enum and a
bounded tab ordinal before the existing whole-record DOM fallback. MPN capture
failures may emit a finite collection-stage enum and sanitized exception
type/frames. Issue #143 follow-up L3 subreason is a second, fixed allowlisted enum on
observer refusal; it must not expose request fields, hashes, labels, DOM content
or asset metadata. The MPN Search action may receive a bounded single-click
timeout (5 seconds maximum within the existing 45-second preparation deadline),
while all other control action budgets remain unchanged; never retry an actual
click after a timeout because dispatch is uncertain.

Post-merge Issue #143 diagnostics split L3 MAIN source digest, VENDOR source
digest and exact two-table count into separate finite `corporate_l3_reason`
categories. Never emit the observed hash, table contents or source identifiers
in logging; on refusal, continue whole-return DOM fallback without weakening
custody. The MPN `accounting_type` mismatch records only catalog-projection
provenance as a fixed enum, not the code/label/DOM value. It is not permission
to replace source labels, repair catalog mappings or click detail under
`MpnSafetyError`.

The general DOM table collector uses a 180-second elapsed budget per table,
checked before each additional page action. Preserve the Stop-first rule,
original owned paginator checks and individual browser timeouts, retain
already captured rows only as PARTIAL, and keep the first failure reason
when row-count reconciliation also disagrees. This is not a hard interrupt
for an in-flight browser action or a reason to increase other timeouts.

Issue #143 follow-up logging preserves the original MPN unfiltered
non-cancelled source-query predicate. On failed preparation, record only
finite source-request filter categories and the inspected period-clear
control's presence class. Do not log filter names/values, claim that the
clear action succeeded, invent a control, accept a filtered list or
increase the two owned Search attempts. L3 failed two-table count gains
a fixed `zero`/`one`/`more_than_two` classification without changing
its admission rule. Elapsed DOM table budget may log a fixed action-stage
category and already captured page count without retrying a paginator
click, changing elapsed policy, or promoting PARTIAL.

For Issue #143 live follow-up after PR #150, classify only owned original
MPN reference GET readiness as accepted, observed-but-unbound, or not observed.
Never trigger a new reference request, infer a catalog from cache, or map a
display label to an unproved code. If the sole mismatched field is accounting
type and no original code inventory exists, refuse as MpnUnsupported rather
than claiming a known contradiction; no detail click. Independent identity
contradictions remain MpnSafetyError. After a DOM paginator click, bound the
Playwright table DOM read to 10 seconds and the remaining per-table deadline;
a timeout retains only preceding verified pages as PARTIAL and never retries
the dispatched click. Classify additional L3 form tables against both
source-reviewed grid owners as hidden/visible extra or unproved pair; retain
the exact two-table native admission requirement on every branch.



These fields are diagnostic evidence, not capture proof: preserve
every original source pin, privacy/identity gate, Stop, checkpoint and PARTIAL
outcome. Never log tab captions, URLs, taxpayer values or exception messages.
See `docs/diagnostik.md`; synthetic tests alone do not certify the live case.

## Verification

Capture table/panel/view failures and the inventory catch use only fixed
`capture_timeout`, `capture_safety_refusal` or `capture_failed` messages. Keep
their existing PARTIAL/Stop/filter/PDF behavior and later-panel recovery.
Diagnostic `error=exception` uses the closed type/frame sanitizer; never replace
it with arbitrary exception class names or serialize exception text. Optional
diagnostic root lookup, including RuntimeError and logging OFF, cannot prevent
CLI execution. Keep old private checkpoints readable.

The source-proven full L1-D profit table has35 slots including account5322.
Its approved34-slot reference may grow only at the verified internal account
position after exact component/group, ten-column, account/group sequence and
reference-merge checks. Plan against copied post-growth merge geometry before
mutating the sheet; retain existing totals, subsequent blocks, styles and final
compaction. Do not append5322 after totals or change the sanitized resource.

Optional `component_lifetime` evidence belongs to the capture manifest only.
For the reviewed ordinary corporate SPA branch, start at one visible submitted
list owner before the inspected View, in the owned Service-Worker-blocked
context. Retain the original Document and exactly one selected `?view=true`
main-frame transition; observe the unique corporate owner and recheck before
sealing. Known document/route detours or the exact financial replacement POST
remain fatal. Record only the replacement veto, never its body or headers.
Unavailable evidence leaves the new dependent branch unsupported. Bind each
replayed fact to the attempt, record and literal source/detail URLs; reject
descriptor overrides and mixed packet evidence. Stop checks surround every
probe and final probes stay inside the existing late-response drain fence.
This metadata alone does not enable L1-D or certify source pins, mapping or PDF
completion.

Native L1-D additionally requires all three loaded corporate/main/vendor pins,
the literal submitted current-View route/model, preceding observed Induk, outer
BC04 classification and an explicit boolean IsMigrated. Observe the unique
visible L1-D form and all three exact table/component/A-B accordion owners;
require script-provider evidence for every pinned asset, not fetch/preload alone,
and validate the actual table's p-table/first-financial-wrapper ancestor chain;
retain their actual source_structure, headers and footer spans without reading
body/footer values or inputs. Require explicit valid PreviousFormData encoding,
the complete current L1dFormData and the reviewed safe code/mask/total projection.
Bind every projected value to its original response sequence/container/path.
Missing proof uses whole-record fallback; known lifetime/encoding contradictions
remain fatal. Replay must retain manifest custody. This branch does not certify
Induk mapping, financial PDFs or other corporate forms.


Ordinary PPh21/Unifikasi grid catalogs and corporate COUNTRY_CODE must reproduce
the pinned full-catalog cache order before grouping by Code or selecting a
version. Default to stable ascending literal UTF-16 CodeDescription order. Only
the first raw Details row can trigger parsed ParameterData.DisplayIndex through
the exact `"DisplayIndex":` substring. The supported triggered subset is one
homogeneous family of safe JSON integer literals or literal UTF-16 strings;
malformed, mixed, coercive and unsafe keys remain unsupported. Preserve original
rows, duplicates, candidate evidence order, ParameterData and selected raw paths.
PERIOD/model dropdown uniqueness and the owned attempt-clock stability rules
remain separate. Sorting does not authorize cache reads or extra requests.
Check every explicit catalog/detail language contradiction before unsupported
shape/order fallback, including packets without observed forms. PPh21/Unifikasi
ordinary duplicate-Code catalogs additionally require positive Induk
`reference_order_build` custody for the exact reviewed loaded vendor digest.
Pure projectors only declare the dependency. Observe the optional proof once
through the existing bounded asset reader; never fetch an absent asset. Any
present invalid proof is unsupported, while missing proof preserves legacy
unique-Code compatibility. Retain the verified digest with selected provenance.
For this optional vendor proof, a resource entry must be script-initiated or
the exact script must be connected. Fetch/preload-only entries are insufficient;
keep this stricter check and hashing in one evaluation without changing the
generic source reader's existing contracts.

Submitted corporate L7/L11-C semantic proofs accept only the literal selected
query-free legacy route or that exact route with `?view=true`, matching the
inspected submitted-list View. Keep the proof route exactly equal to the captured
frame; other query spellings, history routes and identity conflicts retain the
existing rejection rules.

Native current-only L11-A uses the separate corporate-l11a-v1 proof, the exact
three loaded provider pins, fresh owned submitted ?view=true lifetime, preceding
Induk and numeric1 IsDeclareEntertainmentExpense in outer/current MainFormData.
Require explicit PreviousFormData encoding with absent/null L11A predecessor.
Observe all five exact grid/ui-grid/p-table/form and group/header owners before
and after the four owned paginators, including the nested IV/IV.A offline table;
read no DOM business values. Bind the four complete Data/TotalRecords inventories
with the exact inspected seven-field requests, Rows10 and empty SortField.
Closed reference admission adds only the five inspected L11-A singleton GETs
and the literal ordered DEDUCTION_METHOD,TYPE_OF_FULFILLMENT pair. Bind unique
catalog types while preserving original Payload/catalog/detail indices and
ordinary ordering/version proof. Never force-fetch a missing catalog. Preserve
fatal identity/snapshot/query-count checks before fallback, even unbound, and
compare full typed same-kind catalog content across admitted endpoints before
overlap fallback, retaining numeric lexemes, metadata and duplicate order. The
catalog type must be requested by that exact endpoint; a wrong marker remains
unsupported source shape rather than establishing a new catalog identity.
Count queries include endpoint and every field except First. Scope L3/L11-A
auxiliary exact-set checks to each form's endpoints without admitting unrelated
responses. Keep all twelve IV.B fields canonical and unresolved; template,
monetary formats, native eligibility/PDF gates and 45-worker allowlist stay intact.

The pure L8 helper alone grants no native admission, observation or transport.
Its supported ICT_RCIT/id-ID branch requires
matching original numeric literal main/outer years 2020..2100, explicit unsigned
nonnegative safe integral operands, turnover at most 4.8 billion and zero main
research. Translate Decimal conversion failures to the same unsupported-input refusal
inside the L8 guard; never broaden that catch to other projections or controls.
Reconcile captured shares with the thousand-masked main taxable input,
captured 11%/zero taxes and the reported total; never replace a mismatch. Keep
eight physical body rows, original spans/captions, one footer and typed source
provenance, including both captured tax operands supporting that footer. Retain
optional numeric/null ExchangeRateValue as unused parent-control evidence only.
Caller must prove unchanged original CurrentFormData.MainFormData operands equal
stable final inputs and that the effective grid rate remains 1. A fresh grid on
an uninterrupted Rupiah route has that conditional source invariant; it is not
proved by the parent's saved exchange control. Native lifetime, dependency-cache
visibility, main recalculation, async readiness and final callback proofs remain
separate. Preserve the approved renderer/template, 45-worker list and PARTIAL gates.

The separate native L8 branch requires loaded corporate/main/vendor script
providers, id-ID/Asia/Jakarta, the literal submitted selected `?view=true` route,
preceding observed Induk and both the existing component lifetime and optional
manifest-owned `corporate_l8_lifetime`. Arm structure-only history before View
with no corporate root or L7/L13A/L13B host anywhere, including hidden nodes.
Retain the unique root identity; any removal, replacement or duplication is
fatal even after reinsertion. Dependent hosts seen transiently remain unsupported.
One bounded 4096 record/node observation budget may refuse proof; it grants no
business-value read. Final history sampling stays inside the late-response fence,
and observers/handles are released on cleanup. Missing proof preserves legacy
fallback; present malformed, unbound or mixed proof remains fatal before fallback.
Keep strong facts on the manifest only, never response descriptors, and retain
their exact attempt/record/source/detail binding during held reads and replay.
The admitted original main/outer subset has exact TX03 rates, numeric literal
annual 1/12 bounds, explicit null PreviousFormData/LastSubmittedFormData and
numeric literal zero on both owners for IsCarriedForward, IsNetIncomeReduction,
IsInvestmentOtherIncome, IsGrossIncomeVocational and IsGrossIncomeResearch.
Current L7/L13A/L13B roots must be absent, not null. Require nonnegative safe
integral net income, identical fiscal net, zero captured reduction/vocational/
carry/research totals and the exact thousand-truncated taxable input. Copy only
reconciled original L8 values and preserve every contributing raw input path.
The fresh Rupiah grid keeps internal rate 1 despite asynchronous parent rate
references; do not fetch references, inspect Angular state or use a quiet timer.
Other source/lifecycle branches retain whole-record DOM fallback. Capture,
mapping, financial PDFs and live acceptance remain independent gates.

Approved compact Masa presentation: bind against original reference coordinates,
then remove only declared empty body capacity. Keep populated rows (including
zero and False), one body slot for an empty table, intentional separators,
captured totals, merges, styles, row dimensions, widths and page layout. PPN
Induk omits original blank rows 8 and 25. PPh21 L-IA/L-IB omit one extra blank
row before the first header; reuse external group/footer separators rather than
adding a duplicate spacer. L-IA verified percentage points become safe numeric
Excel fractions with a 15-digit precision guard; invalid values stay literal
and unresolved. PPN/PPh21 accounting defaults to zero decimals without rounding
stored values. Checkpoints, proof, native eligibility and PARTIAL gates remain
unchanged. Binding tests can isolate original geometry; independent saved export
tests must exercise final compaction without suppressing it.

PPh21 L-IA dan Unifikasi DAFTAR-I memakai parser persentase bersama di
`coretax_template_cells.py`. Blank tetap kosong; hanya angka biasa atau
digit ASCII dengan koma desimal opsional dalam rentang 0–100 yang boleh
menjadi pecahan numerik. Periksa maksimum 15 digit koefisien sumber sebelum
pembagian, kesetaraan desimal setelah konversi float, dan batas minimum
normal Excel untuk hasil nonzero. Underflow, subnormal, dan presisi tidak
aman tetap literal dan unresolved; jangan mengubah checkpoint atau grammar
persentase Badan yang terpisah.

Create a local `.venv` with the production CPython/GIL pin in `spt_desktop.runtime.PYTHON_PROFILES`. Install the resolved test environment using `uv pip sync --python <venv-python> --require-hashes --only-binary :all: locks/test.txt`; use `locks/build.txt` for packaging. Run `python -m pytest tests -q` on Windows with a dedicated scratch `--basetemp` outside the repository. Linux can run the reviewed portable subset through `-p scripts.ci_tests --ci-workload portable`; Windows runs the full suite. Browser tests use isolated local synthetic HTML fixtures and an installed Microsoft Edge; they are not live taxpayer tests. Verify changed behavior, output counts, literal source text and links before committing.

For this user-authorized work, pytest, product imports, native/Tk/browser fixtures, source/frozen self-tests, builds and EXE execution are GitHub-runner-only. Local AST/source checks and artifact hash/metadata inspection are not execution evidence. Do not modify user-owned CI merely to obtain GREEN. Bind claims to exact head/merge tree/run/artifact ID and preserve recovery work.

Use an existing saved JSON capture for offline export/layout checks when appropriate, but keep that capture and its generated files outside version control. Review `git diff --cached --name-only` and staged content for private data before any push. Preserve the existing LICENSE.


## Desktop boundaries

Register the CLI Playwright manager teardown before entering it: initialization
can acquire its driver transport before an error or Stop. Contain early teardown
failures, retain original exit 1/130 and durable checkpoints, and attempt every
later owned cleanup. Never close a reused browser context.

Detail collection records only the existing fixed capture error categories in
run/checkpoint/console messages, never an external exception's text or string
conversion. Retain original safe error type/frame diagnostics, cancellation and
fatal JSON safety semantics. Owned list restoration lives in the same browser
module helper, preserving module hooks, request/page identity, operation order
and all checks before View. Source-only quality inventories use the explicit AST
definitions in `scripts/quality_inventory.py`; their counts are not runtime proof.

Quality tooling is isolated in `locks/quality.txt` from exact
`requirements-quality.txt` pins, checked by the existing all-or-nothing lock
updater and dependency audit. Mypy strictly adopts only the existing stdlib
build identity and UI state owners under Python3.14, without blanket ignores.
TypedDict/TypeGuard describe validated boundaries; runtime JSON/boolean/value
guards stay authoritative and public payloads unchanged. Bandit scans all
root coretax Python and desktop modules; only reviewed source-local rule IDs
may be suppressed with their reason. New subprocess callers, driver cleanup
or source changes need their own review; annotations grant no new permissions.
Keep CodeQL, locked dependency audits, Ruff and full test/build gates independent.

Windows parent-process coverage uses the existing `.coveragerc` and separately
declared line/branch/module/diff floors in `coverage-policy.json`. Before package
build, validate the complete passing serial or fixed two-shard Windows inventory
for the exact commit/run/attempt and combine only its explicit raw-data slots.
Never use portable-only, old, failed or missing-shard data as representative
acceptance. Changed excluded or unmeasured production lines remain refused;
percentages use exact integer ratios.
Pure comment-only files leave the diff budget only after complete non-comment
token equivalence; retain indentation, statement boundaries and all code tokens.
Mixed/new/code-changing files remain conservatively counted. Keep native/browser/Tk
and in-process
worker coverage distinct from unmeasured isolated worker/bootstrap subprocesses
and browser JavaScript. Preserve runtime isolation and all independent security,
source/frozen, bootstrap, inventory and publication gates. Enumerated security
behavior acceptance is documented in docs/audits/2026-10-29-windows-coverage.md;
it is not a claim of all-source100% or live acceptance.

CLI live failure/Stop recovery writes only a normally validated PARTIAL run.json
after the existing checkpoint/physical-workbook scope and selected-JSON checks,
through the existing guarded atomic checkpoint; never retry save_output from
an error handler. Invalid runs and storage failures preserve the last durable
checkpoint and existing workbooks. Keep fixed public/checkpoint error messages
and sanitized diagnostics. Close every CLI-owned page/context/driver in reverse
ownership order, including after failed acquisition; never close reused external
contexts. Ordinary cleanup failures cannot mask an active error or Stop, and a
cleanup failure after normal work cannot report CLI success. Stop during cleanup
or checkpoint recovery retains exit130; ordinary failure retains exit1. These
rules do not weaken capture/custody/publication checks or alter desktop outcomes.

- The bottom-right bug-report contact uses its own 12-point font and retains wrapping and bottom-right placement. Compact windows reserve enough vertical space for the summary and initial inputs; retain existing horizontal wrapping measurements. Source/frozen self-tests verify its effective font size and real geometry; do not enlarge shared caption/status styles to achieve this.
- The SPT selection list uses presentation-only period captions: exact case-insensitive PPh Badan displays `Tahunan`; recognized monthly numbers, same-month period codes and Indonesian month/year captions display the month name. Ambiguous periods remain literal. Preserve original metadata, checkpoint/export periods, identifiers, search by source values, original chronology keys and inventory-order consent IDs.
- The GUI is a thin stdlib/Tkinter launcher. Do not import Playwright/openpyxl into its process; prepare the isolated worker with uv and copy only `spt_desktop.runtime.WORKER_FILES`. Update that explicit allowlist when adding worker modules; never recursively package workspace/profile/output directories.
- Windows Job Objects must contain suspended children **before** resuming them; uv-created virtualenv Python launchers can spawn an interpreter before Python code runs. Preserve start authorization, cooperative cancellation, 15-second forced owned-tree cleanup and main-thread-only UI callbacks. Success requires terminal COMPLETE, matching exit code, verified output and completed owned cleanup—not a zero exit alone.
- Saved credentials belong only to Windows Credential Manager and exact approved origins. Never print fill exceptions, inherit Playwright credential-debug flags, guess login actions or click generic form-submit controls. Require inspected sign-in intent and no unknown challenge/fields; otherwise manual visible login. No MFA/CAPTCHA bypass.
- Application-owned CLI and desktop download contexts explicitly use browser locale `id-ID` and timezone `Asia/Jakarta`, matching the reviewed Indonesian display/date consumers. Keep service workers blocked and native observer environment checks strict. External reused browsers retain their own environment and unsupported environments use explicit whole-record DOM fallback; never infer the browser locale from the workstation or portal URL.
- Exercise both source and frozen GUI self-tests without real accounts. The Windows CI artifact must be read back by exact run/commit/artifact ID before reporting build success. Do not include private diagnostic logs or local test tax output in artifacts. Preserve source-level COMPLETE/PARTIAL checks and relative Excel links when staging/publishing to Known Folder Downloads.

Schema identitas build dimiliki `spt_desktop.build_info.is_valid_build_info`
dan dipakai bersama oleh producer/validator CI serta reader runtime. Tetap
gunakan tepat empat field, schema integer 1, commit heksadesimal kecil 40
digit, run ID positif 1–24 digit ASCII, dan run attempt integer 1–1.000.000;
boolean dan field tambahan tidak valid. Runtime tetap mengembalikan `None`
dan diagnostik unknown untuk metadata tidak sah; CI melempar `ValueError`
sebelum menulis metadata. Pertahankan pemeriksaan file dan pembacaan terbatas;
modul bersama ini hanya boleh bergantung pada standard library.
