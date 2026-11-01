# Literal Capture Mode Owner Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline; one fresh whole-branch review before merge.

**Goal:** Remove the GUI controller's unnecessary tax-adapter dependency while preserving the literal mode API.

**Architecture:** A tiny common owner supplies the same validator through explicit legacy export and the controller's existing local name. Backend callers remain unchanged.

**Tech Stack:** Python3.14.8, existing hash-locked GitHub Windows CI.

**Spec:** [Shared literal capture-mode contract](../specs/2026-11-02-detail-source-owner.md).

## Constraints and review focus

- No product import/test/build/EXE execution locally; use runners.
- Preserve exact strings, type policy, ValueError, call order, defaults and local patch namespaces.
- No dependency, filesystem, recovery, hash-provider, capture or output changes.
- Keep coretax_json compatibility export and register the new explicit worker resource.
- Import isolation is structural evidence, not a performance benchmark or live acceptance.

## Task 1: Prove and isolate the contract

**Files:** new coretax_detail_source.py and tests/test_detail_source_contract.py;
coretax_json.py, spt_desktop/controller.py, spt_desktop/runtime.py; AGENTS.md and an audit report.

**Interface:** validate_detail_source(value) accepts only exact str dom/json-first,
returns the original value and otherwise raises the original ValueError.

- [ ] Add a fresh-process GUI import boundary test, public identity/literal characterization and local controller patch-injection tests.
- [ ] Run tests-only on a pinned Windows probe; observe the expected adapter-import refusal and inspect original JUnit.
- [ ] Move only the validator body, add the explicit legacy export/controller import/resource and document the actual boundary.
- [ ] Run the same focused runner probe GREEN and full CI; preserve every baseline test identity and inspect exact artifacts.
- [ ] Fresh whole-branch review; review latest main/preceding other-session merge, then merge and update issue134 with evidence and remaining conditional work.

Main166 postmerge package/test readback precedes this task and is recorded in issue134.
