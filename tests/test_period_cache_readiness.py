"""Late source-cache readiness; synthetic Edge fixtures on GitHub runners only."""
from copy import deepcopy
import json

import pytest

from support_isolated_browser import browser
import coretax_browser as driver
from spt_desktop import diagnostics as d
from test_diagnostics import records
from test_json_inventory import synthetic_listing_browser


def stages(root):
    return [e['catalog_stage'] for e in records(root) if e['event'] == 'catalog.checkpoint']


@pytest.mark.parametrize('deferred', [False, True])
def test_cache_available_on_submitted_navigation_filters_without_draft_rescan(browser, tmp_path, monkeypatch, deferred):
    # Read the source cache after normal submitted navigation, never revisit drafts.
    original = driver.read_period_catalog
    write_attempts = []

    def readonly_catalog(page):
        # Trap writes only during the reader; the fixture may seed its own cache
        # during normal navigation outside this observation window.
        page.evaluate('''() => {
            window.catalogWriteAttempts = 0;
            window.catalogOriginalMethods = [];
            for (const [prototype, names] of [
                [IDBObjectStore.prototype, ['put', 'add', 'delete', 'clear', 'createIndex', 'deleteIndex']],
                [IDBDatabase.prototype, ['createObjectStore', 'deleteObjectStore']],
                [IDBFactory.prototype, ['deleteDatabase']]]) {
                for (const name of names) {
                    window.catalogOriginalMethods.push([prototype, name, prototype[name]]);
                    prototype[name] = function() {
                        window.catalogWriteAttempts++;
                        throw new Error('Synthetic readonly cache trap');
                    };
                }
            }
        }''')
        try:
            return original(page)
        finally:
            attempts = page.evaluate('''() => {
                for (const [prototype, name, method] of window.catalogOriginalMethods)
                    prototype[name] = method;
                return window.catalogWriteAttempts;
            }''')
            write_attempts.append(attempts)

    monkeypatch.setattr(driver, 'read_period_catalog', readonly_catalog)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, deferred_catalog=deferred) as (page, metrics):
        with d.session(tmp_path/'logs', 'worker') as log:
            result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path/'job', max_pages=20)
            assert log.flush()
        assert result['inventory_complete'], result['errors']
        assert {r['record_id'] for r in result['records']} == {
            'fixture-normal', 'fixture-amend-001', 'fixture-monthly', 'fixture-cross-year'}
        assert metrics['submitted_requests']
        requests = metrics['submitted_requests']
        assert all(p['Filters'] for p in requests[int(deferred):])
        if deferred:
            assert requests[0]['Filters'] == []
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
        # Only the taxpayer-selection landing precedes submitted partitions.
        assert sum('/not-submitted-' in p for p in metrics['list_navigations']) == 1
        submitted_entries = [e for e in result['audit'] if e['status'] == 'SPT Dilaporkan']
        assert sum('/submitted-' in p for p in metrics['list_navigations']) == len(submitted_entries) + int(deferred)
        assert all(e['filter_mode'] == 'period-year-candidates' for e in submitted_entries)
    assert write_attempts and not any(write_attempts)
    observed = stages(tmp_path/'logs')
    assert observed.count('readiness') == int(deferred)
    assert observed[0] == 'planning' and observed[-1] == 'after_inventory'


@pytest.mark.parametrize('mode', ['absent', 'expired', 'expired_deferred', 'retry_error'])
def test_unavailable_cache_keeps_unfiltered_fallback_and_bounded_reads(browser, tmp_path, monkeypatch, mode):
    original = driver.read_period_catalog
    calls = []

    def read(page):
        calls.append(page.url)
        if mode == 'retry_error' and len(calls) == 2:
            raise RuntimeError('PRIVATE-READINESS-ERROR')
        return original(page)

    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=mode in ('expired', 'expired_deferred'),
                                   expired_catalog=True, deferred_catalog=mode == 'expired_deferred') as (page, metrics):
        with d.session(tmp_path/'logs', 'worker') as log:
            result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path/'job', max_pages=20)
            assert log.flush()
        assert result['inventory_complete'], result['errors']
        assert all(not p['Filters'] for p in metrics['submitted_requests'])
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
        assert len(metrics['list_navigations']) == 2
    assert len(calls) == {'absent': 4, 'expired': 2, 'expired_deferred': 3, 'retry_error': 3}[mode]
    assert stages(tmp_path/'logs').count('readiness') == (0 if mode == 'expired' else 1)
    assert 'PRIVATE-READINESS-ERROR' not in json.dumps(records(tmp_path/'logs'))


@pytest.mark.parametrize('change', ['semantic', 'expired'])
def test_recovered_cache_still_requires_partition_recheck(browser, tmp_path, monkeypatch, change):
    original = driver.read_period_catalog
    calls = []

    def read(page):
        value = original(page)
        calls.append(value is not None)
        if len(calls) == 1:
            return None
        if len(calls) >= 3 and value is not None:
            value = deepcopy(value)
            if change == 'semantic':
                value['Checksum'] += '-changed'
            else:
                value['ExpiryDate'] = '2000-01-01T00:00:00Z'
        return value

    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=20)
        requests = metrics['submitted_requests']
        assert requests[0]['Filters'] == []
        assert all(p['Filters'] for p in requests[1:])
        assert not result['inventory_complete']
        assert any('Period catalog changed' in e['message'] for e in result['errors'])
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0


@pytest.mark.parametrize('cancel', ['raise', 'callback'])
def test_stop_during_readiness_prevents_filtered_restart(browser, tmp_path, monkeypatch, cancel):
    original = driver.read_period_catalog
    calls = []
    stopped = False

    def read(page):
        nonlocal stopped
        calls.append(page.url)
        if len(calls) == 2:
            if cancel == 'raise':
                raise driver.CaptureCancelled()
            stopped = True
        return original(page)

    def check_cancel():
        if stopped:
            raise driver.CaptureCancelled()

    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, deferred_catalog=True) as (page, metrics):
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                     max_pages=20, check_cancel=check_cancel)
        assert len(metrics['submitted_requests']) == 1
        assert metrics['submitted_requests'][0]['Filters'] == []
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
        assert len(metrics['list_navigations']) == 2
        assert not (tmp_path/'inventory.json').exists()
        assert (tmp_path/'inventory-batches.jsonl').read_bytes() == b''
