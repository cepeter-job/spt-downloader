# L3-B renderer timing prerequisite

Status: proposed for review; no production implementation or new release.

## Intent and evidence

The current main is `d7fc64ce3940eefa4b22da7a2b3da9c9e194659a`.
Its latest explicit-DOM worker verified 2000/4654 corporate L3-B rows in
193.410 seconds and retained PARTIAL under the original 180-second cooperative
deadline. Advance and snapshot RPC wall time account for 64.461 and 64.120
seconds across seven accepted transitions. These measurements do not distinguish
execution inside the renderer from dispatch, scheduling, serialization or
transport outside that measured function.

Authorized headed investigation followed the submitted list's inspected View
into the same selected corporate return. A read-only row/state/packing probe
on 250 rows took approximately 23-44 ms in several observations. A later probe
took 285 ms. The separate original group/actionability probe took about 3 ms
on a settled page. An observed transition also kept the browser busy for many
seconds; a sampled profile includes Angular view creation, checking and styling.
This headed/component evidence is not an exact worker benchmark or a complete
capture. It does not establish a new optimal page size.

The pinned L3 column uses `l3bcit`: its async caption branch falls back to the
literal source value while the caption is null/undefined. Observed pages changed
from literal ARTICLE23 to its displayed caption as the async work finished.
Preserve original captured strings; this proposal adds no label normalization.

## Recommended approach and alternatives

Add function-local renderer elapsed times to the two existing cursor RPCs,
alongside their existing Python wall timings. This is a diagnostic prerequisite
for the requested performance repair, not a claim that the timeout is fixed.

Changing page caps or deadlines now would not resolve the missing measurement.
Live size comparisons were exploratory and lacked a request-bound freshness
proof; in particular, the 25-row readiness predicate could accept the old page.
Increasing the 180-second deadline or admitting new API/native paths is outside
this change. Keep all current capture and identity decisions intact.

## Exact change

- Only successful `TABLE_CURSOR_ADVANCE_JS` results (`status=advanced`) and
  successful cursor `TABLE_VERIFIED_JS` results (`packed` present) carry an
  internal `renderer_ms` measured by function-entry/exit `performance.now()`.
- Preserve the inner checks and action ordering. Refusal, budget, done, error
  and generic non-cursor result shapes remain unchanged. Do not catch errors,
  retry actions, add a second click, update a deadline or persist raw state.
- Emit optional `table_advance_renderer_ms` and `table_dom_renderer_ms` on the
  existing accepted `table.page_timing` event. Existing `table_click_ms` and
  `table_dom_ms` remain wall measurements. Initial-page events stay compatible.
- Reuse the existing diagnostic numeric policy: exact int/float only,
  0..604800000 ms, rounded to two decimals. Missing/invalid measurements are
  omitted and do not change capture results. No coercion of untrusted values.
- The difference between wall and renderer duration includes unmeasured
  dispatch, scheduling, serialization and transport. Do not label it as pure
  queue time or sum nested phase durations.
- No workbook/checkpoint/source metadata changes and no raw values, taxpayer
  identifiers, URLs, headers, bodies, cache contents or credentials in telemetry.

## Boundaries and verification

Keep the exact owned corporate L3-B admission, <=250 selection, original owner,
Document and literal URL, full exact states, one inspected Next, Stop, max_pages,
180-second deadline, row order/duplicates, footer and source-total reconciliation.
Generic <=100 capture, native eligibility, PDF, MPN and publication are independent.

Product tests, browser fixtures and packaging run on GitHub runners only.
Tests must distinguish synthetic pre-RPC delay from synchronous renderer work,
prove the timing fields stay private-safe and optional, and preserve capture
contents plus the existing refusal/deadline/cancellation regressions.

Before merging, refresh main and review the preceding other-session merge
(currently PR163), its functions/tests/contracts and interactions. Require a
fresh whole-branch review and exact-head CI, then verify the merged-main package
and copied hashes before delivery. The next live worker run remains necessary
to identify the long boundary and choose a performance fix.

## Separate MPN finding

Live Accounting main/vendor original-response hashes match their existing pins.
The observed neighboring reference GETs were ShowZeroValue, IsDebitIsCredit and
ShowCancelledTransaction. They do not prove a variant of the required four-type
catalog. The source can reuse its reference cache and omit a new catalog GET;
the inspected grid search did not observe that required GET. No browser cache
was read and no catalog fetch was forced. This does not establish what happened
in the earlier worker attempt. Keep its genuine three-field refusal fatal and
leave reference admission unchanged in this proposal.
