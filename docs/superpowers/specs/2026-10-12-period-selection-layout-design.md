# Selected SPT and period workbook design

Approved by the user in chat on 2026-10-12 after pulling feat/windows-desktop to 013dd19. This is a bounded revision of the existing capture/export/desktop flows, not a new tax-data platform.

## Output contract

- Keep resume.xlsx as the selected-run index/audit, with relative links.
- SPT Masa 21, SPT Masa Unifikasi, and SPT Masa PPN have separate folders, and exactly one workbook per literal source period within each folder. Normal and all selected amendments for the same period share that workbook and have distinct descriptive sheets.
- Corporate returns remain in SPT_Badan.xlsx with a sheet per observed form/section (Induk, L1-D, etc.), distinguished by Normal/Pembetulan and a collision-safe ordinal. Do not invent unobserved forms.
- Use flat filterable fields/tables, frozen headers, widths, and source evidence. Preserve raw identifiers/values, duplicate rows, captions, and exact amendment provenance. Add validated numeric analysis values without silently altering raw text.
- Download only existing, inspected read-only financial-statement/audited-financial-statement PDF links in corporate Induk. Never generate a remote document or guess an API URL. Use the authorized browser context, exact HTTPS origin, GET-only downloads with no unchecked redirects, bounded size and PDF validation. Unsupported available controls/failures are explicitly PARTIAL.

## Run interaction

- Inventory only first; show the observed returns and allow choosing individual records by type, period, and Normal/Pembetulan. Capture details only for confirmed IDs. An intentionally selected subset may be COMPLETE for that declared subset, not for the entire year.
- Selection and overwrite replies are job-bound and cancellation-aware. No default all-record capture while waiting. Keep GUI callbacks on the Tk main thread and preserve owned-process cleanup.
- Downloads publication uses verified scope and relative paths. Existing colliding results require explicit overwrite consent; declining preserves old bytes. Never overwrite unselected files, unknown workbooks, mismatched NPWP/year/basis, symlinks or junction escapes. Stage and validate before replacement; retain rollback recovery on failure.

## Authentication and exact copy

- Reproduce recognition gaps with synthetic fixtures and inspected sanitized DOM; do not relax the approved-origin/form/submission/control-binding/CAPTCHA/MFA safeguards or log secrets.
- Header: `Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang`
- Background setting: `jalankan proses sedot di background`
- Output description: `Hasil Sedot berada di folder Downloads Windows`
- Preserve existing personal-use subtitle and credit.

## Verification and boundaries

Baseline on pulled code: 289 tests passed in 67.24 seconds. All new data is clearly synthetic. Test per-period file counts, per-form/amendment names, raw-value preservation and filters, exact relative links, selected-only capture, decline/approve overwrite and rollback, PDF bytes/origin/redirect/cancellation handling, authentication rejection/binding, and all exact GUI strings. Exercise source and frozen GUI self-tests and reopen generated XLSX files with the excel-workbench audit.

Actual login DOM probe timed out. No real taxpayer capture or credential submission has been performed. Live portal recognition and financial download controls require real evidence before claiming live acceptance. No source commit/push without the user's separate confirmation.
