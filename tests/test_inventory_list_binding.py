"""Synthetic regressions for auxiliary list traffic and same-page navigation."""
import pytest

from support_browser_protocol import SignalSource, TAXPAYER, response
from test_inventory_year_browser import ENDPOINT, FILTER, feature, send, synthetic_browser
from test_json_inventory import synthetic_listing_browser


def test_identity_only_auxiliary_response_does_not_replace_empty_grid():
    import coretax_browser as driver
    observer = driver.ListObserver(SignalSource())
    empty = response([], total=0)
    observer.on_response(empty)
    before = observer.sequence
    auxiliary = response([{'RecordId': 'synthetic-auxiliary'}], total=600,
                         url=driver.ORIGIN + '/returnsheet/api/returnsheetssubmitted')
    auxiliary.request.post_data_json = {'TaxpayerAggregateIdentifier': TAXPAYER}
    observer.on_response(auxiliary)
    assert observer.sequence == before
    assert observer.latest['total'] == 0 and observer.latest['rows'] == []


@pytest.mark.parametrize('field,value', [
    ('First', None), ('First', -1), ('First', True), ('First', 1),
    ('Rows', None), ('Rows', 0), ('Rows', True), ('Filters', None),
    ('TaxpayerAggregateIdentifier', ''), ('TaxpayerAggregateIdentifier', None),
])
def test_non_grid_request_never_creates_a_fresh_listing_event(field, value):
    import coretax_browser as driver
    observer = driver.ListObserver(SignalSource())
    item = response()
    item.request.post_data_json[field] = value
    observer.on_response(item)
    assert observer.sequence == 0 and observer.latest is None


def test_non_post_request_is_not_a_grid_response():
    import coretax_browser as driver
    observer = driver.ListObserver(SignalSource())
    item = response()
    item.request.method = 'GET'
    observer.on_response(item)
    assert observer.sequence == 0


def auxiliary(page, payload):
    return page.evaluate('''async ({url,payload}) => {
        try {return (await fetch(url,{method:'POST',body:JSON.stringify(payload)})).status;}
        catch {return 'blocked';}
    }''', {'url': ENDPOINT, 'payload': payload})


def test_owned_route_preserves_exact_auxiliary_read_without_filtering_or_observing_it():
    from coretax_browser import ListObserver
    with synthetic_browser() as (page, metrics):
        observer = ListObserver(page)
        try:
            with feature().InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
                observer.request_filter = guard
                assert send(page) == 200
                result = observer.wait(0)
                sequence = observer.sequence
                payload = {'TaxpayerAggregateIdentifier': 'synthetic-taxpayer'}
                assert auxiliary(page, payload) == 200
                page.wait_for_timeout(100)
                assert metrics['requests'][-1] == payload
                assert observer.sequence == sequence
                assert observer.latest['binding'] == result['binding']
                assert guard.error is None
                assert send(page) == 200
                assert observer.wait(sequence)['binding']['request']['Filters'] == [FILTER]
        finally:
            observer.request_filter = None
            observer.close()


@pytest.mark.parametrize('payload', [
    {'TaxpayerAggregateIdentifier': 'other-taxpayer'},
    {'TaxpayerAggregateIdentifier': 'synthetic-taxpayer', 'First': 0},
    {'TaxpayerAggregateIdentifier': 'synthetic-taxpayer', 'Filters': []},
    {'TaxpayerAggregateIdentifier': 'synthetic-taxpayer', 'isArchieved': False},
])
def test_auxiliary_exception_does_not_authorize_other_request_shapes(payload):
    with synthetic_browser() as (page, metrics):
        with feature().InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
            assert auxiliary(page, payload) == 'blocked'
            assert guard.error is not None and metrics['requests'] == []


@pytest.mark.parametrize('catalog,expired', [(False, False), (True, False), (True, True)])
def test_collection_reconciles_visible_grid_despite_auxiliary_submitted_reads(monkeypatch, tmp_path, catalog, expired):
    import coretax_browser as driver
    with synthetic_listing_browser(monkeypatch, year_catalog=catalog, expired_catalog=expired,
                                   auxiliary_request=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is True, run['errors']
    draft = next(a for a in run['audit'] if a['status'] == 'SPT Belum Disampaikan')
    assert draft['total'] == draft['scanned'] == 0 and draft['result'] == 'RECONCILED'
    assert len(run['records']) == (4 if catalog else 2)
    assert metrics['auxiliary_requests'] > 0
    assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
    assert all(bool(r['Filters']) == (catalog and not expired) for r in metrics['submitted_requests'])


def test_same_page_hash_anchor_is_not_an_additional_status_source(monkeypatch, tmp_path):
    import coretax_browser as driver
    original_wait = driver.ListObserver.wait
    def bounded_wait(self, after, timeout=45):
        return original_wait(self, after, timeout=min(timeout, 3))
    # Only shorten the failure deadline; all observer and browser behavior is real.
    monkeypatch.setattr(driver.ListObserver, 'wait', bounded_wait)
    with synthetic_listing_browser(monkeypatch, hash_link=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is True, run['errors']
    assert len(run['sources']) == 2
    assert all(s['label'] and '#' not in s['url'] for s in run['sources'])
    assert {a['status'] for a in run['audit']} == {'SPT Belum Disampaikan', 'SPT Dilaporkan'}
    assert metrics['unregistered_requests'] == 0
