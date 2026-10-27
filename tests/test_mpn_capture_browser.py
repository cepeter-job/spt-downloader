"""Real Edge UI contracts, entirely synthetic and runner-only."""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import json

import pytest

from support_isolated_browser import browser
from test_mpn import scope_run, payment_source, HEADER
from test_mpn_capture_protocol import snapshot

ORIGIN = 'https://coretax.intranet.pajak.go.id'


@contextmanager
def portal(browser, monkeypatch, *, rounded=False, empty=False, default_stuck=False, foreign=False,
           pending_catalog=False, delayed_mount=False, unrelated_sources=False,
           router_notification=False, grid_after_search=False, delayed_options=False,
           session_redirect=False, withheld_fresh_sources=False, request_language='en-US',
           delayed_page_size=False, tooltip_action=False, delayed_dialog=False):
    import coretax_mpn_ui as ui
    list_headers = ['Aksi', 'Tanggal Transaksi', 'Tanggal Posting', 'Jenis Pencatatan',
        'Detail Jenis Pencatatan', 'Mata Uang', 'Jenis Transaksi', 'Nilai Mata Uang',
        'Nilai Sisa dalam Mata Uang', 'Nilai Tukar', 'Jumlah', 'Nilai Sisa', 'Referensi',
        'KAP', 'Deskripsi KAP', 'KJS', 'Masa Pajak', 'Nomor Transaksi',
        'Tanggal Jatuh Tempo Pembayaran', 'Tanggal Utang Pajak Dapat Ditagih',
        'Tanggal Daluwarsa', 'Dibatalkan', 'NOP', 'Dapat Digunakan']
    detail_headers = ['Tanggal Transaksi', 'Tanggal Posting', 'Nomor Transaksi',
        'Jenis Pencatatan', 'Detail Jenis Pencatatan', 'Nilai Mata Uang',
        'Nilai Tukar Transaksi Induk', 'Jumlah', 'Referensi']
    header, detail = payment_source(amount='-1250.501')
    header.update(Amount=0, CurrencyCode='IDR', RevenueCode='411211', PaymentCode='100',
                  TransactionNumber='SYNTHETIC-PARENT-0007')
    positive = deepcopy(detail)
    positive.update(RecordId='00000000-0000-4000-8000-000000000004')
    from coretax_mpn import MpnNumber
    positive['Amount'] = MpnNumber('40')
    if foreign:
        detail['HeaderRecordId'] = '00000000-0000-4000-8000-000000000099'
    list_raw = snapshot([] if empty else [header])['raw']
    detail_raw = snapshot([positive, detail], kind='detail', parent=HEADER)['raw']
    main = r'''
    let searches=0;
    const head=(table,labels)=>{let tr=document.createElement('tr');for(let label of labels){let th=document.createElement('th');th.textContent=label;tr.append(th);}table.tHead.append(tr);};
    function dropdown(id){const parent=document.getElementById(id);const panel=document.createElement('div');panel.className='p-dropdown-panel';for(const text of ['Yes','No']){let o=document.createElement('div');o.setAttribute('role','option');o.textContent=text;o.onclick=()=>{parent.querySelector('.p-dropdown-label').textContent=text;panel.remove();};panel.append(o);}document.body.append(panel);}
    const number=n=>Number(n).toLocaleString('id-ID',{minimumFractionDigits:2,maximumFractionDigits:ROUNDED?2:3});
    const cells=(tr,values)=>{for(const value of values){let td=document.createElement('td');td.textContent=value;tr.append(td);}};
    const payload=(kind,id,filters)=>({[kind==='list'?'TaxpayerAggregateIdentifier':'RecordId']:id,First:0,Rows:10,SortField:kind==='list'?'PostingDate':'TransactionDate',SortOrder:-1,LanguageId:LANGUAGE,Filters:filters});
    async function loadList(){searches++;const filters=[{PropertyName:'IsCancelled',Value:'0',MatchMode:'equals',CaseSensitive:true,AsString:false}];if(searches<=2||STUCK)filters.push({PropertyName:'TransactionDate',Value:['2026/09/01','2026/10/26'],MatchMode:'between'});const response=await fetch('/accounting/api/taxpayeraccounting/list',{method:'POST',body:JSON.stringify(payload('list',TAXPAYER,filters))});const body=await response.json();const table=document.querySelector('acc-balance-sheet-light-grid table');table.tBodies[0].replaceChildren();for(const row of body.Payload.Data){const tr=document.createElement('tr');const td=document.createElement('td');const button=document.createElement('button');button.title='Detail Transaksi';button.innerHTML='<span class="pi pi-list"></span>';button.onclick=()=>detail(row.RecordId);td.append(button);tr.append(td);cells(tr,['01-02-2026','01-02-2026','OtherTaxReturn','DBP',row.CurrencyCode,'Kredit','0','0','1','0','0','SYNTHETIC REF',row.RevenueCode,'SYNTHETIC KAP',row.PaymentCode,row.PeriodCode,row.TransactionNumber,'','','','','','']);table.tBodies[0].append(tr);}}
    async function detail(id){const host=document.getElementById('isShowDetail');host.style.display='block';const response=await fetch('/accounting/api/taxpayeraccounting/listdetail',{method:'POST',body:JSON.stringify(payload('detail',id,[]))});const body=await response.json();const table=host.querySelector('table');table.tBodies[0].replaceChildren();for(const row of body.Payload.Data){let tr=document.createElement('tr');cells(tr,['01-02-2026','01-02-2026',row.TransactionNumber,row.AccountingTypeCode,row.AccountingTypeDetailCode,number(row.CurrencyAmount),number(row.HeaderExchangeRate),number(row.Amount),row.ReferenceNumber]);table.tBodies[0].append(tr);}}
    document.addEventListener('DOMContentLoaded',()=>{head(document.querySelector('acc-balance-sheet-light-grid table'),LISTHEAD);head(document.querySelector('#isShowDetail table'),DETAILHEAD);document.querySelector('form').onsubmit=e=>{e.preventDefault();loadList();};for(const id of ['ShowZeroValue','ShowCancelledTransaction'])document.querySelector('#'+id+' .p-dropdown-trigger').onclick=()=>dropdown(id);document.querySelector('.p-dialog-header-close').onclick=()=>document.getElementById('isShowDetail').style.display='none';loadList();if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);});
    '''
    if tooltip_action:
        main = main.replace("button.title='Detail Transaksi';", "button.type='button';button.id='ViewButton';")
    if delayed_dialog:
        main = main.replace("host.style.display='block';", "setTimeout(()=>host.style.display='block',250);")
    if delayed_page_size:
        main = 'let selectedSize=10;' + main.replace('Rows:10,SortField:', 'Rows:selectedSize,SortField:')
        main = main.replace('async function loadList(){searches++;',
            "async function loadList(){searches++;const trigger=document.querySelector('.p-paginator .p-dropdown-trigger');"
            "trigger.disabled=true;setTimeout(()=>trigger.disabled=false,1200);")
        main = main.replace("document.addEventListener('DOMContentLoaded',()=>{",
            "document.addEventListener('DOMContentLoaded',()=>{"
            "document.querySelector('.p-paginator .p-dropdown-trigger').onclick=()=>{"
            "const panel=document.createElement('div');panel.className='p-dropdown-panel';"
            "for(const size of [10,25,50]){const option=document.createElement('div');"
            "option.setAttribute('role','option');option.textContent=String(size);"
            "option.onclick=()=>{selectedSize=size;document.querySelector('.p-paginator .p-dropdown-label').textContent=String(size);panel.remove();loadList();};"
            "panel.append(option);}setTimeout(()=>document.body.append(panel),250);};")
    if grid_after_search:
        main = main.replace('async function loadList(){searches++;',
            "async function loadList(){if(!document.querySelector('acc-balance-sheet-light-grid')){"
            "await new Promise(resolve=>setTimeout(resolve,250));document.querySelector('form').after(savedGrid);}searches++;")
        main = 'let savedGrid;' + main.replace(
            'loadList();if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);',
            "savedGrid=document.querySelector('acc-balance-sheet-light-grid');savedGrid.remove();if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);")
        # The real grid is first created by Cari, so only that search gets the default date filter.
        main = main.replace('searches<=2||STUCK', 'searches<=1||STUCK')
    if delayed_options:
        main = main.replace('document.body.append(panel);', 'setTimeout(()=>document.body.append(panel),250);')
    if router_notification:
        main = main.replace("document.addEventListener('DOMContentLoaded',()=>{",
            "document.addEventListener('DOMContentLoaded',()=>{history.replaceState(null,'',location.href);")
    if delayed_mount:
        main = main.replace("document.addEventListener('DOMContentLoaded',()=>{",
                            'const initialize=()=>{').replace(
            'loadList();if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);});',
            "loadList();if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);};"
            "document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{"
            "document.body.append(document.getElementById('late-owner').content.cloneNode(true));"
            "initialize();},250));")
    reference_path = ('/referencedata/api/currentreferencedata/id-ID/'
        'ACCOUNTING_TYPE,ACCOUNTING_TYPE_DETAIL,REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT,PERIOD')
    if unrelated_sources:
        main = main.replace('loadList();if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);',
            "loadList();fetch('/accounting/id-ID/main.synthetic.js');fetch("
            + json.dumps(reference_path) + ",{method:'POST'});if(PENDING_REFERENCE)fetch(PENDING_REFERENCE);")
    main = ('const LANGUAGE=' + json.dumps(request_language) + ';const PENDING_REFERENCE=' + json.dumps(reference_path if pending_catalog else '') + ';'
            + 'const TAXPAYER=' + json.dumps(scope_run()['sources'][0]['url'].rsplit('/', 1)[-1]) + ';'
            + 'const LISTHEAD=' + json.dumps(list_headers) + ';const DETAILHEAD=' + json.dumps(detail_headers) + ';'
            + 'const ROUNDED=' + json.dumps(rounded) + ';const STUCK=' + json.dumps(default_stuck) + ';' + main).encode()
    vendor = b'/* Synthetic vendor only; no portal source or taxpayer data. */'
    pins = {'/accounting/id-ID/main.synthetic.js': hashlib.sha256(main).hexdigest(),
            '/accounting/id-ID/vendor.synthetic.js': hashlib.sha256(vendor).hexdigest()}
    monkeypatch.setattr(ui, 'SOURCE_PINS', pins)
    html = '''<!doctype html><html lang="id-ID"><head>
      <script defer src="/accounting/id-ID/main.synthetic.js"></script>
      <script defer src="/accounting/id-ID/vendor.synthetic.js"></script></head><body>
      <acc-balance-sheet-light><form>
      <ui-dropdown id="ShowZeroValue"><span class="p-dropdown-label">No</span><button type="button" class="p-dropdown-trigger">Open</button></ui-dropdown>
      <ui-dropdown id="ShowCancelledTransaction"><span class="p-dropdown-label">No</span><button type="button" class="p-dropdown-trigger">Open</button></ui-dropdown>
      <button id="submit" type="submit">Cari</button></form>
      <acc-balance-sheet-light-grid><ui-grid><p-table><table><thead></thead><tbody></tbody></table></p-table></ui-grid></acc-balance-sheet-light-grid>
      <p-dialog id="isShowDetail" style="display:none"><div role="dialog"><span class="p-dialog-title">Detail Transaksi</span><button class="p-dialog-header-close">Close</button><ui-grid><p-table><table><thead></thead><tbody></tbody></table></p-table></ui-grid></div></p-dialog>
      </acc-balance-sheet-light></body></html>'''
    if delayed_page_size:
        html = html.replace('</table></p-table>', '</table><div class="p-paginator">'
            '<span class="p-dropdown-label">10</span><button type="button" class="p-dropdown-trigger">Size</button>'
            '</div></p-table>', 1)
    if delayed_mount:
        html = html.replace('<body>', '<body><template id="late-owner">').replace(
            '</body>', '</template></body>')
    metrics = {'list': [], 'detail': [], 'unknown': 0, 'references': [], 'unrelated': [], 'documents': 0, 'initiations': 0}
    context = browser.new_context(service_workers='block', locale='id-ID', timezone_id='Asia/Jakarta',
                                   viewport={'width': 1600, 'height': 1000})
    context._spt_financial_route_policy = 'service_workers_blocked'
    page = context.new_page()
    original_goto = page.goto
    def goto(*args, **kwargs):
        metrics['initiations'] += 1
        return original_goto(*args, **kwargs)
    monkeypatch.setattr(page, 'goto', goto)
    def route(request_route):
        request = request_route.request
        path = request.url.removeprefix(ORIGIN)
        if path == '/accounting/id-ID/balancesheet/' + scope_run()['sources'][0]['url'].rsplit('/', 1)[-1]:
            metrics['documents'] += 1
            if session_redirect and (metrics['documents'] == 1 or session_redirect == 'recurs' and metrics['documents'] == 3):
                request_route.fulfill(body="<script>location.replace('/accounting/id-ID/')</script>", content_type='text/html')
            else:
                request_route.fulfill(body=html, content_type='text/html')
        elif session_redirect and path == '/accounting/id-ID/':
            request_route.fulfill(body="<script>location.replace('/accounting/id-ID/auth-callback?code=SYNTHETIC')</script>", content_type='text/html')
        elif session_redirect and path == '/accounting/id-ID/auth-callback?code=SYNTHETIC':
            target = '/accounting/id-ID/balancesheet/' + scope_run()['sources'][0]['url'].rsplit('/', 1)[-1]
            request_route.fulfill(body="<script>history.replaceState({},'','/');location.replace(" + json.dumps(target) + ")</script>", content_type='text/html')
        elif path in pins:
            if withheld_fresh_sources and metrics['documents'] > 1:
                request_route.fulfill(status=404, body='Synthetic absent provider', content_type='text/plain')
                return
            if request.resource_type != 'script':
                metrics['unrelated'].append(request.resource_type)
            request_route.fulfill(body=main if 'main.' in path else vendor, content_type='application/javascript')
        elif path == '/accounting/api/taxpayeraccounting/list':
            metrics['list'].append(request.post_data_json)
            request_route.fulfill(body=list_raw, content_type='application/json')
        elif path == '/accounting/api/taxpayeraccounting/listdetail':
            metrics['detail'].append(request.post_data_json)
            request_route.fulfill(body=detail_raw, content_type='application/json')
        elif path == reference_path and pending_catalog:
            metrics['references'].append(request_route)  # Intentionally unresolved dependency.
        elif path == reference_path and unrelated_sources and request.method == 'POST':
            metrics['unrelated'].append('POST')
            request_route.fulfill(body=b'{}', content_type='application/json')
        else:
            metrics['unknown'] += 1
            request_route.abort()
    page.route('**/*', route)
    try:
        yield page, metrics
    finally:
        context.close()


@pytest.mark.parametrize('rounded,expected', [(False, 'dom'), (True, 'json')])
def test_real_ui_uses_full_dom_or_whole_detail_json_without_losing_source_precision(browser, tmp_path, monkeypatch, rounded, expected):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, rounded=rounded) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert run['mpn']['rows'][0]['source'] == expected
        assert run['mpn']['rows'][0]['amount'] == '-1250.501'
        assert len(metrics['detail']) == 1
        assert len(metrics['list']) == 4 and metrics['unknown'] == 0
        assert [f['PropertyName'] for f in metrics['list'][-1]['Filters']] == ['IsCancelled']


def test_real_empty_inventory_can_complete_only_after_unfiltered_owned_response(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, empty=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['mpn']['status'] == 'COMPLETE' and run['mpn']['rows'] == []
        assert metrics['detail'] == [] and metrics['unknown'] == 0


def test_nonqualifying_asset_observations_do_not_abort_a_verified_real_capture(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, unrelated_sources=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert sorted(metrics['unrelated']) == ['POST', 'POST', 'fetch', 'fetch']
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


def test_stuck_default_date_filter_never_certifies_empty_or_complete_mpn(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, default_stuck=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert not run['complete'] and run['mpn']['status'] == 'PARTIAL'
        assert metrics['detail'] == []


def test_real_foreign_detail_parent_is_fatal_before_fallback(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    from coretax_mpn import MpnSafetyError
    with portal(browser, monkeypatch, foreign=True) as (page, metrics):
        run = scope_run()
        with pytest.raises(MpnSafetyError):
            collect_mpn(page, run, tmp_path)
        assert not run['complete'] and run['mpn']['status'] != 'COMPLETE'


def test_pending_admitted_reference_cannot_become_complete_at_final_sampling(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, pending_catalog=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert len(metrics['references']) == 2
        assert not run['complete'] and run['mpn']['status'] == 'PARTIAL'


@pytest.mark.parametrize('mode', ['dom', 'json-first'])
def test_unsupported_detail_dom_uses_complete_original_json_through_real_dialog(browser, tmp_path, monkeypatch, mode):
    from coretax_mpn_browser import collect_mpn
    from coretax_mpn import MpnUnsupported
    import coretax_mpn_ui as ui
    original = ui.AccountingUI._table
    rejected = []
    def table(self, owner, headers, count):
        if headers == ui.DETAIL_HEADERS:
            rejected.append(True)
            raise MpnUnsupported('Synthetic incomplete DOM table')
        return original(self, owner, headers, count)
    monkeypatch.setattr(ui.AccountingUI, '_table', table)
    with portal(browser, monkeypatch) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path, detail_source=mode)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert run['mpn']['rows'][0]['source'] == 'json'
        assert run['mpn']['rows'][0]['amount'] == '-1250.501'
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0
        assert rejected if mode == 'dom' else not rejected


def test_accounting_owner_may_mount_after_document_ready(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, delayed_mount=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert run['mpn']['rows'][0]['amount'] == '-1250.501'
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


@pytest.mark.parametrize('case', ['router_notification', 'grid_after_search', 'delayed_options', 'session_redirect'])
def test_accounting_preparation_follows_owned_async_ui(browser, tmp_path, monkeypatch, case):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, **{case: True}) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


@pytest.mark.parametrize('language', ['en-US', 'id-ID'])
def test_full_session_and_asynchronous_real_ui_branch_share_one_complete_capture(browser, tmp_path, monkeypatch, language):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, session_redirect=True, router_notification=True,
                grid_after_search=True, delayed_options=True, request_language=language) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert metrics['documents'] == 3  # session entry, post-callback ledger, fresh owned capture
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


def test_preparation_provider_bytes_cannot_supply_missing_fresh_capture_proof(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, withheld_fresh_sources=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert not run['complete'] and run['mpn']['status'] == 'PARTIAL'
        assert run['mpn']['source_pins'] == {} and run['mpn']['evidence'] == []
        assert metrics['documents'] == 2 and metrics['detail'] == []


def test_session_redirect_during_fresh_capture_remains_fatal_without_retry(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    from coretax_mpn import MpnSafetyError
    with portal(browser, monkeypatch, session_redirect='recurs') as (page, metrics):
        run = scope_run()
        with pytest.raises(MpnSafetyError):
            collect_mpn(page, run, tmp_path)
        assert not run['complete'] and run['mpn']['status'] == 'PARTIAL'
        assert metrics['documents'] in (3, 4) and metrics['detail'] == []
        assert metrics['initiations'] == 2  # Only session preparation and fresh capture; no retry.


def test_owned_capture_keeps_original_size_without_touching_unready_optional_size_control(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, delayed_page_size=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert {request['Rows'] for request in metrics['list']} == {10}
        assert page.locator('.p-dropdown-panel').count() == 0
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


def test_pinned_source_named_detail_action_does_not_require_html_title(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, tooltip_action=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


@pytest.mark.parametrize('attribute,value', [('id','DeleteButton'), ('title','Ubah'), ('aria-label','Hapus')])
def test_source_named_detail_action_rejects_contradictory_metadata(browser, tmp_path, monkeypatch, attribute, value):
    from coretax_mpn_browser import collect_mpn
    import coretax_mpn_ui as module
    original = module.AccountingUI._bind_header
    with portal(browser, monkeypatch, tooltip_action=True) as (page, metrics):
        def bind(self, header):
            self.list_owner.locator('button#ViewButton').evaluate(
                '(button, pair) => button.setAttribute(pair[0],pair[1])', [attribute,value])
            return original(self, header)
        monkeypatch.setattr(module.AccountingUI, '_bind_header', bind)
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert not run['complete'] and run['mpn']['status'] == 'PARTIAL'
        assert metrics['detail'] == []


def test_owned_detail_dialog_may_mount_after_its_original_response(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, tooltip_action=True, delayed_dialog=True) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert len(metrics['detail']) == 1 and metrics['unknown'] == 0


def test_owned_catalog_can_finish_before_first_parent_binding_and_is_retained(browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    from coretax_mpn import mpn_custody
    import coretax_mpn_ui as module
    original = module.AccountingUI._table
    with portal(browser, monkeypatch, pending_catalog=True) as (page, metrics):
        served = []
        def table(self, owner, headers, count):
            result = original(self, owner, headers, count)
            if headers == module.LIST_HEADERS and not served:
                served.append(True)
                metrics['references'][-1].fulfill(content_type='application/json',body=json.dumps({
                    'IsSuccessful':True,'Payload':[{'ReferenceDataType':name,'Checksum':'synthetic-version','Details':[]}
                    for name in ('ACCOUNTING_TYPE','ACCOUNTING_TYPE_DETAIL','REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT','PERIOD')]}))
            return result
        monkeypatch.setattr(module.AccountingUI, '_table', table)
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['complete'] and run['mpn']['status'] == 'COMPLETE'
        assert sum(binding['kind']=='catalog' for binding in run['mpn']['bindings']) == 1
        with mpn_custody(run,tmp_path):
            pass
