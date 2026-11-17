# L9 recap-only candidate: recovery boundary

This implementation is **not full L9 native acceptance**. It fills six recap
slots for a narrow source-proven subset; all twelve detail grids remain
unresolved. The hybrid path must keep whole-record DOM fallback.

## Reviewed source and template

The local public source cache `525.32c49782948fc5ef.js` has SHA-256
`500e5aa4110d211c42ad4d901095e83ca0ae595791bc852a2cec12e00633b153`, equal to
`resources/build-pins.json`. No portal bytes or private records are committed.
Source character offsets below describe that exact UTF-8 bundle, not a new
runtime permission or an observed live capture.

* Around 2543184: the L9 form initializes its six numeric controls to zero.
* Around 2544761: `getFormData` maps six UI controls to the six recap payload
  keys and applies `Math.round` to `TotalTable1..12` only.
* Around 2545100: `setFormData` patches fiscal/commercial controls with `??0`;
  non-migrated initialization invokes all twelve `patchFooterGrid` callbacks.
  **Migrated initialization patches only `DifferenceDepreciation`**, not
  `DifferenceAmortizationIntangible`. The earlier PR description claiming both
  stored differences are authoritative was incorrect. Migrated sources refuse.
* Around 2551072 and 2551484: the two reductions sum the seven tangible/five
  intangible group operands, then subtract their corresponding commercial
  control. Captured results must already equal these fixed points.
* Around 2555842: `changeTotalCommercial` is attached to explicit input events;
  `attachValueChanges` emits the form result rather than inventing grid labels.
  Submitted controls are disabled by `ngOnChanges`/`setDisabledForm`.
* Around 2570500: template p-inputNumber controls use the explicit Indonesia
  locale and no-fraction min/max settings. Restrict to observed id-ID and safe
  integral values; this candidate never guesses fractional rounding behavior.
* The approved `resources/corporate_format.xlsx` has matching column-A recap
  captions at rows 226..228 and 259..261, with column-H numeric destinations.

The allowed operands are genuine JSON number tokens, integral and within
fifteen digits. Non-difference operands are nonnegative. Reconciled bounded
nonnegative sums prove each ordered addition exact in JavaScript; subtraction
of bounded safe integers is exact. Null/missing leaves, strings, bools,
fractions and unsafe magnitudes refuse instead of applying a guessed zero or
rounding rule. Typed original operands and the migration selector retain their
real response sequence, container and source path.

## Admission and custody

The observer only offers the recap capability for bytes matching the reviewed
CIT pin, not merely any caller-approved 64-hex build. The adapter independently
requires the exact positively valid reviewed digest, id-ID, exact selected
submitted `?view=true` route, manifest-owned component lifetime, preceding
observed Induk, current-only Normal source (explicit null previous/last source)
and explicit false/numeric-zero current migration control. Other branches keep
fallback. No additional endpoint, catalog fetch, write action or deadline is
introduced. Present malformed lifetime facts remain fatal in the existing
packet/held validators before this projector runs.

The root audit table and **all twelve** original grid inventories, including
duplicate leaf occurrences, remain in `section.tables`. `unprojected_grids`
contains all twelve names. The dump gate tests this marker **before** the
legacy reviewed-fields exemption, so six fields cannot hide the loss of full
grid projections or promote the candidate to native capture. Rendering carries
`projection_complete=False` / `unprojected_l9_grid_rows` into the existing
`derived_complete` / `derived_reason` mapping report and visible Audit note.
Unmapped table identities and row counts remain truthful. Approved clean
presentation omits raw appendices from sheets, not from checkpoints/custody.

## Unresolved scope

Every detail group (5 tangible + 2 building + 5 intangible) still needs its own
reviewed row/control schema, reference-backed label expansion, month/year
rendering, footer and lifecycle proof. This PR neither exports raw codes as
captions nor claims these twelve grids are mapped. Fraction/null/migrated,
amendment and wider taxpayer/build coverage remain unsupported here.

## Verification and policy blocker

Initial run 44015449642 failed only the existing grid-binding browser test:
its synthetic L9 root is an array, while the newly unconditional observer
capability attempted an object-only projection. Restricting the capability to
the reviewed projector pin preserves that fixture's original evidence-leaf
scope without relaxing any production gate.

Local verification is AST/source/data-only, with no product imports, runtime,
pytest, browser or build execution. Hosted tests exercise numeric boundaries,
closed proof/refusal cases, original duplicate leaves, real owned observer and
manifest-held replay, whole-record fallback and reopened workbook/Audit notes.
Exact-head CI results are recorded in the PR, not inferred from local checks.

An attempted protected `AGENTS.md` contract update was denied. That file remains
unchanged; this report records the supported boundary but is **not** completion
of the separately blocked protected-contract update.
