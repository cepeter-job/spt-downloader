# MPN detail readiness diagnosis

The latest build920ca01 passes the inspected detail click, original response,
dialog and title gates, then refuses the detail grid at the shared five-second
deadline. The matching private checkpoint retains the acquired catalog and list,
one attempted parent and no persisted details. The log cannot distinguish an
absent/hidden grid from a visible grid whose checks finished after the deadline.

Under the operator's instruction to take the next step through merge, add only
the missing readiness evidence. This is a small diagnostic change, not evidence
that the live scraper is repaired.

## Approach

Use only count and visibility results already read by `_ready_one`. On its own
ambiguity/deadline refusal during detail dialog/title/grid readiness, emit one
fixed event with stage, last observed state, refusal category, entry budget and
elapsed call time. Set the fixed UI stage around those three existing waits.
Do not perform a follow-up DOM probe, read business values or retain a locator,
selector, exception message, URL, source body or taxpayer identity in diagnostics.

Changing the selector or extending the deadline lacks live evidence. Bypassing
grid ownership for JSON would change capture permission. Neither is included.
Keep exact selectors, RPC order, original five-second shared deadline, original
exception and Stop/safety precedence, click counts, whole-detail fallback,
catalog/TLS/source custody and PARTIAL/publication rules.

## Verification

Hosted RED/GREEN tests cover missing, hidden, ambiguous and late-visible owners,
pending Document identity, each fixed stage, successful readiness, Stop/safety
precedence, no extra reads/waits, logging OFF and closed-schema privacy. Real
synthetic Edge capture exercises missing/hidden detail-grid ancestry in DOM and
JSON-first modes and proves PARTIAL with one original detail click. Run full
unchanged CI on the final PR tree and obtain fresh review before merge.

The next operator-run live build will supply the missing structural category;
synthetic CI cannot determine the actual live grid state or certify MPN COMPLETE.
