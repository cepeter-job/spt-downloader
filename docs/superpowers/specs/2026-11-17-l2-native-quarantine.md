# L2 native projection: safety quarantine and remaining proof

## Decision and status

PR #274 is **not a completed L2 projector**. Its original affiliate-only
implementation cannot establish equivalent output for the complete
`CurrentFormData.ListOfOwnership` owner. Reject every populated shareholder or
affiliate body. Retain the existing whole-record DOM fallback; do not remove
evidence, invent a `fields` marker, or weaken the dump gate to admit this draft.
The bounded empty-body helper is a partial candidate only, not native capture
permission. No merge, live acceptance, or template-resource change is authorized.

## Reviewed evidence

Read-only source review used `525.32c49782948fc5ef.js`, SHA-256
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`,
matching the configured entry in `resources/build-pins.json`. The local cache
filename is not authority: the bytes were independently hashed before review.
Source anchors are the L2 `fa`, `w1`, `q1` and `z1` classes and parent
`fillForm`/`mapFormData`. The approved workbook's L2 sheet was read as ZIP/XML
through its actual workbook relationship (not by assuming the sheet filename).

- Parent `mapFormData` assigns `formData.ListOfOwnership` to `l2FormData`.
- `z1.getFormData` returns `ListOfShareholders`, `TotalPaidInCapital`,
  `TotalPaidInCapitalPercentage`, `TotalDividend`, `InvestmentList`, `TotalDebt`
  and `TotalReceivable`. It writes `TotalPaidInCapitalPercentage: 0`, not the
  shareholder row sum. A closed source key inventory is necessary, not sufficient.
- `getGrid1DataMap` and `getGrid2DataMap` identify the saved controls, but
  `setFormData`/`setGridValue` populate distinct rendered grid models and
  recompute totals. `setGrid1DataMap` defaults null paid-in capital, percentage
  and dividend to zero, and TIN to null. Literal-null display is not generally
  equivalent to the original helper's blank handling.
- `CitrL2Grid1Columns` binds `Jabatan` to `FullPosition`, not to `Position` or
  `SubPosition`. In these exact bytes, `w1.getFullPosition(t, _)` looks up the
  Position's `CodeDescription` from the related-person reference type; its
  second argument is unused. The earlier PR's claim of concatenating two
  reference labels was inaccurate and is withdrawn.
- **Both** `CitrL2Grid1Columns` and `CitrL2Grid2Columns` declare `NEGARA` as a
  `Dropdown` using `CountryCode` and the country reference type. A payload code
  is not proof of the rendered description. This candidate owns no such catalog
  binding and therefore cannot output the code as if it were the country text.
- In block B, Rupiah investment/debt/receivable columns use `Number`, foreign
  money uses `Number2`, investment percentage uses `Number4`, and debt/receivable
  interest columns use `Number` (not `Number4`, despite the edit-dialog precision).
  The original two-decimal money/four-decimal interest renderer was unproved.
- `fa` totals reduce the rendered arrays in order. `setGridValue` writes those
  results into the form. Exact arbitrary-precision Decimal sums do not by
  themselves prove JavaScript Number/fractional-sum equivalence.
- Submitted `fillForm` restores the saved shareholder list after optional
  related-taxpayer prefill. Keep the shared submitted status/model guard; it
  does not supply missing catalog or rendering/lifecycle proof.

## Caption/control inventory (not a description mapping)

The approved L2 workbook has two blocks: A header row 2/body 3..8/footer 9;
B header row 12/body 13..21/footer 22. Compaction moves these rows on export.

| Block B caption | Saved control | Missing equivalence proof for populated rows |
| --- | --- | --- |
| NO. | rendered row ordinal | exact owned grid/order/duplicates |
| NAMA | Name | saved-to-final lifecycle |
| NEGARA | CountryCode | owned dropdown description, never a raw-code shortcut |
| NPWP/NIK | TIN | literal identity plus null conversion |
| PENYERTAAN MODAL / NILAI (Rp) | Investment | Number, currency and precision |
| PENYERTAAN MODAL / % | InvestmentPercentage | Number4 and Excel percentage-point semantics |
| UTANG / NILAI (Rp) | Debt | Number and ordered reduction |
| UTANG / TAHUN | DebtYear | literal rendered string/type |
| UTANG / BUNGA UTANG/TAHUN | DebtInterest | Number, not edit-dialog Number4 |
| PIUTANG / NILAI (Rp) | Receivable | Number and ordered reduction |
| PIUTANG / TAHUN | ReceivableYear | literal rendered string/type |
| PIUTANG / BUNGA UTANG/TAHUN | ReceivableInterest | Number, not edit-dialog Number4 |
| JUMLAH (G/J) | TotalDebt / TotalReceivable | final rendered-array reconciliation |

Block A is an independent unresolved body, not an optional display appendix.
Its name/address/country/TIN/job-title/capital/percentage/dividend rows must not
be removed merely to pass the native dump gate. No supported populated profile
is claimed, including rows with null/empty country codes or integral amounts.

## Implemented conservative boundary

1. Validate the exact owner root key set and each body container independently.
2. Nonempty `ListOfShareholders` refuses with
   `unprojected_corporate_l2_shareholder_body`; nonempty `InvestmentList` refuses
   with `unverified_corporate_l2_affiliate_rendering`. This includes malformed
   nonempty rows and preserves all original response/checkpoint bytes.
3. The empty-only helper accepts each body as literal null or an empty list and
   each of the five explicit totals only as unsigned numeric zero with the
   closed `0`/`0.0...` grammar. No null-to-zero synthesis, strings, booleans,
   signed zero, exponent conversion, fractions or nonzero totals are admitted.
   Block B's empty reductions render as zero; no populated row is projected.
4. `_apply_l2` requires a positively valid configured CIT digest and exact
   equality with the observed digest, plus the literal captured route, original
   root path, no unowned grids/responses/dependencies, and submitted/model guards.
   Missing/malformed pins cannot match a missing asset.
5. Preserve the **entire** original dump, all body leaves and all totals. Keep
   `fields=[]`, `projection_complete=False` and
   `projection_reason=unprojected_l2_owner_rendering`. Therefore even an
   adapter-eligible empty candidate still fails the existing capture dump gate.
6. Carry the partial marker into the L2 mapping report and Indonesian resume
   Audit note. Keep unresolved counts based on retained real evidence rows.

## CI diagnosis and verification boundary

Historical head `ea2c7743c7d78ec0d9d66755ba6f88f0c8701f50`, run
`44016592247`, failed only the L2 workbook test in Windows shard-2, job
`133816157107`: it chose block A's first `JUMLAH` at G4 and expected block B's
2500. The aggregate/package-skipped error was downstream, not the cause.
The footer test now locates block B's actual approved header before its total;
it does not change the exporter to satisfy an unscoped assertion.

Regression tests were added first for both populated-body refusals and positive
configured-pin equality (commit `ef6c156`); source inspection confirmed those
refusals/equality were missing. No local product imports, pytest, source/frozen
self-tests, browser fixtures, builds or EXE execution are permitted or claimed.
Local checks are AST/source and public workbook/bundle data only. Actual
execution, coverage, saved/reopened workbook and package evidence must be bound
to the final GitHub head/run, not inherited from an earlier green.

## Follow-through source contract (2026-11-17)

The quarantine above describes `corporate-l2-v1` and remains its contract.
A separate whole-owner slice is being built tests-first; it does not silently
reinterpret old proofs or certify live acceptance.

### Independently pinned consumer evidence

Both cached source files were independently rehashed against
`resources/build-pins.json`: CIT SHA `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`
and MAIN SHA `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`.
Decoded-source anchors: CIT `fa` at 2194813, `w1`/`q1` immediately after it,
`z1` at 2234943, submitted `fillForm` at 2647k, `Um` at 2618k and
`onCallbackForm` at 2695011; MAIN offline body at 3878k, footer at 4179k,
reference service at 3036k and `RELATED_PERSON_TYPE` at 2929784.

**Correction:** `Number` is not `NumberInteger`. Offline body `Ue` and footer
`ga` invoke `number` with no digitsInfo. The pinned MAIN Indonesian locale
pattern is `#,##0.###`, with comma decimal and dot grouping; the returnsheet
provider supplies `id-ID`. Offline `Number2` explicitly uses `1.2-2/id` and
`Number4` uses `1.4-4/id`. This is distinct from the online grid's
`numberformat_ignoreprec` path. Both L2 interest columns and every money
footer use ordinary Number. A no-rounding supported subset can therefore
admit finite binary-exact JSON numbers with at most three effective decimal
places for Number and four for Number4, refusing any conversion, ordered
partial sum, precision or representation that cannot be proved exact.
Foreign-currency/oil-and-gas profiles do not have approved Rp destination
headers and remain unsupported, not relabelled as Rupiah.

### Complete saved-to-render chain

1. `fillForm` establishes submitted status, parses Current/PreviousFormData,
   and maps the original ListOfOwnership object to `l2FormData`. RelatedTaxpayers
   may tentatively prefill shareholders, but submitted status restores the
   original shareholder list before the child binding runs. `Um` supplies the
   outer primary as `mainFormData` and `l2FormData` as `formData`.
2. `z1.ngOnChanges` runs `getDataFromMainForm` before `setFormData`. The separate
   prefill branch requires the literal outer CurrentFormData string `"{}"`;
   an admitted nonempty decoded owner cannot enter it. `setFormData` restores
   both lists, then calls `setGridValue(0, A)` followed by `(1, B)`.
3. `setGrid1DataMap` null-defaults TIN to null and the three A numeric controls
   to zero, sets FullPosition to null and copies Position/SubPosition and
   optional ValidFrom/ValidTo. `setGrid2DataMap` null-defaults only TIN, copying
   all B amounts, rates, year strings and IsEditable literally.
4. The valueChanges callback emits `getFormData`; the parent patches only
   `citrForm[L2Form]`. It does not replace `l2FormData`. The child keeps the
   original owner reference; its oldFormData comparison therefore does not
   restore intermediate callbacks. Submitted disables editing.
5. All five getters reduce the rendered arrays **without an initial seed**.
   Empty/null lists yield numeric zero. A numbers are already null-defaulted;
   B singleton null Debt/Receivable yields null (blank Number footer), whereas
   two nulls sum to numeric zero. Subsequent null-plus-number contributes zero.
   Preserve this distinction; an unconditional Decimal sum starting at zero
   would be wrong. Percentage is the ordered sum plus `%`, parsed by the parent
   and rendered by `toFixed(4).replace('.', ',')`; the saved percentage alias is
   literal zero and cannot be used as the displayed total.
6. Saved money totals are overwritten by `setGridValue`, never the inputs of
   these displayed getters. Retain original typed saved totals independently;
   rendering/reconciliation must name the ordered row operands rather than
   pretend a stale saved alias was displayed.
7. `w1.ngOnChanges` asynchronously assigns FullPosition using only Position's
   first matching `RELATED_PERSON_TYPE` description. MAIN `_Xg -> di` proves the
   exact kind. SubPosition is copied but unused. Country's offline Dropdown
   instead uses `codeDescAsync -> getReferenceDataDescription -> active-version`
   selection. These are different consumers: a unique-Code Position subset can
   reuse the shared catalog producer safely, but duplicate Position versions
   must not inherit country's active-version semantics.

### Shared producer and completion boundary

The shared catalog owner alone owns passive transport classification/admission.
L2 needs original same-attempt COUNTRY_CODE and RELATED_PERSON_TYPE bytes and
exact endpoint/method/sequence, order/version/clock custody through existing
`reference_packets` / `_project_corporate_catalog`. It does not need
RELATED_PERSON_SUBTYPE. No endpoint is guessed, no cache is read and no catalog
fetch is forced here. The exact interface request is recorded separately for
parent coordination. Native observer/adapter/held/workbook acceptance remains
an independent next slice; a pure helper alone never enables native capture.

## Concrete blocker to completing L2

Need a reviewed end-to-end L2 branch that owns actual country and Position
catalog bytes/order/version provenance, exact source-to-render transformations,
all shareholder and affiliate rows/duplicates, rendered totals, currency/locale,
null/fraction precision and lifecycle callbacks. Then exercise native observer,
adapter, held replay and saved/reopened full workbook against a same-record DOM
oracle. This PR does not fetch a reference, inspect Angular state or business
values, add endpoints/probes/timers, alter resources, edit AGENTS, or loosen the
capture gate. A green quarantine build is not completion of the user's L2 form.
