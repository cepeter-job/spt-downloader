# Persist unmapped template identities

Baseline main: 0086584973ddb3ee6fc21ff3ee867d022faf014c (PR #185 merge).

## Evidence

SPT Badan live run 5 Nov 2026: the export's template mapping reported
unmapped counts per form (Induk 40 fields, L11-A 14, …) but the run data
kept only the counts. Listing the actual not-mapped values required
guessing from all captured values, because the engine computes exactly
which fields/tables were not placed and then discards the identities.

## Design

Every mapping report (Badan clean + raw-evidence paths, PPh 21/26, Masa
PPN/Unifikasi, PPN workbook fallback) now also carries
`unmapped_field_identities` (label, field, group) and
`unmapped_table_identities` (name, group, headers, complete, row_count,
body_row_count) — via one shared `_unmapped_identities` helper in
`coretax_template_cells`. Identities only, never values: values stay in
the job checkpoint. Keys are added only when unmapped content exists, so
COMPLETE reports are byte-identical to before. Resume/workbook readers
consume specific keys and are unaffected.

## Verification

New `tests/test_unmapped_identities.py` pins identity shape, the
no-values guarantee, and COMPLETE-report stability. Full CI, then the
next live GUI run produces the exact unmapped list in `run.json`.
