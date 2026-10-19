"""Real Edge, local synthetic paginator; never access live pages or accounts."""
from itertools import count
from types import SimpleNamespace
import pytest
from playwright.sync_api import sync_playwright, TimeoutError as BrowserTimeout
import coretax_browser as driver


@pytest.fixture
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page()
        page.route('**/*', lambda route: route.abort())
        page.set_default_timeout(350)
        yield page
        browser.close()


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
    draw();</script>""")
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
