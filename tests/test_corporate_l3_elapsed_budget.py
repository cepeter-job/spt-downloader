"""Large-grid elapsed-budget scaling: synthetic Edge UI only, no live access.

The flat 180 s per-table budget truncated legitimately large L3 grids (live:
60+ server-bound pages at ~20 s each) as PARTIAL with
'Table capture elapsed budget exceeded'. Per-page browser cost is already one
fused owner-bound RPC and is dominated by the server grid fetch, so the host
budget now scales with verified progress and still stops at a hard ceiling.
"""
import pytest

import coretax_browser as driver
from spt_desktop import diagnostics as d
from support_isolated_browser import browser as browser, context as context
from test_corporate_dom_page_size import fixture
from test_diagnostics import records


PAGES = 12
SIZE = 500
SERVER_MS = 120


def slow_pages(page, pages=PAGES):
    """Make every Next click behave like a server-bound grid fetch."""
    page.evaluate('''ms => {
        const next=document.querySelector('.p-paginator-next');
        const draw=window.draw;
        next.onclick=()=>{
            moves++;
            const overlay=document.createElement('div');
            overlay.className='p-datatable-loading-overlay';
            overlay.style.cssText='position:absolute;inset:0;width:40px;height:40px';
            document.querySelector('.p-datatable').append(overlay);
            setTimeout(()=>{at++;draw();overlay.remove();}, ms);
        };
    }''', SERVER_MS)


@pytest.fixture
def page(context):
    owned = context.new_page()
    owned.route('**/*', lambda route: route.abort())
    owned.set_default_timeout(5000)
    return owned


def test_large_multi_page_capture_is_not_truncated_by_the_flat_base_budget(
        page, monkeypatch, tmp_path):
    total = PAGES * SIZE
    table = fixture(page, total=total, selected=SIZE)
    slow_pages(page)
    # A base budget far below the total server-bound page time. Only verified
    # progress may extend it; the pre-fix flat budget stopped after ~2 pages.
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_BUDGET_SECONDS', 0.6)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_PAGE_BUDGET_SECONDS', 0.5)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_MAX_SECONDS', 120)

    with d.session(tmp_path / 'log', 'worker') as log:
        captured = driver.capture_table(page, table, 1, 1000, max_page_size=SIZE)
        assert log.flush()

    assert captured['complete'], captured.get('warning')
    assert captured['pages'] == PAGES
    assert captured['body_row_count'] == total
    assert page.evaluate('moves') == PAGES - 1
    events = [r for r in records(tmp_path / 'log') if r['event'] == 'table.elapsed_budget']
    assert events == []


def test_large_capture_still_stops_at_the_hard_ceiling(page, monkeypatch, tmp_path):
    total = PAGES * SIZE
    table = fixture(page, total=total, selected=SIZE)
    slow_pages(page)
    # Progress may extend the budget, but never past the ceiling.
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_BUDGET_SECONDS', 30)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_PAGE_BUDGET_SECONDS', 30)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_MAX_SECONDS', 0.5)

    with d.session(tmp_path / 'log', 'worker') as log:
        captured = driver.capture_table(page, table, 1, 1000, max_page_size=SIZE)
        assert log.flush()

    assert captured['complete'] is False
    assert captured['warning'] == 'Table capture elapsed budget exceeded'
    assert 1 <= captured['pages'] < PAGES
    # Only verified pages are retained; nothing is invented and the click that
    # was in flight at the ceiling is never retried.
    assert captured['body_row_count'] == captured['pages'] * SIZE
    assert page.evaluate('moves') <= captured['pages']
    events = [r for r in records(tmp_path / 'log') if r['event'] == 'table.elapsed_budget']
    assert len(events) == 1
    assert events[0]['table_elapsed_stage'] in (
        'before_next_click', 'state_poll', 'before_dom_read')
    assert events[0]['pages'] == captured['pages']


def test_stalled_page_mid_grid_still_fails_loudly_without_extra_click(
        page, monkeypatch, tmp_path):
    total = PAGES * SIZE
    table = fixture(page, total=total, selected=SIZE)
    slow_pages(page)
    # Page 3 of the grid never advances again.
    page.evaluate('''() => {
        const next=document.querySelector('.p-paginator-next');
        const slow=next.onclick;
        let clicks=0;
        next.onclick=()=>{if(++clicks>=3){moves++;return;} slow();};
    }''')
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_BUDGET_SECONDS', 2)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_PAGE_BUDGET_SECONDS', 0.4)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_MAX_SECONDS', 120)

    with d.session(tmp_path / 'log', 'worker') as log:
        captured = driver.capture_table(page, table, 1, 1000, max_page_size=SIZE)
        assert log.flush()

    assert captured['complete'] is False
    assert captured['warning'] == 'Table capture elapsed budget exceeded'
    assert captured['pages'] == 3
    assert captured['body_row_count'] == 3 * SIZE
    assert page.evaluate('moves') == 3, 'A stalled page is never retried'
    events = [r for r in records(tmp_path / 'log') if r['event'] == 'table.elapsed_budget']
    assert len(events) == 1
    assert events[0]['table_elapsed_stage'] == 'state_poll'


def test_default_page_allowance_has_headroom_over_measured_live_page_cost():
    """The rolling allowance must exceed a real slow page, not just a fast one.

    Live measurement on a 500-row L3 page (build 2037771): 34.0 s click +
    28.7 s DOM read = 62.7 s. The previous 60 s allowance cut that page off by
    2.7 s and aborted the whole table. Guard the constant against regressing
    back under the observed cost.
    """
    MEASURED_LIVE_PAGE_SECONDS = 62.7
    assert driver.TABLE_CAPTURE_PAGE_BUDGET_SECONDS >= MEASURED_LIVE_PAGE_SECONDS * 1.5, (
        'per-page allowance must keep headroom over the measured live page cost')
    assert driver.TABLE_CAPTURE_PAGE_BUDGET_SECONDS < driver.TABLE_CAPTURE_MAX_SECONDS


def test_slow_page_earns_twice_its_measured_duration(page, monkeypatch, tmp_path):
    """The allowance must track measured page cost, not a fixed constant.

    Live cost on the same 500-row grid swung from 62.7 s (build 2037771) to
    173.9 s (build cb37e3b), so a fixed per-page constant kept needing bumps.
    A page slower than the floor must earn 2x its own duration for the next.
    """
    total = PAGES * SIZE
    table = fixture(page, total=total, selected=SIZE)
    slow_pages(page)
    # Floor far below the real per-page cost: only the 2x-measured rule can
    # carry the capture past the second page.
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_BUDGET_SECONDS', 0.6)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_PAGE_BUDGET_SECONDS', 0.02)
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_MAX_SECONDS', 120)

    with d.session(tmp_path / 'log', 'worker') as log:
        captured = driver.capture_table(page, table, 1, 1000, max_page_size=SIZE)
        assert log.flush()

    assert captured['complete'], captured.get('warning')
    assert captured['pages'] == PAGES
    assert captured['body_row_count'] == total
    events = [r for r in records(tmp_path / 'log') if r['event'] == 'table.elapsed_budget']
    assert events == [], 'adaptive allowance should have covered every page'


def test_overlay_readiness_timeout_has_headroom_over_the_measured_wait():
    """The loading-overlay wait must survive a slow server-bound grid.

    Live L3 table 3 held its overlay past the old hardcoded 45 s and aborted
    the whole panel as capture_timeout. The overlay is still the authoritative
    readiness signal, so the cap must sit well above the observed wait rather
    than being tuned for fast tables.
    """
    MEASURED_OVERLAY_WAIT_SECONDS = 60.7
    assert driver.TABLE_OVERLAY_TIMEOUT_MS >= MEASURED_OVERLAY_WAIT_SECONDS * 1000 * 1.5, (
        'overlay readiness timeout must keep headroom over the measured wait')


def test_cursor_path_overlay_budget_is_threaded_not_hardcoded():
    """The bundled large-table path must use the same overlay budget.

    wait_idle() only runs on the legacy path (cursor is None). The cursor path
    waits inside TABLE_VERIFIED_JS, whose idleDeadline used to be a hardcoded
    performance.now()+45000 -- so raising the Python constant alone left a
    60.7 s overlay still aborting at 45 s on the path the live run actually
    took. The JS must read the budget threaded from TABLE_OVERLAY_TIMEOUT_MS.
    """
    verified = driver.TABLE_VERIFIED_JS
    advance = driver.TABLE_CURSOR_ADVANCE_JS
    assert 'cursor.overlayMs' in verified, 'cursor path must read the threaded budget'
    assert 'performance.now()+45000' not in verified, 'cursor path still hardcodes 45 s'
    assert 'options.overlay_ms' in advance, 'advance must record the host overlay budget'
    # The fallback must be the host constant, not a second literal, and the
    # placeholder must actually have been substituted at import time.
    fallback = str(driver.TABLE_OVERLAY_TIMEOUT_MS)
    assert 'OVERLAY_MS_FALLBACK' not in verified, 'placeholder left unsubstituted'
    assert 'OVERLAY_MS_FALLBACK' not in advance, 'placeholder left unsubstituted'
    assert fallback in verified and fallback in advance, (
        'JS fallback must derive from TABLE_OVERLAY_TIMEOUT_MS')
    assert '45000' not in advance, 'advance still carries the retired 45 s cap'
