"""Real Edge, local synthetic paginator; never access live pages or accounts."""
from itertools import count
from types import SimpleNamespace
import pytest
from playwright.sync_api import TimeoutError as BrowserTimeout
from support_isolated_browser import browser as browser, context as context
import coretax_browser as driver


@pytest.fixture
def page(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    page.set_default_timeout(350)
    return page


def fixture(page, start=0):
    page.set_content("""<p-table><div class="p-datatable">
    <table><thead><tr><th>Value</th></tr></thead><tbody></tbody></table>
    <div class="p-paginator"><button class="p-paginator-prev" type="button">Prev</button>
    <span class="p-paginator-page p-highlight"></span>
    <button class="p-paginator-next" type="button">Next</button>
    <span class="p-paginator-current"></span></div></div></p-table>
    <div id="header" style="position:fixed;inset:0;background:transparent;z-index:999"></div>
    <script>
    window.at=0;window.moves=0;window.noAdvance=false;
    window.draw=()=>{document.querySelector('tbody').innerHTML='<tr><td>SAME VALUE</td></tr>';
      document.querySelector('.p-highlight').textContent=String(at+1);
      document.querySelector('.p-paginator-prev').disabled=at===0;
      document.querySelector('.p-paginator-next').disabled=at===1;
      document.querySelector('.p-paginator-current').textContent='Showing '+(at+1)+' of 2 entries';};
    document.querySelector('.p-paginator-prev').onclick=()=>{moves++;if(!noAdvance){at--;draw();}};
    document.querySelector('.p-paginator-next').onclick=()=>{moves++;if(!noAdvance){at++;draw();}};
    draw();</script>""", timeout=10000, wait_until="domcontentloaded")
    page.evaluate('(start)=>{at=start;draw();}', start)
    return page.locator('table')


@pytest.mark.parametrize('start', [0, 1])
def test_readonly_pagination_survives_pointer_interception_and_keeps_duplicate_rows(page, start):
    table = fixture(page, start)
    direction = '.p-paginator-prev' if start else '.p-paginator-next'
    with pytest.raises(BrowserTimeout):
        page.locator(direction).click(timeout=150)
    result = driver.capture_table(page, table, 1, max_pages=3)
    assert result['complete'] and result['pages'] == 2
    assert result['body_row_count'] == result['source_total'] == 2
    assert result['rows'] == [['SAME VALUE'], ['SAME VALUE']]
    assert page.evaluate('moves') == (2 if start else 1)


@pytest.mark.parametrize('attribute', ["e.hidden=true", "e.setAttribute('aria-disabled','true')"])
def test_hidden_or_aria_disabled_controls_are_never_programmatically_clicked(page, attribute):
    table = fixture(page)
    page.evaluate('(code)=>{const e=document.querySelector(".p-paginator-next");'+attribute+';}')
    with pytest.raises(RuntimeError, match='pagination control'):
        driver.capture_table(page, table, 1, max_pages=3)
    assert page.evaluate('moves') == 0


def test_no_advance_is_partial_not_a_success_after_dom_click(page, monkeypatch):
    table = fixture(page)
    page.evaluate('noAdvance=true')
    ticks=count(0,31)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: next(ticks)))
    result=driver.capture_table(page, table, 1, max_pages=3)
    assert not result['complete'] and result['pages']==1
    assert page.evaluate('moves')==1


def test_page_limit_and_stop_never_click_an_extra_page(page):
    table=fixture(page)
    result=driver.capture_table(page,table,1,max_pages=1)
    assert not result['complete'] and page.evaluate('moves')==0
    def stop():raise driver.CaptureCancelled('synthetic stop')
    with pytest.raises(driver.CaptureCancelled):
        driver.capture_table(page,table,1,max_pages=3,check_cancel=stop)
    assert page.evaluate('moves')==0



def test_nested_foreign_paginator_is_not_clicked_for_parent_table(page):
    table=fixture(page)
    page.evaluate("""() => {
        const foreign=document.createElement('p-table');
        foreign.innerHTML='<button class="p-paginator-next" type="button" onclick="moves++">Foreign</button>';
        document.querySelector('p-table').prepend(foreign);
    }""")
    with pytest.raises(RuntimeError,match='pagination control'):
        driver.capture_table(page,table,1,max_pages=3)
    assert page.evaluate('moves')==0


def test_stop_during_state_wait_is_not_converted_to_partial_return(page):
    table=fixture(page)
    page.evaluate('noAdvance=true')
    def stop_after_click():
        if page.evaluate('moves'):
            raise driver.CaptureCancelled('synthetic stop')
    with pytest.raises(driver.CaptureCancelled):
        driver.capture_table(page,table,1,max_pages=3,check_cancel=stop_after_click)
    assert page.evaluate('moves')==1


@pytest.mark.parametrize('selected', [10, 100])
def test_maximum_page_size_does_not_reload_an_already_selected_size(page, selected):
    table = fixture(page)
    page.evaluate('''selected => {
        window.sizeChanges = 0;
        const picker = document.createElement('div');
        picker.className = 'p-paginator-rpp-options';
        picker.innerHTML = '<span class="p-dropdown-label">'+selected+'</span>' +
            '<button class="p-dropdown-trigger" type="button">Size</button>';
        const options = document.createElement('ul');
        options.className = 'p-dropdown-items'; options.hidden = true;
        options.innerHTML = '<li>10</li><li>100</li>';
        picker.querySelector('button').onclick = () => options.hidden = false;
        options.querySelectorAll('li').forEach(option => option.onclick = () => {
            sizeChanges++; picker.querySelector('span').textContent = option.textContent;
            options.hidden = true;
        });
        document.addEventListener('keydown', event => {if(event.key==='Escape') options.hidden=true;});
        document.querySelector('.p-paginator').append(picker);
        document.body.append(options);
    }''', selected)
    result = driver.capture_table(page, table, 1, max_pages=3)
    assert result['complete'] and result['body_row_count'] == 2
    assert result['rows'] == [['SAME VALUE'], ['SAME VALUE']]
    assert page.evaluate('sizeChanges') == (0 if selected == 100 else 1)
    assert page.locator('.p-dropdown-items').is_hidden()


def test_elapsed_table_budget_stops_next_click_and_preserves_partial_warning(
        page, monkeypatch, tmp_path):
    from spt_desktop import diagnostics
    from test_diagnostics import records
    table = fixture(page)
    ticks = count(0, driver.TABLE_CAPTURE_BUDGET_SECONDS + 1)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: next(ticks)))
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        result = driver.capture_table(page, table, 1, max_pages=1000)
        assert log.flush()
    assert result['complete'] is False
    assert result['pages'] == 1
    assert result['warning'] == 'Table capture elapsed budget exceeded'
    assert page.evaluate('moves') == 0
    events = [e for e in records(tmp_path / 'log')
              if e['event'] == 'table.elapsed_budget']
    assert len(events) == 1
    assert events[0]['table_elapsed_stage'] == 'before_next_click'
    assert events[0]['pages'] == 1


def test_stop_remains_prioritized_over_expired_elapsed_budget(page, monkeypatch):
    table = fixture(page)
    ticks = count(0, driver.TABLE_CAPTURE_BUDGET_SECONDS + 1)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: next(ticks)))
    calls = []
    def stop():
        calls.append(True)
        if len(calls) == 2:
            raise driver.CaptureCancelled('synthetic stop')
    with pytest.raises(driver.CaptureCancelled):
        driver.capture_table(page, table, 1, max_pages=1000, check_cancel=stop)
    assert page.evaluate('moves') == 0


def test_stalled_page_reaching_total_elapsed_budget_retains_original_rows(
        page, monkeypatch, tmp_path):
    from spt_desktop import diagnostics
    from test_diagnostics import records
    table = fixture(page)
    page.evaluate('noAdvance=true')
    ticks = count(0, 60)
    monkeypatch.setattr(driver, 'time', SimpleNamespace(monotonic=lambda: next(ticks)))
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        result = driver.capture_table(page, table, 1, max_pages=1000)
        assert log.flush()
    assert result['complete'] is False
    assert result['warning'] == 'Table capture elapsed budget exceeded'
    assert result['pages'] == 1
    assert result['body_row_count'] == 1
    assert page.evaluate('moves') == 1, 'Never retry a dispatched paginator click'
    events = [e for e in records(tmp_path / 'log')
              if e['event'] == 'table.elapsed_budget']
    assert len(events) == 1
    assert events[0]['table_elapsed_stage'] == 'state_poll'


def test_post_pagination_dom_read_timeout_retains_verified_rows_without_retry(
        page, monkeypatch, tmp_path):
    from spt_desktop import diagnostics
    from test_diagnostics import records
    from playwright.sync_api import ElementHandle
    table = fixture(page)
    original_evaluate = ElementHandle.evaluate
    calls = []

    def fail_owned_snapshot(handle, expression, arg=None):
        if expression == driver.TABLE_VERIFIED_JS:
            calls.append(expression)
            raise BrowserTimeout('SYNTHETIC_PRIVATE_DOM_READ')
        return original_evaluate(handle, expression, arg)

    monkeypatch.setattr(ElementHandle, 'evaluate', fail_owned_snapshot)
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        result = driver.capture_table(page, table, 1, max_pages=3)
        assert log.flush()
    assert result['complete'] is False
    assert result['pages'] == 1
    assert result['body_row_count'] == 1
    assert result['warning'] == 'Table DOM read timed out after pagination'
    assert page.evaluate('moves') == 1
    assert calls == [driver.TABLE_VERIFIED_JS]
    events = [e for e in records(tmp_path / 'log')
              if e['event'] == 'table.dom_read_failed']
    assert len(events) == 1
    assert events[0]['table_dom_stage'] == 'post_pagination'
    assert events[0]['pages'] == 1
    assert events[0]['error']['type'] == 'TimeoutError'
    assert 'SYNTHETIC_PRIVATE_DOM_READ' not in str(events)
