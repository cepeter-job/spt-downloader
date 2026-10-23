"""Slow locator-resolution faults around a real synthetic corporate POST flow.

The transport boundary rejects reads whose allowance cannot cover a 250 ms
renderer round trip. No sleep or machine-speed assertion drives the fault; DOM,
panel ownership, PDF capture/abort/replay and saved bytes remain real Edge work.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

import coretax_browser as driver
from support_financial_browser import browser as browser
from support_financial_browser import RECORD, downloaded
from support_financial_post import ENDPOINT
from support_financial_post import post_routed as post_routed
from test_diagnostics import records as diagnostic_records
from test_financial_actual_route import DETAIL, record


def corporate_tabs(page, *, hidden=False):
    page.evaluate('''hidden => {
        const root = document.querySelector('.main-content');
        const form = root.querySelector('rshshr-citr-main-form');
        root.querySelector('h1').remove();
        const view = document.createElement('div');
        view.className = 'p-tabview';
        view.innerHTML = '<div class="p-tabview-nav-container"><div class="p-tabview-nav-content">' +
            '<ul class="p-tabview-nav">' +
            '<li><a role="tab" aria-controls="synthetic-induk">Induk</a></li>' +
            '<li><a role="tab" aria-controls="synthetic-appendix">L1D</a></li></ul></div></div>' +
            '<div class="p-tabview-panels">' +
            '<p-tabpanel><div class="p-tabview-panel" id="synthetic-induk" hidden></div></p-tabpanel>' +
            '<p-tabpanel><div class="p-tabview-panel" id="synthetic-appendix">' +
            '<label for="synthetic-field">Synthetic appendix</label>' +
            '<input id="synthetic-field" value="0000123"></div></p-tabpanel></div>';
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
    subsequent = []
    locator_type = type(page.locator('body'))
    for method in ('get_attribute', 'wait_for', 'element_handle', 'evaluate'):
        original = getattr(locator_type, method)

        def read(locator, *args, _original=original, _method=method, **kwargs):
            if reads and kwargs.get('timeout') is not None:
                subsequent.append(_method)
            return _original(locator, *args, **kwargs)

        monkeypatch.setattr(locator_type, method, read)

    def cancel():
        if reads:
            raise driver.CaptureCancelled('SYNTHETIC STOP AFTER PANEL READ')

    with pytest.raises(driver.CaptureCancelled):
        driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path, check_cancel=cancel)

    assert page.evaluate('window.syntheticClicks') == 0 and wire == []
    assert subsequent == [], 'Stop must be checked before another readiness read'
    assert not list(tmp_path.rglob('*.pdf'))


@pytest.mark.parametrize('read_seconds', [0.4, 0.18], ids=['early-read', 'final-read'])
def test_one_panel_deadline_is_shared_by_successive_reads(post_routed, monkeypatch, read_seconds):
    page, wire = post_routed(detail_url=DETAIL)
    corporate_tabs(page)
    tab = page.get_by_role('tab', name='Induk', exact=True)
    tab.click()
    clock = [0.0]
    allowances = []
    locator_type = type(tab)
    for method in ('inner_text', 'get_attribute', 'wait_for', 'element_handle', 'evaluate'):
        original = getattr(locator_type, method)

        def read(locator, *args, _original=original, **kwargs):
            allowance = kwargs.get('timeout')
            if allowance is not None:
                allowances.append((clock[0], allowance))
            result = _original(locator, *args, **kwargs)
            clock[0] += read_seconds
            return result

        monkeypatch.setattr(locator_type, method, read)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 1)
    # Probe is a separate after-exhaustion diagnostic budget.
    monkeypatch.setattr(driver, '_record_panel_timeout', lambda *args: None)

    with pytest.raises(driver.PlaywrightTimeoutError):
        driver._wait_tab_panel(page.locator('.p-tabview'), tab, 'Induk', None)

    assert allowances and all(0 < timeout <= max(1, (1 - at) * 1000)
                              for at, timeout in allowances)
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []


def test_slow_timeout_probe_retains_structural_evidence_without_pdf(post_routed, tmp_path, monkeypatch):
    page, wire = post_routed(detail_url=DETAIL)
    corporate_tabs(page, hidden=True)
    # The hidden panel must exhaust its budget, while the later healthy
    # appendix should not depend on six reads finishing inside 50 ms.
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    locator_type = type(page.locator('body'))
    original = locator_type.evaluate
    attempts = []

    def evaluate(locator, expression, *args, **kwargs):
        if expression == driver.PANEL_TIMEOUT_JS:
            attempts.append(kwargs.get('timeout'))
            if kwargs.get('timeout', 0) < 250:
                raise driver.PlaywrightTimeoutError('SYNTHETIC slow probe')
        return original(locator, expression, *args, **kwargs)

    monkeypatch.setattr(locator_type, 'evaluate', evaluate)
    with driver.diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = driver.capture_detail(page, record=record(), folder=tmp_path)
        assert log.flush()

    assert attempts == [1000], 'Probe gets one separate bounded diagnostic read'
    events = [row for row in diagnostic_records(tmp_path / 'diagnostics')
              if row['event'] == 'capture.panel_timeout']
    assert len(events) == 1 and events[0]['panel_state'] == 'hidden'
    assert 'probe_failure' not in events[0]
    assert result['capture_complete'] is False
    assert [section['name'] for section in result['sections']] == ['L1D']
    assert page.evaluate('window.syntheticClicks') == 0 and wire == []
    assert result['attachments'][0]['status'] == 'PARTIAL'
    assert not list(tmp_path.rglob('*.pdf'))
