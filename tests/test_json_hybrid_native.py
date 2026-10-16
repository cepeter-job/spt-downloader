"""Real Edge native-bridge contracts; every byte/identifier is synthetic.

A tiny fixture build replaces only the approved public asset digest, so actual
asset-byte version checking remains exercised without shipping portal code.
All business routes are fulfilled locally; unlisted routes are aborted.
"""
from copy import deepcopy
import hashlib
import html
import inspect
import json

import pytest
from playwright.sync_api import sync_playwright

import coretax_browser as driver
import support_json_corpus as corpus
import support_financial_browser as financial

ASSET = corpus.ORIGIN + '/returnsheets/id-ID/525.ec1edffbb4a91d20.js'
BUILD = b'/* SYNTHETIC CORPORATE BUILD -- no portal code or taxpayer data */'
PDF_URL = corpus.ORIGIN + '/synthetic-existing/statement.pdf'
GROUPS = ((1, 'Group 1'), (1, 'Group 2'), (1, 'Group 3'), (1, 'Group 4'), (1, 'Other Group'),
          (2, 'Permanent'), (2, 'Non-permanent'),
          (3, 'Group 1'), (3, 'Group 2'), (3, 'Group 3'), (3, 'Group 4'), (3, 'Other Group'))


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(channel='msedge', headless=True)
        yield instance
        instance.close()


def native_collector():
    parameter = inspect.signature(driver.collect_details).parameters.get('detail_source')
    assert parameter is not None, 'Native hybrid mode is missing: intentional feature RED'
    assert parameter.default == 'dom'
    assert callable(getattr(driver, 'observe_corporate_forms', None)), 'Native DOM binding producer is missing'
    return driver.collect_details


class NativeFixture:
    def __init__(self, browser, tmp_path, monkeypatch, *, popup=True, groups=False,
                 extra_form=None, changed_build=False):
        self.folder = tmp_path
        self.popup = popup
        self.groups = groups
        self.extra_form = extra_form
        self.pdf_available = True
        self.requests = []
        self.unexpected = []
        self.context = browser.new_context()
        self.page = self.context.new_page()
        self.record = deepcopy(corpus.selected_record())
        self.record.update(key='synthetic-native-record', list_page=1, list_page_size=None, sections=[])
        self.run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
                    'inventory_complete': True, 'errors': [], 'records': [self.record]}
        form = corpus.current_form()
        if groups:
            form.update(ListOfIncomeSubjectToFinalTaxAndNonTaxableObject=[],
                        RecapitulationFiscalDepreciationAmortization=[], DeclarationTransactionRelatedParties=[])
        self.raw = corpus.primary(form)['body']
        self.build = BUILD + (b'/* CHANGED */' if changed_build else b'')
        monkeypatch.setattr(driver, 'CIT_SOURCE_SHA256', hashlib.sha256(BUILD).hexdigest(), raising=False)
        self.context.route('**/*', self.route)

    def close(self):
        self.context.close()

    def route(self, route):
        request = route.request
        url = request.url
        self.requests.append({'url': url, 'method': request.method,
                              'body': request.post_data_json if request.method == 'POST' else None})
        if url == corpus.LIST_URL:
            route.fulfill(content_type='text/html', body=self.list_html())
        elif url == corpus.FRAME_URL:
            route.fulfill(content_type='text/html', body=self.detail_html())
        elif url == ASSET:
            route.fulfill(content_type='application/javascript', body=self.build)
        elif url == corpus.ORIGIN + '/returnsheet/api/returnsheetssubmitted':
            assert request.method == 'POST'
            route.fulfill(content_type='application/json', body=json.dumps({
                'IsSuccessful': True, 'Payload': {'Data': [self.record['source_fields']], 'TotalRecords': 1}}))
        elif url == corpus.PRIMARY_URL:
            assert request.method == 'POST' and request.post_data_json == {
                'RecordId': corpus.RECORD_ID, 'OnManualClick': False}
            route.fulfill(content_type='application/json', body=self.raw)
        elif url.startswith(corpus.ORIGIN + '/returnsheet/api/loadcit/'):
            post = request.post_data_json
            assert request.method == 'POST' and post['ReturnSheetRecordId'] == corpus.RECORD_ID
            suffix = url.rsplit('/', 1)[-1]
            assert suffix in {'l4-table-a-grid', 'l9-table-1-grid', 'l9-table-2-grid', 'l9-table-3-grid', 'l10a-grid'}
            if suffix == 'l4-table-a-grid':
                assert post['PeriodYear'] == '2025'
            total = 60 if suffix == 'l9-table-1-grid' and post['GroupType'] == 'Group 1' else 0
            first, size = post['First'], post['Rows']
            rows = [corpus.source_row() for _ in range(min(size, max(0, total - first)))]
            raw = corpus.wire({'IsSuccessful': True, 'Payload': {
                'Data': rows, 'TotalRecords': total, 'Index': None}}).encode()
            route.fulfill(content_type='application/json', body=raw)
        elif url == PDF_URL:
            assert request.method == 'GET'
            route.fulfill(status=200 if self.pdf_available else 404,
                          content_type='application/pdf', body=financial.PDF if self.pdf_available else b'')
        else:
            self.unexpected.append({'url': url, 'method': request.method})
            route.abort()

    def list_html(self):
        meta = self.record['meta']
        headers = ''.join('<th>' + html.escape(str(k)) + '</th>' for k in meta)
        cells = ''.join('<td>' + html.escape(str(v)) + '</td>' for v in meta.values())
        open_action = ('window.open(' + json.dumps(corpus.FRAME_URL) + ',"_blank")' if self.popup
                       else 'location.assign(' + json.dumps(corpus.FRAME_URL) + ')')
        action = html.escape('if(event.isTrusted){' + open_action + ';}', quote=True)
        request = {'TaxpayerAggregateIdentifier': corpus.TAXPAYER_ID, 'First': 0,
                   'Rows': 10, 'Filters': [], 'isArchieved': False}
        return ('<html><head><link rel="icon" href="data:,"></head><body><div class="main-content">'
                '<p-table><table><thead><tr>' + headers + '<th>Action</th></tr></thead><tbody><tr>' + cells +
                '<td><button id="ViewButton" title="Lihat" onclick="' + action + '">View</button></td>'
                '</tr></tbody></table></p-table></div><script>fetch(' + json.dumps(
                    corpus.ORIGIN + '/returnsheet/api/returnsheetssubmitted') +
                ',{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(' +
                json.dumps(request) + ')});</script></body></html>')

    def grid_html(self, selector, endpoint, identity, name, total=0):
        config = html.escape(json.dumps({'endpoint': endpoint, 'identity': identity,
                                        'total': total, 'first': 0}), quote=True)
        return ('<' + selector + '><p-table data-fixture-config="' + config + '"><h3>' + name + '</h3>'
                '<table><thead><tr><th>Value</th></tr></thead><tbody></tbody></table>'
                '<div class="p-paginator"><span class="p-paginator-current"></span>'
                '<span class="p-dropdown-label">10</span><span class="p-paginator-page p-highlight">1</span>'
                '<button class="p-paginator-prev" onclick="turn(this,-10)">Prev</button>'
                '<button class="p-paginator-next" onclick="turn(this,10)">Next</button></div></p-table></' + selector + '>')

    def detail_html(self):
        main = ('<rshshr-citr-main-form><label for="dom-value">SYNTHETIC DOM AMOUNT</label>'
                '<input id="dom-value" formcontrolname="NetIncomeBeforeTax" value="0000777" readonly>'
                '<a href="/synthetic-existing/statement.pdf">Laporan Keuangan</a></rshshr-citr-main-form>')
        forms = [('Induk', main)]
        if self.groups:
            l4 = self.grid_html('rshshr-citr-l4-grid1', '/loadcit/l4-table-a-grid',
                 {'ReturnSheetRecordId': corpus.RECORD_ID, 'PeriodYear': '2025'}, 'SYNTHETIC L4')
            l9 = ''.join(self.grid_html('rshshr-citr-l9-form-grid' + str(family),
                         '/loadcit/l9-table-' + str(family) + '-grid',
                         {'ReturnSheetRecordId': corpus.RECORD_ID, 'GroupType': group},
                         'SYNTHETIC ' + str(family) + ' / ' + group,
                         60 if family == 1 and group == 'Group 1' else 0) for family, group in GROUPS)
            l10 = self.grid_html('rshshr-citr-l10a-form-grid1', '/loadcit/l10a-grid',
                 {'ReturnSheetRecordId': corpus.RECORD_ID}, 'SYNTHETIC L10-A')
            forms += [('L4', '<rshshr-citr-l4-form>' + l4 + '</rshshr-citr-l4-form>'),
                      ('L9', '<rshshr-citr-l9-form>' + l9 + '</rshshr-citr-l9-form>'),
                      ('L10-A', '<rshshr-citr-l10a-form>' + l10 + '</rshshr-citr-l10a-form>')]
        if self.extra_form:
            caption, selector = self.extra_form
            forms.append((caption, '<' + selector + '><label>UNSUPPORTED FIXTURE FORM</label></' + selector + '>'))
        tabs = ''.join('<li role="presentation"><a role="tab" aria-controls="panel-' + str(i) +
                       '" onclick="show(' + str(i) + ');return false" href="#">' + caption + '</a></li>'
                       for i, (caption, _) in enumerate(forms))
        panels = ''.join('<div class="p-tabview-panel" role="tabpanel" id="panel-' + str(i) +
                         '" style="display:' + ('block' if i == 0 else 'none') + '">' + body + '</div>'
                         for i, (_, body) in enumerate(forms))
        return ('<html><head><link rel="icon" href="data:,"><script src="' + ASSET + '"></script></head>'
            '<body><div class="main-content"><div class="p-tabview"><ul class="p-tabview-nav">' + tabs +
            '</ul><div class="p-tabview-panels">' + panels + '</div></div></div><script>' +
            'function load(g){let c=JSON.parse(g.dataset.fixtureConfig);let r=Object.assign({},c.identity,'
            '{First:c.first,Rows:10,SortField:"",SortOrder:1,Filters:[],LanguageId:"id-ID"});'
            'g.querySelector(".p-paginator-current").textContent="Showing "+(c.total?c.first+1:0)+'
            '" to "+Math.min(c.first+10,c.total)+" of "+c.total;'
            'g.querySelector(".p-paginator-page.p-highlight").textContent=String(c.first/10+1);'
            'g.querySelector(".p-paginator-prev").disabled=c.first===0;'
            'g.querySelector(".p-paginator-next").disabled=c.first+10>=c.total;'
            'return fetch(' + json.dumps(corpus.ORIGIN + '/returnsheet/api') +
            '+c.endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(r)})'
            '.then(r=>r.json()).then(b=>{g.querySelector("tbody").innerHTML=b.Payload.Data.map(x=>'
            '"<tr><td>0000</td></tr>").join("")})}'
            'function turn(b,d){let g=b.closest("p-table"),c=JSON.parse(g.dataset.fixtureConfig);'
            'c.first+=d;g.dataset.fixtureConfig=JSON.stringify(c);load(g)}'
            'function show(i){document.querySelectorAll(".p-tabview-panel").forEach((p,j)=>{'
            'p.style.display=i===j?"block":"none";if(i===j)p.querySelectorAll("p-table").forEach(g=>{'
            'if(!g.dataset.started){g.dataset.started="yes";load(g)}})})}'
            'fetch(' + json.dumps(corpus.PRIMARY_URL) + ',{method:"POST",headers:{"Content-Type":"application/json"},'
            'body:JSON.stringify({RecordId:' + json.dumps(corpus.RECORD_ID) + ',OnManualClick:false})});'
            '</script></body></html>')

    def collect(self):
        return native_collector()(self.page, self.run, self.folder, detail_source='json-first')

    def assert_native(self, result):
        assert result['complete'] is True and result['errors'] == []
        record = result['records'][0]
        assert record['detail_source']['used'] == 'json'
        values = [row for s in record['sections'] for t in s.get('tables', []) for row in t['rows']]
        assert ['/MainFormData/NetIncomeBeforeTax', 'number', '123.4500'] in values
        assert not any(f.get('value') == '0000777' for s in record['sections'] for f in s.get('fields', []))
        attachment = record['attachments'][0]
        assert attachment['status'] == 'COMPLETE'
        assert (self.folder / attachment['relative_path']).read_bytes() == financial.PDF
        assert attachment['hash'] == hashlib.sha256(financial.PDF).hexdigest()
        assert self.unexpected == []


@pytest.mark.parametrize('popup', [True, False])
def test_real_native_bridge_uses_trusted_view_click_and_json_not_dom_values(browser, tmp_path, monkeypatch, popup):
    native_collector()
    fixture = NativeFixture(browser, tmp_path, monkeypatch, popup=popup)
    try:
        fixture.assert_native(fixture.collect())
        assert len([r for r in fixture.requests if r['url'] == corpus.PRIMARY_URL]) == 1
    finally:
        fixture.close()


def test_real_native_bridge_binds_all_grid_roles_and_all_sixty_duplicate_rows(browser, tmp_path, monkeypatch):
    native_collector()
    fixture = NativeFixture(browser, tmp_path, monkeypatch, groups=True)
    try:
        result = fixture.collect()
        fixture.assert_native(result)
        record = result['records'][0]
        coverage = record['detail_source']['coverage']
        assert coverage['complete'] is True and len(coverage['grids']) == 14
        assert all(g['complete'] and g['received'] == g['total'] for g in coverage['grids'])
        declared = [g for g in coverage['grids'] if g['total'] == 60]
        assert len(declared) == 1
        assert {s['name'] for s in record['sections']} == {'Induk', 'L4', 'L9', 'L10-A'}
        target = [t for section in record['sections'] if section['name'] == 'L9'
                  for t in section['tables'] if t['name'] == declared[0]['name']]
        assert len(target) == 1
        # Task3 tables preserve typed leaves, not a new business-row/table schema.
        leaves = [('Name','string','SYNTHETIC SLIP'), ('TIN','string','0000000000000002'),
                  ('Index','number','0'), ('TaxBase','number','12.3400'),
                  ('IncomeTax','number','0'), ('IsManually','boolean',False), ('Action','null',None)]
        expected = [[f'/Payload/Data/{ordinal}/{field}', kind, value]
                    for ordinal in range(60) for field, kind, value in leaves]
        assert target[0]['rows'] == expected
        requests = [r for r in fixture.requests if '/loadcit/' in r['url']]
        assert {r['body']['GroupType'] for r in requests if '/l9-table-2-' in r['url']} == {'Permanent', 'Non-permanent'}
        assert {r['body']['GroupType'] for r in requests if '/l9-table-3-' in r['url']} == {'Group 1','Group 2','Group 3','Group 4','Other Group'}
        assert {r['body']['First'] for r in requests if r['url'].endswith('/l9-table-1-grid')
                and r['body']['GroupType'] == 'Group 1'} == {0,10,20,30,40,50}
    finally:
        fixture.close()


@pytest.mark.parametrize('extra_form', [('L10-A', 'rshshr-citr-l10a-form'), ('L99', 'synthetic-unknown-form')])
def test_missing_declared_root_or_unknown_visible_form_uses_whole_dom(browser, tmp_path, monkeypatch, extra_form):
    native_collector()
    fixture = NativeFixture(browser, tmp_path, monkeypatch, extra_form=extra_form)
    try:
        result = fixture.collect()
        assert result['complete'] is True and result['errors'] == []
        record = result['records'][0]
        assert record['detail_source']['used'] == 'dom' and record['detail_source']['reason']
        assert any(f.get('value') == '0000777' for s in record['sections'] for f in s.get('fields', []))
        assert not any('/MainFormData/NetIncomeBeforeTax' in str(t) for s in record['sections'] for t in s.get('tables', []))
        assert fixture.unexpected == []
    finally:
        fixture.close()


def test_changed_public_source_bytes_reject_catalog_and_fall_back_whole_dom(browser, tmp_path, monkeypatch):
    native_collector()
    fixture = NativeFixture(browser, tmp_path, monkeypatch, changed_build=True)
    try:
        result = fixture.collect()
        assert result['complete'] is True and result['records'][0]['detail_source']['used'] == 'dom'
        assert any(f.get('value') == '0000777' for s in result['records'][0]['sections'] for f in s.get('fields', []))
        assert fixture.unexpected == []
    finally:
        fixture.close()


def test_native_json_financial_partial_is_retried_before_run_can_complete(browser, tmp_path, monkeypatch):
    native_collector()
    fixture = NativeFixture(browser, tmp_path, monkeypatch)
    try:
        fixture.pdf_available = False
        first = fixture.collect()
        assert first['complete'] is False and first['records'][0]['detail_source']['used'] == 'json'
        assert first['records'][0]['attachments'][0]['status'] == 'PARTIAL'
        fixture.pdf_available = True
        fixture.run = {**fixture.run, 'errors': [], 'records': [deepcopy(corpus.selected_record())]}
        fixture.run['records'][0].update(key='synthetic-native-record', list_page=1, list_page_size=None, sections=[])
        fixture.assert_native(fixture.collect())
        assert len([r for r in fixture.requests if r['url'] == PDF_URL]) == 2
        assert fixture.unexpected == []
    finally:
        fixture.close()



@pytest.mark.parametrize('popup', [True, False])
def test_synthetic_native_fixture_navigation_and_grid_handlers_are_independently_valid(browser, tmp_path, monkeypatch, popup):
    # Must PASS on unchanged source: do not hide broken fixtures behind mode RED.
    fixture = NativeFixture(browser, tmp_path, monkeypatch, popup=popup, groups=True)
    try:
        fixture.page.goto(corpus.LIST_URL, wait_until='domcontentloaded')
        if popup:
            with fixture.context.expect_page() as opened:
                fixture.page.locator('#ViewButton').click()
            detail = opened.value
        else:
            fixture.page.locator('#ViewButton').click()
            detail = fixture.page
        detail.wait_for_url(corpus.FRAME_URL)
        detail.wait_for_load_state('domcontentloaded')
        detail.wait_for_function("() => performance.getEntriesByType('resource').some(e => e.name.includes('/prefillreturnsheet/corporate-income'))")
        for caption in ('L4', 'L9', 'L10-A'):
            detail.get_by_role('tab', name=caption, exact=True).click()
        detail.get_by_role('tab', name='L9', exact=True).click()
        grid = detail.locator('rshshr-citr-l9-form-grid1').first
        for offset in (10,20,30,40,50):
            with detail.expect_response(lambda response, offset=offset:
                    response.url.endswith('/loadcit/l9-table-1-grid')
                    and response.request.post_data_json.get('GroupType') == 'Group 1'
                    and response.request.post_data_json.get('First') == offset) as response:
                grid.locator('.p-paginator-next').click()
            response.value.finished()
        assert grid.locator('tbody tr').count() == 10
        assert grid.locator('.p-paginator-next').is_disabled()
        assert detail.url == corpus.FRAME_URL
        requests = [r for r in fixture.requests if '/loadcit/' in r['url']]
        roles = {(r['url'].rsplit('/', 1)[-1], r['body'].get('GroupType')) for r in requests}
        expected = {('l9-table-' + str(family) + '-grid', group) for family, group in GROUPS}
        expected |= {('l4-table-a-grid', None), ('l10a-grid', None)}
        assert roles == expected
        assert fixture.unexpected == []
    finally:
        fixture.close()


@pytest.mark.parametrize('missing', ['ReturnSheetRecordId', 'PeriodYear'])
def test_approved_native_build_missing_grid_identity_uses_whole_dom(
        browser, tmp_path, monkeypatch, missing):
    native_collector()

    class MissingL4Identity(NativeFixture):
        def grid_html(self, selector, endpoint, identity, name, total=0):
            if endpoint == '/loadcit/l4-table-a-grid':
                identity = {key: value for key, value in identity.items() if key != missing}
            return super().grid_html(selector, endpoint, identity, name, total)

        def route(self, route):
            request = route.request
            if request.url.endswith('/loadcit/l4-table-a-grid'):
                body = request.post_data_json
                assert request.method == 'POST' and missing not in body
                other = 'PeriodYear' if missing == 'ReturnSheetRecordId' else 'ReturnSheetRecordId'
                assert body[other] == ('2025' if other == 'PeriodYear' else corpus.RECORD_ID)
                self.requests.append({'url': request.url, 'method': request.method, 'body': body})
                route.fulfill(content_type='application/json', body=corpus.wire({
                    'IsSuccessful': True, 'Payload': {'Data': [], 'TotalRecords': 0, 'Index': None}}))
                return
            super().route(route)

    fixture = MissingL4Identity(browser, tmp_path, monkeypatch, groups=True)
    try:
        result = fixture.collect()
        assert result['complete'] is True and result['errors'] == [], result['errors']
        record = result['records'][0]
        assert record['detail_source']['used'] == 'dom'
        assert any(f.get('value') == '0000777' for s in record['sections'] for f in s.get('fields', []))
        assert not any('/MainFormData/NetIncomeBeforeTax' in str(t)
                       for s in record['sections'] for t in s.get('tables', []))
        l9 = [table for section in record['sections'] if section['name'] == 'L9'
              for table in section.get('tables', [])]
        assert sum(len(table['rows']) for table in l9) == 60
        assert all(row == ['0000'] for table in l9 for row in table['rows'])
        assert all(table['complete'] for table in l9) and max(table['pages'] for table in l9) == 6
        assert any(r['url'].endswith('/loadcit/l4-table-a-grid') and missing not in r['body']
                   for r in fixture.requests)
        assert fixture.unexpected == []
    finally:
        fixture.close()
