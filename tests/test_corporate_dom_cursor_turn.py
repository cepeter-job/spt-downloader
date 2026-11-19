"""Hosted Edge-only guarded 500-row cursor bundling, synthetic data only."""
import pytest
from playwright.sync_api import ElementHandle, JSHandle

import coretax_browser as driver
from spt_desktop import diagnostics as d
from support_isolated_browser import browser as browser, context as context
from test_corporate_dom_page_size import assert_rows, fixture
from test_diagnostics import records


def _count_evaluations(monkeypatch):
    counts = {}
    for kind in (ElementHandle, JSHandle):
        original = kind.evaluate

        def counted(handle, expression, arg=None, *, original=original):
            counts[expression] = counts.get(expression, 0) + 1
            return original(handle, expression, arg)

        monkeypatch.setattr(kind, 'evaluate', counted)
    return counts


def test_500_row_turn_captures_owned_pages_in_one_rpc_each(context, monkeypatch, tmp_path):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=1001, selected=500)
    calls = _count_evaluations(monkeypatch)

    def reject_legacy_click(*_args, **_kwargs):
        pytest.fail('Owned cursor turn must not dispatch a second Python Next click')

    # The large-table owner-bound turn clicks in TABLE_CURSOR_ADVANCE_JS.
    # The Python click helper is reachable only on the cursor=None path.
    monkeypatch.setattr(driver, '_click_table_paginator', reject_legacy_click)
    with d.session(tmp_path, 'worker') as log:
        captured = driver.capture_table(page, table, 1, 1000, max_page_size=500)
        assert log.flush()

    assert_rows(captured, 1001)
    assert captured['pages'] == 3 and page.evaluate('moves') == 2
    assert calls.get(driver.TABLE_CURSOR_TURN_JS) == 3
    assert calls.get(driver.TABLE_CURSOR_ADVANCE_JS, 0) == 0
    assert calls.get(driver.TABLE_CURSOR_POLL_JS, 0) == 0
    assert calls.get(driver.TABLE_VERIFIED_JS, 0) == 0
    timings = [r for r in records(tmp_path)
               if r['event'] == 'table.existing_rpc_timing']
    assert len([r for r in timings if r['table_existing_rpc_stage'] == 'cursor_turn']) == 3
    assert all('row' not in r and 'url' not in r and 'body' not in r for r in timings)
    page.close()


def test_500_row_turn_falls_back_to_existing_poll_when_server_page_is_late(
        context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
      document.querySelector('.p-paginator-next').onclick=()=>{
        moves++;
        setTimeout(()=>{at++;draw();},1100);
      };
    }""")
    calls = _count_evaluations(monkeypatch)

    captured = driver.capture_table(page, table, 1, 1000, max_page_size=500)

    assert_rows(captured, 601)
    assert captured['pages'] == 2 and page.evaluate('moves') == 1
    assert calls.get(driver.TABLE_CURSOR_TURN_JS) == 2
    assert calls.get(driver.TABLE_CURSOR_POLL_JS, 0) >= 1
    assert calls.get(driver.TABLE_VERIFIED_JS, 0) >= 1
    page.close()


def test_500_row_turn_refuses_detached_owner_before_accepting_page(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
      document.querySelector('.p-paginator-next').onclick=()=>{
        moves++;
        setTimeout(()=>document.querySelector('p-table').remove(),60);
      };
    }""")
    captured = driver.capture_table(page, table, 1, 1000, max_page_size=500)

    assert not captured['complete']
    assert captured['pages'] == 1 and captured['body_row_count'] == 500
    assert captured['warning'] == 'Table ownership or uniqueness changed during pagination'
    assert page.evaluate('moves') == 1
    page.close()


def test_500_row_turn_stop_before_accepting_embedded_rows(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)

    def stop():
        if page.evaluate('moves'):
            raise driver.CaptureCancelled('synthetic operator stop')

    with pytest.raises(driver.CaptureCancelled, match='synthetic operator stop'):
        driver.capture_table(page, table, 1, 1000, max_page_size=500,
                             check_cancel=stop)
    assert page.evaluate('moves') == 1
    page.close()


def test_500_row_turn_budget_does_not_click_after_expiry(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_BUDGET_SECONDS', 0)

    captured = driver.capture_table(page, table, 1, 1000, max_page_size=500)

    assert not captured['complete']
    assert captured['warning'] == 'Table capture elapsed budget exceeded'
    assert captured['pages'] == 1 and captured['body_row_count'] == 500
    assert page.evaluate('moves') == 0
    page.close()


def test_500_row_turn_pending_overlay_retains_stop_slice_and_owned_snapshot(
        context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = fixture(page, total=601, selected=500)
    page.evaluate("""() => {
      const overlay=document.createElement('div');
      overlay.className='p-blockui';
      overlay.style='position:fixed;left:0;top:0;width:10px;height:10px';
      document.body.append(overlay);
      const original=document.querySelector('.p-paginator-next').onclick;
      document.querySelector('.p-paginator-next').onclick=(e)=>{
        overlay.style.visibility='visible';
        setTimeout(()=>{overlay.style.visibility='hidden'},1300);
        original.call(e.target,e);
      };
      overlay.style.visibility='hidden';
    }""")
    calls = _count_evaluations(monkeypatch)

    captured = driver.capture_table(page, table, 1, 1000, max_page_size=500)

    assert_rows(captured, 601)
    assert page.evaluate('moves') == 1
    assert calls.get(driver.TABLE_CURSOR_TURN_JS) == 2
    assert calls.get(driver.TABLE_VERIFIED_JS, 0) >= 1
    page.close()
