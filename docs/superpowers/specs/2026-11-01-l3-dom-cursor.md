# Bounded L3-B DOM pagination cursor

The 1 November worker log verified 1500/4654 L3-B rows in 193.9 seconds,
then retained PARTIAL under the existing 180-second cooperative deadline.
Completed page events account for only 93.1 seconds. Repeated full-state reads,
next-control lookups and the pre-click phase are outside those page timers.
Authorized live inspection of the same selected return found 250 rows/eight
columns; the unchanged full projection took 19–21 ms in the browser. This does
not reproduce the worker's headless scheduling latency or prove live completion.

Reduce avoidable browser round trips and repeated raw-state transfer only in
the already admitted `max_page_size=250` corporate L3-B path. A private JSHandle
retains the original owner, Document, literal URL and full exact state strings.
It is not page-global storage, a source cache, native admission or new output.
Combine the fresh state/repeat check, original owned-next checks and one click
in one RPC. Poll with booleans and compare the final atomic snapshot against
the same exact seen states inside the browser. Transfer captured cells once;
do not transfer duplicate state text. Dispose the cursor on every exit.

## Required boundaries

- Preserve CELL_JS, GROUP_JS and TABLE_JS projection semantics.
- Preserve the existing 250 cap, 180-second table deadline and max_pages.
- Preserve Stop, ordered duplicate rows, footer once and source-count checks.
- Preserve original paginator visibility/ownership/disabled checks and one click.
- Refuse replaced owner/Document/URL, ambiguous table and repeated full state.
- Preserve PARTIAL on uncertain action/read, timeout or exhausted budget.
- Retain the generic <=100 path and all native, mapping, PDF and MPN gates.
- Bind a conservative browser-side deadline once; never refresh it per page.
- Run product tests/builds only on GitHub runners; commit synthetic data only.

## Evidence and acceptance

Real Edge fixtures must prove identical rows and fewer raw-state transfers,
including repeated states, owner changes, cancellation and delayed execution.
Existing browser safety, actionability and timeout tests must continue passing.
Exact-head CI/package evidence does not certify a successful live full scrape.
Review preceding other-session merges against current main before integration.
