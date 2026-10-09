# Development instructions

This repository is the development home for the read-only Coretax SPT downloader. Keep changes small, explicit and covered by behavior tests.

## Data and access safety

- Commit source, documentation and clearly synthetic tests only. Never commit real taxpayer identifiers/records, captured JSON, Excel/PDF outputs, cookies, credentials, browser profiles or local virtual environments.
- Preserve NPWP, year, return identifiers and source values exactly. Use only authorized browser access; never bypass login, CAPTCHA, MFA or taxpayer permissions.
- Click only inspected read-only navigation/View controls. Never guess row actions or submit/cancel returns, generate remote documents, or send emails.
- Stop requests take precedence over running capture. Delayed process notifications must not restart a stopped job. Keep limited or failed runs explicitly PARTIAL.
- Do not fabricate missing tax data, simulate live API output, or create files for tax types absent from the captured scope.

## Output contract

`resume.xlsx` contains the global summary/index/audit. Each tax type gets one workbook (Badan, 21/26, Unifikasi, and other available types), containing every selected period and distinct amendment. Preserve relative links and keep all generated workbooks together. Check case-insensitive filename collisions and NPWP/year scope before overwriting outputs.

## Verification

Install production requirements and `pytest==9.1.1` in a local `.venv`. Run `python -m pytest tests -q` with a dedicated scratch `--basetemp` outside the repository. Browser tests use isolated local synthetic HTML fixtures and an installed Microsoft Edge; they are not live taxpayer tests. Verify changed behavior, output counts, literal source text and links before committing.

Use an existing saved JSON capture for offline export/layout checks when appropriate, but keep that capture and its generated files outside version control. Review `git diff --cached --name-only` and staged content for private data before any push. Preserve the existing LICENSE.
