"""Synthetic L11-B observer -> original capture -> held -> workbook (Actions)."""
import html
import json
from copy import deepcopy

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
import coretax_corporate_projection as projection
from coretax_corporate import observe_forms
from coretax_json import adapt_corporate_detail, JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture as BaseFixture, ASSET
from test_corporate_l11b_hydrated import populated, primary, tables, selected_hydrated
from test_corporate_l11b_projection import route
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, part_ii=True, defect=None):
        self.part_ii = part_ii
        super().__init__(browser, monkeypatch, defect=defect)
        self.record = selected_hydrated()
        self.raw = primary(populated(**({} if part_ii else {'BorrowingCostExpense': corpus.Number('1')})))['body']
        monkeypatch.setattr(projection, 'BUILD_DIGESTS', {url: digest for url, digest in self.pins.items()
                                                       if url != projection.VENDOR_SOURCE})
        monkeypatch.setattr(projection, 'L11B_HYDRATED_BUILD_DIGESTS', self.pins, raising=False)

    def detail(self):
        groups = [projection.L11B_GROUPS[i] for i in ((0, 1, 2) if self.part_ii else (2,))]
        grids = []
        for index, (metadata, group) in enumerate(zip(tables(self.part_ii), groups)):
            owner, headers, spans = metadata['component'], metadata['headers'], metadata['footer_spans'][0]
            if self.defect == 'header' and index == 0: headers[0] += ' FOREIGN'
            footer = ''.join('<td colspan="' + str(span) + '">SYNTHETIC FOOTER BAIT</td>' for span in spans)
            body = '<tr>' + '<td>SYNTHETIC BODY BAIT<input value="SYNTHETIC INPUT"></td>' * len(headers) + '</tr>'
            table = ('<p-table><table><thead><tr>' + ''.join('<th>' + html.escape(h) + '</th>' for h in headers)
                     + '</tr></thead><tbody>' + body + '</tbody><tfoot><tr>' + footer + '</tr></tfoot></table></p-table>')
            if self.defect == 'wrapper': wrapper = 'ui-grid'
            else: wrapper = 'ui-grid-offline'
            grids.append('<p-accordiontab><div class="p-accordion-header"><a href="#" aria-expanded="true">'
                '<span class="p-accordion-header-text">' + html.escape(group) + '</span></a></div>'
                '<div class="p-accordion-content"><' + owner + '><' + wrapper + '>' + table
                + '</' + wrapper + '></' + owner + '></div></p-accordiontab>')
        # Part II's outer accordion is a real group in the source.
        if self.part_ii:
            grids[:2] = ['<p-accordiontab><div class="p-accordion-header"><a href="#" aria-expanded="true">'
                '<span class="p-accordion-header-text">' + projection.L11B_PART_II_GROUP + '</span></a></div>'
                '<div class="p-accordion-content">' + ''.join(grids[:2]) + '</div></p-accordiontab>']
        form = '<rshshr-citr-l11b-form><p-accordion>' + ''.join(grids) + '</p-accordion></rshshr-citr-l11b-form>'
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i) + '" href="#" onclick="show('
            + str(i) + ');return false">' + caption + '</a></li>' for i, caption in enumerate(('Induk', 'L11-B')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" id="panel-0"><rshshr-citr-main-form>SYNTHETIC STRUCTURE</rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" id="panel-1" style="display:none">' + form
            + '</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        base = super().document()
        return base.replace('</head>', '<style>rshshr-citr-l11b-form,rsh-citr-l11b-form-grid1,'
            'rsh-citr-l11b-form-grid2,rsh-citr-l11b-form-grid3,ui-grid-offline{display:block}</style></head>')


def opened(fixture, capture):
    page, popup = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
        corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
    assert page is fixture.page and popup is False
    page.wait_for_function('window.primaryDone===true')
    assert capture.observe_component_lifetime() is not None, 'Fixture must own a fresh ICT_RCIT/ICT_RCITR SPA'
    return page


@pytest.mark.parametrize('part_ii', [True, False])
def test_owned_l11b_populated_view_is_saved_and_held_replayed_without_dom_values(
        browser, tmp_path, monkeypatch, part_ii):
    fixture = Fixture(browser, monkeypatch, part_ii=part_ii)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = opened(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                  approved_digest=fixture.pins[ASSET])
            assert forms is not None
            proof = next(f['projection'] for f in forms if f['name'] == 'L11-B')
            assert proof['kind'] == 'corporate-l11b-hydrated-v2'
            assert proof['part_ii'] is part_ii
            manifest = capture.drain()
            assert manifest['complete'] and manifest['component_lifetime']['same_document']
            bodies = list(capture.iter_bodies())
            assert bodies[0]['body'] == fixture.raw
            result = adapt_corporate_detail(iter(bodies), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'], result['reason']
            fixture.record['detail_url'] = route()
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                                            fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        section = next(s for s in result['sections'] if s['name'] == 'L11-B')
        assert len(section['fields']) == 6 and len(section['tables']) == (4 if part_ii else 2)
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        coretax.verify_outputs(run, tmp_path / 'export')
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        book = load_workbook(tmp_path / 'export' / name)
        try:
            sheet = book['L11-B']
            assert sheet['B6'].value == 1250000 and sheet['B7'].value == 312500
            assert sum(cell.value == '0007' for row in sheet for cell in row) == (2 if part_ii else 0)
            assert any(cell.data_type == 'f' for row in sheet for cell in row) is part_ii
        finally: book.close()
        mapping = next(r for r in run['template_mapping'] if r['form'] == 'L11-B')
        assert mapping['complete'] is False and mapping['derived_reason'] == 'unprojected_l11b_header_question'
        assert fixture.unexpected == []
    finally: fixture.close()


@pytest.mark.parametrize('defect', ['header', 'wrapper', 'vendor-pin', 'main-fetch-only'])
def test_unproven_l11b_owned_structure_refuses(browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = opened(fixture, capture)
            assert observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                 approved_digest=fixture.pins[ASSET]) is None
    finally: fixture.close()


def test_stop_in_l11b_provider_probe_is_not_fallback(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = opened(fixture, capture)
            evaluate = page.evaluate
            stopped = []
            def wrapped(script, *args):
                result = evaluate(script, *args)
                if args == (projection.VENDOR_SOURCE,): stopped.append(True)
                return result
            monkeypatch.setattr(page, 'evaluate', wrapped)
            def cancel():
                if stopped: raise KeyboardInterrupt
            with pytest.raises(KeyboardInterrupt):
                observe_forms(page, fixture.record, corpus.SCOPE, capture,
                              approved_digest=fixture.pins[ASSET], check_cancel=cancel)
    finally: fixture.close()


@pytest.mark.parametrize('profile,part_ii', [('manual', True), ('manual', False), ('null-defaults', True)])
def test_l11b_actual_hybrid_json_complete_source_both_held_readers_and_partial_audit(
        browser, tmp_path, monkeypatch, profile, part_ii):
    from coretax_json_capture import json_custody
    from test_corporate_l11b_defaults import default_packet
    fixture = Fixture(browser, monkeypatch, part_ii=part_ii)
    if profile == 'null-defaults':
        fixture.raw = default_packet()['body']
    observed, decoded, events = [], [], []
    monkeypatch.setattr(driver, 'CIT_SOURCE_SHA256', fixture.pins[ASSET])
    original_observe = driver.observe_corporate_forms
    original_adapter = adapt_corporate_detail
    original_record = driver.diagnostics.record

    def observe(*args, **kwargs):
        forms = original_observe(*args, **kwargs)
        observed.append(deepcopy(forms))
        return forms

    def adapter(*args, **kwargs):
        result = original_adapter(*args, **kwargs)
        # Assert before fallback: DOM business bait must never hide adapter RED.
        assert result['eligible'] and result['coverage']['complete'], result['reason']
        decoded.append(deepcopy(result))
        return result

    def record(event, **fields):
        if event == 'detail.source': events.append(fields)
        return original_record(event, **fields)

    monkeypatch.setattr(driver, 'observe_corporate_forms', observe)
    monkeypatch.setattr('coretax_json.adapt_corporate_detail', adapter)
    monkeypatch.setattr(driver.diagnostics, 'record', record)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = opened(fixture, capture)
            native = driver._hybrid_detail(page, fixture.record, corpus.SCOPE, tmp_path, capture, 1000, None)
            manifest = capture.drain()
            assert manifest['complete'] is True
            forms, = observed
            result, = decoded
            assert events == [{'source_requested': 'json-first', 'source_used': 'json', 'source_reason': 'native_verified'}]
            assert native['detail_source']['used'] == 'json'
            assert native['detail_source']['coverage']['complete'] is True
            # Missing financial attachment is a separate real PARTIAL, not mocked success.
            assert native['capture_complete'] is False and native['errors']
            fixture.record['detail_url'] = route()
            live = list(capture.iter_bodies())
            assert len(live) == 1 and live[0]['body'] == fixture.raw
            held = checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE)
            assert held == live
            assert original_adapter(iter(held), fixture.record, corpus.SCOPE, forms) == result
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(native)
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': False, 'errors': deepcopy(native['errors']), 'records': [fixture.record]}
        with json_custody(run, tmp_path, published=False) as (items, streams):
            body, = [item for item in items if item['source_path'].endswith('response-0001.json')]
            assert streams[body['relative_path']].read() == fixture.raw
        export = tmp_path / 'export'
        coretax.save_output(run, export, json_source=tmp_path)
        coretax.verify_outputs(run, export)
        published = checkpoint_bodies(export, manifest, fixture.record, corpus.SCOPE,
            published=True, output_layout=run['json_output_layout'])
        assert original_adapter(iter(published), fixture.record, corpus.SCOPE, forms) == result
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        book = load_workbook(export / name)
        try:
            sheet = book['L11-B']
            assert [sheet.cell(row, 2).value for row in range(2, 8)] == (
                [0] * 6 if profile == 'null-defaults' else
                [1000000, 200000, 50000, 400000 if part_ii else 1, 1250000, 312500])
            assert sum(cell.value == '0007' for row in sheet for cell in row) == (2 if part_ii else 0)
        finally: book.close()
        saved = json.loads((export / 'run.json').read_text(encoding='utf-8'))
        assert saved['complete'] is False and saved['records'][0]['detail_source']['used'] == 'json'
        mapping, = [m for m in saved['template_mapping'] if m['form'] == 'L11-B']
        assert mapping['complete'] is False and mapping['derived_reason'] == 'unprojected_l11b_header_question'
        resume = load_workbook(export / 'resume.xlsx')
        try:
            assert any('header/pertanyaan L11-B' in str(cell.value) for sheet in resume for row in sheet for cell in row)
        finally: resume.close()
        assert fixture.unexpected == []
    finally: fixture.close()


@pytest.mark.parametrize('defect', ['attempt', 'descriptor'])
def test_l11b_held_lifetime_cannot_be_overridden(browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = opened(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms is not None
            manifest = capture.drain()
        fixture.record['detail_url'] = route()
        if defect == 'attempt': manifest['component_lifetime']['attempt'] = 'b' * 32
        else: manifest['responses'][0]['component_lifetime'] = manifest['component_lifetime']
        with pytest.raises(JsonSafetyError):
            list(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE))
    finally: fixture.close()
