"""Native grid navigation uses guarded owned controls and bounded coverage."""
from itertools import count
from types import SimpleNamespace

import pytest
from playwright.sync_api import ElementHandle, Locator, TimeoutError as BrowserTimeout

import coretax_browser as driver
import coretax_corporate as native
from support_isolated_browser import browser as browser, context as context
from test_diagnostics import records
from spt_desktop import diagnostics
from test_pagination_actionability import fixture


@pytest.fixture
def page(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    page.set_default_timeout(350)
    return page


@pytest.mark.parametrize('start', [0, 1])
def test_native_grid_uses_inspected_controls_under_pointer_interception(page, start):
    fixture(page, start)
    direction = '.p-paginator-prev' if start else '.p-paginator-next'
    with pytest.raises(BrowserTimeout):
        page.locator(direction).click(timeout=150)
    assert native._turn_grid(page, page.locator('p-table'), 3, None) is True
    assert page.evaluate('moves') == (2 if start else 1)
    assert page.evaluate('at') == 1


@pytest.mark.parametrize('start,expected_resets,expected_advances', [
    (0, 0, 1), (1, 1, 1),
])
def test_native_paginator_timing_is_aggregated_and_preserves_clicks(
        page, tmp_path, start, expected_resets, expected_advances):
    fixture(page, start)
    with diagnostics.session(tmp_path, 'worker') as log:
        assert native._turn_grid(page, page.locator('p-table'), 3, None) is True
        assert log.flush()
    events = [row for row in records(tmp_path)
              if row['event'] == 'native.paginator_timing']
    stages = {row['native_paginator_step']: row for row in events}
    assert len(stages) == len(events)
    assert stages['total']['count'] == 1
    assert stages['other']['count'] == 1
    assert stages['reset_probe']['count'] == 2 + expected_resets
    assert stages['advance_probe']['count'] == expected_advances + 1
    assert stages['advance_click']['count'] == expected_advances
    assert stages['advance_marker_wait']['count'] == expected_advances
    assert stages['advance_overlay_wait']['count'] == expected_advances
    for stage in ('reset_click', 'reset_marker_wait', 'reset_overlay_wait'):
        assert (stages[stage]['count'] if stage in stages else 0) == expected_resets
    assert page.evaluate('moves') == expected_resets + expected_advances
    assert all(type(row['duration_ms']) in (int, float) and row['duration_ms'] >= 0
               and type(row['count']) is int for row in events)
    assert all(set(row).isdisjoint({'url', 'path', 'record_id', 'payload',
                                   'hash', 'marker', 'request_json'}) for row in events)


def test_native_paginator_stop_preserves_exception_and_emits_bounded_timings(
        page, tmp_path):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')

    def stop():
        if page.evaluate('moves'):
            raise driver.CaptureCancelled('SYNTHETIC_PRIVATE_STOP_MARKER')

    with diagnostics.session(tmp_path, 'worker') as log:
        with pytest.raises(driver.CaptureCancelled):
            native._turn_grid(page, page.locator('p-table'), 3, stop)
        assert log.flush()
    assert page.evaluate('moves') == 1
    events = [row for row in records(tmp_path)
              if row['event'] == 'native.paginator_timing']
    assert any(row['native_paginator_step'] == 'total' for row in events)
    assert any(row['native_paginator_step'] == 'advance_marker_wait' for row in events)
    assert 'SYNTHETIC_PRIVATE_STOP_MARKER' not in str(events)


@pytest.mark.parametrize('condition', ['hidden', 'aria-disabled', 'foreign', 'ambiguous'])
def test_native_grid_refuses_hidden_disabled_ambiguous_and_foreign_controls(page, condition):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')
    page.evaluate("""condition => {
        const next = document.querySelector('.p-paginator-next');
        if (condition === 'hidden') next.hidden = true;
        if (condition === 'aria-disabled') next.setAttribute('aria-disabled', 'true');
        if (condition === 'foreign') {
            const foreign = document.createElement('p-table');
            document.querySelector('p-table').append(foreign); foreign.append(next);
        }
        if (condition === 'ambiguous') {
            const extra = next.cloneNode(true); extra.onclick = () => moves++;
            next.parentElement.append(extra);
        }
    }""", condition)
    assert native._turn_grid(page, page.locator('p-table').first, 3, None) is False
    assert page.evaluate('moves') == 0


def test_native_grid_disabled_next_is_a_legitimate_end(page):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')
    page.evaluate('document.querySelector(".p-paginator-next").disabled=true')
    assert native._turn_grid(page, page.locator('p-table'), 3, None) is True
    assert page.evaluate('moves') == 0


def test_native_grid_stalled_reset_does_not_click_repeatedly(page, monkeypatch):
    fixture(page, 1)
    page.locator('#header').evaluate('(e) => e.remove()')
    page.evaluate('noAdvance=true')
    ticks = count(0, 31)
    monkeypatch.setattr(native, 'time', SimpleNamespace(monotonic=lambda: next(ticks)))
    assert native._turn_grid(page, page.locator('p-table'), 3, None) is False
    assert page.evaluate('moves') == 1


def test_native_grid_budget_does_not_open_an_extra_page(page):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')
    assert native._turn_grid(page, page.locator('p-table'), 1, None) is False
    assert page.evaluate('moves') == 0


def test_native_grid_stop_prevents_next_request(page):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')

    def stop():
        if page.evaluate('moves'):
            raise driver.CaptureCancelled('SYNTHETIC STOP AFTER NATIVE PAGE CLICK')

    with pytest.raises(driver.CaptureCancelled):
        native._turn_grid(page, page.locator('p-table'), 3, stop)
    assert page.evaluate('moves') == 1


def test_native_paginator_many_pages_use_one_owned_probe_per_page(page, monkeypatch, tmp_path):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')
    # Ten synthetic pages with repeated body cells: only the paginator marker
    # changes. This is not a test of private values or native packet ownership.
    page.evaluate("""() => {
        window.at = 0; window.moves = 0;
        window.draw = () => {
            document.querySelector('.p-paginator-current').textContent =
                'Showing ' + (at + 1) + ' of 10 entries';
            document.querySelector('.p-paginator-prev').disabled = at === 0;
            document.querySelector('.p-paginator-next').disabled = at === 9;
        };
        document.querySelector('.p-paginator-next').onclick = () => {
            moves++; at++; draw();
        };
        document.querySelector('.p-paginator-prev').onclick = () => {
            moves++; at--; draw();
        };
        draw();
    }""")
    original_count = Locator.count
    count_calls = []

    def tracked_count(locator, *args, **kwargs):
        count_calls.append(True)
        return original_count(locator, *args, **kwargs)

    monkeypatch.setattr(Locator, 'count', tracked_count)
    with diagnostics.session(tmp_path, 'worker') as log:
        assert native._turn_grid(page, page.locator('p-table'), 10, None) is True
        assert log.flush()
    assert page.evaluate('moves') == 9
    assert page.evaluate('at') == 9
    # Previous implementation counted next/previous on *every* page. The
    # optimized path counts only the single initial marker locator.
    assert len(count_calls) == 1
    events = [row for row in records(tmp_path)
              if row['event'] == 'native.paginator_timing']
    stages = {row['native_paginator_step']: row for row in events}
    assert stages['advance_probe']['count'] == 10
    assert stages['advance_click']['count'] == 9
    assert stages['advance_marker_wait']['count'] == 9
    assert stages['advance_overlay_wait']['count'] == 9
    assert stages['reset_probe']['count'] == 2
    assert stages['total']['count'] == 1
    assert len(stages) == len(events)


@pytest.mark.parametrize('mutation', ['changed_marker', 'detached_owner', 'foreign_button'])
def test_native_paginator_refuses_changes_between_owned_probe_and_click(
        page, monkeypatch, mutation):
    fixture(page)
    page.locator('#header').evaluate('(e) => e.remove()')
    original_evaluate = ElementHandle.evaluate
    calls = []

    def mutate_before_click(handle, expression, arg=None):
        if expression == driver.NATIVE_PAGINATOR_CLICK_JS:
            calls.append(True)
            if mutation == 'changed_marker':
                page.evaluate("""() => {
                    document.querySelector('.p-paginator-current').textContent =
                        'Showing unexpected page';
                }""")
            elif mutation == 'detached_owner':
                page.evaluate("document.querySelector('p-table').remove()")
            else:
                page.evaluate("""() => {
                    const foreign = document.createElement('p-table');
                    document.querySelector('p-table').append(foreign);
                    foreign.append(document.querySelector('.p-paginator-next'));
                }""")
        return original_evaluate(handle, expression, arg)

    monkeypatch.setattr(ElementHandle, 'evaluate', mutate_before_click)
    assert native._turn_grid(page, page.locator('p-table'), 3, None) is False
    assert len(calls) == 1
    assert page.evaluate('moves') == 0


def test_native_click_uses_original_inspected_actionability_contract():
    assert driver.PAGINATOR_CLICK_JS in driver.NATIVE_PAGINATOR_CLICK_JS
    assert 'innerText!==marker' in driver.NATIVE_PAGINATOR_CLICK_JS
