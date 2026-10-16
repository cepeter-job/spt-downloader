"""Native PPN dispatch reaches JSON business DTOs without DOM extraction."""
from types import SimpleNamespace

import coretax_browser as browser
import coretax_masa_observer as observer
from masa_projection_fixture import native_case
from masa_json_fixtures import SCOPE


class Capture:
    def __init__(self, packets):
        self.packets = packets
        self.drained = False

    def request_observations(self):
        return [item['context'] for item in self.packets]

    def drain(self, **kwargs):
        self.drained = True
        return {'complete': True, 'reasons': []}

    def iter_bodies(self, **kwargs):
        assert self.drained
        return iter(self.packets)


def test_ppn_dispatch_uses_real_native_adapter_and_never_reads_dom_values(monkeypatch):
    case = native_case('PPN')
    capture = Capture(case['packets'])
    def observe(*args, **kwargs):
        assert not capture.drained, 'Early drain discards PPN response traffic'
        return case['forms']
    def forbidden(*args, **kwargs):
        raise AssertionError('Native PPN must not fall back to DOM or corporate financial capture')
    monkeypatch.setattr(observer, 'observe_masa_forms', observe)
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    monkeypatch.setattr(browser, 'capture_financial_detail', forbidden)
    page = SimpleNamespace(url=case['packets'][0]['context']['frame_url'])
    result = browser._hybrid_detail(page, case['record'], SCOPE, None, capture, 10, None)
    assert result['capture_complete'] is True
    assert result['detail_source']['used'] == 'json'
    assert result['detail_source']['reason'] == 'verified_native_ppn_source'
    assert result['detail_source']['coverage']['complete'] is True
    assert [s['name'] for s in result['sections']] == ['INDUK','A-1','A-2','B-1','B-2','B-3','C']
