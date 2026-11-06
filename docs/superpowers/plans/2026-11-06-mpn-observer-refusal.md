# Issue #156 — MPN observer failure evidence and refusal classification

Date: 2026-11-06. Base: `main` at `f1fcbfd`.

## Observed boundary (private read-only run)

The current-build MPN live attempt ended PARTIAL during source-owned
`parent_inventory` pagination. Its protected traceback reaches
`AccountingUI._wait` → `AccountingObserver._check_state` →
`MpnUnsupported('MPN owned grid capture failed')`.

This establishes that the observer's `failed` flag was set before the
last-page wait completed. It **does not establish** whether the original
failure was network transport, an HTTP status, unexpected JSON/count,
or an unsupported request. The previous implementation discarded the
originating callback exception, and no fixed reason was logged.
A separate unobserved approved-reference catalog is still an independent
source-provenance gate; a passive path variant is **not** admissible.

## Targeted scope

- Retain the **first** non-safety MPN observer refusal category using
  literal, allowlisted tokens only. Emit `mpn.observer_refused` once,
  with fixed `mpn_observer_reason` and `mpn_paginator_kind` when known.
- Distinguish source-owned request shape or callback failure, transport
  failure, response request binding, HTTP status, content type, unreadable
  body, response shape, count and identity.
- On an owned-grid wait timeout, emit `mpn.grid_wait_timeout` with
  `no_request` or `pending_response` and grid kind, without changing
  timeout duration or final exception.
- Validate with real synthetic observer callbacks and the actual
  diagnostics store; ensure no private payload, filter, taxpayer ID,
  URL, exception message or request body reaches public logs.
- Preserve all terminal refusals, safety precedence, Stop checks,
  source ownership, original page sizes, retry policy, and PARTIAL
  publication. No new external requests or browser actions.

## Test-first evidence

`tests/test_mpn_observer_refusal_diagnostics.py` was RED on
`f1fcbfd`: eight refusal kinds lacked an event and two timeout states
lacked an event (the unsafe-identity guard already passed). After this
bounded implementation those cases pass without weakening existing
tests.

## Latency and remaining live acceptance

The latest live run required many source-owned 10-row parent pages
and terminated at an observer refusal after substantial collection.
There is **no trustworthy evidence** that an unreviewed paginator-size
selector can safely change to 25/50, nor evidence of which observer
callback originally failed. This PR intentionally **does not claim to
make scraping faster** or to make MPN live COMPLETE. Changing the
page-size control, retries, request format or source route before a
source-owned browser proof could silently corrupt pagination.

A separately authorized new exact-build MPN attempt should inspect the
fixed refusal category or wait state, reconcile original parent totals,
audit and output provenance privately, then select the smallest
test-first correction to the *observed* source failure. Keep #156 open.

No real taxpayer identities, original API paths, response bodies,
cookies or financial records are included in this repository document.
