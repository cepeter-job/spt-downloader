# Badan L1-D: absent 5322 must follow the pinned renderer

Date: 2026-11-10
Status: approved by operator; implement fix, regressions and hosted CI
Baseline: main `4402575`, including implementation PR #215 (`4e84bfb`).

## Verified root cause

The build-matched live run passed the classification gate but refused native
with `missing_corporate_l1d_account`. Original retained source contains exactly
the reviewed 31-code set minus `5322`, with 30 unique nodes. Missing does not
mean a zero amount.

A new authorized, read-only browser probe of the same submitted return fetched
active main/corporate/vendor bytes and matched the existing pins. Its enabled
owned L1-D first table has 34 physical body rows, each ten cells, and one footer.
The probe read owners, headers, row/cell counts, spans and element tags only;
no business values, checked state or Angular component state.

Pinned source chain:

- `setFormData` takes the existing `L1dTreeData`. The default `Grid1Data`
  constructor does not fill missing captured nodes.
- `getTreeNodeByAccountCode` returns undefined when absent; `addStyleTreeNode`
  returns undefined for a missing node. `flattenGrid1` pushes that result in
  its fixed `5322` slot.
- Vendor `pTableBody` in the ordinary row path selects
  `I ? ct.template : ct.dt.loadingBodyTemplate`. The financial grid supplies
  no loading-body template. The missing node emits no physical row, not a
  zero-valued or labelled blank row.
- Existing captured/reconciled normal or migrated totals remain authoritative;
  no missing-row rule authorizes changing any stored amount or other account.

Public-source byte sites, zero-based in retained UTF-8 JS: corporate
`setFormData` at 1465617; `setGrid1DataMap` at 1466050;
`getTreeNodeByAccountCode` at 1475408; `addStyleTreeNode` at 1476044;
`5322` flatten push at 1477650; financial table binding around 1482934;
vendor ordinary row-outlet ternary at 2314539. The default `Ca` tree itself
also omits `5322` (its `5321` constructor starts at 1407129), but is not used
as a per-node repair of the captured tree. All 34 live rows were additionally
confirmed visible and all cells unspanned.

Exact reviewed SHA-256:

- `525.32c49782948fc5ef.js`: `500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`
- `main.bed1449c3647a8ca.js`: `ad856c925cddef51d84d49de2027cdb558ef64c0fbd7d4ecac630d54118c5b44`
- `vendor.c32c4ee39d966e30.js`: `6458fddb0ca985860e262293ea1251518f44df497dec987f58ae79eae110d173`

## Narrow admission

1. Keep the complete 31-code/35-body-row branch unchanged.
2. Add an explicit versioned omission-layout proof only when the same owned
   first table has exactly 34 physical body rows of ten unspanned cells and
   existing exact groups/headers/footer spans/three source pins. Read structure
   only. Preserve original ownership, enabled pre/post, route and Stop checks.
3. Require that proof and enabled visibility proof for the omission branch.
   Source must be exactly the reviewed code set minus `5322`, no duplicates,
   other missing or extra accounts. Preserve every schema, mask, numeric,
   total, balance and lifecycle check. Marker with a present `5322` is refused.
4. Emit only the 34 rendered body rows: no invented account object, `5322`
   label, placeholder or zero. Retain every original leaf and response byte.
   Record the omission rule separately in projection provenance, never as a
   fabricated raw leaf/path.
5. Missing/unknown/null/contradictory proof, bad rows/cells/spans, another absent
   code or multiple absences keep whole-record fallback. Old missing-5322
   captures lacking the new structural proof remain ineligible.
6. Keep the approved template unchanged: it already has the original 34-row
   layout. Verify saved/reopened mapping and the existing present-5322 dynamic
   growth/amount77 behavior.

## Verification

Write regressions first; obtain actual RED on hosted CI. Cover Normal/Amendment
and migrated booleans, current-Induk classification, exact 34-row output,
unchanged inputs/raw bytes and real-leaf provenance; negatives for proof,
other/multiple missing accounts, duplicates/extras, masks, unsafe arithmetic,
footers and balances. Exercise the actual owned synthetic observer, Stop,
changed route, disabled/rebound owners, row/cell/span defects and a DOM-value
read trap. Held-custody replay must preserve eligibility, coverage, sections
and provenance. Save/reopen/verify the workbook and audit.

Product tests/imports/browser fixtures/builds run only on hosted CI. Require
independent review and all exact-head checks. Badan acceptance still needs a
new build-matched live `native_verified`. Historical PARTIAL, PDF, capture and
publication gates remain independent; never rewrite them as successful.

No general optional-account policy, guessed zero, missing-row backfill,
completeness bypass, DOM business read, template change, PDF fix or performance
work belongs in this change.
