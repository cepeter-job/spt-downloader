"""Listing throughput contracts using only isolated synthetic Edge pages."""
import pytest

import coretax_browser as driver
from support_isolated_browser import browser as browser
from test_json_inventory import synthetic_listing_browser


def reject_noop_response_wait(monkeypatch):
    """Trap the wrong wait directly without shortening real navigation budgets."""
    resize = driver.maximize_page_size
    paginate = driver._click_table_paginator
    observe = driver.ListObserver.wait
    noop = False

    def sized(page, container):
        nonlocal noop
        changed = resize(page, container)
        noop = not changed
        return changed

    def moved(*args):
        nonlocal noop
        noop = False
        return paginate(*args)

    def waited(self, after, timeout=45):
        assert not noop, 'A no-op resize must not start a fresh-response wait'
        return observe(self, after, timeout=timeout)

    monkeypatch.setattr(driver, 'maximize_page_size', sized)
    monkeypatch.setattr(driver, '_click_table_paginator', moved)
    monkeypatch.setattr(driver.ListObserver, 'wait', waited)


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
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, deferred_catalog=True,
                                   start=2 if extra_read else 0) as (page, metrics):
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
        # Retained UI offset adds one observed reset request per partition.
        assert len(requests) == (6 if extra_read else 4)
        assert requests[0]['Filters'] == []
        assert all(request['Filters'] for request in requests[1:])
        assert [request['First'] for request in requests] == ([2, 0, 0, 2, 0, 0] if extra_read else [0, 0, 2, 0])
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
    reject_noop_response_wait(monkeypatch)
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


@pytest.mark.parametrize('defect', ['request', 'rows', 'status', 'archived', 'endpoint'])
def test_contradictory_readiness_response_cannot_be_discarded_for_valid_filtered_pages(browser, tmp_path,
                                                                                     monkeypatch, defect):
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, deferred_catalog=True,
                                   readiness_defect=defect, empty=defect in ('request', 'archived')) as (page, metrics):
        with pytest.raises(RuntimeError):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        assert len(metrics['submitted_requests']) == 1
        assert metrics['submitted_requests'][0]['Filters'] == []
        assert len(metrics['list_navigations']) == 2
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
        assert not (tmp_path/'inventory.json').exists()
        assert (tmp_path/'inventory-batches.jsonl').read_bytes() == b''


def test_stop_during_catalog_grace_prevents_another_read_or_request(browser, tmp_path, monkeypatch):
    reads, waits = [], []
    stopped = False

    def read(page):
        reads.append(True)
        return None

    def check_cancel():
        if stopped:
            raise driver.CaptureCancelled()

    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(browser, monkeypatch) as (page, metrics):
        original_wait = page.wait_for_timeout

        def wait(milliseconds):
            nonlocal stopped
            original_wait(milliseconds)
            if len(reads) == 2:
                waits.append(milliseconds)
                stopped = True

        monkeypatch.setattr(page, 'wait_for_timeout', wait)
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                     check_cancel=check_cancel)
        assert waits == [100] and len(reads) == 2
        assert len(metrics['submitted_requests']) == 1
        assert not (tmp_path/'inventory.json').exists()
        assert (tmp_path/'inventory-batches.jsonl').read_bytes() == b''


@pytest.mark.parametrize('saved_size', [100, 50])
def test_detail_restore_uses_captured_size_or_fails_before_view_without_noop_wait(browser, tmp_path,
                                                                             monkeypatch, saved_size):
    from support_browser_protocol import capture_failures
    failures = capture_failures(monkeypatch)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, expired_catalog=True,
                                   page_sizes=[10, 50, 100],
                                   initial_page_size=10 if saved_size == 100 else 100) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        record = next(r for r in run['records'] if r['record_id'] == 'fixture-normal')
        assert record['list_page_size'] == 100
        record['list_page_size'] = saved_size
        run['records'] = [record]
        reject_noop_response_wait(monkeypatch)
        before = len(metrics['submitted_requests'])
        driver.collect_details(page, run, tmp_path)
        if saved_size == 100:
            assert metrics['viewed_record_ids'] == ['fixture-normal']
            assert metrics['submitted_requests'][-1]['Rows'] == 100
            assert len(metrics['submitted_requests']) == before + 2
        else:
            assert metrics['viewed_record_ids'] == []
            assert len(metrics['submitted_requests']) == before + 1
            assert any('Could not restore inventory page size' in str(error) for error in failures)
            assert all(e['message'] == 'capture_failed' for e in run['errors'])
