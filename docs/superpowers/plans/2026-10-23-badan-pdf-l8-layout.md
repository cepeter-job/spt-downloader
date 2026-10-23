# Corporate PDF, L8 and audit repair implementation plan

> **For agentic workers:** use superpowers:executing-plans in this session, with one fresh whole-branch review before merge. The operator has authorized the audited fixes, PR, latest-main review, merge after CI and verified Downloads delivery.

**Goal:** Download an existing financial PDF from the observed read-only corporate route, retain owned L8 merged rows, and match the approved manual presentation and Audit headings.

**Architecture:** Keep the existing single captured/aborted POST plus one bounded replay. Admit only the observed literal `view=true` query in addition to the existing bare route. DOM extraction records L8 body-cell spans atomically with raw cells and exact component/group ownership; the renderer consumes only that proof and retains legacy ambiguity as unresolved. Presentation changes remain in the corporate renderer and resume exporter.

**Tech stack:** Existing Python, Playwright/Edge and openpyxl worker; no new dependencies, GUI imports or CI changes.

**Spec:** The operator-approved audit scope: PDF failure before `_read_pdf`; owned L8 headings with `colspan=2`; Induk two-row separator, typed money/accounting zero decimals, borders/title/width/tariff caption; L6/L8 borders; explicit mapping headers in Audit.

## Global constraints

- Product imports, pytest, Edge/Tk fixtures, self-tests, builds and EXE execution run only on GitHub runners. Local work inspects source/AST and private artifact bytes/metadata.
- Synthetic fixtures only in Git. Keep taxpayer captures, workbooks, identifiers, headers, request bodies and credentials out of commits and diagnostics.
- Preserve selected taxpayer/record, submitted route, current document, source pins, Service Worker policy, Stop, one request/replay, PDF byte custody and truthful PARTIAL.
- Base `0bb765c877d68d362a323bbf09ac5cbf7b6730b1` includes preceding PR94's shared Masa percentage and build-identity validators. Keep the separate corporate number/percentage contracts intact.
- Preserve raw cells and duplicate rows. No padding a legacy two-cell row, copying reference taxpayer values, calculating absent tax values or inventing a PDF.

## Review focus

- Read-only URL aliases, duplicate/extra query keys, history routes and scope changes must not authorize a request.
- Span metadata must match the same owned table/rows, reject invalid width/rowspan and retain unsupported raw evidence.
- Induk identifiers and tariff choices stay text; malformed or unsafe-precision money stays literal and unresolved.
- Header insertion must preserve PDF relative links and mapping counts, including DER zero-capital limitations.
- Previous-session changes, cancellation and exact packaged worker resources must survive the merged artifact.

## Task 1 — Regression evidence, then bounded PDF admission

- [ ] Add actual-route `?view=true` positive/one-replay tests; reject duplicate, extra, encoded, false/history query variants and changed documents.
- [ ] Add a real guard-failure diagnostic regression proving useful module frames without messages, identifiers, body or authentication data.
- [ ] Observe expected failures on GitHub before product edits, together with Tasks 2/3 tests.
- [ ] Admit only the exact inspected query on the actual submitted corporate route and retain full document equality/Request_From. Add only reviewed financial-module/function names to diagnostic frame allowlists.

## Task 2 — Owned L8 structural capture and mapping

- [ ] Add synthetic DOM fixture matching the inspected `rshshr-citr-l8-form` / `rsh-citr-l8-form-grid1` owner: eight body rows, heading spans `[1,2]` at source rows 1/3/6, normal spans `[1,1,1]`, one three-cell footer.
- [ ] Verify capture retains raw cells and records body colspan/rowspan metadata from the same evaluation; verify public export yields nine source rows with heading merges and exact safe numeric/footer values.
- [ ] Cover missing/foreign ownership, missing/contradictory spans, bad rowspan/width/count, incomplete/multipage proof, unsafe amounts, duplicate owner and legacy complete three-cell tables.
- [ ] Record only owned L8 metadata in `coretax_browser.py`; bind supported spans in `coretax_badan_template.py`, preserving rejected captures and accurate unresolved counts.

## Task 3 — Approved presentation and Audit headers

- [ ] Add saved public-export assertions for Induk two-row separator, 13 verified monetary slots, zero-decimal accounting, exact identifier/choice text, title, borders and widths; check malformed/unsafe values remain unresolved.
- [ ] Add L6/L8 border assertions without altering other template styles or checkpoint values.
- [ ] Add resume assertions for a separate mapping header: `Status / Objek / Field belum dipetakan / Tabel belum dipetakan / Baris belum dipetakan / Hasil / Keterangan`, preserving existing mapping-row markers, inventory and PDF headers/links.
- [ ] Implement the narrowly scoped renderer/exporter changes; update obsolete presentation expectations without weakening data/privacy oracles.

## Task 4 — Review, runner validation, merge and delivery

- [ ] Run unchanged full runner CI and inspect every failure. Verify source/frozen GUI, exact uploaded distribution, cold bootstrap/reuse/cancellation, audits and code analysis.
- [ ] Obtain fresh whole-branch review; review preceding other-session merged PRs and refresh latest main immediately before merge. Resolve findings and integrate/retest if main changes.
- [ ] Verify exact PR merge tree/run/artifact/bootstrap metadata, merge with expected head, then verify actual-main CI/provenance and immutable distribution readback.
- [ ] Copy the verified actual-main ZIP non-overwriting to both authorized Downloads folders, check size/hash, sync local main and remove only this completed branch. Preserve all recovery stashes and the protected worktree.
