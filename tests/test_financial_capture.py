"""Induk capture contracts use intercepted synthetic pages and bytes only."""
from copy import deepcopy
import hashlib
import json
from pathlib import PurePosixPath

import pytest
from playwright.sync_api import sync_playwright

import coretax_browser as driver
from test_diagnostics import records as diagnostic_records

ORIGIN = 'https://coretax.synthetic.invalid'
RECORD = {
    'key': 'SYNTHETIC_BADAN_RETURN',
    'record_id': 'SYNTHETIC_BADAN_RETURN',
    'list_url': ORIGIN + '/returnsheets/id-ID/corporatereturnsheets/SYNTHETIC_TAXPAYER',
    'scope': ['0000000000000001', 2025, 'period'],
    'source_status': 'SYNTHETIC FIXTURE ONLY',
    'meta': {'Jenis Pajak': 'PPh Badan', 'Masa Pajak': '2025', 'Model SPT': 'Normal'},
}
DETAIL = RECORD['list_url'] + '/' + RECORD['record_id']
PDF_URL = ORIGIN + '/synthetic-existing/statement.pdf'
PDF = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'
LABEL = 'Laporan Keuangan yang Telah Diaudit*'
CONTROL = '<a href="/synthetic-existing/statement.pdf"><span>' + LABEL + '</span></a>'

# Start and finish on L1D: downloading only before or after traversal misses
# the financial href, which exists solely on the visible inspected Induk.
HTML = """<!doctype html><html><body>
<main class="main-content"><div class="p-tabview">
<ul class="p-tabview-nav">
<li><a role="tab" aria-controls="induk" onclick="show('induk')">Induk</a></li>
<li><a role="tab" aria-controls="l1d" onclick="show('l1d')">L1D</a></li>
</ul><div class="p-tabview-panels">
<p-tabpanel><div class="p-tabview-panel" id="induk" hidden>
<label for="identifier">Nomor literal</label><input id="identifier" value="0000123">
<label for="amount">Nilai literal</label><input id="amount" value="1.234,56">
<table><thead><tr><th>Kode</th><th>Nilai</th></tr></thead>
<tbody><tr><td>0007</td><td>1.234,56</td></tr>
<tr><td>0007</td><td>1.234,56</td></tr></tbody></table>
__CONTROL__
</div></p-tabpanel>
<p-tabpanel><div class="p-tabview-panel" id="l1d">
<label for="other">Penanda L1D</label><input id="other" value="SYNTHETIC L1D ONLY">
</div></p-tabpanel>
</div></div></main>
<script>function show(id) {
  document.querySelectorAll('.p-tabview-panel').forEach(p => p.hidden = p.id !== id);
}</script></body></html>"""


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as engine:
        owned = engine.chromium.launch(channel='msedge', headless=True)
        try:
            yield owned
        finally:
            owned.close()


@pytest.fixture
def routed(browser, monkeypatch):
    monkeypatch.setattr(driver, 'ORIGIN', ORIGIN)
    contexts = []

    def create(control=CONTROL):
        context = browser.new_context(service_workers='block')
        contexts.append(context)
        requests = []

        def route(intercept):
            if intercept.request.url == DETAIL:
                intercept.fulfill(body=HTML.replace('__CONTROL__', control), content_type='text/html')
            elif intercept.request.url == PDF_URL:
                intercept.fulfill(body=PDF, content_type='application/pdf')
            else:
                intercept.abort('blockedbyclient')

        context.route('**/*', route)
        page = context.new_page()
        page.on('request', lambda request: requests.append((request.method, request.url)))
        page.goto(DETAIL, wait_until='domcontentloaded')
        assert page.locator('#l1d').is_visible() and not page.locator('#induk').is_visible()
        return page, requests

    try:
        yield create
    finally:
        for context in contexts:
            context.close()


@pytest.mark.parametrize('limited', [False, True])
def test_detail_records_anonymous_table_duration_and_counts(routed, tmp_path, limited):
    page, requests = routed()
    page.evaluate('''limited => {
        const table = '<table><thead><tr><th>Literal</th></tr></thead>' +
            '<tbody><tr><td>SYNTHETIC-PRIVATE-CELL</td></tr></tbody></table>';
        document.querySelector('#induk').insertAdjacentHTML('beforeend', table);
        document.querySelector('#l1d').insertAdjacentHTML('beforeend', '<p-table>'+table+
            (limited ? '<button class="p-paginator-next">Next</button>' : '')+'</p-table>');
    }''', limited)
    with driver.diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path, max_pages=1)
        assert log.flush()
    assert result['capture_complete'] is not limited
    rows = [json.loads(line) for path in (tmp_path / 'diagnostics/logs').glob('*.jsonl')
            for line in path.read_text(encoding='utf-8').splitlines()]
    tables = [row for row in rows if row['event'] == 'phase.completed' and row.get('phase') == 'table']
    assert [(row['form_ordinal'], row['table_ordinal']) for row in tables] == [(1, 1), (1, 2), (2, 1)]
    assert tables[0]['body_rows'] == 2 and tables[0]['pages'] == 1
    assert tables[0]['status'] == 'COMPLETE' and tables[0]['duration_ms'] >= 0
    assert tables[-1]['status'] == ('PARTIAL' if limited else 'COMPLETE')
    serialized = json.dumps(rows)
    for private in (RECORD['record_id'], PDF_URL, '1.234,56', '0000123', 'SYNTHETIC-PRIVATE-CELL'):
        assert private not in serialized


@pytest.mark.parametrize('failure,want_state,want_owned,want_document,want_views', [
    ('hidden', 'hidden', 1, 1, 1),
    ('ancestor', 'hidden', 1, 1, 1),
    ('css-hidden', 'hidden', 1, 1, 1),
    ('missing', 'missing', 0, 0, 1),
    ('outside-view', 'outside_view', 0, 1, 2),
])
def test_induk_timeout_records_structure_without_private_dom_or_repairing_capture(
        routed, tmp_path, monkeypatch, failure, want_state, want_owned, want_document, want_views):
    page, requests = routed()
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    page.evaluate("""failure => {
        const tab = document.querySelector('a[aria-controls="induk"]');
        const panel = document.getElementById('induk');
        panel.id = 'SYNTHETIC_PANEL_SECRET';
        panel.querySelector('input').value = 'SYNTHETIC_FIELD_SECRET';
        tab.setAttribute('aria-controls', panel.id);
        tab.setAttribute('aria-selected', 'true');
        window.indukClicks = 0;
        tab.onclick = () => window.indukClicks++;
        if (failure === 'missing') panel.remove();
        if (failure === 'ancestor') {
            panel.hidden = false;
            panel.parentElement.hidden = true;
        }
        if (failure === 'css-hidden') {
            panel.hidden = false;
            panel.style.visibility = 'hidden';
        }
        if (failure === 'outside-view') {
            const other = document.createElement('div');
            other.className = 'p-tabview';
            document.querySelector('.main-content').append(other);
            other.append(panel);
            panel.hidden = false;
        }
    }""", failure)
    with driver.diagnostics.session(tmp_path, 'worker', level='INFO') as log:
        with driver.diagnostics.detail_context(ordinal=1, tax_kind='corporate', source_requested='dom'):
            result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
        assert log.flush()
    assert [section['name'] for section in result['sections']] == ['L1D']
    assert result['capture_complete'] is False
    assert len(result['attachments']) == 1
    assert result['attachments'][0]['status'] == 'PARTIAL'
    assert result['attachments'][0]['relative_path'] is None
    assert len(result['errors']) == 2 and result['errors'][0]['message'] == 'capture_timeout'
    assert 'No inspected corporate Induk' in result['errors'][1]['message']
    assert requests == [('GET', DETAIL)] and page.evaluate('window.indukClicks') == 1
    events = [row for row in diagnostic_records(tmp_path) if row['event'] == 'capture.panel_timeout']
    assert len(events) == 1, 'Panel timeout must retain one value-free structural snapshot'
    event = events[0]
    assert event['panel_state'] == want_state
    assert event['panel_matches'] == want_owned
    assert event['document_panel_matches'] == want_document
    assert event['tab_views'] == want_views
    assert event['panel_controlled'] is True and event['tab_state'] == 'selected'
    assert event['ordinal'] == 1 and event['tax_kind'] == 'corporate'
    assert event['source_requested'] == 'dom' and event['duration_ms'] >= 2000
    text = json.dumps(diagnostic_records(tmp_path))
    for secret in ('SYNTHETIC_PANEL_SECRET', 'SYNTHETIC_FIELD_SECRET', '0000123',
                   '1.234,56', ORIGIN, RECORD['record_id'], 'aria-controls', 'outerHTML'):
        assert secret not in text


def test_induk_timeout_probe_failure_keeps_original_timeout_and_later_appendix(routed, tmp_path, monkeypatch):
    import sys

    page, requests = routed()
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    page.locator('a[aria-controls="induk"]').evaluate('(tab) => { tab.onclick = () => {}; }')
    locator_type = type(page.locator('body'))
    original_evaluate = locator_type.evaluate
    original_probe = driver._record_panel_timeout
    original_timeouts = []

    def observe_original_timeout(*args, **kwargs):
        # The shared deadline can expire in any bounded locator read. Capture
        # the actual exception before the diagnostic probe, then require exact
        # preservation instead of assuming which locator operation expired.
        error = sys.exc_info()[1]
        assert isinstance(error, driver.PlaywrightTimeoutError)
        original_timeouts.append(type(error).__name__)
        return original_probe(*args, **kwargs)

    def fail_snapshot(locator, expression, arg=None, **kwargs):
        # Inject a failed browser read at the diagnostic boundary, not the
        # capture itself: the original timeout must remain the primary error.
        if expression == getattr(driver, 'PANEL_TIMEOUT_JS', None):
            raise RuntimeError('SYNTHETIC_SNAPSHOT_PRIVATE')
        return original_evaluate(locator, expression, arg, **kwargs)

    monkeypatch.setattr(locator_type, 'evaluate', fail_snapshot)
    monkeypatch.setattr(driver, '_record_panel_timeout', observe_original_timeout)
    with driver.diagnostics.session(tmp_path, 'worker') as log:
        result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
        assert log.flush()
    assert [section['name'] for section in result['sections']] == ['L1D']
    assert result['capture_complete'] is False
    assert len(original_timeouts) == 1
    assert original_timeouts == ['TimeoutError']
    assert result['errors'][0]['message'] == 'capture_timeout'
    partial = [row for row in diagnostic_records(tmp_path) if row['event'] == 'capture.partial']
    assert partial[0]['error']['type'] == 'TimeoutError'
    assert requests == [('GET', DETAIL)]
    events = [row for row in diagnostic_records(tmp_path) if row['event'] == 'capture.panel_timeout']
    assert len(events) == 1 and events[0]['panel_state'] == 'unavailable'
    assert not {'panel_matches', 'document_panel_matches', 'tab_views', 'tab_state'} & events[0].keys()
    assert 'SYNTHETIC_SNAPSHOT_PRIVATE' not in json.dumps(diagnostic_records(tmp_path))


def test_stop_during_induk_panel_wait_does_not_become_timeout_evidence(routed, tmp_path, monkeypatch):
    page, requests = routed()
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 1)
    page.locator('a[aria-controls="induk"]').evaluate(
        '(tab) => { tab.onclick = () => window.indukWaiting = true; }')
    checks = 0

    def cancel():
        nonlocal checks
        if page.evaluate('Boolean(window.indukWaiting)'):
            checks += 1
            if checks == 2:
                raise driver.CaptureCancelled('SYNTHETIC STOP')

    with driver.diagnostics.session(tmp_path, 'worker') as log:
        with pytest.raises(driver.CaptureCancelled):
            driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path, check_cancel=cancel)
        assert log.flush()
    assert not any(row['event'] == 'capture.panel_timeout' for row in diagnostic_records(tmp_path))
    assert requests == [('GET', DETAIL)]


def test_successful_induk_does_not_emit_panel_timeout(routed, tmp_path):
    page, requests = routed()
    with driver.diagnostics.session(tmp_path, 'worker', level='INFO') as log:
        result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
        assert log.flush()
    assert result['capture_complete'] is True
    assert not any(row['event'] == 'capture.panel_timeout' for row in diagnostic_records(tmp_path))
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


def test_financial_pdf_is_captured_while_induk_is_visible_without_changing_raw_data(routed, tmp_path):
    page, requests = routed()
    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
    assert result['capture_complete'] is True and result['errors'] == []
    assert [section['name'] for section in result['sections']] == ['Induk', 'L1D']
    induk = result['sections'][0]
    assert induk['fields'] == [
        {'label': 'Nomor literal', 'field': 'identifier', 'value': '0000123'},
        {'label': 'Nilai literal', 'field': 'amount', 'value': '1.234,56'},
    ]
    assert induk['tables'][0]['rows'] == [['0007', '1.234,56'], ['0007', '1.234,56']]
    assert page.locator('#l1d').is_visible() and not page.locator('#induk').is_visible()
    assert len(result['attachments']) == 1
    attachment = result['attachments'][0]
    assert attachment['label'] == LABEL and attachment['status'] == 'COMPLETE'
    relative = PurePosixPath(attachment['relative_path'])
    assert not relative.is_absolute() and '..' not in relative.parts and '\\' not in str(relative)
    assert relative.suffix == '.pdf'
    path = tmp_path.joinpath(*relative.parts)
    assert path.is_file() and not path.is_symlink() and path.read_bytes() == PDF
    assert attachment['bytes'] == len(PDF) and attachment['hash'] == hashlib.sha256(PDF).hexdigest()
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


@pytest.mark.parametrize('control', [
    '',
    '<button onclick="fetch(\'/generate-statement\', {method:\'POST\'})">Laporan Keuangan</button>',
])
def test_unsupported_or_absent_financial_control_keeps_structured_capture_partial(routed, tmp_path, control):
    page, requests = routed(control)
    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
    assert result['capture_complete'] is False and result['errors']
    assert result['sections'][0]['fields'][0]['value'] == '0000123'
    assert result['attachments'] and all(item['status'] == 'PARTIAL' for item in result['attachments'])
    assert all(not item.get('relative_path') for item in result['attachments'])
    assert not list(tmp_path.rglob('*.pdf'))
    assert requests == [('GET', DETAIL)]


def test_stop_during_financial_get_propagates_instead_of_becoming_partial(routed, tmp_path):
    page, requests = routed()

    def stop_after_financial_request():
        if ('GET', PDF_URL) in requests:
            raise driver.CaptureCancelled('SYNTHETIC STOP DURING FINANCIAL GET')

    with pytest.raises(driver.CaptureCancelled):
        driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path,
                              check_cancel=stop_after_financial_request)
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]
    assert not list(tmp_path.rglob('*.pdf'))


def test_periodic_return_never_downloads_even_an_observed_financial_href(routed, tmp_path):
    page, requests = routed()
    record = deepcopy(RECORD)
    record['meta']['Jenis Pajak'] = 'PPh Pasal 21/26'
    result = driver.capture_detail(page, record=record, folder=tmp_path)
    assert result['capture_complete'] is True
    assert result['attachments'] == []
    assert not list(tmp_path.rglob('*.pdf'))
    assert requests == [('GET', DETAIL)]


def test_legacy_capture_without_record_context_does_not_download_financial_files(routed, tmp_path):
    page, requests = routed()
    result = driver.capture_detail(page)
    assert result['capture_complete'] is True
    assert result.get('attachments', []) == []
    assert not list(tmp_path.rglob('*.pdf'))
    assert requests == [('GET', DETAIL)]


def test_verified_checkpoint_restores_record_bound_financial_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, 'ORIGIN', ORIGIN)
    path = tmp_path / 'attachments' / 'synthetic' / 'statement.pdf'
    path.parent.mkdir(parents=True)
    path.write_bytes(PDF)
    saved = deepcopy(RECORD)
    saved.update(detail_url=DETAIL, capture_complete=True,
                 sections=[{'name': 'Induk', 'fields': [], 'tables': [], 'text': 'SYNTHETIC ONLY'}],
                 attachments=[{'label': LABEL, 'relative_path': path.relative_to(tmp_path).as_posix(),
                               'status': 'COMPLETE', 'bytes': len(PDF),
                               'hash': hashlib.sha256(PDF).hexdigest()}])
    checkpoint = tmp_path / 'record.json'
    checkpoint.write_text(json.dumps(saved), encoding='utf-8')
    restored = driver.read_detail_checkpoint(checkpoint, deepcopy(RECORD), RECORD['scope'])
    assert restored['attachments'] == saved['attachments']
    assert restored['scope'] == RECORD['scope']
    assert restored['detail_url'] == DETAIL


def test_partial_capture_retry_reuses_identical_pdf_without_replacing_saved_bytes(routed, tmp_path, monkeypatch):
    page, requests = routed()
    capture_table = driver.capture_table
    attempts = []

    def transient_table_error(*args, **kwargs):
        attempts.append(True)
        if len(attempts) == 1:
            raise RuntimeError('SYNTHETIC TRANSIENT TABLE FAILURE')
        return capture_table(*args, **kwargs)

    monkeypatch.setattr(driver, 'capture_table', transient_table_error)
    first = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
    assert not first['capture_complete'] and first['errors']
    item = first['attachments'][0]
    assert item['status'] == 'COMPLETE'
    path = tmp_path / item['relative_path']
    before = path.stat()
    assert path.read_bytes() == PDF

    second = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)

    assert len(attempts) == 2, 'The failed table must actually be retried'
    assert requests == [('GET', DETAIL), ('GET', PDF_URL), ('GET', PDF_URL)]
    assert second['capture_complete'] and not second['errors']
    assert second['attachments'] == first['attachments']
    after = path.stat()
    assert (after.st_dev, after.st_ino, after.st_mtime_ns) == (before.st_dev, before.st_ino, before.st_mtime_ns)
    assert path.read_bytes() == PDF
