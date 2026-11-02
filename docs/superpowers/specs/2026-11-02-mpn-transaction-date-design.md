# Owned Accounting transaction-date clear

The user requested fixes for the two observed live failures and directed MPN
first while Returnsheets live access waits. This bounded bug fix uses the
existing runtime/UI flow and does not change source or completion admission.
Baseline main:8f67b4f96ae65eed2faaca98925379872c058a9c.

## Evidence and approach

The2November run refused both Search responses with date_filter_present,
period widget present and period clear absent. Live inspection of the loaded,
matching Accounting main/vendor pins finds a different control:
ui-input-date contains p-calendar#filterTransactionDate with input#TransactionDate
and a sibling button[type=button][aria-label="Clear date"] with .pi-times.
Both belong to one .input-date-container.p-inputgroup inside the owned table.
The pinned initial Search introduces TransactionDate/between. Its owned Clear
date updates the form; its immediate request can still contain the old filter.
The following inspected Search produces the original request without that date
filter. No business input values, framework component state or browser cache
were read for this conclusion. No endpoint was constructed or replayed.

Retaining period-only clear cannot remove the actual date filter. Accepting a
filtered query or rewriting its POST would weaken inventory proof. Choose a
single inspected TransactionDate Clear date before the existing second Search.
Only a source query with exactly that date rule and the already accepted
IsCancelled rule qualifies this new action. Other filter shapes retain refusal.

## Supported boundary

Require the current pinned Accounting attempt, one owned ui-grid/p-table, one
calendar with the exact ID, one input ID, one ui-input-date and its exact direct
container/button/icon ancestry. Reject duplicate calendars/containers/buttons,
foreign input/metadata, hidden or disabled actions. Never read control values.
Missing calendar retains the existing legacy period preparation path. An
ambiguous present date control must not fall through to another clear control.
Do not click date clear after the final Search or retry an actual clear click.

Keep the shared45-second preparation deadline, retained Document/attempt,
Stop and sticky source/observer failures before/after RPCs and before actions.
Only the final owned response satisfying the unchanged unfiltered non-cancelled
predicate can supply inventory. An immediate stale clear response is not proof.
Keep two Search actions maximum, original source pins/catalog policy, no extra
fetch, request budgets, final drain, row custody and PARTIAL/publication gates.

## Verification and remaining scope

Use synthetic browser behavior tests on GitHub runners: reproduce sticky dates,
including a stale clear response; successful complete/empty inventories;
unchanged filter refusal; malformed/foreign/duplicate/hidden/disabled controls;
one actual clear; two Search actions; Stop and sticky failures outrank clicks.
Keep the complete existing test inventory. Review latest main/other-session PRs,
run exact-head full CI and verify the package before live acceptance. A manual
UI investigation is source evidence, not proof the new application build works.
L3-B performance and existing mapping/catalog gaps are separate work.
