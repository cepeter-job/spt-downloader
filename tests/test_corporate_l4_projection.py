"""Reviewed L4 final-income projection contracts; GitHub-runner execution only.

Block A maps each approved template column to one literal payload control of the
pinned L4 owner, re-checks the owner's own IncomeTax = round(base*rate/100) rule,
and reconciles the declared footer with both the row sums and the stored totals.
Block B stays deliberately unprojected: its JENIS PENGHASILAN cell is rendered
from a runtime reference catalog this capture never binds.
"""
import json

import pytest

import coretax_corporate_projection as projection
from coretax_json import _UnsupportedMetadata, _corporate_json, adapt_corporate_detail
import support_json_corpus as corpus
from support_templates import section, source_run


GRID = projection.CORPORATE_L4_GRID_URL
FOOTER = projection.CORPORATE_L4_FOOTER_URL
DETAIL = corpus.FRAME_URL
ROWS = [{'TIN': '0000000000000002', 'Name': 'SYNTHETIC FINAL PAYER', 'TaxObjectCode': '28-423-99',
         'TaxObject': 'SYNTHETIC FINAL OBJECT', 'TaxBase': 1000, 'TaxRate': 2, 'IncomeTax': 20,
         'TaxBaseUsd': 0.0, 'IncomeTaxUsd': 0.0, 'RecordId': 'SYNTHETIC-ROW',
         'IsManually': False, 'TableSource': None, 'Action': None, 'Index': 0,
         'WithholdingDate': None, 'WithholdingSlipsAggregateIdentifier': 'SYNTHETIC-AGGREGATE'},
        {'TIN': '0000000000000003', 'Name': 'SYNTHETIC SECOND PAYER', 'TaxObjectCode': '28-411-01',
         'TaxObject': 'SYNTHETIC SECOND OBJECT', 'TaxBase': 250, 'TaxRate': 4.38,
         'IncomeTax': 11, 'TaxBaseUsd': 0.0, 'IncomeTaxUsd': 0.0, 'RecordId': 'SYNTHETIC-ROW-2',
         'IsManually': False, 'TableSource': None, 'Action': None, 'Index': 1,
         'WithholdingDate': None, 'WithholdingSlipsAggregateIdentifier': 'SYNTHETIC-AGGREGATE-2'}]


def root(**overrides):
    value = {'TotalTaxBase': 1250, 'TotalFinalIncomeTaxPayable': 31,
             'TotalFinalIncomeTaxPayableUsd': 0.0, 'TotalGrossIncome': 500,
             'ListOfIncomeExcludedFromIncomeTax': [{'TaxObjectCode': '1', 'TypeOfIncome': '1',
                                                    'IncomeSource': 'SYNTHETIC SOURCE',
                                                    'GrossIncome': 500}]}
    value.update(overrides)
    return value


def footer(**overrides):
    value = {'TaxBase': 1250, 'IncomeTax': 31, 'TaxBaseUsd': 0.0, 'IncomeTaxUsd': 0.0}
    value.update(overrides)
    return value


def pages(total=None, *, rows=None, size=10):
    values = ROWS if rows is None else rows
    return [{'offset': 0, 'rows': size, 'total': len(values) if total is None else total,
             'data': values}]


def project(form=None, *, footer_value=None, page_list=None, **overrides):
    options = {'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    crop = _corporate_json(json.dumps(root() if form is None else form))
    capture = [{'offset': page['offset'], 'rows': page['rows'], 'total': page['total'],
                'data': _corporate_json(json.dumps(page['data']))}
               for page in (pages() if page_list is None else page_list)]
    return projection.project_l4(crop, footer=_corporate_json(
        json.dumps(footer() if footer_value is None else footer_value)), pages=capture, **options)


def request(first, **overrides):
    value = {'ReturnSheetRecordId': corpus.RECORD_ID, 'LanguageId': 'id-ID', 'First': first,
             'Rows': 10, 'SortField': '', 'SortOrder': 1, 'Filters': [],
             'PeriodYear': str(corpus.SCOPE[1])}
    value.update(overrides)
    return value


def bindings(page_requests=None):
    return [{'name': 'L4', 'paths': [[projection.L4_ROOT]], 'grids': [
                {'name': projection.L4_GRID_NAME, 'endpoint': GRID,
                 'pages': [{'request_json': item, 'offset': item['First']}
                           for item in (page_requests or [request(0)])]}],
            'responses': [],
            'dependencies': [{'endpoint': FOOTER,
                              'request_json': {'ReturnSheetRecordId': corpus.RECORD_ID}}],
            'projection': {'kind': 'corporate-l4-v1',
                           'builds': {projection.CIT_SOURCE: projection.BUILD_DIGESTS[projection.CIT_SOURCE]},
                           'route': DETAIL}}]


def observed(page_requests=None):
    forms = corpus.observed()
    forms.extend(bindings(page_requests))
    return forms


def tokens(value):
    """Fixture-only JSON number tokens for the raw payload shape."""
    if isinstance(value, dict):
        return {key: tokens(item) for key, item in value.items()}
    if isinstance(value, list):
        return [tokens(item) for item in value]
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return corpus.Number(str(value))
    return value


def primary(form=None):
    value = corpus.current_form()
    value[projection.L4_ROOT] = tokens(root() if form is None else form)
    return corpus.primary(value)


def packets(page_requests=None, data=None, *, footer_value=None, include=('grid', 'footer')):
    values = [primary(data)]
    if 'grid' in include:
        for index, item in enumerate(page_requests or [request(0)]):
            values.append(corpus.packet({'IsSuccessful': True, 'Payload': {
                'TotalRecords': len(ROWS), 'Data': ROWS, 'Index': None}}, index + 2,
                endpoint=GRID, request=item))
    if 'footer' in include:
        values.append(corpus.packet({'IsSuccessful': True, 'Payload': footer_value or footer()},
                                    len(values) + 1, endpoint=FOOTER,
                                    request={'ReturnSheetRecordId': corpus.RECORD_ID}))
    return values


def adapt(forms=None, raw=None, record=None):
    return adapt_corporate_detail(iter(packets() if raw is None else raw),
                                  corpus.selected_record() if record is None else record,
                                  corpus.SCOPE, observed() if forms is None else forms)


def test_every_block_a_column_comes_from_one_proven_payload_control():
    result = project()
    table, excluded = result['tables']
    assert table['headers'] == projection.L4_A_HEADERS
    assert table['body_row_count'] == table['source_total'] == 2 and table['complete']
    assert table['rows'][:2] == [
        ['0000000000000002', 'SYNTHETIC FINAL PAYER', '28-423-99', 'SYNTHETIC FINAL OBJECT',
         '1.000', '2,00', '20'],
        ['0000000000000003', 'SYNTHETIC SECOND PAYER', '28-411-01', 'SYNTHETIC SECOND OBJECT',
         '250', '4,38', '11']]
    assert table['footer'] == [['', '', '', '', '1.250', '', '31']]
    assert table['footer_spans'] == projection.L4_A_SPANS
    assert table['rows'][2:] == table['footer']
    assert excluded['headers'] == projection.L4_B_HEADERS
    assert result['fields'] == []
    evidence = {(entry['source'], tuple(entry['path'])) for entry in result['provenance']}
    for key in projection.L4_ROW_FIELDS:
        assert ('grid', ('Data', 0, key)) in evidence
    assert ('footer', (projection.L4_ROOT, 'TotalTaxBase')) in evidence
    assert ('footer', (projection.L4_ROOT, 'TotalFinalIncomeTaxPayable')) in evidence
    columns = {entry['path'][-1]: entry['destination']['column']
               for entry in result['provenance']
               if entry['source'] == 'grid' and 'column' in entry['destination']}
    assert columns == {'TIN': 1, 'Name': 2, 'TaxObjectCode': 3, 'TaxObject': 4,
                       'TaxBase': 5, 'TaxRate': 6, 'IncomeTax': 7}


def test_block_b_stays_unprojected_and_keeps_the_section_honestly_partial():
    result = project()
    excluded = result['tables'][1]
    assert excluded['complete'] is False and excluded['body_row_count'] == 1
    assert excluded['rows'] == [['', '', '', '', '']]
    assert result['unprojected_reason'] == projection.L4_UNPROJECTED_REASON
    entry, = [item for item in result['provenance'] if item['rule'] == 'unprojected-dynamic-reference-label']
    assert entry['path'] == [projection.L4_ROOT, 'ListOfIncomeExcludedFromIncomeTax', 0, 'TypeOfIncome']
    # A taxpayer with no block B rows has nothing to render, so the block is complete.
    empty = project(root(ListOfIncomeExcludedFromIncomeTax=None, TotalGrossIncome=0))
    assert empty['tables'][1]['complete'] is True and empty['unprojected_reason'] is None


def test_row_and_footer_arithmetic_must_reconcile_exactly():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(footer_value=footer(TaxBase=1249))
    assert str(error.value) == 'unreconciled_corporate_l4_final_totals'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(root(TotalFinalIncomeTaxPayable=30))
    assert str(error.value) == 'unreconciled_corporate_l4_final_totals'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(root(TotalGrossIncome=499))
    assert str(error.value) == 'unreconciled_corporate_l4_gross_income'
    defect = dict(ROWS[0], IncomeTax=21)
    with pytest.raises(_UnsupportedMetadata) as error:
        project(page_list=pages(rows=[defect, ROWS[1]]))
    assert str(error.value) == 'unreconciled_corporate_l4_income_tax'


@pytest.mark.parametrize('mutation,reason', [
    ({'Synthetic': 0}, 'unsupported_corporate_l4_source_shape'),
    ({'TotalTaxBase': '1250'}, 'unsupported_corporate_l4_number_type'),
    ({'TotalTaxBase': True}, 'unsupported_corporate_l4_number_type'),
    ({'TotalFinalIncomeTaxPayable': 30.5}, 'unsupported_corporate_l4_number_precision'),
])
def test_unreviewed_root_shapes_refuse(mutation, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(root(**mutation))
    assert str(error.value) == reason


@pytest.mark.parametrize('row,reason', [
    ({'TaxBase': '1000'}, 'unsupported_corporate_l4_number_type'),
    ({'TaxBase': True}, 'unsupported_corporate_l4_number_type'),
    ({'IncomeTax': 20.5}, 'unsupported_corporate_l4_number_precision'),
    ({'TaxBase': -1000, 'IncomeTax': -20}, 'unsupported_corporate_l4_negative_amount'),
    ({'TaxRate': '2'}, 'unsupported_corporate_l4_rate_type'),
    ({'TaxRate': 2.005}, 'unsupported_corporate_l4_rate_precision'),
    ({'TaxRate': 101}, 'unsupported_corporate_l4_rate_precision'),
    ({'TaxObject': 7}, 'unsupported_corporate_l4_text'),
    ({'Action': 'EditButton'}, 'unsupported_corporate_l4_grid_metadata'),
    ({'Index': '1'}, 'unsupported_corporate_l4_grid_metadata'),
    ({'RecordId': ''}, 'unsupported_corporate_l4_grid_metadata'),
    ({'IsManually': 'true'}, 'unsupported_corporate_l4_grid_metadata'),
    ({'TaxBaseUsd': '0.0'}, 'unsupported_corporate_l4_grid_metadata'),
    ({'UnreviewedColumn': 0}, 'unsupported_corporate_l4_grid_metadata'),
])
def test_unreviewed_grid_row_shapes_refuse(row, reason):
    defect = dict(ROWS[0], **row)
    with pytest.raises(_UnsupportedMetadata) as error:
        project(page_list=pages(rows=[defect]))
    assert str(error.value) == reason


def test_a_grid_row_without_a_displayed_column_refuses():
    defect = {key: value for key, value in ROWS[0].items() if key != 'TaxObject'}
    with pytest.raises(_UnsupportedMetadata) as error:
        project(page_list=pages(rows=[defect, ROWS[1]]))
    assert str(error.value) == 'unsupported_corporate_l4_grid_row'


@pytest.mark.parametrize('page,reason', [
    ({'offset': 1, 'rows': 10, 'total': 1}, 'incomplete_corporate_l4_pages'),
    ({'offset': 0, 'rows': 7, 'total': 1}, 'incomplete_corporate_l4_pages'),
    ({'offset': 0, 'rows': 10, 'total': 3}, 'incomplete_corporate_l4_pages'),
    ({'offset': 0, 'rows': 10, 'total': 100001}, 'incomplete_corporate_l4_pages'),
])
def test_incomplete_or_unreviewed_pages_refuse(page, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(page_list=[{**page, 'data': ROWS}])
    assert str(error.value) == reason


def test_excluded_rows_must_keep_the_reviewed_payload_shape():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(root(ListOfIncomeExcludedFromIncomeTax=[{'TaxObjectCode': '1'}]))
    assert str(error.value) == 'unsupported_corporate_l4_excluded_row'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(root(ListOfIncomeExcludedFromIncomeTax={'TaxObjectCode': '1'}))
    assert str(error.value) == 'unsupported_corporate_l4_excluded_body'


@pytest.mark.parametrize('amount,reason', [
    ('500', 'unsupported_corporate_l4_amount_type'),
    (1000000000000000, 'unsupported_corporate_l4_amount_precision'),
])
def test_unreviewed_block_b_amounts_refuse(amount, reason):
    row = {'TaxObjectCode': '1', 'TypeOfIncome': '1', 'IncomeSource': 'SYNTHETIC SOURCE',
           'GrossIncome': amount}
    with pytest.raises(_UnsupportedMetadata) as error:
        project(root(ListOfIncomeExcludedFromIncomeTax=[row]))
    assert str(error.value) == reason


def test_usd_totals_are_type_checked_even_though_they_are_not_projected():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(footer_value=footer(TaxBaseUsd='0'))
    assert str(error.value) == 'unsupported_corporate_l4_usd_type'


def test_an_unsafe_ordered_amount_sum_refuses():
    big = dict(ROWS[0], TaxBase=999999999999999, TaxRate=0, IncomeTax=0)
    with pytest.raises(_UnsupportedMetadata) as error:
        project(page_list=pages(rows=[big, dict(big, Index=1)]))
    assert str(error.value) == 'unsafe_corporate_l4_ordered_sum'


def test_l4_defects_behind_the_top_level_gate_refuse_before_rendering():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(tax_type='ICT_ROGCIT')
    assert str(error.value) == 'unsupported_corporate_l4_source_shape'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(locale='en-US')
    assert str(error.value) == 'unsupported_corporate_l4_source_shape'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(footer_value={'TaxBase': 1250})
    assert str(error.value) == 'unsupported_corporate_l4_source_shape'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(page_list=[])
    assert str(error.value) == 'unsupported_corporate_l4_source_shape'


@pytest.mark.parametrize('projection_value', [
    {'kind': 'corporate-l4-v0'},
    {'kind': 'corporate-l4-v1', 'builds': {}, 'route': DETAIL},
    {'kind': 'corporate-l4-v1',
     'builds': {projection.CIT_SOURCE: 'APPROVED'}, 'route': DETAIL},
    {'kind': 'corporate-l4-v1', 'builds': {projection.CIT_SOURCE: 'a' * 64},
     'route': DETAIL, 'locale': 'id-ID'},
])
def test_projection_proof_must_match_the_reviewed_shape(projection_value):
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L4']
    binding['projection'] = projection_value
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l4_binding'


def test_grid_and_footer_bindings_are_part_of_the_admission_proof():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L4']
    binding['grids'] = []
    result = adapt(forms, raw=packets(include=('footer',)))
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l4_grid_binding'
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L4']
    binding['dependencies'] = []
    result = adapt(forms, raw=packets(include=('grid',)))
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l4_footer_binding'


def test_unreviewed_page_requests_refuse_the_projection():
    modified = [request(0, SortField='TaxBase')]
    result = adapt(observed(modified), raw=packets(modified))
    assert not result['eligible'] and result['reason'] == 'unsupported_corporate_l4_page_request'


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L4']
    binding['projection'] = {**binding['projection'], 'route': DETAIL + '/changed'}
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l4_binding'
    forms = observed()
    # Drop the Induk projection so this isolates the L4 lifecycle gate.
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l4_submitted_lifecycle'


def test_projected_l4_section_replaces_the_dump_and_reports_the_shortfall():
    forms = observed()
    result = adapt(forms)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section_value, = [item for item in result['sections'] if item['name'] == 'L4']
    assert [table['headers'] for table in section_value['tables']] == [
        projection.L4_A_HEADERS, projection.L4_B_HEADERS]
    assert not any(table['headers'] == ['JSON path', 'JSON type', 'Source value']
                   for table in section_value['tables'])
    assert section_value['fields'] == []
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L4']
    assert projected['kind'] == 'corporate-l4-v1'
    assert projected['unprojected_reason'] == projection.L4_UNPROJECTED_REASON
    grid_entries = {entry['path'][-1] for entry in projected['values']
                    if entry.get('source') == 'grid' and 'column' in entry['destination']}
    assert grid_entries == set(projection.L4_ROW_FIELDS)
    footer_entry, = [entry for entry in projected['values'] if entry.get('source') == 'footer'
                     and entry['path'][-1] == 'TotalTaxBase']
    assert footer_entry['container'] == ['Payload']
    assert footer_entry['response_sequence'] == 3


def test_capture_without_the_declared_footer_response_refuses():
    result = adapt(raw=packets()[:-1])
    assert not result['eligible']
    assert 'missing_declared_corporate_source_response' in result['reason']


def packet_map(*, page=None, footer_payload=None, page_request=None):
    from coretax_json import _corporate_request_key
    request_value = page_request or request(0)
    return {(GRID, _corporate_request_key(request_value)): {
                'payload': tokens(page or {'TotalRecords': 0, 'Data': [], 'Index': None}),
                'event': {'sequence': 2}},
            (FOOTER, _corporate_request_key({'ReturnSheetRecordId': corpus.RECORD_ID})): {
                'payload': tokens(footer_payload or {'TaxBase': 0, 'IncomeTax': 0,
                                                     'TaxBaseUsd': 0, 'IncomeTaxUsd': 0}),
                'event': {'sequence': 3}}}


def refusal(binding, packets):
    section_value = {'name': 'L4', 'fields': [], 'tables': [], 'text': ''}
    with pytest.raises(_UnsupportedMetadata) as error:
        projection._apply_l4(binding, section_value, [binding], root=root(),
            payload={'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL'},
            record=corpus.selected_record(), event={'frame_url': DETAIL, 'sequence': 1},
            auxiliary_packets=packets)
    assert section_value['tables'] == []
    return str(error.value)


@pytest.mark.parametrize('case,reason', [
    ('no-packets', 'incomplete_corporate_l4_auxiliary_packets'),
    ('extra-packet', 'incomplete_corporate_l4_auxiliary_packets'),
    ('no-pages', 'missing_corporate_l4_page_requests'),
    ('extra-declaration-key', 'unverified_corporate_l4_grid_binding'),
    ('bad-page-envelope', 'unsupported_corporate_l4_page_payload'),
    ('declared-responses', 'unverified_corporate_l4_binding'),
    ('foreign-footer', 'unverified_corporate_l4_footer_binding'),
])
def test_projection_refuses_unproved_grid_and_footer_packets(case, reason):
    binding, = bindings()
    packets = packet_map()
    if case == 'no-packets':
        packets = {}
    elif case == 'extra-packet':
        from coretax_json import _corporate_request_key
        packets[(FOOTER, _corporate_request_key(
            {'ReturnSheetRecordId': corpus.RECORD_ID, 'PeriodYear': '2024'}))] = \
            {'payload': tokens({'TaxBase': 0, 'IncomeTax': 0,
                                'TaxBaseUsd': 0, 'IncomeTaxUsd': 0}),
             'event': {'sequence': 4}}
    elif case == 'no-pages':
        binding['grids'][0]['pages'] = []
    elif case == 'extra-declaration-key':
        binding['grids'][0]['pages'][0]['unreviewed'] = 0
    elif case == 'bad-page-envelope':
        packets[(GRID, next(iter(packets))[1])]['payload'] = {
            'TotalRecords': 0, 'Data': [], 'Index': 'unreviewed'}
    elif case == 'declared-responses':
        binding['responses'] = [{'name': 'L4/extra', 'endpoint': GRID, 'requests': [request(0)]}]
    else:
        binding['dependencies'][0]['request_json'] = {'ReturnSheetRecordId': 'OTHER'}
    assert refusal(binding, packets) == reason


def test_l4_projection_does_not_mutate_source_bindings_or_payload():
    from copy import deepcopy
    forms = observed()
    before = deepcopy(forms)
    payload = primary()
    raw = payload['body']
    adapt(forms, raw=[payload, *packets()[1:]])
    assert forms == before and payload['body'] == raw


def test_projected_l4_binds_every_template_amount_cell(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    result = project()
    run = source_run('PPh Badan', [section('L4', tables=result['tables'], fields=result['fields'])])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L4']
        assert [sheet.cell(3, column).value for column in range(1, 8)] == [
            '0000000000000002', 'SYNTHETIC FINAL PAYER', '28-423-99',
            'SYNTHETIC FINAL OBJECT', 1000, '2,00', 20]
        assert [sheet.cell(4, column).value for column in range(1, 8)] == [
            'TOTAL', None, None, None, 1250, None, 31]
        assert sheet.cell(3, 5).data_type == 'n' and sheet.cell(3, 7).data_type == 'n'
        assert sheet.cell(4, 5).data_type == 'n' and sheet.cell(4, 7).data_type == 'n'
        assert 'Rp' in sheet.cell(4, 7).number_format
        # Block B stays blank; its rows are reported, never guessed.
        assert sheet.cell(9, 5).value is None and sheet.cell(9, 3).value is None
        assert sheet.cell(9, 1).value == 'JUMLAH'
        assert reports[0]['complete'] is False
        assert reports[0]['unmapped_tables'] == 1 and reports[0]['unmapped_rows'] == 1
        assert reports[0]['unmapped_fields'] == 0
    finally:
        book.close()
