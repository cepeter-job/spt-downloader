# Owned MPN reference GET implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve missing Accounting reference labels using the single approved, bounded GET before strict parent binding.

**Architecture:** Keep passive capture and strict `_bind_header` unchanged. A preparation stage acquires original reference bytes only when missing catalogs explain all current parent mismatches. Record adapter acquisition distinctly in private evidence and reconcile it during publication.

**Tech Stack:** Python 3.14.8, synchronous Playwright, synthetic pytest tests on GitHub Windows runners, existing GitHub CI/package verification.

**Spec:** `docs/superpowers/specs/2026-11-03-mpn-owned-reference-get-design.md` (approved, including implementation and release).

## Global constraints

- One fixed id-ID/four-type GET per owned attempt; no body, arbitrary query, redirects or retries.
- Existing authenticated Service-Worker-blocked context, both original loaded pins, retained Document/attempt, exact ledger, original selected-scope unfiltered list, Stop and sticky failures are mandatory.
- One 5-second transaction, 8 MiB body; preserve locale, checksums, snapshot and final-drain refusals.
- No cache reads/clears, token extraction, other endpoint, POST or relaxation of genuine parent contradictions.
- Original bytes stay under private `mpn/<attempt>/`; legacy missing origin remains readable and unknown explicit origins are refused.
- Local checks are source/AST/Git/hash only. Tests, product imports, builds and application execution run on GitHub runners.

## Review focus

1. A callback changes ownership while transport/body/disposal fails: Stop and sticky safety must win.
2. A catalog arrives while a request is being considered: wait for admitted traffic and never issue a duplicate GET.
3. Raw source codes already match: do not fetch merely to enrich metadata.
4. A non-reference field differs or a known catalog contradicts display: preserve strict refusal without fetching.
5. Acquired bytes survive checkpoint/publication with truthful actor metadata; legacy evidence remains readable.

### Task 1: Bounded acquisition and pre-binding integration

**Files:** `coretax_mpn_ui.py`, `tests/test_mpn_reference_acquisition.py`, `tests/test_mpn_capture_browser.py`.

**Interfaces:** `_acquire_reference(snapshot)` consumes the current original list snapshot and sets validated `reference_raw`, catalogs and `reference_origin`. `_prepare_header_catalog(header)` runs before `_bind_header` and authorizes no Detail action itself.

- [ ] Write failing synthetic tests for a three-label warm-cache mismatch, exact GET options, one attempt, no unnecessary GET, pending-source drain, context/pin/scope/Document refusals, timeout/status/redirect/body/envelope/locale/snapshot failures, callback Stop and safety failures on success and exception exits.
- [ ] Push a test-only commit and observe the expected failures on a temporary runner probe; never execute product tests locally.
- [ ] Implement the two methods and their bounded value-free ownership guard; invoke preparation before strict parent binding, preserving final comparison and all action gates.
- [ ] Run the new tests and existing MPN behavior/browser regressions on the runner. Add a synthetic browser case demonstrating that the acquired original catalogs allow real inspected Detail navigation; preserve genuine mismatch tests.

### Task 2: Private acquisition provenance

**Files:** `coretax_mpn_browser.py`, `coretax_mpn.py`, `tests/test_mpn_reference_acquisition.py`, `tests/test_mpn_capture_protocol.py`.

**Interfaces:** catalog bindings declare `origin=observed-get-v1` or `origin=adapter-get-v1`; missing origin means legacy observed capture. Only a catalog may declare an origin. The descriptor and held-reader reconciliation both enforce these literals.

- [ ] Write failing tests for accepted acquired/observed/legacy origins, rejected unknown origins or origin on non-catalog evidence, and private-byte custody after acquisition and before failure.
- [ ] Observe RED on the runner, then implement origin persistence and validation without changing original bytes, public workbooks or publication gates.
- [ ] Run protocol, physical proof, publication, Stop, final-drain and legacy regressions on the runner.

### Task 3: Review, full CI, merge and delivery

**Files:** `AGENTS.md`, the approved spec/this plan; no permanent workflow change.

- [ ] Document the narrow approved exception and unchanged independent completion gates in AGENTS.md.
- [ ] Remove the temporary probe, perform source/diff checks, and request one independent whole-branch review. Resolve material findings with regression evidence.
- [ ] Refresh latest main and review preceding merges from other sessions and their interactions; preserve their contracts.
- [ ] Open/update the PR, obtain exact-head full CI and required review, then merge using the already granted authorization.
- [ ] Verify the exact main commit/tree/push run/attempt/artifact, full versioned distribution and read-back hashes; deliver to both established Downloads folders, preserving previous packages.
- [ ] Report build evidence separately from manual GET evidence and full build-matched live acceptance. Keep L3-B performance as the separate remaining task.
