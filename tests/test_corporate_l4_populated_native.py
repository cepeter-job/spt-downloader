"""Original-packet and hosted owned-View populated L4 vertical slice."""
from copy import deepcopy
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
import coretax_corporate_projection as projection
from coretax_corporate import observe_forms
from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
import support_json_corpus as corpus
from test_corporate_l1d_native import DETAIL, packet as primary_packet
from test_corporate_l3_native import packet
from test_corporate_l7_native import bindings as legacy_bindings, selected
from test_corporate_l4_projection import ROOT, ROW, B_ROW, root, footer, request, table_proofs
from test_corporate_l4_populated import KINDS, LABELS
from test_json_hybrid_native import browser as browser

GRID, FOOTER = projection.CORPORATE_L4_GRID_URL, projection.CORPORATE_L4_FOOTER_URL
REFS = {kind: corpus.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + kind for kind in KINDS}


def original_packets():
    current = corpus.current_form()
    current[ROOT] = root(TotalTaxBase=12000, TotalFinalIncomeTaxPayable=240,
        TotalGrossIncome=1000.5, ListOfIncomeExcludedFromIncomeTax=[{**B_ROW, 'GrossIncome': 500.25}] * 2)
    value = {'IsSuccessful': True, 'Payload': {'TIN': corpus.NPWP, 'PeriodYear': 2025,
        'IsDraft': True, 'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PreviousFormData': None, 'LastSubmittedFormData': None, 'CurrentFormData': corpus.wire(current)}}
    values = [primary_packet(value)]
    for first, count in ((0, 10), (10, 2)):
        values.append(packet({'IsSuccessful': True, 'Payload': {'TotalRecords': 12,
            'Data': [ROW] * count, 'Index': None}}, len(values) + 1, GRID, request(First=first)))
    values.append(packet({'IsSuccessful': True, 'Payload': footer(TaxBase=12000, IncomeTax=240)},
        4, FOOTER, {'ReturnSheetRecordId': corpus.RECORD_ID, 'PeriodYear': '2025'}))
    for kind, endpoint in REFS.items():
        values.append(packet({'IsSuccessful': True, 'Payload': [{'ReferenceDataType': kind,
            'language': 'id-ID', 'Details': [{'Code': code, 'CodeDescription': text,
                'ValidFrom': None, 'ValidTo': None, 'ParameterData': '{}'}
                for code, text in LABELS[kind].items()]}]}, len(values) + 1, endpoint, None, method='GET'))
    for item in values:
        context = item['context']
        context['clock_interval'] = {'attempt': context['attempt'], 'start_ms': 1735689600000,
                                     'end_ms': 1735689601000, 'timezone': 'Asia/Jakarta'}
        context['corporate_reference_providers'] = {'kind': 'corporate-reference-providers-v1',
            'attempt': context['attempt'], 'record_id': context['record_id'],
            'source_url': context['component_lifetime']['source_url'], 'detail_url': DETAIL,
            'builds': dict(projection.L4_POPULATED_BUILD_DIGESTS)}
    return values


def populated_bindings():
    return [legacy_bindings()[0], {'name': 'L4', 'paths': [[ROOT]], 'grids': [{
        'name': projection.L4_GRID_NAME, 'endpoint': GRID, 'pages': [
            {'offset': first, 'request_json': request(First=first)} for first in (0, 10)]}],
        'responses': [], 'dependencies': [{'endpoint': FOOTER, 'request_json': {
            'ReturnSheetRecordId': corpus.RECORD_ID, 'PeriodYear': '2025'}}],
        'projection': {'kind': 'corporate-l4-populated-v2',
            'builds': dict(projection.L4_POPULATED_BUILD_DIGESTS), 'route': DETAIL,
            'locale': 'id-ID', 'timezone': 'Asia/Jakarta', 'tables': table_proofs(),
            'references': [{'endpoint': url, 'method': 'GET', 'sequences': [index + 5]}
                           for index, url in enumerate(REFS.values())],
            'visibility_binding': 'current-induk-enabled-v1'}}]


def retain_packet_custody(item, original):
    for key in ('clock_interval', 'corporate_reference_providers'):
        item['context'][key] = deepcopy(original['context'][key])
    return item


def adapt(raw=None, forms=None):
    return adapt_corporate_detail(iter(original_packets() if raw is None else raw),
        selected(), corpus.SCOPE, populated_bindings() if forms is None else forms)


def test_populated_original_pages_and_both_catalogs_project_without_mutation():
    raw, forms = original_packets(), populated_bindings()
    before = deepcopy((raw, forms))
    result = adapt(raw, forms)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert (raw, forms) == before
    value = next(s for s in result['sections'] if s['name'] == 'L4')
    assert [t['body_row_count'] for t in value['tables']] == [12, 2]
    proof = next(p for p in result['provenance']['projections'] if p['form'] == 'L4')
    assert proof['scope'] == 'source-bound-populated-both-blocks'
    entries = proof['values']
    for sequence, path in ((2, ['Data', 0, 'TIN']), (3, ['Data', 0, 'TIN']),
                           (4, ['TaxBase']), (5, [0, 'Details', 0, 'CodeDescription']),
                           (6, [0, 'Details', 0, 'CodeDescription'])):
        assert any(e['response_sequence'] == sequence and e['path'] == path
                   and e['container'] == ['Payload'] for e in entries)
    assert all(e['path'][0] != ROOT for e in entries if e['response_sequence'] == 4)


@pytest.mark.parametrize('case', ['missing-ref', 'failed-ref', 'wrong-sequence', 'duplicate-sequence',
    'bool-sequence', 'wrong-method', 'wrong-type', 'wrong-label', 'null-label', 'missing-pin',
    'wrong-pin', 'wrong-locale', 'wrong-timezone', 'no-lifetime', 'previous', 'model'])
def test_unproved_populated_catalog_render_or_lifecycle_refuses_without_replacing_sections(case):
    raw, forms = original_packets(), populated_bindings()
    proof = forms[1]['projection']
    if case == 'missing-ref': proof['references'].pop()
    elif case == 'failed-ref': raw[-1]['context']['status'] = 500
    elif case in ('wrong-sequence', 'duplicate-sequence', 'bool-sequence'):
        proof['references'][0]['sequences'] = {'wrong-sequence': [99],
            'duplicate-sequence': [5, 5], 'bool-sequence': [True]}[case]
    elif case == 'wrong-method': proof['references'][0]['method'] = 'POST'
    elif case in ('wrong-type', 'wrong-label', 'null-label'):
        value = json.loads(raw[-1]['body'])
        if case == 'wrong-type': value['Payload'][0]['ReferenceDataType'] = 'COUNTRY_CODE'
        else: value['Payload'][0]['Details'][0]['CodeDescription'] = '' if case == 'wrong-label' else None
        raw[-1] = retain_packet_custody(packet(value, 6, REFS[KINDS[1]], None, method='GET'), raw[-1])
    elif case == 'missing-pin': proof['builds'].pop(projection.MAIN_SOURCE)
    elif case == 'wrong-pin': proof['builds'][projection.MAIN_SOURCE] = 'a' * 64
    elif case == 'wrong-locale': proof['locale'] = 'en-US'
    elif case == 'wrong-timezone': proof['timezone'] = 'UTC'
    elif case == 'no-lifetime':
        for item in raw:
            item['context'].pop('component_lifetime')
            item['context'].pop('corporate_reference_providers')
    else:
        value = json.loads(raw[0]['body'])
        value['Payload']['PreviousFormData' if case == 'previous' else 'ReturnSheetModel'] = '{}'
        raw[0] = retain_packet_custody(primary_packet(value), raw[0])
    before = deepcopy((raw, forms))
    if case in ('duplicate-sequence', 'bool-sequence'):
        with pytest.raises(JsonSafetyError, match='sequence'): adapt(raw, forms)
    else:
        result = adapt(raw, forms)
        assert not result['eligible'] and result['sections'] == []
    assert (raw, forms) == before


@pytest.mark.parametrize('case', ['snapshot', 'locale', 'mixed-attempt', 'mixed-lifetime', 'footer'])
def test_original_bound_contradictions_remain_fatal_before_projection(case):
    raw = original_packets()
    if case == 'snapshot':
        item = json.loads(raw[-1]['body'])
        item['Payload'][0]['Details'][0]['CodeDescription'] = 'SYNTHETIC CHANGED'
        raw.append(retain_packet_custody(packet(item, 7, REFS[KINDS[1]], None, method='GET'), raw[-1]))
    elif case == 'locale':
        item = json.loads(raw[-1]['body'])
        item['Payload'][0]['language'] = 'en-US'
        raw[-1] = retain_packet_custody(packet(item, 6, REFS[KINDS[1]], None, method='GET'), raw[-1])
    elif case == 'mixed-attempt': raw[-1]['context']['attempt'] = 'b' * 32
    elif case == 'mixed-lifetime': raw[-1]['context'].pop('component_lifetime')
    else:
        raw[3] = retain_packet_custody(packet({'IsSuccessful': True, 'Payload': footer(TaxBase=1, IncomeTax=240)},
            4, FOOTER, {'ReturnSheetRecordId': corpus.RECORD_ID, 'PeriodYear': '2025'}), raw[3])
    with pytest.raises(JsonSafetyError): adapt(raw)


def test_duplicate_catalog_codes_follow_original_cache_order_and_keep_selected_raw_path():
    raw = original_packets()
    value = json.loads(raw[-1]['body'])
    row = value['Payload'][0]['Details'][0]
    row['CodeDescription'] = 'SYNTHETIC ZULU'
    value['Payload'][0]['Details'].append({**row, 'CodeDescription': 'SYNTHETIC ALPHA'})
    raw[-1] = retain_packet_custody(packet(value, 6, REFS[KINDS[1]], None, method='GET'), raw[-1])
    result = adapt(raw)
    assert result['eligible'], result['reason']
    section = next(s for s in result['sections'] if s['name'] == 'L4')
    assert section['tables'][1]['rows'][0][2] == 'SYNTHETIC ALPHA'
    proof = next(p for p in result['provenance']['projections'] if p['form'] == 'L4')
    assert any(e['path'] == [0, 'Details', 1, 'CodeDescription'] and e['response_sequence'] == 6
        and e.get('destination') == {'table': projection.L4_EXCLUDED_TABLE, 'row': 0, 'column': 2}
        for e in proof['values'])


def test_owned_populated_l4_capture_adapter_held_replay_and_reopened_workbook(browser, tmp_path, monkeypatch):
    from l4_observer_fixture import Fixture, ASSET
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page, popup = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
                corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
            assert page is fixture.page and not popup
            page.wait_for_function('window.primaryDone===true')
            assert capture.observe_component_lifetime()['same_document'] is True
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms is not None
            assert forms[1]['projection']['kind'] == 'corporate-l4-populated-v2'
            manifest = capture.drain()
            assert manifest['complete'] and manifest['component_lifetime']['same_document'] is True
            assert manifest['corporate_reference_providers']['builds'] == fixture.pins
            bodies = list(capture.iter_bodies())
            assert len(bodies) == 6
            for original in bodies:
                url = original['context']['url']
                expected = (fixture.raw if url == corpus.PRIMARY_URL else
                    fixture.grid_raw[original['context']['request_json']['First']] if url == GRID else
                    fixture.footer_raw if url == FOOTER else fixture.reference_raw[url])
                assert original['body'] == expected
            result = adapt_corporate_detail(iter(bodies), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        coretax.verify_outputs(run, tmp_path / 'export')
        mapping = next(r for r in run['template_mapping'] if r['form'] == 'L4')
        assert mapping['complete'] and mapping['unmapped_rows'] == mapping['unmapped_tables'] == 0
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        book = load_workbook(tmp_path / 'export' / name)
        try:
            sheet = book['L4']
            values = [cell.value for row in sheet for cell in row]
            assert values.count(ROW['TIN']) == 12
            assert values.count(LABELS[KINDS[0]][ROW['TaxObjectCode']]) == 12
            assert values.count(LABELS[KINDS[1]][B_ROW['TypeOfIncome']]) == 2
            assert ROW['TaxObject'] not in values and 'SYNTHETIC BODY BAIT' not in values
            rates = [r[5] for r in sheet if r[0].value == ROW['TIN']]
            # The approved L4 rate slot is General, not the separately approved
            # L2 percentage-fraction contract. Keep rendered percentage points.
            assert len(rates) == 12 and all(c.value == '2,00' and c.data_type == 's' for c in rates)
            gross = [r[4] for r in sheet if r[2].value == LABELS[KINDS[1]][B_ROW['TypeOfIncome']]]
            assert len(gross) == 2 and all(c.value == 500.25 and c.data_type == 'n' for c in gross)
            assert any(r[0].value == 'TOTAL' and r[4].value == 12000 and r[6].value == 240 for r in sheet)
            assert any(r[0].value == 'JUMLAH' and r[4].value == 1000.5 for r in sheet)
        finally: book.close()
        assert fixture.unexpected == []
        assert fixture.requests.count((GRID, 'POST')) == 2
        for url in REFS.values(): assert fixture.requests.count((url, 'GET')) == 1
    finally: fixture.close()


@pytest.mark.parametrize('defect', ['external-context', 'locale', 'timezone', 'vendor-pin',
    'corporate-fetch-only', 'main-fetch-only', 'vendor-fetch-only', 'missing-reference',
    'owner', 'wrong-ui-owner', 'header', 'footer', 'table-outside-p-table', 'duplicate-owner',
    'changed-header-after-page', 'changed-b-header-after-page'])
def test_unproved_populated_l4_observer_cannot_drop_b_or_grant_native_coverage(
        browser, tmp_path, monkeypatch, defect):
    from l4_observer_fixture import Fixture, ASSET
    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page, _ = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
                corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
            page.wait_for_function('window.primaryDone===true')
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            capture.drain()
            if forms is not None:
                result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
                assert not result['eligible'] and result['sections'] == []
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
    finally: fixture.close()


@pytest.mark.parametrize('phase', ['entry', 'after-next'])
def test_populated_l4_stop_is_cancellation_not_fallback_or_publication(browser, tmp_path, monkeypatch, phase):
    from l4_observer_fixture import Fixture, ASSET
    fixture = Fixture(browser, monkeypatch)
    stopped = []
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page, _ = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
                corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
            page.wait_for_function('window.primaryDone===true')
            def stop():
                if phase == 'entry' or fixture.requests.count((GRID, 'POST')) >= 2:
                    stopped.append(True)
                    raise driver.CaptureCancelled('SYNTHETIC L4 STOP')
            with pytest.raises(driver.CaptureCancelled):
                observe_forms(page, fixture.record, corpus.SCOPE, capture,
                              approved_digest=fixture.pins[ASSET], check_cancel=stop)
            assert stopped == [True] and not list(tmp_path.rglob('manifest.json'))
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        assert capture._component_document is None
    finally: fixture.close()


def test_populated_l4_late_same_document_route_detour_is_sticky_before_seal(browser, tmp_path, monkeypatch):
    from l4_observer_fixture import Fixture, ASSET
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page, _ = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
                corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
            page.wait_for_function('window.primaryDone===true')
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms and forms[1]['projection']['kind'] == 'corporate-l4-populated-v2'
            page.evaluate('url=>{history.pushState({},"",url+"&changed=true");history.replaceState({},"",url);}', DETAIL)
            with pytest.raises(JsonSafetyError): capture.drain()
            assert not list(tmp_path.rglob('manifest.json'))
    finally: fixture.close()


@pytest.mark.parametrize('owner', ['rshshr-citr-l4-grid1', 'rsh-citr-l4-grid2'])
def test_l4_headers_changed_during_shared_provider_work_cannot_use_earlier_metadata(
        browser, tmp_path, monkeypatch, owner):
    from l4_observer_fixture import Fixture, ASSET
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page, _ = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
                corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
            page.wait_for_function('window.primaryDone===true')
            observe = capture.observe_corporate_reference_providers
            changed = []
            def replace_header(**options):
                builds = observe(**options)
                assert builds == fixture.pins
                page.locator(owner + ' th').first.evaluate('(e)=>e.textContent="SYNTHETIC CHANGED AFTER PROVIDER"')
                changed.append(True)
                return builds
            monkeypatch.setattr(capture, 'observe_corporate_reference_providers', replace_header)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert changed == [True] and forms is None
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
    finally: fixture.close()
