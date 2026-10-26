# Named SPT JSON Folders Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Steps use checkbox syntax for tracking.

**Goal:** Publish JSON evidence in readable SPT folders while preserving old evidence and publication guarantees.

**Architecture:** A strict optional run-layout field controls only public paths. Capture references remain private and immutable; held custody reads the source layout and maps its same declared bytes to the requested destination layout.

**Tech Stack:** Existing Python standard library, pytest and existing GitHub Windows/portable/package CI.

**Spec:** docs/superpowers/specs/2026-10-26-json-tax-folders-design.md

## Global Constraints

- Four exact public names: PPh Badan, SPT PPh 21, SPT PPh Unifikasi, PPN; safe unknown fallback SPT Lainnya.
- Private paths and manifest/response bytes unchanged; source metadata never normalized.
- Missing run layout means legacy; only explicit tax-kind-v1 is supported.
- Runner-only execution, no CI/dependency/resource/worker changes, no private data in Git.

## Review Focus

- Same-type records retain distinct original ordinals and original capture attempts.
- Offline legacy-to-named conversion reads old paths before changing the destination declaration.
- Changed selected evidence in either layout refuses replacement without changing workbooks.
- Case/reparse aliases and unknown layout values cannot authorize reads or writes.
- Duplicate private capture references remain invalid across different tax folders.

## Task 1: Define and prove named and legacy publication

**Files:** Create tests/test_json_tax_folders.py; modify tests/test_json_output_folder.py helpers only; modify coretax_json_capture.py and coretax.py; update AGENTS.md.

**Interfaces:** Existing json_output_names(run), verified_json_names(run), verify_existing_json(run, folder) remain callable. Add optional checkpoint_bodies(..., output_layout=None) for published reads and json_custody(..., target_layout=None) for source-to-destination relocation. save_output always produces tax-kind-v1 metadata and declared named paths.

- [ ] Add independent four-name, unknown-safe, multiple-ordinal and immutable-byte assertions; add invalid-layout, duplicate-source, legacy replay/conversion/tamper and case-alias regressions. Keep existing publication, Stop and crash tests intact and make their expectation helper understand the explicit new layout.
- [ ] Commit tests/design/plan, create draft PR from current main, and read runner failures to prove RED. Preserve every baseline node; distinguish intentionally changed path expectations from accidental regressions.
- [ ] Add strict layout/path helpers and source-to-target custody mapping, preserving all validators. Check both supported selected locations before replacement; update save_output metadata only after successful publication.
- [ ] Update AGENTS.md with actual supported layout/legacy boundaries. Run existing full Windows, portable and frozen/package CI on exact PR tree.
- [ ] Obtain a fresh whole-branch review, fix material findings through runner RED/GREEN, and reconcile exact test inventories against main.
- [ ] Review latest preceding other-session PRs and strict required gates, merge with expected head, verify actual main artifacts and hash-copy the complete package to Downloads.
