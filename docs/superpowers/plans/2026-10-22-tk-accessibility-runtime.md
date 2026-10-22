# Tk Accessibility Runtime Candidate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and evaluate an isolated desktop runtime candidate with Tcl/Tk 9.1 accessibility, producing evidence for a separate adoption decision.

**Architecture:** Build matching CPython 3.14.8 x64/GIL, `_tkinter`, Tcl 9.1.0 and Tk 9.1.0 in an isolated GitHub Windows job. Keep the managed worker/CLI and production distribution unchanged. Qualify the candidate with exact runtime inventories, password protection and actual reader tests before proposing adoption.

**Tech Stack:** CPython 3.14.8, Tcl/Tk 9.1.0, Windows MSVC/SDK, stdlib Tkinter, existing locked PyInstaller, Windows MSAA/UIA, NVDA and Narrator.

**Spec:** [Approved runtime design](../specs/2026-10-22-tk-accessibility-runtime-design.md).

**Status:** Approved by the owner on 22 October 2026 for subagent-driven execution.

## Global Constraints

- Worker and CLI remain CPython 3.14.8 x64/GIL with uv 0.13.4, existing locks and WORKER_FILES.
- No local product imports, tests, native calls, builds or executable runs; GitHub runners only.
- No real accounts/taxpayer data, password logging, remote scraping, private profiles or live outputs in artifacts.
- Consent, Stop precedence, owned-process cleanup, literal source values and COMPLETE/PARTIAL rules remain unchanged.
- The desktop stays stdlib/Tkinter; it must not import Playwright/openpyxl.
- Signing is deferred. The owner performs live Coretax/Excel acceptance.
- Actual 200% and cross-monitor acceptance require a suitably configured GitHub Windows runner; unavailable equipment is a blocker, not PASS.
- This plan authorizes a candidate investigation. Production runtime adoption remains a separate reviewed change after evidence is available.

## Review Focus

- Masked entry typing, selected substrings and reader echo must not reveal a synthetic password: Task 3.
- DLL or script-library fallback to a developer checkout must fail qualification: Tasks 1–2.
- A reader started after Tk initialization must not be silently treated as already supported: Task 3.
- A candidate build must not migrate or overwrite an existing production worker: Tasks 2 and 4.
- Missing reader/display facilities must remain explicitly untested/blocked: Tasks 3–4.

## File structure and isolation

Use a separate feature branch/worktree for the runtime candidate, preserving PR #71
and its recovery work. Base it on the reviewed UI change; if #71 is unmerged,
record that dependency and keep the candidate PR draft. Do not commit unrelated
local investigation files. Read repository instructions before any implementation.

Candidate code is under `scripts/launcher_candidate/`; none of it enters WORKER_FILES.
`sources.json` describes inputs, `inventory.py` validates identities/artifact files,
`build.ps1` builds the candidate, and `probe.py` records actual loaded runtime data.
`scripts/launcher_candidate/reader_probe.ps1` and `reader_host.py` exercise only
synthetic owned windows. A dedicated `launcher-candidate.yml` workflow owns all
execution. Existing production workflow/gates remain intact.

Each test task uses the candidate workflow on GitHub, with a test-only commit
first and an implementation commit after its intended failure is observed.
For Tasks 1–3 respectively, run the following with the task's test filename:
`<runner-python> -m pytest tests/test_launcher_candidate_inventory.py -q --basetemp "$env:RUNNER_TEMP/candidate-tests"`;
`tests/test_launcher_candidate_package.py` and
`tests/test_launcher_candidate_reader_report.py` replace the filename for Tasks 2–3.
Use the managed production test interpreter until Task 1 proves the candidate;
then use the candidate interpreter with the same hashed test lock. GREEN means
all selected behavior assertions pass; a missing reader is never a passed native gate.

### Task 1: Reproducible native runtime and loaded-library proof

**Files:** Create `scripts/launcher_candidate/{sources.json,inventory.py,build.ps1,probe.py}`,
`.github/workflows/launcher-candidate.yml`, and `tests/test_launcher_candidate_inventory.py`.
Add a narrowly reviewed CPython/Tcl/Tk build patch under this candidate directory only if required by inspected upstream build projects.

**Interfaces:**
- `validate_inventory(document: dict, root: Path) -> None` rejects wrong runtime versions, architecture, missing/mismatched files, symlinks and paths outside the candidate root.
- `probe.py --output <json>` records interpreter/GIL/bitness, Tcl/Tk patchlevels, actual loaded DLL paths/hashes and script-library paths.
- `build.ps1 -Sources <json> -OutputDirectory <new-directory>` emits the candidate interpreter and inventory; failure never replaces a prior artifact.

- [ ] Write synthetic inventory tests: reject Tcl/Tk 9.0.4; wrong `_tkinter`/DLL hashes; external script paths; missing license; unexpected architecture; file-set mismatch. Accept only the explicit candidate fixture.
- [ ] Run these tests on GitHub and observe the intended failures before implementing validation.
- [ ] Record immutable upstream identities verified during planning: CPython `8e6e75d9102e39bed2a2b279203a396741180f12` (v3.14.8), Tcl `0c6bad08d91fa2ad51f05a50a41f8c1ea82ce985`, Tk `3f45110c0a568b70f2ebd5412f215e87d199bc7d` (core-9-1-0). Download by immutable revision and record archive SHA-256 before accepting input manifests. Resolve every additional native build dependency with equivalent identity checks.
- [ ] Inventory the Windows compiler/toolset/SDK and record exact selected versions before qualification. Inspect upstream Windows build projects and build matching `_tkinter` against the chosen Tcl/Tk headers/libraries. Never rename/substitute DLLs in managed Python. Capture minimal synthetic build diagnostics and patch hashes.
- [ ] Implement inventory validation and run the tests to GREEN. Execute `probe.py` under the built candidate with developer checkout/library environment overrides removed. Assert CPython 3.14.8, x64, GIL, Tcl/Tk 9.1.0 and candidate-local loaded resources.
- [ ] Upload only declared candidate runtime files, licenses, inventory and synthetic build/probe evidence. Download by exact artifact ID and verify hashes. A build incompatibility produces a report and blocks later tasks; do not silently change versions.
- [ ] Review staged source/manifest data and commit this independently testable candidate build.

### Task 2: Candidate packaging and exact source/frozen identity

**Files:** Create `scripts/launcher_candidate/package.py` and `tests/test_launcher_candidate_package.py`;
extend candidate workflow and inventory/probe modules from Task 1. Modify `build_desktop.py`
or `spt_gui.py` only for an explicit candidate report interface that preserves existing production behavior.

**Interfaces:**
- `package.py --runtime <candidate-root> --output <new-directory>` uses the existing build lock and candidate interpreter, producing an unsigned candidate application plus runtime identity.
- `validate_candidate_report(report: dict, inventory: dict) -> None` checks exact launcher identity independently of the unchanged worker profile.

The validator lives in `inventory.py`. Both validators raise `ValueError` on
invalid evidence and return `None` only on acceptance; tests assert rejection
for each named negative fixture and acceptance for one complete synthetic fixture.

- [ ] Write report tests rejecting syntactically valid but wrong Tcl/Tk versions, wrong native-resource identity, old-runtime self-tests attached to a candidate, and missing frozen resources.
- [ ] Observe RED on GitHub; implement the smallest candidate-only packaging/report interface. Reuse existing production validation without weakening it or inferring launcher identity from worker Python alone.
- [ ] Run source and frozen self-tests under the candidate. Record actual loaded native libraries, exact versions, resources and absence of real credential/portal access. Verify freezing does not depend on the checkout or source-build environment.
- [ ] Read back the candidate application artifact by exact ID; inspect the explicit file allowlist, licenses and every checksum. Run frozen validation on those downloaded bytes on the runner.
- [ ] Verify candidate preparation and startup leave the existing production worker identity/preferences untouched, using synthetic paths and worker inventories. Commit after the negative report tests and source/frozen proof pass.

### Task 3: Password gate and actual reader behavior

**Files:** Create `scripts/launcher_candidate/{reader_probe.ps1,reader_host.py}` and
`tests/test_launcher_candidate_reader_report.py`; extend candidate workflow. Add a
product accessibility adapter only in a subsequent reviewed change if evidence proves it necessary and safe.

**Interfaces:**
- `reader_host.py --scenario <main|settings|selection|overwrite|progress|result> --directory <new-directory>` creates synthetic existing app flows without starting a real worker or accessing credentials.
- `reader_probe.ps1 -Runtime <source-or-frozen-candidate> -Reader <NVDA|Narrator> -OutputDirectory <new-directory>` records native ownership, activation, MSAA/UIA and reader observations with exact candidate identity.
- Reader reports use independent `passed`, `failed`, `blocked`, `not_tested` outcomes for password, names/roles/values/states, focus, selection and speech/navigation.
- `validate_reader_report(report: dict, inventory: dict) -> None` in `inventory.py` validates identity and outcome/evidence consistency, raising `ValueError` for an invalid claim. Valid blocked reports remain blocked in the adoption report. Each report identifies reader/version, source or frozen mode, scenario, activation timing, and evidence references; absence of an observation cannot satisfy a passed gate.

- [ ] Write report-validation tests rejecting absent/late-unverified reader activation, missing MSAA/UIA coverage, source-only evidence presented as frozen acceptance, missing protected-password observations, and unavailable readers presented as PASS. Run RED on GitHub.
- [ ] Verify availability of actual NVDA and Narrator on the selected runner. For NVDA, record an official version, immutable download/hash and license before acquisition. Use an isolated synthetic user context; never attach to personal windows or accounts. If a required reader cannot run, record the exact prerequisite and stop qualification of its scenarios.
- [ ] Launch each reader before constructing the source candidate; independently test late activation. Repeat against the exact read-back frozen candidate. Record observed initialization rather than inferring it from API existence.
- [ ] Before general acceptance, type a synthetic sentinel into the masked Settings password field. Test MSAA/UIA value and selection access, focus notifications, typing echo, copy-like reader inspection, remap, reopen and late activation. Report only whether the sentinel/substrings appeared; do not publish raw value dumps. Reject any exposure through either reader/provider.
- [ ] If the password gate fails, stop adoption and produce a minimal synthetic reproduction for separate review. Do not patch over raw entry callbacks, disable the probe, or proceed with real credentials.
- [ ] If safe, exercise all existing flows: meaningful control/row/header announcements, enabled/disabled state, edit changes, selection, modal focus/grabs, keyboard activation, Stop, return focus and result actions. Preserve consent and exact source strings. Record NVDA and Narrator results separately.
- [ ] Implement report validation to GREEN, preserve synthetic evidence and commit. No UIA/Narrator success may be inferred from an NVDA/MSAA success.

### Task 4: Candidate regression, display qualification and adoption report

**Files:** Extend `.github/workflows/launcher-candidate.yml`; create
`docs/audits/2026-10-22-tk-accessibility-candidate.md`; update candidate operator instructions.
Create those instructions at `scripts/launcher_candidate/README.md`.
Do not change the normal production runtime in this task.

**Interfaces:** Consume Task 1 inventory, Task 2 source/frozen reports and Task 3 per-reader reports.
Emit one adoption report bound to exact commit/tree/run/attempt/artifact IDs and hashes.

- [ ] Run the complete Windows GUI/native suite using the candidate interpreter, with the existing hashed test lock and external scratch basetemp. Run portable tests and dependency audit. Worker bootstrap/reuse must still verify the unchanged managed CPython 3.14.8 worker.
- [ ] Exercise both source and exact read-back frozen application: Settings decisions/password clearing, selection and overwrite consent, stale events, cancellation, owned cleanup and COMPLETE/PARTIAL eligibility. A matching version string is insufficient evidence.
- [ ] Run the unchanged paired dialog-performance observer against the reviewed baseline and candidate on the same runner. Keep raw samples, payload hashes and environmental identity; retain the below-100-ms settled-opening target and report regressions.
- [ ] On a suitable GitHub Windows runner, inspect normal/compact layouts, actual 200% geometry, High Contrast and actual distinct-DPI monitor movement. Record initial state, changes and restoration. Missing hardware stays blocked; do not use fabricated monitor metadata or raise minimum geometry beyond the real work area.
- [ ] Repeat a controlled native build to assess reproducibility. Compare inventories/output hashes; explain any nondeterminism before making a byte-reproducibility claim.
- [ ] Read back all final candidate artifacts by exact IDs, verify manifests and separate passed/failed/blocked gates. Keep the normal distributed launcher unchanged. Present the candidate and privacy/accessibility limitations for a separate adoption decision.
- [ ] Review staged content for private data and obtain a fresh whole-change review. Commit and open a separate draft candidate PR; do not merge or publish a release automatically.

## Self-review and execution handoff

The four tasks cover runtime identity, packaging, password/reader behavior and
full regression/display qualification. No task treats missing facilities as a
pass. All tests and native work execute remotely; source and frozen evidence are
explicitly bound to the candidate. A failed compatibility or privacy gate halts
adoption while preserving diagnostics and the production runtime.

Recommended execution: **subagent-driven**, with a fresh implementation and
review context at each native-runtime/privacy boundary. Native execution by the
primary agent is also possible, with an independent whole-change review before
the adoption report. Owner plan review and execution-method selection precede
candidate implementation.
