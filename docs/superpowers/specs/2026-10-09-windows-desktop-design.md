# SPT Downloader — Windows Desktop Design

Status: written specification approved by the user; implementation plan awaiting review and execution-method selection.

## Purpose and agreed outcome

Make the existing authorized, read-only Coretax exporter usable from a simple Windows application without manually preparing a Python environment or using a terminal. A user enters an exact NPWP and tax year, runs one export, sees meaningful progress, and opens verified split Excel files in their Windows Downloads folder. Build the Windows executable on GitHub Actions and verify the resulting artifact.

This specification implements the user's four requirements: automatic Python/uv/dependency setup, a settings-backed background scraper, percentage/bar progress with browser cleanup, and Downloads output under `NPWP - NAMA WP`. It preserves the existing tax-period year rule, provenance checks, partial-run semantics and split-file workbook contract.

## Chosen approach

Use a small Tkinter/ttk launcher, packaged as a Windows x64 executable with PyInstaller, and a separate Python worker process. The launcher contains the GUI's Python/Tcl runtime, the explicitly allowlisted worker source and requirements, and a pinned uv executable. Therefore the GUI itself starts even when Python and uv are absent from the user's PATH; the separately prepared worker environment satisfies the portable-Python/workspace requirement.

A fully frozen scraper would remove the runtime setup but conflict with the requested uv-managed workspace. WinUI/.NET would add another toolchain and Python integration without improving this small form-based app. Neither alternative is needed for this scope.

Supported target: Windows 10/11 x64 with authorized intranet connectivity and Microsoft Edge. Chrome is a selectable fallback. A missing browser is an actionable setup error, not permission to install a system-wide browser silently. The existing CLI remains usable.

## 1. Per-user workspace and bootstrap

Use Windows Known Folder resolution for LocalAppData and Downloads. The workspace is `%LOCALAPPDATA%\SPTDownloader`; no administrator rights, machine-wide registry changes or global PATH edits are required. The executable may be launched from the downloaded artifact; installing shortcuts or an uninstaller is outside this scope.

Workspace contents have separate responsibilities:

- `tools`: the application's uv executable when a compatible installed uv is unavailable.
- `python` and `runtime`: application-managed CPython and the worker virtual environment.
- `app`: the current explicitly allowlisted worker source and pinned requirements, copied from the executable's resources rather than downloaded as arbitrary scripts.
- `profile`: one dedicated application browser profile, never the user's personal Edge/Chrome profile.
- `jobs`: unique local checkpoint directories. Normal non-secret preferences may be stored separately in the workspace; credentials are not preference-file contents.

On setup, inspect and execute candidate Python interpreters to verify CPython 3.11 x64. Never trust a filename alone or invoke an unbounded Windows Store installation prompt. Reuse a compatible interpreter to create an isolated environment; otherwise use uv-managed portable CPython 3.11 within the workspace. Managed installation uses `--install-dir`, `--no-bin` and `--no-registry`, with environment variables scoped to the subprocess. The application's worker must never use an arbitrary incompatible interpreter, including a Python version merely present on PATH.

Use uv to create the worker environment and install the pinned Playwright/openpyxl requirements. Setup is idempotent, validates required imports and installed versions before reporting ready, and repairs an incomplete environment on the next explicit setup/run. Record a non-secret requirements/resource fingerprint so changed application dependencies cannot be mistaken for an already complete setup. Keep downloads and installation output free of credentials; preserve TLS verification. First setup requires connectivity to the package/runtime distribution services. Offline/network/proxy failures report the failed step and allow retry, without inventing success or silently disabling certificate verification.

Perform preparation off the Tkinter UI thread. Display installation step text and an indeterminate setup indicator where a byte/work denominator is unavailable; do not manufacture a percentage from elapsed time.

## 2. Main window, settings and job isolation

Provide a compact Indonesian-language Tkinter/ttk window with NPWP and tax-year inputs, Mulai, Stop, Pengaturan, Buka Hasil, a percentage label, a progress bar and bounded status text. NPWP must be exactly 16 ASCII digits and year exactly four ASCII digits using the existing `validate_scope` contract. Do not trim, remove separators, substitute IDs or silently normalize either input. The default interpretation is tax period/year, not submission date.

Allow only one active preparation/export job. Disable conflicting controls while it runs. A second instance must not share the same browser profile or launch a concurrent worker. Closing the window during a job asks the user whether to stop the active job; cancelling that dialog leaves it running.

Run the scraper in a separate, console-hidden subprocess using the prepared worker Python. Pass only validated non-secret scope/path options as an argv list, never a shell command assembled from user input. Use a bounded JSON-lines status channel tagged with the current job identity. Ignore stale events from finished workers. The GUI thread polls a queue; worker-reader/setup threads must never manipulate Tk widgets directly.

Settings contain the account identifier, a masked password entry, browser preference and a headless preference (default on). Saving credentials writes to an application-specific Windows Credential Manager target bound to the selected approved login origin. It must offer removal of the application's saved credential. Opening settings does not reveal or prefill the stored password in readable form. Preferences contain no password, token or verification code. The worker reads only this application's credential target when login is actually needed; unrelated credentials are never enumerated or read.

## 3. Authentication and background browser

Start with a dedicated persistent Edge profile in headless mode when requested. Reuse an authenticated application session before attempting password login. Retained profile/session files are confidential, local and excluded from Git, release resources, diagnostic artifacts and GitHub.

The application may use the user's setting-backed identifier/password only on an exact approved HTTPS login origin: `https://coretax.intranet.pajak.go.id` or the intranet SSO origin `https://satu.intranet.pajak.go.id`. Credential binding must match the current origin. Inspect the page at runtime for an unambiguous sign-in form, its identifier and password fields, its submit action and the absence of a challenge. Use only that form's identified sign-in action. Do not fill credentials into arbitrary password fields, change-password forms, multiple/unknown forms, frames on other origins or redirects outside the allowlist. Do not retry a rejected password automatically.

Unknown login layouts, missing credentials, CAPTCHA, MFA, passkeys and additional user approvals switch to a visible application browser with explicit status. The user enters challenge answers directly there. No challenge-solving service, copied personal cookies, exposed debugging port or authentication bypass is permitted. Do not send secrets through stdout, logs, errors, command arguments, environment variables, checkpoints, source code, the conversation or GitHub. The application's GUI/worker handling credentials is distinct from Hermes browser-tool login, which still uses vault tools only.

If a headless session needs manual login, close that owned context before reopening the same dedicated profile visibly. After the authenticated taxpayer-search control is confirmed, close the visible context and restart headless when preferred. Verify authentication again; if the server does not accept the headless session, remain visible rather than retrying indefinitely. Never open the same persistent profile concurrently. Manual-login waiting has a bounded deadline and remains cancellable.

An expired session or unknown layout during capture stops with an actionable PARTIAL/BLOCKED result. It does not select a different taxpayer or restart the job behind the user's back.

## 4. Scraping, progress and cancellation

Reuse `collect_inventory`, `collect_details`, the existing structured capture, `save_output` and workbook verification. Add optional progress/cancellation hooks with compatible defaults; existing CLI behavior and read-only operations remain intact. Do not expand scraping scope to PDF contents, row drill-downs, remote document generation or tax submission.

Progress is stage-weighted work completion, not a claim about estimated remaining time:

| Range | Evidence that advances progress |
| --- | --- |
| 0–5% | Browser/session preparation and authenticated search confirmation |
| 5–20% | Discovered status lists processed; show scanned/current-list counts separately |
| 20–90% | Detail records processed against the reconciled inventory denominator |
| 90–95% | Excel export and workbook verification |
| 95–99% | Publishing verified files to the final Downloads directory |
| 100% | COMPLETE result, saved files verified and owned browser resources closed |

Before a denominator is known, retain the last honest percentage and update the stage text; do not tick the percentage with a timer. Show processed/total details and verified-detail count separately so failed captures cannot masquerade as verified data. Emit progress for complete checkpoints reused during resume as well as newly attempted details. An empty reconciled scope is handled explicitly without division by zero or fabricated tax-type files.

A partial, blocked, cancelled or crashed job never emits a successful 100% event. Preserve existing COMPLETE/PARTIAL meanings; process exit zero alone is insufficient evidence. Buka Hasil is enabled only for a published result, including an explicitly labelled partial export where files were actually verified.

Stop requests set cooperative cancellation checked between status-list pages, detail records and detail-table pages. Retain durable partial checkpoints. Navigation and authentication waits are bounded. If the worker does not stop within 15 seconds, terminate only its owned process tree. Use a Windows Job Object with kill-on-close for worker/browser descendants so a crash or forced cancellation cannot leave orphaned automation browsers. If ownership enforcement cannot be established, fail before starting the browser rather than issuing broad `taskkill` commands.

Close each owned detail popup after capture. On success, failure, cancellation and manual-login transitions, remove listeners, close owned pages and contexts, stop Playwright and release process handles in finally/cleanup paths. Never kill or close unrelated personal browser sessions. Retain the dedicated login profile for reuse; cleanup means live processes/tabs and handles, not deleting the user's downloaded workbooks or silently deleting recovery data.

## 5. Downloads and result publication

Resolve Downloads with `SHGetKnownFolderPath(FOLDERID_Downloads)`, not a guessed `%USERPROFILE%\Downloads` string. Respect redirected, non-ASCII, OneDrive and network-backed locations. If Windows resolution or write access fails, preserve the local job and show an actionable publication error; do not silently save somewhere else while claiming Downloads success.

The agreed final path is:

```text
<Windows Downloads>\<NPWP> - <NAMA WP>\<TAHUN PAJAK>\<WAKTU EKSPOR>\
```

Use the taxpayer name from the exact validated NPWP search result. Preserve the original name in all workbook/checkpoint data. Sanitize only filesystem-invalid/control characters in the folder component, strip invalid trailing dots/spaces, and bound its length so Windows paths remain usable. Do not invent a taxpayer name when the source name is unavailable: retain the local capture and report a publication blocker. The unique time/job component prevents overwriting earlier jobs for the same taxpayer and year; creation must detect collisions rather than merge output sets.

Keep `resume.xlsx` and all present type workbooks together in the final job folder, maintaining existing relative hyperlinks. No absent-type workbook is fabricated. Store raw JSON/JSONL recovery data under the application's local job directory rather than copying it into GitHub or automatically exposing it as a release artifact.

Export/verify locally first. Copy a complete workbook set into a newly reserved hidden/staging destination within the resolved Downloads target, verify file contents/counts and workbook links after copy, and publish by renaming the staging directory to the unique final job folder. Do not use cross-volume rename as the copy strategy. On copy, disk-full, permission or locked-file failure, do not advertise a successful final folder; keep recovery checkpoints and an actionable error. Partial exports may be published only with their existing PARTIAL status and a clearly labelled GUI result. Cancellation before publication leaves the durable local job, not a falsely finished Downloads result.

## 6. Build, documentation and verification

Add a Windows GitHub Actions workflow with push/manual-dispatch triggers and explicit minimal permissions (`contents: read`). Use a Windows x64 runner and CPython 3.11. Install pinned build/test tooling using uv, run the existing and new synthetic tests, build the console-hidden executable, exercise its packaged self-test, then upload the executable and accompanying license/readme as a downloadable artifact. Include the pinned uv executable and explicit worker sources/requirements in the build resources. Avoid bundling browser profiles, application credentials, private tax outputs, local virtual environments, tests as user tax results or unrelated repository files.

CI must not contact the Coretax intranet, perform taxpayer scraping, require a taxpayer account or download real taxpayer data. Browser fixtures use synthetic local HTML only. The packaged self-test checks GUI/runtime-resource discovery and configuration-path handling without starting a live export or exposing credentials. Check that the build's resource payload contains the expected allowlist and no private paths/files.

Verify the GitHub run by exact commit SHA and run ID, read its terminal conclusion, and read back the artifact list before declaring the GitHub build successful. A workflow file or local executable alone does not satisfy the requested GitHub build. If runner availability, workflow permissions or network/authentication block the build, report that blocker and the actual completed checks without claiming a release exists.

Automated tests cover bootstrap decisions/idempotence/failure, literal input validation, Windows redirected Downloads, folder sanitization/collision and copy failure, origin-bound credential operations, safe/manual auth fallback, progress denominators and partial outcomes, cooperative stop, stale events, cleanup on all exits, and preservation of existing split-file output/link behavior. Exercise Tkinter and packaged execution on Windows in addition to mocked logic tests. Live Coretax login/export is a separate authorized acceptance check and must not be represented as verified by synthetic fixtures.

Update README with first-run setup, secure Settings, headless/manual behavior, result location, stop/recovery semantics, build-download steps and unsigned-executable limitations. Never instruct the user to disable Defender or TLS validation. Code signing, automatic updates, scheduling, multi-job queues, browser installation, shortcuts/uninstaller and new tax-data features are outside this version.

## Acceptance criteria

1. The packaged GUI starts without installed Python/uv, prepares a verified isolated worker environment in the standard per-user workspace, and gives an honest actionable setup error on failure.
2. Exact NPWP/year input launches only one authorized worker; setting-backed secrets stay in Windows Credential Manager and are used only for approved-origin sign-in, with manual challenge fallback and no credential leakage.
3. The responsive GUI shows stage/count-based percentage/bar progress, supports stopping, never marks an incomplete job successful, and cleans up only its own tabs/browser/processes on every terminal path.
4. Verified split Excel files are saved in the resolved Downloads `NPWP - NAMA WP\TAHUN PAJAK\WAKTU EKSPOR` directory, preserving literal values and links without overwriting earlier jobs.
5. Existing tests plus new Windows/GUI/worker tests pass, the packaged artifact is exercised, and an actual GitHub Actions Windows build and its downloadable artifact are independently read back and verified.

## Evidence and assumptions

Repository inspected: `C:/Users/kpp096/spt-downloader`, base commit `9770854`. The existing project environment is CPython 3.11.16 x64 with Tkinter available; current worker requirements are `playwright==1.63.0` and `openpyxl==3.1.5`. The installed uv reports 0.12.16 and exposes `--install-dir`, `--no-bin` and `--no-registry`. Its official Python-install guide confirms managed distributions use python-build-standalone.

Official reference: <https://docs.astral.sh/uv/guides/install-python/>. Direct documentation retrieval failed on this host; retrieval through the existing SOCKS route succeeded. GitHub access continues to use the profile's established proxy and secure credential manager with TLS verification; that host-specific development route is not embedded as a user's application default.

The approved-origin automated login flow still requires runtime form inspection and fixture tests; no actual credentials or challenge selectors have been read or assumed. No live scrape, dependency installation for this feature, or executable build has run during design. Independent technical investigation results will be incorporated before implementation where they reveal a correctness/security issue.
