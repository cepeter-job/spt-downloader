# JSON L3 and MPN repair

The 3 November build-matched capture on main 920ca01 retained original JSON but
fell back at L3, captured only part of DOM L3-B, and timed out on MPN Clear date.
The goal is to remove these bounded implementation obstacles without certifying
unproved source, output completeness or live speed.

## Source and design

The reviewed corporate asset SHA256
fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d
creates a third, standalone p-table immediately after grid1 in group A. Its
header-only two rows contain RefundDeductionCreditOverseas and
TotalIncomeTaxPaidOverseas. The two data-grid observer omitted that structure.
Accept this exact additional structure, including header captions/spans and
control names, without reading business values. Reject arbitrary extra tables,
changed ownership and changed snapshots; retain legacy two-table captures. An
optional fixed proof marker identifies the reviewed standalone layout on replay.
The existing scalar projection and unresolved template fields stay unchanged.

For the existing 250-cap owned DOM cursor, combine the global loading-overlay
wait and 180ms settling interval with its existing atomic snapshot RPC. Each
attempt waits at most 1000ms before returning pending, preserving Python Stop
checks, the original owner/Document/URL, exact state and original table deadline.
Keep the original45-second loading bound across pending slices as well.
Other table paths retain their existing waits. This reduces remote calls; it is
not a claim that the unmeasured source of host/transport latency is solved.

Use the existing five-second actual-action timeout for the uniquely inspected
MPN Clear date click, bounded by preparation's original 45-second deadline.
Never retry the real click, accept an old reply, or proceed after Stop or sticky
source/Document refusal.

## Alternatives and boundaries

Ignoring extra tables would lose structure proof; increasing table deadlines
would only defer PARTIAL. Both are rejected. Keep the 250-row cap, 180-second
table budget, exact ten-row native grid requests, original source pins,
identity/privacy/catalog gates, financial PDF custody and output contracts.
Tests and builds run only on GitHub runners. Only synthetic fixtures enter Git.
The author implements inline; one fresh whole-branch reviewer gates merge.

## Acceptance

Hosted regressions must cover the reviewed standalone structure, malformed and
unrelated extras, no business reads, original byte replay, delayed one-shot MPN
clicks and deadline/fatal/Stop behavior, and reduced owned DOM wait RPCs with
identical rows, duplicates, totals and partial results. Full exact-head CI and
latest-main interaction review precede merge. Live acceptance remains separate.
