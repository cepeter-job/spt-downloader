# Native JSON PPh Pasal 21/26

## Approved scope

Extend the existing PPN JSON-first pipeline for the five observed PPh21 forms:
Induk, L-IA, L-IB, L-II and L-III. This is a separate PR based on merged PR #36
(`4482063b9ada37125d1e3d49b83e401a23719cdb`). The user approved the following
bounded design before implementation:

- Source business values only from custody-checked JSON responses, with per-value
  source paths and sequences; use DOM only for read-only navigation and structure.
- Preserve the approved PPh21 template, dynamic body growth and reported totals.
  Monetary slots use native Excel numbers under the existing strict precision
  contract; identifiers, periods and document numbers remain literal text.
- Unsupported JSON shapes/builds may fall back to DOM, explicitly reported as DOM.
  Identity contradictions, authentication failures and privacy violations fail
  closed even when coverage or the public build is unsupported.
- Reuse existing capture, listing identity, projection, observer and export
  infrastructure where the verified PPh21 contract actually matches. Keep
  PPN/Unifikasi behavior unchanged; do not generalize unrelated tax types.
- All product imports, tests, synthetic browser/Tk fixtures and builds run on
  GitHub runners. No real taxpayer captures or identifiers belong in this PR.

## Public-source evidence

Source bytes are inspected as text, never executed. These are public application
bundles, not taxpayer responses. Their existence is not native-data acceptance.

| Source | SHA-256 | Binding |
| --- | --- | --- |
| `/returnsheets/id-ID/main.cccfdb820c20596c.js` | `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd` | character offset 217305: `article-21-26-tax-return/:taxpayerAggregateId/:recordId/:taxTypeCode/:aggregateIdentifier` loads chunk 803/module 82736 |
| `/returnsheets/id-ID/runtime.ad6c8837930b6ad2.js` | `934f411dec7ead216ca4d936a71c5b6a9ebf100874412b052fa6035e41102c57` | chunk 803 filename suffix `8681206e4827011e` |
| `/returnsheets/id-ID/803.8681206e4827011e.js` | `cd7b51042384a63e1d1fae9b9b284a38a0a942ab9f95a7fceb46b3c76fcd9add` | `ReturnsheetsSharedArticleTwentyoneTwentysixTaxReturnModule` |

All seven grid constructors below bind `GridId={ReturnSheetRecordId:this.recordId}`
and `IdColumn="RecordId"`. Offsets are Unicode string positions in the decoded
public 803 bundle, not inferred API aliases. Paths are relative to the configured
returnsheet API base.

| Form/group | Endpoint | Offset |
| --- | --- | --- |
| L-IA | `/loadarticle2126/l1a-grid` | 2640 |
| L-IB/BPA1 | `/loadarticle2126/l1b-bpa1-grid` | 11994 |
| L-IB/BPA2 | `/loadarticle2126/l1b-bpa2-grid` | 12192 |
| L-II/BPA1 | `/loadarticle2126/l2-bpa1-grid` | 21922 |
| L-II/BPA2 | `/loadarticle2126/l2-bpa2-grid` | 22175 |
| L-III/BP21 | `/loadarticle2126/l3-bp21-grid` | 31529 |
| L-III/BP26 | `/loadarticle2126/l3-bp26-grid` | 31726 |

Chunk 693 is the separate Unifikasi family, not the PPh21 component.

### Reference labels: verified cell consumer, not filter dropdowns

The pinned main bundle contains module 75969 at offset 3726035 and module 29844
(the shared grid) later in the same file. The body-cell default branch at
4124027 selects `codeDescAsync` when `ReferenceDataType` is present; the pipe at
4217095 calls `getReferenceDataDescription`. In contrast, the `dropdownValues`
assignment drives filter choices and the separate custom-dropdown cell type.
The PPh21 columns do not declare that custom-dropdown cell type. Therefore the
TaxCertificate filter's `GiU` catalog does not override its body label source.

Reviewed reference types are `EBUPOT_TAX_CERTIFICATE` (`cN`, definition 2876400),
`COUNTRY_CODE` (`gD1`, 2720543) and `EBUPOT_STATUS` (`SSB`, 2876070). The ordinary
cache-miss branch of `getSingleReferenceData` invokes `internalLoadBulkReferenceData`
at 3022028, a read-only bulk GET with locale and type/checksum bindings. The
`getdescription` POST branch is specific to district/subdistrict; it must not be
assumed to be the PPh21 reference source. `getActiveReferenceDataValue` uses strict
code equality and validity precedence; a naked code/label dictionary cannot
establish its own custody or locale. The adapter must validate reference response
bytes, requested types, locale and selection before passing lookups to projection.

### Primary and final Induk lifecycle

The parent `getPrefillData` calls `/prefillreturnsheet/article-2126` with
`{RecordId, onManualClick}`. Its successful response consumer passes `Payload`
to `fillForm`, which parses `Payload.FormData` and runs the PPh21 `calculate`
method. History instead calls `/returnsheethistory/a2126`; it is not the same
read-only capture contract. Neither update checks nor save/submit methods are
native data sources or actions to invoke.

The service calculation is NOT the end of the Induk lifecycle. In the same
pinned chunk, `rshshr-art2126-main-form` applies `Math.round`, then its
`valueChanges` subscription recomputes balances from the rounded controls.
`getDataFromBaseForm` overwrites period/model/header fields from the outer
payload and can trigger that subscription again. Migrated A21 balances retain
raw FormData values; A26 balances do not have the same migration exemption.
For example, `round(sum) - round(carry) - round(SP2D)` can differ from rounding
the service's unrounded balance. Negative halfway values use JavaScript rounding,
not decimal half-away-from-zero. Tests must pin these later writes explicitly.

The `updatedL1a` method has only one textual occurrence (its definition) in the
reviewed bundle; the L-IA template wires `isHaveValue` to validation, not to this
method. Its existence alone does not prove an executing footer callback.
Claims-dependent declarator fallback exists in the child `setFormData`; it must
not become guessed JSON identity data. The approved template omits that display
control. Unknown lifecycle branches remain unsupported, not silently equivalent.

## Implementation and verification order

1. Publish RED safety contracts for every grid's literal record identity,
   cross-family contamination, and dispatch checks before observation, after
   observation and after final response drain. Unknown structure must not hide
   any contradiction. Matching requests alone never grant JSON eligibility.
2. Trace the actual primary response consumer, FormData schema and final Induk
   calculation lifecycle. Verify header and appendix footer source paths,
   reference-label dependencies, read-only visibility and later assignments.
   Do not mistake the `wsarticle2126` update-check method for proof of the primary
   source. Do not copy Unifikasi identity types or aliases without evidence.
3. Add synthetic five-form adapter, per-value provenance, pagination/count,
   repeated-snapshot and identity contracts; implement the specific projections.
   Include empty/optional groups, duplicates, zero/negative values and amendments.
4. Wire value-free observation and dispatch with getter-trap browser tests,
   fallback audit assertions, original-capture immutability, saved-workbook
   numeric/layout checks and unchanged PPN/Unifikasi regression contracts.
5. Verify exact-head runner results and packaged worker resources; publish the
   completed PR without claiming installation or live-account acceptance.

## Current acceptance state

Initial safety contracts are runner-verified after the guard/dispatch change.
The next Windows RED run verified 60 new amount/footer failures caused by the
missing projection module, with all existing tests passing. Source-bound amount
and footer projections are now implemented in `coretax_pph21_json_bindings.py`
and registered in the worker allowlist. Windows run `39094810785` verified
2,824 cases with no failures after implementation.

Independent review suggested restoring stored withheld/balance scalars. Those
findings were rejected after tracing the complete chain: `fillForm` calls
`calculate(JSON.parse(t.FormData))` at offset 93581, `mapFormData` calls
`mapMainFormData` at 94053, and the child receives these calculated values.
The child subscription at 55466 explicitly sets the A26 balance as well. Thus
stored `999`/`888` sentinels must not replace computed 41/36 in the synthetic
contracts. A separate parent check corrected BP21 footer spans to `[4,4,1,1,4]`
from the actual grid column declarations; BP26 remains `[5,7,1,1,4]`.

Windows run `39096081265` verified the next RED contracts: 43 failures limited to
the absent primary/grid implementations. On head `6d8b053`, Windows run
`39098304768`, artifact `12125831907`, verified 2,880 cases with only 11 expected
reference-projector failures. Primary identity, all seven grid projections,
amounts/footers and existing tests passed that runner suite.

Reference-label projection now implements strict literal codes, the first
explicit null/empty `ValidTo` version, source paths and locale contradiction
checks. Multiple closed versions remain unsupported without a bound browser
clock; the pinned main `getActiveReferenceDataValue` selection rule includes
character offsets 3017302–3017442.
This new implementation still requires its own runner result and response
custody integration; a passed pure projector does not authorize a naked lookup.

The browser RED contracts use five real component wrappers and seven inner
`ui-grid` elements, start pagination at a later page, and trap input/checked,
textarea, body and footer value reads. Fixture health and getter traps run
independently of the missing observer. Missing APIs fail assertions, never skip.
Failed delegated test files were reviewed and corrected before publication.

Windows run `39100071027`, artifact `12126690858`, verified 2,896 cases on
`1036911`: only the ten missing-observer contracts failed. Reference projection
and six independent browser-fixture/getter checks passed. The next Windows run
`39101045530`, artifact `12125814623`, verified 2,921 cases on `75dfa71`: all
observer contracts passed, including four Induk tables containing Angular
`p-inputnumber` hosts; only four new reference-capture/admission contracts failed.

The reference GET repair now extends both capture admission and the shared byte
custody validator. It allows only the exact three-catalog URL, GET with no body,
and selected PPh21 metadata; the decoder additionally requires native
`ICT_WIT`/`ICT_WITR`. Other families retain the POST-only rules. Source bytes,
manifest/checkpoint readback, frame ownership, authorization and repeated-snapshot
checks are retained. This repair awaits its own runner verification.

Independent review's double-binding finding was rejected: `fields` is the
control catalog while `row_fields` records table geometry. Neither contains tax
values, and no value-producing consumer of `row_fields` yet exists. The runner
asserts exactly one catalog entry per amount host plus matching geometry; losing
the geometry would prevent source-to-cell binding rather than deduplicate output.

### Remaining header contracts

The public source does **not** hide Status for submitted returns: public803 at
73000–74200 creates `ui-dropdown` at node 19 unconditionally, while the later
`ngIf` at node 25 guards a different block. The static label is `Status SPT` in
`HEADER`; `customFormControl` binds `mainForm.get("Status")` at 76625. A scoped
structural binding is required because production Angular property bindings need
not expose `formcontrolname` as an HTML attribute.

Main at 2977022 declares `RETURN_SHEET_MODEL` with codes `NORMAL`/`AMENDMENT`.
Its `ui-dropdown` component at 3995316 uses `getSingleReferenceData`, defaults
`excludeExpiredOptions` to false, and uses `CodeDescription`/`Code`; it does not
invoke the grid's active-version selector. Therefore the additional model-catalog
contract rejects duplicate versions rather than reusing grid selection rules.
The exact separate model GET, four final outer-header projections, and structural
Status control are new RED contracts, not implemented acceptance claims.
`getDataFromBaseForm` at 59922 overrides period/identity/status after inner form
mapping; `DeclaratorName` at 59449 uses nullish fallback, not Boolean OR.

Windows run `39102638017`, artifact `12127472419`, verified 2,948 cases on
`394cea0`: 18 missing-header, three missing-model-projector, one structural
Status and two new model-GET failures were expected RED. One additional failure
was a test-fixture defect: checkpoint replay requires the selected `detail_url`,
which the stub omitted. The fixture now declares its owned detail URL; the
production checkpoint identity guard was not relaxed. The prior three-catalog
capture, authorization and packet-admission behavior passed up to that replay
assertion. Independent source review found no blocker in `670cbda`.

Header/model projection and scoped structural Status observation are now
implemented, awaiting runner verification. Reference admission now has exactly
two GET URLs: the three grid catalogs and the separate model catalog. Both retain
the same family, identity, custody, method and no-body restrictions.

New complete-attempt contracts assemble all five forms, both pages of all seven
grids, original response-backed reference labels and reported (not body-summed)
footers. Workbook contracts require five clean sheets, unchanged template styles
and print layout, numeric money, textual period/identity, and complete mapping
reports. Missing/extra forms, missing pages, unbound lookups, DOM values and
repeated monetary geometry must not grant native coverage. These assembly/export
contracts are RED until the full adapter exists.

Windows run `39103587730`, artifact `12127770901`, verified 2,963 cases on
`e7f0998`: only the two complete-assembly/export positives and the wrong-reference
sequence contract failed. Header/model/Status, GET custody and checkpoint replay
passed. The verified artifact SHA-256 is
`00ea8679b57a6af01ec089c394cac3c5ca1185c98544f415c180db4a02965f2e`.

The separate five-form projector is now implemented, with original packet
binding, explicit lookup custody, single emission of monetary geometry and
independent appendix groups. It awaits runner verification; no native export
success is claimed. Additional contracts cover an empty first BPA group, literal
PPh21 listing identity, dedicated observer dispatch, captured reference GETs,
authorization failure and real synthetic Edge capture-to-workbook output.

Windows benchmark run `39105134964` on `f6394ee` verified 2,985 unique cases
across artifacts `12128725488` and `12127729793`: all 17 full-projection contracts
passed, including five-sheet styles/print layout/numeric-money export, empty BPA1
with independent BPA2, immutable original sources and wrong-reference rejection.
The remaining 18 failures were exactly the new listing, dispatch and reference
observer contracts. Independent read-only review found no concrete blocker in
`d7bfef3`; this was source review, not execution evidence.

The integration implementation now selects the dedicated PPh21 observer, binds
listing identity with literal ICT_WIT/ICT_WITR codes and saves original listing
bytes, and fetches only the two reviewed reference URLs in the same capture.
GETs refuse redirects, stream-discard with a 32 MiB limit and 30-second timeout,
check cancellation and selected-page ownership around each request, and return
only transport facts. No tokens, storage credentials or complete headers are
read. In pinned main source, the interceptor explicitly exempts
`/referencedata/api/currentreferencedata` at offset 232330 from its authorization
rewrite; the reference service uses a JSON-content-type GET. Direct reference
fetching therefore does not require extracting the application's credentials.

These integration changes await runner verification. Existing cross-return
injection tests now patch the dedicated observer selected by production, with
all original fatal-before-fallback assertions retained. New full-collector proof
checks original listing bytes before View and native checkpoint replay; additional
reference tests cover network failure, redirect refusal, non-JSON, advertised
size overflow and cancellation between catalogs. Synthetic runner evidence is
not authorized live acceptance, an installed build, or permission to merge.

On `f642f09`, Windows benchmark `39106484594` artifacts `12129235090` and
`12128473923` verified 2,991 unique cases: 2,990 passed, including the real Edge
capture-to-five-sheet workbook, listing/dispatch and reference transport/auth
contracts. One new whole-collector test exposed a missing-directory prerequisite:
`listing-responses` was assumed to exist from prior inventory. Job `117613348028`
reported WinError 2 at that exact directory, before View. The fix pins the job
folder, creates the direct proof child, pins that child, then uses exclusive-create
for the original bytes; it does not relax identity or reparse-point checks.

The stronger collector contract checks proof before the actual View action and
rejects an existing file at the proof-directory path without touching it. An
isolated allowlisted-worker contract now exercises the real PPh21 projector
without repository imports. These last changes await runner verification.
