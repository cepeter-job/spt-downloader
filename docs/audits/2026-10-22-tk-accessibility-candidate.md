# Isolated Tcl/Tk accessibility candidate — 22 October 2026

**Decision: do not adopt this candidate into production.** This investigation
built a matching CPython 3.14.8 x64/GIL launcher with Tcl/Tk 9.1.0, packaged and
read back the frozen application, and measured compatibility. Actual reader
activation before Tk fails during Settings construction. Late reader activation
has not established the required provider/speech behavior. Password accessibility
safety, full 200% display geometry and distinct-DPI monitor movement remain gates.
The combined Windows suite also fails two Tk setup cases; production adoption is blocked.

The normal distributed launcher, managed worker/CLI CPython 3.14.8, uv 0.13.4,
locks remain pinned. The worker resource allowlist now includes the reviewed main recovery modules. This branch is an unsigned
candidate for a separate adoption decision. Signing is deferred; the owner said
“I will test it later” for live Coretax/Excel acceptance. No real account or tax
data was used. Runtime execution took place only on GitHub runners.

## Latest main integration

The user authorized integration of all reviewed main changes, including PR #72,
into both working branches. Main `44969fcd73534153f5b656ec5ee9f5c8f11f42f4`
merged into the UI parent as `20cda264c28fd661f98c6b25bd09d1bf0a725173`,
then into this candidate as `35e091a236f6d8e628d8af58d970468ff9603246`
(tree `3d81fa6819d1fbc9cdaa614473fcfde6fa1aeeef`). Recovery files were preserved.
The candidate retains main's recovery, 43 worker resources, immutable build
identity, SBOM, exact executable bootstrap/reuse/cancellation verification,
manual-only benchmark and two-shard normal CI. Runtime pins remain unchanged.

**All evidence below for `e9391eb` and earlier is historical pre-integration
qualification. It does not qualify the combined tree.** Fresh combined candidate
runner results are recorded in the combined-tree section below. Candidate Windows execution now uses main's two
shards and strict inventory/outcome gate; no test skips or failures count as
successful coverage. A post-suite native hash inventory records whether the
pinned runtime files remain present and unchanged after tests.

Historical interim run `39728128973`, job `119656706698`, recorded 3734 passed
and two setup errors in 1123.16 seconds. Both were `tk.Tk()` fixture failures at
`tests/test_desktop_dialog_layout.py:56`, reporting that the candidate Tcl
`init.tcl` path could not be read because it did not exist. The affected cases
were `selection_empty...[False]` and `overwrite_response...[switched-io]`.
Without a post-failure inventory this does not establish permanent file deletion
or a root cause. Later old-head run `39728690587`, job `119658463630`, finished
with 3735 passed, one failure and one setup error (pytest 1428.72 seconds;
JUnit 1428.410 seconds). Its exact 3737-test inventory records exit status 1.
The selection-context setup reported the same unreadable `init.tcl`; the compact
bugreport-footer case `[540-430-1.5]` reported `invalid command name tcl_findLibrary`.
Managed worker fresh bootstrap/reuse subsequently passed with CPython 3.14.8.
Artifact `12405267796` ZIP SHA-256 is
`03a392418a5fd264d49bb6ffd73e8c7cac20dda9cc1cdad50140c243dc204273`.
## Historical evidence boundary

Task 4 began at `3beda5b8500eb9cf703c344654cc11dac2f13a60` and merged reviewed
parent `6026814c6b010af3afb24b2c83b5c3211f5c1155` as `636ad5e`. That merge added
parent audit documentation; the reviewed layout fix already matched the candidate.
The workflow keeps independent regression jobs running despite reader failures.
No normal production workflow was changed to obtain a passing result.

A finite candidate-only regression fixture supplements the narrower application
self-test. It invokes actual Settings and consent handlers, stale/Stop handling,
terminal UI eligibility and native owned-process cleanup using synthetic inputs.
The source suite additionally tests full controller/output eligibility, exit and
cleanup checks. A UI COMPLETE event with a synthetic path does not prove a real
export was verified. Masked-entry clearing tests are behavioral evidence, not
reader/provider secrecy, speech echo or copy acceptance.

## Native build custody and controlled repeat

Both builds used the same `build.ps1` blob
`7ba8fdc2dbc317ad3037930124fb1dc55c7d99d8` and `sources.json` blob
`888bf3908eb1371085c9335df14c500e0725d893`. The source manifest pins CPython
`8e6e75d9102e39bed2a2b279203a396741180f12`, Tcl
`0c6bad08d91fa2ad51f05a50a41f8c1ea82ce985` and Tk
`3f45110c0a568b70f2ebd5412f215e87d199bc7d`, with archive hashes and dependencies.
The controlled second build is retained rather than rebuilding on every edit.

| Run / attempt | Runtime artifact | Role |
| --- | --- | --- |
| 39717092291 / 1 | 12400030052 | First successful native build |
| 39718421643 / 1 | 12400037968 | Repeated build; pinned qualification input |

The first run head is `85c464e37d665558fb7d167671ef1d94c19d9e16`, tree
`5e242293c26bd4b4e414aa633866cb04529d96d5`. Its ZIP SHA-256 is
`19a8c748e2c3ae6a9f544758b32bb12c7ecf92351e2aa83fbf93281ec2b1643f`.
All 1,859 member hashes in each retained runtime matched their inventories.

The second run head is `0f699321614550c3d710cf66647878188d5f23ee`, tree
`cd74bf0f8a0613b63711ac621c63ade96c40c457`. Its ZIP SHA-256 is
`87b1ee844efa08398bb110f48335dfd68eeb2241da2bc6c38503e8448305fb4a`;
`inventory.json` SHA-256 is
`9758f2a63e8815952ca91178a9c20397f4292ad2aca8bfbff0feeb3c87b80239`.
Native build evidence artifact `12400930086` has ZIP SHA-256
`9ccf761de50dabb2a72e46d831d7d969e9c5f46130f0fff1756a980cb38b7356`.
Fresh-runner relocation/venv artifact `12400655959` has ZIP SHA-256
`d71f0a84b971e7606700eb49759a4adbdf4d947359bb34d88c8df618ef86ded8`.

The recorded source arrays and toolchain observations match: runner image
20261018.275.1, Visual Studio 18.11.12306.390, VC tools 14.51.36231/v145,
SDK 10.0.26100.0, compiler 19.51.36260.0, MSBuild 18.11.0.47511. Compiler
SHA-256 is `b0a1818ebae6da7f18230a84e76ce839212584ac4c2ab55b97a0d5268085da57`;
bootstrap SHA-256 is
`1b276111176d62c944c84ccffc25aa1b861d45fea27131a4c31326ed5c0fb417`.

**Not byte-reproducible.** Of 1,859 inventoried files per build, 1,825 match and
34 differ. All 34 differing files are same-size PE outputs with different COFF timestamps. The four principal files have
the same sizes but different COFF timestamps; CPython and `_tkinter` also embed
different UUID-based build-directory PDB paths. For example, python314.dll
TimeDateStamp changes from 1792639986 to 1792640953, and `_tkinter.pyd` from
1792639988 to 1792640956. These are directly observed nondeterministic metadata;
this comparison does not prove all other bytes become equivalent after stripping
metadata. No code-equivalence or byte-reproducibility assertion is made.

Both native log sets contain exactly three MSB3073 warnings for Git metadata
queries in source archives without `.git`, one C4267 size_t-to-int warning in
CPython `unicodedata.c`, and eight D9025 `/GL` overridden by `/GL-` warnings in
Tcl/Tk builds. The accompanying Git exit128 messages are bounded to those metadata
queries. These known warnings were retained, not blanket-suppressed. New warnings
or changed locations require inspection.

## Reader qualification

Final Task 3 qualification: head `3beda5b8500eb9cf703c344654cc11dac2f13a60`,
run `39727224679`, attempt 1; application artifact `12403407358`, EXE SHA-256
`b532e35e26d0fdb027eefaa5bd92324d53f71da31a1fcd8e0222bf1169e04204`.
All 22 application manifest members matched. Actual NVDA 2026.2.0.57664 and
Narrator 10.0.26100.33296 ran in isolated source/frozen scenarios.

With either reader started before Tk, source exits with TclError and frozen waits
until host readiness timeout; the recorded host phase is `before_settings`, with
`app.py` Settings/refresh calling `ttk.Widget.state`. The password gate is not
reached. This is an observed compatibility failure, not unavailable hardware.
Late activation produces reports but has not established Tk/provider activation
or speech coverage. All 20 late acceptance gates remain BLOCKED. No observed
provider/speech sentinel exposure is **not** a password safety pass.

All eight direct cleanup and owned-tree reports confirmed host/reader exit,
containment before resume, complete cleanup and no unverified process handles.
Screen-reader SPI state restoration completed. Earlier incomplete harness
failures remain historical evidence; the immutable snapshot correction and
complete diagnostics do not retroactively establish their causes.

## Remaining adoption requirements

A successful build, a version string, a screenshot or a zero process exit cannot
substitute for the required behavioral and accessibility observations. Preserve
separate passed/failed/blocked gates. Native reader compatibility and password
protection must pass before names/roles/values, focus, selection and speech can be
accepted. Actual 200% normal/compact geometry needs sufficient real work area;
cross-monitor acceptance needs actual movement between distinct-DPI monitors.
Missing suitable hardware stays BLOCKED.

The [operator procedure](../../scripts/launcher_candidate/README.md) gives runner
commands, custody rules and interpretation. A fresh whole-change review and a
separate draft candidate PR precede any future adoption decision. No release or
production merge is authorized by this report.

## Task 4 measured candidate and artifact custody

Current measured code head: `e9391eb68eb4f4f48fa0203878dfef36295959fc`, tree
`b6166db53a3e3a98e522b85d2932b5a3f89b142d`,
[run 39728690587](https://github.com/cepeter-job/spt-downloader/actions/runs/39728690587),
attempt 1. Later documentation commits do not inherit an execution claim for a
different tree; this section identifies the actual measured code revision.

The new finite behavioral fixture was tested RED at
`ae0fb88916b12fe4e3fb1de1473e2e62238dec00`, run 39728329144, job 119657347016:
1 failed/112 passed, rejecting the absent finite regression scenario. GREEN at
the measured code head, job 119658463647: 113 passed in 13.99 seconds under the
pinned candidate and existing hash-locked test environment.

| Artifact | Exact ID | ZIP SHA-256 |
| --- | --- | --- |
| Candidate application | 12403949028 | `0d54c5380da9c47bb24814b294b069b7359c7d205e4f23ad4b9d838b0fd5731f` |
| Fresh frozen readback | 12403689627 | `896d0eb15a8aeef9d2e2c58f57278cb5d5c8a664c70442515997ccfab897f478` |
| Portable tests | 12403594958 | `1cbeef19064500e68aed9c0f20f74c471a72bf51220a10abbe88d061ef01e5c8` |
| Locked dependency audit | 12403744223 | `2bd84cf7e82bafe889f98f095cbd33eae0331e9b998c0ce9d958d7712caf3589` |
| Production-mode exclusion | 12403629695 | `907db178a8144e1c49bc47f0da612449aee0ba3cb0704f9c7cea0d750d5f9855` |

These ZIPs were downloaded by exact artifact ID and independently hashed against
API digests. All 24 application manifest members match, with exactly 25 files
including the manifest. Candidate EXE SHA-256:
`c123b75a5b077ed40af40cfae9e8bd152d3fd4eed459fb3d5e8a1439a4c6934c`.

Source, packaged frozen and fresh exact-readback frozen regression reports each
pass all six behavioral checks, identify their correct mode, and contain 1,025
candidate native/script resource hashes matching the pinned inventory. The frozen
readback self-test reports `ok=true`, managed worker Python 3.14.8, connected
synthetic existing-workspace preferences loaded, before/after byte equality and
completed fixture cleanup. This does not establish reader/password acceptance.

Portable: 568 passed, zero failures/errors/skips, 42.829 seconds. Dependency audit:
46 locked Python packages, zero reported vulnerabilities. Current-source normal
production-mode build passed its frozen self-test and CArchive/PYZ exclusion;
no `scripts.launcher_candidate` fixture/probe modules were present. That diagnostic
EXE SHA-256 is `fbbafcb21385f157b17f4c5c322e2e7b7e9ea26aaf99fa4d80014b766d9fbabc`;
it was inspected on the runner and was not uploaded as a release payload.

The same measured run produced four independent reader artifacts, all bound by
`custody.json` to the application ID and EXE hash above:

| Reader / activation | Artifact ID | ZIP SHA-256 |
| --- | --- | --- |
| NVDA before Tk | 12403224945 | `7030327fa7a4801bc85ff2b4bca82291cb9e9b58d9d6d17429681bbe08a54e2e` |
| Narrator before Tk | 12403379607 | `07aded6220fee9e636e5698bb7fec41b8e3c4902e8b866de9aa6e0286ca6d89a` |
| NVDA late | 12404346257 | `87134adf34ece1068969cdf7e53e52c1e97821cdb2182a7111c9c42180b4d893` |
| Narrator late | 12404098879 | `85bd68be26e5490cf8b7cd2b563d9d584dce64c2073756e63f3b8b311d9597d8` |

Before-Tk source/frozen failures reproduce the same `app.py:1115` →
`app.py:961` → `ttk.py:572` TclError. Late reports preserve BLOCKED provider/speech
acceptance. All eight direct cleanup records show host and reader exited; all
eight owned-tree records show containment before resume, completed cleanup and
zero unverified processes. These newer artifacts preserve the Task 3 conclusion.

## Performance and actual display observations

Exact observer artifact `12404227467`, ZIP SHA-256
`4efd243818be13281ee29c6ff44ee66b7845cb760e7ac7f6eb27ce86f9a0b702`, belongs to
the measured code head/run/attempt above. Both raw pairs completed and were
internally comparable. Observer SHA-256 remained
`ce7f1f8ce6db98c0a452cd576e541ba5e33d08bf9eff72d9fd0bec3871db20c9`.
No timers, settling rules, sample counts or prewarming were changed.

The same runner used image 20261007.264.1, Windows 10.0.26100.0, native DPI 96,
100% monitor scale and the same work area/geometry. Corresponding cross-runtime
operations have identical synthetic payload hashes/bytes, dialog sizes, work
areas, scaling and awareness. Managed Python identifies MSC v.1944/Tcl/Tk 9.0.4;
the candidate identifies MSC v.1951/Tcl/Tk 9.1.0. This compares entire launcher
runtime builds; it does not isolate Tcl/Tk as the sole cause of the difference.

All values below are settled-opening medians in milliseconds. Each observer pair
uses reviewed UI baseline `cfa30a41e1106b8b0565c44b46da6b4ffdba0b4d` and the
measured current source under one interpreter.

| Dialog / records | Managed baseline | Managed current | Candidate baseline | Candidate current | Candidate current p95/max |
| --- | ---: | ---: | ---: | ---: | ---: |
| Selection / 1 | 56.30 | 56.55 | 69.55 | 64.91 | 76.72 |
| Selection / 100 | 61.82 | 67.05 | 84.19 | 82.10 | 89.55 |
| Selection / 1,000 | 79.99 | 81.78 | 99.29 | 97.46 | 118.86 |
| Overwrite / 101 | 91.49 | 90.62 | 138.14 | 120.44 | 163.36 |

The managed current pair meets the unchanged median-below-100-ms target; the
candidate fails it for overwrite. Relative to corresponding managed current
operations, candidate opening medians are approximately 15%, 22%, 19% and 33%
slower. Some individual samples exceed 100 ms even where the median passes.
All cancellation-service samples remained below 100 ms; the largest candidate
sample was 60.61 ms. Raw open/filter/sort samples and payload/environment evidence
remain in the artifact. Passing observer execution is not a performance pass.

Display started at 1024×768 with 1024×720 work area, one physical monitor at 100%.
The largest applied mode was 1920×1080 with 1920×1032 work area, still 100% and
native DPI 96. This does not meet actual 200% or distinct-DPI monitor requirements.
The observer attempted 12 main/selection/overwrite normal/compact cases across
original and High Contrast modes. It retained 70 screenshots. Representative
normal/compact and High Contrast frames were visually inspected; visible controls,
scrolling surfaces and the compact text/column constraints are actual 100%
observations, not a full accessibility or 200% acceptance claim.

The run is **FAILED/PARTIAL**: original-mode compact selection records “Stream was
not readable” after four snapshots, the close-command write also fails, and the
owned synthetic host needs forced cleanup (exit -1). Other eleven cases exit 0.
The retained original error lacks exception stack identity; its cause must not be
invented from the shared-file design. A separate diagnostic branch records bounded
exception types, HRESULTs, invocation command/line, phase and sanitized stack frames
without changing observer behavior, thresholds or timers.

High Contrast changes from flags 126, disabled, empty scheme to flags 127,
enabled, `High Contrast Black`. Restoration disables it and restores flags 126,
but retains `High Contrast Black` instead of the original empty scheme. Exact
High Contrast restoration therefore **FAILED**. The display mode did restore to
1024×768, 32-bit, 64 Hz, orientation 0 with native return code 0. Initial, changed
and restored state are retained. Fresh-window High Contrast observation is not
live-window theme-switch acceptance.

### Bounded follow-up on the display harness failure

A separate diagnostic branch `feat/tk-display-diagnostic` retains commit
`fe73e40951c57c973ad9626f027bfa3a57a102e0`, tree
`74ed38eba3925c7cae739679914c5f5866c355d0`, based on the measured candidate.
[Run 39729537226](https://github.com/cepeter-job/spt-downloader/actions/runs/39729537226),
attempt 1, job 119661163541 ran only the existing display observer/host with bounded
exception metadata added to its catch paths. Runtime inventory stayed pinned;
no flow, threshold, timer, provider or product changes were made. No full-suite or
packaging rerun was used for this diagnosis.

Artifact `12404428011`, ZIP SHA-256
`be83dd7d3f04e698df5d95dc966d9800c4434687e02f4c40c148519646dd6e1b`, was downloaded
by exact ID and hash-checked. All 12 cases exited 0, producing 72 screenshots; the
stream error did not recur, so no new exception identity was captured. Exact High
Contrast scheme restoration failed again. The original 70-frame candidate run
therefore remains FAILED/PARTIAL with an unresolved intermittent harness error.
This follow-up neither establishes its cause nor retrospectively passes it. The
diagnostic branch and worktree remain available for future controlled reproduction;
no speculative fix was merged into the candidate.

Static visual inspection used retained PNGs from the exact measured observer
artifact, not only JSON geometry: original main normal/compact frame 0; original
selection compact frame 0 and normal frame 5; original overwrite normal frame 0
and compact frame 5; High Contrast main compact frame 0, selection normal frame 0
and compact frame 3, and overwrite compact frame 0. Compact selection visibly
truncates long period/identifier cell text and exposes a horizontal scrollbar;
its lower detail area extends into the scrollable surface. Footer decision buttons
remain visible in these frames, with confirmation disabled for zero selection.
Original selection frame 5 shows the search caret; overwrite compact frame 5 shows
selected folder text after Tk-generated Tab bindings. These are not physical-keyboard
or reader-focus tests. High Contrast frames show dark surfaces, white borders/text
and yellow native chrome; no contrast-ratio or full usability pass is inferred.

The existing display observer does not capture Settings. Settings behavior was
exercised by source/frozen regression, but **Settings visual inspection is NOT
CAPTURED**. Complete layout acceptance remains unestablished, alongside actual
200% and distinct-DPI monitor movement. Missing coverage must be supplied before
future adoption; it is not converted to a pass by this failed investigation.

## Historical adoption gate summary (e9391eb)

| Gate | Status for the measured candidate | Evidence / limit |
| --- | --- | --- |
| Historical full Windows suite | FAILED | 3735 passed, one failure, one setup error; Tcl initialization failures; managed worker bootstrap/reuse passed |
| Native identity, loaded resources, relocated runtime | PASSED | Exact pinned inventory and earlier fresh-runner relocation/venv readback |
| Source/frozen/read-back behavioral safety fixture | PASSED for its stated scope | Six actual UI/native checks per mode; full controller/output gates additionally exercised by Windows suite |
| Portable tests and locked Python dependency audit | PASSED | 568 tests; 46 packages, zero reported vulnerabilities |
| Current-source production-mode fixture exclusion | PASSED | Actual CArchive and PYZ inspection plus normal frozen self-test |
| Before-Tk NVDA/Narrator compatibility | FAILED | Settings construction TclError in source/frozen |
| Password/provider/reader speech acceptance | BLOCKED | Password prerequisite not reached or late activation/provider/speech not established |
| Candidate settled-opening performance | FAILED | Overwrite median 120.44 ms exceeds unchanged 100 ms target |
| Complete normal/compact display observation | FAILED/PARTIAL | Original compact-selection fixture error; separate diagnostic did not reproduce it |
| Exact High Contrast restoration | FAILED | Disabled flag restored, original scheme not restored |
| Settings visual coverage | NOT CAPTURED | Existing display observer has no Settings scenario |
| Actual 200% and distinct-DPI monitor movement | BLOCKED | Only a single 100% monitor observed; no appropriate hardware demonstrated |
| Native byte reproducibility | NOT ESTABLISHED | 34 same-size native PE files differ; timestamps/debug paths differ |
| Signing and owner live acceptance | DEFERRED | Separate owner decision; no release/publishing claim |
| Fresh whole-change review / draft PR | CONTROLLER HANDOFF | Required before candidate handoff is closed; no production adoption |

## Combined collection boundary

Review identified that a candidate-only native test under `tests/` would skip
under normal production CI, violating main's strict completed-outcome gate.
The unchanged test now lives at `scripts/launcher_candidate/test_native_regression.py`
and is explicitly mandatory in candidate inventory and package verification,
with no environment skip. The combined shared collection is 3925 tests plus one
separate candidate-native qualification case. Source/frozen/readback behavioral
execution remains required. No production gate or native assertion was weakened.

## Combined-tree verification: 98461b6

Measured code `98461b655f672cc500593bfd875c6e5c1341e2f2`, tree
`3f35a8b1a412e9966f6b6173a658b452f51ff21a`, run `39731378364`, attempt 1,
includes the latest reviewed main and primary checksum repair `dd3407b`.
The mandatory four-file candidate contract command passed 113 tests in 10.37s
(job `119666961986`), including the explicitly separate native case.

| Proof | Exact artifact ID | ZIP SHA-256 |
| --- | --- | --- |
| Portable inventory/JUnit | 12405445750 | `2a084b080dbaf1b7bbf0a42340faf97374e0dd43fd2c6cf55d2c04656dc07d0d` |
| Production bundle exclusion | 12405308548 | `42f36a87638996ab5cba69b4961e663ba9d258dd286c671ffe74facdd5ec0fe9` |
| Dependency audit | 12404874276 | `c2192805427b10a6f0dffe99ec35be2dad5e308c35b0477fb18a984273f4d2f1` |

Exact readback metadata confirms 3925 shared tests collected, 670 portable tests
selected and passed, zero failures/errors/skips, JUnit 40.256s. The audit reports
46 packages and zero vulnerabilities. The normal production-mode EXE hash is
`e9d63c461764eca7683c7e01b5dda59c49cb3edf74befa7a61b45d45a60bff53`;
actual CArchive/PYZ inspection excludes candidate modules and its frozen self-test
passes with managed worker pin 3.14.8 and 43 worker resources. Subsequent combined
frozen readback, reader, observer and full Windows results follow below.

Combined application artifact `12405139152` has ZIP SHA-256
`f5b3f0348d65be1fe16718d2a51254dccf69aeb632c8ced4b36c1651288d9e21`;
readback artifact `12404854805` has ZIP SHA-256
`2cd05c07b5db20477d0ce8e15f411f0725695962be13104add7de897b9791b42`.
All 26 declared application members match their hashes and exact file set, with
27 case-insensitively unique files including the manifest. The executable hash
is `d8afdfda0024c2db7d8e750e3b3fe3b55ca3830a07a6ff8aa53de666c107e522`.
Build identity and the 1161-component SBOM bind that executable to the measured
commit/run/attempt. Native hashing is not a native vulnerability assessment.

Source, frozen and exact-readback behavioral reports each pass all six checks,
with correct source/frozen mode, no credentials/live scrape/accessibility
acceptance claim, and all 1025 candidate resource hashes matching the pinned
inventory. The actual existing-workspace fixture remains connected and unchanged
and its owned synthetic state is cleaned. The exact readback self-test passes.
Main's unchanged packaged-bootstrap validator confirms artifact `12405139152`,
matching executable/build identity, managed CPython 3.14.8 x64/GIL, bundled uv
0.13.4 with PATH uv absent, all 43 worker resources and six pinned worker packages.
Cold installation, ready-state reuse, cancellation and owned cleanup all pass;
foreign uv policy is ignored. These passes do not establish reader acceptance.

Combined reader custody binds the same head/run/attempt, application artifact
`12405139152` and executable hash above:

| Reader / timing | Exact artifact | ZIP SHA-256 |
| --- | --- | --- |
| Narrator before Tk | 12405895157 | `79b307df1f24f46bb9681bf4e8a08025288ea4b26efb9983dbbb90b43de0cd30` |
| NVDA before Tk | 12405586064 | `7a8dedd4171b163f5831d82c9d75993f614ccbd554ca0bf2c25b2756b4b9e92a` |
| NVDA late | 12405780584 | `5ee1c6691a521bf92900e3bfd562f34670fca7c15c24759a25dd21b26d90d7cb` |
| Narrator late | 12404974928 | `9ece5d3213b731e0b2e0e2cd8982cfacaf6b5f86126a0756a19bb5b1b560764e` |

Both readers before Tk still fail source and frozen Settings construction at
`app.py:1115` → `app.py:961` → `ttk.py:572`. The password gate is not reached.
NVDA late source/frozen and Narrator late source each retain five blocked outcomes
because Tk reader initialization/provider/speech acceptance was not established.
Narrator late frozen fails earlier: `checking_preexisting_reader`, RuntimeException,
HResult `-2146233087`, exit 1 without timeout or reader report. At that phase the
probe refuses a preexisting Narrator process. Its origin/ownership is not known
from retained evidence; it must not be inferred from the preceding source run.
That source run reports its direct host/reader exited. All eight outer owned-tree
reports confirm containment before resume and completed owned cleanup with no
unverified owned processes; seven reached direct host/reader cleanup and report
both exited. Frozen Narrator's refused prerequisite is not an accessibility or
password-safety pass. No speculative product fix or repeat was made.

Combined observer artifact `12405711442` ZIP SHA-256 is
`9cddebffdc34a9c45abcf2c91fb3b6617b3f14826ac1c602ec0f5fefa68d562e`.
Custody matches the measured head/tree/run/attempt and unchanged observer SHA-256
`ce7f1f8ce6db98c0a452cd576e541ba5e33d08bf9eff72d9fd0bec3871db20c9`.
Both paired runs completed and are internally comparable; corresponding runtime
samples also match payload bytes/hashes, dialog geometry, work area, DPI 96,
awareness 0, monitor scale 100%, Tk scaling 1.3330053300533005 and effective scale
0.9997539975399753. Managed Python uses MSC 1944/Tcl-Tk 9.0.4; candidate uses
MSC 1951/Tcl-Tk 9.1.0. This compares whole runtime builds, not an isolated Tk cause.

| Opening case | Managed baseline / combined median ms | Candidate baseline / combined median ms | Candidate p95 / max ms |
| --- | --- | --- | --- |
| Selection 1 | 87.5791 / 85.3621 | 98.0309 / 104.0711 | 109.4279 / 109.4279 |
| Selection 100 | 97.43425 / 97.1402 | 119.06085 / 123.13575 | 131.961 / 131.961 |
| Selection 1000 | 114.6944 / 114.6401 | 140.8942 / 150.3073 | 189.0544 / 189.0544 |
| Overwrite 101 | 126.0791 / 125.7377 | 161.65825 / 187.9517 | 221.5471 / 221.5471 |

Both current pairs fail the unchanged median-below-100-ms opening target.
Candidate opening is about 22%, 27%, 31% and 49% slower than the corresponding
managed measurements. All cancel samples remain below 100 ms; candidate maximum
is 76.2643 ms. All ten operations' raw samples and payload identities are retained.

The combined display run completed all 12 scenario/layout/contrast cases with
exit 0 and 72 screenshots; every frame's exact path hash matches its report.
The historical stream error did not recur and remains unexplained, not erased.
The combined job still fails exact High Contrast restoration: original flags
126/scheme empty, enabled flags 127/High Contrast Black, restored flags 126 but
scheme still High Contrast Black. Display mode restored to 1024×768/32-bit/64 Hz,
orientation 0 with native return code 0. The observed enlarged display is one
1920×1080 monitor, work area 1920×1032, at 100%; no actual 200% or distinct-DPI
movement was qualified. UIA expected input/table role exposure remains absent.

Static image inspection covered combined `original-main-compact/frame-0.png`,
`original-selection-normal/frame-5.png`, `original-selection-compact/frame-0.png`,
`original-overwrite-compact/frame-5.png`,
`high-contrast-selection-compact/frame-3.png` and
`high-contrast-overwrite-normal/frame-0.png`. Footer actions remain visible;
compact selection cells truncate long period/ID strings with horizontal scrolling,
and lower details use the vertical scroll area. The search caret and selected
folder text are visible after fixture-generated actions. High Contrast shows dark
surfaces, light borders/text and yellow chrome, without a contrast-ratio or reader
focus acceptance claim. Settings remains uncaptured; 100% screenshots cannot
establish 200% layout acceptance.

Combined Windows shard artifacts are:

| Shard / job | Artifact | ZIP SHA-256 | JUnit outcome |
| --- | --- | --- | --- |
| 0/2 / 119666961917 | 12406325059 | `9a93ea89ced3c885be783e2b60b839d8f26c0a3c00511623f9e596e0e28a4c11` | 2008 passed, one setup error; 574.361s |
| 1/2 / 119666961879 | 12405113701 | `dfdcb6754c9782e178f5d96be308087443e09dcf8b7f099c1b051a99c6158eec` | 1915 passed, one setup error; 575.413s |

Both inventories bind the measured head/run/attempt, agree on 3925 collected
shared tests, select disjoint partitions with union exactly 3925, and report exit
status 1 with no skips. Thus the suite records **3923 passed and two setup errors**;
complete successful coverage is FAILED. The strict aggregate job `119670224595`
failed its `REGRESSION_RESULT=failure` prerequisite before invoking the inventory
verifier. The independent inventory inspection above is not a passed coverage gate. Shard 0's
`test_selection_context_uses_matching_job_snapshot` reports unreadable `init.tcl`;
shard 1's `test_selection_empty_and_no_match_keep_exact_counts[False]` reports
unreadable `auto.tcl`. Both originate in Tk initialization in the real dialog
fixture. No tests, thresholds or product/runtime behavior were weakened.

Both post-suite inventories show all 1859 pinned runtime files present with their
expected hashes. In particular `init.tcl` is
`636818d3e4071d28ffb610c86d895cb4f0cff57ddf7d8523dabf1feed821ca9f`
and `auto.tcl` is
`1953e3830f90106aa322cfc66644cc36ae39f8350bf214f07fa4d75afd80da02`
on both runners after their suites. This establishes intact bytes at the later
checkpoint, not the cause of the earlier read failures or continuous availability.
It does not support a permanent deletion claim. Managed worker fresh bootstrap
and verified reuse subsequently passed with CPython 3.14.8. No speculative
runtime fix or extra rerun was used to turn these failures green.

## Combined adoption decision and handoff

| Gate for measured code 98461b6 | Result |
| --- | --- |
| Exact native inventory / retained controlled build comparison | Identity verified; byte reproducibility not established |
| Mandatory candidate contracts, including separate native case | 113 passed |
| Source/frozen/exact-readback behavioral safety | Six checks passed per mode; scope excludes reader acceptance and real export verification |
| Full shared Windows suite / strict coverage | FAILED: 3923 passed, two Tk setup errors; no skips or inventory gaps |
| Managed source worker bootstrap / reuse | PASSED, production CPython 3.14.8 |
| Exact frozen managed bootstrap / reuse / cancellation / owned cleanup | PASSED with exact artifact/executable/build identity |
| Portable suite / Python dependency audit | 670 passed; 46 packages, zero reported vulnerabilities |
| Normal-mode candidate fixture exclusion | PASSED on actual current-source CArchive/PYZ |
| Before-Tk reader compatibility | FAILED for both readers in source/frozen Settings |
| Late reader/provider/password/speech qualification | BLOCKED; Narrator frozen additionally refused a preexisting reader |
| Settled-opening performance | FAILED; candidate medians 104.07–187.95 ms, unchanged target below 100 ms |
| Normal/compact observed display cases | 12 cases exited 0, 72 frame hashes verified; limited representative visual inspection |
| Exact High Contrast restoration | FAILED; scheme mismatch persists |
| Settings visual / actual 200% / distinct-DPI movement | NOT CAPTURED / BLOCKED / BLOCKED |
| Signing / owner live acceptance | DEFERRED |
| Production adoption | BLOCKED; no runtime upgrade, release or merge authorization implied |

Task 4 source/spec review on `3beda5b..98461b6` found no Critical or Important
implementation findings. Its README platform-wording Minor is corrected. The
controller still owns the final evidence/documentation review, fresh whole-change
review and separate draft PR. This documents a failed qualification candidate,
not a completed production accessibility upgrade. The diagnostic branch and all
recovery/SDD material remain preserved.
