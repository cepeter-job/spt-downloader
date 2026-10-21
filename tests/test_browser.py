"""Local HTML fixtures test the real browser driver; no fixture is used as tax output."""
from pathlib import Path
import sys
import importlib.util
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support_isolated_browser import browser, isolated_context

HTML = '''<div class="main-content"><div class="p-tabview">
<ul class="p-tabview-nav"><li><a role="tab" onclick="show(0)">Induk</a></li><li><a role="tab" onclick="show(1)">Lampiran</a></li></ul>
<div class="p-tabview-panels"><div class="p-tabview-panel" id="panel0"><div class="form-group"><label for="turnover">Peredaran Bruto</label><input id="turnover" formcontrolname="Turnover" disabled value="7.500,00"></div></div>
<div class="p-tabview-panel" id="panel1" hidden><p-table><div class="p-datatable"><table><thead><tr><th>Kode</th><th>Nilai</th></tr></thead><tbody><tr><td>001</td><td><input disabled value="1.000,00"></td></tr><tr><td>001</td><td><input disabled value="1.000,00"></td></tr></tbody></table><div class="p-paginator"><button class="p-paginator-page p-highlight">1</button><button class="p-paginator-next" onclick="this.disabled=true;this.parentNode.querySelector('.p-highlight').textContent='2'">Next</button></div></div></p-table></div></div></div></div>
<script>function show(i){document.querySelectorAll('.p-tabview-panel').forEach((e,j)=>e.hidden=j!==i);}</script>'''


import pytest


@pytest.mark.parametrize('wrapped_panels', [False, True])
def test_driver_captures_tabs_and_all_table_pages_without_deduplication(browser, wrapped_panels):
    assert importlib.util.find_spec('coretax_browser'), 'Browser extractor missing'
    import coretax_browser as driver
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(HTML)
        if wrapped_panels:
            page.evaluate('''() => document.querySelectorAll('.p-tabview-panel').forEach(panel=>{
                let wrapper=document.createElement('p-tabpanel');
                panel.parentNode.insertBefore(wrapper,panel); wrapper.appendChild(panel);
            })''')
        result = driver.capture_detail(page, max_pages=5)
        assert [s['name'] for s in result['sections']] == ['Induk', 'Lampiran']
        field = result['sections'][0]['fields'][0]
        assert field['value'] == '7.500,00'
        assert field['label'] == 'Peredaran Bruto'
        table = result['sections'][1]['tables'][0]
        assert table['headers'] == ['Kode', 'Nilai']
        assert table['rows'] == [['001', '1.000,00']] * 4
        assert table['pages'] == 2
        assert result['capture_complete']


def test_pagination_uses_largest_supported_page_size(browser):
    import coretax_browser as driver
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(HTML)
        page.evaluate('''() => {
          const trigger=document.createElement('div'); trigger.className='p-dropdown-trigger'; trigger.textContent='page size';
          trigger.onclick=()=>{
            let list=document.createElement('ul'); list.className='p-dropdown-items';
            [10,25,50].forEach(n=>{let li=document.createElement('li'); li.textContent=n; li.onclick=()=>{
              document.body.dataset.chosen=String(n); list.remove();
            }; list.appendChild(li);}); document.body.appendChild(list);
          }; document.querySelector('.p-paginator').appendChild(trigger);
        }''')
        result = driver.capture_detail(page, max_pages=5)
        assert page.locator('body').get_attribute('data-chosen') == '50', 'Largest supported UI page size was not selected'
        assert result['capture_complete']


def test_capture_starts_at_first_page_even_if_grid_retained_a_later_page(browser):
    import coretax_browser as driver
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(HTML)
        page.evaluate('''() => {
          const paginator=document.querySelector('.p-paginator');
          const first=document.createElement('button'); first.className='p-paginator-first'; first.textContent='First';
          first.onclick=()=>{paginator.querySelector('.p-highlight').textContent='1'; paginator.querySelector('.p-paginator-next').disabled=false; first.disabled=true;};
          paginator.prepend(first); paginator.querySelector('.p-highlight').textContent='2'; paginator.querySelector('.p-paginator-next').disabled=true;
        }''')
        result=driver.capture_detail(page,max_pages=5)
        assert len(result['sections'][1]['tables'][0]['rows']) == 4, 'Retained later-page state skipped source rows'


def test_readonly_view_opens_return_in_new_tab(browser):
    import coretax_browser as driver
    assert callable(getattr(driver, 'open_return_readonly', None)), 'Read-only return navigation missing'
    target='https://coretax.intranet.pajak.go.id/returnsheets/id-ID/corporate-income-tax-return/fixture-taxpayer/fixture-return/ICT_RCIT/fixture-record'
    with isolated_context(browser) as context:
        page=context.new_page()
        page.route('**/*',lambda route:route.fulfill(body=HTML,content_type='text/html'))
        page.set_content(f'''<div class="main-content"><table><tbody><tr><td><button id="ViewButton" onclick="window.open('{target}')">View</button><button id="Action9" onclick="throw Error('Must not cancel')">Cancel</button></td></tr></tbody></table></div>''')
        context.route('**/*',lambda route:route.fulfill(body=HTML,content_type='text/html'))
        detail,popup=driver.open_return_readonly(page,page.locator('tbody tr').first,'fixture-taxpayer')
        assert popup
        assert detail.url == target


def test_inventory_reads_every_page_and_filters_to_selected_year(browser, tmp_path):
    import coretax_browser as driver
    assert callable(getattr(driver, 'collect_inventory', None)), 'Inventory workflow missing'
    origin='https://coretax.intranet.pajak.go.id'
    taxpayer_id='00000000-0000-0000-0000-000000000001'
    periods=['Januari 2025','Februari 2025','Januari 2026']
    search=f'''<div class="main-content"><input id="ObjectPermitNumber"><table><tbody></tbody></table></div>
    <script>document.querySelector('input').onkeydown=e=>{{if(e.key==='Enter'){{let row=document.createElement('tr'); row.innerHTML='<td>0000000000000001</td><td>Fixture</td><td><button>Pilih</button></td>'; row.querySelector('button').onclick=()=>location.href='{origin}/returnsheets/id-ID/not-submitted-returnsheets/{taxpayer_id}'; document.querySelector('tbody').appendChild(row);}}}};</script>'''
    def listing(submitted):
        endpoint = '/returnsheet/api/returnsheetssubmitted' if submitted else '/returnsheet/api/returnsheetsfixture'
        return f'''<a href="/returnsheets/id-ID/submitted-returnsheets/{taxpayer_id}">SPT Dilaporkan</a><div class="main-content"><h2>Fixture taxpayer</h2>
        <p-table><table><thead><tr><th></th><th>Jenis Pajak</th><th>Masa Pajak</th><th>Model SPT</th></tr></thead><tbody></tbody></table><div class="p-paginator"><button class="p-paginator-page p-highlight">1</button><button class="p-paginator-next" onclick="offset=2;load()">Next</button></div></p-table></div>
        <script>let offset=0; function load(){{fetch('{endpoint}',{{method:'POST',body:JSON.stringify({{TaxpayerAggregateIdentifier:'{taxpayer_id}',First:offset,Rows:2,Filters:[],isArchieved:false,Submitted:{str(submitted).lower()}}})}}).then(r=>r.json()).then(d=>{{document.querySelector('tbody').innerHTML=d.Payload.Data.map(x=>'<tr><td><button id="ViewButton">View</button></td><td>PPh</td><td>'+x.Period+'</td><td>Normal</td></tr>').join(''); document.querySelector('.p-highlight').textContent=offset/2+1;document.querySelector('.p-paginator-next').disabled=offset+d.Payload.Data.length>=d.Payload.TotalRecords;}})}}load();</script>'''
    with isolated_context(browser) as context:
        page=context.new_page()
        def handle(route):
            url=route.request.url
            if '/returnsheet/api/' in url:
                data=route.request.post_data_json
                assert data['TaxpayerAggregateIdentifier'] == taxpayer_id
                rows=[{'RecordId':f'fixture-{i}','Period':period,'TaxpayerAggregateIdentifier':taxpayer_id} for i,period in enumerate(periods)] if data['Submitted'] else []
                route.fulfill(json={'IsSuccessful':True,'Payload':{'TotalRecords':len(rows),'Data':rows[data['First']:data['First']+2]}})
            elif '/taxpayer-search' in url:
                route.fulfill(body=search,content_type='text/html')
            else:
                route.fulfill(body=listing('/not-submitted-' not in url),content_type='text/html')
        page.route('**/*',handle)
        result=driver.collect_inventory(page,'0000000000000001',2025,'period',tmp_path,max_pages=5)
        assert len(result['records']) == 2
        assert result['inventory_complete']
        assert result['audit'][-1]['total'] == 3
        assert result['audit'][-1]['scanned'] == 3
        assert result['audit'][-1]['selected'] == 2


def test_table_source_total_mismatch_is_reported_as_partial(browser):
    import coretax_browser as driver
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(HTML)
        page.evaluate('''() => {let total=document.createElement('span'); total.className='p-paginator-current'; total.textContent='Menampilkan 1 sampai 2 dari 99 entri'; document.querySelector('.p-paginator').appendChild(total);}''')
        result = driver.capture_detail(page, max_pages=5)
        assert not result['capture_complete'], 'Unreconciled source count must not be marked complete'
        assert result['errors']


def test_detail_expands_all_collapsed_accordions(browser):
    import coretax_browser as driver
    fixture = '''<div class="main-content">
    <div class="p-accordion-header"><a aria-expanded="false" onclick="this.setAttribute('aria-expanded','true');document.getElementById('fixture-one').hidden=false">Fixture one</a></div>
    <div id="fixture-one" hidden><label for="value-one">Fixture one value</label><input id="value-one" disabled value="001"></div>
    <div class="p-accordion-header"><a aria-expanded="false" onclick="this.setAttribute('aria-expanded','true');document.getElementById('fixture-two').hidden=false">Fixture two</a></div>
    <div id="fixture-two" hidden><label for="value-two">Fixture two value</label><input id="value-two" disabled value="002"></div>
    </div>'''
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_default_timeout(1500)
        page.set_content(fixture)
        captured = driver.capture_detail(page)
        assert captured['capture_complete'], captured['errors']
        assert [field['value'] for field in captured['sections'][0]['fields']] == ['001', '002']


def test_capture_resets_with_previous_when_first_control_is_absent(browser):
    import coretax_browser as driver
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(HTML)
        page.evaluate('''() => {
          const paginator=document.querySelector('.p-paginator');
          const previous=document.createElement('button'); previous.className='p-paginator-prev'; previous.textContent='Previous';
          previous.onclick=()=>{paginator.querySelector('.p-highlight').textContent='1'; paginator.querySelector('.p-paginator-next').disabled=false; previous.disabled=true;};
          paginator.prepend(previous); paginator.querySelector('.p-highlight').textContent='2'; paginator.querySelector('.p-paginator-next').disabled=true;
        }''')
        captured = driver.capture_detail(page, max_pages=5)
        table = captured['sections'][1]['tables'][0]
        assert table['rows'] == [['001', '1.000,00']] * 4
        assert table['pages'] == 2
        assert captured['capture_complete']


def test_exclusive_accordion_preserves_visible_data_but_reports_partial(browser):
    import coretax_browser as driver
    fixture = '''<div class="main-content">
    <div class="p-accordion-header"><a aria-expanded="false" onclick="showAccordion(this,'fixture-one')">Fixture one</a></div>
    <div class="fixture-content" id="fixture-one" hidden><label for="value-one">Fixture one value</label><input id="value-one" disabled value="001"></div>
    <div class="p-accordion-header"><a aria-expanded="false" onclick="showAccordion(this,'fixture-two')">Fixture two</a></div>
    <div class="fixture-content" id="fixture-two" hidden><label for="value-two">Fixture two value</label><input id="value-two" disabled value="002"></div>
    </div><script>
    function showAccordion(control,id){
      document.querySelectorAll('.p-accordion-header a').forEach(e=>e.setAttribute('aria-expanded','false'));
      document.querySelectorAll('.fixture-content').forEach(e=>e.hidden=true);
      control.setAttribute('aria-expanded','true'); document.getElementById(id).hidden=false;
    }</script>'''
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_content(fixture)
        captured = driver.capture_detail(page)
        assert not captured['capture_complete']
        assert [field['value'] for field in captured['sections'][0]['fields']] == ['002']
        assert any('collapsed' in error['message'] for error in captured['errors'])
