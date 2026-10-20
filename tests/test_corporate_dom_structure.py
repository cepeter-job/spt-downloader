"""Synthetic browser regression tests for corporate DOM table structural identity
metadata (source_structure) required by the approved Badan renderer.

Contract under test (no production code is implemented here): every table
captured inside an actual selected PPh Badan record gains
    source_structure = {
        'form': 'L1-D' | 'L9',
        'component': <inspected owner custom tag>,
        'groups': [<outer accordion caption>, <inner panel caption>, ...]
    }
only when exact ancestor-role proof exists; unknown components and forms
without an owned corporate form emit no identity ({}). Existing metadata
fields are kept for compatibility and control values are never captured into
metadata. Pages are intercepted synthetic fixtures only: no live browser
access and no local test execution (CI runs Playwright against msedge).
"""

from copy import deepcopy
from hashlib import sha256
from pathlib import PurePosixPath

import pytest
from playwright.sync_api import sync_playwright

import coretax_browser as driver

ORIGIN = 'https://coretax.synthetic.invalid'

RECORD = {
    'key': 'SYNTHETIC_CORPORATE_RETURN',
    'record_id': 'SYNTHETIC_CORPORATE_RETURN',
    'list_url': ORIGIN + '/returnsheets/id-ID/corporatereturnsheets/SYNTHETIC_TAXPAYER',
    'scope': ['0000000000000001', 2025, 'period'],
    'source_status': 'SYNTHETIC FIXTURE ONLY',
    'meta': {'Jenis Pajak': 'PPh Badan', 'Masa Pajak': '2025', 'Model SPT': 'Normal'},
}
DETAIL = RECORD['list_url'] + '/' + RECORD['record_id']
PDF_URL = ORIGIN + '/synthetic-existing/laporan-keuangan.pdf'
PDF = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'
LABEL = 'Laporan Keuangan yang Telah Diaudit*'
CONTROL = f'<a href="{PDF_URL}"><span>{LABEL}</span></a>'

L1D = [
    {'form': 'L1-D', 'component': 'rsh-citr-l1d-grid1',
     'groups': ['A. LAPORAN LABA RUGI']},
    {'form': 'L1-D', 'component': 'rsh-citr-l1d-grid2',
     'groups': ['B. LAPORAN POSISI KEUANGAN']},
    {'form': 'L1-D', 'component': 'rsh-citr-l1d-grid3',
     'groups': ['B. LAPORAN POSISI KEUANGAN']},
]

L9_SPECS = [
    ('rshshr-citr-l9-form-grid1', 'HARTA BERWUJUD', ['KELOMPOK 1', 'KELOMPOK 2', 'KELOMPOK 3', 'KELOMPOK 4', 'LAINNYA']),
    ('rshshr-citr-l9-form-grid2', 'BANGUNAN', ['PERMANEN', 'TIDAK PERMANEN']),
    ('rshshr-citr-l9-form-grid3', 'HARTA TIDAK BERWUJUD', ['KELOMPOK 1', 'KELOMPOK 2', 'KELOMPOK 3', 'KELOMPOK 4', 'LAINNYA']),
]
L9 = [
    {'form': 'L9', 'component': component,
     'groups': [accordion, panel]}
    for component, accordion, panels in L9_SPECS
    for panel in panels
]
assert len(L9) == 12

L9_HEADERS = ['KODE HARTA', 'KELOMPOK/JENIS HARTA']
L9_ROW = [['0101', 'Tanah']]


def table_html(headers, rows, wrap=None):
    head = '<thead><tr>' + ''.join(f'<th>{h}</th>' for h in headers) + '</tr></thead>'
    body = '<tbody>' + ''.join('<tr>' + ''.join(f'<td>{v}</td>' for v in row) + '</tr>' for row in rows) + '</tbody>'
    inner = f'<table>{head}{body}</table>'
    if wrap:
        inner = f'<{wrap}>{inner}</{wrap}>'
    return f'<p-table><div class="p-datatable">{inner}</div></p-table>'


def grid_block(component, caption, inner):
    owned = f'<{component}>{inner}</{component}>' if component else inner
    return (f'<p-accordiontab><div class="p-accordiontab">'
            f'<div class="p-accordion-header"><a>{caption}</a></div>'
            f'<div class="p-accordion-content">'
            f'<div><div><div><div>{owned}</div></div></div></div>'
            f'</div></div></p-accordiontab>')


def panel_block(component, accordion, panel_caption):
    core = table_html(L9_HEADERS, L9_ROW, wrap='ui-grid')
    owned = f'<{component}>{core}</{component}>'
    nested = '<div><div><div><div><div><div>' + owned + '</div></div></div></div></div></div>'
    panel = (f'<p-panel><div class="p-panel">'
             f'<div class="p-panel-header"><span class="p-panel-title">{panel_caption}</span></div>'
             f'<div class="p-panel-content">{nested}</div></div></p-panel>')
    return grid_block(None, accordion, panel)


def l9_body():
    return ''.join(panel_block(c, a, p) for c, a, panels in L9_SPECS for p in panels)


def l1d_html(l1d_blocks, l9_blocks=(), control=CONTROL):
    return f'''<!doctype html><html><body>
<main class="main-content"><div class="p-tabview">
<ul class="p-tabview-nav">
<li><a role="tab" aria-controls="induk" onclick="show('induk')">Induk</a></li>
<li><a role="tab" aria-controls="l1d" onclick="show('l1d')">L1-D</a></li>
<li><a role="tab" aria-controls="l9" onclick="show('l9')">L9</a></li>
</ul><div class="p-tabview-panels">
<p-tabpanel><div class="p-tabview-panel" id="induk" hidden>
<label for="identifier">Nomor literal</label><input id="identifier" value="0000123">
<label for="amount">Nilai literal</label><input id="amount" value="1.234,56">
<table><thead><tr><th>Kode</th><th>Nilai</th></tr></thead>
<tbody><tr><td>0007</td><td>1.234,56</td></tr></tbody></table>
{control}
</div></p-tabpanel>
<p-tabpanel><div class="p-tabview-panel" id="l1d" hidden>
<rshshr-citr-l1d-form><div><form><div><p-accordion>{''.join(l1d_blocks)}</p-accordion></div></form></div></rshshr-citr-l1d-form>
</div></p-tabpanel>
<p-tabpanel><div class="p-tabview-panel" id="l9" hidden>
<rshshr-citr-l9-form><div><form><div><p-accordion>{''.join(l9_blocks)}</p-accordion></div></form></div></rshshr-citr-l9-form>
</div></p-tabpanel>
</div></div></main>
<script>function show(id){{document.querySelectorAll('.p-tabview-panel').forEach(p=>p.hidden=p.id!==id)}}</script>
</body></html>'''


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

    def create(html):
        context = browser.new_context(service_workers='block')
        contexts.append(context)

        def route(intercept):
            if intercept.request.url == DETAIL:
                intercept.fulfill(body=html, content_type='text/html')
            elif intercept.request.url == PDF_URL:
                intercept.fulfill(body=PDF, content_type='application/pdf')
            else:
                intercept.abort('blockedbyclient')

        context.route('**/*', route)
        page = context.new_page()
        page.goto(DETAIL, wait_until='domcontentloaded')
        return page

    try:
        yield create
    finally:
        for context in contexts:
            context.close()


def test_l1d_corporate_tables_carry_exact_source_structure(routed, tmp_path):
    g1 = grid_block('rsh-citr-l1d-grid1', 'A. LAPORAN LABA RUGI',
                    '<rshshr-citr-financial-statement-grid>' +
                    table_html(['KODE AKUN', 'NAMA AKUN', 'NILAI KOMERSIAL', 'TIDAK TERMASUK OBJEK PAJAK'],
                               [['1111', 'Kas', '100', '0']]) +
                    '</rshshr-citr-financial-statement-grid>')
    g2 = grid_block('rsh-citr-l1d-grid2', 'B. LAPORAN POSISI KEUANGAN',
                    table_html(['KODE AKUN', 'NAMA AKUN', 'NILAI'], [['2222', 'Bank', '300']]))
    g3 = grid_block('rsh-citr-l1d-grid3', 'B. LAPORAN POSISI KEUANGAN',
                    table_html(['KODE AKUN', 'NAMA AKUN', 'NILAI'], [['3333', 'Piutang', '400']]))
    page = routed(l1d_html([g1, g2, g3]))
    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
    assert result['capture_complete'] is True and result['errors'] == []
    assert [section['name'] for section in result['sections']] == ['Induk', 'L1-D', 'L9']
    tables = result['sections'][1]['tables']
    assert len(tables) == 3
    for table, expected in zip(tables, L1D):
        assert table['source_structure'] == expected
    induk_tables = result['sections'][0]['tables']
    assert len(induk_tables) == 1
    assert not induk_tables[0].get('source_structure')
    assert len(result['attachments']) == 1
    attachment = result['attachments'][0]
    assert attachment['label'] == LABEL and attachment['status'] == 'COMPLETE'
    relative = PurePosixPath(attachment['relative_path'])
    assert not relative.is_absolute() and '..' not in relative.parts
    path = tmp_path.joinpath(*relative.parts)
    assert path.is_file() and path.read_bytes() == PDF
    assert attachment['bytes'] == len(PDF) and attachment['hash'] == sha256(PDF).hexdigest()


def test_l9_corporate_tables_carry_exact_source_structure(routed, tmp_path):
    page = routed(l1d_html([], [l9_body()]))
    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
    assert result['capture_complete'] is True and result['errors'] == []
    tables = result['sections'][2]['tables']
    assert len(tables) == 12
    for table, expected in zip(tables, L9):
        assert table['source_structure'] == expected


def test_unknown_component_and_unowned_form_emit_no_identity(routed, tmp_path):
    html = '''<!doctype html><html><body>
<main class="main-content"><div class="p-tabview">
<ul class="p-tabview-nav"><li><a role="tab" aria-controls="lainnya" onclick="show('lainnya')">Lainnya</a></li></ul>
<div class="p-tabview-panels">
<p-tabpanel><div class="p-tabview-panel" id="lainnya" hidden>
<rshshr-citr-main-form><nui-grid><ui-grid-documents>
<table><thead><tr><th>NO.</th><th>FILENAME</th><th>TINDAKAN</th></tr></thead>
<tbody><tr><td>1</td><td>a.pdf</td><td>-</td></tr></tbody></table>
</ui-grid-documents></nui-grid></rshshr-citr-main-form>
</div></p-tabpanel>
</div></div></main>
<script>function show(id){document.querySelectorAll('.p-tabview-panel').forEach(p=>p.hidden=p.id!==id)}</script>
</body></html>'''
    page = routed(html)
    result = driver.capture_detail(page)
    assert result['capture_complete'] is True and result['errors'] == []
    assert not result['sections'][0]['tables'][0].get('source_structure')
    assert result.get('attachments', []) == []


def test_reordered_components_and_duplicate_headers_keep_per_table_identity(routed, tmp_path):
    g3 = grid_block('rsh-citr-l1d-grid3', 'B. LAPORAN POSISI KEUANGAN',
                    table_html(['KODE AKUN', 'NAMA AKUN', 'NILAI'], [['3333', 'Piutang', '400']]))
    g1 = grid_block('rsh-citr-l1d-grid1', 'A. LAPORAN LABA RUGI',
                    '<rshshr-citr-financial-statement-grid>' +
                    table_html(['KODE AKUN', 'NAMA AKUN', 'NILAI', 'NILAI'], [['1111', 'Kas', '100', '200']]) +
                    '</rshshr-citr-financial-statement-grid>')
    g2 = grid_block('rsh-citr-l1d-grid2', 'B. LAPORAN POSISI KEUANGAN',
                    table_html(['KODE AKUN', 'NAMA AKUN', 'NILAI'], [['2222', 'Bank', '300']]))
    page = routed(l1d_html([g3, g1, g2], l9_blocks=()))
    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
    assert result['capture_complete'] is True and result['errors'] == []
    tables = result['sections'][1]['tables']
    assert [table['source_structure'] for table in tables] == [L1D[2], L1D[0], L1D[1]]
    assert tables[1]['headers'] == ['KODE AKUN', 'NAMA AKUN', 'NILAI', 'NILAI']
    assert tables[1]['body_row_count'] == 1
