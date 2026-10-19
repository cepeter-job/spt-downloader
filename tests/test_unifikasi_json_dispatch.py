"""Native Unifikasi dispatch must use the real Masa adapter and no DOM values."""
from types import SimpleNamespace
import pytest
import coretax_browser as browser
import coretax_masa_observer as observer
import coretax_pph21_observer as pph21_observer
from coretax_json import JsonSafetyError
from masa_json_fixtures import FOREIGN, SCOPE
from masa_projection_fixture import native_case
from test_ppn_json_dispatch import Capture


@pytest.mark.parametrize('populated', [False, True])
def test_unifikasi_native_dispatch(monkeypatch, populated):
    case = native_case('PPh Unifikasi', populated=populated)
    capture = Capture(case['packets'])
    def observe(*args, **kwargs):
        assert not capture.drained
        return case['forms']
    def forbidden(*args, **kwargs):
        raise AssertionError('Native Unifikasi must not use DOM values or another tax observer')
    monkeypatch.setattr(observer, 'observe_masa_forms', observe)
    monkeypatch.setattr(pph21_observer, 'observe_pph21_forms', forbidden)
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    monkeypatch.setattr(browser, 'capture_financial_detail', forbidden)
    page = SimpleNamespace(url=case['packets'][0]['context']['frame_url'])
    result = browser._hybrid_detail(page, case['record'], SCOPE, None, capture, 10, None)
    assert result['capture_complete']
    audit = result['detail_source']
    assert audit['used'] == 'json'
    assert audit['reason'] == 'verified_native_unifikasi_source'
    assert audit['coverage']['complete']
    assert len(audit['coverage']['grids']) == 5
    assert [s['name'] for s in result['sections']] == ['INDUK', 'DAFTAR-I', 'DAFTAR-II', 'LAMPIRAN-I']
    assert audit['json']['bindings']
    assert not result['attachments']


@pytest.mark.parametrize('status', [401, 403])
def test_unifikasi_auth_rejection_never_falls_back(monkeypatch, status):
    case = native_case('PPh Unifikasi')
    case['packets'][0]['context']['status'] = status
    monkeypatch.setattr(observer, 'observe_masa_forms', lambda *a, **k: None)
    def forbidden(*a, **k):
        raise AssertionError('Authorization rejection must stop before DOM fallback')
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    with pytest.raises(JsonSafetyError):
        browser._hybrid_detail(None, case['record'], SCOPE, None, Capture(case['packets']), 10, None)


def test_unifikasi_observation_request_conflict_stops_before_drain(monkeypatch):
    case = native_case('PPh Unifikasi')
    capture = Capture(case['packets'])
    def observe(*a, **k):
        capture.packets[0]['context']['request_json']['RecordId'] = FOREIGN
        return None
    def forbidden(*a, **k):
        raise AssertionError('Contradictory request must stop before fallback')
    monkeypatch.setattr(observer, 'observe_masa_forms', observe)
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    with pytest.raises(JsonSafetyError):
        browser._hybrid_detail(None, case['record'], SCOPE, None, capture, 10, None)
    assert not capture.drained
