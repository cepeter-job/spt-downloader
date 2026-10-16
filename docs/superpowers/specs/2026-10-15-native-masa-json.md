# Native Masa JSON — approved design

## Acceptance
The user approved native JSON values for PPN and PPh Unifikasi before PR #20 merge. DOM is limited to inspected read-only navigation, labels, structure and pagination verification. Require response-derived values, verified taxpayer/return/year/period/model, complete form/grid coverage, `detail_source.used == 'json'`, and local JSON-versus-DOM/template parity. Fallback is not acceptance. Preserve corporate and DOM paths; no PPh21 JSON expansion.

## Constraints
- Observe UI requests only: no guessed/replayed API endpoints, mutation or remote document generation.
- Preserve literal identifiers, duplicate rows, null/zero distinctions and raw response evidence. Display transformations require reviewed bindings and JSON-path provenance.
- Unknown build/schema permits explicit fallback, not native success. Identity/auth/privacy contradictions fail closed independently of eligibility.
- Commit only synthetic tests/source/docs. Taxpayer evidence stays private. Tests/product imports/builds/executable verification run on GitHub runners; authorized local live observation/acceptance is separate.
- Preserve original outputs/untracked work. Extend only the explicit worker packaging allowlist.

## Verified public builds
PPN `/returnsheets/id-ID/640.36c042afd2381189.js`: SHA-256 `4a7e33826b6d0395afb23372fb6b4a9d4be6abaab0ec25fa743c897d0e654aef`.
Unifikasi `/returnsheets/id-ID/693.4de61c6eb2000c7e.js`: SHA-256 `2694fdda5c23b7d5f0eefe0cf0a0c55caa0fe29acc590363f34684ed90188fe0`.

Observed PPN prefill: `/returnsheet/api/prefillreturnsheet/nvat`; grids `/returnsheet/api/loadndvat/{la1,la2,lb1,lb2,lb3,lc}-grid` and `lc-grid/footer`. Observed Unifikasi prefill: `/returnsheet/api/prefillreturnsheet/withholding-tax`; grids `/returnsheet/api/loadwtr/{list-i-bpu,list-i-bpnr,list-ii-sp,list-ii-cy,attachment-i}-grid`. Match captured packets; do not issue direct requests.

`DetailJsonCapture.bind_detail_page` binds provenance, not semantic form paths. Traverse/wait for actual Masa forms before draining responses.

## Required mapping tests
1. PPN initialization overrides `ExportOfTangibleGoods` with `A1FormListOfExportTaxableGoodsOrServices.Total` after mapping `ExportTangibleTaxableGoods.SellingPrice`. Trace later calculations rather than using name similarity.
2. PPN Normal model renders previous/amendment STLG controls null. Preserve this distinction and raw source provenance.
3. Unifikasi `IncomeTaxes` is a tree; rows use `TotalIncomeTaxByGovernment`, footer uses `TotalIncomeTaxByGoverment`. Preserve hierarchy/order. Public UI translates top-level `Article` to `Pasal` and `Section` to `Ayat`.
4. Verify all grid columns, ordinals, formatting, reference-data labels and footer spans from the public component definitions; empty captures cannot certify populated mapping.
5. Declaration controls can depend on user claims rather than response JSON. Do not use credentials/claims to fabricate response provenance; unresolved dependencies prevent unjustified complete/native claims.

## Delivery
Verify PPN January and populated February, and Unifikasi January, in DOM/native JSON. Compare source values, templates/layout, row completeness, provenance and original-file hashes. Independent review and exact-SHA CI success precede merge. Deliver the verified main-build Windows ZIP and checksum.
