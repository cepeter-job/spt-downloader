"""Coretax NPWP + tax-year -> formatted Excel. Login is completed by the user in the browser."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from urllib.parse import urlparse

from openpyxl import load_workbook
from playwright.sync_api import sync_playwright
from coretax_exporter import validate_scope, export_split_workbooks, tax_type_filename
from coretax_browser import SEARCH_URL, collect_inventory, collect_details

BASE = Path(__file__).resolve().parent


def verify_workbook(path, run, *, include_details=True):
    wb = load_workbook(path, read_only=True, data_only=False)
    try:
        assert wb['Ringkasan']['B4'].value == run['npwp'], 'NPWP mismatch in output'
        assert wb['Ringkasan']['B4'].data_type == 's', 'NPWP was not preserved as text'
        assert wb['Ringkasan']['B5'].value == run['year'], 'Tax year mismatch in output'
        assert wb['Ringkasan']['B8'].value == ('COMPLETE' if run['complete'] else 'PARTIAL'), 'Incorrect completion status'
        assert wb['Daftar SPT'].max_row == 4 + len(run['records']), 'Excel index count mismatch'
        expected_sheets = 3 + len(run['records']) if include_details else 3
        assert len(wb.sheetnames) == expected_sheets, 'Incorrect worksheet count'
    finally:
        wb.close()


def save_output(run, folder):
    folder = Path(folder)
    validate_scope(run['npwp'], run['year'])
    scope_file = folder / 'run.json'
    if scope_file.exists():
        previous = json.loads(scope_file.read_text(encoding='utf-8'))
        scope_keys = ('npwp', 'year', 'year_basis')
        if any(previous.get(key) != run.get(key) for key in scope_keys):
            raise FileExistsError('Output scope differs from existing run.json; use a new output folder')
    folder.mkdir(parents=True, exist_ok=True)
    files = export_split_workbooks(run, folder)
    verify_workbook(files['resume.xlsx'], run, include_details=False)
    sheet_names = {}
    for filename, path in files.items():
        if filename == 'resume.xlsx':
            continue
        records = [record for record in run['records'] if tax_type_filename(record['meta'].get('Jenis Pajak')) == filename]
        verify_workbook(path, {**run, 'records': records})
        wb = load_workbook(path, read_only=True)
        try:
            sheet_names[filename] = set(wb.sheetnames)
        finally:
            wb.close()
    # Relative links keep the output portable when the whole folder is moved.
    resume = load_workbook(files['resume.xlsx'])
    try:
        for ordinal, record in enumerate(run['records'], 1):
            link = resume['Daftar SPT'].cell(ordinal + 4, 1).hyperlink
            expected_file = tax_type_filename(record['meta'].get('Jenis Pajak'))
            assert link and link.target == expected_file, 'Missing or incorrect type-workbook link'
            linked_sheet = link.location.rsplit('!', 1)[0][1:-1].replace("''", "'")
            assert linked_sheet in sheet_names[expected_file], 'Resume links to a nonexistent detail sheet'
    finally:
        resume.close()
    run['output_files'] = list(files)
    scope_file.write_text(json.dumps(run, ensure_ascii=False, indent=2), encoding='utf-8')
    return files['resume.xlsx']


def authenticate(page, noninteractive):
    page.goto(SEARCH_URL, wait_until='domcontentloaded', timeout=60000)
    if page.locator('#ObjectPermitNumber').is_visible():
        return
    page.bring_to_front()
    if noninteractive:
        # Angular may not have rendered the search yet; a login wall is never bypassed.
        page.locator('#ObjectPermitNumber').wait_for(state='visible', timeout=20000)
        return
    print('\nSign in directly in the browser window. Complete password, CAPTCHA and MFA there.')
    print('Do not enter any password or verification code into this script.')
    input('After sign-in, press Enter here to continue: ')
    page.goto(SEARCH_URL, wait_until='domcontentloaded', timeout=60000)
    page.locator('#ObjectPermitNumber').wait_for(state='visible', timeout=45000)


def parser():
    cli = argparse.ArgumentParser(description='Read-only authorized Coretax SPT export by exact NPWP and selected tax year.')
    cli.add_argument('--npwp', help='Exactly 16 digits; no normalization or separators')
    cli.add_argument('--year', help='Four-digit tax year')
    cli.add_argument('--year-basis', choices=['period', 'submission'], default='period', help='Default: tax period/year, not submission date')
    cli.add_argument('--output', type=Path, help='Output folder; default is a timestamped local folder')
    cli.add_argument('--resume', type=Path, help='Resume a previous output folder from verified checkpoints')
    cli.add_argument('--from-json', type=Path, help='Rebuild Excel offline from an existing run.json')
    cli.add_argument('--browser', choices=['msedge', 'chrome'], default='msedge')
    cli.add_argument('--profile', type=Path, default=BASE / 'browser-profile', help='Dedicated persistent profile, never your personal browser profile')
    cli.add_argument('--reuse-browser', nargs='?', const='http://127.0.0.1:9235', help='Connect to an already opened local automation browser')
    cli.add_argument('--non-interactive', action='store_true', help='Requires NPWP/year and an authenticated session; never prompts for credentials')
    cli.add_argument('--inventory-only', action='store_true', help='Capture SPT list only; output is explicitly PARTIAL for full-detail scope')
    cli.add_argument('--detail-limit', type=int, help='Test-only detail limit; output stays PARTIAL if any return remains unexported')
    cli.add_argument('--max-pages', type=int, default=1000, help='Safety cap per list/table; reaching it is reported as PARTIAL')
    return cli


def main(argv=None):
    cli = parser()
    args = cli.parse_args(argv)
    if args.max_pages < 1 or args.detail_limit is not None and args.detail_limit < 1:
        cli.error('Page and detail limits must be positive')
    if args.from_json:
        run = json.loads(args.from_json.read_text(encoding='utf-8'))
        validate_scope(run['npwp'], run['year'])
        folder = args.output or args.from_json.parent
        path = save_output(run, folder)
        print(f'Resume rebuilt and verified: {path.resolve()}')
        print('SPT files: ' + ', '.join(name for name in run['output_files'] if name != 'resume.xlsx'))
        return 0 if run.get('complete') else 2
    if args.resume:
        folder = args.resume.resolve()
        run = json.loads((folder / 'inventory.json').read_text(encoding='utf-8'))
        if args.npwp is not None and args.npwp != run['npwp'] or args.year is not None and str(args.year) != str(run['year']):
            cli.error('Resume scope must match the checkpoint exactly')
        npwp, year = validate_scope(run['npwp'], run['year'])
    else:
        if args.non_interactive and (args.npwp is None or args.year is None):
            cli.error('--non-interactive requires --npwp and --year, or --resume')
        npwp = args.npwp if args.npwp is not None else input('NPWP (16 digits, no separators): ')
        entered_year = args.year if args.year is not None else input('Tax year (e.g. 2025): ')
        npwp, year = validate_scope(npwp, entered_year)
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        folder = (args.output or BASE / 'output' / f'{npwp}_{year}_{stamp}').resolve()
        run = None
    print(f'Scope: NPWP {npwp} | year {year} | basis {run["year_basis"] if run else args.year_basis}')
    print('READ-ONLY: no submission, cancellation, PDF-generation or email actions.')
    if args.reuse_browser:
        endpoint = urlparse(args.reuse_browser)
        if endpoint.scheme not in ('http', 'https') or endpoint.hostname not in ('127.0.0.1', 'localhost', '::1'):
            cli.error('--reuse-browser must be a localhost HTTP debugging endpoint')
    start = time.monotonic()
    owned_context = None
    work_page = None
    output_path = None
    with sync_playwright() as playwright:
        try:
            if args.reuse_browser:
                browser = playwright.chromium.connect_over_cdp(args.reuse_browser, timeout=20000)
                context = browser.contexts[0]
            else:
                owned_context = playwright.chromium.launch_persistent_context(str(args.profile.resolve()), channel=args.browser,
                    headless=False, no_viewport=True, args=['--no-first-run', '--no-default-browser-check'])
                context = owned_context
            work_page = context.new_page()
            work_page.set_viewport_size({'width': 1600, 'height': 1000})
            authenticate(work_page, args.non_interactive)
            if run is None:
                run = collect_inventory(work_page, npwp, year, args.year_basis, folder, max_pages=args.max_pages)
            run['started_at'] = run.get('started_at') or datetime.now().astimezone().isoformat()
            run['complete'] = False
            if args.inventory_only:
                run['errors'].append({'object': 'Scope', 'message': 'Inventory-only run. Return-detail content not captured.'})
            else:
                def progress(current_run, ordinal):
                    if ordinal % 5 == 0:
                        current_run['complete'] = False
                        save_output(current_run, folder)
                collect_details(work_page, run, folder, max_pages=args.max_pages, detail_limit=args.detail_limit, on_progress=progress)
            run['finished_at'] = datetime.now().astimezone().isoformat()
            run['duration_seconds'] = round(time.monotonic() - start, 2)
            output_path = save_output(run, folder)
        except KeyboardInterrupt:
            if run is not None:
                run['complete'] = False
                run['errors'].append({'object': 'Run', 'phase': 'details', 'message': 'Interrupted. Resume this output folder to retry incomplete returns.'})
                output_path = save_output(run, folder)
            print('Interrupted; existing checkpoints retained.', file=sys.stderr)
            return 130
        except Exception as exc:
            if run is not None:
                run['complete'] = False
                run['errors'].append({'object': 'Run', 'phase': 'details', 'message': str(exc).split('\n')[0]})
                output_path = save_output(run, folder)
            print(f'BLOCKED: {str(exc).splitlines()[0]}', file=sys.stderr)
            print('Sign in again if needed; close a locked dedicated profile or use --reuse-browser; inspect Audit for data-layout failures.', file=sys.stderr)
            return 1
        finally:
            if work_page is not None and not work_page.is_closed():
                work_page.close()
            if owned_context is not None:
                owned_context.close()
    count = sum(r.get('capture_complete', False) for r in run['records'])
    print(f"{'COMPLETE' if run['complete'] else 'PARTIAL'}: {count}/{len(run['records'])} return details verified")
    print(f'Resume Excel: {output_path.resolve()}')
    print('SPT files: ' + ', '.join(name for name in run['output_files'] if name != 'resume.xlsx'))
    print(f'Checkpoints: {folder}')
    print(f"Duration: {run['duration_seconds']} seconds")
    return 0 if run['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
