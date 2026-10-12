# SPT Downloader Windows Desktop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended by the skill) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship and verify a simple Windows GUI that prepares Python/uv automatically, runs the authorized exporter with secure Settings and truthful progress, saves verified Excel files in Windows Downloads and is built by GitHub Actions.

**Architecture:** A frozen standard-library Tkinter launcher owns one worker and its Windows Job Object. The worker uses a uv-prepared Python environment, the existing scraper/exporter and a dedicated browser profile. Small `spt_desktop` modules isolate Windows paths/credentials/process ownership, bootstrap, authentication, events, worker orchestration and UI.

**Tech Stack:** CPython 3.11 x64; tkinter/ttk and ctypes from the standard library; `playwright==1.63.0`, `openpyxl==3.1.5`; build/test `uv==0.12.16`, `pyinstaller==6.22.3`, `pytest==9.1.1`.

**Spec:** `docs/superpowers/specs/2026-10-09-windows-desktop-design.md` (approved by the user). Implement on `feat/windows-desktop`, based on `9770854`; the specification commit is `dd0758b`.

## Global Constraints

- Windows 10/11 x64; CPython 3.11 x64 worker; workspace `%LOCALAPPDATA%\SPTDownloader`; no admin/global PATH/registry changes.
- Exact 16 ASCII-digit NPWP and four ASCII-digit year; use the existing validator and tax-period/year rule without normalizing user input.
- Passwords only in application-specific Windows Credential Manager targets bound to `https://coretax.intranet.pajak.go.id` or `https://satu.intranet.pajak.go.id`; no secrets in argv, environment, logs, JSON, source or GitHub. CAPTCHA/MFA remain manual.
- One active job/profile owner; Stop grace period 15 seconds; kill-on-close Job Object must contain worker/browser descendants. Never close unrelated browsers or delete previous exports/recovery data.
- Progress is stage/count-based: session 0–5, inventory 5–20, details 20–90, export/verification 90–95, publication 95–99, 100 only for verified/published COMPLETE after browser cleanup.
- Final folder `<Windows Downloads>\<NPWP> - <NAMA WP>\<TAHUN PAJAK>\<WAKTU EKSPOR>`; use a filesystem-safe name and a unique timestamp/job component, never overwrite prior jobs. Only Excel results are published; raw checkpoints remain local.
- Preserve `resume.xlsx` plus one workbook per present SPT type, literal values, leading zeros, scope checks, relative links and PARTIAL semantics. Synthetic fixtures are not live taxpayer results.
- Actual GitHub Actions success and artifact read-back are required; a workflow file or local build alone is not completion. No live Coretax scraping without separate user-authorized scope.

## Review Focus

- An incompatible/missing Python, interrupted setup or changed bundled requirements must repair or fail clearly, not run a stale/incompatible worker (Task 2).
- OneDrive/UNC/non-ASCII Downloads, invalid/long names, collisions, disk-full or locked files must not overwrite output or announce a half-published result (Task 3).
- A redirected/multiple/change-password/GET-submitting login form, CAPTCHA or rejected password must not leak or retry saved credentials (Task 3).
- A close/stop/crash during navigation or a late event from an earlier job must not leave owned browser processes or turn a cancelled run into success (Tasks 1 and 4).
- An empty inventory, reused complete checkpoint or partial record must produce correct counts and never cause division by zero or false 100% (Task 3).

## Task 1: Native Windows boundaries and safe process ownership

**Files:** Create `spt_desktop/__init__.py`, `spt_desktop/paths.py`, `spt_desktop/credentials.py`, `spt_desktop/windows.py`; tests `tests/test_desktop_windows.py`, `tests/test_desktop_credentials.py`.

**Interfaces:**
- `paths.workspace_root() -> Path`; `paths.downloads_folder() -> Path`: resolve LocalAppData/Downloads with `SHGetKnownFolderPath`, free allocated memory and raise on failure instead of silently guessing.
- `paths.safe_taxpayer_name(name: str, max_length: int = 100) -> str`: reject blank source names; replace filesystem-invalid/control characters only, remove illegal trailing dots/spaces and bound length. Raw workbook name stays unchanged.
- `credentials.Login`: identifier and secret, with password excluded from repr. `save_login(origin: str, identifier: str, password: str) -> None`, `read_login(origin: str) -> Login | None`, `delete_login(origin: str) -> None`. All operations validate the exact allowlisted origin and use a target prefix `SPTDownloader:login:`. Use native CredWriteW/CredReadW/CredDeleteW/CredFree; no broad credential enumeration.
- `windows.InstanceLock(root: Path)`: per-user named-mutex ownership; fail clearly for a second application instance.
- `windows.ProcessJob`: parent-owned Job Object, `assign(pid: int) -> None`, `close() -> None`, context-manager support. Apply `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` and fail closed on assignment errors. The worker waits for a startup command, allowing assignment before any browser child starts; do not assign the running GUI to the worker's Job Object.

- [ ] Write failing tests for redirected known folders and API cleanup, invalid names, missing credential, origin mismatch, secret-free repr, second-instance detection and Job Object assignment/close behavior. Mock credential APIs so tests never read/write real saved logins.
- [ ] Run `.venv/Scripts/python.exe -m pytest tests/test_desktop_windows.py tests/test_desktop_credentials.py -q` and confirm the new functionality is missing.
- [ ] Implement the small native boundaries; keep imports safe on non-Windows where pure logic tests run, with explicit errors for native operations.
- [ ] Run new tests, then a Windows-only isolated dummy-child test proving Job Object close kills that child while an unrelated dummy process survives. Do not use Edge/personal sessions for this test.
- [ ] Commit only these source/test files: `feat: add Windows paths credentials and process ownership`.

## Task 2: Idempotent uv bootstrap and explicit resource payload

**Files:** Create `spt_desktop/runtime.py`, `requirements-build.txt`; tests `tests/test_desktop_runtime.py`. Add runtime resource metadata in a text/TOML form only if required; no tracked local JSON/state.

**Interfaces:**
- `runtime.resource_root() -> Path`: repository source root in development, bundled resource root in the frozen app.
- `runtime.ensure_runtime(root: Path, on_status: Callable[[str], None], cancelled: Callable[[], bool]) -> Path`: returns the verified worker Python executable; all preparation happens off the UI thread.
- `runtime.worker_source(root: Path) -> Path`: returns the prepared, explicit source allowlist in `root/app`.
- Pin build/test dependencies listed in Tech Stack. Bundle the uv binary from the installed pinned uv distribution rather than an unaudited installer script. At runtime prefer a verified compatible uv and fall back to the bundled one; copy it into `root/tools` when needed.

- [ ] Write failing tests for compatible 3.11 x64 selection, rejection of other interpreters/Store aliases, missing system Python, bundled uv fallback, dependency fingerprint changes, incomplete setup retry and import verification failure. Inject subprocess results/temporary roots; no downloads in unit tests.
- [ ] Run the new runtime test file and confirm missing implementation.
- [ ] Implement bounded subprocess execution with argv lists, TLS intact, command-scoped `UV_PYTHON_INSTALL_DIR`/cache settings, `uv python install 3.11 --install-dir ... --no-bin --no-registry` when necessary, `uv venv` and `uv pip install --python ... -r ...`. Never use frozen `sys.executable` as the worker Python or install into a personal/global environment.
- [ ] Validate versions/imports before writing a ready fingerprint. Source deployment uses only app files needed by the worker, existing three Coretax modules and pinned requirements; never glob the repository into resources.
- [ ] Run tests and exercise real bootstrap in a dedicated scratch workspace, including a second idempotent call. Check the returned Python version and actual Playwright/openpyxl imports. The probe must not contact Coretax.
- [ ] Commit: `feat: prepare portable uv-managed worker runtime`.

## Task 3: Scraper hooks, secure authentication and verified publication

**Files:** Modify `coretax_browser.py`, `coretax.py`; create `spt_desktop/events.py`, `spt_desktop/auth.py`, `spt_desktop/worker.py`, `spt_desktop/output.py`; tests `tests/test_desktop_worker.py`, `tests/test_desktop_auth.py`, `tests/test_desktop_output.py`; extend `tests/test_browser.py` for hook coverage.

**Interfaces:**
- `coretax_browser.CaptureCancelled`: cancellation sentinel derived from KeyboardInterrupt so existing broad `except Exception` capture handlers do not swallow Stop.
- Append optional `check_cancel: Callable[[], None] | None = None` to table/detail/inventory/detail-collection APIs, preserving existing positional/default behavior. Check before navigation and between loops. `collect_inventory` also accepts optional `on_progress(event: dict)`, emitting discovered-list denominator, completed lists and current scanned rows. Keep `collect_details(..., on_progress(run, ordinal))` unchanged and invoke it for reused complete checkpoints too.
- Factor existing workbook verification into `coretax.verify_outputs(run: dict, folder: Path) -> None`, reused by `save_output` and publication without changing their output contract.
- `events.Progress(job_id: str, emit: Callable[[dict], None])`: methods for authenticated, inventory(completed, total, scanned), details(processed, total, verified), exported(), publishing(), finished(complete: bool, output: Path | None). Events contain `job_id`, `type`, `stage`, integer `percent` and applicable counts. Never advance from time alone; fail/partial terminal events stay below 100.
- `auth.authenticate_owned(playwright, root: Path, browser: str, headless: bool, progress: Callable[[dict], None], check_cancel: Callable[[], None]) -> tuple[context, page]`: owns sequential persistent-context transitions; reuse session first, inspect a unique approved-origin sign-in form before reading that bound credential, then manual visible fallback as specified. Preserve manual challenge/user approvals and close attempted contexts on every error. No automated retries after rejected password.
- `output.publish_workbooks(run: dict, source: Path, downloads: Path, job_id: str) -> Path`: validates an explicit basename-only `.xlsx` allowlist, stages/copies/verifies the entire set within the final filesystem and renames to a collision-free final job directory. Uses `safe_taxpayer_name` and `coretax.verify_outputs`; never copy raw checkpoints or overwrite existing files.
- `worker.main(argv=None) -> int`: console-hidden subprocess entry `python -m spt_desktop.worker`. Wait for an initial `start` stdin command before creating descendants; a reader thread sets a cancellation Event on `stop`. Validate scope and paths, resolve own credentials, run inventory/details, preserve checkpoints, close browsers/Playwright, verify/publish and emit exactly one terminal event. JSON lines only on stdout; route existing non-secret scraper prints to bounded stderr handling. Exit codes preserve complete/partial/blocked/cancelled distinctions.

- [ ] Write failing tests for stage mapping/monotonic percentages, zero denominator, partial not 100, reused checkpoint progress, cancellation between pages and popup cleanup. Use synthetic fixtures only.
- [ ] Write auth fixture tests with Playwright request routing on the exact allowlisted synthetic origins: session ready without credentials; unique POST sign-in form; other origin/multiple/new-password/GET forms refused; visible CAPTCHA/MFA and rejected login require manual action; cleanup on timeout. Use only clearly synthetic identifiers/passwords in memory, mock Credential Manager reads.
- [ ] Write publication tests using the existing synthetic split-workbook fixture for redirected/non-ASCII target, unchanged raw taxpayer name, expected folder layout, relative links, missing name, traversal filename rejection, repeated-job collision, failed copy and partial status preservation. Assert a failed staging operation cannot appear as a finished output.
- [ ] Run the focused new tests and record their missing-behavior failures before implementation.
- [ ] Implement the optional hooks and modules using the named interfaces; no unrelated exporter refactor or scraping expansion. Use a timestamp plus unique job token for `WAKTU EKSPOR`. Keep complete checkpoint aggregation as the final capture certification.
- [ ] Run focused tests and all original tests with a fresh scratch `--basetemp`. Exercise a subprocess worker against a synthetic routed/local fixture, not the intranet. Verify terminal event arrives only after owned context cleanup and publication.
- [ ] Commit: `feat: add secure desktop worker progress and Downloads export`.

## Task 4: Responsive GUI and one-job lifecycle

**Files:** Create `spt_desktop/controller.py`, `spt_desktop/app.py`, `spt_gui.py`; tests `tests/test_desktop_gui.py`.

**Interfaces:**
- `controller.JobController(root: Path, on_event: Callable[[dict], None])`: `start(npwp: str, year: str, browser: str, headless: bool)`, `stop()`, `poll()`, `close()`. Own one subprocess/job handle and a bounded event queue. Assign process to its Job Object before sending `start`. Keep settings secrets out of child argv/env. Validate job identity and event shape; limit line/message size and buffered stderr. On normal worker exit wait for cleanup/exit before closing Job Object; on Stop terminate the owned tree after the 15-second grace period.
- `app.App(root: tkinter.Tk, workspace: Path)`: compact Indonesian ttk form and settings dialog; main-thread-only widget updates; asynchronous preparation; one active job. Settings use `credentials` functions, masked password entry and replace/delete behavior without revealing a saved password. Read preference files through an explicit non-secret schema.
- `spt_gui.main(argv=None) -> int`: normal Windows UI entry plus `--self-test --report <scratch-path>` for packaged verification. The self-test checks Tk creation/destruction, resource payload and bundled uv availability without credentials, runtime installation or live network/export. It writes a non-secret diagnostic result and exits deterministically.

- [ ] Write failing tests for exact input rejection, no concurrent start, current-job filtering, bounded event/error queues, worker startup ownership order, close confirmation, grace-period force stop, result-button enablement and settings secrecy. Use fake workers and Tk roots on Windows; never spawn a live tax job.
- [ ] Run focused GUI tests and confirm missing behavior.
- [ ] Implement controller and GUI, reusing Tasks 1–3 instead of duplicating their logic. Run poll callbacks with `after`; cancel callbacks and release process/pipe/mutex handles on application close.
- [ ] Exercise the real Tk window on this Windows host, programmatically verify labels/control states, run a synthetic progress/terminal sequence, close it and assert owned handles/worker state are released. Verify credentials are not populated or read from any real user target.
- [ ] Run the complete test suite; commit `feat: add simple Windows desktop interface`.

## Task 5: Build on GitHub and verify the deliverable

**Files:** Create `scripts/build_windows.py`, `.github/workflows/windows-build.yml`; update `README.md`, `.gitignore` (only build artifacts); include existing LICENSE in downloadable packaging. Tests/build smoke checks may live in `tests/test_desktop_build.py`.

**Interfaces:**
- `scripts/build_windows.py`: derives the pinned uv binary location, checks an explicit GUI/worker resource allowlist, invokes PyInstaller one-file/windowed/no-UPX build as `SPTDownloader.exe`, includes worker sources/requirements and uv, and runs the packaged self-test. Keep Playwright/browser binaries out of the thin launcher; they belong to the prepared worker runtime, and Edge is system-provided.
- Workflow `Windows desktop build`: push on `feat/windows-desktop`/`main` and manual `workflow_dispatch`; `permissions: contents: read`; Windows x64 runner and Python 3.11; install pinned tooling via uv; run synthetic tests, build, packaged self-test, then upload executable/license/readme. Use verified current action versions pinned to commit SHA before publication; no Coretax/account secrets in CI.

- [ ] Write failing resource/command construction checks that reject private output/profile/venv files and verify the self-test entry works in source mode.
- [ ] Implement build script/workflow/docs after those checks fail. Install build dependencies into the local project environment using uv; do not replace the existing host Python installation.
- [ ] Run all tests, build locally and exercise the actual EXE. Inspect bundled resource inventory and deliverable contents; verify no private folders or real taxpayer identifiers. Record real build output, not fabricated package size or CI results.
- [ ] Request a fresh independent code/security review of the changed source, tests and workflow (no private outputs/profiles/vault access). Fix verified findings with regression tests and rerun relevant checks.
- [ ] Commit reviewed changes, scan staged tracked files for secrets/private IDs, and push the feature branch via the existing secure GitHub/proxy workflow without force-push. Read back the exact remote SHA.
- [ ] Read GitHub Actions runs filtered to that commit; inspect the actual run/job conclusion and logs on failure (at most three fixes before identifying a doubtful assumption). Verify the successful run's artifact list, download artifact to scratch when access permits, inspect its allowlisted contents and run that downloaded EXE self-test locally.
- [ ] Report the verified run URL, artifact/download route, executable path and actual test result; explicitly separate synthetic/packaged checks from still-unperformed live Coretax authentication/export. Do not claim all acceptance criteria complete if GitHub build/artifact verification remains blocked.

## Plan self-review and execution choice

All five specification acceptance criteria are covered by Tasks 1–5; Review Focus cases appear in their owning tasks. Public function names and cancellation/progress contracts above are the integration decisions; implementations may remain small and conventional. Every significant logic unit gets a failing test before product code and a passing behavior check afterward. A future root-cause finding from the read-only investigations may refine the approach before affected code is written; no investigation result is treated as proof of an upload/build.

Recommended execution: **Native** parent implementation and integration, with the already dispatched independent investigations plus a fresh whole-branch code/security review in Task 5. These tasks share authentication, progress and process-lifecycle interfaces, making parent integration simpler than handing every small module to a separate implementer. The user must review this plan and choose Native or Subagent-driven before implementation begins.
