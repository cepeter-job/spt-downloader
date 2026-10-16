# SPT optimization completion

## Approved scope

Finish shared fixture ownership, structural workflow contracts and the Windows
sharding decision. Changes must preserve application behavior, truthful output,
full Windows coverage, serial native/Tk execution per runner, exact artifact
readback, provenance and the required aggregate. Functional tax-feature drafts
remain independent. No release or live-account acceptance is included.

## Implementation and proof

- [x] Merge fixture-owner cleanup after unchanged inventory, native/GUI tests,
  package readback and independent source review.
- [x] Replace four whole-YAML substring tests with structured dependency/order,
  permissions, diagnostic and opt-in benchmark contracts. A test-only YAML parser
  belongs in the hash-locked test/build environment, never the runtime lock.
- [x] Prove invalid workflow mutations fail and equivalent YAML representations
  pass. Keep routing/gate behavioral tests and exact package checks.
- [x] Run at least five identical-source Windows benchmark comparisons, distinguish
  cold/restored cache observations and record total-runner/critical-path costs.
- [x] Adopt production sharding only when the full required workflow independently
  demonstrates the approved benefit with identical inventory and no weakened gates.
  Evaluation finished with an explicit retain-serial decision; no production
  sharding implementation is pending.
Final integration evidence belongs in PR #28: exact documentation-head CI,
guarded merge identity and the completed post-merge main artifact checks. This
plan does not preclaim those execution results.

All product/pytest/GUI/browser/build execution is GitHub-runner-only. Local work
is source analysis, lock resolution and artifact metadata/hash inspection.

Measured outcome: [optimization completion report](../../audits/2026-10-16-optimization-completion.md).
