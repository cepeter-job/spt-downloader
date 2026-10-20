# Bounded period-cache readiness

## Evidence and scope
The installed diagnostic established a missing PERIOD record during planning and a valid catalog after inventory. It does not identify when or why Coretax populated the cache. Improve only the opportunity to use an already available cache. No reference fetch, extra navigation, sleep/poll loop, cache writes, auto-selection or live retry.

## Decision
Preserve initial planning and all semantic/freshness gates. If the initial period-cache reader returns None, make one additional readonly read immediately before the first eligible submitted source is processed, after preceding sources have completed their already-authorized navigation. Each read retains the existing 5000 ms JS deadline (not an OS watchdog). Invalid nonempty catalogs and unsupported scope are not readiness retries. Reader exceptions keep safe fallback.

Only replace the not-yet-started submitted source with verified disjoint partitions. Preserve order, actual source list/progress totals, literal selection, request custody, partition validation and end-of-partition rechecks. Never replan a started source or rewrite earlier audit/checkpoints. A cache appearing only after submitted capture remains diagnostic-only in the final snapshot.

Cancellation checks bracket the extra read; CaptureCancelled propagates. Retry failure remains unfiltered, with no raw error values in diagnostic logs. Add only the finite readiness stage to the existing serializer allowlist.

## Verification
GitHub runners only: deferred real IndexedDB fixture, warm/absent/expired cache, failing second read, changed/expired partition recheck, Stop during reread, unchanged late-only diagnostic behavior, no additional navigation or unknown network, preserved selection and reconciliation. Existing Windows/portable suites and frozen package gates remain unchanged. All fixtures synthetic.

Permission covers code/tests and draft PR, not merge/install or live-account execution. No performance claim until separately authorized live comparison.
