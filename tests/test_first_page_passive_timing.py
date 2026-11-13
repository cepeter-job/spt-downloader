"""Synthetic first-idle boundary evidence: no browsers, accounts or endpoints."""
import json
from contextlib import nullcontext

import pytest

import coretax_browser as browser
from spt_desktop import diagnostics as d
from test_diagnostics import records


class FakeFirstWaitPage:
    def __init__(self, *, fail=False):
        self.calls = []
        self.fail = fail
        self.callbacks = {}
        self.first = self

    def on(self, event, callback):
        self.callbacks[event] = callback

    def remove_listener(self, event, callback):
        assert self.callbacks.pop(event) is callback

    def locator(self, selector):
        self.calls.append(('locator', selector))
        return self

    def wait_for(self, *, state, timeout):
        self.calls.append(('wait_for', state, timeout))
        # Simulate an existing unbound request lifecycle without reading it.
        request = object()
        if self.callbacks:
            self.callbacks['request'](request)
            self.callbacks['requestfinished'](request)
        if self.fail:
            raise browser.PlaywrightTimeoutError('SYNTHETIC_PRIVATE_TIMEOUT_BODY')

    def wait_for_timeout(self, milliseconds):
        self.calls.append(('wait_for_timeout', milliseconds))


def expected_calls(fail):
    calls = [
        ('locator', '.p-datatable-loading-overlay:visible,.p-blockui:visible'),
        ('wait_for', 'hidden', 45000),
    ]
    if not fail:
        calls.append(('wait_for_timeout', 180))
    return calls


@pytest.mark.parametrize('fail', [False, True])
def test_first_idle_local_timing_preserves_original_calls_and_timeout(
        fail, tmp_path):
    page = FakeFirstWaitPage(fail=fail)
    original = FakeFirstWaitPage(fail=fail)
    with pytest.raises(browser.PlaywrightTimeoutError) if fail else nullcontext():
        # Caller is uninstrumented by default.
        browser.wait_idle(original)
    assert original.calls == expected_calls(fail)

    with d.session(tmp_path, 'worker') as log:
        observer = browser._InitialLoadingDiagnostics(page, 3)
        observer.stage = 'first_idle'
        token = browser._FIRST_PAGE_TIMING_SCOPE.set((3, 500, observer))
        try:
            with pytest.raises(browser.PlaywrightTimeoutError) if fail else nullcontext():
                browser.wait_idle(page)
        finally:
            browser._FIRST_PAGE_TIMING_SCOPE.reset(token)
            observer.close()
        assert log.flush()

    assert page.calls == original.calls
    timing = [r for r in records(tmp_path) if r['event'] == 'table.first_page_timing']
    assert [r['table_first_page_step'] for r in timing] == (
        ['first_overlay_wait'] if fail else ['first_overlay_wait', 'first_settle_wait'])
    assert timing[0]['table_first_page_outcome'] == ('raised' if fail else 'returned')
    assert timing[0]['table_first_page_finished_requests'] == 1
    assert timing[0]['table_first_page_last_finish_ms'] >= 0
    assert timing[0]['duration_ms'] >= 0
    assert timing[0]['table_rpc_thread_cpu_ms'] >= 0
    assert all(r['form_ordinal'] == 1 and r['table_ordinal'] == 3 for r in timing)
    assert 'SYNTHETIC_PRIVATE_TIMEOUT_BODY' not in json.dumps(records(tmp_path))


def test_first_idle_not_logged_when_session_disabled(tmp_path):
    page = FakeFirstWaitPage()
    with d.session(tmp_path, 'worker', level='OFF'):
        observer = browser._InitialLoadingDiagnostics(page, 3)
        observer.stage = 'first_idle'
        token = browser._FIRST_PAGE_TIMING_SCOPE.set((3, 500, observer))
        try:
            browser.wait_idle(page)
        finally:
            browser._FIRST_PAGE_TIMING_SCOPE.reset(token)
            observer.close()
    assert page.calls == expected_calls(False)
    assert not records(tmp_path)


def test_first_idle_diagnostic_is_scoped_and_fails_closed(tmp_path):
    page = FakeFirstWaitPage()
    with d.session(tmp_path, 'worker') as log:
        observer = browser._InitialLoadingDiagnostics(page, 3)
        observer.stage = 'first_idle'
        token = browser._FIRST_PAGE_TIMING_SCOPE.set((3, 500, observer))
        try:
            browser.wait_idle(page)
        finally:
            browser._FIRST_PAGE_TIMING_SCOPE.reset(token)
            observer.close()
        assert log.flush()
        # The context is guaranteed to reset before an unrelated wait.
        fresh = FakeFirstWaitPage()
        browser.wait_idle(fresh)
        assert log.flush()
    assert fresh.calls == expected_calls(False)
    assert [r['table_first_page_step'] for r in records(tmp_path)
            if r['event'] == 'table.first_page_timing'] == [
                'first_overlay_wait', 'first_settle_wait']


def test_first_idle_preserves_stop_without_sending_settle_call(tmp_path):
    page = FakeFirstWaitPage()
    original_wait = page.wait_for

    def stop_in_original_wait(*, state, timeout):
        original_wait(state=state, timeout=timeout)
        raise browser.CaptureCancelled('SYNTHETIC_PRIVATE_CANCEL')

    page.wait_for = stop_in_original_wait
    with d.session(tmp_path, 'worker') as log:
        observer = browser._InitialLoadingDiagnostics(page, 3)
        token = browser._FIRST_PAGE_TIMING_SCOPE.set((3, 500, observer))
        try:
            with pytest.raises(browser.CaptureCancelled):
                browser.wait_idle(page)
        finally:
            browser._FIRST_PAGE_TIMING_SCOPE.reset(token)
            observer.close()
        assert log.flush()
    assert page.calls == expected_calls(True)
    events = [r for r in records(tmp_path)
              if r['event'] == 'table.first_page_timing']
    assert len(events) == 1
    assert events[0]['table_first_page_step'] == 'first_overlay_wait'
    assert events[0]['table_first_page_outcome'] == 'raised'
    assert 'SYNTHETIC_PRIVATE_CANCEL' not in json.dumps(records(tmp_path))


def test_small_table_scope_never_emits_first_page_diagnostic(tmp_path):
    page = FakeFirstWaitPage()
    with d.session(tmp_path, 'worker') as log:
        observer = browser._InitialLoadingDiagnostics(page, 1)
        token = browser._FIRST_PAGE_TIMING_SCOPE.set((1, 100, observer))
        try:
            browser.wait_idle(page)
        finally:
            browser._FIRST_PAGE_TIMING_SCOPE.reset(token)
            observer.close()
        assert log.flush()
    assert page.calls == expected_calls(False)
    assert not any(r['event'] == 'table.first_page_timing'
                   for r in records(tmp_path))


def test_first_idle_schema_keeps_only_fixed_categories_and_numeric_values(tmp_path):
    secret = 'SYNTHETIC_PRIVATE_FIRST_IDLE_REQUEST'
    with d.session(tmp_path, 'worker') as log:
        d.record('table.first_page_timing',
                 table_first_page_step='first_overlay_wait',
                 table_first_page_outcome='raised',
                 table_first_page_finished_requests=2,
                 table_first_page_last_finish_ms=44.1234,
                 table_rpc_thread_cpu_ms=2.3456,
                 duration_ms=45000.12345,
                 url=secret, pid=secret, selector=secret,
                 request=secret, exception=secret, message=secret)
        d.record('table.first_page_timing',
                 table_first_page_step=secret,
                 table_first_page_outcome=secret,
                 table_first_page_finished_requests=-1,
                 table_first_page_last_finish_ms=float('inf'),
                 duration_ms=float('nan'))
        assert log.flush()
    events = [r for r in records(tmp_path) if r['event'] == 'table.first_page_timing']
    assert len(events) == 2
    assert events[0]['table_first_page_step'] == 'first_overlay_wait'
    assert events[0]['table_first_page_finished_requests'] == 2
    assert events[0]['table_first_page_last_finish_ms'] == 44.12
    assert events[0]['table_rpc_thread_cpu_ms'] == 2.35
    assert events[0]['duration_ms'] == 45000.12
    assert all(x not in events[1] for x in (
        'table_first_page_step', 'table_first_page_outcome',
        'table_first_page_finished_requests', 'table_first_page_last_finish_ms',
        'duration_ms'))
    assert secret not in json.dumps(events)
