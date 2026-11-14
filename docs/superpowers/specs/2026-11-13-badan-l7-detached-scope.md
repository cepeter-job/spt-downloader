# Badan L7: scope the detached-ambiguity refusal to the corporate chain

Date: 2026-11-13
Status: proposal — implementation not started; no admission change yet.
Baseline: main `01cbe66`, including diagnostics PRs #251, #253 and #254.

## Verified root cause

Live runs on the official main builds (#251, #253, #254) request `json-first`
for Corporate and fall back to DOM with
`detail_source.reason=unverified_corporate_l7_raw_negative_lifecycle` on every
attempt. The named predicates are now precise and consistent:

| Field | Live value |
| --- | --- |
| `corporate.l7_history_arm` | `clear` — no corporate root/L7 host in the document when the optional history is armed, before the inspected View click |
| `corporate.l7_capture_gate` | `js_detached` (sequence 42 of the run) |
| `corporate.l7_negative_gate` | `structure_start` (sequence 43) |
| JS state at refusal | `available=false`, `changed=false` |

`_L7_HISTORY` keeps `investigate → adopt` scoped for retained roles, but its
ambiguity branch is not scoped:

```js
const scope = inside(element) || inside(target) || roles.includes(element);
if(scope){ relevant=true; adopt(element,index,removed); }
else if(!target.isConnected){
  // A detached intermediate's historic generic-table owner is unknown.
  relevant=true; if(debit())unavailable();
}
```

Any removed `p-table`/`table` whose mutation target is already disconnected
sets `state.available=false`, even when the removed subtree has nothing to do
with the corporate return or the L7 form. Angular tears subtrees down
incrementally: during the list→detail transition and during unrelated grid
re-renders a table is removed from a wrapper that is itself detached, so the
branch fires. Once `available=false` the observer disconnects and the optional
proof can never be produced for that capture attempt — `changed` stays false
because no retained role contradicted anything.

Consequence: the strict L7 raw-negative capability introduced by #235 has never
been reachable in a live run, regardless of the L7 DOM itself.

## Proposed rule

Refuse ambiguity only where it can affect the L7 chain:

1. `roles.includes(element)` and `inside(element)` / `inside(target)` keep their
   current meaning and keep refusing when a retained role (or its remembered
   ancestors) is removed or replaced — that path already sets `changed`.
2. A detached candidate that is not attributable to the corporate root is not
   L7 evidence: ignore it (no debit, no `unavailable()`).
3. A candidate whose removal target is a retained role or a remembered chain
   ancestor keeps the conservative refusal. A disconnected target can never be
   proven "inside" the retained root — `Node.contains` is false across a
   detached boundary — so only retained roles and remembered ancestors may
   refuse; everything else is unrelated teardown and is ignored.
4. The arming precondition (`clear`), the 4096 relevant-record budget, the
   root/form/grid/`p-table`/`table` retention, the uniqueness/hidden-duplicate
   rules, `enabled()` boundaries and every projection gate are unchanged.

Attribution is limited to what the observer can actually prove:

- retained roles and their remembered ancestors (`roles`, `ancestors`);
- the retained corporate root, when it is still connected.

A disconnected wrapper whose historic owner cannot be proven is therefore
ignored — the same conclusion the design already applies to unrelated row/text
churn, now extended to unrelated table teardown. No foreign component can lend
ownership: adoption still requires the candidate to be inside the retained L7
form, and the final snapshot still requires unique ownership over the exact
`rshshr-corporate-income-tax-return > rshshr-citr-l7-form > rsh-citr-l7-grid1 >
p-table > table` chain.

## What deliberately does not change

- No new endpoint, request, pin, preload or forced provider fetch.
- No new page property, timer or `WeakRef`; the observer stays a single
  `MutationObserver` armed before the inspected View.
- Non-negative `corporate-l7-v1` admission stays byte-identical; this rule only
  governs whether the optional negative proof can be offered.
- Missing/invalid proof still refuses; nothing is clamped, invented or zeroed.

## Verification plan

Hosted Windows browser fixtures (`tests/test_corporate_l7_history.py` style,
real Edge page in CI):

1. Synthetic corporate root + L7 form/grid/`p-table`/`table`, armed while the
   document is clear; remove unrelated tables from detached wrappers → history
   stays `available` and a later bind succeeds.
2. Remove/replace a retained role or a remembered ancestor → `changed` stays
   fatal (`JsonSafetyError`), as today.
3. Detached candidate whose removal target sits inside the retained corporate
   root → `unavailable` (`js_detached`), as today.
4. Full bind/sample/final-custody flow unchanged: the existing
   `test_corporate_l7_history.py` and `test_corporate_l7_negative_*` suites stay
   green with no expectation edits.

Live acceptance remains operator-owned: after merge, one official main build and
one live Corporate run must show `raw_negative_projection` present (native
`json-first` used) or name the next precise gate.

## Follow-up: corporate host wrappers in the chain (live `4d3b44a`)

After the detached scope landed, the live gate moved to
`corporate.l7_capture_gate=js_chain_foreign_2`: between
`rsh-citr-l7-grid1` and its `rshshr-citr-l7-form` owner the real DOM renders a
custom host wrapper that is not one of the generic transparent outlets
(`p-tabview`, `p-tabpanel`, `ui-grid-offline`).

Rule: a custom element whose tag belongs to the corporate component family
(`rsh-citr-*`, `rshshr-citr-*`, `rshshr-corporate-*`) is a host wrapper, not a
foreign business component, and may sit between a retained role and its owner.
Another `*-form` element and any unknown custom tag still refuse. Ownership is
still proven by `closest(owner)` plus the uniqueness check, so a host wrapper
cannot lend ownership from another component.
