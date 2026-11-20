"""Hosted synthetic 500-row First-page pilot safety and RPC count."""
import pytest
from playwright.sync_api import ElementHandle, Error as PlaywrightError

import coretax_browser as driver
from spt_desktop import diagnostics as d
from support_isolated_browser import browser as browser, context as context
from test_corporate_dom_page_size import assert_rows, fixture
from test_diagnostics import records


def test_500_row_absent_first_skips_expensive_lookup_with_atomic_source_proof(
        context, monkeypatch, tmp_path):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=1001, selected=500)
    old_query = ElementHandle.query_selector

    def forbid_extra_first_query(handle, selector):
        if selector == '.p-paginator-first:not([disabled]):not(.p-disabled)':
            pytest.fail('Redundant First lookup despite same-owner absence proof')
        return old_query(handle, selector)

    monkeypatch.setattr(ElementHandle, 'query_selector', forbid_extra_first_query)
    with d.session(tmp_path, 'worker') as log:
        result = driver.capture_table(page, table, 1, 1000, max_page_size=500)
        assert log.flush()

    assert_rows(result, 1001)
    assert page.evaluate('moves') == 2
    steps = [r for r in records(tmp_path)
             if r['event'] == 'table.reset_timing'
             and r['table_reset_step'] == 'first_lookup']
    assert len(steps) == 1
    assert steps[0]['table_first_lookup_source'] == 'pilot_absence'
    assert steps[0]['count'] == 0
    page.close()


def test_500_row_pilot_refuses_first_reenabled_between_proof_and_initial_snapshot(
        context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)
    old_evaluate = ElementHandle.evaluate
    injected = [False]

    def reenable_first_after_pilot(handle, expression, arg=None):
        result = old_evaluate(handle, expression, arg)
        if expression == driver.OWNED_PILOT_LABEL_TEXT_JS and not injected[0]:
            injected[0] = True
            page.evaluate("document.querySelector('.p-paginator-first').disabled=false")
        return result

    monkeypatch.setattr(ElementHandle, 'evaluate', reenable_first_after_pilot)
    with pytest.raises(PlaywrightError, match='First-page pilot proof changed'):
        driver.capture_table(page, table, 1, 1000, max_page_size=500)
    assert injected[0]
    assert page.evaluate('moves') == 0
    page.close()


def test_500_row_positive_first_still_uses_inspected_python_click(
        context, tmp_path):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)
    page.evaluate('at=1;draw()')
    with d.session(tmp_path, 'worker') as log:
        result = driver.capture_table(page, table, 1, 1000, max_page_size=500)
        assert log.flush()
    assert_rows(result, 601)
    assert page.evaluate('moves') == 2  # First reset, then one Next
    steps = [r for r in records(tmp_path)
             if r['event'] == 'table.reset_timing'
             and r['table_reset_step'] == 'first_lookup']
    assert len(steps) == 1
    assert steps[0]['table_first_lookup_source'] == 'owner_query'
    assert steps[0]['count'] == 1
    page.close()


def test_250_cap_keeps_original_first_lookup_method(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=251, selected=250, sizes=(100, 250))
    old_query = ElementHandle.query_selector
    counter = [0]

    def track_query(handle, selector):
        if selector == '.p-paginator-first:not([disabled]):not(.p-disabled)':
            counter[0] += 1
        return old_query(handle, selector)

    monkeypatch.setattr(ElementHandle, 'query_selector', track_query)
    result = driver.capture_table(page, table, 1, 1000, max_page_size=250)
    assert_rows(result, 251)
    assert counter == [1]
    page.close()


def test_new_cursor_diagnostics_are_fixed_category_only(tmp_path):
    # Diagnostic caller values are untrusted: no arbitrary marker/payload can
    # leave the allowlisted log schema or enable additional browser requests.
    with d.session(tmp_path, 'worker') as log:
        d.record('table.existing_rpc_timing',
                 table_existing_rpc_stage='cursor_turn',
                 table_cursor_turn_outcome='PRIVATE_SOURCE_ROW',
                 table_cursor_snapshot_outcome='PRIVATE_BROWSER_STATE',
                 table_first_lookup_source='PRIVATE_SELECTOR',
                 table_ordinal=1, duration_ms=12.5)
        assert log.flush()
    matches = [r for r in records(tmp_path)
               if r['event'] == 'table.existing_rpc_timing']
    assert len(matches) == 1
    assert matches[0]['table_existing_rpc_stage'] == 'cursor_turn'
    assert 'table_cursor_turn_outcome' not in matches[0]
    assert 'table_cursor_snapshot_outcome' not in matches[0]
    assert 'table_first_lookup_source' not in matches[0]
