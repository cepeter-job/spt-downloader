"""Actual hosted L2 observer/capture/held/workbook seam, no live data."""
from copy import deepcopy
import html
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
import coretax_corporate as observer
import coretax_corporate_projection as projection
from coretax_json import JsonSafetyError, adapt_corporate_detail, has_audit_dump_tables
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture as SpaFixture, ASSET
from l3_observer_fixture import l3_form_html
from test_corporate_l1d_observer import open_selected
from test_corporate_l1d_native import DETAIL
from test_corporate_l2_owner import populated
from test_corporate_l2_projection import wire
from test_corporate_l11c_native import COUNTRY, catalog, related_person_catalog
from test_corporate_l3_native import (GRID as L3_GRID, FOOTER as L3_FOOTER,
    REFERENCES as L3_REFERENCES, packets as l3_packets, request)
from test_corporate_l3_projection import ROOT as L3_ROOT, inputs as l3_inputs
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


A_HEADERS = ['NO.', 'NAMA', 'ALAMAT', 'NEGARA', 'NPWP/NIK', 'Jabatan',
             'Modal Disetor / NILAI (Rp)', 'Modal Disetor / %', 'DIVIDEN/PEMBAGIAN LABA(Rp)']
RELATED_PERSON = corpus.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/RELATED_PERSON_TYPE'
GROUPS = [
    'A. DAFTAR PEMEGANG SAHAM/PEMILIK MODAL DAN JUMLAH DIVIDEN/PEMBAGIAN LABA YANG DIBAGIKAN SERTA DAFTAR SUSUNAN PENGURUS DAN KOMISARIS',
    'B. DAFTAR PENYERTAAN MODAL, UTANG, DAN/ATAU PIUTANG PADA PERUSAHAAN AFILIASI']


class Fixture(SpaFixture):
    def __init__(self, browser, monkeypatch, *, defect=None, oracle=False, model='Normal',
                 context=None, record_id=None, position=None, l3=False, rows=None):
        self.oracle = oracle
        self.l3 = l3
        self.l3_footer_raw = self.l3_grid_raw = self.l3_reference_raw = None
        self.position = position if position is not None else (
            'SYN_REL_A' if defect == 'cached-references' else None)
        natural_refs = (list(dict.fromkeys([COUNTRY, RELATED_PERSON]
            + list(L3_REFERENCES.values()))) if l3
            else ([COUNTRY] if defect != 'cached-references' else []))
        super().__init__(browser, monkeypatch, defect=defect, model=model, context=context,
                         record_id=record_id, rows=rows, natural_refs=natural_refs)
        # The L2-only document keeps its legacy natural COUNTRY_CODE GET (the
        # SPA issues it on the detail load); the cache-miss defect observes
        # none of them, so the bounded re-fetch restores the catalogs.
        monkeypatch.setattr(projection, 'L2_BUILD_DIGESTS', self.pins, raising=False)
        if l3:
            monkeypatch.setattr(projection, 'L3_BUILD_DIGESTS', self.pins, raising=False)
        value = corpus.current_form()
        value['ReturnSheetRecordIdentifier'] = self.record['record_id']
        l2 = populated()
        # Position transport is separately owned. The default end-to-end subset
        # uses literal-null Position; a populated case uses a real code so the
        # (re-)fetched nonempty catalog proves binding a Position label.
        for row in l2['ListOfShareholders']:
            row['Position'] = self.position
            row['CountryCode'] = 'SYN_COUNTRY_A'
        for row in l2['InvestmentList']:
            row['CountryCode'] = 'SYN_COUNTRY_A'
        value['ListOfOwnership'] = wire(l2)
        model_value = 'NORMAL' if model == 'Normal' else 'AMENDMENT'
        payload = {'IsSuccessful': True, 'Payload': {
            'TIN': corpus.NPWP, 'PeriodYear': 2025, 'IsDraft': True,
            'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': model_value,
            'PreviousFormData': None, 'LastSubmittedFormData': None,
            'RelatedTaxpayers': [{'Name': 'SYNTHETIC PREFILL MUST NOT WIN'}],
            'CurrentFormData': corpus.wire(value)}}
        if l3:
            # The combined return also carries the L3-B data-conditional
            # content: the L3 overseas form plus the owned grid source.
            l3_form, _, _ = l3_inputs()
            value['MainFormData']['IsIncomeTaxOverseas'] = 1
            value[L3_ROOT] = l3_form
            payload['Payload']['IsIncomeTaxOverseas'] = 1
            payload['Payload']['CurrentFormData'] = corpus.wire(value)
        self.raw = corpus.wire(payload).encode()
        if l3:
            l3_raw = l3_packets(model, record_id=self.record['record_id'])
            self.l3_footer_raw = l3_raw[1]['body']
            self.l3_grid_raw = {0: l3_raw[2]['body'], 10: l3_raw[3]['body']}
            self.l3_reference_raw = {url: l3_raw[index + 4]['body']
                for index, url in enumerate(L3_REFERENCES.values())}

    def route(self, route):
        req = route.request
        if self.l3 and self.l3_grid_raw is not None and req.url == L3_GRID:
            self.requests.append((req.url, req.method))
            assert req.method == 'POST' and req.post_data_json in (
                request(0, self.record['record_id']), request(10, self.record['record_id']))
            return route.fulfill(content_type='application/json',
                body=self.l3_grid_raw[req.post_data_json['First']])
        if self.l3 and self.l3_footer_raw is not None and req.url == L3_FOOTER:
            self.requests.append((req.url, req.method))
            assert req.method == 'POST' and req.post_data_json == {
                'ReturnSheetRecordId': self.record['record_id']}
            return route.fulfill(content_type='application/json', body=self.l3_footer_raw)
        if req.url == COUNTRY:
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            payload = catalog()
            if self.l3:
                # One shared COUNTRY_CODE catalog serves both consumers: the
                # L2 country label and the L3 overseas ZZ label.
                payload[0]['Details'].append({'Code': 'ZZ', 'CodeDescription': 'SYNTHETIC COUNTRY',
                                              'ValidFrom': None, 'ValidTo': None})
            return route.fulfill(content_type='application/json',
                body=corpus.wire({'IsSuccessful': True, 'Payload': payload}))
        if req.url == RELATED_PERSON:
            # The L2 owner needs COUNTRY_CODE + RELATED_PERSON_TYPE; a later
            # return reacquires the cached catalogs, so serve both here. A
            # populated case serves a NONEMPTY catalog so the (re-)fetch
            # proves binding a real Position label, not an empty placeholder.
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            payload = related_person_catalog()
            if self.defect == 'cached-references' or self.position:
                payload = [{'ReferenceDataType': 'RELATED_PERSON_TYPE', 'language': 'id-ID',
                            'Details': [{'Code': 'SYN_REL_A',
                                         'CodeDescription': 'SYNTHETIC RELATED PERSON A'}]}]
            return route.fulfill(content_type='application/json',
                body=corpus.wire({'IsSuccessful': True, 'Payload': payload}))
        if (self.l3 and self.l3_reference_raw is not None
                and req.url in self.l3_reference_raw and req.url not in (COUNTRY, RELATED_PERSON)):
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            return route.fulfill(content_type='application/json',
                body=self.l3_reference_raw[req.url])
        return super().route(route)

    def document(self):
        source = super().document()
        # Only the test's separate post-native DOM oracle enables value reads.
        # Every production observer/capture call still runs with the trap armed.
        source = source.replace('if(owner&&(', 'if(!window.oracleRead&&owner&&(')
        if not self.l3:
            # The legacy L2-only document: its natural COUNTRY_CODE GET (all
            # defects except the cache-miss one, which issues none) now runs
            # through the page-level SPA cache registered in __init__.
            return source
        # The combined document carries the L3 form: L3 block styles, the
        # paginator click allowance and the per-record L3 source script. The
        # natural reference GETs run through the page-level SPA cache, so a
        # later return in the same document observes none of them.
        source = source.replace('</head>', '<style>rshshr-citr-l3-form,rsh-citr-l3-grid1,'
            'rshshr-citr-l3-grid2,ui-grid,ui-grid-offline{display:block}</style></head>')
        source = source.replace('!e.target.closest("a[role=tab]"))window.forbiddenClicks++;',
            '!e.target.closest("a[role=tab]")&&!e.target.closest(".p-paginator button"))window.forbiddenClicks++;')
        bait = json.dumps('<td>SYNTHETIC BODY BAIT<input value="SYNTHETIC INPUT"></td>' * 8)
        script = ('<script>window.l3Started=false;window.l3Done=false;window.l3FooterDone=false;'
            'window.l3FooterReplies=0;const baseShowL3=window.show;window.show=function(i){'
            'baseShowL3(i);if(i===2&&!window.l3Started){window.l3Started=true;startL3();}};'
            'function fetchFooterL3(){return fetch(' + json.dumps(L3_FOOTER) + ',{method:"POST",'
            'headers:{"Content-Type":"application/json"},body:JSON.stringify({ReturnSheetRecordId:'
            'window.__sptCurrentRecord})}).then(r=>r.json()).then(()=>{window.l3FooterReplies++;'
            'window.l3FooterDone=true;});}'
            'function moveL3(first){const req={ReturnSheetRecordId:window.__sptCurrentRecord,'
            'PeriodYear:"2025",First:first,Rows:10,SortField:"WithholdingSlipsDate",SortOrder:1,'
            'Filters:[],LanguageId:"id-ID"};return fetch(' + json.dumps(L3_GRID) + ',{method:"POST",'
            'headers:{"Content-Type":"application/json"},body:JSON.stringify(req)})'
            '.then(r=>r.json()).then(()=>{const grid=document.querySelector("rshshr-citr-l3-grid2");'
            'if(!grid)return;grid.querySelector(".p-paginator-current").textContent='
            'first===0?"1 of 2":"2 of 2";grid.querySelector(".p-paginator-prev").disabled=first===0;'
            'grid.querySelector(".p-paginator-next").disabled=first!==0;'
            'grid.querySelector("tbody").innerHTML=("<tr>"+' + bait + '+"</tr>")'
            '.repeat(first===0?10:2);window.l3Done=true;});}'
            'function startL3(){fetchFooterL3();moveL3(0);}</script>')
        return source.replace('</body>', script + '</body>')

    def _l2_form_html(self):
        """The rshshr-citr-l2-form fragment the SPA renders for this return."""
        tables = []
        for index, (headers, spans) in enumerate(((A_HEADERS, [1, 5, 1, 1, 1]),
                (projection.L2_AFFILIATE_HEADERS, [1, 5, 1, 2, 1, 2]))):
            owner = f'rsh-citr-l2-form-grid{index + 1}'
            if self.defect == 'owner' and index == 0:
                owner = 'synthetic-foreign-owner'
            labels = list(headers)
            if self.defect == 'header' and index == 0:
                labels[0] = 'SYNTHETIC UNKNOWN'
            if self.oracle:
                # Independent literal DOM oracle, not generated by a product
                # projector or formatter; both grids share this record's bytes.
                cells = ([['1', 'SYNTHETIC OWNER', 'SYNTHETIC ADDRESS', 'SYNTHETIC COUNTRY LABEL',
                    '0000000000000009', '', '1.000,125', '50,0000', '0'],
                    ['2', 'SYNTHETIC OWNER', 'SYNTHETIC ADDRESS', 'SYNTHETIC COUNTRY LABEL',
                     '0000000000000009', '', '1.000,125', '50,0000', '0']] if index == 0 else
                    [['1', 'SYNTHETIC AFFILIATE 1', 'SYNTHETIC COUNTRY LABEL', '0000000000000002',
                      '2.000,5', '12,0625', '500,125', '2025', '4,125', '250,5', '02024', '1,5'],
                     ['2', 'SYNTHETIC AFFILIATE 1', 'SYNTHETIC COUNTRY LABEL', '0000000000000002',
                      '2.000,5', '12,0625', '500,125', '2025', '4,125', '250,5', '02024', '1,5']])
                body = ''.join('<tr>' + ''.join('<td>' + html.escape(v) + '</td>' for v in row)
                               + '</tr>' for row in cells)
                footer = (['', 'JUMLAH', '2.000,25', '100,0000', '0'] if index == 0 else
                          ['', 'JUMLAH', '1.000,25', '', '501', ''])
            else:
                body = ('<tr>' + '<td>SYNTHETIC WRONG DOM VALUE</td>' * len(headers) + '</tr>') * 2
                footer = ['SYNTHETIC WRONG TOTAL'] * len(spans)
            if self.defect == 'reference-loading' and index == 0:
                body = body.replace('<td>', '<td><ui-grid-offline-body><div class="loading-container"></div></ui-grid-offline-body>', 1)
            tables.append('<p-accordiontab><div class="p-accordion-header"><a href="#" '
                'aria-expanded="true"><span class="p-accordion-header-text">' + GROUPS[index]
                + '</span></a></div><div class="p-accordion-content"><' + owner
                + ' style="display:block"><ui-grid-offline style="display:block"><p-table><table><thead><tr>'
                + ''.join('<th>' + html.escape(label) + '</th>' for label in labels)
                + '</tr></thead><tbody>' + body
                + '</tbody><tfoot><tr>' + ''.join('<td colspan="' + str(span)
                + '">' + html.escape(value) + '</td>' for span, value in zip(spans, footer))
                + '</tr></tfoot></table></p-table></ui-grid-offline></' + owner
                + '></div></p-accordiontab>')
        return ('<rshshr-citr-l2-form style="display:block"><h2>DAFTAR KEPEMILIKAN</h2>'
            '<p-panel><span class="p-panel-title">HEADER</span>'
            '<label>Tahun Pajak/Bagian Tahun Pajak</label><input formcontrolname="TaxPeriodYear">'
            + ('' if self.defect == 'header-control' else
               '<label>Nomor Identitas WP</label><input formcontrolname="CollectorTin">')
            + '</p-panel><p-accordion>' + ''.join(tables) + '</p-accordion></rshshr-citr-l2-form>')

    @staticmethod
    def _tabview(tabs, panels):
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            + panels + '</div></div></div></rshshr-corporate-income-tax-return>')

    def detail(self):
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i)
            + '" href="#" onclick="show(' + str(i) + ');return false">' + name + '</a></li>'
            for i, name in enumerate(('Induk', 'L2')))
        panels = ('<div class="p-tabview-panel" role="tabpanel" id="panel-0"><rshshr-citr-main-form>'
            '<label>SYNTHETIC PLACEHOLDER</label></rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-1" style="display:none">'
            + self._l2_form_html() + '</div>')
        return self._tabview(tabs, panels)

    def detail_combined(self):
        """Induk + L2 + L3 tab view for the combined two-return document."""
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i)
            + '" href="#" onclick="show(' + str(i) + ');return false">' + name + '</a></li>'
            for i, name in enumerate(('Induk', 'L2', 'L3')))
        panels = ('<div class="p-tabview-panel" role="tabpanel" id="panel-0"><rshshr-citr-main-form>'
            '<label>SYNTHETIC PLACEHOLDER</label></rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-1" style="display:none">'
            + self._l2_form_html() + '</div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-2" style="display:none">'
            + l3_form_html(None) + '</div>')
        return self._tabview(tabs, panels)

    def _detail_fragment(self):
        return self.detail_combined() if self.l3 else self.detail()


@pytest.mark.parametrize('oracle', [False, True], ids=['business-read-trap', 'independent-DOM-oracle'])
def test_populated_observer_capture_held_replay_and_both_saved_workbook_blocks(browser, tmp_path, monkeypatch, oracle):
    fixture = Fixture(browser, monkeypatch, oracle=oracle)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            assert forms is not None
            binding, = [f for f in forms if f['name'] == 'L2']
            assert binding['projection']['kind'] == 'corporate-l2-owner-v2'
            manifest = capture.drain()
            assert manifest['complete'] and 'component_lifetime' in manifest
            packets = list(capture.iter_bodies())
            before = deepcopy((packets, forms))
            result = adapt_corporate_detail(packets, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            section, = [s for s in result['sections'] if s['name'] == 'L2']
            assert not has_audit_dump_tables([section])
            assert len(section['tables']) == 2
            assert section['tables'][0]['rows'][0][3] == 'SYNTHETIC COUNTRY LABEL'
            assert section['tables'][1]['rows'][0][2] == 'SYNTHETIC COUNTRY LABEL'
            assert section['projection_complete'] is False  # Two header controls have no approved slots.
            assert section['projection_reason'] == 'unmapped_l2_header_controls'
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
            assert (packets, forms) == before
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            if oracle:
                page.evaluate('window.oracleRead=true')
                dom = page.locator('rshshr-citr-l2-form table').evaluate_all('''tables => tables.map(table => ({
                    body:[...table.tBodies].flatMap(body=>[...body.rows]).map(row=>[...row.cells].map(cell=>cell.textContent.trim())),
                    footer:[...table.tFoot.rows].map(row=>[...row.cells].map(cell=>cell.textContent.trim()))}))''')
                page.evaluate('window.oracleRead=false')
                assert len(dom) == len(section['tables']) == 2
                for table, actual in zip(section['tables'], dom):
                    assert table['rows'] == actual['body'] + actual['footer']
                    assert table['footer'] == actual['footer']
            assert fixture.unexpected == []
        fixture.record.update(capture_complete=True, sections=[section])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        folder = tmp_path / 'export'
        coretax.save_output(run, folder)
        coretax.verify_outputs(run, folder)
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        book = load_workbook(folder / name)
        resume = load_workbook(folder / 'resume.xlsx')
        try:
            sheet = book['L2']
            headers = [next(r for r in range(1, sheet.max_row + 1)
                if [sheet.cell(r, c).value for c in range(1, len(labels) + 1)] == labels)
                for labels in (A_HEADERS, projection.L2_AFFILIATE_HEADERS)]
            a, b = headers
            assert sheet.cell(a + 1, 2).value == sheet.cell(a + 2, 2).value == 'SYNTHETIC OWNER'
            assert sheet.cell(a + 1, 4).value == 'SYNTHETIC COUNTRY LABEL'
            assert sheet.cell(a + 1, 5).value == '0000000000000009'
            assert sheet.cell(a + 1, 7).value == 1000.125
            assert sheet.cell(a + 1, 8).value == 0.5
            assert sheet.cell(b + 1, 3).value == 'SYNTHETIC COUNTRY LABEL'
            assert sheet.cell(b + 1, 6).value == 0.120625
            assert sheet.cell(b + 1, 9).value == 4.125
            # Scope each total by its own header, never the first JUMLAH.
            totals = [next(r for r in range(header + 1, stop)
                if sheet.cell(r, 1).value == 'JUMLAH') for header, stop in
                ((a, b), (b, sheet.max_row + 1))]
            assert sheet.cell(totals[0], 7).value == 2000.25
            assert sheet.cell(totals[0], 8).value == 1
            assert sheet.cell(totals[1], 7).value == 1000.25
            assert sheet.cell(totals[1], 10).value == 501
            report, = [r for r in run['template_mapping'] if r['form'] == 'L2']
            assert report['complete'] is False and report['derived_complete'] is False
            assert report['unmapped_rows'] == report['unmapped_tables'] == 0
            assert report['derived_reason'] == 'unmapped_l2_header_controls'
            assert 'header L2' in ' '.join(str(c.value) for row in resume['Audit'] for c in row)
        finally:
            book.close()
            resume.close()
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['pins', 'locale', 'timezone', 'route', 'tables',
    'owner', 'group', 'header', 'span', 'span-bool', 'references', 'method', 'endpoint', 'sequence-shape', 'missing-sequence'])
def test_strong_proof_does_not_bypass_any_owner_or_reference_guard(browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            assert forms is not None
            binding, = [f for f in forms if f['name'] == 'L2']
            proof = binding['projection']
            assert proof['kind'] == 'corporate-l2-owner-v2'
            capture.drain()
            if defect == 'pins':
                proof['builds'][projection.MAIN_SOURCE] = None
            elif defect in ('locale', 'timezone', 'route'):
                proof[defect] = 'SYNTHETIC UNREVIEWED'
            elif defect == 'tables':
                proof['tables'] = None
            elif defect == 'owner':
                proof['tables'][0]['component'] = 'SYNTHETIC FOREIGN OWNER'
            elif defect == 'group':
                proof['tables'][0]['source_structure']['groups'] = []
            elif defect == 'header':
                proof['tables'][0]['headers'][0] = 'SYNTHETIC FOREIGN HEADER'
            elif defect == 'span':
                proof['tables'][1]['footer_spans'] = [[12]]
            elif defect == 'span-bool':
                proof['tables'][1]['footer_spans'][0][0] = True
            elif defect == 'references':
                proof['references'] = None
            elif defect == 'method':
                proof['references'][0]['method'] = 'POST'
            elif defect == 'endpoint':
                proof['references'][0]['endpoint'] = []
            elif defect == 'sequence-shape':
                proof['references'][0]['sequences'] = [True]
            elif defect == 'missing-sequence':
                proof['references'][0]['sequences'] = [999]
            if defect == 'sequence-shape':
                with pytest.raises(JsonSafetyError):
                    adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
            else:
                result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
                assert not result['eligible'] and result['sections'] == []
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('change', ['route-detour', 'mixed-attempt'])
def test_new_owner_does_not_demote_fatal_original_custody(browser, tmp_path, monkeypatch, change):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            assert forms is not None
            if change == 'route-detour':
                page.evaluate('''()=>{const url=location.href;history.pushState({},'',url+'&synthetic=detour');
                    history.pushState({},'',url);}''')
                with pytest.raises(JsonSafetyError):
                    capture.drain()
            else:
                capture.drain()
                packets = list(capture.iter_bodies())
                packets[-1]['context']['attempt'] = 'b' * 32
                with pytest.raises(JsonSafetyError):
                    adapt_corporate_detail(packets, fixture.record, corpus.SCOPE, forms)
    finally:
        fixture.close()


def test_l2_stop_stays_cancellation_after_owned_view(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            def cancel():
                raise driver.CaptureCancelled('SYNTHETIC STOP')
            with pytest.raises(driver.CaptureCancelled):
                observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                    approved_digest=fixture.pins[ASSET], check_cancel=cancel)
            assert not list(tmp_path.rglob('manifest.json'))
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['owner', 'header', 'header-control', 'reference-loading', 'vendor-pin', 'external-context'])
def test_unproved_native_owner_keeps_quarantine_or_whole_record_fallback(browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            if forms is not None:
                capture.drain()
                result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
                assert not result['eligible']
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


def test_cached_l2_references_are_reacquired(browser, tmp_path, monkeypatch):
    # A later return in the same job observes no fresh reference GETs (the SPA
    # serves COUNTRY_CODE + RELATED_PERSON_TYPE from cache). The observer
    # reacquires them with a bounded cache-busting GET; the L2 owner is
    # reconciled against both catalogs and the record stays eligible.
    fixture = Fixture(browser, monkeypatch, defect='cached-references')
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            assert forms is not None
            binding, = [f for f in forms if f['name'] == 'L2']
            endpoints = {r['endpoint'] for r in binding['projection']['references']}
            assert endpoints == {COUNTRY, RELATED_PERSON}
            capture.drain()
            result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'], result['reason']
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


def _assert_projected_labels(result):
    """Exact label projections: the nonempty catalogs bind both returns."""
    l2, = [s for s in result['sections'] if s['name'] == 'L2']
    for table in l2['tables']:
        for row in [r for r in table['rows'] if r[1] != 'JUMLAH']:
            # Body rows only: the footer JUMLAH row carries totals, not labels.
            assert 'SYNTHETIC COUNTRY LABEL' in row
    shareholders = [r for r in l2['tables'][0]['rows'] if r[1] != 'JUMLAH']
    for row in shareholders:
        assert row[5] == 'SYNTHETIC RELATED PERSON A'
    l3, = [s for s in result['sections'] if s['name'] == 'L3']
    assert [t['body_row_count'] for t in l3['tables']] == [2, 12]
    assert l3['tables'][0]['rows'][0][2] == 'SYNTHETIC COUNTRY'
    assert l3['tables'][1]['rows'][0][3] == 'SYNTHETIC TAX'


def test_two_return_l2_reference_reacquired_with_populated_catalog(browser, tmp_path, monkeypatch):
    # True two-record, same-document SPA integration: ONE page carries both
    # returns of the same taxpayer (Normal record A, then Amendment record B).
    # The SPA catalog cache is page-level and persists through the
    # list/detail/list/detail transitions: the 1st return observes every
    # reference catalog naturally; after the list restore the 2nd return
    # observes NO natural reference GETs, so the bounded cache-busting
    # re-fetch (cache:'reload', AbortController) restores them. The two
    # records have distinct record/route/primary IDs and distinct capture
    # attempts, the nonempty Position catalog binds the same label on both
    # returns, and the L3-B grid projects populated rows on the 2nd return.
    # Separate missing/failed-catalog negatives stay in the L2/L3 fixtures.
    rid1, rid2 = '00000000-0000-4000-8000-000000000021', '00000000-0000-4000-8000-000000000022'
    first = Fixture(browser, monkeypatch, model='Normal', record_id=rid1,
                    rows=[rid1, rid2], position='SYN_REL_A', l3=True)
    bodies1, log1 = None, None
    try:
        with DetailJsonCapture(first.context, first.page, first.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(first, capture)
            first_forms = observer.observe_forms(page, first.record, corpus.SCOPE, capture,
                approved_digest=first.pins[ASSET])
            assert first_forms is not None
            assert {f['name'] for f in first_forms} >= {'L2', 'L3'}
            capture.drain()
            bodies1 = list(capture.iter_bodies())
            first_result = adapt_corporate_detail(bodies1, first.record, corpus.SCOPE, first_forms)
            assert first_result['eligible'], first_result['reason']
            _assert_projected_labels(first_result)
            # 1st return: every catalog is observed by a NATURAL GET (the
            # SPA issues no cache-busting re-fetch for a fresh return).
            log1 = page.evaluate('window.__sptFetchLog.filter(e => e.url.includes("/referencedata/"))')
            assert {e['url'] for e in log1} == set(first.natural_refs)
            assert all(e['cache'] is None for e in log1)
            assert all(b['context']['record_id'] == rid1 for b in bodies1)
        first.context.unroute('**/*', first.route)
        page.evaluate('window.__sptFetchLog = []')
        second = Fixture(browser, monkeypatch, model='Amendment 002', record_id=rid2,
                         position='SYN_REL_A', l3=True, context=first.context)
        with DetailJsonCapture(second.context, second.page, second.record, corpus.SCOPE, tmp_path) as capture2:
            page = open_selected(second, capture2)
            forms = observer.observe_forms(page, second.record, corpus.SCOPE, capture2,
                approved_digest=second.pins[ASSET])
            assert forms is not None
            binding, = [f for f in forms if f['name'] == 'L2']
            assert {r['endpoint'] for r in binding['projection']['references']} == {
                COUNTRY, RELATED_PERSON}
            l3_binding, = [f for f in forms if f['name'] == 'L3']
            assert l3_binding['projection']['references']
            capture2.drain()
            bodies2 = list(capture2.iter_bodies())
            result = adapt_corporate_detail(bodies2, second.record, corpus.SCOPE, forms)
            assert result['eligible'], result['reason']
            _assert_projected_labels(result)
            # 2nd return: the SPA served every catalog from its page-level
            # cache, so no natural GET occurred; each observed catalog GET is
            # a cache-busting re-fetch (cache:'reload'), including the L3
            # COUNTRY_CODE catalog reacquired by the L2 consumer.
            log2 = page.evaluate('window.__sptFetchLog.filter(e => e.url.includes("/referencedata/"))')
            assert {e['url'] for e in log2} == set(second.natural_refs)
            assert all(e['cache'] == 'reload' for e in log2)
            # Distinct-record custody: separate capture attempts, record IDs
            # and primary routes; no source packet of one return leaks into
            # the other's capture.
            assert capture.attempt != capture2.attempt
            assert all(b['context']['record_id'] == rid2 and
                       b['context']['attempt'] == capture2.attempt for b in bodies2)
            assert all(b['context']['attempt'] == capture.attempt for b in bodies1)
            assert first.raw not in [b['body'] for b in bodies2]
            assert second.raw not in [b['body'] for b in bodies1]
            assert all(rid1 not in b['context'].get('frame_url', '') for b in bodies2)
            assert page.evaluate('window.businessReads') == 0
    finally:
        first.context.close()
