"""Dynamic tab binding regressions use isolated synthetic DOM and PDF bytes."""
from copy import deepcopy
import json

import pytest

import coretax_browser as driver
from test_diagnostics import records as diagnostic_records
from test_financial_capture import browser, routed, RECORD, DETAIL, PDF_URL


def rebind_after_first_control_read(page, monkeypatch, outcome='owned'):
    """Change the real DOM after the collector obtains its first panel ID.

    Only the read boundary is wrapped: its real result is returned unchanged.
    The custom event then leaves that first result stale while the tab/view
    survive. There is no timer or dependency on a short scheduling deadline.
    """
    page.evaluate("""outcome => {
        const tab = document.querySelector('a[aria-controls="induk"]');
        const click = tab.onclick;
        tab.onclick = event => {
            window.syntheticIndukClicked = true;
            return click.call(tab, event);
        };
        tab.addEventListener('synthetic-rebind', () => {
            const previous = document.getElementById('induk');
            const replacement = previous.cloneNode(true);
            previous.hidden = true;
            previous.querySelector('input').value = 'SYNTHETIC STALE ONLY';
            replacement.id = 'synthetic-rebound';
            replacement.hidden = outcome === 'hidden';
            replacement.querySelector('input').value = 'SYNTHETIC REBOUND ONLY';
            tab.setAttribute('aria-controls', replacement.id);
            tab.setAttribute('aria-selected', 'true');
            document.querySelector('a[aria-controls="l1d"]').setAttribute('aria-selected', 'false');
            if (outcome === 'foreign' || outcome === 'nested-foreign') {
                const other = document.createElement('div');
                other.className = 'p-tabview';
                const host = outcome === 'foreign' ? document.querySelector('.main-content') : previous.parentElement;
                host.append(other);
                other.append(replacement);
            } else {
                previous.parentElement.append(replacement);
                if (outcome === 'ambiguous') {
                    previous.parentElement.append(replacement.cloneNode(true));
                }
            }
            window.syntheticPanelRebound = true;
        }, {once: true});
    }""", outcome)
    locator_type = type(page.locator('body'))
    original_get_attribute = locator_type.get_attribute
    released = False

    def get_attribute(locator, name, *args, **kwargs):
        nonlocal released
        result = original_get_attribute(locator, name, *args, **kwargs)
        if (not released and name == 'aria-controls' and result == 'induk'
                and page.evaluate('Boolean(window.syntheticIndukClicked)')):
            released = True
            page.locator('a[aria-controls="induk"]').dispatch_event('synthetic-rebind')
        return result

    monkeypatch.setattr(locator_type, 'get_attribute', get_attribute)
    # Two seconds bound a genuine negative result, without asserting elapsed
    # time or requiring a fixture update to land inside a micro-deadline.
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)


def test_induk_follows_rebound_owned_panel_before_financial_get(routed, tmp_path, monkeypatch):
    page, requests = routed()
    rebind_after_first_control_read(page, monkeypatch)

    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)

    assert page.evaluate('Boolean(window.syntheticPanelRebound)')
    assert result['capture_complete'] is True and result['errors'] == []
    assert [section['name'] for section in result['sections']] == ['Induk', 'L1D']
    assert result['sections'][0]['fields'][0] == {
        'label': 'Nomor literal', 'field': 'identifier', 'value': 'SYNTHETIC REBOUND ONLY',
    }
    assert 'SYNTHETIC STALE ONLY' not in json.dumps(result['sections'])
    assert len(result['attachments']) == 1
    assert result['attachments'][0]['status'] == 'COMPLETE'
    assert requests == [('GET', DETAIL), ('GET', PDF_URL)]


@pytest.mark.parametrize('outcome', ['hidden', 'foreign', 'nested-foreign', 'ambiguous'])
def test_rebound_invalid_panel_never_uses_stale_or_foreign_form(
        routed, tmp_path, monkeypatch, outcome):
    page, requests = routed()
    rebind_after_first_control_read(page, monkeypatch, outcome)

    result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)

    assert page.evaluate('Boolean(window.syntheticPanelRebound)')
    assert result['capture_complete'] is False
    assert [section['name'] for section in result['sections']] == ['L1D']
    assert len(result['attachments']) == 1
    assert result['attachments'][0]['status'] == 'PARTIAL'
    assert result['attachments'][0]['relative_path'] is None
    assert requests == [('GET', DETAIL)]
    assert not list(tmp_path.rglob('*.pdf'))


def test_stop_after_panel_rebinding_prevents_capture_and_financial_get(routed, tmp_path, monkeypatch):
    page, requests = routed()
    rebind_after_first_control_read(page, monkeypatch)

    def stop_after_rebinding():
        if page.evaluate('Boolean(window.syntheticPanelRebound)'):
            raise driver.CaptureCancelled('SYNTHETIC STOP AFTER REBINDING')

    with driver.diagnostics.session(tmp_path, 'worker') as log:
        with pytest.raises(driver.CaptureCancelled):
            driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path,
                                  check_cancel=stop_after_rebinding)
        assert log.flush()

    assert page.evaluate('Boolean(window.syntheticPanelRebound)')
    assert requests == [('GET', DETAIL)]
    assert not list(tmp_path.rglob('*.pdf'))
    assert not any(row['event'] == 'capture.panel_timeout' for row in diagnostic_records(tmp_path))


def test_panel_probe_failure_retains_safe_classification_without_exception_text(
        routed, tmp_path, monkeypatch):
    page, requests = routed()
    page.locator('a[aria-controls="induk"]').evaluate('(tab) => { tab.onclick = () => {}; }')
    monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
    locator_type = type(page.locator('body'))
    original_evaluate = locator_type.evaluate

    def fail_probe(locator, expression, arg=None, **kwargs):
        if expression == driver.PANEL_TIMEOUT_JS:
            raise RuntimeError('SYNTHETIC PRIVATE PROBE MESSAGE 0000123')
        return original_evaluate(locator, expression, arg, **kwargs)

    monkeypatch.setattr(locator_type, 'evaluate', fail_probe)
    with driver.diagnostics.session(tmp_path, 'worker') as log:
        result = driver.capture_detail(page, record=deepcopy(RECORD), folder=tmp_path)
        assert log.flush()

    assert result['capture_complete'] is False
    assert [section['name'] for section in result['sections']] == ['L1D']
    assert result['errors'][0]['message'].startswith('Locator.wait_for: Timeout')
    assert requests == [('GET', DETAIL)]
    rows = diagnostic_records(tmp_path)
    events = [row for row in rows if row['event'] == 'capture.panel_timeout']
    assert len(events) == 1
    assert events[0]['panel_state'] == 'unavailable'
    assert events[0].get('probe_failure') == 'evaluation_error'
    assert events[0].get('error', {}).get('type') == 'RuntimeError'
    assert 'SYNTHETIC PRIVATE PROBE MESSAGE' not in json.dumps(rows)
