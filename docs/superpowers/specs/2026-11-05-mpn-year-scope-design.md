# MPN year scope via header PeriodCode

Baseline main: f550d9be44adf094b40efe6b63f1c097f315bae5 (PR #182 merge).

## Evidence

Live runs proved the MPN list inventory is all-years for large
taxpayers: one run paginated 373 list pages and captured 3,723
parents / 7,091 detail rows (~72 minutes), then hit the 4,096-file
evidence budget (`MAX_RESPONSES`) and degraded to PARTIAL. Only
1,032 canonical rows were in the SPT scope year (2025); 6,059 detail
rows were excluded after capture.

Two server-side scoping paths were investigated live:

- **TransactionDate year filter** — unsafe. In captured evidence,
  287 of 2,231 in-scope detail rows (PeriodCode year 2025) carry a
  TransactionDate in 2026. A calendar-year date filter would silently
  drop them.
- **PeriodCode (`#filterPeriodCode`) dropdown** — single-select live
  (selecting one range closes the panel and fills the field with that
  one range; options are period ranges back to 1939, searchable).
  Year 2025 needs 13 exact codes (12 monthly + annual
  `01122025`), which one selection cannot express.

Captured evidence also proves the header is a safe scope proxy for
this taxpayer: across 3,730 parents, header PeriodCode year always
equals its details' year (0 exceptions, 0 multi-year parents).

## Design

The header PeriodCode becomes the canonical scope, replacing the
detail PeriodCode in `project_payment`:

- The unfiltered list inventory is unchanged (only `IsCancelled=0`;
  the default TransactionDate interval is still cleared in `open()`).
- The collector opens a parent's detail dialog only when the header's
  PeriodCode year (digits, `period_code_year`) equals the SPT scope
  year. Out-of-year parents keep their list evidence; their dialogs
  are never opened. A malformed header code is treated as in-scope
  and captured.
- `project_payment` gates on the header year (full `period_year`
  validation with the captured catalog for in-scope rows). A
  divergent detail period can neither rescue an out-of-year header
  nor condemn an in-year one; its code must still be well-formed.
- Held custody re-proves out-of-scope parents from the same header
  year digits before accepting COMPLETE: a parent without detail
  bindings is complete only if its header year is a valid different
  year. In-year or malformed headers without details still refuse.

## Verification

Synthetic collector/custody tests: mixed-year inventory captures
details only for in-scope parents and certifies COMPLETE; removing
an in-scope parent's detail bindings still refuses; malformed header
codes are captured (unresolved → PARTIAL). Full CI, then live GUI
rerun expecting ~25–30 minutes and COMPLETE for the same taxpayer.
