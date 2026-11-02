"""Review regressions: owned UI, request reordering, bounded reads and fatality."""
import json
import threading
import time

import pytest
from playwright.sync_api import Error as PlaywrightError, Locator

from support_isolated_browser import browser as browser
from coretax_browser import CaptureCancelled
from coretax_mpn import MpnSafetyError
from coretax_mpn_browser import collect_mpn
from coretax_mpn_ui import AccountingUI
from test_mpn import scope_run
from test_mpn_browser import Request, Response
from test_mpn_capture_browser import portal


def test_second_search_waits_for_actual_clear_reply_not_an_older_pending_request(browser, tmp_path, monkeypatch):
    state = {'held': None, 'released': False, 'cleared': False}
    original_clear = AccountingUI._clear_initial_transaction_date
    original_click = AccountingUI._click_ready
    with portal(browser, monkeypatch, default_stuck=True, transaction_date_clear='valid') as (page, metrics):
        def hold(route):
            if state.get('hold_next'):
                state['hold_next'] = False
                state['held'] = route
            else:
                route.fallback()
        page.context.route('**/accounting/api/taxpayeraccounting/list', hold)
        def clear(owned, snapshot, grid):
            state['owned'] = owned
            state['raw'] = snapshot['raw']
            old = Request(page)
            old.post_data_json['Filters'] = snapshot['request']['Filters']
            old.post_data = json.dumps(old.post_data_json)
            owned.observer.on_request(old)
            state['old'] = old
            state['hold_next'] = True
            return original_clear(owned, snapshot, grid)
        def click(owned, locator, *args, **kwargs):
            is_date = locator.get_attribute('aria-label', timeout=1000) == 'Clear date'
            if not is_date and state['cleared'] and not state['released']:
                pytest.fail('Second Search ran before its actual clear response completed')
            result = original_click(owned, locator, *args, **kwargs)
            if is_date:
                state['cleared'] = True
                # The older request was admitted before the clear boundary,
                # but its response finishes only after the real clear click.
                owned.observer.on_response(Response(state['old']))
            return result
        original_wait = page.wait_for_timeout
        def pump(milliseconds):
            if state['held'] is not None and not state['released']:
                state['released'] = True
                state['held'].fulfill(body=state['raw'], content_type='application/json')
            return original_wait(milliseconds)
        monkeypatch.setattr(AccountingUI, '_clear_initial_transaction_date', clear)
        monkeypatch.setattr(AccountingUI, '_click_ready', click)
        monkeypatch.setattr(page, 'wait_for_timeout', pump)
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert state['held'] is not None and state['released']
        assert run['mpn']['status'] == 'COMPLETE' and run['complete']
        assert page.evaluate('window.syntheticDateClicks') == 1
        assert page.evaluate('window.syntheticSearchClicks') == 2
        assert len(metrics['detail']) == 1


def test_missing_date_container_is_refused_without_waiting_default_locator_timeout(browser, tmp_path, monkeypatch):
    elapsed = []
    original_clear = AccountingUI._clear_initial_transaction_date
    def clear(owned, snapshot, grid):
        owned.preparation_deadline = time.monotonic() + .2
        start = time.monotonic()
        try:
            return original_clear(owned, snapshot, grid)
        finally:
            elapsed.append(time.monotonic() - start)
    monkeypatch.setattr(AccountingUI, '_clear_initial_transaction_date', clear)
    with portal(browser, monkeypatch, default_stuck=True, transaction_date_clear='missing_parent') as (page, metrics):
        page.set_default_timeout(1500)
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['mpn']['status'] == 'PARTIAL' and not run['complete']
        assert elapsed and max(elapsed) < .75
        assert page.evaluate('window.syntheticDateClicks') == 0
        assert metrics['detail'] == []


def test_detached_date_metadata_read_obeys_remaining_budget_and_stop(browser, tmp_path, monkeypatch):
    state = {'reading': False, 'detached': False, 'elapsed': []}
    stopped = threading.Event()
    timers = []
    original_clear = AccountingUI._clear_initial_transaction_date
    original_attribute = Locator.get_attribute
    with portal(browser, monkeypatch, default_stuck=True, transaction_date_clear='valid') as (page, metrics):
        page.set_default_timeout(1500)
        def clear(owned, snapshot, grid):
            owned.preparation_deadline = time.monotonic() + .2
            state['reading'] = True
            start = time.monotonic()
            try:
                return original_clear(owned, snapshot, grid)
            finally:
                state['elapsed'].append(time.monotonic() - start)
        def attribute(locator, name, **kwargs):
            if state['reading'] and not state['detached'] and name == 'class':
                page.evaluate("document.querySelector('p-calendar#filterTransactionDate').parentElement.remove()")
                state['detached'] = True
                timer = threading.Timer(.05, stopped.set)
                timer.daemon = True
                timers.append(timer)
                timer.start()
            return original_attribute(locator, name, **kwargs)
        def stop():
            if stopped.is_set():
                raise CaptureCancelled('SYNTHETIC_STOP')
        monkeypatch.setattr(AccountingUI, '_clear_initial_transaction_date', clear)
        monkeypatch.setattr(Locator, 'get_attribute', attribute)
        try:
            with pytest.raises(CaptureCancelled):
                collect_mpn(page, scope_run(), tmp_path, check_cancel=stop)
            assert state['detached'] and max(state['elapsed']) < .75
            assert page.evaluate('window.syntheticDateClicks') == 0
            assert metrics['detail'] == []
        finally:
            for timer in timers:
                timer.cancel()


@pytest.mark.parametrize('phase', ['trial', 'actual'])
def test_date_click_error_cannot_demote_callback_pumped_fatal_source_refusal(browser, tmp_path, monkeypatch, phase):
    state = {'owned': None, 'attempts': 0}
    original_clear = AccountingUI._clear_initial_transaction_date
    original_click = Locator.click
    def clear(owned, snapshot, grid):
        state['owned'] = owned
        return original_clear(owned, snapshot, grid)
    def click(locator, *args, **kwargs):
        is_date = state['owned'] is not None and locator.get_attribute('aria-label', timeout=1000) == 'Clear date'
        if is_date and bool(kwargs.get('trial')) is (phase == 'trial'):
            original_click(locator, *args, **kwargs)
            state['attempts'] += 1
            state['owned']._reject_source('ownership', safety=True, ownership_reason='page_route')
            raise PlaywrightError('SYNTHETIC_POST_CALLBACK_FAILURE')
        return original_click(locator, *args, **kwargs)
    monkeypatch.setattr(AccountingUI, '_clear_initial_transaction_date', clear)
    monkeypatch.setattr(Locator, 'click', click)
    with portal(browser, monkeypatch, default_stuck=True, transaction_date_clear='valid') as (page, metrics):
        with pytest.raises(MpnSafetyError):
            collect_mpn(page, scope_run(), tmp_path)
        assert state['attempts'] == 1
        assert page.evaluate('window.syntheticDateClicks') == (phase == 'actual')
        assert page.evaluate('window.syntheticSearchClicks') == 1
        assert metrics['detail'] == []
