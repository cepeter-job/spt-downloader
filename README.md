# spt-downloader

Local, authorized Coretax SPT capture and split-file Excel export.

## Run on Windows

1. Open the cloned `spt-downloader` folder and run **setup.cmd** first (requires `uv` 0.12.18 or newer and installed Edge or Chrome). Then double-click **run.cmd**.
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

Each type workbook contains its own type-specific Ringkasan/Daftar SPT, the run Audit, and only that type's detail worksheets. All periods and amendment identifiers are retained. No absent tax-type files are fabricated. Detail sheets link back to resume.xlsx. Keep all generated workbooks together in the same folder and do not rename them; hyperlinks are relative so the whole folder can be moved. Existing single-file exports are not deleted; choose a new folder if it contains other workbooks. All new workbooks are staged and verified before replacing the previous set, with rollback if a later file replacement fails. Abrupt power loss is not a transactional filesystem guarantee. Use a new output folder when changing the NPWP, year, year basis, or test scope. A different NPWP/year/year-basis cannot overwrite an existing run.json output scope.

The raw checkpoint command `--resume` is independent of the Excel filename `resume.xlsx`; it still resumes capture from inventory.json and return checkpoints. `--from-json` rebuilds all the split Excel files offline without opening the browser.

Identifiers and source figures are stored as literal text to preserve leading zeros, Indonesian number formatting and source precision. Summary counts are numeric. Source strings beginning with `=` are **not** executed as Excel formulas. Values that Excel cannot represent exactly, including a field/table cell longer than 32,767 characters, unsupported XML controls or numeric precision that would be lost, stop the export explicitly. Long page-context text is split across cells without truncation; the raw JSON remains available for recovery. Only HTTP/HTTPS source URLs become active links; other URL text is preserved without an executable link. The workbook is not encrypted; handle it as confidential taxpayer data.

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

If a local debugging browser is reused, its endpoint must be a localhost HTTP/HTTPS origin without credentials, path, query or fragment. Other local programs may be able to access that session while the debugging browser is open, so close the dedicated automation window after use. Never expose its port to the network. The normal fresh-browser path does not enable a debugging port.

No submission, cancellation, email, PDF-generation or arbitrary row-action buttons are clicked. If the View selector or page structure changes, the tool reports an error rather than guessing an action.

## Troubleshooting and tests

- **Login required / MFA / CAPTCHA:** finish in the visible browser. `--non-interactive` requires an existing authenticated session.
- **Profile in use:** close only the dedicated automation window, or reuse its known local endpoint. Do not kill your personal browser or copy its cookies.
- **NPWP not found / ambiguous result:** check the exact input and account authorization. The script does not select partial matches.
- **Source counts or metadata change mid-run:** start a fresh inventory in a new folder. Check Audit.
- **Unknown return layout:** inspect the relevant saved checkpoint before extending selectors; keep the run PARTIAL until verified.

Development tests use locally served synthetic HTML fixtures, explicitly separate from taxpayer outputs:

```bat
uv pip install --python .venv\Scripts\python.exe -r requirements-test.txt
.venv\Scripts\python.exe -m pytest tests -q --basetemp "%LOCALAPPDATA%\hermes\cache\scratch\coretax-tests"
```

The tool has been exercised against the authorized intranet session as well as the fixture tests. See the delivered workbook's Audit for the particular run's verified results and limitations.

## Development repository

Development takes place in https://github.com/cepeter-job/spt-downloader. The repository contains source, documentation and synthetic fixture tests only. Never commit real taxpayer data, captured JSON, Excel outputs, browser profiles, credentials or cookies. Existing local tax outputs stay outside this repository.

## Continuous verification

GitHub Actions runs the synthetic test suite on Windows with CPython 3.11 and the installed Edge browser for pull requests and pushes to `main` and `feat/windows-desktop`. It audits the installed runtime, test and available desktop-build dependencies with `pip-audit`; a weekly scheduled run checks dependencies without rebuilding the app. An unavailable advisory service fails the check so an unverified audit cannot look successful.

The workflow pins actions by commit and uv to the patched 0.12.18 release. Its uv cache contains dependency packages, never browser profiles, tax outputs or test workspaces. PRs can restore the cache but do not save it. Desktop builds, when present, run after tests and dependency audit in the same job, exercise the frozen GUI, and upload only the allowlisted executable, license, usage instructions, self-test report and SHA-256 manifest. Artifact names include the tested commit. Dependabot groups weekly dependency and action update PRs for review.

For the findings, verification boundaries and follow-up priorities, see [the October 2026 audit](docs/audit-2026-10-12.md).

## License

The repository retains its existing GNU General Public License, version 3. See [LICENSE](LICENSE).
