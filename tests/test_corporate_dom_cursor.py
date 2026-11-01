"""Hosted Edge regressions for private exact-state comparison, synthetic only."""
import json

import pytest

from playwright.sync_api import ElementHandle, JSHandle

import coretax_browser as driver
from support_isolated_browser import browser, context
from test_corporate_dom_page_size import fixture, assert_rows


def test_250_capture_preserves_rows_without_transferring_raw_pagination_state(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=250)
    transferred = []
    original_element = ElementHandle.evaluate
    original_js = JSHandle.evaluate

    def observe(original):
        def evaluated(handle, expression, arg=None):
            result = original(handle, expression, arg)
            if expression == driver.STATE_JS:
                transferred.append(result)
            elif isinstance(result, dict) and 'state' in result:
                transferred.append(result['state'])
            return result
        return evaluated

    monkeypatch.setattr(ElementHandle, 'evaluate', observe(original_element))
    monkeypatch.setattr(JSHandle, 'evaluate', observe(original_js))
    result = driver.capture_table(page, table, 1, 1000, max_page_size=250)
    assert_rows(result, 601)
    assert result['pages'] == 3
    assert page.evaluate('moves') == 2
    assert sum(len(json.dumps(value)) for value in transferred) == 0
    page.close()


def test_cursor_queued_advance_cannot_refresh_expired_table_budget(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=250)
    owner = table.element_handle().evaluate_handle("e=>e.closest('p-table')")
    cursor = owner.evaluate_handle(driver.TABLE_CURSOR_INIT_JS)
    # Represents a delayed first command: the deadline is based on creation,
    # never on the later command's dispatch time.
    page.wait_for_timeout(30)
    result = cursor.evaluate(driver.TABLE_CURSOR_ADVANCE_JS,
                             {'remaining_ms': 1, 'allow': True})
    assert result['status'] == 'budget'
    assert page.evaluate('moves') == 0
    cursor.dispose()
    owner.dispose()
    page.close()


@pytest.mark.parametrize('change', ['owner', 'duplicate_table', 'route'])
def test_cursor_refuses_changed_ownership_before_another_click(context, change):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=250)
    owner = table.element_handle().evaluate_handle("e=>e.closest('p-table')")
    cursor = owner.evaluate_handle(driver.TABLE_CURSOR_INIT_JS)
    mutations = {
        'owner': "const o=document.querySelector('p-table');o.replaceWith(o.cloneNode(true))",
        'duplicate_table': "const t=document.querySelector('table');t.after(t.cloneNode(true))",
        'route': "history.replaceState({},'', '#different-document-route')",
    }
    page.evaluate('()=>{' + mutations[change] + '}')
    result = cursor.evaluate(driver.TABLE_CURSOR_ADVANCE_JS,
                             {'remaining_ms': 10000, 'allow': True})
    assert result['status'] == 'refused'
    assert page.evaluate('moves') == 0
    cursor.dispose()
    owner.dispose()
    page.close()


def test_cursor_full_state_repetition_is_refused_before_accepting_rows(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=250)
    owner = table.element_handle().evaluate_handle("e=>e.closest('p-table')")
    cursor = owner.evaluate_handle(driver.TABLE_CURSOR_INIT_JS)
    assert cursor.evaluate(driver.TABLE_CURSOR_ADVANCE_JS,
                           {'remaining_ms': 10000, 'allow': True})['status'] == 'advanced'
    assert cursor.evaluate(driver.TABLE_CURSOR_POLL_JS) is True
    # A transient changed page is not enough: original page returned before
    # the atomic data/state read must keep the initial verified rows only.
    page.evaluate('at=0;draw()')
    snapshot = owner.evaluate(driver.TABLE_VERIFIED_JS, cursor)
    assert snapshot == {'refusal': 'repeated_state'}
    assert page.evaluate('moves') == 1
    cursor.dispose()
    owner.dispose()
    page.close()


def test_cursor_disposal_does_not_mask_stop_after_pagination(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=250)
    original = JSHandle.dispose
    disposed = []

    def dispose(handle):
        disposed.append(True)
        original(handle)
        raise RuntimeError('synthetic cleanup failure')

    def stop():
        if page.evaluate('moves'):
            raise driver.CaptureCancelled()

    monkeypatch.setattr(JSHandle, 'dispose', dispose)
    with pytest.raises(driver.CaptureCancelled):
        driver.capture_table(page, table, 1, 1000, check_cancel=stop, max_page_size=250)
    assert disposed
    assert page.evaluate('moves') == 1
    page.close()


def test_cursor_deadline_is_not_reset_by_later_advance(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=250)
    owner = table.element_handle().evaluate_handle("e=>e.closest('p-table')")
    cursor = owner.evaluate_handle(driver.TABLE_CURSOR_INIT_JS)
    assert cursor.evaluate(driver.TABLE_CURSOR_ADVANCE_JS,
                           {'remaining_ms': 10000, 'allow': True})['status'] == 'advanced'
    snapshot = owner.evaluate(driver.TABLE_VERIFIED_JS, cursor)
    assert isinstance(snapshot['packed'], str)
    decoded = json.loads(snapshot['packed'])
    assert len(decoded['rows']) == 250
    assert decoded['rows'][0] == ['126', '0']
    cursor.evaluate('c=>{c.deadline=performance.now()-1}')
    assert cursor.evaluate(driver.TABLE_CURSOR_ADVANCE_JS,
                           {'remaining_ms': 100000, 'allow': True})['status'] == 'budget'
    assert page.evaluate('moves') == 1
    cursor.dispose()
    owner.dispose()
    page.close()
