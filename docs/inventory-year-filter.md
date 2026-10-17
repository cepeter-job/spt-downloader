# Inventory speed: source-side period-year filtering

## Scope and delivery order

This change is independent of native PPN JSON export (PR #30). Build and merge inventory acceleration first, then integrate it into PR #30. Do not import PPN-native feature changes into this branch.

The requested year remains the existing tax-period-label scope, including cross-year labels and validated migrated period codes. Do not substitute submission-date filtering, assume twelve monthly periods cover a year, or narrow the selected tax types/statuses implicitly.

## Required behavior

1. Derive period codes from verified source metadata before filtering the submitted list. Catalog coverage must be explicit; a virtual dropdown's visible options are not a complete catalog.
2. Bind a source-derived multi-period filter to the selected taxpayer, list status, request sequence, offset and page size. Reject returned rows that contradict it, including when metadata rendering falls back to DOM.
3. Reconcile filtered totals and every page against the same filter. Persist enough filter context to restore the selected record safely before opening a detail. Preserve duplicates/amendments and all existing identity checks.
4. Unsupported status endpoints, year bases or incomplete metadata must not silently lose returns or produce a false COMPLETE. Retain a clearly reported correctness-preserving fallback where optimization cannot be established.
5. Keep the native PPN exporter, monetary values, templates, authentication boundaries and user-owned CI unchanged.

## Evidence and limitations

A bounded authorized live experiment established that the submitted endpoint accepts the shipped grid serializer's two-value OR-equality form and returns exactly the union of two complete single-period baselines. The mode is constructed by appending `-equals` for each constraint, not by assuming a generic `in` mode. Only aggregate, non-private evidence belongs in this repository.

This establishes a request capability, not complete year coverage. Full reference-catalog coverage, migrated/cross-year periods, large constraint sets, pagination and selected-row restoration remain acceptance gates.

## Implementation sequence

1. Validate the shipped OR-equality request shape before metadata fallback, including empty responses. This slice has runner RED evidence and a successful correction run.
2. Add a pure year planner and owned-request rewriting contract in `coretax_inventory.py`. Plan disjoint candidates: codes containing the requested year, plus source-catalog label matches whose codes do not contain it. Retain ambiguous catalog labels as candidates so local scope validation can report them. A missing/expired/conflicting catalog or unsupported year basis uses explicit unfiltered fallback. Keep the existing local `in_scope` check.
3. Add browser integration with read-only PERIOD-cache evidence, a narrowly guarded submitted-request route, effective-request provenance, fixed filters across pagination, per-partition totals and cancellation cleanup. Unknown endpoints retain existing collection. Persist and restore the exact filter and page size before selected-row navigation; include filter identity in the active group key.
4. Exercise synthetic browser contracts on runners: rewritten-body binding, empty partitions, changing totals/filters/catalog, stale offsets, catalog failures, cancellation, amendment/deduplication, and detail restoration. Verify the managed-worker allowlist includes the new module. Close the live acceptance and review gates below before marking ready.

## Verification and merge gates

- Publish synthetic RED contracts and verify their failures on GitHub runners before implementing the corresponding production changes.
- Require exact-final-tree Windows/portable tests, packaging, security/dependency checks and independent review. No local product imports, pytest, fixtures, builds or EXE self-tests.
- Exercise a bounded read-only live inventory comparison with explicit scope and unchanged prior outputs. Measure requests/pages rather than claiming a speedup from source inspection alone.
- Resolve review findings and mark the PR ready only after all applicable gates pass. Merge this PR before updating PR #30; do not bypass protections or merge a draft.
