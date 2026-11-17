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
from test_corporate_l1d_observer import open_selected
from test_corporate_l1d_native import DETAIL
from test_corporate_l2_owner import populated
from test_corporate_l2_projection import wire
from test_corporate_l11c_native import COUNTRY, catalog
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


A_HEADERS = ['NO.', 'NAMA', 'ALAMAT', 'NEGARA', 'NPWP/NIK', 'Jabatan',
             'Modal Disetor / NILAI (Rp)', 'Modal Disetor / %', 'DIVIDEN/PEMBAGIAN LABA(Rp)']
GROUPS = [
    'A. DAFTAR PEMEGANG SAHAM/PEMILIK MODAL DAN JUMLAH DIVIDEN/PEMBAGIAN LABA YANG DIBAGIKAN SERTA DAFTAR SUSUNAN PENGURUS DAN KOMISARIS',
    'B. DAFTAR PENYERTAAN MODAL, UTANG, DAN/ATAU PIUTANG PADA PERUSAHAAN AFILIASI']


class Fixture(SpaFixture):
    def __init__(self, browser, monkeypatch, *, defect=None):
        super().__init__(browser, monkeypatch, defect=defect)
        monkeypatch.setattr(projection, 'L2_BUILD_DIGESTS', self.pins, raising=False)
        value = corpus.current_form()
        l2 = populated()
        # Position transport is separately owned. This end-to-end admitted
        # subset uses literal-null Position, not a fake catalog or raw code.
        # Non-null job descriptions are covered by the pure owner tests and
        # remain blocked until the shared producer's reviewed transport lands.
        for row in l2['ListOfShareholders']:
            row['Position'] = None
            row['CountryCode'] = 'SYN_COUNTRY_A'
        for row in l2['InvestmentList']:
            row['CountryCode'] = 'SYN_COUNTRY_A'
        value['ListOfOwnership'] = wire(l2)
        self.raw = corpus.wire({'IsSuccessful': True, 'Payload': {
            'TIN': corpus.NPWP, 'PeriodYear': 2025, 'IsDraft': True,
            'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
            'PreviousFormData': None, 'LastSubmittedFormData': None,
            'RelatedTaxpayers': [{'Name': 'SYNTHETIC PREFILL MUST NOT WIN'}],
            'CurrentFormData': corpus.wire(value)}}).encode()

    def route(self, route):
        if route.request.url == COUNTRY:
            self.requests.append((route.request.url, route.request.method))
            assert route.request.method == 'GET' and route.request.post_data is None
            return route.fulfill(content_type='application/json',
                body=corpus.wire({'IsSuccessful': True, 'Payload': catalog()}))
        return super().route(route)

    def document(self):
        source = super().document()
        return source.replace('.then(()=>window.primaryDone=true)',
            '.then(()=>fetch(' + json.dumps(COUNTRY) + ')).then(r=>r.json()).then(()=>window.primaryDone=true)')

    def detail(self):
        tables = []
        for index, (headers, spans) in enumerate(((A_HEADERS, [1, 5, 1, 1, 1]),
                (projection.L2_AFFILIATE_HEADERS, [1, 5, 1, 2, 1, 2]))):
            owner = f'rsh-citr-l2-form-grid{index + 1}'
            if self.defect == 'owner' and index == 0:
                owner = 'synthetic-foreign-owner'
            labels = list(headers)
            if self.defect == 'header' and index == 0:
                labels[0] = 'SYNTHETIC UNKNOWN'
            tables.append('<p-accordiontab><div class="p-accordion-header"><a href="#" '
                'aria-expanded="true"><span class="p-accordion-header-text">' + GROUPS[index]
                + '</span></a></div><div class="p-accordion-content"><' + owner
                + ' style="display:block"><ui-grid-offline style="display:block"><p-table><table><thead><tr>'
                + ''.join('<th>' + html.escape(label) + '</th>' for label in labels)
                + '</tr></thead><tbody>' + ('<tr>' + '<td>SYNTHETIC WRONG DOM VALUE</td>' * len(headers) + '</tr>') * 2
                + '</tbody><tfoot><tr>' + ''.join('<td colspan="' + str(span)
                + '">SYNTHETIC WRONG TOTAL</td>' for span in spans)
                + '</tr></tfoot></table></p-table></ui-grid-offline></' + owner
                + '></div></p-accordiontab>')
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i)
            + '" href="#" onclick="show(' + str(i) + ');return false">' + name + '</a></li>'
            for i, name in enumerate(('Induk', 'L2')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-0"><rshshr-citr-main-form>'
            '<label>SYNTHETIC PLACEHOLDER</label></rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" role="tabpanel" id="panel-1" style="display:none">'
            '<rshshr-citr-l2-form style="display:block"><h2>DAFTAR KEPEMILIKAN</h2>'
            '<p-accordion>' + ''.join(tables) + '</p-accordion></rshshr-citr-l2-form>'
            '</div></div></div></div></rshshr-corporate-income-tax-return>')


def test_populated_observer_capture_held_replay_and_both_saved_workbook_blocks(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
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
    'owner', 'group', 'header', 'span', 'references', 'method', 'sequence-shape', 'missing-sequence'])
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
            elif defect == 'references':
                proof['references'] = None
            elif defect == 'method':
                proof['references'][0]['method'] = 'POST'
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


@pytest.mark.parametrize('defect', ['owner', 'header', 'vendor-pin', 'external-context'])
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
