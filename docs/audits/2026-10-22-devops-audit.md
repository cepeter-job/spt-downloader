# SPT Downloader — Full DevOps Audit and Completed Checklist

**Audit date:** 22 October 2026 (WIB / Asia–Jakarta)
**Repository:** [cepeter-job/spt-downloader](https://github.com/cepeter-job/spt-downloader)
**Audited main:** [`d402b98a1a534f761e60500fc1cc17f367461298`](https://github.com/cepeter-job/spt-downloader/commit/d402b98a1a534f761e60500fc1cc17f367461298)
**Primary execution evidence:** [run 39629732190, attempt 1](https://github.com/cepeter-job/spt-downloader/actions/runs/39629732190)
**Audit completion:** 5/5 work stages completed. All 60 checklist items assessed; unresolved controls retain their actual status.

## Verdict

**The current CI and build pipeline is healthy and strongly protected. Operational recovery and durable distribution still need work.** No critical or high-severity issue was established in the inspected scope. Three controls have concrete source/configuration counterexamples: cancellation checkpoint durability, abandoned temporary-profile cleanup, and preservation of a main code build when a documentation-only push follows it. The latest build itself passed.

**Checklist result:** 37 PASS · 3 FAIL · 12 PARTIAL · 7 UNVERIFIED · 1 N/A.

“Completed” means the audit work is complete, not that every control passed or every finding was fixed. PASS can be supported by source inspection, live repository configuration or execution evidence; each row states its evidence. FAIL means a demonstrated violation of the assessed control, not necessarily an incident in the latest run. PARTIAL identifies a material boundary or maturity gap. UNVERIFIED identifies missing evidence rather than assumed failure. N/A is excluded from readiness judgments.

This is an audit deliverable. No source, repository setting, PR, release, branch or production installation was changed.

## 1. Scope and evidence

The review covered repository governance, both versioned workflows, routing and required gates, runners, cache trust, test inventory, dependency locks/audits, packaged artifacts, bootstrap, credentials and diagnostics, process cancellation, output publication, recovery and runbooks. Three independent workstreams reviewed CI, supply chain and operations; findings were reconciled against the actual source and downloaded evidence.

Repository instructions require pytest, application imports, native/Tk/browser fixtures, self-tests, builds and EXE execution to run on GitHub runners. Those instructions were respected. Local verification was limited to source/AST inspection and parsing/hashing already-produced evidence. The 246 tracked Python files parsed without AST errors. A narrow current-tree search for three credential/private-key signature families found no candidates; this is not a complete secret scan.

The API returned zero open PRs, zero open issues, no releases and no tag refs. Two branches were visible: main and feat/ui-delivery-completion. The remaining feature branch was not classified as stale merely because it lacks an open PR.

### Verified execution at the audited SHA

| Workload | Passed | Failed / errors / skipped | Pytest duration | Setup after checkout | uv / Python cache |
| --- | ---: | --- | ---: | ---: | --- |
| Windows shard 0 | 1,826 | 0 / 0 / 0 | 610.375 s | 6.754 s | hit / hit |
| Windows shard 1 | 1,770 | 0 / 0 / 0 | 621.664 s | 7.094 s | hit / hit |
| Portable Linux | 568 | 0 / 0 / 0 | 36.589 s | 3.514 s | hit / hit |

**Windows total: 3,596 passed.** The portable 568 are a Linux execution of an overlapping subset, not 568 additional distinct Windows cases. The original inventories were downloaded independently: both shard selections are disjoint, their union exactly covers all 3,596 collected IDs, and the portable selection is a subset. All three bind to the same full inventory, commit, Python version, run and attempt. The two Windows jobs have distinct GitHub runner identities.

The main pipeline reached the required aggregate in **12m18s**, and its last executed cleanup job completed in **12m36s** after run creation. Package took **44s**, attestation **15s**, and the maximum observed per-job queue was **4s**. Windows runner wall time summed to **22m41s**; all nine jobs summed to **24m09s**. These are capacity measurements, not CPU use or billed cost.

Two adjacent PR70 full runs reached their final gates in **12m43s** and **12m56s**, using job completion timestamps. Their workflow `updated_at` fields were later; treating those metadata updates as execution end times would incorrectly report much longer builds. The latest main's created-to-updated interval is 12m38s, which is not its required-gate latency.

The current shards differ by **11.290 seconds (about 1.8%)**. More shards or a more complex scheduler are not justified by these measurements. Earlier five-pair sharding results at `a6afdb97...` and scoped browser-reuse results are historical comparisons, not new speedups measured at this audited SHA. **Priority 4 browser reuse/readiness work is already completed through PR69/70**; the newer [completion report](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/audits/2026-10-21-browser-fixture-completion.md) supersedes older pending-work wording.

### Artifact and dependency evidence

| Item | Verified result |
| --- | --- |
| Distribution artifact | [12359181813](https://github.com/cepeter-job/spt-downloader/actions/runs/39629732190/artifacts/12359181813), 28,495,230 ZIP bytes |
| ZIP SHA-256 | `af2fc36d59ea7acba7d23abb2274dd23333698dfcd7500a600976e670d862898` |
| Executable SHA-256 | `3746a2a88ec5d5cb965a3cd05a8b4111ae164f73f1180e8f93b62bd8fea70cae` |
| Allowed payload | SPTDownloader.exe, LICENSE.txt, README.txt, build-selftest.json, SHA256SUMS.txt; all four listed payload hashes matched |
| Frozen self-test | ok=true; CPython 3.14.8, 64-bit, GIL enabled; Tcl/Tk 9.0.4; uv bundled; no live scraping or credential access |
| Python dependency audit | [artifact 12358078387](https://github.com/cepeter-job/spt-downloader/actions/runs/39629732190/artifacts/12358078387): 46 distributions, zero reported vulnerabilities, zero skipped distributions |
| Build provenance | [attestation 58279383](https://github.com/cepeter-job/spt-downloader/attestations/58279383): EXE and checksum manifest; trusted main-only job succeeded |
| Publisher signature | PE certificate directory offset/size are zero; Authenticode is absent and documented |
| Expiry | 4 November 2026, 23:04:59 WIB for the current distribution artifact |

All **eight** archives from the run were downloaded and their SHA-256 digests matched GitHub metadata: package, dependency report, three test-result archives and three inventory archives. The audit did not execute the EXE locally. Provenance generation/publication was confirmed in the job log; independent consumer-side signature verification was not rerun. A clean Python-package audit is not a statement about all native components or the absence of application vulnerabilities.

## 2. Findings and bounded fixes

### F1 — Medium: cancellation can damage the previous valid aggregate checkpoint

**Location:** [spt_desktop/worker.py:118-125](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/worker.py#L118-L125); compare the existing durable writer at [coretax_browser.py:1259-1281](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/coretax_browser.py#L1259-L1281) and its normal use at [coretax_browser.py:1561-1562](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/coretax_browser.py#L1561-L1562).

The Stop handler opens `run.json` directly with `write_text`. After successful detail capture, disk exhaustion, an I/O failure or process termination during this write can truncate the previous aggregate. An error inside that exception handler also bypasses its worker terminal emission. Individual return checkpoints may survive; offline reconstruction can still fail because it reads the damaged aggregate. The controller continues to honor Stop, so this finding is not evidence of false GUI COMPLETE.

**Fix:** use the existing atomic checkpoint policy for cancellation, preserve the previous file on failure, and keep CANCELLED reporting failure-safe. Preserve individual checkpoints and original evidence.

**Acceptance:** runner-only partial-write, ENOSPC and replacement-failure cases must retain a parseable old or complete new aggregate, preserve return files, emit cancellation, and allow offline reconstruction from retained valid data.

### F2 — Medium: forced Stop can retain temporary login profiles

**Location:** [spt_desktop/auth.py:346-352](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/auth.py#L346-L352), [spt_desktop/worker.py:49-56](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/worker.py#L49-L56) and [spt_desktop/controller.py:313-320](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/controller.py#L313-L320).

Account-bound exports and credential checks create persistent browser profiles under `cache/login-run-*` and `cache/login-check-*`. Ordinary cleanup relies on Python context managers. The intentional forced-stop path terminates the owned Windows process tree, bypassing that cleanup. No parent-side or next-start reconciliation for abandoned profiles was found.

Residual directories can consume space and may retain browser session state. No actual session contents were inspected, and this does not imply plaintext password storage or cross-user access. The intentional default persistent profile is a separate case.

**Fix:** track temporary-profile ownership, reclaim only inactive application-owned directories after the process tree exits, and provide conservative next-start recovery. Never remove active/default profiles, unrelated files, reparse targets or tax recovery data.

**Acceptance:** synthetic Windows forced-termination tests for both profile prefixes, with active-profile, junction and unrelated-directory protections.

### F3 — Medium: frozen bootstrap can inherit external uv selection and policy

**Location:** [spt_desktop/runtime.py:166-183](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/runtime.py#L166-L183), [spt_desktop/runtime.py:226-234](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/runtime.py#L226-L234) and [spt_desktop/runtime.py:255-271](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/runtime.py#L255-L271).

The launcher tries PATH `uv` before the bundled copy and accepts the matching version string. It copies most of the parent environment and does not disable uv configuration discovery. Consequently, the isolated runtime's acquisition policy can depend on the launching machine rather than only the reviewed package. Official uv documentation confirms that [UV_PYTHON_DOWNLOADS_JSON_URL](https://docs.astral.sh/uv/reference/environment/#uv_python_downloads_json_url) can replace the embedded interpreter catalog, and [configuration discovery](https://docs.astral.sh/uv/concepts/configuration-files/) includes project/user settings.

This is a source-supported isolation/reproducibility gap requiring influence over the local environment/configuration. No remote unauthenticated exploit or current tampering was established. Hash-required wheel installation and post-install checks remain real controls.

**Fix:** use the bundled uv for frozen operation, explicitly control supported environment overrides, and disable unrelated configuration discovery. Preserve legitimate enterprise proxy/certificate settings through an intentional policy.

**Acceptance:** runner-only contaminated-PATH, UV_* and uv.toml cases must choose the reviewed tool/configuration and retain package-hash and interpreter checks. Pair this work with F7.

### F4 — Medium: verified builds do not have a durable release and rollback channel

**Location:** [.github/workflows/windows-build.yml:404-417](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/.github/workflows/windows-build.yml#L404-L417); [releases API](https://api.github.com/repos/cepeter-job/spt-downloader/releases); [docs/python-314.md:86-92](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/python-314.md#L86-L92).

The README directs users to Actions artifacts retained for 14 days. No tags or GitHub Releases exist. The current executable is available now but expires on the date above; no durable current/previous supported binary pair or actual rollback rehearsal was established. Rebuilding an old commit is not equivalent to retaining the original verified bytes. The documented historical Python 3.11 artifact is not an automatically suitable rollback target.

**Fix:** choose a versioned distribution policy, promote exact verified artifact bytes with source/run/artifact coordinates, checksums and provenance, and retain at least the supported rollback target for its agreed support period.

**Acceptance:** prove a fresh download after promotion matches the verified bytes, then exercise upgrade and rollback using synthetic state on a Windows runner while preserving profiles, checkpoints and outputs.

### F5 — Medium: documentation supersession can cancel the last code build

**Location:** [.github/workflows/windows-build.yml:25-28](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/.github/workflows/windows-build.yml#L25-L28); [scripts/ci_route.py:25-33](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/scripts/ci_route.py#L25-L33) and [scripts/ci_route.py:104-133](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/scripts/ci_route.py#L104-L133).

All main push runs share a cancelling concurrency group. If code commit A is building when documentation-only commit B arrives, B can cancel A, compare only A→B, select the docs fast path and finish green with packaging/attestation skipped. The last code change can therefore lack a completed trusted post-merge artifact. Prior successful PR tests are not erased. This is a demonstrated configuration race, not an incident observed in the latest successful run.

**Fix:** keep stale-PR cancellation while preserving active and pending main code builds. Unique main-push groups are a simple option. A preserved queue is another option after validating supported syntax. Setting only `cancel-in-progress: false` does not solve replacement of the default single pending run. [GitHub concurrency semantics](https://docs.github.com/en/actions/concepts/workflows-and-actions/concurrency) distinguish running cancellation from pending replacement.

**Acceptance:** test code→docs and multiple-pending-push scenarios, preserve the documentation optimization, and demonstrate a completed main package/provenance path for the code revision. Update the existing structural workflow contract to express this behavior.

### F6 — Medium: desktop selection is not preserved by CLI continuation

**Location:** [spt_desktop/interaction.py:15-41](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/interaction.py#L15-L41), [coretax_browser.py:1375-1382](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/coretax_browser.py#L1375-L1382) and [coretax.py:444-449](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/coretax.py#L444-L449).

Desktop filtering keeps the full inventory on disk but uses selected-list ordinals for detail checkpoints. For inventory `[A,B,C]` and selection `[B,C]`, B can be saved as `returns/0001.json`. CLI `--resume` reloads the full inventory and attempts to bind that checkpoint to A; provenance rejects it. A prefix selection can instead allow continuation into records outside the original desktop selection because the selection is not reapplied.

The README correctly labels `--resume` as CLI recovery. This is a desktop recovery coverage gap, not a claim that the documentation promises transparent desktop continuation. Offline `--from-json` reconstructs captured output but does not finish capture.

**Fix:** persist a selection/mode manifest bound to job, inventory and record identities, then preserve that exact scope on continuation. A smaller interim control is explicit rejection of selected desktop folders in CLI resume with a clear supported recovery procedure. Do not advise manual checkpoint editing.

**Acceptance:** nonprefix, prefix and all-record selections; Stop immediately after selection and after partial capture; JSON-first mode; exact reuse; no expansion beyond consent.

### F7 — Medium: packaged first-run worker setup has no direct execution evidence

**Location:** [scripts/ci_runtime.py:20-60](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/scripts/ci_runtime.py#L20-L60), [spt_gui.py:19-52](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_gui.py#L19-L52) and [spt_gui.py:144-145](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_gui.py#L144-L145).

The source worker bootstrap is exercised, and the frozen GUI self-test passes. However, frozen self-test injects a synthetic controller, checks that bundle files exist, and reports the configured worker version. It does not install/use a worker through the actual distributed EXE. A bundle extraction/path/dependency problem on a clean machine without PATH uv can evade those separate tests.

**Fix:** add a bounded account-free packaged-bootstrap smoke mode using the exact read-back EXE, an empty workspace and no external uv.

**Acceptance:** verify managed interpreter identity, locked imports/resources, reuse, cancellation and owned cleanup; bind results to the artifact digest. This is a coverage gap, not an observed installation failure.

### F8 — Medium residual risk: publication is not crash-atomic

**Location:** [spt_desktop/output.py:591-655](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/output.py#L591-L655); [README.md:89-93](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/README.md#L89-L93).

Staging, consent, identity checks and ordinary exception rollback are strong. Multi-file replacement still uses an in-memory journal. Abrupt termination can leave mixed old/new files or displaced originals before a recovery notice is written. The README explicitly disclaims transactional guarantees for process death/power loss.

**Decision required for future hardening:** preserve this documented limitation with a tested recovery procedure, or add a durable publication manifest/restart recovery or whole-new-folder publication. This is not an undisclosed promise violation.

**Acceptance:** synthetic Windows kill-at-barrier/restart tests around replacement operations must identify a consistent recoverable set and preserve bytes/links. Existing exception-injection tests alone do not establish this guarantee.

### Additional improvements, after the findings above

| Control | Remaining boundary | Proportionate next improvement |
| --- | --- | --- |
| Unexpected test skips | Inventory proves selection and session success; JUnit outcomes do not gate package. Current run has zero skips. | Explicit per-workload skip allowances and CI precondition failures; preserve justified platform exclusions. |
| CI uv archive pin | setup-uv is commit-pinned, but uv 0.13.4 uses the mutable upstream manifest checksum because this action revision's known table ends at 0.13.0. SHA-256 checking exists. | Reviewed platform-specific checksum inputs or immutable manifest snapshot. |
| SBOM/native advisory coverage | Python audit excludes a complete assessment of CPython, Tcl/Tk, native uv and browser prerequisites. | Versioned component inventory and upstream advisory review; do not label the whole application vulnerability-free. |
| Authenticode publisher identity | Provenance and checksums do not provide a Windows publisher signature. Current absence is disclosed. | Decide whether publisher signing is required for distribution; if enabled, attest and hash final signed bytes. |
| Private storage and support identity | Jobs/captures/recovery lack a lifecycle/capacity procedure; diagnostic logs lack immutable application build ID. | Safe user-reviewed storage inventory/retention and a fixed, nonsecret build ID in session diagnostics. |

The immutable-checksum finding was checked against the exact upstream action revision: [checksum selection](https://github.com/astral-sh/setup-uv/blob/1c37ad07a6a961277cf70c0d37d6f313000f5884/src/download/checksum/checksum.ts), [known checksums](https://github.com/astral-sh/setup-uv/blob/1c37ad07a6a961277cf70c0d37d6f313000f5884/src/download/checksum/known-checksums.json), and [manifest URL](https://github.com/astral-sh/setup-uv/blob/1c37ad07a6a961277cf70c0d37d6f313000f5884/src/utils/constants.ts). The separately bundled uv comes from a hash-locked build wheel and is not described as unverified.

## 3. Completed 60-control checklist

Each row has been assessed. A completed assessment does not close its remediation. The execution evidence above is bound to the exact main SHA; static findings are explicitly source-supported.

### Governance

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| GOV-01 | **PASS** | Exact source identity and clean audit checkout | Remote main and local git object match d402b98a1a534f761e60500fc1cc17f367461298; 332 tracked files; source unchanged. |
| GOV-02 | **PASS** | PR and strict required checks enforced | Live active ruleset 24914050 requires PR, Windows tests and dependency audit, and CodeQL; no bypass actors. |
| GOV-03 | **PASS** | Main deletion and force-push prevented | Live ruleset contains deletion and non_fast_forward protections; main is protected. |
| GOV-04 | **PASS** | Review policy is explicit and fits the current maintainer model | Zero required human approvals is documented for a solo maintainer. No CODEOWNERS requirement; this is an intentional policy, not a failed check. |
| GOV-05 | **PASS** | Branch cleanup preserves unrelated work | cleanup_branches.py checks ancestry, exact head, active PR use and protected state, then uses force-with-lease. Two branches and zero open PRs/issues observed. |

### CI orchestration

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| CI-01 | **PASS** | Triggers and conservative change routing | PR/main workflow has no path filter; unknown paths or unavailable diff select full validation. Weekly schedule selects dependency audit. |
| CI-02 | **PASS** | Required-job aggregation fails closed | Latest aggregate passed. Historical failed main run 39590576108 failed aggregate and skipped package/provenance after a Windows failure. |
| CI-03 | **FAIL** | Main code builds survive following documentation pushes | Shared main-push cancellation can discard a code build; a following docs route can finish green without replacement package/provenance. F5. |
| CI-04 | **PASS** | Token permissions and checkout credentials are limited | contents:read default; no persisted checkout credentials; OIDC/attestation and cleanup write permission isolated to trusted main jobs. |
| CI-05 | **PASS** | Runner isolation, timeouts and PR supersession | Hosted Windows/Linux runners; isolated Windows jobs; serial pytest per runner; explicit 3–30 minute job budgets; PR supersession. |

### Test evidence

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| TEST-01 | **PASS** | Full Windows suite on audited main | Exact-run JUnit: 1,826 + 1,770 = 3,596 passed; zero failures, errors or skips. |
| TEST-02 | **PASS** | Portable Linux subset on audited main | 568 passed on CPython 3.14.8; zero failures, errors or skips. This overlaps the Windows inventory. |
| TEST-03 | **PASS** | Complete original inventory and revision binding | All three downloaded inventories contain the same 3,596 collected IDs; shard selections disjoint and cover all; portable selection is a subset; commit/run/attempt/runtime match. |
| TEST-04 | **PARTIAL** | Unexpected test skips block distribution | Current run has zero skips, but package verifies selected IDs and session exit status, not each case outcome. Add reviewed platform-specific skip allowances. |
| TEST-05 | **PASS** | Failure evidence survives ordinary test failures | JUnit/measurements/inventory uploads use always() after attempted tests; nonzero PowerShell exits propagate. Hard runner termination remains an explicit limit. |

### Performance and cache

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| PERF-01 | **PASS** | Parallelism is justified and balanced | Two Windows pytest sessions: 610.375 s and 621.664 s; difference 11.290 s, about 1.8%. No evidence for additional shards. |
| PERF-02 | **PASS** | Cache keys and writers respect trust boundaries | OS/architecture/Python/workload/lock inputs included; only trusted main pushes write caches; only shard 0 writes the shared integration cache. |
| PERF-03 | **PASS** | Current cache-hit status and setup times are recorded | Both uv and managed-Python cache hits true in all three measurement files; setup after checkout 6.754/7.094/3.514 s. |
| PERF-04 | **PASS** | Historical cold/warm comparisons are scoped correctly | Five paired pipeline runs at a6afdb97... include restored and cold cases. Their 40.54% median reduction is historical, not a new measurement on d402b98. |
| PERF-05 | **UNVERIFIED** | Peak memory, CPU use and billed cost | Runner wall seconds were calculated, but no peak-RAM/CPU/billing measurements were available. No monetary-savings claim is made. |

### Dependencies

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| DEP-01 | **PASS** | Direct and transitive dependencies are exactly pinned and hashed | runtime/test/build/audit locks have 6/13/21/28 pins and 95/180/223/378 SHA-256 entries; no malformed, unhashed, duplicate or cross-layer version drift. |
| DEP-02 | **PASS** | Python dependency vulnerability audit has current evidence | Exact-run pip-audit JSON covers 46 distributions, zero reported vulnerabilities and zero skipped distributions as of the CI execution. |
| DEP-03 | **PASS** | Ongoing dependency review is configured and has run | Weekly pip/Actions Dependabot configuration; scheduled audit run 39226957179 completed successfully on 19 October. |
| DEP-04 | **PARTIAL** | CI uv archive identity is immutable | uv version and action commit are pinned, and SHA-256 is checked; selected uv 0.13.4 checksum falls back to a mutable upstream version manifest. Add reviewed checksum inputs. |
| DEP-05 | **PARTIAL** | Shipped native components and SBOM are covered | Python audit does not establish native CPython/Tcl/Tk/uv/browser advisory status. No full component SBOM is produced. |

### Build and distribution

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| BUILD-01 | **PASS** | Packaging follows tests, audit and GUI checks | Source GUI and frozen GUI self-tests passed after inventory and dependency gates; source worker setup/reuse also passed. |
| BUILD-02 | **PASS** | Downloaded package identity and contents are verified | Artifact 12359181813 has exactly five allowed files; ZIP digest matches GitHub; all four SHA256SUMS entries match downloaded bytes. |
| BUILD-03 | **PASS** | Trusted build provenance is generated | Main-only attestation job succeeded for EXE and checksum manifest; attestation 58279383 published. Independent consumer signature verification was not rerun in this audit. |
| BUILD-04 | **PARTIAL** | Publisher Authenticode signing | Executable PE certificate table offset/size are zero; absence is explicitly documented. Publisher signing is a distribution-policy decision. |
| BUILD-05 | **PARTIAL** | Durable versioned downloads and rollback targets | No tags or GitHub Releases; current build artifact expires 4 November 2026 at 23:04:59 WIB. Retained current/previous verified release bytes not established. F4. |

### Runtime bootstrap

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| RUN-01 | **PASS** | Worker interpreter and package identity are checked | Managed CPython 3.14.8 x64/GIL and location checks; required locked package versions/imports; source-resource fingerprint and readiness revalidation. |
| RUN-02 | **PARTIAL** | Frozen bootstrap is isolated from external tool/config choices | PATH uv precedes bundled uv; inherited UV_* and configuration discovery remain. F3. |
| RUN-03 | **PARTIAL** | Actual distributed first-run worker bootstrap is exercised | Source bootstrap and frozen GUI tests are separate; frozen self-test uses a synthetic controller. No actual packaged cold bootstrap with PATH uv absent. F7. |
| RUN-04 | **PASS** | Owned processes and terminal outcomes are reconciled | Suspended children assigned before resume; cooperative Stop followed by 15-second owned-tree kill; controller checks terminal status against exit code. |
| RUN-05 | **PASS** | Bootstrap and IPC waits have explicit bounds | Subprocess timeouts, cancellation polling and bounded IPC are present. This does not claim every browser call has a strict global wall-clock bound. |

### Observability

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| OBS-01 | **PASS** | Diagnostics use a privacy-focused event schema | Allowlisted structured fields, stages, durations and safe error categories; no raw browser stdout/stderr, payload or credential logging in diagnostic channel. |
| OBS-02 | **PASS** | Diagnostic disk retention is bounded | 1 MiB segments; three segments/session; seven-day retention; 32-file directory budget; active/unrelated/link targets preserved. |
| OBS-03 | **PASS** | Diagnostics do not determine business success | Bounded queue/store and failure isolation; COMPLETE requires business and process reconciliation, not a log message. |
| OBS-04 | **PARTIAL** | Logs identify the immutable application build | Session includes Python/frozen metadata but not application commit/build ID. Current bug reporting requires manual artifact identity. |
| OBS-05 | **UNVERIFIED** | Failure notifications reach an accountable maintainer | Workflow results and diagnostics exist; notification subscription and response ownership were not independently confirmed. |

### Recovery

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| REC-01 | **PASS** | Normal detail checkpoint writes preserve prior state | Normal detail and aggregate writes use exclusive temp creation, flush/fsync and replace under path guards. |
| REC-02 | **FAIL** | Cancellation preserves the last valid aggregate checkpoint | worker.py writes run.json directly during cancellation. Partial write/ENOSPC/termination can truncate prior aggregate and bypass worker terminal emission. F1. |
| REC-03 | **PARTIAL** | Interrupted desktop selections resume within the same scope | CLI resume reloads full inventory, while desktop checkpoints use selected-list ordinals. CLI-only recovery is documented; selected desktop continuation is not complete. F6. |
| REC-04 | **PASS** | Normal publication failures preserve rollback evidence | Verified staging, overwrite consent, identity/path checks and exception rollback preserve old bytes and unresolved recovery. |
| REC-05 | **PARTIAL** | Abrupt termination has durable publication recovery | Multi-file replacement is not crash-atomic; in-memory journal and exception recovery do not establish restart recovery after power loss. Explicitly documented. F8. |

### Credentials and privacy

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| PRIV-01 | **PASS** | Credentials are origin-bound and stored in the OS credential store | Windows Credential Manager with exact approved origins; no password/token/cookie in preferences; manual challenge handling retained. |
| PRIV-02 | **PASS** | Private selection messages do not enter public diagnostics | Job-bound private message files, bounded size, strict schema and protected path handling; safe progress protocol. |
| PRIV-03 | **PASS** | Output operations enforce consent and filesystem scope | Physical output validation, case-insensitive collision checks, relative-link preservation, guarded paths and explicit selected-file overwrite consent. |
| PRIV-04 | **FAIL** | Temporary authenticated profiles are reclaimed after forced Stop | login-check-* and login-run-* depend on worker context-manager cleanup; forced Job Object termination bypasses it; no abandoned-profile reconciler. F2. |
| PRIV-05 | **PARTIAL** | Private jobs, captures and recovery have a retention/capacity procedure | Logs have limits; private job/capture/recovery storage has no application-level lifecycle or safe maintenance inventory. Preserve unresolved recovery. |

### Security assurance

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| SEC-01 | **PASS** | CodeQL covers Python and Actions with current execution evidence | Exact-main security run 39629732204 analyzed Python and Actions successfully; separate quality run 39629732816 succeeded. |
| SEC-02 | **UNVERIFIED** | Secret scanning and push-protection settings | Repository metadata omits security settings; available authenticated audit access did not establish enabled states. A narrow current-tree signature scan is not equivalent. |
| SEC-03 | **UNVERIFIED** | Private alert backlog and full-history secret scan | CodeQL job success is not proof of zero open alerts. No complete history scan or private alert inventory was established through available audit access. |
| SEC-04 | **PARTIAL** | Private security disclosure and response procedure | No SECURITY.md in the tracked tree. Existing bug-report guidance covers sanitization but does not establish a private vulnerability disclosure procedure. |
| SEC-05 | **PASS** | Project license is retained in distribution | GPL-3.0 project license exists; LICENSE.txt is one of the four files covered by the verified checksum manifest. No exhaustive third-party legal review implied. |

### Operational scope

| ID | Status | Control | Evidence / remaining boundary |
| --- | --- | --- | --- |
| OPS-01 | **PASS** | Setup, maintenance and troubleshooting runbooks exist | Indonesian contributor/setup/architecture/CI/diagnostic/troubleshooting docs describe exact artifact identity and preservation of recovery data. |
| OPS-02 | **UNVERIFIED** | End-to-end backup restore and executable rollback rehearsal | Runbooks are present, but a retained compatible rollback artifact and an observed synthetic restore/rollback drill were not provided. |
| OPS-03 | **UNVERIFIED** | Endpoint ACL, encryption and backup configuration | Source-level credential/path controls do not establish actual user-machine ACL, disk encryption or approved backup configuration. |
| OPS-04 | **UNVERIFIED** | Current artifact acceptance against the live portal | Only synthetic CI evidence assessed; no live taxpayer/account access or Windows 10/11 end-user acceptance was performed. |
| OPS-05 | **N/A** | Server/container/cluster deployment controls | This is a desktop/CLI application; Kubernetes, server HA, database replication and cloud service deployment controls are not applicable. |

## 4. Remediation order

These are proposed follow-up changes, not work represented as already fixed. Estimates are engineering effort, excluding reviewer availability; a normal warm CI validation currently takes approximately 13 minutes.

| Order | Bounded work | Findings / controls | Estimated engineering effort | Completion evidence |
| ---: | --- | --- | --- | --- |
| 1 | Recovery-safe Stop and temporary-session cleanup | F1, F2 | 4–8 hours | Atomic-write fault tests and synthetic forced-stop/profile-reclamation tests on Windows |
| 2 | Deterministic packaged bootstrap | F3, F7 | 4–8 hours | Exact-EXE cold/reuse/cancel checks with no PATH uv and contaminated config cases |
| 3 | Durable verified distribution and rollback | F4 | 3–6 hours | Promoted bytes, published identity/provenance and synthetic upgrade/rollback record |
| 4 | Preserve main build completion | F5 | 1–3 hours | Code→docs and pending-run scenarios plus unchanged required gates |
| 5 | Selection-preserving recovery and remaining maturity work | F6, F8 and PARTIAL rows | Scope separately; F6 estimate 4–8 hours | Explicit selection contract and crash recovery evidence; maturity controls closed individually |

Do not relax required checks, remove behavioral tests, increase shard count without measurement, automatically delete tax/recovery data, or treat the historical 3.11 build as the rollback default.

## 5. Evidence limits and handoff

The audit establishes source/configuration findings and the verified CI/artifact snapshot. It does not claim live Coretax acceptance, user-endpoint encryption/ACL/backup compliance, byte-for-byte rebuild reproducibility, a completed backup/rollback drill, or zero private security alerts. The protected main ruleset was read successfully; the managed integration's legacy branch-protection endpoint returned 403, so that response was not misreported as absent protection. Zero mandatory human approvals is an explicitly documented solo-maintainer choice. Repository-level Actions defaults and administrative security settings were not independently established; the explicit workflow permissions and artifact retention were inspected.

A successful CodeQL job proves the analysis ran; it does not by itself prove all repository alerts are closed. Dependency results describe the advisory database at the recorded CI execution. New advisories and future commits require fresh assessment.

### Primary evidence index

| Evidence | Link / coordinates |
| --- | --- |
| Exact source snapshot | [commit d402b98](https://github.com/cepeter-job/spt-downloader/commit/d402b98a1a534f761e60500fc1cc17f367461298) |
| Live enforced policy | [ruleset 24914050](https://github.com/cepeter-job/spt-downloader/rules/24914050); [API](https://api.github.com/repos/cepeter-job/spt-downloader/rulesets/24914050) |
| Main build and job evidence | [run 39629732190](https://github.com/cepeter-job/spt-downloader/actions/runs/39629732190); [jobs API](https://api.github.com/repos/cepeter-job/spt-downloader/actions/runs/39629732190/jobs?per_page=100) |
| Main artifact identities and expiry | [artifacts API](https://api.github.com/repos/cepeter-job/spt-downloader/actions/runs/39629732190/artifacts?per_page=100) |
| Source definitions of gates | [.github/workflows/windows-build.yml](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/.github/workflows/windows-build.yml); [scripts/ci_route.py](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/scripts/ci_route.py); [scripts/ci_tests.py](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/scripts/ci_tests.py) |
| Negative evidence: gate rejects failed Windows run | [run 39590576108](https://github.com/cepeter-job/spt-downloader/actions/runs/39590576108) |
| Scheduled audit execution | [run 39226957179](https://github.com/cepeter-job/spt-downloader/actions/runs/39226957179) |
| Python/Actions security analysis | [run 39629732204](https://github.com/cepeter-job/spt-downloader/actions/runs/39629732204) |
| Separate code-quality analysis | [run 39629732816](https://github.com/cepeter-job/spt-downloader/actions/runs/39629732816) |
| Adjacent full PR70 executions | [39627036641](https://github.com/cepeter-job/spt-downloader/actions/runs/39627036641), [39624130235](https://github.com/cepeter-job/spt-downloader/actions/runs/39624130235) |
| Artifact checksum/provenance checks | [scripts/ci_artifact.py](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/scripts/ci_artifact.py); [attestation 58279383](https://github.com/cepeter-job/spt-downloader/attestations/58279383) |
| Runtime/version policy | [docs/python-314.md](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/python-314.md); [spt_desktop/runtime.py](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/spt_desktop/runtime.py) |
| Diagnostics and recovery runbooks | [docs/diagnostik.md](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/diagnostik.md); [docs/pemecahan-masalah.md](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/pemecahan-masalah.md); [docs/arsitektur.md](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/arsitektur.md) |
| Historical optimization scope | [docs/audits/2026-10-21-windows-shard-evaluation.md](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/audits/2026-10-21-windows-shard-evaluation.md); [docs/audits/2026-10-21-browser-fixture-completion.md](https://github.com/cepeter-job/spt-downloader/blob/d402b98a1a534f761e60500fc1cc17f367461298/docs/audits/2026-10-21-browser-fixture-completion.md) |

**Recommended next action:** review remediation order 1 and use its two acceptance contracts as the scope for the first repair PR.
