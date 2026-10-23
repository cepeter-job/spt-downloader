# Dated reference catalog implementation plan

> Use superpowers:executing-plans inline. Autonomous implementation was approved on 2026-10-23. All product execution stays on GitHub runners.

**Goal:** Reproduce the pinned grid active-version selector for PPh21 and Unifikasi when custody-checked browser clock evidence proves one selection throughout the capture interval. Preserve old captures and stricter model/PERIOD dropdown rules.

**Spec:** `docs/superpowers/specs/2026-10-23-json-mode-completion-design.md`, section 5.

**Delivery:** draft PR #86 depends on native readiness PR #85. It targets `main` to use the existing PR workflow; its initial diff includes #85 until that prerequisite is integrated. Keep both runner identities distinct.

**Source proof:** unauthenticated pinned `main.cccfdb820c20596c.js`, SHA256 `696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd`, `getActiveReferenceDataValue` at UTF-16 offset 3017141: filter literal Code; first own null/empty ValidTo; first truthy valid ValidTo strictly greater than new Date(); latest valid truthy ValidFrom (stable ties); otherwise first candidate. A generic latest version heuristic is incorrect. Static source inspection is not runtime execution evidence.

The bounded parser uses full `YYYY-MM-DD` dates and second-resolution ISO datetimes with optional three-digit milliseconds and numeric/Z offsets, years 1970..9999. Date-only UTC and offset-free local datetime semantics follow [ECMAScript Date.parse](https://tc39.es/ecma262/multipage/numbers-and-dates.html#sec-date.parse). Other date spellings, calendar normalization, expanded years and historic local offsets remain unsupported.

## Constraints

- No workstation clock, DOM business values, new requests, endpoint permissions, template changes, dependencies or CI edits.
- Add only optional metadata to version-1 private captures. Original response bytes and descriptor hashes remain unchanged.
- Malformed or mixed clock evidence is a safety failure even without eligible form metadata. Missing evidence keeps new calendar-dependent branches unsupported.
- Evaluate interval endpoints and every ValidTo cutoff within it. Endpoints alone miss a first/future/fallback selection that changes and returns to the original row.
- Support a deliberately bounded ISO date grammar with exact millisecond arithmetic, UTC date-only and Asia/Jakarta local datetime semantics. Unknown/malformed dates remain unsupported.
- Preserve strict distinct-code requirements for model and PERIOD dropdowns.

## Task 1: Regression contracts and runner RED

- [x] Add pure projection tests for first-future order, latest ValidFrom/stable ties, first fallback, strict cutoff, UTC/offset/local dates, unchanged sources and candidate-path provenance.
- [x] Add interval crossing (including A -> B -> A), absent clock, malformed dates, and invalid clock types/order/timezone/attempt tests; retain old clock-independent behavior.
- [x] Add whole-attempt tests for unchanged packet bytes, captured clock provenance, fatal mixed/malformed evidence, and unrelated reference sequences.
- [x] Add owned-capture and checkpoint replay tests for before-View/after-drain samples, optional unavailable clocks, invalid samples, Stop, tampered metadata, and identical replay without reading present time.
- [x] Publish tests only and record exact-tree GitHub RED before product edits.

## Task 2: Minimal source-bound implementation

- [x] Add clock validation and reviewed version-selection primitives to existing `coretax_json.py`; avoid a new worker module.
- [x] Sample browser clock/timezone at capture enter and after final drain, validate the owned attempt interval, and bind optional metadata through the manifest, live packets and checkpoint packets.
- [x] Validate optional packet clocks and whole-attempt consistency before projection or fallback; copy only validated clock metadata into bounded provenance.
- [x] Wire only the two reviewed grid catalog consumers. Retain candidate validity paths and selection rule in provenance and leave model/PERIOD uniqueness unchanged.

## Task 3: Verification and delivery

- [x] Read exact final Windows/portable JUnit and package/bootstrap artifacts, verify hashes/build/tree/allowlist identities, and reconcile every new RED node with a passing successor.
- [x] Obtain fresh-context source review; address concrete findings with runner evidence.
- [x] Document supported date grammar, source coordinates, exact evidence and remaining live acceptance. Keep corporate semantic and PPN final-lifecycle work explicitly open.


Completed against code/test head 9997c80bc9011b9d5768998b215dd0b7269d8369, merge c099aab8f95ba4cb98f7448ea2e0b994ae98d32b, tree 7e73f1b4c9146594ebc7c2835233dec94c66057e, run 39884865149 attempt 1: 4083 Windows and 696 overlapping portable cases passed; all 57 authoritative RED nodes reconciled; distribution/bootstrap and 44 worker sources read back. See [final evidence](../reports/2026-10-23-dated-reference-catalogs.md). No local product execution or live-account acceptance.
