"""L9 details source/cancellation/structure guards, without live portal access."""
from copy import deepcopy

import pytest

import coretax_browser as driver
from conftest import pin_override
import coretax_corporate as observer
import coretax_corporate_projection as projection
import coretax_json as adapter
import support_json_corpus as corpus
from test_corporate_l9_details_consumer import (adapt, bindings, packets, clock, lifetime,
    shared_catalog_contract as shared_catalog_contract)
from test_corporate_l9_projection import ROUTE


class Page:
    url = ROUTE
    def __init__(self, defect=None):
        self.calls, self.defect = [], defect
    def evaluate(self, script, arg=None, **kwargs):
        self.calls.append((script, arg))
        if 'AbortController' in script:
            return None
        if arg in (projection.MAIN_SOURCE, projection.VENDOR_SOURCE):
            return 'a' * 64 if self.defect == arg else projection.L9_DETAIL_BUILD_DIGESTS[arg]
        if 'urls.every' in script:
            return self.defect != 'providers'
        assert 'navigator.language' in script
        return {'locale': 'id-ID', 'timezone': 'UTC' if self.defect == 'environment' else 'Asia/Jakarta'}


class Capture:
    def __init__(self, urls, defect=None):
        self.events = [{'url': url, 'method': 'GET', 'request_json': None, 'sequence': index + 14}
                       for index, url in enumerate(urls.values())]
        self.defect = defect
    def request_observations(self):
        return self.events[:-1] if self.defect == 'missing-reference' else self.events
    def observe_component_lifetime(self, **kwargs):
        return None if self.defect == 'lifetime' else lifetime()


@pytest.mark.parametrize('defect', [None, 'providers', 'environment', 'lifetime', 'missing-reference',
    projection.MAIN_SOURCE, projection.VENDOR_SOURCE, 'malformed-pin', 'no-pin', 'no-shared-producer', 'tables'])
def test_observer_only_offers_details_with_positive_pins_sources_and_dependencies(
        shared_catalog_contract, monkeypatch, defect):
    urls = shared_catalog_contract
    page = Page(defect)
    tables = bindings(urls)[1]['projection']['tables']
    monkeypatch.setattr(observer, '_l9_tables', lambda *args: None if defect == 'tables' else tables)
    if defect == 'malformed-pin':
        monkeypatch.setattr(projection, 'L9_DETAIL_BUILD_DIGESTS', {**projection.L9_DETAIL_BUILD_DIGESTS,
            projection.VENDOR_SOURCE: None})
    elif defect == 'no-pin':
        pin_override(monkeypatch, {})
    elif defect == 'no-shared-producer':
        monkeypatch.delitem(adapter.CORPORATE_REFERENCE_REQUESTS, urls['TANGIBLE_ASSET'])
    proof = observer._observe_l9(page, object(), Capture(urls, defect),
        projection.BUILD_DIGESTS[projection.CIT_SOURCE], None)
    assert (proof is not None) is (defect is None)
    if defect is None:
        assert proof['kind'] == 'corporate-l9-details-v1' and len(proof['tables']) == 12
    if defect in ('no-shared-producer', 'malformed-pin', 'no-pin', 'lifetime'):
        assert page.calls == []
    elif defect == 'missing-reference':
        # The bounded re-fetch is an approved read-only catalog acquisition; it
        # makes one cache-bust call even though the reference stays absent here
        # (the stub capture does not record the re-fetch response), so the L9
        # still refuses.
        assert sum(1 for call in page.calls if 'AbortController' in call[0]) <= 1


def test_stop_precedes_any_details_provider_rpc(shared_catalog_contract, monkeypatch):
    page = Page()
    monkeypatch.setattr(observer, '_l9_tables', lambda *a: [])
    def stop():
        raise driver.CaptureCancelled()
    with pytest.raises(driver.CaptureCancelled):
        observer._observe_l9(page, object(), Capture(shared_catalog_contract),
            projection.BUILD_DIGESTS[projection.CIT_SOURCE], stop)
    assert page.calls == []


class Count:
    def __init__(self, count):
        self.value = count
    def count(self):
        return self.value


class Table:
    def __init__(self, index, defect):
        self.index, self.defect = index, defect
    def evaluate(self, script, arg=None):
        if 'ui.contains(owner)' in script:
            return self.defect != 'chain'
        if arg == 'L9':
            return None if self.defect == 'structure' else projection.l9_grid_structure(self.index)
        assert 'footer_spans' in script
        return {'headers': [] if self.defect == 'headers' else list(projection.L9_GRID_HEADERS),
            'footer_spans': [] if self.defect == 'spans' else deepcopy(projection.L9_GRID_SPANS)}


class Grid:
    def __init__(self, index, defect):
        self.index, self.defect = index, defect
    def is_visible(self):
        return self.defect != 'hidden'
    def locator(self, selector):
        if selector == 'table':
            table = Table(self.index, self.defect)
            table.count = lambda: 2 if self.defect == 'tables' else 1
            return table
        return Count(2 if self.defect == selector else 1)


class Grids(Count):
    def __init__(self, first, count, defect):
        super().__init__(count - 1 if defect == 'grid-count' else count)
        self.first, self.defect = first, defect
    def nth(self, index):
        return Grid(self.first + index, self.defect)


class Form:
    def __init__(self, defect):
        self.defect = defect
    def locator(self, selector):
        if selector == 'table':
            return Count(11 if self.defect == 'form-count' else 12)
        index = ('rshshr-citr-l9-form-grid1', 'rshshr-citr-l9-form-grid2',
                 'rshshr-citr-l9-form-grid3').index(selector)
        return Grids((0, 5, 7)[index], (5, 2, 5)[index], self.defect)


@pytest.mark.parametrize('defect', [None, 'form-count', 'grid-count', 'hidden', 'ui-grid', 'p-table',
    'tables', 'chain', 'structure', 'headers', 'spans'])
def test_all_twelve_structure_guards_are_exercised_without_business_values(defect):
    tables = observer._l9_tables(Form(defect), None)
    assert (tables is not None) is (defect is None)
    if tables is not None:
        assert len(tables) == 12


@pytest.mark.parametrize('defect', ['attempt', 'clock', 'locale', 'changed-grid'])
def test_full_details_original_safety_contradictions_stay_fatal(shared_catalog_contract, defect):
    urls = shared_catalog_contract
    raw = packets(urls)
    if defect == 'attempt':
        raw[-1]['context']['attempt'] = 'b' * 32
    elif defect == 'clock':
        raw[-1]['context']['clock_interval'] = {**clock(), 'end_ms': clock()['end_ms'] + 1}
    else:
        index = -1 if defect == 'locale' else 1
        payload = deepcopy(raw[index]['payload'])
        if defect == 'locale':
            payload['Payload'][0]['language'] = 'en-US'
        else:
            payload['Payload']['Data'][0]['FiscalYearValue'] = corpus.Number('99')
        changed = corpus.packet(payload, 19, endpoint=raw[index]['context']['url'],
            request=raw[index]['context']['request_json'])
        changed['context'].update(frame_url=ROUTE, component_lifetime=lifetime(), clock_interval=clock(),
            method=raw[index]['context']['method'])
        raw.append(changed)
    with pytest.raises(adapter.JsonSafetyError):
        adapt(urls, raw=raw)
