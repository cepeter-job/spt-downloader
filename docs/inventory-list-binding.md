# Inventory grid/auxiliary response isolation

> Scope update, 22 October 2026: new live inventory reads only the uniquely inspected SPT Dilaporkan navigation. The all-status traversal below records the earlier contract and remains relevant to interpreting old captures; it is superseded for new collection by [the current provenance contract](arsitektur.md#identitas-scope-dan-provenance). Observer isolation, literal identity, cancellation, pagination reconciliation, and catalog validation still apply. Old evidence is not rewritten to claim the new scope.

## Evidence and scope

A bounded authorized read-only inspection of the not-submitted page observed paginated POSTs to `/returnsheet/api/returnsheetsnotsubmitted/data` returning an empty grid, plus a separate POST to `/returnsheet/api/returnsheetssubmitted` whose body contains only `TaxpayerAggregateIdentifier`. The latter is not a paginated grid request. The existing observer accepts both, allowing the auxiliary response to replace the visible-grid result. Native acceptance also discovered the current route plus a trailing `#` as a second, empty-label status source; same-document navigation emits no fresh grid response.

These inventory failures keep the run PARTIAL even though the selected PPN native capture succeeds. Fix shared inventory separately from PR30. Preserve all-status completeness, literal taxpayer identity, cancellation, per-page reconciliation, original data and existing native PPN behavior. Do not turn PARTIAL into COMPLETE by suppressing genuine failures or by dropping real status lists.

## Contract

- Only an owned paginated POST with a nonempty taxpayer key, valid `First`/`Rows` and a list-valued `Filters` can advance the listing observer. An auxiliary response cannot overwrite the last grid or satisfy a fresh-response wait.
- The filter route may pass through the exact observed identity-only submitted read unchanged, for its already-validated frame and taxpayer. It must not rewrite or record it as filtered-grid evidence. Malformed pagination, different identities and arbitrary extra fields remain rejected before transport.
- Same-page anchors are not extra status inventories. Deduplicate fragment variants without changing literal taxpayer identifiers or inventing status endpoints. Keep real unknown status routes on explicit unfiltered capture.
- Keep expired/unverified catalogs on the existing explicit full-scan fallback. The shipped reference cache has a write-time one-day expiry but does not guarantee a refresh when a page loads; never manufacture fresh expiry or bypass the gate.

## Verification

Publish synthetic RED contracts first; inspect exact-head runner failures before source edits. Use real routed browser fixtures for unfiltered, filtered and expired-catalog collection with auxiliary traffic, unchanged auxiliary requests, strict negative request shapes and the same-page anchor. Require final full Windows/portable/build/security checks and independent review, then integrate the verified fix into PR30 and repeat the already-authorized native acceptance in a new output folder. No local pytest, product imports, synthetic exports, builds or self-tests.
