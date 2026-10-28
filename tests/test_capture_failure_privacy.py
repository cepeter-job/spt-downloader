"""Production capture failures retain safe proof, never arbitrary error text."""
import json

import pytest

import coretax_browser as driver
from test_diagnostics import records as diagnostic_records
from test_financial_capture import browser, routed, DETAIL


@pytest.mark.parametrize(('kind', 'message', 'want_type', 'want_message'), [
    (RuntimeError, 'SYNTHETIC_PRIVATE_FAILURE_BODY', 'RuntimeError', 'capture_failed'),
    (type('SYNTHETIC_PRIVATE_CLASS', (Exception,), {}), 'SYNTHETIC_PRIVATE_FAILURE_BODY',
     'Error', 'capture_failed'),
    (driver.PlaywrightTimeoutError, 'SYNTHETIC_PRIVATE_FAILURE_BODY',
     'TimeoutError', 'capture_timeout'),
])
def test_actual_table_failure_keeps_safe_proof_and_recovers_later_panel(
        routed, tmp_path, monkeypatch, kind, message, want_type, want_message):
    page, requests = routed(control='')

    def failed_table(*args, **kwargs):
        raise kind(message)

    monkeypatch.setattr(driver, 'capture_table', failed_table)
    with driver.diagnostics.session(tmp_path / 'logs', 'worker') as log:
        result = driver.capture_detail(page)
        assert log.flush()

    assert result['capture_complete'] is False
    assert [s['name'] for s in result['sections']] == ['Induk', 'L1D']
    assert result['sections'][0]['tables'] == []
    assert result['sections'][1]['fields']
    assert result['errors'] == [{'object': 'Induk/table 1', 'message': want_message}]
    assert requests == [('GET', DETAIL)]
    partial = [r for r in diagnostic_records(tmp_path / 'logs') if r['event'] == 'capture.partial']
    assert len(partial) == 1
    assert partial[0]['error']['type'] == want_type
    assert any(f['file'] == 'coretax_browser.py' for f in partial[0]['error']['frames'])
    serialized = json.dumps([result['errors'], diagnostic_records(tmp_path / 'logs')])
    assert message not in serialized and 'SYNTHETIC_PRIVATE_CLASS' not in serialized


def test_stop_from_actual_table_capture_is_not_demoted_to_partial(routed, tmp_path, monkeypatch):
    page, requests = routed(control='')

    def cancelled(*args, **kwargs):
        raise driver.CaptureCancelled('SYNTHETIC_STOP')

    monkeypatch.setattr(driver, 'capture_table', cancelled)
    with driver.diagnostics.session(tmp_path / 'logs', 'worker') as log:
        with pytest.raises(driver.CaptureCancelled):
            driver.capture_detail(page)
        assert log.flush()
    assert not any(r['event'] == 'capture.partial' for r in diagnostic_records(tmp_path / 'logs'))
    assert requests == [('GET', DETAIL)]


@pytest.mark.parametrize('body', ['{', 'SYNTHETIC_NON_JSON_BODY'])
def test_real_unreadable_request_body_cannot_establish_grid_custody(routed, body):
    page, _ = routed(control='')
    endpoint = driver.ORIGIN + '/returnsheet/api/returnsheets/list'
    page.route(endpoint, lambda route: route.fulfill(body='{}', content_type='application/json'))
    with page.expect_request(endpoint) as observed:
        page.evaluate('''([url, body]) => fetch(url, {method:'POST',
            headers:{'Content-Type':'application/json'},body}).then(reply=>reply.text())''',
            [endpoint, body])
    observer = driver.ListObserver.__new__(driver.ListObserver)
    observer.page = page
    observer.navigation_source = None
    assert observer._grid_request(observed.value, endpoint) is None
