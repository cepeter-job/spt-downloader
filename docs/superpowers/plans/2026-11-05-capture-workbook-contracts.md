# Issue #187 — capture/XLSX contracts, first implementation slice

Baseline: `main` at `56528a559582a00a03599bd3a2143590707098e6` (2026-11-05).
This work intentionally adds **synthetic characterization tests first** without
changing capture, projection, publication or security behavior.

## Gap inventory before implementation

Already covered by repository tests:
- `test_model_workbooks.py`: workbook per model, duplicated generic rows,
  source metadata, literal text, amendment separation and PARTIAL proofs.
- `test_export_safety.py`: XML-invalid/cell-length/numeric precision rejection,
  preflight, scope mismatches, formulas as text and long-context chunking.
- `test_pph21_template.py`, `test_corporate_template_layout.py` and
  form-specific Masa tests: template geometry, mapped values and source text.
- `test_json_hybrid_native.py` and `test_json_hybrid_rejections.py`:
  source-owned JSON admission, whole-record DOM fallback, authorization refusal
  and browser fixture safety.
- `test_corporate_l7_native.py`: packet-to-approved workbook integration.

First missing frozen contract addressed by this PR:
- A small **versioned semantic cell manifest** for the generic `L-Z` appendix
  produced by all four supported families in the existing `model_run` fixture.
- Fixed cell **locations** and **types**, not just token presence/counts:
  literal identifier `00007`, localized amount `1.234,50`, separate
  optional numeric `1234.5`, duplicate rows, and identical record identity.
- Deliberately changed second row to prove ordered rows do not collapse.
- One entire saved-output PARTIAL path: workbook proof, visible partial marker,
  and resume/index status must agree.
- The manifest lives at `tests/fixtures/workbook_contract_v1.json`; it contains
  no tax records, network captures, credentials or generated XLSX binaries.

## Test-first verification plan

1. Review new assertions independently against the current export public API.
2. Run `python -m pytest -q tests/test_workbook_contract_golden.py` on the
   **GitHub Windows test runner** (the project pins Python 3.14.8), plus the
   existing repository's complete-inventory and coverage gates.
3. If red, classify a test expectation mistake versus a real code regression;
   record the exact failing test and failure cause before changing production.
4. Retain this PR as draft until exact-head green CI and review. Never claim
   a preexisting failure (RED) unless one was actually observed.
5. Continue #187 in **separate narrow slices** for cross-path JSON/DOM semantic
   equivalence and representative approved-template golden cases, subject to
   fixture ownership and non-duplication review.

## Non-goals

This slice does **not** establish live Coretax acceptance, entire-record
JSON/DOM parity, new MPN source eligibility, release signing, ZIP-byte golden
snapshots, a new capture adapter or broad refactoring.

Issue [#161](https://github.com/cepeter-job/spt-downloader/issues/161)
continues Corporate live acceptance; [#156](https://github.com/cepeter-job/spt-downloader/issues/156)
continues MPN live acceptance. Nothing here relaxes those safety gates.
