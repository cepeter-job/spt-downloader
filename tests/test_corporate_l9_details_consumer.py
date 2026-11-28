"""Original-packet L9 details consumer contract, separate from catalog admission.

The shared producer is independently owned. shared_catalog_contract injects its
five source-reviewed singleton registrations into the EXISTING maps for this
consumer's hosted tests only; it changes no ordering/version/packet algorithm.
These tests are NOT evidence that the unintegrated production registry admits
those classes. The integration blocker is recorded in the L9 report.
"""
from copy import deepcopy

import pytest

import coretax_corporate_projection as projection
import coretax_json as adapter
import support_json_corpus as corpus
from test_corporate_l9_grids import asset, LABELS, HEADERS
from conftest import pin_override
from test_corporate_l9_projection import (ROUTE, selected, lifetime, grid_declarations,
    observed as recap_bindings, payload_form)


@pytest.fixture
def shared_catalog_contract(monkeypatch):
    # Test-local interface injection only, not a competing production registry.
    for kind in LABELS:
        url = corpus.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + kind
        monkeypatch.setitem(adapter.CORPORATE_REFERENCE_REQUESTS, url, (kind,))
        monkeypatch.setitem(adapter.CORPORATE_L11A_REFERENCE_URLS, kind, url)
    return {kind: next(url for url, kinds in adapter.CORPORATE_REFERENCE_REQUESTS.items()
                       if kinds == (kind,)) for kind in LABELS}


def clock():
    return {'attempt': corpus.ATTEMPT, 'start_ms': 1735689600000, 'end_ms': 1735689600001,
            'timezone': 'Asia/Jakarta'}


def recap():
    values = {name: corpus.Number('51') for name in projection.L9_TABLE_TOTALS}
    values.update(TotalFiscalDepreciationTangible=corpus.Number('357'),
        TotalCommercialDepreciationTangible=corpus.Number('300'),
        DiferencesDepreciationTangible=corpus.Number('57'),
        TotalFiscalAmortization=corpus.Number('255'),
        TotalCommercialAmortization=corpus.Number('200'), DiferencesAmortization=corpus.Number('55'))
    return values


def wire_asset(index):
    row = asset(index)
    for key in ('AcquisitionPrice', 'RemainingBeginningValue', 'FiscalYearValue', 'Index'):
        row[key] = corpus.Number(str(row[key]))
    return row


def bindings(urls):
    result = recap_bindings()
    grids = grid_declarations()
    for grid in grids:
        grid['pages'][0]['request_json']['Filters'] = []
    result[1]['grids'] = grids
    tables = []
    for index in range(12):
        structure = projection.l9_grid_structure(index)
        tables.append({'component': structure['component'], 'source_structure': structure,
                       'headers': list(HEADERS), 'footer_spans': [[7, 1, 1]]})
    result[1]['projection'] = {'kind': 'corporate-l9-details-v1',
        'builds': dict(projection.L9_DETAIL_BUILD_DIGESTS), 'route': ROUTE,
        'locale': 'id-ID', 'timezone': 'Asia/Jakarta', 'tables': tables,
        'references': [{'endpoint': urls[kind], 'method': 'GET', 'sequences': [index + 14]}
                       for index, kind in enumerate(projection.L9_REFERENCE_KINDS)]}
    return result


def packets(urls, mutate=None):
    form = corpus.current_form()
    form['MainFormData']['IsMigrated'] = False
    form[projection.L9_ROOT] = payload_form(recap())
    if mutate is not None:
        mutate(form)
    body = [corpus.primary(form)]
    for index, grid in enumerate(bindings(urls)[1]['grids']):
        body.append(corpus.packet({'IsSuccessful': True, 'Payload': {'TotalRecords': 2,
            'Data': [wire_asset(index), wire_asset(index)], 'Index': None}}, index + 2,
            endpoint=grid['endpoint'], request=grid['pages'][0]['request_json']))
    for index, kind in enumerate(projection.L9_REFERENCE_KINDS):
        catalog = [{'ReferenceDataType': kind, 'language': 'id-ID',
            'Details': [{'Code': code, 'CodeDescription': label, 'ValidFrom': None, 'ValidTo': None,
                         'ParameterData': None} for code, label in LABELS[kind].items()]}]
        item = corpus.packet({'IsSuccessful': True, 'Payload': catalog}, index + 14,
            endpoint=urls[kind], request=None)
        item['context']['method'] = 'GET'
        body.append(item)
    for item in body:
        item['context'].update(frame_url=ROUTE, component_lifetime=lifetime(), clock_interval=clock())
    return body


def adapt(urls, *, forms=None, raw=None):
    return adapter.adapt_corporate_detail(iter(packets(urls) if raw is None else raw), selected(),
        corpus.SCOPE, bindings(urls) if forms is None else forms)


def test_all_populated_grids_use_original_packets_and_reopen_all_template_cells(
        shared_catalog_contract, tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    urls = shared_catalog_contract
    raw, forms = packets(urls), bindings(urls)
    before = deepcopy((raw, forms))
    result = adapt(urls, forms=forms, raw=raw)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [s for s in result['sections'] if s['name'] == 'L9']
    assert section['projection_complete'] is True and section['unprojected_grids'] == []
    assert len(section['tables']) == 12 and all(t['body_row_count'] == 2 for t in section['tables'])
    assert len(section['custody_tables']) == 13
    assert all(t['headers'] == ['JSON path', 'JSON type', 'Source value'] for t in section['custody_tables'])
    assert all(len(t['rows']) == 26 for t in section['custody_tables'][1:])
    assert not adapter.has_audit_dump_tables(result['sections'])
    assert adapter.has_audit_dump_tables([*result['sections'], {'name': 'L2', 'fields': [],
        'tables': [{'headers': ['JSON path', 'JSON type', 'Source value']}]}])
    assert (raw, forms) == before
    proof, = [p for p in result['provenance']['projections'] if p['form'] == 'L9']
    for index in range(12):
        values = [v for v in proof['values'] if v['destination'].get('table') == projection.L9_GRIDS[index][0]
                  and v.get('source') == 'grid']
        assert values and {v['response_sequence'] for v in values} == {index + 2}
        assert all(v['container'] == ['Payload'] for v in values)
        assert {v['path'][-1] for v in values if v['path'][:2] == ['Data', 1]} == set(asset(index))
        assert any(v['response_sha256'] == raw[index + 1]['context']['sha256'] for v in values)
    run = source_run('PPh Badan', [section])
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [name for name in paths if name != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L9']
        body = [row for row in sheet if row[0].value == 'SYNTHETIC-001']
        assert len(body) == 24
        assert all(row[2].value == '02-2024' and row[3].value == 1235 and row[7].value == 26 for row in body)
        assert all(row[3].data_type == row[7].data_type == 'n' for row in body)
        assert len([row for row in sheet if row[0].value == 'TOTAL' and row[7].value == 51]) == 12
        assert reports[0]['complete'] and reports[0]['unmapped_rows'] == 0
    finally:
        book.close()


def test_unproved_one_grid_keeps_exact_marker_custody_and_whole_record_gate(shared_catalog_contract, tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    urls = shared_catalog_contract
    raw = packets(urls)
    item = raw[8]
    request = item['context']['request_json']
    broken = corpus.packet({'IsSuccessful': True, 'Payload': {'Data': [wire_asset(7)],
        'TotalRecords': 1, 'Index': None}}, 9, endpoint=item['context']['url'], request=request)
    broken['payload']['Payload']['Data'][0]['MonthYearAcquisition'] = '2024-02-01T23:00:00Z'
    broken = corpus.packet(broken['payload'], 9, endpoint=item['context']['url'], request=request)
    broken['context'].update(frame_url=ROUTE, component_lifetime=lifetime(), clock_interval=clock())
    raw[8] = broken
    result = adapt(urls, raw=raw)
    assert result['eligible'], result['reason']
    section = result['sections'][1]
    assert section['unprojected_grids'] == [projection.L9_GRIDS[7][0]]
    assert section['projection_complete'] is False and len(section['custody_tables']) == 13
    assert adapter.has_audit_dump_tables(result['sections'])
    assert section['projection_reason'] == 'unprojected_l9_detail_grids'
    run = source_run('PPh Badan', [section])
    reports = []
    exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert not reports[0]['complete'] and reports[0]['derived_reason'] == 'unprojected_l9_detail_grids'
    assert reports[0]['unmapped_tables'] == 1
    run['template_mapping'] = reports
    exporter.export_workbook(run, tmp_path / 'audit.xlsx', include_details=False)
    book = load_workbook(tmp_path / 'audit.xlsx')
    try:
        assert any('masih ada grid rincian L9' in str(cell.value) for row in book['Audit'] for cell in row)
    finally:
        book.close()


@pytest.mark.parametrize('defect', ['main_pin', 'vendor_pin', 'missing_configured_pin', 'timezone',
    'table_owner', 'headers', 'spacer', 'missing_reference', 'wrong_sequence', 'duplicate_sequence',
    'query_rows', 'query_filter', 'no_clock'])
def test_details_proof_and_original_custody_refuse_closed_defects(shared_catalog_contract, monkeypatch, defect):
    urls = shared_catalog_contract
    raw, forms = packets(urls), bindings(urls)
    proof = forms[1]['projection']
    if defect in ('main_pin', 'vendor_pin'):
        proof['builds'][projection.MAIN_SOURCE if defect == 'main_pin' else projection.VENDOR_SOURCE] = 'a' * 64
    elif defect == 'missing_configured_pin':
        pin_override(monkeypatch, {})
    elif defect == 'timezone':
        proof['timezone'] = 'UTC'
    elif defect == 'table_owner':
        proof['tables'][4]['source_structure']['groups'] = ['HARTA TIDAK BERWUJUD', 'KELOMPOK LAINNYA']
    elif defect == 'headers':
        proof['tables'][4]['headers'] = HEADERS[:-1]
    elif defect == 'spacer':
        proof['tables'][4]['footer_spans'] = [[], [7, 1, 1]]
    elif defect == 'missing_reference':
        proof['references'].pop()
    elif defect == 'wrong_sequence':
        proof['references'][0]['sequences'] = [2]
    elif defect == 'duplicate_sequence':
        proof['references'][0]['sequences'] *= 2
    elif defect in ('query_rows', 'query_filter'):
        forms[1]['grids'][0]['pages'][0]['request_json']['Rows' if defect == 'query_rows' else 'Filters'] = 20 if defect == 'query_rows' else {}
        raw[1]['context']['request_json'] = deepcopy(forms[1]['grids'][0]['pages'][0]['request_json'])
    else:
        for item in raw:
            item['context'].pop('clock_interval')
    if defect == 'duplicate_sequence':
        with pytest.raises(adapter.JsonSafetyError):
            adapt(urls, raw=raw, forms=forms)
    else:
        result = adapt(urls, raw=raw, forms=forms)
        assert not result['eligible'], defect


def replace_catalog(raw, details, *, interval=None):
    item = raw[13]
    payload = deepcopy(item['payload'])
    payload['Payload'][0]['Details'] = details
    changed = corpus.packet(payload, 14, endpoint=item['context']['url'], request=None)
    changed['context'].update(frame_url=ROUTE, method='GET', component_lifetime=lifetime(),
        clock_interval=clock() if interval is None else interval)
    raw[13] = changed
    if interval is not None:
        for item in raw:
            item['context']['clock_interval'] = dict(interval)


def test_duplicate_catalog_labels_use_original_display_order_and_selected_path(shared_catalog_contract):
    raw = packets(shared_catalog_contract)
    base = {'Code': 'SYNTHETIC-001', 'ValidFrom': None, 'ValidTo': None}
    replace_catalog(raw, [{**base, 'CodeDescription': 'Z SYNTHETIC LABEL', 'ParameterData': '{"DisplayIndex":2}'},
        {**base, 'CodeDescription': 'A SYNTHETIC LABEL', 'ParameterData': '{"DisplayIndex":1}'}])
    result = adapt(shared_catalog_contract, raw=raw)
    assert result['eligible'], result['reason']
    assert result['sections'][1]['tables'][0]['rows'][0][1] == 'A SYNTHETIC LABEL'
    proof = result['provenance']['projections'][1]
    selected = [entry for entry in proof['values'] if entry['destination'].get('column') == 1
        and entry['path'] == [0, 'Details', 1, 'CodeDescription']]
    assert selected and all(entry['response_sequence'] == 14 for entry in selected)
    assert all(entry['catalog_order_rule'] == 'reviewed-cache-display-index-integer' for entry in selected)


@pytest.mark.parametrize('defect', ['mixed-order', 'unstable-version'])
def test_catalog_order_and_original_attempt_clock_negatives_refuse(shared_catalog_contract, defect):
    raw = packets(shared_catalog_contract)
    base = {'Code': 'SYNTHETIC-001', 'ValidFrom': None, 'ValidTo': None}
    if defect == 'mixed-order':
        replace_catalog(raw, [{**base, 'CodeDescription': 'A SYNTHETIC', 'ParameterData': '{"DisplayIndex":1}'},
            {**base, 'CodeDescription': 'B SYNTHETIC', 'ParameterData': '{"DisplayIndex":"2"}'}])
        reason = 'mixed_reference_display_index_types'
    else:
        replace_catalog(raw, [{**base, 'CodeDescription': 'A SYNTHETIC', 'ValidTo': '2025-01-01T00:00:00.000Z'},
            {**base, 'CodeDescription': 'B SYNTHETIC', 'ValidTo': '2026-01-01T00:00:00.000Z'}],
            interval={**clock(), 'start_ms': 1735689599999})
        reason = 'unstable_grid_reference_version'
    result = adapt(shared_catalog_contract, raw=raw)
    assert not result['eligible'] and result['reason'] == reason


def test_full_projected_l9_survives_save_output_physical_verifier_and_reopen(shared_catalog_contract, tmp_path):
    import coretax
    from openpyxl import load_workbook
    result = adapt(shared_catalog_contract)
    assert result['eligible'], result['reason']
    record = selected()
    record.update(capture_complete=True, sections=result['sections'])
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
           'complete': True, 'errors': [], 'records': [record]}
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    report, = [report for report in run['template_mapping'] if report['form'] == 'L9']
    assert report['complete'] and report['unmapped_tables'] == report['unmapped_rows'] == 0
    name, = [name for name in run['output_files'] if name != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        rows = [row for row in book['L9'] if row[0].value == 'SYNTHETIC-001']
        assert len(rows) == 24 and all(row[2].value == '02-2024' and row[7].value == 26 for row in rows)
    finally:
        book.close()
