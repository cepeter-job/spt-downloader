"""Real-browser contracts with synthetic routes only; GitHub Windows runners."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib
import importlib.util
import json
from pathlib import Path
import sys

import pytest

from support_isolated_browser import browser, isolated_context

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
ORIGIN = 'https://coretax.intranet.pajak.go.id'
URL = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/synthetic-taxpayer'
ENDPOINT = ORIGIN + '/returnsheet/api/returnsheetssubmitted'
FILTER = {'PropertyName': 'TaxPeriodCode', 'Value': '2024', 'MatchMode': 'contains',
          'CaseSensitive': True, 'AsString': False}


def feature():
    assert importlib.util.find_spec('coretax_inventory') is not None, 'Inventory feature missing'
    return importlib.import_module('coretax_inventory')


@contextmanager
def synthetic_browser(browser):
    metrics = {'requests': [], 'unknown': 0}
    with isolated_context(browser) as owned_context:
        page = owned_context.new_page()
        page.set_default_timeout(5000)

        def handle(route):
            if route.request.url == URL:
                route.fulfill(body='<html lang="id-ID"><div class="main-content">Synthetic list</div></html>',
                              content_type='text/html')
            elif route.request.url == ENDPOINT:
                metrics['requests'].append(route.request.post_data_json)
                route.fulfill(json={'IsSuccessful': True, 'Payload': {'Data': [], 'TotalRecords': 0}})
            else:
                metrics['unknown'] += 1
                route.abort()
        page.route('**/*', handle)
        page.goto(URL)
        yield page, metrics


def send(page, **changes):
    payload = {'TaxpayerAggregateIdentifier': 'synthetic-taxpayer', 'First': 0, 'Rows': 50,
               'Filters': [], 'isArchieved': False, 'LanguageId': 1,
               'SortField': '', 'SortOrder': 1}
    payload.update(changes)
    return page.evaluate('''async ({url, payload}) => {
        try {const r=await fetch(url,{method:'POST',body:JSON.stringify(payload)});return r.status;}
        catch {return 'blocked';}
    }''', {'url': ENDPOINT, 'payload': payload})


def test_owned_filter_route_exposes_effective_request_and_unroutes_on_exit(browser):
    module = feature()
    from coretax_browser import ListObserver
    with synthetic_browser(browser) as (page, metrics):
        observer = ListObserver(page)
        try:
            with module.InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
                observer.request_filter = guard
                before = observer.sequence
                assert send(page) == 200
                response = observer.wait(before)
                assert metrics['requests'][0]['Filters'] == [FILTER]
                assert response['binding']['request']['Filters'] == [FILTER]
                assert response['binding']['request']['First'] == 0
                assert response['binding']['filter_rewrite']['original_sha256'] != response['binding']['filter_rewrite']['effective_sha256']
            observer.request_filter = None
            assert send(page) == 200
            assert metrics['requests'][-1]['Filters'] == []
            assert metrics['unknown'] == 0
        finally:
            observer.close()


def test_filter_route_blocks_foreign_taxpayer_before_transport(browser):
    module = feature()
    with synthetic_browser(browser) as (page, metrics):
        with module.InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
            assert send(page, TaxpayerAggregateIdentifier='different-taxpayer') == 'blocked'
            assert guard.error is not None
            assert metrics['requests'] == []


@pytest.mark.parametrize('auxiliary', [False, True])
def test_owned_filter_starts_at_zero_then_preserves_requested_pages(browser, auxiliary):
    module = feature()
    from coretax_browser import ListObserver
    with synthetic_browser(browser) as (page, metrics):
        observer = ListObserver(page)
        try:
            with module.InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
                observer.request_filter = guard
                if auxiliary:
                    assert page.evaluate('''async url => (await fetch(url, {method:'POST',
                        body:JSON.stringify({TaxpayerAggregateIdentifier:'synthetic-taxpayer'})})).status
                    ''', ENDPOINT) == 200
                before = observer.sequence
                assert send(page, First=50) == 200
                initial = observer.wait(before)
                assert initial['first'] == initial['binding']['request']['First'] == 0
                before = observer.sequence
                assert send(page, First=50) == 200
                following = observer.wait(before)
                assert following['first'] == following['binding']['request']['First'] == 50
                grid = [r for r in metrics['requests'] if 'First' in r]
                assert [r['First'] for r in grid] == [0, 50]
                assert all(r['Filters'] == [FILTER] for r in grid)
            observer.request_filter = None
            assert send(page, First=100) == 200
            assert metrics['requests'][-1]['First'] == 100
            assert metrics['requests'][-1]['Filters'] == []
            assert metrics['unknown'] == 0
        finally:
            observer.close()


@pytest.mark.parametrize('first', [-1, 1, True])
def test_initial_filter_reset_never_qualifies_malformed_pagination(browser, first):
    module = feature()
    with synthetic_browser(browser) as (page, metrics):
        with module.InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
            assert send(page, First=first) == 'blocked'
            assert guard.error is not None
            assert metrics['requests'] == []


def test_filter_route_never_overwrites_existing_user_filters(browser):
    module = feature()
    with synthetic_browser(browser) as (page, metrics):
        with module.InventoryFilterRoute(page, 'synthetic-taxpayer', FILTER) as guard:
            assert send(page, Filters=[{**FILTER, 'Value': '2023'}]) == 'blocked'
            assert guard.error is not None
            assert metrics['requests'] == []


def test_reference_read_does_not_create_database_or_issue_network_requests(browser):
    module = feature()
    with synthetic_browser(browser) as (page, metrics):
        assert module.read_period_catalog(page) is None
        assert page.evaluate('async()=> (await indexedDB.databases()).length') == 0
        assert metrics == {'requests': [], 'unknown': 0}


def test_reference_read_returns_only_period_metadata_with_date_provenance(browser):
    module = feature()
    with synthetic_browser(browser) as (page, metrics):
        expiry = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        page.evaluate('''async expiry => await new Promise((resolve,reject)=>{
            const request=indexedDB.open('e-tax-database',2);
            request.onupgradeneeded=()=>{
                const store=request.result.createObjectStore('referenceDataStore',{keyPath:['ReferenceDataType','language']});
                store.createIndex('ReferenceDataType','ReferenceDataType');
            };
            request.onerror=reject;
            request.onsuccess=()=>{
                const db=request.result,tx=db.transaction('referenceDataStore','readwrite');
                tx.objectStore('referenceDataStore').put({ReferenceDataType:'PERIOD',language:'id-ID',Checksum:'fixture',ExpiryDate:new Date(expiry),Details:[{Code:'01122024',CodeDescription:'Januari - Desember 2024'}]});
                tx.objectStore('referenceDataStore').put({ReferenceDataType:'UNRELATED',language:'id-ID',Details:[{Code:'private-do-not-read'}]});
                tx.oncomplete=()=>{db.close();resolve();};tx.onerror=reject;
            };
        })''', expiry)
        observed = module.read_period_catalog(page)
        assert observed['ReferenceDataType'] == 'PERIOD'
        assert observed['language'] == 'id-ID'
        assert observed['Details'] == [{'Code': '01122024', 'CodeDescription': 'Januari - Desember 2024'}]
        assert datetime.fromisoformat(observed['ExpiryDate'].replace('Z', '+00:00')).tzinfo is not None
        assert 'private-do-not-read' not in json.dumps(observed)
        assert metrics == {'requests': [], 'unknown': 0}
