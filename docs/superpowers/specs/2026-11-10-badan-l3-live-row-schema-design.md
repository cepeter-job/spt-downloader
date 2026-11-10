# Corporate L3 B: live row inventory and Jakarta-offset date proposal

Date: 2026-11-10

Status: Implemented and merged through #229. The operator separately authorized publication of design records #227/#228 and their AGENTS.md contract follow-up. The sections below retain the historical pre-fix investigation and approved scope; hosted implementation verification is recorded in section 7. The contracts for the merged L3 and financial-PDF fixes are maintained alongside this record in AGENTS.md after a freshly authorized normal protected edit. Runtime execution remains hosted-CI-only; operator live acceptance is not established. No performance work is included.

## Outcome and acceptance boundary

The saved exact-build attempt falls back with `unsupported_corporate_l3_domestic_row`. The current projector's first domestic-row guard accepts only eight exact keys. Every original captured B row has thirteen keys. A second deterministic incompatibility lies behind that first guard: every captured date uses an explicit `+07:00` ISO offset, while the active-B date helper accepts only date-only or UTC-Z syntax.

Changing only the key guard would expose the date refusal on the same data. Neither finding authorizes arbitrary row extras, removing leaves, coercing absent values, replacing dates, changing pagination, or claiming whole-record native acceptance.

## 1. Evidence, provenance and privacy

Investigation baseline: `536fa0cb69657026725a7f82f60d57fdbc951467`. Diagnosis uses the already associated private failed job and its sealed original responses. No real records, identifiers, dates, amounts, URLs, filenames or source payloads belong in this document or tests.

Read-only source analysis independently rechecks SHA-256 of each original L3 page/footer body against its manifest descriptor before examining shapes and predicates. Safe aggregate results:

| Predicate | Result |
| --- | --- |
| Original B pages / rows | 466 / 4654 |
| Ten-row requests, contiguous offsets, one consistent total, exact final-page count | all true |
| Rows with exact thirteen-key inventory | 4654 |
| Missing keys from the current eight-key inventory | none |
| Added keys | `IncomeTaxUsd`, `IsManually`, `TableSource`, `Index`, `Action` |
| `Index` is a JSON integer zero | all rows |
| `IsManually` is literal JSON true | all rows |
| `TableSource` and `Action` are explicitly null | all rows |
| `IncomeTaxUsd` is a JSON numeric zero | all rows |
| Existing TaxBase/IncomeTax and added IncomeTaxUsd are safe integral JSON operands within fifteen digits | all rows |
| Date shape | all rows are 25-character explicit ISO-offset strings |
| Date offset equals Jakarta +07:00; time is midnight; year is within existing 1970..2100 bounds | all rows |
| Original footer responses | one, with exact TaxBase/IncomeTax/IncomeTaxUsd inventory and safe operands |

These are comparisons/counts, not printed business values. Numeric zero/true/null above describe the closed reviewed metadata branch, not invented defaults for missing source. No local product import, pytest, fixture browser, build or EXE execution was performed. No adapter replay or full native result has been claimed.

## 2. Authorized operator-browser corroboration

The parent reopened the existing operator profile; manual login remained valid. Only inspected read-only selected-return navigation and L3/Induk tabs were used. No submission, cancellation, generation, email, document download or arbitrary backend request was performed. No Angular state, input value, checked state, business body cell or footer amount was read.

Freshly enumerated loaded public providers were fetched as same-origin JavaScript and independently hashed:

| Provider | SHA-256 |
| --- | --- |
| `525.32c49782948fc5ef.js` | `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153` |
| `main.bed1449c3647a8ca.js` | `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44` |
| `vendor.c32c4ee39d966e30.js` | `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173` |

All match the current reviewed source pins. This is source/structure corroboration, not an application-owned capture lifetime or permission to relax native environment checks.

The visible owned L3 form contains one B grid and one actual table. Its first header row has the existing eight submitted Rupiah columns, with the expected filter row. Its first body page has ten rows of eight cells. Its three footer rows have spans `[4,1,1,2]`. Only headings, counts and spans were inspected; no body/footer text was returned.

## 3. Public-source consumer and current guard order

Reviewed corporate L3-B component is around decoded-character offsets 2253200..2259850 in the pinned corporate provider:

- The submitted branch excludes TINDAKAN; the ordinary Rupiah branch excludes the USD column.
- The actual shared type-row renderer uses page-local `rowIndex + 1`, not source `Index`. The component also defines an equivalent showIndex callback, but the real renderer is the decisive proof.
- `IsManually`, `TableSource` and action configuration concern edit/delete actions, which are not admitted in this submitted read-only branch. TableSource is not globally unused: a parent accounting-validation callback also inspects it. Requiring literal null deliberately excludes that branch.
- The parent stores emitted B data, but final totals are patched from the separate captured B-footer endpoint, not inferred from displayed rows.
- The active date column is explicitly `type: 'date'`; the existing source-proven locale/timezone gates remain mandatory.

`project_l3` currently rejects the thirteen-key row before monetary, catalog-label, date and footer projection. `_apply_l3` already binds owned current source, the submitted route/lifetime/Induk visibility, exact requests and four observed catalogs before invoking this helper. Its raw pages, sequences, paths and source bytes must remain unchanged.

Independent tracing establishes that this active date column uses Day.js, not Angular DatePipe. The chain below was rehashed against the approved providers, and the parent independently checked the format helper, parser and accounting-validation anchors. Offsets here are zero-based UTF-8 byte offsets, unlike the approximate decoded-character component region above.

| Provider / byte anchor | Source-proven behavior |
| --- | --- |
| Corporate 2253816..2254254 and 2254839 | Metadata affects edit/delete predicates; submitted construction excludes TINDAKAN. |
| Corporate 2255651 | Ordinary Rupiah construction excludes the IncomeTaxUsd body column. |
| MAIN 4224852, wired at 4241600..4243450 | Actual row renderer emits page-local rowIndex plus one. |
| Corporate 2298739..2298950 | B-change stores rows; only TableSource TAXPAYER_ACCOUNTING enters the additional accounting validation. Literal null excludes it. |
| Corporate 2294627 / 2295426 | Separate footer request and populateFooterGrid2 copy captured footer operands; no body-row sum supplies final totals. |
| Corporate 2255910; MAIN 4226303, 4241774, 4243402 | Active WithholdingSlipsDate type-date renderer calls formatDate with the source field and configured format. |
| MAIN 4298773..4299200; default 2732882 | Format helper uses one-argument Day.js and maps dd-MM-yyyy to DD-MM-YYYY. |
| MAIN 4204870; vendor 191706, 193618..194220 | Import resolves Day.js module71764. Its component-constructor regex has no signed-offset alternative; canonical explicit-offset strings reach new Date(originalString). |
| Vendor 194081 and 197034..197216 | Local getFullYear/getMonth/getDate provide the formatted day. Existing independently proved Asia/Jakarta environment therefore remains essential. |
| Vendor 202370 / 204131 | CustomParseFormat does not reinterpret this one-argument call; without a format argument it delegates to the original parser. |

The five new metadata leaves must remain typed source evidence. Shared Masa `_evidence` currently rejects booleans; handle only the reviewed literal-True IsManually provenance locally instead of widening that shared helper. Corporate raw evidence already represents it as type boolean and value true.

The date helper is shared beyond L3-A: L11-A also calls `_l3_date`. A separate default-off option or L3-B-only helper is mandatory; only the active-B caller may opt into the new offset branch. Do not globally widen the helper grammar.

## 4. Proposed closed extension

1. Retain the legacy exact eight-key row branch unchanged. Add one exact thirteen-key branch: the old inventory plus exactly the five reviewed fields. Any unknown, removed, partial extension or case-normalized key set stays unsupported.
2. For the added branch require the actual reviewed typed metadata: Index is JSON numeric zero, IsManually is literal true, TableSource and Action are explicit null, and IncomeTaxUsd is exact safe integral numeric zero. Reject bool-as-zero, ordinary numeric strings, unsafe numeric tokens, objects/arrays, missing keys and nonreviewed values. Never fill missing values or delete extras to fit the legacy schema.
3. Preserve each added value and original numeric lexeme as typed source provenance with the original page index and Data-row path. Existing `_apply_l3` then binds the actual response sequence and Payload container. Explicitly classify these as retained nondisplayed source metadata; do not claim a worksheet cell or fabricate a rendered USD column. Keep original response bytes and leaves untouched.
4. Extend only active-B date handling to the source-proven explicit `+07:00` form. Bound it to a valid ISO calendar within the existing year limits and the existing id-ID/Asia/Jakarta environment; preserve the original full date string in source provenance. The initial candidate is the observed seconds/midnight form only. Any justified wider time/fraction support must be written into the reviewed design first. Do not add other offsets, arbitrary Python date parser syntax, local machine clock/timezone, or a generic strip-offset operation.
5. Preserve legacy date-only/UTC-Z support and all offline-A/L11-A date/null/empty-string semantics. Active-B null remains blank; empty-string and malformed dates remain unsupported. Do not silently broaden the shared helper for other consumers.
6. Preserve exact monetary arithmetic, raw code/label bindings, duplicate row order, page-local row numbering, authoritative footer inputs, all three footer layouts, overwritten/unused controls, unresolved standalone fields and template scope. No sums of B rows may replace captured footers.

Unknown variants remain whole-record DOM fallback. Known source/identity/snapshot contradictions remain fatal. Stop remains cancellation. This grants no new transport, request, native environment, template mapping or financial-PDF permission.

## 5. Tests-first hosted verification

After operator approval, use a fresh implementation branch from current origin/main; keep this proposal separate. No local product imports or runtime execution.

1. Add a clearly synthetic exact thirteen-key plus Jakarta-offset case through the real pure projector. Confirm hosted RED is the exact domestic-row key-set refusal, not a fixture/import error. Then minimally implement this bounded behavior.
2. Independently prove the date gate: use a legacy eight-key B row with the reviewed offset so the schema guard cannot mask the date refusal. Verify the formatted date and retained original date string together. Include invalid calendars/year bounds, offset variants, whitespace, unexpected fractions, empty string and bool/nonstring inputs; preserve offline-A and L11-A behavior.
3. Negative schema/metadata matrix: missing each added/base field, unknown extras, partial extensions, wrong casing, bool-as-zero, string/number marker distinctions, changed Index/IsManually/TableSource/Action/IncomeTaxUsd and precision. Assert refusal without mutation or discarded leaves.
4. Positive provenance tests: all five added leaves retain exact type/lexeme/path/page index and later actual response sequence/container. Reject mutated original bytes and changed metadata during held replay; a caller-provided proof cannot invent or replace source leaves.
5. At least two B pages including a partial final page and duplicates; also one inexpensive pure synthetic 466-page/4654-row inventory test to cover the real count boundary without live taxpayer data. Assert order, duplicate retention, local numbering and complete normalized page coverage.
6. Use the actual owned L3 observer fixture with original packet custody, adapter, held replay and saved/reopened workbook. Cover current-classification enabled proof and existing predecessor/model variants; preserve no-DOM-business-read traps. Assert the real eight-column body, captured footers, original provenance and verified native source result together.
7. Run existing L3/catalog/clock/safety/lifecycle/Induk/native/template/GUI suites and full exact-head Windows CI. An independent review must inspect raw-leaf carriage, datetimes, type-marker handling and existing eight-key behavior. Do not update shared fixtures to hide malformed inputs or bypass guards.

## 6. Completion and explicit nonclaims

AST/diff/source inspection is not behavior-test evidence. A full hosted green run and synthetic native case are not acceptance of the real submitted return. The operator must run the exact verified build and the correlated live source result must become `native_verified`; PDF capture and final mapping/publication completeness remain separate gates. A later distinct refusal is still unresolved, never silently marked fixed.

No performance/pagination-size change, retry, timeout increase, new catalog GET, missing-account synthesis, unsupported attachment download, template-slot invention or publication change belongs in this PR. Update the applicable AGENTS.md contract only through its normal approval-protected edit after approval; do not overwrite unrelated current-main instructions.

## 7. Implemented state and remaining documentation gate

- Implementation #229 was merged as `7da937e906462889430179e24edae977c1fc90f2`. Its final pre-merge head `5b5605b6842d5a9afc2acb7a3564270cfda2974e` passed full hosted Build `42800307173`, including all 77 schema/date cases and 10 actual native/custody/workbook cases.
- The combined L3 and financial-PDF head `70d2528113eb71e203a73aadbe01a6959c5bb204` passed Build `42809281591`. Four downloaded Windows JUnit artifacts independently confirmed all 194 new cases passed, with no new skips/failures/errors or older Windows failures/errors. CodeQL, all four Windows shards, coverage, packaging, exact uploaded-artifact readback and packaged bootstrap passed.
- Official main `e5e0e988f1908d08c8a730d5a27e17665772b681` passed Build `42813223671`, including CodeQL, Windows workloads, packaging/readback/bootstrap and artifact provenance. Its source tree equals the verified combined head. These are hosted synthetic/build results, not operator native acceptance.
- Earlier protected-file attempts timed out without applying contract text. The operator then issued fresh explicit authorization, and one normal protected edit succeeded. The bounded L3 schema/date/provenance and modern financial discovery/label/action contracts are maintained in AGENTS.md with their independent hosted/live verification boundaries. No alternate write path or runtime code change was used; documentation publication adds no new runtime or live-acceptance permission.
- The operator separately authorized publication of both design records. A correlated application-owned exact-build `native_verified` result, real portal PDF completion, mapping and whole-run completion remain separate unproved gates. No L11-A/L11-C expansion is included.
