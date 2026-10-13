# PR consolidation implementation plan

> **For agentic workers:** Use superpowers:executing-plans for the inline integration; independent reviewers inspect exact immutable commit ranges.

**Goal:** Consolidate reviewed PRs #11–#14 into the native Tkinter Phase 1 branch and merge only after exact-head runner verification.

**Architecture:** Preserve the controller/worker authority and the new native presentation layer. Integrate the already requested workbook and progress fixes, without extending the design-only JSON-hybrid pilot into product code.

**Tech Stack:** Existing CPython 3.14.8, stdlib Tkinter/ttk, existing exporter and GitHub Actions.

**Spec:** `2026-10-13-magicpath-b-tkinter-design.md`, `2026-10-13-spt-json-hybrid-design.md` in `../specs/`, and the explicit requirements of PR #14. The later request to remove the personal-name footer supersedes that one older locked-copy entry.

## Constraints and review focus

Preserve exact selected IDs, NPWP/year/period scope, source values, PDF custody, overwrite consent and Stop precedence. Keep all runtime execution on GitHub runners, CI and runtime pins unchanged. No live portal, credentials, private captures, deployment, VirusTotal work or manual acceptance is included.

Review the footer/copy migration, initial selected-scope counters, late/stopped consent replies, destruction callbacks, and forms-only workbook/PDF proof compatibility. PR #13 remains specification only; implementation and its own acceptance remain pending.

## Tasks

- [ ] Independently review immutable PR #12 and #14 diffs plus the design-only PR #13; verify #11 ancestry.
- [ ] Add native GUI and pure-state regression tests before integration repair; publish the tests and read their expected failure on the exact GitHub head.
- [ ] Merge the approved branch histories into #12, retaining both sets of tests. Remove only the retired footer/copy ID; initialize zero selected detail counts only after accepted current-job consent; address reviewed cleanup/import/return comments and align current docs.
- [ ] Run the unchanged complete runner pipeline, review the actual integration diff, read the exact artifact and hashes, resolve substantiated review threads, merge with expected head SHA, and read back main/PR state.

## Test contracts

`tests/test_desktop_ui_state.py`: accepting a current selection of two records keeps inventory counters separate and initializes `Counters(processed=0, total=2, verified=0)`; duplicate replies remain inert.

`tests/test_desktop_selection_gui.py`: the real synthetic Tk dialog shows `SPT diproses: 0 / 1`, `Lengkap: 0`, selected scope `1`, and the requested status immediately after accepted consent, before any worker detail event. No 100% or terminal status is invented.

`tests/test_desktop_requested_text.py`: the consolidated native widget tree retains the generic personal-use subtitle but excludes the explicitly removed personal-name footer. Existing PR #14 footer/source-comment/source-frozen tests and all Phase 1 geometry/focus tests remain in the complete suite.

## Verification

Use the existing `Build Windows app` PR workflow. Local checks are limited to source/AST, Git diffs, and downloaded artifact metadata/hashes, never product imports or tests. Bind RED/GREEN, Windows and portable counts, packaging, and artifact proof to their exact SHA and run. Main provenance is verified separately after merge.
