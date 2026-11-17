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
Final sampling is the last browser RPC inside the existing late-response drain
fence. Missing/unavailable proof cannot authorize the new branch; known changed
custody remains fatal. Old captures and unrelated native capabilities remain
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
