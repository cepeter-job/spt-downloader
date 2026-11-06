# Issue #156 — MPN owned-grid response count refusal split

Date: 2026-11-06. Scope: synthetic diagnostics only, based on main
`bdcbf2e1ebb80f29e6901f40c4a27f4e5fa4a76f`.

## Grounded live evidence

An operator-initiated exact-build run on 6 November ended MPN/overall
PARTIAL after around 30m31s. The first fixed-category warning was
`mpn.observer_refused` with `mpn_observer_reason=response_count`,
`mpn_paginator_kind=list`, followed by `mpn.capture_failed` at
`parent_inventory`. The private response cannot be classified further
from the existing log and is not copied into the repository. PPh 21/26
capture was COMPLETE, while MPN capture was not. The approved original
reference catalog was also not observed; passive `path_variant` is
still untrusted.

## Precise existing refusal predicate

The `AccountingObserver.on_response` callback previously grouped:
1. Invalid or unavailable literal `Payload.TotalRecords` integer.
2. An owned posted `First` offset greater than `TotalRecords`.
3. `len(Data)` different from `min(posted Rows, TotalRecords - First)`.
4. Non-object entries in the `Data` list.

Each is terminal and still raises the original
`MpnUnsupported('MPN page count does not reconcile')`, except invalid
numeric literals, which continue to raise the existing bounded-integer
`MpnUnsupported`. The generic public `response_count` label did not
identify which predicate failed.

## Bounded change

Emit only the **first** fixed reason in `mpn.observer_refused`:
- `response_total_invalid`
- `response_offset_exceeds_total`
- `response_row_count_mismatch`
- `response_row_shape_invalid`

The 4 new reason strings are explicitly allowlisted by both the
observer and privacy-safe diagnostic schema. The old `response_count`
enum remains accepted for compatibility with historical diagnostic
records but is no longer emitted by these four predicates.

No numeric totals, offsets, row values, source URLs, private payloads,
exceptions or taxpayer identities are included in diagnostic events.

## RED → GREEN proof

`tests/test_mpn_response_count_diagnostics.py` exercises actual
owned list and detail observer callbacks, with 18 negative cases and
2 positive acceptance cases. Before implementation, **18 failed**:
every refusal still reported `response_count`; 2 valid-response
cases passed. After implementation, all pass. The earlier
`tests/test_mpn_observer_refusal_diagnostics.py` regression now
expects `response_row_count_mismatch` for its previously generic
synthetic count failure.

Expanded MPN source-custody and pagination tests and the exact-head CI
must pass without relaxing source ownership, period filtering, parent
identity, original request literals, strict page-size constraints,
Stop behavior, or PARTIAL classification.

## Remaining boundaries

This is observability, **not** a production scraping-speed fix.
The next separately authorized exact-build MPN run must show which
category occurs, and original owned source evidence should be
inspected privately before any behavioral change. An independently
missing approved reference catalog remains a separate gate. Do not
blindly retry or increase page size.
