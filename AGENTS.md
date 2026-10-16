# Development instructions

This repository is the development home for the read-only Coretax SPT downloader. Keep changes small, explicit and covered by behavior tests.

Panduan kontributor bahasa Indonesia: mulai dari [docs/README.md](docs/README.md), lalu baca [setup dan pengujian](docs/pengembangan.md), [kontrak arsitektur](docs/arsitektur.md), dan [CI/rilis](docs/ci-dan-rilis.md). CLI dan desktop dikembangkan bersama pada `main` melalui PR.

## Data and access safety

- Commit source, documentation and clearly synthetic tests only. Never commit real taxpayer identifiers/records, captured JSON, Excel/PDF outputs, cookies, credentials, browser profiles or local virtual environments.
- Preserve NPWP, year, return identifiers and source values exactly. Use only authorized browser access; never bypass login, CAPTCHA, MFA or taxpayer permissions.
- Click only inspected read-only navigation/View controls. Never guess row actions or submit/cancel returns, generate remote documents, or send emails.
- Stop requests take precedence over running capture. Delayed process notifications must not restart a stopped job. Keep limited or failed runs explicitly PARTIAL.
- Do not fabricate missing tax data, simulate live API output, or create files for tax types absent from the captured scope.

## Output contract

`resume.xlsx` contains the global summary/index/audit. Every observed tax type gets a separate workbook per literal source period/year and literal `Model SPT`: Normal, Pembetulan 1, Pembetulan 2 and subsequent amendments must never share one workbook. Periodic types remain under `SPT Masa 21`, `SPT Masa Unifikasi` and `SPT Masa PPN`. Badan uses `SPT_Badan_<period>_<model>.xlsx`; periodic and other type filenames likewise include source period and model. Each workbook contains all observed form-only sheets for its own model. Use simple form names and minimal numeric suffixes only for workbook-local collisions; preserve raw period/model strings and leading zeroes in metadata and physical proof, never group by a display-normalized amendment label. Validate old combined exports before choosing a new final folder; do not silently rewrite or delete old combined workbooks or their PDFs. Preserve the entire folder hierarchy and exact relative links; reject case-insensitive path collisions and verify NPWP/year/basis before replacing outputs. Keep raw source values and duplicates; numeric analysis columns are optional and never replace source evidence. PPh Pasal 21/26 uses the approved sanitized user template for observed Induk/L-IA/L-IB/L-II/L-III forms: preserve cell styles, number formats, merges, dimensions and page layout; grow data rows by copying their original styles. Unsupported or ambiguous source content stays visible below the form without restyling its original cells. PPN and PPh Unifikasi likewise use the approved clean layouts for observed reference forms only; bind multi-level headers and repeated labels to their visible group, never guess JSON aliases. For PPN only, omit the redundant extra/unmapped block from exported forms; keep source captures unchanged and report unresolved bindings in the resume mapping audit. Its observed Period display supplies the month/year header, and Status Penyampaian is not displayed. Other Masa types retain explicit raw source evidence below the form for incomplete tables. Never ship sample taxpayer values or reference defaults (including a compensation choice) from reference templates.

Financial PDFs are limited to ordinary inspected read-only links exposed on the verified selected corporate Induk. Preserve explicit record/scope declarations, size/signature/hash checks, byte custody, cancellation and relative links; metadata alone is not a downloaded PDF. Publish only declared COMPLETE PDFs, never unrelated files in the job folder. Unsupported controls and failed downloads remain PARTIAL; do not invent API endpoints or remote generation actions.

## Verification

Create a local `.venv` with the production CPython/GIL pin in `spt_desktop.runtime.PYTHON_PROFILES`. Install the resolved test environment using `uv pip sync --python <venv-python> --require-hashes --only-binary :all: locks/test.txt`; use `locks/build.txt` for packaging. Run `python -m pytest tests -q` on Windows with a dedicated scratch `--basetemp` outside the repository. Linux can run the reviewed portable subset through `-p scripts.ci_tests --ci-workload portable`; Windows runs the full suite. Browser tests use isolated local synthetic HTML fixtures and an installed Microsoft Edge; they are not live taxpayer tests. Verify changed behavior, output counts, literal source text and links before committing.

For this user-authorized work, pytest, product imports, native/Tk/browser fixtures, source/frozen self-tests, builds and EXE execution are GitHub-runner-only. Local AST/source checks and artifact hash/metadata inspection are not execution evidence. Do not modify user-owned CI merely to obtain GREEN. Bind claims to exact head/merge tree/run/artifact ID and preserve recovery work.

Use an existing saved JSON capture for offline export/layout checks when appropriate, but keep that capture and its generated files outside version control. Review `git diff --cached --name-only` and staged content for private data before any push. Preserve the existing LICENSE.


## Desktop boundaries

- The GUI is a thin stdlib/Tkinter launcher. Do not import Playwright/openpyxl into its process; prepare the isolated worker with uv and copy only `spt_desktop.runtime.WORKER_FILES`. Update that explicit allowlist when adding worker modules; never recursively package workspace/profile/output directories.
- Windows Job Objects must contain suspended children **before** resuming them; uv-created virtualenv Python launchers can spawn an interpreter before Python code runs. Preserve start authorization, cooperative cancellation, 15-second forced owned-tree cleanup and main-thread-only UI callbacks. Success requires terminal COMPLETE, matching exit code, verified output and completed owned cleanup—not a zero exit alone.
- Saved credentials belong only to Windows Credential Manager and exact approved origins. Never print fill exceptions, inherit Playwright credential-debug flags, guess login actions or click generic form-submit controls. Require inspected sign-in intent and no unknown challenge/fields; otherwise manual visible login. No MFA/CAPTCHA bypass.
- Exercise both source and frozen GUI self-tests without real accounts. The Windows CI artifact must be read back by exact run/commit/artifact ID before reporting build success. Do not include private diagnostic logs or local test tax output in artifacts. Preserve source-level COMPLETE/PARTIAL checks and relative Excel links when staging/publishing to Known Folder Downloads.
