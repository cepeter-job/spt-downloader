"""Synthetic PPN initial-shell readiness and real DOM-to-XLSX contracts."""
import pytest
from support_isolated_browser import browser, context

import coretax_browser as driver
from support_templates import export_ppn


NAMES = ['INDUK', 'A-1', 'A-2', 'B-1', 'B-2', 'B-3', 'C']
RECORD = {'meta': {'Jenis Pajak': 'PPN'}}
LABEL = 'PPN kurang atau (lebih) bayar (III.A - III.B - III.C - III.D)'
GROUP = 'III. PENGHITUNGAN PPN KURANG BAYAR / LEBIH BAYAR'


@pytest.fixture
def page(context):
    context.route('**/*', lambda route: route.abort())
    return context.new_page()


def markup(names):
    tabs = ''.join(f'<li><a role="tab" aria-controls="panel-{i}" onclick="show({i})">{name}</a></li>'
                   for i, name in enumerate(names))
    panels = ''.join(
        f'<p-tabpanel><div class="p-tabview-panel" id="panel-{i}" {"hidden" if i else ""}>'
        + (f'<h3>{GROUP}</h3><div><label for="amount">{LABEL}</label>'
           '<input id="amount" disabled value="-17,00"></div>' if i == 0 else
           '<table><thead><tr><th>Fixture code</th></tr></thead>'
           '<tbody><tr><td colspan="2">Tidak ada data</td></tr></tbody></table>')
        + '</div></p-tabpanel>' for i, _ in enumerate(names))
    return ('<div class="main-content"><div class="p-tabview"><ul class="p-tabview-nav">'
            + tabs + '</ul><div class="p-tabview-panels">' + panels + '</div></div></div>')


def install(page, names):
    page.set_content(markup(names))
    page.evaluate('''() => {window.show=i=>document.querySelectorAll('.p-tabview-panel').forEach(
        (e,j)=>e.hidden=j!==i);}''')


def test_ppn_induk_only_shell_never_certifies_complete(page, monkeypatch):
    monkeypatch.setattr(driver, 'DETAIL_READY_TIMEOUT', 0.05, raising=False)
    install(page, ['INDUK'])
    result = driver.capture_detail(page, record=RECORD, max_pages=2)
    assert [section['name'] for section in result['sections']] == ['INDUK']
    assert result['capture_complete'] is False
    assert result['errors']


def test_ppn_waits_for_delayed_catalog_before_collecting_default_shell(page, monkeypatch, tmp_path):
    install(page, ['INDUK'])
    full = markup(NAMES)
    # Release the initialized page only when the readiness loop yields to the
    # browser. Existing overlay waits alone must not certify the Induk shell.
    original_wait = page.wait_for_timeout
    released = False

    def wait(milliseconds):
        nonlocal released
        if milliseconds == 100 and not released:
            page.locator('.main-content').evaluate('(e, html)=>e.outerHTML=html', full)
            released = True
        return original_wait(milliseconds)

    monkeypatch.setattr(page, 'wait_for_timeout', wait)
    result = driver.capture_detail(page, record=RECORD, max_pages=2)
    assert released, 'Collector did not wait for a supported complete form catalog'
    assert [section['name'] for section in result['sections']] == NAMES
    assert result['capture_complete'] is True
    assert all(table['body_row_count'] == 0 for section in result['sections'][1:]
               for table in section['tables'])
    book, _, _ = export_ppn(tmp_path, result['sections'])
    try:
        assert book['INDUK']['E45'].value == -17
        assert book['INDUK']['E45'].data_type == 'n'
        assert book.sheetnames == NAMES
    finally:
        book.close()


def test_complete_ppn_catalog_with_verified_nil_grids_is_valid(page):
    install(page, NAMES)
    result = driver.capture_detail(page, record=RECORD, max_pages=2)
    assert result['capture_complete'] is True
    assert len(result['sections']) == len(NAMES)
    assert all(t['source_total'] in (None, 0) if 'source_total' in t else t['body_row_count'] == 0
               for section in result['sections'][1:] for t in section['tables'])


def test_disabled_expected_ppn_tab_is_partial_not_silent_success(page, monkeypatch):
    monkeypatch.setattr(driver, 'DETAIL_READY_TIMEOUT', 0.05, raising=False)
    install(page, NAMES)
    page.locator('a[aria-controls="panel-6"]').evaluate('(e)=>e.setAttribute("aria-disabled","true")')
    result = driver.capture_detail(page, record=RECORD, max_pages=2)
    assert result['capture_complete'] is False
    assert result['errors']


def test_ppn_readiness_poll_propagates_stop(page, monkeypatch):
    install(page, ['INDUK'])
    original_wait = page.wait_for_timeout
    polling = False

    def wait(milliseconds):
        nonlocal polling
        polling = polling or milliseconds == 100
        return original_wait(milliseconds)

    def cancel():
        if polling:
            raise driver.CaptureCancelled()

    monkeypatch.setattr(page, 'wait_for_timeout', wait)
    with pytest.raises(driver.CaptureCancelled):
        driver.capture_detail(page, record=RECORD, check_cancel=cancel)
