"""Slow locator-resolution faults around a real synthetic corporate POST flow.

The transport boundary rejects reads whose allowance cannot cover a 250 ms
renderer round trip. No sleep or machine-speed assertion drives the fault; DOM,
panel ownership, PDF capture/abort/replay and saved bytes remain real Edge work.
"""
from copy import deepcopy

import pytest

import coretax_browser as driver
from support_financial_browser import browser as browser
from support_financial_browser import RECORD, downloaded
from support_financial_post import ENDPOINT
from support_financial_post import post_routed as post_routed
from test_financial_actual_route import DETAIL, record


def corporate_tabs(page, *, hidden=False):
    page.evaluate('''hidden => {
        const root = document.querySelector('.main-content');
        const form = root.querySelector('rshshr-citr-main-form');
        root.querySelector('h1').remove();
        const view = document.createElement('div');
        view.className = 'p-tabview';
        view.innerHTML = '<ul class="p-tabview-nav">' +
            '<li><a role="tab" aria-controls="synthetic-induk">Induk</a></li>' +
            '<li><a role="tab" aria-controls="synthetic-appendix">L1D</a></li></ul>' +
            '<div class="p-tabview-panels">' +
            '<div class="p-tabview-panel" id="synthetic-induk" hidden></div>' +
            '<div class="p-tabview-panel" id="synthetic-appendix">' +
            '<label for="synthetic-field">Synthetic appendix</label>' +
            '<input id="synthetic-field" value="0000123"></div></div>';
        root.append(view);
        view.querySelector('#synthetic-induk').append(form);
        for (const tab of view.querySelectorAll('a[role=tab]')) {
            tab.onclick = () => {
                window.syntheticIndukSelected = tab.textContent === 'Induk';
                for (const panel of view.querySelectorAll('.p-tabview-panel')) {
                    panel.hidden = panel.id !== tab.getAttribute('aria-controls') ||
                        (hidden && panel.id === 'synthetic-induk');
                }
            };
        }
    }''', hidden)


def slow_resolution(page, monkeypatch, method):
    """Inject latency rejection only at the panel-read transport boundary."""
    locator_type = type(page.locator('body'))
    original = getattr(locator_type, method)
    reads = []

    def read(locator, *args, **kwargs):
        allowance = kwargs.get('timeout')
        if (allowance is not None
                and page.evaluate('Boolean(window.syntheticIndukSelected)')):
            reads.append(allowance)
            if allowance < 250:
                raise driver.PlaywrightTimeoutError('SYNTHETIC slow renderer read')
        return original(locator, *args, **kwargs)

    monkeypatch.setattr(locator_type, method, read)
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    return reads


@pytest.mark.parametrize('method', ['inner_text', 'wait_for'])
def test_slow_induk_resolution_reaches_one_guarded_post_and_verified_pdf(
        post_routed, tmp_path, monkeypatch, method):
    page, wire = post_routed(detail_url=DETAIL)
    corporate_tabs(page)
    reads = slow_resolution(page, monkeypatch, method)

    result = driver.capture_detail(page, record=record(), folder=tmp_path)

    assert reads, 'The fault must exercise the Induk readiness read'
    assert result['capture_complete'] is True, result['errors']
    assert [section['name'] for section in result['sections']] == ['Induk', 'L1D']
    downloaded(result['attachments'], tmp_path)
    assert page.evaluate('window.syntheticClicks') == 1
    assert len(wire) == 1 and wire[0]['url'] == ENDPOINT
    assert wire[0]['headers']['request_from'] == DETAIL
    assert page.locator('#synthetic-appendix').is_visible()


def test_slow_reads_do_not_authorize_hidden_induk_or_a_pdf_request(post_routed, tmp_path, monkeypatch):
    page, wire = post_routed(detail_url=DETAIL)
    corporate_tabs(page, hidden=True)
    reads = slow_resolution(page, monkeypatch, 'inner_text')

    result = driver.capture_detail(page, record=record(), folder=tmp_path)

    assert reads and result['capture_complete'] is False
    assert [section['name'] for section in result['sections']] == ['L1D']
    assert result['attachments'][0]['status'] == 'PARTIAL'
    assert result['attachments'][0]['relative_path'] is None
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []
    assert not list(tmp_path.rglob('*.pdf'))


def test_stop_after_slow_panel_read_prevents_capture_and_post(post_routed, tmp_path, monkeypatch):
    page, wire = post_routed(detail_url=DETAIL)
    corporate_tabs(page)
    reads = slow_resolution(page, monkeypatch, 'inner_text')

    def cancel():
        if reads:
            raise driver.CaptureCancelled('SYNTHETIC STOP AFTER PANEL READ')

    with pytest.raises(driver.CaptureCancelled):
        driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path, check_cancel=cancel)

    assert page.evaluate('window.syntheticClicks') == 0 and wire == []
    assert not list(tmp_path.rglob('*.pdf'))
