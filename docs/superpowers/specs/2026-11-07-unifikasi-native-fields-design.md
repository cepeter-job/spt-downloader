# Unifikasi native JSON: paginator fields + ReturnSheetType identity

Baseline main: a67f2e4 (PR #199 merge).

## Live evidence

Latest live run (build 42322609832, job 4f08418c, 2026-11-07 05:37–05:41 UTC):

- PPh 21/26 ordinal 1: `native_verified` (JSON-first works).
- Unifikasi ordinal 2: `masa.observer_gate=fields` → `detail.source=forms_unavailable` → DOM fallback.
- PPN ordinal 3: `adapter_ineligible` (`unverified_ppn_final_balance_lifecycle`) — separate lifecycle issue, not in scope.

Captured Unifikasi primary (`withholding-tax`, 6-response attempt, complete):

- Outer Payload keys: FormData, IsFound, Name, PeriodCode, PeriodEndMonth,
  PeriodStartMonth, PeriodYear, ReturnSheetModel, ReturnSheetStatusCode, TIN,
  TaxpayerIdentifier — **no `ReturnSheetType`**. FormData (25 keys) also has
  no `ReturnSheetType`; family is endpoint `withholding-tax` + TIN/period/status.
- PPN `nvat` primary does carry `ReturnSheetType` (and PPh21 `article-2126`
  carries none either, but `_check_pph21_primary` never required it).
  The Unifikasi `_check_primary` requirement for `ReturnSheetType=ICT_WTR`
  can never pass live; like PPh21, Unifikasi must not gate on it.

Live CDP probe (controlled Edge, logged-in Unifikasi detail, tab-activated):

- INDUK FIELDS: OK, 11 fields (Masa Pajak ui-dropdown + 10 inputs/radios),
  no empties.
- DAFTAR-I / DAFTAR-II / LAMPIRAN-I FIELDS: `null` (fields gate).
- Candidate enumeration per form (visible, panel-owned, outside tables):
  INDUK 11; DAFTAR-I 4 (ui-dropdown, TaxIdentificationNumber, 2× P-DROPDOWN);
  DAFTAR-II 4; LAMPIRAN-I 3. The P-DROPDOWNs are paginator
  rows-per-page selectors: inside `.p-paginator` + `p-table`, exactly one
  `.p-paginator-current` marker, inside the reviewed grid element
  (`rshshr-list-i-grid-a/b`, `rshshr-list-ii-grid-a/b`,
  `rshshr-attachment-i-grid`). The inner p-dropdown of the ui-dropdown
  Masa Pajak control is deduped via `seen` and is not a candidate.

Root cause: `FIELDS` in `coretax_masa_observer.py` exempts paginator
`p-dropdown` only for PPN forms `A-1…C`. Unifikasi appendix forms contain the
same paginator shape inside the form root (grid component nested in form),
so every Unifikasi appendix form fails at `fields` before any grid is
observed. PPN passes because its paginator grids sit outside the form
elements it evaluates — the exemption there is a no-op for the same shape.

## Fix

1. **FIELDS paginator exemption (Unifikasi):** extend the existing
   paginator allowlist branch to `PPh Unifikasi` forms
   `DAFTAR-I, DAFTAR-II, LAMPIRAN-I` (INDUK has no grids and stays
   excluded). Keep the shape checks unchanged: `p-dropdown`, inside
   `.p-paginator` and `p-table`, exactly one `.p-paginator-current` in the
   paginator. A business `p-dropdown` outside a paginator still returns
   `null` (fail-closed); `INDUK` paginator-shaped controls still fail.
   No new diagnostic: the existing `masa.observer_gate=fields` continues to
   cover refusals.

2. **Unifikasi primary identity:** drop the `_check_primary` requirement
   `_identity_field(payload, 'ReturnSheetType', 'ICT_WTR')` for
   `PPh Unifikasi`. Keep the PPN `ReturnSheetType=VAT_VATR` check (PPN
   payload carries it live). Family proof for Unifikasi is retained:
   `source_tax` from the prefill endpoint (`withholding-tax`) already
   raises on family mismatch, plus TIN / PeriodCode / PeriodYear /
   PeriodStartMonth / PeriodEndMonth / ReturnSheetStatusCode checks and
   the listing binding (`TaxTypeCode=ICT_WT`,
   `ReturnSheetTypeCode=ICT_WTR`). No field is newly trusted; the removed
   check was a false expectation proven absent by live bytes, mirroring
   the PPh21 primary contract which never required it.

## What does not change

- Fail-closed to DOM is unchanged; the observer still refuses unknown
  structure. PPN `unverified_ppn_final_balance_lifecycle` stays open and
  is not fixed here.
- No diagnostic event/enum changes. No values, offsets, identities, or
  payloads are recorded.

## Tests (CI-only execution; confirm RED by source)

- `masa_json_fixtures.payload('PPh Unifikasi')`: remove the synthetic
  `ReturnSheetType` (live shape). Update
  `test_unifikasi_json_identity` wrong-lifecycle expectations: a mutated
  `ReturnSheetType` can no longer refuse (field ignored); `DRAFT` status
  still refuses.
- `masa_observer_fixture.table()`: add a visible paginator `p-dropdown`
  (rows-per-page selector) inside `.p-paginator`, matching live shape.
  Before the FIELDS fix, Unifikasi observations fail at `fields`; after,
  they observe. Keep a negative: a `p-dropdown` outside a paginator
  still fails at `fields`.

## Verification

- CI: full green on the PR head, then merge.
- Live rerun on the merged EXE (SHA256-verified, `build-info.json`):
  expect Unifikasi `detail.source=native_verified`. If it still refuses,
  the next `masa.observer_gate` (or adapter reason) names the following
  gate; fix second, never by relaxing the refusal without evidence.
