# Unifikasi footer spacer (PrimeNG empty tFoot row)

Baseline main: 03949e6 (PR #200 merge).

## Live evidence

Latest live run (build 42350905490, job 39e5a313, 2026-11-07 08:15-08:20 UTC):

- PPh 21/26 ordinal 1: `native_verified`.
- Unifikasi ordinal 2: observer passed (no `masa.observer_gate`,
  `json_observe` 6211ms) → now `adapter_ineligible`,
  reason `unverified_masa_footer_layout`. Both PR #200 blockers are gone
  (`fields`, `missing_masa_identity_ReturnSheetType`).
- PPN ordinal 3: `adapter_ineligible`
  (`unverified_ppn_final_balance_lifecycle`) — unchanged, out of scope.

Live CDP probe of the Unifikasi detail tFoots (counts only, no values):

- `list-i-bpu` (grid-a): no tFoot → observed `[]`, projected `[]` — matches.
- `list-i-bpnr`: observed `[[],[10,1,5]×4]` vs projected `[[10,1,5]]×4`.
- `list-ii-sp`: `[[],[6,1,4]×2]` vs `[[6,1,4]]×2`; `list-ii-cy` and
  `attachment-i` likewise with a leading `[]`.
- First tFoot row has 0 cells (`0:`); following rows have 3 cells with the
  expected spans. The empty row is the physical blank spacer.

PPh21 already models this spacer: `project_pph21_footer` returns
`rows=[[]]` and `footer_spans=[[]]+…` with comment "physical blank spacer
separate from body rows", and its fixture expects `[[],[4,4,1,1,4],…]`.
Unifikasi `project_unifikasi_footer` starts `rows=[]` with no spacer.

## Fix

Mirror PPh21 for Unifikasi only: in `project_unifikasi_footer`, start with
`rows=[[]]` and return `footer_spans=[[]] + [list(spans) for …]`. The
`list-i-bpu` early return stays `[]` (no tFoot, no spacer).

`TABLE` JS is unchanged (observer stays faithful to the physical tFoot),
and PPN footer projection is unchanged (no live empty-row evidence; PPN
remains blocked at the balance lifecycle first).

The workbook consumer already skips the spacer:
`_unifikasi_footer` continues on `values == [] and widths == []`, so the
leading `[]` does not reach sheet rows.

## Tests (CI-only; RED by source)

- `test_masa_json_unifikasi_footers`: leading `[]` now part of `footer` and
  `footer_spans`; `list-i-bpu` still exactly `[]`.
- `masa_observer_fixture.table()`: Unifikasi tables gain the live-shaped
  empty leading tFoot row (`<tr></tr>`); PPN tables unchanged. Observer
  assertion becomes `[[],[2,1]]` for Unifikasi, `[[2,1]]` for PPN.
- `masa_projection_fixture`: Unifikasi grid spans gain the leading `[]`
  (except `list-i-bpu`).

## Verification

- CI: full green on the PR head, then merge.
- Live rerun on the merged EXE (SHA256-verified): expect Unifikasi
  `native_verified`. If it still refuses, the next adapter reason names
  the following gate; fix second, never by relaxing without evidence.
