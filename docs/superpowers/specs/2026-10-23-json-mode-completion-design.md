# JSON mode completion: coverage, projection, and acceptance

Date: 2026-10-23. Status: approved by the user on 2026-10-23 for autonomous inline planning and implementation; runner/live evidence is recorded separately.

Presentation addendum: the user later requested consolidation of the latest Excel-formatting PR. Merged PR #90 supplies the approved clean Induk/L8 layouts, compact corporate body ranges and zero-decimal accounting display while retaining exact stored values. These newer approved presentation rules supersede the earlier generic-Induk restriction. The JSON branch preserves them; native eligibility, raw source custody, truthful mapping counts and PDF completion remain independent. Consolidated verification is recorded in the L7 implementation report.

Consolidation addendum: the user also explicitly included PR #89's submitted inventory readiness and page sizing. Preserve that reviewed implementation and its tests alongside the JSON changes, without adding status scans or weakening preliminary response ownership, Stop, literal metadata or restoration checks. The final combined-tree evidence is recorded separately from either prerequisite's earlier run.

## Intent and baseline

The user requested the remaining JSON scraping work from the latest codebase, then instructed us to do it. Deliver the identified improvements through the existing JSON-first architecture, preserve approved workbook layouts and source evidence, and distinguish implemented behavior, runner verification, and live acceptance.

Baseline: `413c440b725baafece976fcad2914c1d2a4eb826` on `main`, merged through PR #82. Use the attached isolated worktree and branch `feat/json-mode-completion`. Preserve the primary checkout and all private captures, profiles, and outputs.

The accepted backlog has seven workstreams: corporate form coverage; corporate semantic projection; PPN Normal and remaining AskedTo lifecycle branches; native observer readiness; dated reference versions; current-build acceptance and throughput measurement; and documentation reconciliation. Implement these as independently reviewable slices. A source or runtime gate is not satisfied by finishing another slice.

Current capabilities already include PPN native export (PR #30), five-form/seven-grid PPh21 (PR #37), four-form/five-grid Unifikasi (PR #40), and desktop JSON-first defaults with source/timing diagnostics (PR #41). The successful historical live PPN acceptance covers one approved amendment. These capabilities are regression baselines, not unfinished implementation tasks.

## Approach and alternatives

| Approach | Benefit | Cost / decision |
| --- | --- | --- |
| Extend each existing family observer/projector, sharing only proven readiness and transport primitives | Preserves family-specific lifecycle rules and existing synthetic contracts | Selected. New corporate semantic code follows the existing Masa/PPh21 split. |
| Build one declarative projector for every tax family | Centralizes field declarations | Requires a cross-family schema and migration of working adapters; introduces unrelated risk. |
| Complete corporate coverage while retaining the existing generic leaf-table output | Smaller initial implementation | Useful as an intermediate test slice, but does not meet approved template mapping acceptance. |

Keep the public CLI/desktop mode contract unchanged. JSON-first remains a per-record choice: native sections only when the entire attempt is eligible; otherwise a whole-record DOM fallback for safe unsupported coverage. Authentication, privacy, identity, changed-source and Stop failures retain their existing fatal/cancellation behavior.

## Invariants

- Source business values originate in custody-checked response bytes. DOM supplies navigation, visibility, labels, column geometry, component/group ownership and other inspected structure only.
- Preserve literal identities, period/year/model strings, leading zeroes, source types, duplicate rows, order and original captures. Do not merge amendment workbooks or infer missing aliases.
- Preserve selected submitted-list scope and exact request/response identity bindings. No archived-list scans, new guessed endpoints, broad POST permissions or authentication extraction.
- Native eligibility, capture completion, inventory completion, workbook mapping and final run completion remain distinct. A missing mapping is never converted into a fabricated zero or hidden COMPLETE.
- Keep approved resources, numeric precision rules, footer ownership, financial PDF custody and publication semantics. L10-B/L10-D remain in capture/proof namespaces and are excluded only from new corporate workbook presentation.
- All product imports, pytest, Edge/Tk/native fixtures, self-tests, builds and EXE execution occur on GitHub runners. Local work is source editing, text/AST inspection, Git, and artifact hash/metadata inspection.
- No CI, dependency, LICENSE, installed package, stored preference or credential changes are needed by this design.

## 1. Corporate source and form coverage

The current `coretax_corporate.FORMS` has eleven entries. It omits L1-D, L3, L7, L11-A and L11-C, which are represented in the approved corporate template. Add a form only after tracing its actual read-only consumer, visible component, data ownership, paginated grids and final assignments.

Static source evidence: an existing local copy of public `525.ec1edffbb4a91d20.js` contains 3,326,578 bytes and SHA-256 `fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d`, matching the current production pin. It was read as text, without executing the bundle or opening a taxpayer session. Offsets below are UTF-16 character indexes from .NET string inspection. The bundle stays outside version control.

| Form | Verified component | Parent CurrentFormData root / dependency | Parent assignment offset |
| --- | --- | --- | ---: |
| L1-D | `rshshr-citr-l1d-form` | `L1dFormData`; child also declares `financialData`, `isMigrated`, and `isRupiah` inputs | 2645386 |
| L3 | `rshshr-citr-l3-form` | `ListIncomeTaxWithheldByOtherParties` | 2645829 |
| L7 | `rshshr-citr-l7-form` | `CalculationOfFiscalLossCompensation` | 2646078 |
| L11-A | `rshshr-citr-l11a-form` | `{current: formData.L11AFormData, previous: previousFormData.L11AFormData}` | 2646559 |
| L11-C | `rshshr-citr-l11c-form` | `L11CFormData` | 2646706 |

These are root/ownership facts, not proof that raw root values equal the final displayed controls. L11-A previous-source dependencies and L1-D financial/migration branches must have explicit response custody and source paths. An unavailable dependency keeps that branch unsupported; never substitute current data, zeroes, claims or DOM business values.

Maintain a source ledger per form: source asset/hash/offset; component and visible group; primary/auxiliary request consumer; source container/path; later assignments and formatting; output field/table/footer destination; and required coverage evidence. A grid declares only inspected routes, literal group keys, request bodies and source offsets. Embedded form arrays are not assigned invented grid endpoints.

Observation verifies every enabled observed form, including empty groups. Pagination must reset to a proved first page, cover contiguous offsets, reconcile totals, retain duplicate business rows, and reject changed snapshots. Unknown enabled forms still require whole-record fallback. Disabled tabs do not become fabricated empty forms.

## 2. Corporate semantic projection and template mapping

Add a focused corporate semantic projection layer alongside the current adapter, following the existing PPh21/Masa separation. `coretax_json` retains byte decoding, identity, privacy, packet validation and source coverage responsibilities. `coretax_corporate` retains value-free UI bindings. Keep the current evidence-leaf projection available for compatibility with old canonical captures; a leaf table is not proof of approved template mapping.

The semantic layer emits the existing canonical sections, fields and tables used by `coretax_badan_template`. It must provide:

- Exact observed field labels/groups and response-backed values.
- Exact visible multi-level table headers, ordered body rows, explicit body/source counts and page coverage.
- `source_structure` form/component/group ownership for repeated headers, including the existing L1-D/L9 contracts.
- Reported footer values and physical `footer_spans`; do not calculate replacements from body sums.
- Per-value provenance with response sequence, container/path, source type/literal value, destination and any verified rendering rule. Derived display results preserve all contributing source paths.
- Explicit unsupported/unresolved accounting for captured values that have no approved destination. Preserve the full checkpoint even where approved presentation omits raw display blocks.

Preserve the approved twelve-sheet corporate resource and its per-form style, merge, dimension and page-layout contracts. Do not fabricate an Induk template. Use existing strict id-ID/15-digit monetary and percentage writers; retain identifiers, job titles, dates and headings as text. Preserve the exact L1-D negative subtraction rule, all L3 footer rows, final L1-D total, L7 dynamic year/header rules, and L11-B DER operands/merges.

The 58 unresolved scalar fields mentioned in PR #82 are a scope-specific audit observation. Do not hard-code this number, invent destinations, mark all of them solved by native capture, or add fake unmapped counts. The final mapping report must reconcile its actual input capture.

New worker modules enter only the explicit `WORKER_FILES` allowlist. Do not recursively include source folders or private evidence. Old offline captures remain readable without upgrading their source provenance or silently claiming native coverage.

## 3. PPN Normal and AskedTo lifecycle

`project_ppn_asked_to` currently supports verified amendment short-circuits and rejects Normal and unresolved calendar-dependent carry-forward cases. Preserve the existing amendment results and nonnegative-balance clearing behavior.

Trace the pinned PPN final parent/child lifecycle before implementing each extension: initial prefill mapping, calculation, footer callbacks, nested model guards, bookkeeping/calendar conditions and later control assignments. Document the actual final source rule for Normal and each overpayment/compensation branch. Do not reuse amendment balance paths for Normal by analogy.

A new branch needs response-backed monetary/bookkeeping inputs and the exact environment evidence used by its reviewed consumer. When the final choice depends on time, bind a browser clock interval to the owned capture attempt. Admit the native result only if every possible time within that interval selects the same branch. Otherwise preserve explicit fallback. Do not guess the user's current tax year, replace an unavailable choice with compensation, or read DOM checked-state as JSON evidence.

Test Normal/amendment, nonnegative/negative/zero balances, all literal choices, null/stale choices, export-present/export-absent paths and relevant calendar/bookkeeping boundaries. Assert per-value provenance and saved-workbook values, not only the helper return.

## 4. Native observer readiness and pagination

Reuse the current `coretax_browser._wait_tab_panel` behavior through a small shared internal helper when its identity contract fits. A native observer retains its stricter form/component/header checks after readiness.

For every visited tab: inspect the intended caption and owning view; click once; wait within one existing deadline while rereading the current `aria-controls`; refuse a missing binding after one has been seen; require one actually visible owned panel for an initially unbound tab; and verify caption, owner and final binding together before observing structure. Cancellation checks remain inside the wait. A reordered tab cannot relabel another form.

The native grid walker must use the same inspected-control ownership/actionability rules as the generic read-only paginator where applicable. Preserve first-page proof, disabled/hidden control refusal, no-advance and repeated-page handling, source totals, page limits and cancellation. Pointer interception is not authority to click arbitrary controls.

Add native-family browser regressions for changing/missing bindings, reordered tabs, nested/foreign/duplicate panels, CSS/ancestor-hidden panels, delayed readiness, cancellation and intercepted paginator controls. Existing getter traps must continue to prove that native observation never reads business values.

## 5. Reference catalog versions

Keep exact family, locale, requested-type, no-body GET, response custody and code-equality rules. Preserve unique-code requirements for dropdown consumers whose reviewed implementation differs from grid active-version selection. Do not turn a generic clock into permission to select ambiguous model/PERIOD options.

For the reviewed clock-dependent grid selector only, record browser epoch milliseconds at capture start before View/reference requests and after final response drain. Preserve that interval with the same owned attempt in provenance/checkpoint metadata. Match the pinned consumer's date parsing, ordering and validity comparisons. A version is eligible only when selection is identical throughout the interval; boundary crossings, invalid dates, missing required validity fields or unstable selection remain unsupported. No workstation clock, latest-version heuristic or selected DOM label may resolve it.

New metadata is optional for old captures and required only by the new branches. Validators must reject malformed types, reversed/non-finite intervals, unrelated sequences or mismatched attempts. Replaying a checkpoint uses its recorded evidence, not the replay machine's current time. Original response bytes remain unchanged.

## 6. Runner verification and review

Each behavior slice follows source ledger -> reviewed synthetic tests -> observed GitHub RED -> minimal implementation -> GitHub GREEN -> source review -> exact artifact verification. Keep failing evidence and recovery commits. Never weaken old identity/privacy/source assertions to obtain GREEN.

Required synthetic acceptance classes:

1. Full native attempt -> canonical sections -> approved saved/reopened workbook -> truthful mapping report.
2. Missing/extra forms, missing pages, explicit empty groups, repeated snapshots, changed totals and duplicate rows.
3. Normal and literal numbered amendments kept in separate workbooks with correct relative links.
4. Current/previous dependency swaps, cross-record/cross-tax contamination, changed build/source, authorization/privacy failures and Stop remain rejected.
5. Native getter traps, DOM fallback audit, checkpoint replay, isolated worker import and original-capture immutability.
6. Numeric money/percent precision, literal identifiers/dates, zero/negative/unsafe values, template styles/merges/layout and reported footer custody.
7. Corporate PDF COMPLETE/PARTIAL and publication continue to follow the reviewed existing-document GET/POST contract.

Run the existing complete Windows suite, portable subset, audits/security analysis, source/frozen self-tests, package and bootstrap verification without changing user-owned CI. Read back distribution and diagnostic artifacts by exact run/attempt/artifact ID. Verify archive/member hashes, build identity, worker allowlist and embedded source against the exact tested head/merge tree. Report suite counts separately where they overlap.

## 7. Current-build acceptance and performance

After a verified candidate exists, select an authorized live scope using existing operator-approved records; credentials and taxpayer values stay private. This design does not select an arbitrary taxpayer/year or expand historical permission. If no exact live scope is available, leave live acceptance open and deliver the synthetic evidence separately.

For observed available returns, record actual requested/used source, full native coverage, capture/inventory/run completion, mapping results, literal model/period, workbook/source comparisons, relative links, PDF custody and owned-process cleanup. Cover corporate additions, five PPh21 forms/seven grids, four Unifikasi forms/five grids, PPN Normal and the supported amendment branches. A DOM fallback may be a valid export but does not close native acceptance.

Use separate output folders and preserve earlier files. A historical accepted PPN amendment does not certify every PPN branch or the latest consolidated build. Keep scope-specific results; do not claim types or forms that were absent.

For throughput, use the same candidate build, selected source records, mode-specific fresh jobs, PDF options and verified completion status. Separate login/selection and checkpoint reuse. Alternate DOM/JSON order across repeated paired runs; report individual times, actual fallback counts and median differences. Existing nested timers are inclusive and must not be added twice. A PARTIAL/timeout run is not a normal-throughput measurement.

## 8. Documentation and delivery

Reconcile `docs/pph21-json-native.md`, `docs/unifikasi-json-native.md`, the Unifikasi spec, `docs/ppn-native-integration.md`, and the pagination/default plan with merged implementation evidence. Preserve historical RED/PARTIAL results and mark superseded statements clearly. Update architecture/code-map/manual-acceptance ownership pages when their actual contracts change.

Deliver focused PRs with final behavior, exact source coordinates, runner/artifact evidence, source ledger and remaining unsupported/live cases. Automatic review comments require technical disposition against the actual code and evidence. Merge, distribution replacement and live operations must follow the authority established for the concrete result; do not present a proposed design as finished implementation.

## Completion criteria

A workstream is complete only when its supported branches have source proof, passing exact-tree runner contracts and an independently reviewable result. The overall backlog is complete only when the coverage matrix, mapping audit, documentation, artifact verification, authorized live acceptance and paired performance evidence have each reached their own stated result. Unavailable permissions/evidence remain explicit open work; no fabricated source values or success claims can substitute for them.

## Review performed for this design

Checked against current dispatch, corporate form catalog and generic leaf projection, template ownership/format/DER contracts, PPN choice guard, native panel waits and strict PPh21 projection metadata keys. Recomputed the public corporate bundle digest and traced the five missing parent form roots. This is static evidence only; no tests, product imports, browser fixtures, builds or live capture were run.
