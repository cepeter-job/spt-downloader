# L10-B non-display custody — implementation boundary

This implements the operator's newer decision **“Tetap tanpa sheet B/D;
lanjutkan pembuktian custody non-display”**, not the display-layout proposal
in #277. That docs-only PR remains open and unmerged. This implementation
must not be described as a completed L10-B worksheet or live acceptance.

## Closed supported subset

`corporate-l10b-nondisplay-v1` requires the actual loaded CORPORATE/MAIN/VENDOR
script providers, positive exact SHA equality against `load_build_pins()`, the
selected ordinary Rupiah ICT_RCIT/ICT_RCITR submitted Normal/NORMAL literal
`?view=true` route, preceding Induk, explicit null PreviousFormData and
LastSubmittedFormData, and original numeric-literal **1** on BOTH outer Payload
and current MainFormData IsTransactionWithRelated. Original outer TIN/PeriodYear
must be present and agree with the already validated selected/current identity.
A present L10bFormData must contain exactly the fifteen reviewed Question keys,
each a JSON boolean. Missing/null, numeric/string substitutes, extra keys,
predecessors and unreviewed models remain refused; false is never empty/null.

The public 525 source is the same SHA reviewed in #277
(`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`). Its
`mapFormData` assigns the original root (offset 2651161), `jm` passes that root
and outer baseFormData to the child (2622937), and the child round-trips the
fifteen booleans through JSON.stringify/JSON.parse (40474/42461). No display
representation or radio selection is read or emitted here. The initial parent
setter (2648646) and later MainForm callback (2695904) both use
IsTransactionWithRelated. The only main-control assignment is the original
setFormData patch (2795046); the later getRawValue callback preserves it. The
setter's numeric-one branch enables the attachment; only its zero branch clears
L10BForm (2705414). Requiring both original ones excludes that clearing branch
without assuming a quiet timer, reading Angular state or borrowing another form.
These offsets are evidence in the supplied public bytes, not runtime proof.

## Own same-attempt lifetime

Optional manifest-only `corporate_l10b_lifetime` / `corporate-l10b-spa-v1` has
closed identity keys and literal-true fresh_root/fresh_form/stable_root/
stable_form/enabled_boundaries facts. Its independent structure-only history is
armed on the retained list Document **before View**, with neither corporate root
nor L10-B host present. It retains original root/form identities and actual
owned enabled tab/panel boundaries, detects transient removal/replacement,
duplicates and disable/re-enable, and refuses unknown custom-form ancestry.
The relevant-structure budget is 4096; browser query/observer allocations are
not claimed as a hard memory cap. It reads no input/checked/business values.
Final sealing now samples every requested retained L7/L8/L10-B history and the
coarse parent/Document binding together in **one synchronous browser RPC**,
inside the existing late-response drain fence. Earlier per-child reads are only
candidates, not final authority. Missing/unavailable proof cannot authorize the
new branch; known changed custody remains fatal. Old captures and unrelated native capabilities remain
readable. Both live and held readers reject descriptor overrides and validate
the manifest fact; absence-inclusive packet fingerprints reject mixed evidence.

## Custody is not presentation

Keep the original dump table **unchanged**, with no placeholder fields, empty
replacement table, sheet or template/resource edit. The versioned provenance
report retains all fifteen typed original booleans in original source order,
all consumed identity/lifecycle metadata, positive presence facts, exact
Payload versus CurrentFormData container, path, response sequence and attempt.
Raw response/manifest bytes and held replay remain authoritative.

The native dump gate accepts L10-B only with this independently reconstructed
report, exact configured pins, same-attempt final event/lifetime and the exact
unchanged original table. A name, display exclusion, arbitrary SHA, dummy field,
empty table or incomplete report never grants permission. Other forms' dump
gates are unchanged. `_display_sections`, workbook proof/index namespaces and
historical links are untouched: new workbooks still omit literal L10-B/L10-D,
while private checkpoints and published original JSON keep their custody.
No worksheet mapping-complete claim or new transport/reference permission follows.

## Review findings and correction

The earlier successful run **44022505547**, head
`d69e050dd964a4a34f9888bce43949ff6e37f21e`, is historical synthetic evidence,
not clearance of the two independently confirmed review findings:

1. **P1 — stale sibling custody.** The earlier drain sampled L7 before later
   L10-B parent/child RPCs. A pure L7 structural change in those RPCs required no
   network event, so the local request/sequence fence could not invalidate the
   already-positive L7 fact. L7 also had an older post-sample parent-probe window;
   the combined profile added later opportunities, rather than creating that
   older window. Reordering sequential samples only transfers the defect.
2. **P2 — earlier non-primary event.** A legitimate earlier admitted catalog
   shared the attempt, frame and manifest lifetime. The dump gate tried that
   event first and returned false on its sequence mismatch before considering
   the actual primary bound by the report.

The correction keeps the existing child-specific histories and typed manifest
contracts. `_FINAL_LIFETIMES` receives only their actual retained handles (or null
for an unrequested child) plus the retained Document. It drains each history and
reads the existing coarse parent structure in one synchronous turn. There is no
await, new page-side registry, speculative sibling capability or supplied
boolean authority. `_final_lifetimes` can only **narrow** already-produced
candidates; it checks changed child states before optional-unavailable exits.
Only local Stop, binding/sticky-state, pending/sequence checks and file I/O follow
that final RPC. L8 handle acquisition now retains its result before the
post-RPC Stop check, matching L7/L10-B cleanup ownership.

The report gate first selects exactly one positively typed original response
sequence with the report's attempt/route, then requires the original primary
POST, both strict lifetimes, typed source reconstruction, exact pins, positive
presence facts and the unchanged raw table. Missing, mixed or duplicate/conflicting
bound evidence is refused; it does not generically skip contradictions to find a
passing event. No transport, original-data, worksheet or native-profile contract
is broadened.

Focused synthetic coverage lives in:

- `tests/test_corporate_l10b_final_snapshot.py`: actual negative-L7 AND L10-B
  observer bindings, real MutationObservers, network-free structural mutations
  during final B evaluation, the inverse window, last-parent mutation,
  unchanged dual-positive held replay, and late optional L7 unavailability that
  cannot be dropped to accept native.
- `tests/test_corporate_final_lifetimes.py`: final snapshot/parent/child refusal,
  optional unavailable/malformed states, known-change priority, Stop, late JSON
  and excluded-MIME replies, acquisition and cleanup. Its protocol-only
  all-history case is not admission of mutually exclusive L7/L8 source profiles.
- `tests/test_corporate_l10b_nondisplay.py`: legitimately admitted catalog-before-
  primary adapter-to-gate positive, strict report sequence/attempt and duplicate
  event negatives, and refusal to rebind primary values to a catalog event.

The first hosted test run **44029879973** established P2 RED, but its first
P1 hook targeted only the Document subclass rather than the plain history
handles. Those P1 failures are **not** accepted as reproduction evidence. The
corrected test hooks their shared JSHandle base, asserts that all three handles
are intercepted, and independently requires the real history to witness the
injected mutation outside production's unavailable-driver exception policy.
The short superseded run **44032703379** was cancelled by that test correction.
Corrected hosted **RED: run 44032924361**, test-only head
`ca32bd66d0ecf4569fb69e7793fee67ed1603afd`. The real B-evaluation and last-parent
L7 mutation cases both failed with `DID NOT RAISE JsonSafetyError`; the unchanged
and inverse cases passed. The catalog-before-primary positive failed at the dump
gate. The complete four-shard JUnit readback contained 249 focused cases, 27
expected failures across the new final-snapshot/cleanup and report regressions,
zero errors/skips. That run exercised unchanged production, before the correction.

Final exact-head GREEN, run/head identities and downloaded four-shard JUnit
readback belong to the verification ledger on PR #282. Local AST/source
inspection is never reported as executed RED or GREEN.

## Verification and outstanding deliverables

Tests are synthetic and **GitHub-runner-only**: strict admission negatives,
all-false/all-true custody, loaded-provider pins, independent continuous-history
browser fixtures, both held readers, final-drain late response, original JSON
publication and saved/reopened workbook absence. Local checks are AST/source/
diff only; no local product imports, pytest, browser fixtures, builds or EXE runs.
CI status is recorded on the implementation PR, bound to its exact head.

The protected **AGENTS.md update is a separate outstanding parent deliverable**
after reviewing the combined shared boundary. This document does not replace
that update or claim approval-protected contract completion. Application-owned
build-matched live acceptance, other forms, mapping, PDF and whole-run completion
remain independent and unproved here. No private values or captures are uploaded.
