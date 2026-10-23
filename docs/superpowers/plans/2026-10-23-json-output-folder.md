# JSON output folder implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Retain declared original JSON evidence under `json/` in the final SPT output and complete the authorized PR consolidation.

**Architecture:** Reuse the existing private capture manifest and checkpoint verifier with a published-path adapter. Copy only held, hash-verified declared files; add their names to desktop publication selection and their fingerprints to consent/recovery snapshots. Workbook output declarations stay workbook-only.

**Tech Stack:** Python, stdlib file custody, existing Windows publication transaction, pytest on GitHub Windows runners.

**Spec:** `docs/superpowers/specs/2026-10-23-json-output-folder.md`

## Global constraints

- Product/test/build execution is GitHub-runner-only; local AST/Git checks are source inspection only.
- Preserve raw bytes, literal identity/scope, privacy policy, byte budgets, cancellation and truthful PARTIAL.
- Keep checkpoint references backward compatible and preserve recovery artifacts.
- Do not modify CI, locks, resources or LICENSE to obtain GREEN.

## Review focus

- An unselected stale attempt must not enter a fresh publication.
- An existing selected JSON path with modified bytes must fail before any public replacement.
- Interrupted JSON publication must recover prior workbooks and JSON together.
- DOM-only and fallback/PARTIAL jobs must retain their distinct completion semantics.
- Case aliases, symlinks and late modifications must fail through existing guarded publication boundaries.

### Task 1: Export and publish declared JSON evidence

**Files:** `coretax_json_capture.py`, `coretax.py`, `spt_desktop/output.py`, `spt_desktop/publication_recovery.py`, `tests/test_json_output_folder.py`, `AGENTS.md`, `docs/arsitektur.md`.

**Interfaces:** Consume record `detail_source.capture`, `checkpoint_bodies`, output selection and recovery snapshots. Produce `output_json` names, `json_output_names`, `json_custody` and `copy_held_json` without changing workbook/PDF declarations.

- [ ] Write synthetic capture-to-CLI/desktop publication, PARTIAL/fallback, DOM-only, stale-attempt, tampering, cancellation, overwrite and crash recovery tests.
- [ ] Publish tests first; observe failures for missing JSON output on the existing GitHub workflow. Expected: assertions about absent `json/` files fail, existing suite remains accounted for.
- [ ] Implement minimal custody/export/transaction changes and update AGENTS/documentation.
- [ ] Run the unchanged workflow on the implementation. Expected: new behavior tests and full Windows/portable suite pass; exact uploaded package/source/frozen self-tests pass.
- [ ] Read back exact artifacts; perform one fresh whole-change review and one TDD fix pass for any Important/Critical findings.
- [ ] Review current preceding main merges and merge the verified consolidated PR; close superseded #85/#86 with a link to the delivered PR. Expected: all three PR states verified from GitHub, main retains the reviewed upstream changes.
