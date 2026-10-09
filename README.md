# spt-downloader

## Windows interface (recommended)

Download the `SPTDownloader-Windows-x64` artifact from [Build Windows app](https://github.com/cepeter-job/spt-downloader/actions/workflows/windows-build.yml), extract it, and run **SPTDownloader.exe**. The executable is Windows 10/11 x64 and does not require administrator rights or Python on PATH merely to open the GUI. It is unsigned: verify the source/build; never disable Defender or TLS verification. An optional standard location for the portable executable is `%LOCALAPPDATA%\Programs\SPTDownloader`.

1. Open **Pengaturan** and choose the actual approved intranet login origin, browser (`msedge` or `chrome`), and headless preference. Enter credentials directly in the masked Windows dialog, never in chat. Passwords are stored in this application's origin-bound Windows Credential Manager entries, not in the preferences file. Blank password preserves an existing saved entry; removing an entry requires confirmation.
2. Enter the **exact 16-digit NPWP** and **4-digit tahun pajak**, then select **Mulai**. No spaces, separators or silent normalization. The existing tax-period year interpretation is preserved. Only one application/job can use the dedicated profile at a time.
3. The first run checks a compatible installed CPython 3.11 x64 or prepares portable Python in `%LOCALAPPDATA%\SPTDownloader`, then installs pinned worker dependencies with bundled/compatible uv. No global PATH edits or registry registration. First setup needs package/runtime download access; scraping needs authorized intranet connectivity and installed Edge/Chrome. A setup error remains retryable rather than claiming success.
4. Progress displays stage-weighted work and processed/verified SPT counts; setup has an indeterminate indicator where no denominator exists. **100% only means COMPLETE after verified workbook publication and owned browser cleanup.** CAPTCHA/MFA and unknown/unsafe sign-in layouts switch to the application's visible browser; solve challenges there. Stored credentials are never used for unknown forms or tax submission buttons. If headless session transfer is rejected, the application remains visible.
5. Use **Buka Hasil** after publication. **Stop** preserves private local PARTIAL checkpoints and closes only owned worker/browser descendants; a stubborn worker is terminated after 15 seconds. Closing the window during a job asks for confirmation. Previously downloaded exports are never overwritten or deleted.

### Windows paths and confidentiality

The actual Windows Known Folder API resolves Downloads, including OneDrive, relocated, network and non-ASCII locations. Successful jobs publish only the verified Excel set:

```text
<actual Downloads>\NPWP - NAMA WP\TAHUN PAJAK\WAKTU EKSPOR-JOB ID\
  resume.xlsx
  SPT_Badan.xlsx     # only if captured in this scope
  SPT_21.xlsx        # only if captured in this scope
  ...other available tax-type workbooks
```

Keep all workbooks together for relative hyperlinks. The folder name uses the exact-matched taxpayer's name, sanitizing only its filesystem component; the literal source name stays in Excel. A missing taxpayer name or unwritable/failed Downloads publication is an error, not a fabricated name or silently changed destination. Raw recovery JSON and the dedicated confidential browser profile stay under `%LOCALAPPDATA%\SPTDownloader`, outside this repository. Preferences whitelist only browser/headless/origin/account identifier; no password, token, cookies or code is stored there.

Live account login/export is an authorized user acceptance check; synthetic tests and packaged self-test do **not** prove live Coretax access. Unknown detail layouts, failed pages or cancelled jobs remain explicitly PARTIAL/BLOCKED, and never display successful 100%.

### Build from source / GitHub

GitHub Actions uses pinned actions, Windows x64 CPython 3.11, uv-installed production/build dependencies, synthetic tests, and `build_desktop.py`. The thin windowed executable contains only the GUI runtime, pinned uv binary and an explicit worker-source allowlist; no browser binaries, tax captures, personal profiles, credentials or output files. The artifact contains the executable, LICENSE, quick-start README and a non-secret frozen self-test report. No intranet account/data is used in CI.

```bash
uv venv --python 3.11 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt -r requirements-build.txt
.venv/Scripts/python.exe -m pytest tests -q
.venv/Scripts/python.exe build_desktop.py --output dist
```

`build_desktop.py` runs the frozen executable's `--self-test` and fails if GUI/resources/uv/known-folder checks fail. Build artifacts are generated under `dist` or the explicitly selected output directory and excluded from Git. The original CLI and offline Excel export remain available below.


Local, authorized Coretax SPT capture and split-file Excel export.

## Run on Windows

1. Open the cloned `spt-downloader` folder and run **setup.cmd** first (requires `uv` and installed Edge or Chrome). Then double-click **run.cmd**.
2. Enter the **exact 16-digit NPWP** and **four-digit tax year**. Separators/spaces are rejected, not silently normalized.
3. Sign in directly in the separate browser window if prompted; complete password, CAPTCHA or MFA there. Press Enter in the script terminal after signing in. An existing local automation browser on port 9235 is reused by the launcher.
4. Open the Excel file in the printed `output` folder. Check **Ringkasan → Status** and **Audit** before relying on completeness.

```bat
.venv\Scripts\python.exe coretax.py
```

For an already-authenticated automation browser:

```bat
.venv\Scripts\python.exe coretax.py --npwp YOUR_16_DIGIT_NPWP --year 2025 --reuse-browser http://127.0.0.1:9235
```

The placeholder `YOUR_16_DIGIT_NPWP` must be replaced; it is intentionally not a valid NPWP.

## Scope and year rule

The default is **tax-period / tax year**, not the submission year. A December 2025 return submitted in January 2026 belongs to the default 2025 export. For submission-date selection, add `--year-basis submission`.

The tool searches the Coretax **SPT taxpayer search** at `/returnsheets/id-ID/taxpayer-search`, selects the exact NPWP result, discovers the taxpayer's exposed status lists, and reads every list page. It observes the UI's own JSON list responses to reconcile `TotalRecords` against scanned rows. It does not extract authentication tokens or issue independent API write requests.

All available return types and amendments for the selected year are retained. Duplicate appearances of the same `RecordId` in different status lists are exported once with their source occurrences recorded in JSON. Distinct amendment IDs remain separate. Year interpretation of migrated numeric periods is restricted to the observed validated `MMMMYYYY` pattern; the original source value is preserved. Unrecognizable year values are errors, not silently excluded.

For each selected return, the tool clicks only the observed **View** control, verifies taxpayer/record provenance, and captures exposed tabs, read-only form values, visible tables and their pagination. Disabled tabs are not traversed. Navigation/accordion/page-size controls only reveal content.

**Not included:** file contents of PDF/BPE/other uploaded attachments, generated PDFs, and per-row drill-down dialogs. Their visible table metadata is included where available. “COMPLETE” means the supported exposed-page scope is reconciled, not that every underlying Coretax document or database object has been downloaded. Unsupported layouts or inaccessible returns are explicitly marked **PARTIAL**.

## Workbook layout — separate files by SPT type

- **resume.xlsx:** global Ringkasan, Daftar SPT, and Audit only; detail data is kept in the type files. Click an index number to open the correct external workbook and worksheet.
- **SPT_Badan.xlsx:** all captured PPh Badan periods and amendments in one workbook, with one detail worksheet per unique return.
- **SPT_21.xlsx:** all captured PPh Pasal 21/26 periods and amendments in one workbook.
- **SPT_Unifikasi.xlsx:** all captured PPh Unifikasi periods and amendments in one workbook.
- **Other tax types:** one `SPT_<type>.xlsx` each; filenames are checked for collisions before any workbook is written.

Each type workbook contains its own type-specific Ringkasan/Daftar SPT, the run Audit, and only that type's detail worksheets. All periods and amendment identifiers are retained. No absent tax-type files are fabricated. Detail sheets link back to resume.xlsx. Keep all generated workbooks together in the same folder and do not rename them; hyperlinks are relative so the whole folder can be moved. Existing single-file exports are not deleted. Use a new output folder when changing the NPWP, year, year basis, or test scope. A different NPWP/year/year-basis cannot overwrite an existing run.json output scope.

The raw checkpoint command `--resume` is independent of the Excel filename `resume.xlsx`; it still resumes capture from inventory.json and return checkpoints. `--from-json` rebuilds all the split Excel files offline without opening the browser.

Identifiers and source figures are stored as literal text to preserve leading zeros, Indonesian number formatting and source precision. Summary counts are numeric. Source strings beginning with `=` are **not** executed as Excel formulas. The workbook is not encrypted; handle it as confidential taxpayer data.

## Checkpoints and recovery

Raw JSON stays locally under the output folder. List batches are saved incrementally; every completed return has its own JSON checkpoint. A failed/limited/interrupted run stays PARTIAL. Resume skips complete matching checkpoints and retries incomplete returns:

```bat
.venv\Scripts\python.exe coretax.py --resume "output\YOUR_PREVIOUS_RUN_FOLDER" --reuse-browser http://127.0.0.1:9235
```

Rebuild Excel offline from already-captured data:

```bat
.venv\Scripts\python.exe coretax.py --from-json "output\YOUR_PREVIOUS_RUN_FOLDER\run.json"
```

Inventory only (explicitly PARTIAL for full-detail scope):

```bat
.venv\Scripts\python.exe coretax.py --npwp YOUR_16_DIGIT_NPWP --year 2025 --inventory-only
```

`--detail-limit N` is for bounded testing, not a complete export. `--max-pages` defaults to 1000 per list/table; reaching the safety cap is reported as PARTIAL.

Exit codes: **0** complete supported scope; **2** partial; **1** blocked; **130** interrupted. Authentication or layout failures never cause fabricated tax output. Use a new output folder for a fresh inventory; do not edit checkpoints manually.

## Security

Use only an account and taxpayer records you are authorized to access. The script never asks for a password, CAPTCHA answer, card or verification code. Login is performed by you in the browser; persistent login cookies may remain in the dedicated browser profile. The profile is separate from your personal Firefox/Chrome/Edge profile. Neither profiles, credentials, tax output nor the virtual environment is included in the distributable ZIP. No tax data is uploaded to a cloud scraping service by this tool. This chat's live inspection does not change that local execution model.

If a local debugging browser is reused, its endpoint must be localhost. Other local programs may be able to access that session while the debugging browser is open, so close the dedicated automation window after use. Never expose its port to the network. The normal fresh-browser path does not enable a debugging port.

No submission, cancellation, email, PDF-generation or arbitrary row-action buttons are clicked. If the View selector or page structure changes, the tool reports an error rather than guessing an action.

## Troubleshooting and tests

- **Login required / MFA / CAPTCHA:** finish in the visible browser. `--non-interactive` requires an existing authenticated session.
- **Profile in use:** close only the dedicated automation window, or reuse its known local endpoint. Do not kill your personal browser or copy its cookies.
- **NPWP not found / ambiguous result:** check the exact input and account authorization. The script does not select partial matches.
- **Source counts or metadata change mid-run:** start a fresh inventory in a new folder. Check Audit.
- **Unknown return layout:** inspect the relevant saved checkpoint before extending selectors; keep the run PARTIAL until verified.

Development tests use locally served synthetic HTML fixtures, explicitly separate from taxpayer outputs:

```bat
uv pip install --python .venv\Scripts\python.exe pytest==9.1.1
.venv\Scripts\python.exe -m pytest tests -q --basetemp "%LOCALAPPDATA%\hermes\cache\scratch\coretax-tests"
```

The tool has been exercised against the authorized intranet session as well as the fixture tests. See the delivered workbook's Audit for the particular run's verified results and limitations.

## Development repository

Development takes place in https://github.com/cepeter-job/spt-downloader. The repository contains source, documentation and synthetic fixture tests only. Never commit real taxpayer data, captured JSON, Excel outputs, browser profiles, credentials or cookies. Existing local tax outputs stay outside this repository.

## License

The repository retains its existing GNU General Public License, version 3. See [LICENSE](LICENSE).
