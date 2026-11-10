"""Exact live-shaped synthetic L3 packets through owned native/export custody.

Runner-only regressions. The existing fixture's eight-field/date-only defaults
are untouched; only this test's original routed response bytes are extended.
PDF absence must remain PARTIAL even after the JSON source is native-verified.
"""
from copy import deepcopy
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
import coretax_json as adapter
from coretax_corporate import observe_forms
from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l3_observer_fixture import Fixture, ASSET
from test_corporate_l3_native import DETAIL, GRID, FOOTER, REFERENCES, OWNERS, request
from test_corporate_l3_observer import open_selected
from test_corporate_l3_projection import HEADERS, SPANS
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


BASE_FIELDS = {'RecordId', 'Name', 'TIN', 'TaxType', 'TaxBase', 'IncomeTax',
               'WithholdingSlipsNumber', 'WithholdingSlipsDate'}
METADATA = {'IncomeTaxUsd': ('number', '0'), 'IsManually': ('boolean', True),
            'TableSource': ('null', None), 'Index': ('number', '0'), 'Action': ('null', None)}
DATES = {0: ('2024-02-29T00:00:00+07:00', '29-02-2024'),
         10: ('2025-01-01T00:00:00+07:00', '01-01-2025')}
FOOTERS = [['JUMLAH', '50', '40', ''],
           ['KREDIT PAJAK LUAR NEGERI', '', '1', ''],
           ['JUMLAH KREDIT PAJAK', '', '41', '']]


def live_fixture(browser, monkeypatch, *, model='Normal', footer_order='early'):
    fixture = Fixture(browser, monkeypatch, model=model, footer_order=footer_order)
    # Routes read these bytes only after the trusted View/tab actions. No shared
    # fixture constructor, DOM, request, paginator, catalog or default is changed.
    for first, raw in fixture.grid_raw.items():
        value = json.loads(raw)
        assert set(value['Payload']) == {'TotalRecords', 'Data'}
        for row in value['Payload']['Data']:
            assert set(row) == BASE_FIELDS
            row.update(IncomeTaxUsd=0, IsManually=True, TableSource=None, Index=0, Action=None,
                       WithholdingSlipsDate=DATES[first][0])
            assert set(row) == BASE_FIELDS | METADATA.keys()
        fixture.grid_raw[first] = corpus.wire(value).encode()
    value = json.loads(fixture.raw)
    # Exercise the actual current-Induk enabled binding, not a caller-invented
    # visibility proof or a synthetic outer flag added by the regression.
    del value['Payload']['IsIncomeTaxOverseas']
    assert json.loads(value['Payload']['CurrentFormData'])['MainFormData']['IsIncomeTaxOverseas'] == 1
    if model != 'Normal':
        value['Payload']['PreviousFormData'] = '{}'
    fixture.raw = corpus.wire(value).encode()
    return fixture


def assert_owned(forms, fixture):
    assert forms is not None
    assert [form['name'] for form in forms] == ['Induk', 'L3', 'L1-B', 'L8']
    proof = forms[1]['projection']
    assert proof['kind'] == 'corporate-l3-v1' and proof['builds'] == fixture.pins
    assert proof['visibility_binding'] == 'current-induk-enabled-v1'
    assert proof['route'] == DETAIL
    assert proof['locale'] == 'id-ID' and proof['timezone'] == 'Asia/Jakarta'
    assert [table['component'] for table in proof['tables']] == OWNERS
    assert [table['headers'] for table in proof['tables']] == HEADERS
    assert [table['footer_spans'] for table in proof['tables']] == SPANS
    assert forms[1]['responses'][0]['requests'] == [request(0), request(10)]


def assert_original_bodies(bodies, fixture):
    assert len(bodies) == 8
    assert next(p['body'] for p in bodies if p['context']['url'] == corpus.PRIMARY_URL) == fixture.raw
    assert next(p['body'] for p in bodies if p['context']['url'] == FOOTER) == fixture.footer_raw
    for item in bodies:
        context = item['context']
        if context['url'] == GRID:
            assert item['body'] == fixture.grid_raw[context['request_json']['First']]
        elif context['url'] in REFERENCES.values():
            assert item['body'] == fixture.reference_raw[context['url']]


def assert_live_projection(result, bodies):
    section, = [s for s in result['sections'] if s['name'] == 'L3']
    a, b = section['tables']
    assert [a['body_row_count'], b['body_row_count']] == [2, 12]
    assert b['headers'] == HEADERS[1] and b['footer_spans'] == SPANS[1]
    expected = [[str(local + 1), 'SYNTHETIC DOMESTIC', '0000000000000002',
                 'SYNTHETIC TAX', '5', '3', '000001', DATES[first][1]]
                for first, count in ((0, 10), (10, 2)) for local in range(count)]
    assert all(len(row) == 8 for row in b['rows'][:12])
    assert b['rows'] == expected + FOOTERS and b['footer'] == FOOTERS
    assert b['source_total'] == 12 and b['complete'] is True
    # Identical source rows are separate occurrences; source Index=0 is never
    # used as either a global or local displayed row number.
    assert b['rows'][0][1:] == b['rows'][9][1:]
    assert b['rows'][10][1:] == b['rows'][11][1:]
    assert a['rows'][0][3] == '02-12-2025'  # Existing A UTC conversion is intact.
    projection, = [p for p in result['provenance']['projections'] if p['form'] == 'L3']
    assert projection['visibility_binding'] == 'current-induk-enabled-v1'
    evidence = projection['values']
    pages = sorted((p for p in bodies if p['context']['url'] == GRID),
                   key=lambda p: p['context']['request_json']['First'])
    metadata_entries = [e for e in evidence if e.get('source') == 'grid'
                        and e['path'][-1] in METADATA]
    assert len(metadata_entries) == 60
    for page_index, item in enumerate(pages):
        first = item['context']['request_json']['First']
        count = 10 if first == 0 else 2
        for local in range(count):
            for field, (kind, value) in METADATA.items():
                entry, = [e for e in metadata_entries if e['page_index'] == page_index
                          and e['path'] == ['Data', local, field]]
                assert entry['response_sequence'] == item['context']['sequence']
                assert entry['container'] == ['Payload']
                assert entry['type'] == kind and type(entry['value']) is type(value) and entry['value'] == value
                assert entry['destination']['table'] == 'L3/domestic'
                assert entry['destination']['row'] == first + local
                assert 'column' not in entry['destination']  # No invented USD/action cell.
            date, = [e for e in evidence if e.get('source') == 'grid'
                     and e['page_index'] == page_index
                     and e['path'] == ['Data', local, 'WithholdingSlipsDate']]
            assert date['type'] == 'string' and date['value'] == DATES[first][0]
            assert date['response_sequence'] == item['context']['sequence'] and date['container'] == ['Payload']
            assert date['destination'] == {'table': 'L3/domestic', 'row': first + local, 'column': 7}
    footer, = [p for p in bodies if p['context']['url'] == FOOTER]
    assert any(e.get('source') == 'footer' and e['path'] == ['IncomeTax']
               and e['response_sequence'] == footer['context']['sequence']
               and e['container'] == ['Payload'] and e['type'] == 'number' and e['value'] == '40'
               for e in evidence)
    # The captured40 differs from the12 body rows'36; saved totals must not be
    # silently replaced by a body sum or by stored model totals999.
    return expected


@pytest.mark.parametrize('model,footer_order', [('Normal', 'early'), ('Amendment 002', 'late')])
def test_owned_live_l3_native_source_held_replay_and_saved_workbook_keep_independent_gates(
        browser, tmp_path, monkeypatch, model, footer_order):
    fixture = live_fixture(browser, monkeypatch, model=model, footer_order=footer_order)
    original_observe = driver.observe_corporate_forms
    observed, decoded, source_events = [], [], []
    original_record = driver.diagnostics.record

    def observe(*args, **kwargs):
        forms = original_observe(*args, **kwargs)
        observed.append(deepcopy(forms))
        return forms

    def project(*args, **kwargs):
        assert capture.drain()['complete'] is True
        result = adapt_corporate_detail(*args, **kwargs)
        # Fail at the real adapter reason on RED, before whole-record DOM
        # fallback would intentionally read the fixture's trapped business bait.
        assert result['eligible'] and result['coverage']['complete'], result['reason']
        decoded.append(deepcopy(result))
        return result

    def record(event, **fields):
        if event == 'detail.source':
            source_events.append(dict(fields))
        return original_record(event, **fields)

    monkeypatch.setattr(driver, 'CIT_SOURCE_SHA256', fixture.pins[ASSET])
    monkeypatch.setattr(driver, 'observe_corporate_forms', observe)
    monkeypatch.setattr(adapter, 'adapt_corporate_detail', project)
    monkeypatch.setattr(driver.diagnostics, 'record', record)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            native = driver._hybrid_detail(page, fixture.record, corpus.SCOPE, tmp_path, capture, 1000, None)
            forms, = observed
            assert_owned(forms, fixture)
            manifest = capture.drain()
            assert manifest['complete'] is True and manifest['component_lifetime']['same_document'] is True
            bodies = list(capture.iter_bodies())
            assert_original_bodies(bodies, fixture)
            result, = decoded
            expected = assert_live_projection(result, bodies)
            assert source_events == [{'source_requested': 'json-first', 'source_used': 'json',
                                      'source_reason': 'native_verified'}]
            audit = native['detail_source']
            assert audit['requested'] == 'json-first' and audit['used'] == 'json'
            assert audit['reason'] == 'verified_native_corporate_source'
            assert audit['capture'] == manifest and audit['coverage']['complete'] is True
            assert audit['json'] == result['provenance'] and native['sections'] == result['sections']
            # This fixture has no attachment control. Run the real PDF discovery;
            # do not mock a downloaded document or promote capture to COMPLETE.
            assert native['capture_complete'] is False and native['errors']
            attachment, = native['attachments']
            assert attachment['status'] == 'PARTIAL' and attachment['relative_path'] == ''
            assert not list(tmp_path.rglob('*.pdf'))
            fixture.record['detail_url'] = DETAIL
            before = deepcopy((bodies, forms, fixture.record))
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                                           fixture.record, corpus.SCOPE, forms)
            assert replay == result and (bodies, forms, fixture.record) == before
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(native)
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': False, 'errors': deepcopy(native['errors']), 'records': [fixture.record]}
        export = tmp_path / 'export'
        coretax.save_output(run, export, json_source=tmp_path)
        coretax.verify_outputs(run, export)
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        assert model in name
        book = load_workbook(export / name)
        try:
            sheet = book['L3']
            assert sheet['D3'].value == '02-12-2025' and sheet.max_row < 40
            # Locate by the preserved slip identifier, not new template slots.
            body = [list(row[:8]) for row in sheet.iter_rows(values_only=True) if row[6] == '000001']
            assert body == [[*row[:4], int(row[4]), int(row[5]), *row[6:]] for row in expected]
            assert [row[0].value for row in sheet
                    if row[0].value in {r[0] for r in FOOTERS}] == ['JUMLAH', *[r[0] for r in FOOTERS]]
            # L3-A also has a JUMLAH footer. Bind these three totals to the
            # already-verified domestic body, rather than matching both tables.
            last_body_row = max(row[0].row for row in sheet if row[6].value == '000001')
            footer_rows = [row for row in sheet.iter_rows(min_row=last_body_row + 1)
                           if row[0].value in {r[0] for r in FOOTERS}]
            assert [row[0].value for row in footer_rows] == [r[0] for r in FOOTERS]
            totals = [row[5] for row in footer_rows]
            assert [cell.value for cell in totals] == [40, 1, 41]
            assert all('Rp' in cell.number_format and '0.00' not in cell.number_format for cell in totals)
            assert not any(cell.value == 'Data sumber tambahan / belum dipetakan' for row in sheet for cell in row)
        finally:
            book.close()
        mapping, = [r for r in run['template_mapping'] if r['form'] == 'L3']
        assert mapping['complete'] is False and mapping['unmapped_fields'] == 2
        assert mapping['unmapped_rows'] == mapping['unmapped_tables'] == 0
        induk, = [r for r in run['template_mapping'] if r['form'] == 'Induk']
        assert induk['complete'] is False
        saved = json.loads((export / 'run.json').read_text(encoding='utf-8'))
        assert saved['complete'] is False and saved['records'][0]['capture_complete'] is False
        assert saved['records'][0]['detail_source']['used'] == 'json'
        assert saved['output_attachments'] == []
        published = adapt_corporate_detail(checkpoint_bodies(export, manifest, fixture.record, corpus.SCOPE,
            published=True, output_layout=run['json_output_layout']), fixture.record, corpus.SCOPE, forms)
        assert published == result
        assert fixture.unexpected == []
        assert fixture.requests.count((GRID, 'POST')) == 2 and fixture.requests.count((FOOTER, 'POST')) == 1
        assert (fixture.requests.index((FOOTER, 'POST')) < fixture.requests.index((GRID, 'POST'))) is (footer_order == 'early')
        assert all(fixture.requests.count((url, 'GET')) == 1 for url in REFERENCES.values())
    finally:
        fixture.close()


@pytest.mark.parametrize('field,value,reason', [
    ('IsManually', 1, 'unsupported_corporate_l3_domestic_row'),
    ('Index', False, 'unsupported_corporate_l3_number_type'),
    ('IncomeTaxUsd', '0', 'unsupported_corporate_l3_number_type'),
    ('TableSource', 'TAXPAYER_ACCOUNTING', 'unsupported_corporate_l3_domestic_row'),
    ('Action', {}, 'unsupported_corporate_l3_domestic_row'),
])
def test_owned_complete_capture_with_unreviewed_l3_metadata_refuses_projection_not_transport(
        browser, tmp_path, monkeypatch, field, value, reason):
    fixture = live_fixture(browser, monkeypatch)
    changed = json.loads(fixture.grid_raw[10])
    changed['Payload']['Data'][-1][field] = value
    fixture.grid_raw[10] = corpus.wire(changed).encode()
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert_owned(forms, fixture)
            manifest = capture.drain()
            assert manifest['complete'] is True
            bodies = list(capture.iter_bodies())
            assert_original_bodies(bodies, fixture)
            before = deepcopy((bodies, forms, fixture.record))
            result = adapt_corporate_detail(iter(bodies), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] is False and result['sections'] == []
            assert reason in result['reason'].split(',')
            assert 'unsupported_corporate_l3_date' not in result['reason']
            assert 'incomplete_corporate_l3_pages' not in result['reason']
            assert (bodies, forms, fixture.record) == before
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                                           fixture.record, corpus.SCOPE, forms)
            assert replay == result
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
    finally:
        fixture.close()


def test_owned_live_l3_changed_held_metadata_bytes_cannot_be_replayed(browser, tmp_path, monkeypatch):
    fixture = live_fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert_owned(forms, fixture)
            manifest = capture.drain()
            assert manifest['complete'] is True
            fixture.record['detail_url'] = DETAIL
            held = checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE)
            assert_original_bodies(held, fixture)
            descriptor, = [d for d in manifest['responses'] if d['url'] == GRID and d['request_json']['First'] == 10]
            target = tmp_path / descriptor['relative_path']
            value = json.loads(fixture.grid_raw[10])
            value['Payload']['Data'][-1]['Index'] = 1
            changed = corpus.wire(value).encode()
            assert len(changed) == descriptor['bytes'] and changed != fixture.grid_raw[10]
            target.write_bytes(changed)  # Same length, valid JSON, unchanged manifest/hash proof.
            with pytest.raises(JsonSafetyError, match='response bytes changed'):
                list(capture.iter_bodies())
            with pytest.raises(JsonSafetyError, match='response bytes changed'):
                checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE)
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('bound', [False, True])
def test_owned_live_l3_metadata_snapshot_change_is_fatal_even_before_projection(
        browser, tmp_path, monkeypatch, bound):
    fixture = live_fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert_owned(forms, fixture)
            value = json.loads(fixture.grid_raw[0])
            value['Payload']['Data'][0]['IsManually'] = False
            fixture.grid_raw[0] = corpus.wire(value).encode()
            # Repeat an already admitted fixture query, with a real new request
            # object and response. No malformed pagination or invented sequence.
            page.evaluate('''async ({url, body}) => {
                await (await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'},
                    body:JSON.stringify(body)})).json();
            }''', {'url': GRID, 'body': request(0)})
            manifest = capture.drain()
            assert manifest['complete'] is True
            bodies = list(capture.iter_bodies())
            repeated = [p for p in bodies if p['context']['url'] == GRID and p['context']['request_json']['First'] == 0]
            assert len(repeated) == 2 and repeated[0]['body'] != repeated[1]['body']
            before = deepcopy((bodies, forms))
            with pytest.raises(JsonSafetyError, match='snapshot'):
                adapt_corporate_detail(iter(bodies), fixture.record, corpus.SCOPE, forms if bound else [])
            assert (bodies, forms) == before
            fixture.record['detail_url'] = DETAIL
            with pytest.raises(JsonSafetyError, match='snapshot'):
                adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                                       fixture.record, corpus.SCOPE, forms if bound else [])
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
    finally:
        fixture.close()
