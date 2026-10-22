# Proposed desktop runtime accessibility upgrade

> **Historical / retired investigation.** This document is retained from [candidate commit `26cbec9`](https://github.com/cepeter-job/spt-downloader/commit/26cbec98b5cd384d9500945ab46dcd749e733919) as documentation only. The candidate runtime and diagnostic implementation are not adopted into `main`. Failed and blocked qualification gates below remain unresolved; this record does not authorize implementation, execution, runtime adoption or release. References to candidate scripts and workflows point to that immutable source revision. Branch/worktree and handoff statements below describe the original investigation, not a requirement to keep an active branch.

Status: **isolated candidate investigation implemented; production adoption blocked**.
The owner approved implementation on 22 October 2026. The candidate is kept separate
from production; see the [candidate audit](../../audits/2026-10-22-tk-accessibility-candidate.md)
for exact evidence, failed reader qualification and remaining display gates.
The owner requested this separate review after the current Tk 9.0.4 diagnostic
exposed the tested inputs as unnamed UI Automation panes. The existing UI fixes
are reviewed separately in [PR #71](https://github.com/cepeter-job/spt-downloader/pull/71).

## Intended outcome and boundaries

Users of NVDA and Narrator should be able to identify and operate the main
form, Settings, SPT selection, overwrite decision, progress and results. Required
observations include names, roles, values, states, selection and focus. A window
that opens, an available API, or a screenshot is not an accessibility pass.

Keep the existing Tkinter flows, literal tax data, read-only access, consent,
Stop precedence, owned-process cleanup, and COMPLETE/PARTIAL rules. Keep worker
and CLI CPython 3.14.8 x64/GIL, uv 0.13.4, dependency locks and WORKER_FILES.
The desktop process stays a thin launcher without Playwright/openpyxl imports.
Signing remains deferred. Live Coretax/Excel acceptance belongs to the owner.
All runtime execution remains GitHub-runner-only.

Full nominal normal/compact 200% acceptance remains a separate gate. The current
hosted Windows display modes are too small. Use an appropriately configured
GitHub Windows runner with a sufficiently large real display at actual 200%
scaling; never substitute Tk scaling or mocked work-area metadata as that proof.
Cross-monitor acceptance likewise needs distinct-DPI monitors and actual movement.

## Options and recommendation

| Option | Assessment |
| --- | --- |
| A maintained, exact-hash Python distribution already containing Tk 9.1 | Preferred if verified available and compatible. None was verified in this review; a Python/uv version bump alone does not establish a Tk upgrade. |
| Build a matching desktop-only CPython/_tkinter/Tcl/Tk candidate | **Recommended next investigation.** Retains the managed worker while allowing a separately verified launcher runtime. Adds responsibility for native build provenance and packaging. |
| Change the managed distribution for both launcher and worker | Adds worker migration/cache/download scope without a necessary worker accessibility benefit. Not proposed. |

Use CPython 3.14.8 x64/GIL and stable Tcl/Tk 9.1.0 as the candidate sources.
Resolve tags to immutable revisions and archive hashes before building. This is
a compatibility hypothesis to test, not a claim that the combination already
builds or passes. Do not copy or rename Tk DLLs into the existing managed Python.
Build the matching `_tkinter`, libraries, DLLs and Tcl/Tk script resources together.

Upstream references checked during review:

- [CPython 3.14.8 Windows Tcl/Tk properties](https://raw.githubusercontent.com/python/cpython/v3.14.8/PCbuild/tcltk.props)
  and [3.15.0 properties](https://raw.githubusercontent.com/python/cpython/v3.15.0/PCbuild/tcltk.props)
  still identify Tcl/Tk 9.0.4; these do not supply the proposed candidate.
- Stable [Tcl 9.1.0 release source](https://raw.githubusercontent.com/tcltk/tcl/core-9-1-0/changes.md)
  and [Tk 9.1.0 release source](https://raw.githubusercontent.com/tcltk/tk/core-9-1-0/changes.md).
- [TIP 733](https://core.tcl-lang.org/tips/doc/main/tip/733.md) describes the
  Windows MSAA backend, limited UIA bridge and weaker Narrator support than NVDA.
- [Tk 9.1 accessibility API](https://www.tcl-lang.org/man/tcl9.1/TkCmd/accessible.html)
  and [stable Windows implementation](https://raw.githubusercontent.com/tcltk/tk/core-9-1-0/win/tkWinAccessibility.c).

## Candidate build and identity

Use an isolated GitHub Windows build job and output directory. Record immutable
source revisions, archive SHA-256, compiler/toolset/SDK versions, configuration,
patches, native dependencies, licenses and output hashes. Dependency acquisition
must remain explicit and verified. Produce a candidate runtime inventory and
an unsigned application artifact with exact run/attempt/commit/tree coordinates.

Keep the candidate separate from production distribution until its gates pass.
The initial candidate must not mutate the user's existing managed worker or
its cache identity. A later adoption change must make the launcher-runtime
identity explicit instead of inferring it from the worker's Python pin.

Current build validation accepts syntactically valid Tcl/Tk version strings.
Candidate validation must require exact reviewed versions and native resource
identity. Source and frozen reports must identify the runtime actually loaded.
The frozen artifact must contain matching script libraries and DLLs and work
without developer checkout paths. Preserve LICENSE and include required runtime
licenses. No claim of reproducible bytes until two controlled builds establish it.

## Password protection is a prerequisite

The stable [accessibility script](https://raw.githubusercontent.com/tcltk/tk/core-9-1-0/library/accessibility.tcl)
reads raw entry values and installs focus/selection/key callbacks. Source review
did not establish masking for `-show` password entries. This is an unresolved
privacy risk, not a demonstrated leak in an executed candidate.

Before adopting the runtime, use a clearly synthetic sentinel password to test
MSAA and UIA values, selected text, focus notifications, keyboard echo and reader
speech with both readers. Cover initial focus, typing, selection, reveal through
navigation, closing/reopening Settings and late reader activation. The sentinel
must not be exposed as a value, substring or character echo. Preserve password
clearing after successful vault writes and Settings closure.

If upstream behavior exposes password text, stop adoption. Review a narrow
protected-entry solution or an upstream fix before adding it; do not hide the
problem by disabling the failing probe or by calling the whole application
accessible while its credential control is unsafe.

## Accessibility activation and observation

Start the actual reader before Tk construction for the primary tests and test
late activation separately. Upstream detects a Windows screen-reader flag with
a Narrator-process fallback; available `tk accessible` commands or a generic UIA
client alone do not prove that the accessibility path is active.

Observe both MSAA and UIA with the actual reader running. Check every critical
input/button, selection row/header, overwrite decision and result action for
meaningful names/roles/states and correct focus. Test keyboard operation,
disabled controls, selection announcements, value changes, cancellation and
return focus. Preserve protected/password semantics in all observers and reports.
NVDA success does not imply Narrator success; record results separately.

Keep synthetic observer code outside the shipped worker/application payload.
Inspect only owned fixture processes/windows, including verified virtualenv
launcher/interpreter ancestry. Restore display/High Contrast changes and retain
phase/exit evidence when a probe fails. Exclude real credentials, taxpayer data,
personal browser state and private diagnostic logs from artifacts.

## Verification and adoption decision

1. Verify the exact candidate can build and load a matching `_tkinter`/Tcl/Tk
   in source and frozen applications; retain artifact inventories and hashes.
2. Pass the password-protection gate with each reader against both the source
   candidate and exact read-back frozen candidate before using real credentials.
3. Run the complete Windows GUI/native suite under the candidate launcher
   interpreter, plus portable tests, audit and source/frozen self-tests. Worker
   bootstrap/reuse verifies the unchanged managed production worker. Retain all
   existing gates; tests run only on the old Tk runtime cannot qualify the candidate.
4. Exercise actual NVDA and Narrator scenarios against both the source candidate
   and exact read-back frozen candidate, and inspect MSAA/UIA evidence.
   Mark unsupported or untested scenarios explicitly; do not infer reader speech.
5. Check normal/compact, High Contrast, actual DPI and cross-monitor behavior on
   a suitable GitHub runner. Measure performance using the unchanged observer.
6. Read back the exact candidate artifact by run/commit/artifact ID and verify
   allowlist, manifest and all hashes. Present results for a separate adoption
   review before replacing the normal distributed launcher runtime.

The first decision is whether to authorize this isolated candidate investigation
and its implementation plan. A failed compatibility, privacy or accessibility
gate leaves the current production runtime in place and returns concrete
evidence for the next design decision. A Tk 9.1 version string alone never
completes the original Windows accessibility item.
