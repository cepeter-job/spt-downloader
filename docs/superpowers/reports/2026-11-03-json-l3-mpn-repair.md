# Source-bound L3 and MPN capture repair

Baseline main faad237/PR175 was reviewed alongside PR174's native driver trust.
The original build-matched diagnostic evidence separated three obstacles:
native L3's table-count refusal, expensive post-pagination DOM RPCs, and a
one-second actual Clear date dispatch timeout during MPN preparation.

The corporate asset hash
fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d
was matched locally using static byte inspection. Its L3 template declares the
two data grids and an additional header-only p-table beside grid1 for the two
overseas controls. The observer now validates this exact owned structure on
both passes, including captions/spans, wrapper/ancestry and control metadata,
without business reads. Optional standalone_layout=overseas-controls-v1 is
validated on replay; old two-table proofs remain readable. Unproved extras
still fall back as a whole record. Existing scalar projection, unresolved
template mappings and native lifecycle gates are unchanged.

Only the existing250-cap DOM cursor combines overlay readiness and180ms
settling with its same-owner atomic snapshot RPC. Renderer waiting returns
pending within1000ms for Stop checks. The original45s loading and180s table
deadlines remain fixed across slices. Full states, duplicates, rows, footer,
source totals, one-shot clicks and partial/error handling remain intact.
Wall snapshot timing includes waiting; renderer extraction timing excludes it.
This reduces RPCs without claiming a measured full live speedup.

The uniquely inspected MPN Clear date now uses Search's existing5000ms actual
dispatch ceiling, still limited by the original preparation deadline. Only
trial readiness may retry. Actual dispatch, source/Document ownership, Stop,
sticky failures and exact clear-response/second-Search custody are unchanged.

## Hosted evidence

- Tests-only836c2a6, run41570176430/attempt1: three intended L3/DOM failures,
  nine passes; artifact13201246408.
- 96a8d48, run41570499498/attempt1: the corrected real parent-overlay fixture
  reproduces one-second MPN dispatch refusal; artifact13201446566. DOM
  regression failures are GREEN. The L3 fixture initially omitted source
  paginator type=button inside its new enclosing form; that fixture error was
  corrected without relaxing product ownership checks.
- b429b1b, run41571305963/attempt1: L3 observation/replay and MPN positive
  dispatch are GREEN. The pending-snapshot loading-deadline regression was RED,
  then repaired; artifact13200829539.
- 40638c9f1aaf9ac3b95846ec23350ea7ccf21a46,
  run41571620429/attempt1:295 passes, zero failures/errors/skips, including20
  new cases. Artifact13201916293, independently downloaded and reconciled from
  JUnit, SHA256
  1ab1964f457918ba6de6f70af1d9847a4fbc48e121cbd8c88a97a975147918a5.

The focused set includes L3 observer/native/projection/fallback, corporate
cursor/page-size/timing, MPN transaction-date and callback/fatality regressions.
The temporary isolated probe is removed; existing CI/coverage policies remain
unchanged. Full final-tree CI and fresh whole-branch review gate merge.

Independent whole-branch review atbc3a768 found one Important acceptance gap:
a browser snapshot could finish on time but reach or finish decoding at the
host after the original table deadline, allowing a final page to complete.
No Critical/Minor issues were found. Hosted RED run41573178167/attempt1 at
ec6143d reproduced three assertion failures: late final reply, late pending
reply followed by another RPC, and late decoding. Artifact13202466986 retains
that JUnit evidence. The fix rechecks the original host deadline before pending
retries and after decoding before appending rows, with Stop first.

Hosted GREEN run41573371050/attempt1 at
57a14263f57cef4578ed18c7bb72612747e91696 passed298 cases, zero failures/errors/
skips, including those three real successful-reply/decode regressions. Original
JUnit artifact13202705920 was downloaded and reconciled; ZIP SHA256
e572d4a70cebb73a67670aec7049b90adb478e104a4076abcb968e27c5cd6277.
The review fix pass is complete; full final-tree CI remains required. Its
separate temporary probe is removed as well.

## Interaction and limits

PR176 at b047f1f was reviewed and merged as main197e85d: it instruments `_ready_one` and
`detail_pages` for dialog/title/grid readiness refusals. That is later than this
Clear date preparation action. Preserve its diagnostic schema, observations,
shared five-second detail deadline and JSON fallback when integrating main.
Main197e85d was merged without conflicts. Static AST comparison confirms that
only `_clear_initial_transaction_date` differs from its AccountingUI; its
readiness methods are intact and diagnostics.py is byte-identical to main.
PR175's selection ranking/preset/search/manual-edit and consent boundaries,
and PR174's owned driver trust/cleanup/allowlist, remain unchanged here.

The old live primary lacks the independently required outer L3 lifecycle flag.
This change does not substitute its current-main flag or certify that old
capture native-eligible. Missing lifecycle evidence still requires whole-record
fallback. Source pins, literal identity/period/model, privacy, native/catalog,
Induk/PDF, mapping, MPN completeness and publication are independent gates.
Synthetic GREEN is not build-matched full live completion, speed, or interactive
Excel acceptance. No product execution took place on the operator machine.
