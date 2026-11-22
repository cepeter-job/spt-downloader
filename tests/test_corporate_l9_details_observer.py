"""Hosted full L9 consumer pipeline with the explicit shared-producer interface.

The test-only registration dependency is defined in details_consumer; production
admission is not claimed before the separately owned producer is integrated.
"""
from copy import deepcopy
import html
import json

import pytest

import coretax_browser as driver
import coretax_corporate as observer
import coretax_corporate_projection as projection
import coretax_json as adapter
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
import support_json_corpus as corpus
from test_corporate_l1d_observer import open_selected
from test_corporate_l9_projection import ROUTE, payload_form
from test_corporate_l9_grids import HEADERS
from test_corporate_l9_details_consumer import (recap, wire_asset, LABELS,
    shared_catalog_contract as shared_catalog_contract)
from test_corporate_l9_observer import Fixture as RecapFixture
from test_json_hybrid_native import browser as browser


class Fixture(RecapFixture):
    def __init__(self, browser, monkeypatch, urls, *, defect=None):
        self.urls, self.detail_defect = urls, defect
        super().__init__(browser, monkeypatch, natural_refs=list(self.urls.values()))
        monkeypatch.setattr(projection, 'L9_DETAIL_BUILD_DIGESTS', self.pins)
        current = corpus.current_form()
        current['MainFormData']['IsMigrated'] = defect == 'migrated'
        current[projection.L9_ROOT] = payload_form(recap())
        if defect == 'unprojected-form':
            current['ListOfOwnership'] = {'SyntheticUntouched': 'SYNTHETIC OTHER FORM'}
        self.raw = corpus.primary(current)['body']

    def route(self, route):
        if route.request.url in self.urls.values():
            self.requests.append((route.request.url, route.request.method))
            assert route.request.method == 'GET' and route.request.post_data is None
            kind, = [kind for kind, url in self.urls.items() if url == route.request.url]
            catalog = [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
                {'Code': code, 'CodeDescription': label, 'ValidTo': None, 'ValidFrom': None,
                 'ParameterData': None} for code, label in LABELS[kind].items()]}]
            return route.fulfill(content_type='application/json', body=corpus.wire({
                'IsSuccessful': True, 'Payload': catalog}))
        if route.request.url in {url for _, url in projection.L9_GRIDS}:
            self.requests.append((route.request.url, route.request.method))
            request = route.request.post_data_json
            index, = [i for i, (name, endpoint) in enumerate(projection.L9_GRIDS)
                      if endpoint == route.request.url and name.rsplit('/', 1)[1] == request['GroupType']]
            row = wire_asset(index)
            if self.detail_defect == 'one-grid-month' and index == 11:
                row['MonthYearAcquisition'] = '2024-01-01T23:00:00Z'
            return route.fulfill(content_type='application/json', body=corpus.wire({
                'IsSuccessful': True, 'Payload': {'Data': [row, row], 'TotalRecords': 2, 'Index': None}}))
        return super().route(route)

    def detail(self):
        grids = []
        for index, (name, endpoint) in enumerate(projection.L9_GRIDS):
            structure = projection.l9_grid_structure(index)
            component = structure['component']
            headings = list(HEADERS)
            if self.detail_defect == 'header' and index == 2:
                headings[0] = 'SYNTHETIC WRONG HEADER'
            outer, inner = structure['groups']
            if self.detail_defect == 'owner' and index == 2:
                inner = 'KELOMPOK 4'
            config = html.escape(json.dumps({'endpoint': endpoint, 'group': name.rsplit('/', 1)[1]}), quote=True)
            grid = ('<' + component + '><ui-grid><p-table data-grid="' + config + '"><table><thead><tr>'
                + ''.join('<th>' + html.escape(value) + '</th>' for value in headings) + '</tr></thead>'
                '<tbody><tr>' + '<td>SYNTHETIC BUSINESS BAIT</td>' * 9 + '</tr></tbody>'
                '<tfoot><tr><td colspan="7">SYNTHETIC BUSINESS BAIT</td><td>SYNTHETIC BUSINESS BAIT</td>'
                '<td></td></tr></tfoot></table><p-paginator><div class="p-paginator">'
                '<span class="p-paginator-current">Showing 1 to 2 of 2</span>'
                '<button class="p-paginator-prev" disabled>Prev</button>'
                '<button class="p-paginator-next" disabled>Next</button></div></p-paginator></p-table></ui-grid></' + component + '>')
            grids.append('<p-accordiontab><div class="p-accordion-header"><a aria-expanded="true">'
                '<span class="p-accordion-header-text">' + outer + '</span></a></div>'
                '<p-panel><span class="p-panel-title">' + inner + '</span>' + grid + '</p-panel></p-accordiontab>')
        tabs, panels = [], []
        for index, name in enumerate(observer.FORMS):
            enabled = name in ('Induk', 'L9') or name == 'L2' and self.detail_defect == 'unprojected-form'
            tabs.append('<li' + ('' if enabled else ' class="p-disabled"') + '><a role="tab" '
                'aria-controls="panel-' + str(index) + '" href="#" onclick="show(' + str(index)
                + ');return false">' + name + '</a></li>')
            content = ('<rshshr-citr-main-form><label>SYNTHETIC STRUCTURE</label></rshshr-citr-main-form>'
                if name == 'Induk' else '<rshshr-citr-l9-form>' + ''.join(grids) + '</rshshr-citr-l9-form>'
                if name == 'L9' else '<rshshr-citr-l2-form><label>SYNTHETIC STRUCTURE</label></rshshr-citr-l2-form>'
                if enabled else '')
            panels.append('<div class="p-tabview-panel" role="tabpanel" id="panel-' + str(index)
                + '"' + ('' if name == 'Induk' else ' style="display:none"') + '>' + content + '</div>')
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + ''.join(tabs) + '</ul><div class="p-tabview-panels">'
            + ''.join(panels) + '</div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        # The natural reference GETs run through the page-level SPA cache
        # (natural_refs registered in __init__), so only the L9 block styles
        # are added here.
        return super().document().replace('</head>', '<style>ui-grid,p-panel,p-accordiontab,'
            'rshshr-citr-l2-form{display:block}</style></head>')


@pytest.mark.parametrize('defect', [None, 'one-grid-month', 'unprojected-form', 'migrated', 'header', 'owner'])
def test_real_observer_original_custody_held_replay_and_reopened_full_l9(
        browser, tmp_path, monkeypatch, shared_catalog_contract, defect):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    fixture = Fixture(browser, monkeypatch, shared_catalog_contract, defect=defect)
    forms_seen, decoded, fallback = [], [], []
    original_observe, original_adapt = driver.observe_corporate_forms, adapter.adapt_corporate_detail
    def observe(*args, **kwargs):
        forms = original_observe(*args, **kwargs)
        forms_seen.append(deepcopy(forms))
        return forms
    def project(*args, **kwargs):
        result = original_adapt(*args, **kwargs)
        decoded.append(deepcopy(result))
        return result
    def dom(*args, **kwargs):
        fallback.append(True)
        return {'capture_complete': False, 'sections': [{'name': 'DOM-FALLBACK-SENTINEL'}],
                'errors': [], 'attachments': []}
    monkeypatch.setattr(driver, 'observe_corporate_forms', observe)
    monkeypatch.setattr(adapter, 'adapt_corporate_detail', project)
    monkeypatch.setattr(driver, 'capture_detail', dom)
    # Financial PDFs remain an independent acceptance gate; no fabricated PDF.
    monkeypatch.setattr(driver, 'capture_financial_detail', lambda *a, **k: {
        'capture_complete': False, 'errors': [], 'attachments': []})
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            native = driver._hybrid_detail(page, fixture.record, corpus.SCOPE, tmp_path, capture, 10, None)
            forms, = forms_seen
            assert forms is not None
            binding, = [f for f in forms if f['name'] == 'L9']
            result, = decoded
            expected_native = defect is None
            assert native['detail_source']['used'] == ('json' if expected_native else 'dom')
            assert bool(fallback) is not expected_native
            assert native['capture_complete'] is False  # Independent PDF deliberately not certified.
            if defect not in ('header', 'owner'):
                assert binding['projection']['kind'] == 'corporate-l9-details-v1'
            manifest = capture.drain()
            assert manifest['complete'] and manifest['component_lifetime']['same_document']
            held_record = {**fixture.record, 'detail_url': ROUTE}
            held = checkpoint_bodies(tmp_path, manifest, held_record, corpus.SCOPE)
            assert original_adapt(held, held_record, corpus.SCOPE, forms) == result
            assert next(p for p in held if p['context']['url'] == corpus.PRIMARY_URL)['body'] == fixture.raw
            if expected_native:
                overridden = deepcopy(manifest)
                overridden['responses'][0]['component_lifetime'] = dict(manifest['component_lifetime'])
                with pytest.raises(adapter.JsonSafetyError):
                    checkpoint_bodies(tmp_path, overridden, held_record, corpus.SCOPE)
                section, = [s for s in native['sections'] if s['name'] == 'L9']
                assert section['projection_complete'] and not section['unprojected_grids']
                assert len(section['tables']) == 12 and len(section['custody_tables']) == 13
                run = source_run('PPh Badan', [section])
                run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
                reports = []
                out = tmp_path / 'saved'
                paths = exporter.export_split_workbooks(run, out, mapping_reports=reports)
                name, = [name for name in paths if name != 'resume.xlsx']
                book = load_workbook(out / name)
                try:
                    rows = [row for row in book['L9'] if row[0].value == 'SYNTHETIC-001']
                    assert len(rows) == 24 and all(row[2].value == '02-2024' for row in rows)
                    assert all(row[3].value == 1235 and row[7].value == 26 for row in rows)
                    assert reports[0]['complete'] and reports[0]['unmapped_rows'] == 0
                finally:
                    book.close()
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
    finally:
        fixture.close()
