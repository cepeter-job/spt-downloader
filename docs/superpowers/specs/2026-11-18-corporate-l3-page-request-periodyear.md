# Corporate L3: page request carries PeriodYear, not Language

Status: implementation candidate. Live acceptance of the real record remains
pending; this records the fix for the `unsupported_corporate_l3_page_request`
fallback observed on a real submitted corporate SPT.

Date: 2026-11-18. Extends the L3 native branch without widening any other form.

## Live evidence

Local job `97003f04b67143a381f95c2a9139dc48` (PPh Badan, Normal, SUBMITTED,
json-first) fell back to DOM with
`detail_source.reason = unsupported_corporate_l3_page_request` after the Induk
and L2 fixes cleared.

The captured `loadcit/l3-table-b-grid` page requests carry exactly:

`ReturnSheetRecordId, PeriodYear, First, Rows, SortField, SortOrder, Filters,
LanguageId`

with `PeriodYear = "2025"`, `LanguageId = "id-ID"`, `Rows = 10`,
`SortField = "WithholdingSlipsDate"`, `SortOrder = 1`, `Filters = []`. There is
no `Language` key.

## Root cause

`_apply_l3` required `Language == 'id-ID'` and rejected any other key set, so
the live `PeriodYear`-bearing request failed the shape guard and refused the
whole record.

## Fix

Mirror the already-approved L4 page-request contract: the L3 page request key
set is `{ReturnSheetRecordId, PeriodYear, First, Rows, SortField, SortOrder,
Filters, LanguageId}`, and `PeriodYear` must equal the last four digits of the
record's `TaxPeriodCode` (the same `period[-4:]` check L4 uses). `LanguageId`
stays `id-ID`; `Rows`, `SortField`, `SortOrder` and `Filters` are unchanged.

## What does not change

- The L3 grid/footer/reference bindings, row schema, ordered totals, dates and
  every other form.
- Whole-record DOM fallback for genuinely unsupported profiles.

## Verification

`tests/test_corporate_l3_native.py` builds the page request with `PeriodYear`
and the `language` defect now mutates `PeriodYear`; all L3 suites pass.
