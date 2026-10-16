"""Synthetic financial browser helpers; no collected tests or shared mutable test state."""
import hashlib
import importlib
import importlib.util
from pathlib import PurePosixPath
import pytest
from playwright.sync_api import sync_playwright
import coretax_browser as source_browser


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
