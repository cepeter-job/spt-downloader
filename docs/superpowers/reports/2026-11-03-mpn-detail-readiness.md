# MPN detail readiness evidence

The build920ca01 live failure reaches the inspected detail action, owned original
response and dialog/title gates, then refuses `ui-grid p-table` at the shared
five-second readiness deadline. The matched checkpoint contains the acquired
`adapter-get-v1` catalog and list, one attempted parent and no persisted details.
These facts localize the failure but do not identify the actual live grid state.

The change adds only fixed diagnostic evidence at existing refusal points:
dialog/title/grid stage, last observed count/visibility category, deadline versus
ambiguity, remaining budget at call entry and elapsed call time. A visible final
observation after the deadline still refuses capture. No diagnostic browser RPC,
selector or timeout change, new action/request, business-value logging, output
metadata change or capture permission is introduced. Existing Stop and sticky
safety precedence, JSON fallback, TLS/catalog custody and PARTIAL gates remain.

## Hosted regression evidence

The first tests-only run41567695648 found15 intended unit failures and four
browser fixture setup failures because the scratch job directory was absent.
The fixture was corrected before production code changed.

Corrected RED run41568226259, attempt1, at
0a8e878e5ff7dcbf70d9eb914f6a1a6c15aa850b ran26 new cases:19 expected failures
from missing diagnostic events, seven passes, no errors/skips. The browser
cases first establish PARTIAL, zero persisted detail rows and one original
detail action, then fail on absent telemetry. Downloaded JUnit confirms this.
Artifact13200370485 has API ZIP digest
2a00fec1227cbf51fc29d1728d62d1d3178e1475c9a57e3bdf2ead2dd3098fd0.

GREEN run41568400736, attempt1, at
8f572c8aedf291d6aa924b630ad5c875db0c273d passed310 cases with no failures,
errors or skips:22 readiness unit, four real synthetic Edge readiness,74
existing capture browser,63 reference acquisition,54 source custody and93
diagnostics cases. Downloaded JUnit independently reconciles those counts.
Artifact13200009912 has API ZIP digest
05f387cd7dbddd490d778317ba5061f1d5ee984b7d0e20ea8b32c5ee800a33c7.
The temporary workflow is removed from the final candidate.

## Merge interaction and limits

Baseline main920ca01/PR174 and successful main run41562794711 were reviewed.
PR174's owned Windows driver trust manager, explicit environment preservation,
cleanup, local factories, worker allowlist and TLS verification are untouched.
PR173's fixed one-GET acquisition, five-second bound, source pins, Document/
scope and original-byte evidence remain intact. Local AST inspection confirms
only `_ready_one` and `detail_pages` changed within AccountingUI.

Fresh review and full final-tree PR CI are separate gates after the focused
proof above. Refresh latest main/preceding merged PR before merge. These are
synthetic runner results, not proof of the actual live layout or MPN COMPLETE.
No live product execution, tests, fixtures or builds ran on the operator machine.
