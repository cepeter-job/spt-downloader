"""Native PPh21 dispatch must use its own observer and real source adapter."""
from types import SimpleNamespace
import pytest
import coretax_browser as browser
import coretax_masa_observer as masa_observer
import coretax_pph21_observer as pph21_observer
from coretax_json import JsonSafetyError
from masa_json_fixtures import SCOPE
from pph21_projection_fixture import case
from test_ppn_json_dispatch import Capture


def test_pph21_dispatch_uses_real_adapter_without_dom_or_ppn_observer(monkeypatch):
    record, packets, forms = case()
    capture = Capture(packets)
    def observe(*args, **kwargs):
        assert not capture.drained
        return forms
    def forbidden(*args, **kwargs):
        raise AssertionError('PPh21 native path must not read DOM values or use another tax observer')
    monkeypatch.setattr(pph21_observer, 'observe_pph21_forms', observe)
    monkeypatch.setattr(masa_observer, 'observe_masa_forms', forbidden)
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    monkeypatch.setattr(browser, 'capture_financial_detail', forbidden)
    result = browser._hybrid_detail(SimpleNamespace(url=packets[0]['context']['frame_url']),
                                   record, SCOPE, None, capture, 10, None)
    assert result['capture_complete']
    assert result['detail_source']['used'] == 'json'
    assert result['detail_source']['reason'] == 'verified_native_pph21_source'
    assert result['detail_source']['coverage']['complete']
    assert [s['name'] for s in result['sections']] == ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III']


@pytest.mark.parametrize('status', [401, 403])
def test_reference_auth_failure_is_fatal_even_when_observation_is_unsupported(monkeypatch, status):
    record, packets, _ = case()
    packets[1]['context']['status'] = status
    capture = Capture(packets)
    monkeypatch.setattr(pph21_observer, 'observe_pph21_forms', lambda *a, **k: None)
    monkeypatch.setattr(masa_observer, 'observe_masa_forms', lambda *a, **k: None)
    def forbidden(*a, **k):
        raise AssertionError('Authorization failure must never fall back to DOM')
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    with pytest.raises(JsonSafetyError):
        browser._hybrid_detail(SimpleNamespace(url=packets[0]['context']['frame_url']),
                               record, SCOPE, None, capture, 10, None)
