"""Financial PDF contracts use intercepted synthetic pages and bytes only."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
from pathlib import PurePosixPath
import subprocess
import sys

import pytest
from playwright.sync_api import sync_playwright

import coretax_browser as source_browser

# Even an accidentally followed redirect must not target the real portal.
# Existing browser-safety tests separately cover the production origin pin.
ORIGIN = 'https://coretax.synthetic.invalid'

RECORD = {
    'record_id': 'SYNTHETIC_BADAN_RETURN',
    'list_url': ORIGIN + '/returnsheets/id-ID/corporatereturnsheets/SYNTHETIC_TAXPAYER',
    'scope': ['0000000000000001', '2025', 'period'],
    'meta': {'Jenis Pajak': 'PPh Badan', 'Masa Pajak': '2025', 'Model SPT': 'Normal'},
}
DETAIL = RECORD['list_url'] + '/' + RECORD['record_id']
PDF_URL = ORIGIN + '/synthetic-existing/statement.pdf'
PDF = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'
LABEL = 'Laporan Keuangan'


def attachments():
    # Resolve inside a test, so missing implementation is an explicit RED
    # assertion instead of preventing collection of the existing full suite.
    assert importlib.util.find_spec('coretax_attachments') is not None, 'Financial attachment implementation is missing'
    module = importlib.import_module('coretax_attachments')
    assert callable(getattr(module, 'download_financial_attachments', None)), 'Financial attachment public API is missing'
    return module


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as engine:
        owned = engine.chromium.launch(channel='msedge', headless=True)
        yield owned
        owned.close()


@pytest.fixture
def routed(browser, monkeypatch):
    monkeypatch.setattr(source_browser, 'ORIGIN', ORIGIN)
    contexts = []

    def create(control, *, body=PDF, content_type='application/pdf', status=200, headers=None, detail=DETAIL):
        context = browser.new_context(service_workers='block')
        contexts.append(context)
        requests = []

        def route(intercept):
            request = intercept.request
            if request.url == detail:
                intercept.fulfill(body='<main class="main-content"><h1>Induk</h1>' + control + '</main>', content_type='text/html')
            elif request.url == PDF_URL:
                intercept.fulfill(body=body, content_type=content_type, status=status, headers=headers or {})
            else:
                # A redirect or navigation can never escape to the intranet.
                intercept.abort('blockedbyclient')

        context.route('**/*', route)
        page = context.new_page()
        # Route handlers need not see redirected destinations; page events do.
        page.on('request', lambda request: requests.append((request.method, request.url)))
        page.goto(detail, wait_until='domcontentloaded')
        return page, requests

    yield create
    for context in contexts:
        context.close()


def partial(result):
    assert result and all(item['status'] == 'PARTIAL' for item in result)
    assert all(not item.get('relative_path') for item in result)


def downloaded(result, folder):
    assert len(result) == 1 and result[0]['status'] == 'COMPLETE'
    item = result[0]
    relative = PurePosixPath(item['relative_path'])
    assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in str(relative)
    assert relative.suffix.lower() == '.pdf'
    path = folder.joinpath(*relative.parts)
    assert path.is_file() and not path.is_symlink() and path.read_bytes() == PDF
    assert item['bytes'] == len(PDF) and item['hash'] == hashlib.sha256(PDF).hexdigest()
    return item, path


@pytest.mark.parametrize('label', [LABEL, 'Laporan Keuangan yang Telah Diaudit*'])
def test_existing_inspected_financial_href_is_downloaded_by_get_only(routed, tmp_path, label):
    module = attachments()
    page, requests = routed('<a href="/synthetic-existing/statement.pdf"><span>' + label + '</span></a>')
    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    item, path = downloaded(result, tmp_path)
    assert item['label'] == label
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]
    assert not any(path.name.endswith(suffix) for suffix in ('.part', '.tmp'))


@pytest.mark.parametrize('control', [
    '<button onclick="fetch(\'/generate-statement\',{method:\'POST\'})">Laporan Keuangan</button>',
    '<a href="/synthetic-existing/statement.pdf" onclick="fetch(\'/generate-statement\')">Laporan Keuangan</a>',
    '<a href="javascript:generatePDF()">Laporan Keuangan</a>',
    '<a href="data:application/pdf;base64,JVBERg==">Laporan Keuangan</a>',
    '<a href="blob:https://coretax.synthetic.invalid/synthetic">Laporan Keuangan</a>',
    '<a href="#">Laporan Keuangan</a>',
    '<a href="https://outside.invalid/statement.pdf">Laporan Keuangan</a>',
    '<a href="http://coretax.synthetic.invalid/statement.pdf">Laporan Keuangan</a>',
    '<a href="https://coretax.synthetic.invalid:444/statement.pdf">Laporan Keuangan</a>',
    '<a href="/generate-statement">Laporan Keuangan</a>',
])
def test_unsupported_control_never_clicks_generates_or_follows_an_unapproved_url(routed, tmp_path, control):
    module = attachments()
    page, requests = routed(control)
    partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path))
    assert requests == [('GET', DETAIL)] and not list(tmp_path.rglob('*.pdf'))


def test_absent_financial_control_is_explicitly_partial_without_an_invented_file(routed, tmp_path):
    module = attachments()
    page, requests = routed('<p>No financial download control exposed in this synthetic Induk.</p>')
    partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path))
    assert requests == [('GET', DETAIL)] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('detail', [
    ORIGIN + '/returnsheets/id-ID/corporatereturnsheets/OTHER_SYNTHETIC_TAXPAYER/SYNTHETIC_BADAN_RETURN',
    ORIGIN + '/returnsheets/id-ID/corporatereturnsheets/SYNTHETIC_TAXPAYER/OTHER_SYNTHETIC_RETURN',
])
def test_pdf_capture_cannot_cross_the_inspected_return_or_taxpayer_scope(routed, tmp_path, detail):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>', detail=detail)
    with pytest.raises((ValueError, RuntimeError)):
        module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    assert requests == [('GET', detail)] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('body,content_type', [
    (b'<html>synthetic expired login</html>', 'text/html'),
    (b'%PDF-1.4\ntruncated synthetic response', 'application/pdf'),
    (b'synthetic non-PDF\n%%EOF', 'application/pdf'),
])
def test_html_and_incomplete_pdf_responses_remain_partial(routed, tmp_path, body, content_type):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>', body=body, content_type=content_type)
    partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path))
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('headers', [{}, {'Content-Length': '999999'}])
def test_pdf_limit_is_enforced_even_without_a_trustworthy_content_length(routed, tmp_path, monkeypatch, headers):
    module = attachments()
    monkeypatch.setattr(module, 'MAX_PDF_BYTES', len(PDF) - 1)
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>', headers=headers)
    partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path))
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('location', [ORIGIN + '/synthetic-existing/other.pdf', 'https://outside.invalid/statement.pdf'])
def test_redirect_fixture_proves_error_mode_prevents_a_destination_request(routed, location):
    page, requests = routed('', body=b'', status=302, headers={'Location': location})
    rejected = page.evaluate('''async url => {
        try {
            await fetch(url, {method: 'GET', redirect: 'error', credentials: 'same-origin'});
            return false;
        } catch {
            return true;
        }
    }''', PDF_URL)
    assert rejected and requests == [('GET', DETAIL), ('GET', PDF_URL)]


@pytest.mark.parametrize('location', [ORIGIN + '/synthetic-existing/other.pdf', 'https://outside.invalid/statement.pdf'])
def test_redirect_is_rejected_before_following_any_destination(routed, tmp_path, location):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>', body=b'', status=302, headers={'Location': location})
    partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path))
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('during_read', [False, True])
def test_stop_wins_before_request_or_before_persisting_completed_bytes(routed, tmp_path, during_read):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>')

    def cancelled():
        if not during_read or ('GET', PDF_URL) in requests:
            raise source_browser.CaptureCancelled('synthetic financial download stop')

    with pytest.raises(source_browser.CaptureCancelled):
        module.download_financial_attachments(page, deepcopy(RECORD), tmp_path, check_cancel=cancelled)
    assert not list(tmp_path.rglob('*.pdf'))
    if not during_read:
        assert requests == [('GET', DETAIL)]


def test_existing_owned_pdf_is_never_silently_overwritten(routed, tmp_path):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>')
    first = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)
    item, path = downloaded(first, tmp_path)
    sentinel = b'UNAPPROVED SYNTHETIC FILE'
    path.write_bytes(sentinel)
    partial(module.download_financial_attachments(page, deepcopy(RECORD), tmp_path))
    assert path.read_bytes() == sentinel


def test_private_output_cannot_redirect_through_a_real_junction(routed, tmp_path):
    module = attachments()
    outside = tmp_path / 'outside'
    outside.mkdir()
    alias = tmp_path / 'alias'
    if sys.platform == 'win32':
        command = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(alias), str(outside)], capture_output=True, text=True)
        assert command.returncode == 0, command.stdout + command.stderr
    else:
        alias.symlink_to(outside, target_is_directory=True)
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>')
    try:
        with pytest.raises((ValueError, RuntimeError)):
            module.download_financial_attachments(page, deepcopy(RECORD), alias)
        assert not list(outside.iterdir()) and requests == [('GET', DETAIL)]
    finally:
        if sys.platform == 'win32':
            alias.rmdir()
        else:
            alias.unlink()


def set_document_base(page, href):
    page.evaluate('''href => {
        let base = document.querySelector('base');
        if (!base) {
            base = document.createElement('base');
            document.head.append(base);
        }
        base.href = href;
    }''', href)


@pytest.mark.parametrize('base_href', ['/synthetic-existing/', ORIGIN + '/synthetic-existing/'])
def test_pdf_get_uses_the_inspected_browser_resolved_href_with_document_base(routed, tmp_path, base_href):
    module = attachments()
    page, requests = routed('<a href="statement.pdf">Laporan Keuangan</a>')
    set_document_base(page, base_href)
    assert page.locator('a').evaluate('anchor => anchor.href') == PDF_URL

    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    downloaded(result, tmp_path)
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


def test_foreign_document_base_cannot_turn_a_raw_relative_href_into_an_approved_get(routed, tmp_path):
    module = attachments()
    page, requests = routed('<a href="/synthetic-existing/statement.pdf">Laporan Keuangan</a>')
    set_document_base(page, 'https://outside.synthetic.invalid/published/')
    assert page.locator('a').evaluate('anchor => anchor.href') == 'https://outside.synthetic.invalid/synthetic-existing/statement.pdf'

    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    partial(result)
    assert requests == [('GET', DETAIL)] and not list(tmp_path.rglob('*.pdf'))


def test_absolute_approved_pdf_href_is_not_rejected_only_because_document_base_is_foreign(routed, tmp_path):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>')
    set_document_base(page, 'https://outside.synthetic.invalid/published/')
    assert page.locator('a').evaluate('anchor => anchor.href') == PDF_URL

    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    downloaded(result, tmp_path)
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


@pytest.mark.parametrize('href', [' ' + PDF_URL, ORIGIN + '/synthetic-existing\\statement.pdf'])
def test_browser_url_normalization_cannot_bypass_the_existing_raw_href_guards(routed, tmp_path, href):
    module = attachments()
    page, requests = routed('<a href="' + href + '">Laporan Keuangan</a>')
    # Browser normalization is not permission to discard unsafe raw evidence.
    assert page.locator('a').evaluate('anchor => anchor.href') == PDF_URL

    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    partial(result)
    assert requests == [('GET', DETAIL)] and not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('boundary', ['after_scan', 'before_fetch'])
def test_changed_detail_document_is_rejected_before_any_pdf_get(routed, tmp_path, monkeypatch, boundary):
    module = attachments()
    page, requests = routed('<a href="' + PDF_URL + '">Laporan Keuangan</a>')
    other_detail = RECORD['list_url'] + '/OTHER_SYNTHETIC_RETURN'
    page.route(other_detail, lambda route: route.fulfill(
        body='<main class="main-content"><h1>Other synthetic return</h1></main>',
        content_type='text/html'))
    evaluate = page.evaluate
    reached = []

    def evaluate_with_document_change(expression, *args, **kwargs):
        if boundary == 'before_fetch' and expression == module._START and not reached:
            reached.append(boundary)
            page.goto(other_detail, wait_until='domcontentloaded')
        result = evaluate(expression, *args, **kwargs)
        if boundary == 'after_scan' and expression == module._SCAN and not reached:
            reached.append(boundary)
            page.goto(other_detail, wait_until='domcontentloaded')
        return result

    # Inject real navigation at the existing browser boundary, not a fake URL.
    monkeypatch.setattr(page, 'evaluate', evaluate_with_document_change)
    result = module.download_financial_attachments(page, deepcopy(RECORD), tmp_path)

    assert reached == [boundary]
    partial(result)
    assert requests == [('GET', DETAIL), ('GET', other_detail)]
    assert not list(tmp_path.rglob('*.pdf'))
