"""PPh21 native JSON must reject cross-return traffic before DOM fallback.

Synthetic requests mirror the reviewed 803 public grid constructors, not portal
records. These are safety contracts, not evidence of complete form projection.
"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

import coretax_browser as browser
import coretax_masa_observer as observer
from coretax_json import JsonSafetyError, ORIGIN
from coretax_masa_json import check_masa_request_identities
from masa_json_fixtures import FOREIGN, RECORD, SCOPE, selected

TAX = 'PPh Pasal 21/26'
GRIDS = ('l1a', 'l1b-bpa1', 'l1b-bpa2', 'l2-bpa1', 'l2-bpa2', 'l3-bp21', 'l3-bp26')


def event(grid='l1a', identity=RECORD):
    return {'url': ORIGIN + '/returnsheet/api/loadarticle2126/' + grid + '-grid',
            'method': 'POST', 'status': 200,
            'request_json': {'ReturnSheetRecordId': identity, 'First': 0, 'Rows': 50, 'Filters': []}}


@pytest.mark.parametrize('grid', GRIDS)
@pytest.mark.parametrize('identity', [FOREIGN, ' ' + RECORD, None, True, 1])
def test_pph21_every_grid_rejects_nonliteral_or_foreign_identity(grid, identity):
    with pytest.raises(JsonSafetyError):
        check_masa_request_identities([event(grid, identity)], selected(TAX), SCOPE)


@pytest.mark.parametrize('grid', GRIDS)
def test_matching_pph21_request_is_not_eligibility_and_is_immutable(grid):
    events = [event(grid)]
    before = deepcopy(events)
    assert check_masa_request_identities(events, selected(TAX), SCOPE) is None
    assert events == before


@pytest.mark.parametrize('tax', [TAX, 'PPN', 'PPh Unifikasi'])
def test_pph21_contradiction_is_checked_after_missing_identity_for_every_masa_tax(tax):
    missing = event()
    missing['request_json'] = {}
    with pytest.raises(JsonSafetyError):
        check_masa_request_identities([missing, event('l3-bp26', FOREIGN)], selected(tax), SCOPE)


class Capture:
    def __init__(self, phase):
        self.phase = phase
        self.observed = False
        self.drained = False

    def request_observations(self):
        bad = (self.phase == 'initial' or self.phase == 'observe' and self.observed
               or self.phase == 'drain' and self.drained)
        return [event(identity=FOREIGN if bad else RECORD)]

    def drain(self, **kwargs):
        self.drained = True
        return {'complete': True, 'reasons': []}

    def iter_bodies(self, **kwargs):
        assert self.drained
        return iter(())


@pytest.mark.parametrize('phase', ['initial', 'observe', 'drain'])
def test_dispatch_checks_pph21_identity_before_and_after_observation_and_final_drain(monkeypatch, phase):
    capture = Capture(phase)

    def observe(*args, **kwargs):
        assert not capture.drained
        capture.observed = True
        return None  # Unsupported structure cannot hide an identity failure.

    def forbidden(*args, **kwargs):
        raise AssertionError('Foreign PPh21 traffic must never become DOM fallback')

    monkeypatch.setattr(observer, 'observe_masa_forms', observe)
    monkeypatch.setattr(browser, 'capture_detail', forbidden)
    monkeypatch.setattr(browser, 'capture_financial_detail', forbidden)
    with pytest.raises(JsonSafetyError):
        browser._hybrid_detail(SimpleNamespace(url='unused'), selected(TAX), SCOPE,
                               None, capture, 10, None)


def test_pph21_unsupported_structure_falls_back_without_claiming_json(monkeypatch):
    capture = Capture('never')

    def observe(*args, **kwargs):
        assert not capture.drained
        capture.observed = True
        return None

    monkeypatch.setattr(observer, 'observe_masa_forms', observe)
    monkeypatch.setattr(browser, 'capture_detail', lambda *a, **kw: {
        'capture_complete': True, 'sections': [{'name': 'Induk', 'fields': [], 'tables': []}]})
    result = browser._hybrid_detail(SimpleNamespace(url='unused'), selected(TAX), SCOPE,
                                   None, capture, 10, None)
    assert capture.observed and capture.drained
    assert result['detail_source']['requested'] == 'json-first'
    assert result['detail_source']['used'] == 'dom'
    assert result['detail_source']['reason'] != 'verified_native_pph21_source'
