# Issue #187 — Capture-boundary semantic parity, slice 2

> For agentic workers: preserve the existing source-specific observers and
> publication gates. This is a synthetic test contract, not new admission logic.

**Goal:** Compare the same synthetic taxpayer, selected record, scope, and
literal business values through existing JSON-first and DOM capture boundaries,
then verify persisted workbook proof and PARTIAL status without conflating
source-specific diagnostics.

**Base:** `main` at `ffa510d1c8a653735f0aafea2bf5d5665af8710e`
(merged PR #188). **Language:** Python 3.14.8. **Scope:** test-only.

## Ownership and prior coverage

- `tests/support_json_corpus.py`: original synthetic JSON wire + selected
  return facts (authoritative for this branch).
- `tests/support_json_hybrid.py:Scenario`: real JSON capture/decoder with a
  **stubbed** DOM capture function; tests can swap only this stub's section
  fixture without touching product source.
- `tests/test_json_hybrid.py`: native admission, DOM fallback, failed source,
  STOP, PDF failure and checkpoint custody. Do not duplicate these.
- `tests/test_json_hybrid_native.py`: browser-native source ownership and
  pagination. Do not claim the stubbed DOM path validates the live parser.
- `tests/test_workbook_contract_golden.py` (PR #188): fixed common XLSX cell
  geometry and types. This slice pins **capture path identity**, not those
  cells again.

## New narrow contract

1. `tests/fixtures/capture_semantic_pair_v1.json` declares only invented
   business facts: same record/scope/period and a leading-zero identifier plus
   a monetary lexeme with trailing zeroes. The JSON fixture remains the
   existing versioned synthetic wire corpus; the DOM fixture is an independent
   source-section observation for the stubbed browser boundary.
2. `tests/test_capture_semantic_parity.py` runs both existing capture modes
   in isolated `monkeypatch.context` scopes and checks selected source
   identity, exact source literals, section identity, complete status,
   workbook-proof identity, and absence of JSON-mode DOM reading.
3. Both modes export a saved **proof declaration** and agree on PARTIAL when
   independent financial evidence is missing. This does not mean the output
   is eligible for final publication: mapping completeness, custody and user
   consent have separate owners.
4. Assert source-specific `detail_source.used=json` only for JSON-first;
   never require byte-identical internal structures or absent DOM provenance
   fields.

## Verification

- [ ] CI Windows test inventory runs the new tests; inspect exact failures,
  don't change runtime behavior to satisfy invented fixtures.
- [ ] Existing JSON-hybrid/browser/Excel and cross-shard quality gates remain
  green on the exact candidate head.
- [ ] Run independent code review on scope and inadvertent privacy/ownership
  assertions before merge.

**TDD evidence honesty:** this is characterization of existing behavior;
there is no claimed pre-existing RED. If a test fails, record the actual
failure and its cause before adjusting expectation or making a production
change. A new production change would require a real failing contract first.

## Remaining issue work

This does **not** prove browser DOM-parser equivalence for complete real
tables, cross-path source pagination with duplicate/empty/unknown rows, or
interrupted publication recovery. Those remain future narrow sub-PRs under
#187; issue #161 and #156 still own live Corporate/MPN acceptance.
