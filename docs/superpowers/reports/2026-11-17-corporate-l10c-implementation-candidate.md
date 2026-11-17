# L10-C implementation candidate and remaining admission blocker

Status: **C consumer/observer dispatch, independent lifecycle and framework-source
proof implemented; full coordinated populated native acceptance still BLOCKED**.
This implementation follows the full-populated scope decision after the separate
[docs-only proposal in PR #276](https://github.com/cepeter-job/spt-downloader/pull/276).
It does not replace that decision with empty-only support and does not complete
native L10-C. PR #276 remains separate and unchanged.

## Initial implemented boundary (historical candidate)

`coretax_corporate_projection.project_l10c` transforms the exact four-column
original body plus its row numbering into the five approved worksheet columns.
It preserves literal partner names, source order and duplicate occurrences.
Transaction/country codes require independently supplied description inputs;
missing/blank/nonstring descriptions refuse rather than exporting a code.
Those inputs are **not** native catalog evidence. Initially no observer or
adapter called this candidate. The new guarded dispatch below independently
reconstructs labels from shared original packets; arbitrary labels/digests still
cannot turn a helper call into native permission.

`TransactionValue` follows the MAIN offline-body **Number** branch, not
NumberInteger or the online-grid `numberformat_ignoreprec` formatter. The
candidate accepts null as blank and only finite, exact-binary JSON numbers
within fifteen significant digits, absolute value at most 999999999999999,
and at most three normalized fractional digits. It never rounds a candidate.
For example the synthetic exact fraction 1234.125 becomes `1.234,125`, not
`1.234`. Numeric strings, booleans, signed zero, unsafe precision and wider
fractional/rounding profiles refuse. This bounded transformation is not a
loaded-framework or application-owned display-parity proof.

The initial exact-binary/no-rounding subset above is historical: the new
source-excerpt proof described below replaces that restriction with the actual
default 1.0-3 DecimalPipe rule for bounded Number-to-string-stable inputs.

The source getter's `TotalTransactionValue` is retained as typed nondisplayed
provenance. It does not create a footer or a sum, and a nonzero stored total is
not silently replaced by the getter's constant zero. Question remains typed
unresolved evidence: no boolean-to-`Ya`/`Tidak` conversion and no claimed radio
selection. Its boolean support is local, not a widened shared Masa scalar rule.
Literal null and an empty body list remain distinguishable in provenance.

The candidate marks `projection_complete=False` and carries three unresolved
control identities (PeriodYear, CollectorTin, Question). L10-C's existing
renderer now counts those identities once and carries the fixed
`unprojected_l10c_controls` reason into mapping and the resume Audit. The approved
A:E layout, reserved empty accounting slot and resource bytes are unchanged.
The L10-C body parser alone accepts the reviewed default Number consumer's
three fractional digits; every other form and all footer parsers retain their
existing two-digit grammar. The stored safe value is never rounded to the
zero-decimal accounting display.
No new worksheet/question row or omission approval is implied.

## Source observations for shared infrastructure coordination

Source-only read against configured pins was repeated independently:

- CIT `525.32c49782948fc5ef.js`:
  `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
- MAIN `main.bed1449c3647a8ca.js`:
  `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
- Unchanged approved resource SHA-256:
  `47770d95a613ed496c8f121cbe39f41ea17947855e709ab0f931adbe9ca58ab0`.

The following offsets are **decoded character offsets**, not byte offsets:

- CIT 59312: `CitrL10CGrid1Columns`, `TRANSACTION_TYPE` and country
  reference keys, Number column and child `rsh-citr-l10c-grid1`.
- CIT 69597 onwards: child constructor, initial change handler, body mapping,
  question patch, getter, disabled state and common output emission.
- CIT 2623320: `Qm` passes **baseFormData** as the child's mainFormData and
  l10cFormData as formData, with `onCallbackForm("L10CForm", value)`.
- CIT 2651207: original `formData.L10cFormData` assignment.
- CIT 2695011: common parent callback patches `[t]` before its switch. The
  MainForm arm calls `setShowAttachment10abc(_.IsTransactionWithRelated)`.
- CIT 2705414: only the source's numeric-equivalent 1 enables the L10-A/B/C
  group; zero disables it and patches all three parent controls to null.
- MAIN 3879597: offline-body Number uses the `number` pipe without an explicit
  precision argument; NumberInteger is a distinct `1.0-0` branch.
- MAIN 3882118 and 4318830: ordinary Dropdown goes through codeDescAsync to
  `getReferenceDataDescription` with ReferenceKey, not raw-code fallback.
- MAIN 3036628: reference description selects the active code/version.
- MAIN 3038044: getSingleReferenceData first waits for active bulk loading,
  then reads its application cache; a cache miss calls internalLoadBulkReferenceData
  with one type and null checksum. That source permits a naturally emitted
  exact no-checksum singleton GET, but does not prove that this capture saw it.
- MAIN 3042005: internalLoadBulkReferenceData builds its language/type
  GET from a list, including optional checksum suffixes. Re-find the symbol
  before implementing a request matcher; a generic identifier does not
  authorize all batch/checksum variants.
- MAIN 4175512: offline grid emits `rowIndex+1`. The independent exact-provider
  source proof below now traces and tests the nonvirtual paginator context.

The transaction reference catalog is a common L10-A/L10-C dependency. Its
same-attempt passive packet/provider/order/version custody should have one
coordinated owner; this independent tree intentionally does not edit that
shared capture registry, response parser or manifest protocol.

## What still blocks full native support

1. No original TRANSACTION_TYPE packet is available in the reviewed retained
   capture. Its absence does not prove no portal request occurred. No cache
   read, forced GET, guessed batch URL, fabricated catalog or code-as-label
   fallback is permitted.
2. A native descriptor needs exact source-proven request classes and original
   sequence sets, typed catalog/version/order provenance, positive configured
   **loaded** CIT/MAIN/framework provider pins, and all final-drain/clock checks.
   Source-byte matching offline is not loaded-provider custody.
3. Require the selected submitted current Rupiah route, preceding observed
   Induk, current IsTransactionWithRelated choice and exact owned enabled
   form/grid/offline/p-table structure. A stable parent root alone does not prove
   an uninterrupted child. The descriptor and any stronger manifest lifetime
   must be checked independently during live and held replay; no descriptor
   overrides, mixed attempts, child remount or late overwrite are admitted.
4. The source writer/no-late invariant and exact Number/radio/paginator
   consumers are now proved below. Full acceptance must still exercise that
   same current profile through the production shared catalog and joint
   final-custody path; isolated unit seams do not substitute for it.
5. The approved sheet has no question/header slots. Keep those identities and
   their typed raw controls unresolved and mapping PARTIAL unless a separate
   layout/omission decision is approved. Native/source coverage alone is not
   mapping COMPLETE or financial-PDF/job acceptance.

## Exact bounded operator request after coordinated passive capture exists

Have the operator select **one already-authorized, submitted ordinary-Rupiah
SPT known to contain populated L10-C**, in one fresh application-owned,
Service-Worker-blocked context. Perform the normal inspected View/Induk/L10-C
read only. Retain the original same-attempt id-ID COUNTRY_CODE and
TRANSACTION_TYPE response packets if the application naturally emits the
reviewed exact request forms, with original response bytes, request method/no
body, request-object ownership, sequences, attempt/selected-record/Document
binding, loaded-provider digests and final-drain/clock custody. Keep all private
bytes local. Return only value-free counts/presence/type/pin-match summaries.

Do not issue a reference GET, read browser storage/cache, open edit controls,
clear caches in an existing context, reuse another record's catalogs, or try
alternate language/checksum/batch forms to make the run pass. If no admissible
original packet appears, record that bounded attempt as unresolved and stop.
A separately authorized same-record populated DOM capture is also needed for
row/description/number/radio comparison; never print taxpayer values.

## Initial candidate verification status (historical)

Tests were written before their production changes. Local RED was established
by source/AST: `project_l10c` did not exist, and the L10-C renderer did not
consume `projection_complete`. No pytest, product import, fixture, build or EXE
ran locally. Runtime claims must be filled from exact-head Actions evidence.

The new hosted tests cover populated duplicates, literal strings and differing
code/label representations, exact fractional numbers versus integer rendering,
null/empty distinction, closed row/root shapes, missing/unsafe labels and
numbers, nondisplayed total/question evidence, saved/reopened approved workbooks
and resume PARTIAL notes, and actual hybrid DOM fallback without invented
catalog requests. They do **not** establish an admitted populated native packet,
owned child history, callback parity, or application-owned live acceptance.

## Follow-through: independent C-owned lifetime transport (not full completion)

The observer now calls `_observe_l10c_history` for an enabled L10-C with the
source-proven header/radio/grid structure. It binds the same actual form, grid,
table, tab and panel twice through `DetailJsonCapture.bind_l10c_structure` and
samples the C-owned capability. This first milestone was custody-only. The
guarded dispatch added subsequently is described below and requires independent
catalog and provider facts in addition to this lifetime.

`_L10C_HISTORY` is armed on the original Document before inspected View. Its
independent relevant-structure budget retains the unique original corporate
root, current Induk host, C child, offline-grid/p-table/table chain and the two
header/two radio control identities. It never reads an input value, checked
state, Angular instance or table body/footer content. A remount, detach/reinsert,
transient disable/re-enable, replaced header/radio or Induk host remains a sticky
contradiction even if the final selectors look unchanged. Ordinary row churn
and a tab's presentation-only highlight change do not assert a new child.

The closed `corporate_l10c_lifetime` schema is manifest-owned, binds the exact
attempt/record/list/detail route and is validated by live iteration, held
`checkpoint_bodies`, and the adapter's absence-inclusive event fingerprints.
Descriptor overrides (even equal ones), malformed/null facts, missing parent
custody and mixed attempts remain fatal. Cleanup retains newly acquired handles
before the post-RPC Stop check. The C-only final sample is the last browser RPC
inside the existing late-response fence. That same RPC now returns the end
clock; an unavailable/reversed clock never reuses the earlier pre-child sample.
Only local sticky parent-route, binding, late-response and Stop checks run after
it; Stop cannot seal a manifest.

**Combined history is deliberately not claimed.** If a C fact was already
offered and L7 or L8 history is requested, drain marks the attempt incomplete
with `unsupported-child-history-combination` rather than moving the stale-child
window to another sequential sampler or dropping a required fact. An unavailable
C capability that was never offered does not disable a valid legacy sibling.
The B owner's reviewed joint final-snapshot interface must be integrated by the
parent before that combination can be admitted. No competing shared registry
was created and no sibling worktree was edited.

### Exact remaining dependencies / bounded parent request

- Resolved source dependency: a broader read-only scratch inventory subsequently
  found cached public vendor bytes (`l10a-reviewed-vendor.js` and
  `induk-vendor-decoded.js`), both independently matching configured SHA-256
  `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`.
  No portal request or browser-cache read was needed. The provider excerpts
  below now have hosted tests; their final exact-head execution status must
  still be checked independently from application-owned loaded-provider custody.
- Integrate the parent's reviewed shared passive catalog producer (exact
  TRANSACTION_TYPE/COUNTRY_CODE request classes, original sequence sets,
  provider/order/version and final clock custody). This branch does not add a
  TRANSACTION_TYPE registry entry, force a GET or fabricate label evidence.
- Integrate the parent's reviewed B-owned final joint snapshot. C offers
  `bind_l10c_structure(...)`, `observe_l10c_lifetime(...)`, `_L10C_HISTORY` and
  `_capture_l10c_lifetime`; the shared owner must retain C and every already
  requested sibling through the same final browser RPC and end-clock boundary.
- Bounded layout question: may PeriodYear, CollectorTin and Question remain
  explicitly unresolved original controls with mapping PARTIAL and the existing
  Audit note, while only approved A:E body rows are projected? Or is a separately
  approved resource/layout change required? Nothing here approves omission or
  creates a row/sheet. The default remains honest PARTIAL.

The full populated observer -> capture -> semantic adapter -> held replay ->
saved/reopened native workbook acceptance case is **still missing**, not green
by quarantine. Existing pure saved/reopened candidate tests and the new lifetime
protocol/browser tests must not be relabelled as that end-to-end proof. No
protected AGENTS.md/resource/runtime/workflow changes, catalog transport changes,
active portal traffic, merges, or design-PR changes were made.

## Exact framework-source follow-through

`tests/fixtures/corporate_l10c_framework.js` retains only public Angular/PrimeNG
consumer excerpts from that exact vendor, plus clearly labelled DI/locale-lookup
and component-construction harness stubs. It is not a replacement formatter,
Intl approximation, application cache, business capture, or downloaded full
portal bundle. Tests execute these actual consumers on the GitHub-hosted Edge
fixture only. The fixture's normalized-text SHA-256 is
`d38db3f3cef2646e87fc2cb09e1e0ddd4082ed9f68fc4cddb4ead5deee911187`.
No provider algorithm was executed locally.

Decoded-character source ranges (end exclusive) and excerpt SHA-256:

| Consumer | Range | SHA-256 |
|---|---|---|
| Indonesian locale, including `#,##0.###`, comma decimal and dot group | 0:1549 | `5d7518b07cb4c6bc1435352efed94039125f76c658081eba257f5a351b17bd95` |
| Number-format and symbol enums | 1183395:1184352 | `a7fe0f86238a64a1f1d8e4924fa5ef83f2727a1133bde129e773c713dfa16a0e` |
| Locale number-symbol accessor | 1184545:1184774 | `5eb56029709f409409479ca47d9e74c26c22eb52ff417019f3b110ad312c88d0` |
| Digit-info regexp/integer parser | 1194568:1194725 | `79656259c91274c7b33679342d177933493a605d3d1ac83fc0fecc25254b5dfa` |
| Actual DecimalPipe constructor/transform and nested formatter | 1214520:1218199 | `5ecad55e031e526db3fc7a546106830948899c9b385f750ae2e50df3ffae4160` |
| Actual radio `writeValue` | 2247636:2247813 | `75a3e1ee4d90563e825ffb1e37e07a8f72cfccf8b20c241a6d42976e8c8927f4` |
| Actual pTableBody scroller option / row-index consumer | 2382002:2382220 | `cbc8dc95f0c96e29d5589ea9266d2f21d1eed6ca80fa2204f20173d034db4d98` |

The actual radio uses **loose** `B == this.value`, not strict equality. Thus
boolean true and string `"1"` select the source's string-`"1"` option; false and
string `"0"` select `"0"`. The child's nullish patch supplies `"0"`, whereas an
empty string selects neither string option. This proves why a generic strict
comparison or boolean-to-label guess is not acceptable. No new worksheet radio
slot or omission approval follows; the original control remains unresolved in
the approved layout.

The pTableBody context calls `getRowIndex(index)`, which uses `dt.first + index`
when `dt.paginator` is enabled and only delegates to a scroller index when
virtual scrolling is configured. The pinned MAIN offline template binds its
reviewed Paginator/Rows options and does not bind virtual scrolling. Its body
then emits `rowIndex + 1`; global duplicate-preserving ordinal numbering is the
reviewed nonvirtual profile, not a guessed per-page reset.

Number's default is the locale pattern's **0..3 fractional digits**, rounding
the JS Number's shortest decimal digits half-up. The pure candidate now accepts
at most fifteen significant digits and absolute value 999999999999999, only when
conversion to Number and back to its shortest decimal retains the original
numeric value. It matches `4.38 -> 4,38`, `0.1 -> 0,1`, and
`0.0625 -> 0,063` (including negative half cases), null blank, and zero suppression
after rounding. Strings, booleans, signed source zero, wider precision and
unstable Number conversions remain unsupported. The online fraction-0 and
NumberInteger consumers are not substituted. This transformation proof still
does not provide the missing coordinated native catalog/combined-lifecycle acceptance.

## Current-Induk and no-late input invariant (source proof, not observed quiet time)

The decoded pinned CIT source SHA remains
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`.
A fresh bounded source inventory retained these decoded-character offsets:

- 2648011/2648203: the sole parent `this.formData=` is the original
  `JSON.parse(t.CurrentFormData)` in `fillForm`; the sole `mapFormData()` caller
  is that same initial fill. `mapFormData` assigns current Main and C inputs;
  the parent C-input assignment is at 2651206.
- 2623687: the C template passes `baseFormData` to the child's `mainFormData`
  and the immutable mapped `l10cFormData` to `formData`. Thus the C headers
  originate from outer Payload.TIN/PeriodYear, not MainFormData.Tin/TaxYear.
- 2648621 and 2695879: the only calls to `setShowAttachment10abc` consume the
  initial outer flag and Main callback's IsTransactionWithRelated respectively.
  Its only writers are constructor false and the numeric loose-1/loose-0
  setter at 2705414. The zero branch clears the parent C FormGroup slot, not
  the original `l10cFormData` input; explicit outer contradictions still refuse.
- 2795046: the selector's sole nonconstructor Main-form assignment copies
  original `this.formData.IsTransactionWithRelated`. All other Main patchValue
  sites were inventoried; none writes that selector. There are no Main-form
  reset/setValue/setControl/removeControl call sites. Generic ternary patch
  arguments only target the enumerated amount controls, not this selector.
- 2812396/2844201: Main valueChanges emits getFormData, which reads getRawValue
  and changes only IncomeTaxInAYear/SignBy in the returned object. Even a delayed
  submitted disable/other-control callback therefore preserves the copied
  numeric-1 selector; it is not necessary to assert that no callback occurs.
- C 699xx-716xx: ngOnChanges re-runs setFormData only for a changed input
  reference; original grid mapping copies the four literal row operands.
  Header writes, Question patch and submitted disable may emit C callbacks.
  `onCallbackForm` patches its separate parent FormGroup accumulator; it does
  not assign/map a new original C input. C's getter-zero total and normalized
  question consequently do not overwrite the original child input/body.

The admitted consumer deliberately requires current submitted NORMAL Rupiah,
preceding inspected Induk, numeric-1 current selection, noncontradictory outer
selection and literal-null prior/last-submitted inputs. Independent continuous
original root/Main/C/control history is still required. The pending shared
final snapshot must preserve that history through the final seal. This static
invariant does not claim that a synthetic fixture observed application-owned
callbacks, nor does B's proof itself provide C permission.

## Guarded consumer and observer dispatch / exact remaining integration

`observe_forms` now calls `_observe_l10c_projection`; `apply_projections` now
dispatches `_apply_l10c` for `corporate-l10c-v1`. These are real call sites, not
another uncalled projector. They require positive exact configured loaded
CIT/MAIN/VENDOR pins, reviewed id-ID/Jakarta environment, the original enabled
C child, selected current submitted NORMAL Rupiah route, prior observed Induk,
current numeric-1 IsTransactionWithRelated and noncontradictory outer selection,
literal-null preceding form references, the exact no-footer five-column grid,
and the independently sealed manifest C capability.

The consumer obtains descriptions only through the existing shared
`CORPORATE_REFERENCE_REQUESTS` and `_project_corporate_catalog`. It binds exact
original sequence sets, all successful repeated packets, earliest original
catalog source per kind, selected label paths, original order/version/clock
provenance and all typed base Payload PeriodYear/TIN plus current Induk selection
operands. Caller-supplied label overrides refuse. Original question and the
nondisplayed nonzero total stay retained; no getter-zero or calculated footer
is invented. Mapping remains explicitly PARTIAL with all three unresolved
control identities.

`tests/test_corporate_l10c_consumer.py` is explicitly a **consumer unit seam**:
while the independent TX producer is absent from this branch, it substitutes
that producer interface in tests only. Its adapter/saved/reopened positives do
not establish production transport admission or the full populated real-browser
acceptance case. Production registry/catalog code is unchanged and unavailable
producer capability keeps whole-record fallback. Never cite this test as full
native producer/capture acceptance.

The parent supplied the reviewed committed B interface at
`686730a3cd9116ee490d84e8a590deed27aebee1`; its actual committed capture source
and the interface report were read. No B tree or uncommitted bytes were copied.
Parent integration must:

1. Add the actual requested `_l10c_history` handle to the existing fixed
   `_FINAL_LIFETIMES` synchronous Document snapshot, alongside L8/L7/B. Add exact
   reply key `l10c` and the same-turn final `clock` (no later clock RPC).
2. Run `_l10c_state(sample.get('l10c'))` for requested C **before** any optional
   unavailable/malformed-parent early exit, preserving every known-change
   fatality. Extend the exact reply key set rather than accepting arbitrary keys.
3. Extend the candidate argument/return tuple with C and narrow a previously
   offered C fact only when final state is available/complete and not sticky
   unavailable. An absent earlier candidate must stay absent.
4. Seal `corporate_l10c_lifetime` from that joint result, and bind end clock to
   the same final synchronous turn. Both live/held validators and mixed/absent
   event fingerprints are already implemented in this branch.
5. Remove the standalone C final sampler only as part of that reviewed joint
   integration. The current branch explicitly refuses C whenever a shared
   `_final_lifetimes` seam is present, or L7/L8 is requested; it cannot append a
   sequential probe behind B and accidentally seal stale siblings.
6. Exercise real dual-history mutations in both directions, final-parent
   changes, optional unavailability, Stop and late responses through the common
   JSHandle base (Document is ElementHandle, histories are ordinary JSHandles).

This report does not implement or approve the parent's combined merge or
protected contract. The full production-positive observer/capture/shared-catalog
adapter/held/saved/reopened test remains the coordinated acceptance blocker.

Milestone verification: `a2b6a03b849a0f8b742ddb9b9847b9ac180be25b`, run
`44036100797`, completed/success across portable, dependency audit, four Windows
shards, coverage/package/readback/bootstrap. Main-only provenance/cleanup were
intentionally skipped. That green verifies the independent lifetime milestone,
not subsequent framework/consumer changes; a fresh final-head run is required.

The guarded consumer/framework milestone `f7a10680ccd064093433a465f6a879cc4f7b6cd0`
then completed full workflow `44040700522` successfully: portable, dependency
audit, all four Windows shards, coverage/package and final aggregate gate.
Main-only provenance/cleanup were intentionally skipped. This executes the
actual provider excerpt/radio/paginator tests and the clearly labelled consumer
unit seam; it still does not supply the missing production shared producer or
joint C history. Subsequent hardening retains transient THEAD/TFOOT changes and
known changed child state even under malformed final wrappers; its new exact
head requires its own fresh full run, recorded in the PR body/readback.
