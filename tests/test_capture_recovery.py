"""Real Edge DOM recovery contracts. All traffic is routed synthetic data."""
import pytest
import coretax_browser as driver
from support_isolated_browser import browser as browser, context as context
from test_ppn_capture_readiness import page as page, install
from support_browser_protocol import SourcePage, Table, run_fixture


@pytest.mark.parametrize('kind', ['aria', 'ancestor', 'nested'])
def test_real_disabled_previous_is_never_clicked(page, monkeypatch, tmp_path, kind):
    button='<button class="p-paginator-prev" onclick="window.clicks++">Previous</button>'
    if kind=='aria': button=button.replace('class=', 'aria-disabled="true" class=')
    elif kind=='ancestor': button='<span aria-disabled="true">'+button+'</span>'
    else: button='<p-table>'+button+'</p-table>'
    page.set_content('<p-table id="owner"><table></table><div class="p-paginator">'+button+'</div></p-table><script>window.clicks=0</script>')
    source=SourcePage()
    monkeypatch.setattr(Table,'evaluate_handle',lambda self,script: page.query_selector('#owner'))
    monkeypatch.setattr(driver,'wait_idle',lambda page:None)
    monkeypatch.setattr(driver,'capture_detail',lambda *a,**k:{'sections':[{'name':'Fixture','fields':[],'tables':[]}],'capture_complete':True,'errors':[]})
    # The list source emits a real observer-compatible response; the paginator
    # is a real browser element. Limit the missing-response timeout on RED.
    original_wait=driver.ListObserver.wait
    monkeypatch.setattr(driver.ListObserver,'wait',lambda self,after,timeout=45:original_wait(self,after,timeout=0.1))
    source.wait_for_timeout=lambda ms:page.wait_for_timeout(ms)
    result=driver.collect_details(source,run_fixture(),tmp_path,max_pages=2)
    assert page.evaluate('window.clicks')==0
    assert result['complete'],result['errors']


def test_failed_middle_panel_preserves_later_tab_and_partial(page,monkeypatch):
    # Real Edge round trips for a healthy panel may exceed 50 ms. Retain the
    # strict production deadline tests separately; this fixture tests recovery.
    monkeypatch.setattr(driver,'DETAIL_PANEL_TIMEOUT',2,raising=False)
    install(page,['First','Middle','Last'])
    page.locator('a[aria-controls="panel-1"]').evaluate('(e)=>e.setAttribute("aria-controls","missing")')
    locator_type=type(page.locator('body'))
    original_text=locator_type.inner_text
    def slow_healthy_read(locator,*args,**kwargs):
        text=original_text(locator,*args,**kwargs)
        if text=='First':page.wait_for_timeout(75)
        return text
    monkeypatch.setattr(locator_type,'inner_text',slow_healthy_read)
    result=driver.capture_detail(page)
    assert [s['name'] for s in result['sections']]==['First','Last']
    assert result['capture_complete'] is False
    assert [error['object'] for error in result['errors']]==['Middle']


def test_stop_while_waiting_for_panel_propagates(page,monkeypatch):
    monkeypatch.setattr(driver,'DETAIL_PANEL_TIMEOUT',2,raising=False)
    install(page,['First','Middle','Last'])
    page.locator('a[aria-controls="panel-1"]').evaluate('(e)=>{e.setAttribute("aria-controls","missing");e.onclick=()=>window.middle=true}')
    def cancel():
        if page.evaluate('Boolean(window.middle)'):raise driver.CaptureCancelled()
    with pytest.raises(driver.CaptureCancelled):driver.capture_detail(page,check_cancel=cancel)
