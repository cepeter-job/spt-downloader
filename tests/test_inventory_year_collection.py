"""End-to-end inventory/replay contracts using only the synthetic Coretax fixture."""
from copy import deepcopy

import pytest

from support_isolated_browser import browser
from test_json_inventory import synthetic_listing_browser


def test_year_inventory_filters_before_pagination_and_reconciles_both_partitions(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is True
    assert {r['record_id'] for r in run['records']} == {
        'fixture-normal', 'fixture-amend-001', 'fixture-monthly', 'fixture-cross-year'}
    requests = metrics['submitted_requests']
    assert len(requests) == 3
    assert all(request['Filters'] for request in requests)
    assert [r['First'] for r in requests] == [0, 2, 0]
    filtered = [a for a in run['audit'] if a.get('list_filter')]
    assert [(a['total'], a['scanned'], a['selected']) for a in filtered] == [(3, 3, 3), (1, 1, 1)]
    for record in run['records']:
        assert record['list_filter']['PropertyName'] == 'TaxPeriodCode'
        assert len(record['list_catalog_sha256']) == 64
    assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_expired_catalog_uses_explicit_complete_unfiltered_fallback(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, expired_catalog=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is True
    assert len(run['records']) == 4
    assert all(r['Filters'] == [] for r in metrics['submitted_requests'])
    submitted = [a for a in run['audit'] if a['status'] == 'SPT Dilaporkan']
    assert len(submitted) == 1
    assert submitted[0]['filter_mode'] == 'unfiltered'
    assert submitted[0]['filter_reason']


def test_filtered_dom_fallback_rejects_server_ignoring_declared_filter(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, ignore_source_filter=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is False
    assert any(e['message'] == 'capture_safety_refusal' for e in run['errors'])
    assert metrics['detail_actions'] == 0


def test_empty_filtered_partitions_are_reconciled_without_unfiltered_retry(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, empty=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is True and run['records'] == []
    filtered = [a for a in run['audit'] if a.get('list_filter')]
    assert len(filtered) == 2
    assert all(a['total'] == a['scanned'] == 0 and a['result'] == 'RECONCILED' for a in filtered)
    assert len(metrics['submitted_requests']) == 2
    assert all(r['Filters'] for r in metrics['submitted_requests'])


def test_changed_filtered_total_stays_partial(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, changed_total=True) as (page, _):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is False
    assert any(a.get('list_filter') and a['result'] == 'PARTIAL' for a in run['audit'])


def test_empty_filtered_partitions_reset_retained_offset_before_request(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, empty=True,
                                   start=2, auxiliary_request=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'] is True, run['errors']
    assert run['records'] == [] and run['errors'] == []
    assert [(a['total'], a['scanned'], a['result']) for a in run['audit']] == [
        (0, 0, 'RECONCILED'), (0, 0, 'RECONCILED')]
    assert [request['First'] for request in metrics['submitted_requests']] == [0, 0]
    assert all(request['Filters'] for request in metrics['submitted_requests'])
    assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_selected_record_restores_persisted_filter_before_readonly_view(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        record = deepcopy(next(r for r in run['records'] if r['record_id'] == 'fixture-cross-year'))
        record.update(list_page=1, row_position=0, list_page_size=2,
                      list_filter={'PropertyName': 'TaxPeriodCode', 'MatchMode': 'equals',
                                   'Value': '02012023', 'CaseSensitive': True, 'AsString': False})
        run['records'] = [record]
        driver.collect_details(page, run, tmp_path)
        assert metrics['viewed_record_ids'] == ['fixture-cross-year']
        assert metrics['submitted_requests'][-1]['Filters'] == [record['list_filter']]


def test_cancelled_filtered_inventory_removes_request_route(browser, monkeypatch, tmp_path):
    import coretax_browser as driver
    stop = {'requested': False}
    def cancelled():
        if stop['requested']:
            raise driver.CaptureCancelled('synthetic cancellation')
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, stop_state=stop) as (page, metrics):
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                     check_cancel=cancelled)
        page.evaluate('''async () => await fetch('/returnsheet/api/returnsheetssubmitted', {
            method:'POST',body:JSON.stringify({TaxpayerAggregateIdentifier:'fixture-taxpayer',
                First:0,Rows:2,Filters:[],isArchieved:false,LanguageId:1,SortField:null,SortOrder:null})})''')
        assert metrics['submitted_requests'][-1]['Filters'] == []


def test_managed_worker_includes_inventory_filter_module():
    from spt_desktop.runtime import WORKER_FILES
    assert 'coretax_inventory.py' in WORKER_FILES
