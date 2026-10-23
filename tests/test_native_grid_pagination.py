"""Native grid navigation uses guarded owned controls and bounded coverage."""
from itertools import count
from types import SimpleNamespace

import pytest
from playwright.sync_api import TimeoutError as BrowserTimeout

import coretax_browser as driver
import coretax_corporate as native
from support_isolated_browser import browser, context
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
