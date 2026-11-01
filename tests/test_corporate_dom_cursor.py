"""Hosted Edge regressions for private exact-state comparison, synthetic only."""
import json

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
