# Issue #187 — Phase 3: real-browser DOM semantic boundary

Date: 2026-11-05. Based on `main` at `f8c7cd33a939bd20930141587575977eb1d1d072`.

## Gap assessment

Phase 1 (#188) pinned synthetic XLSX field geometry, duplicates and
proof/partial declarations. Phase 2 (#190) compared real JSON wire decoding
with a **stubbed** DOM collector; the DOM parser was not executed.

Existing real-browser tests cover tab traversal, duplicate pages,
retained page reset, bounded page sizes, cursor ownership/timeout, table
structure and simple mismatched total. JSON native tests separately cover
capture binding, incomplete grids, overlapping pages, duplicate rows, types
and source custody. Do not duplicate these cases.

## Narrow test-only addition

`tests/test_issue187_real_dom_parity.py` uses Playwright's actual Edge DOM
extractor (`coretax_browser.capture_detail`) and the actual synthetic-wire
decoder (`coretax_json.adapt_corporate_detail`), with no monkeypatch of
either parser and no external portal navigation.

- Declare a consistent synthetic pair using the already versioned
  `capture_semantic_pair_v1.json` contract. Compare the 16-character
  leading-zero TIN literal and precise `123.4500` numeric lexeme, while
  **preserving** their source-specific types (`string` and `number` in
  JSON; a textual value in DOM). This is *business-literal parity only*,
  not byte-identical source custody or live Coretax equivalence.
- In the same DOM extraction, traverse a two-page table, preserve two
  genuinely duplicate source rows, and reconcile three body rows to the
  advertised count with one permitted next click.
- Independently mutate the synthetic terminal page to be empty while a
  nonzero advertised count remains; and test a mismatched reported count.
  Both must remain PARTIAL without inventing source rows.
- Feed the **actual incomplete DOM sections** to the existing workbook
  exporter, confirm saved partial proof and visible resume markers, and
  reject a forged COMPLETE claim using the existing export validation API.

## Verification and boundaries

- The included tests are *characterization of existing production behavior*;
  no production defect and no pre-existing feature RED is asserted.
- Run new and adjacent tests on a reviewed exact SHA. Required GitHub-hosted
  Windows/portable/shard/package CI remains authoritative; the optional
  private `puntoap` workflow is supplementary.
- The fixture has no real names, taxpayer records, browser profiles,
  cookie state, remote Coretax queries or downloaded attachments.
- Source record identity/custody, real portal DOM variants, financial
  attachment status and user publication consent remain separate gates.
  The test's synthetic `record_id` in workbook proof is supplied by the
  fixture's run, **not** established by the DOM parser.

## Remaining issue #187 work

Phase 4 should audit interrupted-publication and rollback coverage,
source-owned stale total/unknown table shapes and approved-template mapping
goldens. Add only demonstrated gaps. Do not treat green synthetic tests
as acceptance of issues #161 or #156. Keep #187 open.
