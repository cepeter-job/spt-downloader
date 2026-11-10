# Financial PDF live discovery: evidence and bounded repair proposal

Date: 2026-11-10

Status: **Implemented and merged through #231 under separate operator merge approval; this design PR remains open and unmerged.** The historical investigation below was source/artifact-only plus authorized value-free operator-browser probes and same-origin public JavaScript GETs; no PDF action or replay was used during diagnosis. Current hosted implementation verification is recorded in section 8. The requested AGENTS.md contract update remains blocked pending protected-file approval. Real operator PDF completion remains unproved.

## Outcome

The saved attempt refused **discovery before any PDF request capture**, not authentication, response transport, PDF signature validation or publication. The exact terminal predicate is `if not controls` in `coretax_attachments.py:325-328`.

The authorized selected-return live probe confirms the incompatibility with the scanner's legacy shape: all three visible `ui-grid-documents` tables have the extra filename-filter header, and their enabled download buttons have `aria-label="Unduh"` without HTML `title`. Exactly one table has the existing approved financial-caption association; the other two do not. Thus the first live predicate rejects all tables before the later action-caption predicate can run. Saved diagnostics retain no historical DOM snapshot; this is a new corroborating observation on the same selected return and unchanged reviewed frontend, not a reconstructed historical snapshot.

## 1. Evidence and version boundary

Investigation baseline is repository commit `536fa0cb69657026725a7f82f60d57fdbc951467`. The diagnostic build matches the supplied failed-attempt build, and its diagnostic job reference matches the supplied job using the existing namespaced hash rule. The implicated attachment/POST, DOM collector, corporate caller and reviewed pin data have no diff between that build and this baseline. Private artifact identifiers and paths are intentionally omitted here.

Reviewed safe aggregates:

| Saved evidence | Result |
| --- | --- |
| Records | 1 |
| `pdf.discovery` events | 1 |
| `pdf.partial` events | 1 |
| `pdf.request_captured` / `pdf.request_rejected` events | 0 / 0 |
| Discovery `attachment_tables` / `candidate_controls` | 0 / 0 |
| Discovery `control_kind` / `binding_state` | `none` / `no_control` |
| Discovery `href_present` / `handler_present` | false / false |
| Record attachment declarations | 1, `PARTIAL` |
| Attachment reason classification | exact match to the source's no-supported-control branch |
| Attachment byte count | 0 |
| Attachment label/path/hash | all empty |
| Published-output attachment declarations | 0 |
| Overall complete flag | false |

The checkpoint's `attachments` field, not an invented `financial_pdfs` field, carries this result. The `pdf.partial` row has no sanitized error object, consistent with the explicit early return rather than the per-control exception handler at `coretax_attachments.py:405-408`.

The saved Induk section additionally has **three complete, one-page, one-body-row tables**, each with three saved columns exactly matching the scanner's approved attachment header tuple. These are captured table summaries, not retained DOM. `coretax_browser.py:123-137` excludes input/filter header rows before flattening headers; the PDF scanner does not. Thus three captured attachment-shaped tables and zero scanner-recognized tables are consistent with the modern filter-row incompatibility. They do not prove which of those tables was the financial statement, their live header count, or their visibility at the later scan. No private table labels, filenames, cells or record values were printed or copied.

## 2. First refusal and limits of what it means

### Actual ordering

1. `coretax_browser.py:875-939` captures the visible owned Induk, including accordion expansion, then invokes the PDF collector before moving to another form. The separate native caller is `coretax_corporate.py:1000-1015`; this attempt used DOM fallback, so do not conflate the two caller readiness paths.
2. `coretax_attachments.py:295-308` checks Stop, selected page/record and ordinary output directories before scanning.
3. `_SCAN` requires a unique `.main-content` (`:34-35`). The observed zero-table sentinel is created only at `:139-141`, so the final logged scan did not take the nonunique-root early return.
4. `attachmentTable` requires **exactly one** `tHead` row and exact three captions (`:45-49`); only visible matching tables enter `tables` (`:79`). General ordinary-link discovery is separately restricted (`:95-107`).
5. The collector rescans within its existing ten-second window only while there are no controls and no recognized attachment tables (`:310-322`). It logs the **final** observations, not each interim sample or all DOM tables (`:323-324`).
6. After filtering controls by the fixed financial-caption allowlist, `if not controls` records `pdf.partial` and returns the empty-label PARTIAL declaration (`:325-328`). **This is the proven first refusal that terminates PDF collection.**
7. Only after that branch would it verify POST sources, enter `FinancialPost`, capture/abort the application request and replay once (`:336-350`).

### Interpretation

- `attachment_tables=0` means **zero visible tables accepted by this exact scanner predicate**, not zero tables in Induk. `candidate_controls=0` is a sentinel, not a document-wide count of buttons or links.
- It is not the observed present-but-`unbound` case: no accepted table reached label binding or action enumeration. An unrecognized table can still contain a real download action.
- `handler_present=false` here says nothing about an Angular listener: the sentinel has no element, and the scanner only checks three inline handler attributes.
- Loaded-source verification (`coretax_financial_post.py:79-100`), owned-context and detail-route checks, final body/authentication checks (`:193-226`), route/request guards (`:228-269`), response MIME/redirect/size (`coretax_attachments.py:145-171`), signature/trailer (`:259-260`), file custody and publication were not reached for a supported PDF control. They remain **untested by this attempt**, not certified healthy or implicated as its cause.
- Increasing the Authorization budget again, refreshing pins without measured drift, extending waits, changing TLS, accepting metadata as a PDF, or modifying publication cannot repair this proven early exit.
- The corporate L3 fallback and later table elapsed-budget problem are independent blockers; clearing discovery alone cannot make this run COMPLETE.

## 3. Public-source proof

The retained public corporate and MAIN JavaScript bytes independently hash-match the entries in `resources/build-pins.json:2,6`. `_PDF_PIN_PATHS` already selects those exact providers (`coretax_attachments.py:23-31`); `load_build_pins` validates reviewed data (`coretax_build_pins.py:16-37`). This is static provenance, **not evidence that the failed page passed `verify_sources`**, which was never reached. Historical bundle names in `docs/pdf-keuangan-post.md:11-23` are not the current pin authority.

Reproducible anchors below are zero-based decoded-character offsets in those hash-matched public files; no private frontend state was inspected:

| Provider / anchor | Proven consumer behavior |
| --- | --- |
| Corporate `525.32c49782948fc5ef.js`, `PN`, about 2761390-2762000 | `ui-grid-documents` receives `FinancialStatement`; its `buttonDownloadClick` calls `onDownloadDocuments`. Neighboring consumers receive other attachment collections and must not inherit financial permission. |
| Corporate, about 2937700-2938400 | Financial grid rendering depends on `FinancialStatement.length > 0`. Therefore genuine missing data and DOM/visibility/shape mismatch remain distinguishable possibilities. |
| Corporate, `onDownloadDocuments`, 2819324 | Builds the existing two-field document/taxpayer request from the selected row and current taxpayer, then calls the document download service. No generation permission follows. |
| MAIN `main.bed1449c3647a8ca.js`, document-grid class, 4102199-4105600 | Three ordinary columns; filename field; download action with fixed name, caption, icon and secondary class. `ui-grid-documents` renders `nui-grid`, with paginator/export disabled, and relays only the named download event. |
| MAIN, filter-kind helper `He`, 3070170 | Row/action columns have no filter; ordinary filename column defaults to text filtering. The column helper `P`, 3047866, does not disable that filter. |
| MAIN, `nui-grid` constructor about 3133000 and `filterRowVisible`, 3157353 | `showFilterRow` defaults true and a filter row is visible when any body column has a filter. The reviewed filename column satisfies this source condition. |
| MAIN, `Ri`/`oi`/`Ia`/`pi`, 3116800-3118300 | A separate `tr.ng-filterrow` has one header cell per body column; the filename cell owns `nui-grid-filter-control`. This extra row is incompatible with the scanner's literal one-row predicate. |
| MAIN, `aa`/`Pa`, 3118500-3119350 | Action is a real `button[type=button].ng-actbtn`, receives the source class/icon, tooltip and `aria-label` from action Title; this template does not set HTML `title`. The scanner's `title === Unduh` at `coretax_attachments.py:121-126` is a second incompatibility, downstream of table recognition. |
| MAIN, download service, 577520 | Existing-document download remains POST with blob response; no new endpoint or method is needed. |

The current operator probe freshly fetched all three loaded providers; their JavaScript types, plausible byte sizes and SHA-256 digests match the reviewed corporate/MAIN/vendor pins. The modern branch below is corroborated by current structure. Do not describe the later action-caption mismatch as the historical first observed failure: a button-only mismatch on an otherwise accepted table would still emit an attachment-table observation. The operator probe is not application-owned native/PDF authorization or live acceptance of a future build.

## 4. Minimal source/live-proven repair proposal

Keep the legacy ordinary-link and legacy flat-table POST branches. Add **one explicitly reviewed modern document-grid branch inside the existing scanner**, not a general tolerance for extra headers or a document-wide download-button search.

1. Require the existing selected corporate Induk precondition and financial label binding. For the modern branch additionally bind the exact ancestry: original visible main form, owning `ui-grid-documents`, its sole `nui-grid`, sole `p-table` and actual table. Reject competing/nested owners and ambiguity. Do not identify the financial collection by table ordinal, a filename, the download icon alone or OtherDocuments content.
2. Recognize only a flat, unspanned three-caption header plus the **exact source/live-proven filename-filter row**. Both rows have exactly three cells with colSpan/rowSpan one. The second row is `tr.ng-filterrow`, has no caption text, and has `nui-grid-filter-control` host counts `[0,1,0]`, with its one text input in the filename cell. Reject unexplained header rows/cells/controls. Read no filter values; never clear filters, click search/filter controls or use them as download candidates. Keep table-derived ordinary GET discovery restricted to its legacy single-header branch; reusing a widened label helper must not admit anchors through a newly recognized modern table. Existing direct approved ordinary links remain unchanged.
3. Couple action admission to the inspected layout branch. The modern action is `button[type=button].ng-actbtn.p-button-secondary`, has exactly one `i.pi.pi-download`, literal `aria-label="Unduh"` and **no HTML title attribute**. Keep the separate legacy exact-title branch. Contradictory caption metadata and unreviewed legacy/modern hybrids refuse; do not use an unconditional `title OR aria-label` shortcut. Preserve enabled state, unique body-row action, three unspanned cells, literal row-number shape, PDF extension and inline-handler exclusions.
4. Produce the **same control descriptor** and keep the WeakMap actual-node identity and original row/filename/document snapshot. `FinancialPost.check` and the immediate pre-click scanner must independently revalidate the new shape (`coretax_financial_post.py:171-191,277-306`); cloned/replaced buttons or owners must not acquire permission through a fresh broad search.
5. Make no changes to POST body/route/authentication/replay, source pin values or request count. Keep the existing ten-second lazy-discovery policy and definitive present-but-unbound refusals. An absent/empty/unknown financial grid remains PARTIAL; do not synthesize a request from saved JSON document metadata.

Unknown single-header modern hybrids, missing/hidden grids, conflicting ownership and unsupported financial-caption bindings remain refused; do not reinterpret them as this proven branch. Any new diagnostic event/enum/counter must be registered and privacy-tested; no raw DOM, headers, body, URLs, filenames or labels.

## 5. Completed authorized value-free probe

The parent reopened the existing operator profile and confirmed the retained manual login works. Only inspected read-only L3/Induk navigation was clicked. Public source providers were enumerated from loaded resources and re-fetched for type/size/hash verification. No Angular state, credential/storage value, native business input, checked state or financial table body/footer tax value was read. For the PDF-specific existing-document shape, only row-number syntax and filename-PDF-suffix booleans were returned; no filename or row text left the probe.

The final read-only evaluation checks the private selected literal detail URL and original Document before/after without returning either. It inspects all visible document-grid candidates within the single visible original main form, including tables rejected by the old header predicate. It returns counts, booleans and local candidate ordinals only. Candidate ordinals below report observations and are not selectors or authorization.

Observed:

- Unique `.main-content`, unique visible `rshshr-citr-main-form`, unique Induk tab, visible original panel and literal tab-controls/panel-ID match: all true.
- Three visible document grids, each containing one `nui-grid`, one `p-table` and one actual table with matching closest owners.
- Each table: two unspanned three-cell header rows, the exact approved first caption tuple, second `ng-filterrow` with blank caption text and filename-only filter-host/input counts `[0,1,0]`. The old single-header predicate is false for all three.
- Financial-caption association, tested independently of the old header precondition: true for exactly one candidate, false for the other two.
- Each table has one visible flat three-cell body row and one enabled sole action; row-number syntax and PDF filename suffix are true without returning their text.
- Every action has the exact modern class, secondary class, one download icon, literal approved aria-label and absent title; no href or inline pointer/mouse/click handler.

This distinguishes the **first failing table predicate** from the later button predicate and proves the existing financial-label scope still excludes the neighboring attachments. It is still a new observation, not a historical DOM snapshot. Final live acceptance requires a subsequently approved build/run; no PDF network/authentication health claim follows from discovery structure.

## 6. Safety invariants and required verification

Do not change:

- Selected taxpayer/record, literal read-only route/document URL, visible owned Induk and financial-caption scope.
- Service-Worker-blocked owned context, loaded provider/node/source identity, exact source hashes, node replacement checks and immediate pre-action reconciliation.
- Exact same-origin POST route, method/frame/resource kind, two-field body, final taxpayer and `Request_From`, captured original authentication and its finite budget.
- Capture-and-abort before one bounded authenticated replay; no retries, guessed document IDs, generation, email, new attachment collections or alternate endpoints.
- TLS verification, redirect refusal, PDF MIME, 20 MiB stream/host bounds, signature/trailer/hash, Stop and cleanup.
- Ordinary directories, same-byte reuse, record/scope declarations, manifest/held-byte custody, relative links, consent and publication. See `coretax_exporter.py:120-183`, `coretax_pdf.py` and existing desktop publication contracts. Metadata alone is never COMPLETE.

### Runner-only test plan after approval

1. Add a synthetic modern document-grid fixture matching the confirmed header/filter and action subtree. Initially assert the current scanner fails discovery; then assert the repaired scanner recognizes only the bound financial row. Exercise both mismatches separately so header rejection cannot mask missing-title handling.
2. Positive end-to-end modern case: real event listener, matching synthetic loaded pins, inspected owned Induk, exactly one application click, aborted original POST, exactly one authenticated replay, verified PDF metadata and bytes. Include neighboring nonfinancial document grids and ensure no action there.
3. Negative header/owner cases: wrong/reordered/duplicate caption, extra/malformed filter row, filter outside filename cell, spans, hidden or nested/duplicate grid/table, unknown controls, absent/ambiguous/contradictory label binding. Assert zero clicks and zero backend requests.
4. Negative action cases: contradictory title/aria metadata, missing modern action class, extra icon/action, disabled/hidden/inline-handler control, foreign row, changed filename/document, cloned/replaced node or grid between scan, pre-click and persistence. Assert existing fail-closed outcomes.
5. Preserve tests in `test_financial_discovery.py`, `test_financial_discovery_diagnostics.py`, `test_financial_post.py`, `test_financial_actual_route.py`, `test_financial_authorization_budget.py`, `test_financial_rejection_cause.py` and `test_financial_attachments.py`. Update `support_financial_post.py:56-63`, which currently models only one header row and HTML title, with an additive modern fixture rather than replacing all legacy coverage.
6. Retain delayed-render, unchanged poll deadline, present-but-unbound no-poll behavior and Stop regressions. If diagnostics change, assert fixed schema and secret-sentinel exclusion. Keep actionability/transport/auth/source/redirect/oversize/signature failures separate from discovery.
7. Run financial capture/export/publication/flat-layout suites and the normal full Windows CI/build gates. Include PARTIAL-with-no-file/link, undeclared-file exclusion, byte mutation, scope/identity, relative links and cancellation rollback regressions.
8. Exact-build authorized live acceptance must show successful discovery, captured/replayed request and declared COMPLETE PDF with verified bytes/custody. Neither a request-captured event nor this design proves download/publication or whole-run completion. Other form/table failures retain their own PARTIAL status.

## 7. Verification performed and outstanding blocker

Historical diagnosis performed: read-only sanitized saved-data/log analysis; job/build association; repository lineage/diff and source/test inspection; independent public-source hashes; authorized read-only live structure and public-JavaScript GET probes. At that diagnosis stage no pytest, product imports, source/frozen tests, Tk/browser fixtures, builds, EXE runs, PDF action, document request/replay or publication was performed. Later hosted RED/GREEN and build evidence is recorded separately below.

The historical implementation gates were subsequently completed by #231; see section 8. This documentation PR still requires its own merge authorization, and the AGENTS.md edit requires protected-file approval. Actual portal PDF transport/authentication/signature/custody and whole-run completion remain to be exercised by an application-owned exact-build live run.

## 8. Implemented state and remaining documentation gate

- Implementation #231 was merged as `e5e0e988f1908d08c8a730d5a27e17665772b681`. Its reviewed standalone head `7acdd23e57f29e294dba1c8cb7a4e367098e2083` passed full Build `42800288738` with all 107 new financial cases: 81 discovery, 11 synthetic transport/snapshot, 10 local-label scope, four missing/hidden-caption scope cases and one extra-icon case.
- The final modern branch preserves transparent field-wrapper association while refusing borrowed headings from adjacent empty fields, including explicit-ID variants. Modern admission rejects an extra non-pi icon and ambiguous financial groups without rejecting multiple PDF rows within one uniquely bound group. Legacy and modern action/header branches remain coupled; no transport or OtherDocuments permission was added.
- After #229 merged, combined head `70d2528113eb71e203a73aadbe01a6959c5bb204` passed Build `42809281591`. Four downloaded Windows JUnit artifacts independently confirmed all 194 new L3/PDF cases passed, no new skips/failures/errors and no older Windows failures/errors. CodeQL, all four shards, coverage, packaging, exact-ID readback and uploaded-EXE bootstrap/reuse/cancellation passed before #231 merge.
- Official main Build `42813223671` then passed, including artifact provenance, exact seven-file readback and packaged bootstrap. Its tree equals the verified combined head. These checks prove synthetic/build behavior and artifact identity, not a real portal download or whole-run COMPLETE result.
- The operator subsequently requested the deferred AGENTS.md contracts. One normal protected-file edit was attempted; its approval prompt timed out and no contract text was applied. No alternate write path or retry was used. This status record is not a substitute for that blocked edit.
- This design PR remains unmerged pending separate approval. Operator-owned build-matched native/PDF acceptance, declared COMPLETE PDF bytes/custody, mapping and whole-run completion remain independent gates.
