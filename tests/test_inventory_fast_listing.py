"""Listing throughput contracts using only isolated synthetic Edge pages."""
import pytest

import coretax_browser as driver
from support_isolated_browser import browser
from test_json_inventory import synthetic_listing_browser


@pytest.mark.parametrize('extra_read', [False, True])
def test_late_catalog_filters_before_any_unfiltered_page_is_checkpointed(browser, tmp_path, monkeypatch, extra_read):
    original_read = driver.read_period_catalog
    submitted_reads = []
    grace_waits = []
    waiting = False

    def read(page):
        nonlocal waiting
        if '/submitted-returnsheets/' in page.url:
            submitted_reads.append(True)
            if extra_read and len(submitted_reads) == 1:
                waiting = True
                return None
            waiting = False
        return original_read(page)

    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, deferred_catalog=True) as (page, metrics):
        original_wait = page.wait_for_timeout

        def wait(milliseconds):
            if waiting:
                grace_waits.append(milliseconds)
            original_wait(milliseconds)

        monkeypatch.setattr(page, 'wait_for_timeout', wait)
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        assert run['inventory_complete'], run['errors']
        assert {r['record_id'] for r in run['records']} == {
            'fixture-normal', 'fixture-amend-001', 'fixture-monthly', 'fixture-cross-year'}
        requests = metrics['submitted_requests']
        assert len(requests) == 4, 'One readiness page followed by three filtered pages'
        assert requests[0]['Filters'] == []
        assert all(request['Filters'] for request in requests[1:])
        assert [request['First'] for request in requests] == [0, 0, 2, 0]
        assert all(a['filter_mode'] == 'period-year-candidates' for a in run['audit'])
        assert all(r.get('list_filter') for r in run['records'])
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
        assert len(metrics['list_navigations']) == 4
        assert len((tmp_path/'inventory-batches.jsonl').read_text(encoding='utf-8').splitlines()) == 4
        assert len(submitted_reads) == (5 if extra_read else 4)
        assert sum(grace_waits) == (500 if extra_read else 0)
        assert all(milliseconds <= 100 for milliseconds in grace_waits)


@pytest.mark.parametrize(('initial', 'options', 'expected'), [
    (10, [10, 50, 100], 100), (50, [10, 50, 100], 100),
    (100, [10, 50, 100], 100), (50, [10, 50], 50), (10, [10], 10),
])
def test_inventory_uses_largest_offered_page_size_without_waiting_for_noop(browser, tmp_path, monkeypatch,
                                                                         initial, options, expected):
    original_wait = driver.ListObserver.wait

    def bounded_wait(self, after, timeout=45):
        # A no-op resize must not consume the production 45-second timeout.
        return original_wait(self, after, timeout=0.5)

    monkeypatch.setattr(driver.ListObserver, 'wait', bounded_wait)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, expired_catalog=True,
                                   outside_year_padding=120, page_sizes=options,
                                   initial_page_size=initial) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        assert run['inventory_complete'], run['errors']
        assert len(run['records']) == 4
        assert {r['list_page_size'] for r in run['records']} == {expected}
        requests = metrics['submitted_requests']
        assert len(requests) == (125 + expected - 1)//expected + (initial != expected)
        assert requests[0]['Rows'] == initial
        assert all(r['Rows'] == expected for r in requests[int(initial != expected):])
        assert run['audit'][0]['scanned'] == run['audit'][0]['total'] == 125
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_stop_after_readiness_navigation_prevents_filtered_restart_and_checkpoint(browser, tmp_path, monkeypatch):
    stop = {'requested': False}

    def check_cancel():
        if stop['requested']:
            raise driver.CaptureCancelled()

    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, deferred_catalog=True,
                                   stop_state=stop) as (page, metrics):
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                     check_cancel=check_cancel)
        assert len(metrics['submitted_requests']) == 1
        assert metrics['submitted_requests'][0]['Filters'] == []
        assert not (tmp_path/'inventory.json').exists()
        assert (tmp_path/'inventory-batches.jsonl').read_bytes() == b''
