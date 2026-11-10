# Corporate L3 B: live row inventory and Jakarta-offset date proposal

Date: 2026-11-10

Status: Proposal only. Operator approval is required before production changes. Runtime execution remains hosted-CI-only. This proposal is separate from financial-PDF discovery and performance work.

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
- The first displayed number is the page-local `gridModel.Data.indexOf(row) + 1`, not source `Index`.
- `IsManually`, `TableSource` and action configuration concern edit/delete actions, which are not admitted in this submitted read-only branch.
- The parent stores emitted B data, but final totals are patched from the separate captured B-footer endpoint, not inferred from displayed rows.
- The active date column is explicitly `type: 'date'`; the existing source-proven locale/timezone gates remain mandatory.

`project_l3` currently rejects the thirteen-key row before monetary, catalog-label, date and footer projection. `_apply_l3` already binds owned current source, the submitted route/lifetime/Induk visibility, exact requests and four observed catalogs before invoking this helper. Its raw pages, sequences, paths and source bytes must remain unchanged.

Independent tracing of the shared date renderer and explicit-offset parser is required before implementation; record its exact public-source anchors in the approval revision. Do not substitute a general assumption about browser date parsing for that chain.

## 4. Proposed closed extension

1. Retain the legacy exact eight-key row branch unchanged. Add one exact thirteen-key branch: the old inventory plus exactly the five reviewed fields. Any unknown, removed, partial extension or case-normalized key set stays unsupported.
2. For the added branch require the actual reviewed typed metadata: Index is JSON numeric zero, IsManually is literal true, TableSource and Action are explicit null, and IncomeTaxUsd is exact safe integral numeric zero. Reject bool-as-zero, ordinary numeric strings, unsafe numeric tokens, objects/arrays, missing keys and nonreviewed values. Never fill missing values or delete extras to fit the legacy schema.
3. Preserve each added value and original numeric lexeme as typed source provenance with the original page index and Data-row path. Existing `_apply_l3` then binds the actual response sequence and Payload container. Explicitly classify these as retained nondisplayed source metadata; do not claim a worksheet cell or fabricate a rendered USD column. Keep original response bytes and leaves untouched.
4. Extend only active-B date handling to the source-proven explicit `+07:00` form. Bound it to a valid ISO calendar within the existing year limits and the existing id-ID/Asia/Jakarta environment; preserve the original full date string in source provenance. The initial candidate is the observed seconds/midnight form only. Any justified wider time/fraction support must be written into the reviewed design first. Do not add other offsets, arbitrary Python date parser syntax, local machine clock/timezone, or a generic strip-offset operation.
5. Preserve legacy date-only/UTC-Z support and all offline-A date/null/empty-string semantics. Active-B null remains blank; empty-string and malformed dates remain unsupported. Do not silently broaden the offline helper merely because A and B share code.
6. Preserve exact monetary arithmetic, raw code/label bindings, duplicate row order, page-local row numbering, authoritative footer inputs, all three footer layouts, overwritten/unused controls, unresolved standalone fields and template scope. No sums of B rows may replace captured footers.

Unknown variants remain whole-record DOM fallback. Known source/identity/snapshot contradictions remain fatal. Stop remains cancellation. This grants no new transport, request, native environment, template mapping or financial-PDF permission.

## 5. Tests-first hosted verification

After operator approval, use a fresh implementation branch from current origin/main; keep this proposal separate. No local product imports or runtime execution.

1. Add a clearly synthetic exact thirteen-key plus Jakarta-offset case through the real pure projector. Confirm hosted RED is the exact domestic-row key-set refusal, not a fixture/import error. Then minimally implement this bounded behavior.
2. Independently prove the date gate: use a legacy eight-key B row with the reviewed offset so the schema guard cannot mask the date refusal. Verify the formatted date and retained original date string together. Include invalid calendars/year bounds, offset variants, whitespace, unexpected fractions, empty string and bool/nonstring inputs; preserve offline-A behavior.
3. Negative schema/metadata matrix: missing each added/base field, unknown extras, partial extensions, wrong casing, bool-as-zero, string/number marker distinctions, changed Index/IsManually/TableSource/Action/IncomeTaxUsd and precision. Assert refusal without mutation or discarded leaves.
4. Positive provenance tests: all five added leaves retain exact type/lexeme/path/page index and later actual response sequence/container. Reject mutated original bytes and changed metadata during held replay; a caller-provided proof cannot invent or replace source leaves.
5. At least two B pages including a partial final page and duplicates; also one inexpensive pure synthetic 466-page/4654-row inventory test to cover the real count boundary without live taxpayer data. Assert order, duplicate retention, local numbering and complete normalized page coverage.
6. Use the actual owned L3 observer fixture with original packet custody, adapter, held replay and saved/reopened workbook. Cover current-classification enabled proof and existing predecessor/model variants; preserve no-DOM-business-read traps. Assert the real eight-column body, captured footers, original provenance and verified native source result together.
7. Run existing L3/catalog/clock/safety/lifecycle/Induk/native/template/GUI suites and full exact-head Windows CI. An independent review must inspect raw-leaf carriage, datetimes, type-marker handling and existing eight-key behavior. Do not update shared fixtures to hide malformed inputs or bypass guards.

## 6. Completion and explicit nonclaims

AST/diff/source inspection is not behavior-test evidence. A full hosted green run and synthetic native case are not acceptance of the real submitted return. The operator must run the exact verified build and the correlated live source result must become `native_verified`; PDF capture and final mapping/publication completeness remain separate gates. A later distinct refusal is still unresolved, never silently marked fixed.

No performance/pagination-size change, retry, timeout increase, new catalog GET, missing-account synthesis, unsupported attachment download, template-slot invention or publication change belongs in this PR. Update the applicable AGENTS.md contract only through its normal approval-protected edit after approval; do not overwrite unrelated current-main instructions.
