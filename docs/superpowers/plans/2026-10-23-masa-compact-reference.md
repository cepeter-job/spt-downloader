# Compact PPN and PPh21 implementation plan

> **For agentic workers:** Use superpowers:executing-plans. Product execution and tests run only on GitHub runners.

**Goal:** Match the operator-supplied PPN/PPh21 reference presentation without modifying capture custody or eligibility.

**Architecture:** Bind against the existing sanitized template coordinates, then delete only approved unused body rows and redundant spacers. Move merges and row dimensions with deleted rows. Keep the existing workbook proof, audit and export paths.

**Tech stack:** Existing Python/openpyxl worker and synthetic Windows CI fixtures.

**Spec:** The operator's approved `shouldbe` workbooks, inspected read-only outside version control, and AGENTS.md output contract. The source files remain unchanged and are never packaged or committed.

## Constraints and review focus

- Preserve literal identifiers, dates, model/period, duplicates, source values and capture completion; zero and False count as content.
- Retain one empty body slot for empty tables, observed footer spacers, section separators, headers and captured totals. Grow only for populated rows.
- PPN Induk removes original blank rows 8 and 25; PPN appendices keep only used body capacity.
- PPh21 L-IA and L-IB remove one extra blank row before their first headers. Reuse existing group separators for observed footer spacers rather than adding a second empty row.
- L-IA rate percentage points become exact safe numeric fractions; malformed, nonfinite, out-of-range or unsafe-precision values stay literal and unresolved.
- Accounting uses zero decimals without rounding stored values. Preserve other formats, styles, widths, page settings and merges.
- No new endpoint permissions, capture changes, dependencies, worker modules or CI edits. Merged PR #89 is the baseline.

## Execution

- [x] Inspect both workbook pairs via ZIP/XML, compare all sheets, and verify unchanged input hashes.
- [x] Add `tests/test_masa_compact_export.py` with literal final positions and real export/proof checks.
- [x] Observe regression failures on GitHub before implementation (test-only run 39899268058: 22 failures).
- [x] Add bounded row compaction and accounting normalization to existing template support; wire PPN/PPh21 after semantic binding.
- [x] Add safe L-IA rate conversion and preserve truthful unresolved reports.
- [x] Keep existing semantic binding tests on original reference geometry using explicit test helpers. Test actual final saved workbooks independently without suppressing presentation.
- [x] Verify empty, populated, growing, duplicate, zero, False, malformed numeric and ambiguous mapping cases; verify source immutability and totals. First implementation run 39900540975 passed all new regressions; two model-separation assertions still addressed the original PPN Induk row and are updated to final row 43.
- [ ] Run full unchanged Windows CI, portable subset, package/source/frozen/bootstrap gates on the exact candidate tree; obtain independent source review.
- [ ] Merge after all required checks pass, verify main artifact identity/hashes/provenance, deliver ZIP to the requested Downloads folder, and remove this task's merged branch/worktree.
