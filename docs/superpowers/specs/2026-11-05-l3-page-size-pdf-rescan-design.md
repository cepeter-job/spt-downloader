# Corporate L3-B page size 500 and lazy PDF discovery

Baseline main: ae6af1aa56283337e1d85875e350f6ba19596d90 (PR #184 merge).

## Evidence

Live SPT Badan run (PR #183 build, json-first → DOM fallback, PARTIAL
exit 2, 6.5 min):

- L3-B table (form 4, table 3): 9 pages / 2,250 rows in 184.5 s, then
  `table.elapsed_budget` at the 180 s table budget. Per-page timing is
  server-bound (click ~8–12 s, grid fetch ~8–13 s; renderer ~100 ms at
  250 rows), so page size — not renderer cost — dominates.
- Financial PDF discovery found 0 attachment tables
  (`pdf.discovery` no_control), where a direct DOM run found 3. The
  scan runs once immediately after the Induk tab click + `wait_idle`;
  lazily rendered grids can appear after the overlay clears.

## Design

- L3-B page-size cap 250 → 500 via the existing inspected dropdown
  path (`maximize_page_size` already picks the largest offered option
  within the bound and degrades gracefully when 500 is unoffered).
  The bound check and DOM cursor now trigger at `>= 250` with the
  caller's cap, so existing 250-cap cursor tests keep exercising the
  cursor path. The 180 s budget, totals and custody proofs are
  unchanged; tables still incomplete at the budget stay PARTIAL.
  At live pace (~20 s/page) 500 rows/page fits tables up to ~4,500
  rows in one run. Partial-table resume across runs remains future
  work.
- `download_financial_attachments` rescans for up to 10 s (500 ms
  polls, Stop- and document-aware) while no attachment table/control
  is observed at all. Present-but-unbound tables are definitive
  refusals and are never polled. Only the final scan's observations
  are recorded.

## Verification

Synthetic delayed-render financial test (table inserted 1.5 s after
load is still downloaded), updated page-size cap tests (4654 rows in
10 pages at 500; 1000-row preselection downsized; guarded refusal
above 500), full CI, then live GUI rerun.
