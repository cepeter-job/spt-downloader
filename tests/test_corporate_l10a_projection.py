"""Reviewed L10-A (hubungan istimewa) projection contracts; GitHub-runner only.

The pinned L10-A panel owns no scalar control. Its declared root is patched
straight into a form group that only re-reads the two header values from
MainFormData, so the approved worksheet is exactly the reviewed l10a-grid row
model: nine literal columns whose captions are row 2 of the template sheet.
"""
import importlib

import pytest

from coretax_json import _CorporateNumber, adapt_corporate_detail
import support_json_corpus as corpus


GRID = corpus.ORIGIN + '/returnsheet/api/loadcit/l10a-grid'
ROOT = 'DeclarationTransactionRelatedParties'


def module():
    return importlib.import_module('coretax_corporate_projection')


def row(**overrides):
    value = {'RecordId': '00000000-0000-4000-8000-000000000010',
             'Name': 'SYNTHETIC RELATED PARTY', 'TIN': '0000000000000002',
             'Country': 'ID', 'RelationshipCode': '01',
             'BusinessActivity': 'SYNTHETIC ACTIVITY', 'TypeOfTransaction': '01',
             'TransactionValue': _CorporateNumber('1234.5'),
             'PricingMethod': '01', 'ReasonPricingMethod': 'SYNTHETIC REASON'}
    value.update(overrides)
    return value


def wire_row(**overrides):
    value = row(**overrides)
    value['TransactionValue'] = corpus.Number(str(value['TransactionValue']))
    return value


def project(rows=None, **overrides):
    helper = getattr(module(), 'project_l10a', None)
    assert callable(helper), 'Missing reviewed L10-A projection'
    options = {'headers': list(module().L10A_HEADERS), 'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    return helper([row()] if rows is None else rows, **options)


def request(first=0):
    return {'ReturnSheetRecordId': corpus.RECORD_ID, 'First': first, 'Rows': 10,
            'SortField': '', 'SortOrder': 1, 'Filters': [], 'LanguageId': 'id-ID'}


def grid_packet(rows, sequence=2, *, total=None, first=0):
    return corpus.packet({'IsSuccessful': True, 'Payload': {
        'TotalRecords': len(rows) if total is None else total, 'Data': rows, 'Index': None}},
        sequence, endpoint=GRID, request=request(first))


def proof(route=None):
    return {'kind': 'corporate-l10a-v1',
            'builds': {module().CIT_SOURCE: module().BUILD_DIGESTS[module().CIT_SOURCE]},
            'route': corpus.FRAME_URL if route is None else route}


def observed(projection=None, *, pages=None):
    forms = corpus.observed()
    forms.append({'name': 'L10-A', 'paths': [[ROOT]],
                  'grids': [{'name': 'L10-A/l10a-grid', 'endpoint': GRID,
                             'pages': pages if pages is not None
                             else [{'request_json': request(), 'offset': 0}]}],
                  'responses': [], 'dependencies': [],
                  'projection': proof() if projection is None else projection})
    return forms


def primary(value=(), *, included=True):
    form = corpus.current_form()
    if included:
        form[ROOT] = list(value)
    return corpus.primary(form)


def adapt(forms=None, packets=None, record=None):
    return adapt_corporate_detail(iter(packets if packets is not None
                                       else [primary(), grid_packet([wire_row()])]),
                                  corpus.selected_record() if record is None else record,
                                  corpus.SCOPE, observed() if forms is None else forms)


def test_caption_row_is_the_reviewed_grid_column_order():
    assert module().L10A_HEADERS == [
        'Nama', 'NPWP/TIN', 'Negara', 'BENTUK HUBUNGAN', 'Kegiatan Usaha', 'Jenis Transaksi',
        'NILAI TRANSAKSI (Rupiah)', 'METODE PENENTUAN HARGA TRANSFER YANG DIGUNAKAN',
        'ALASAN PENGGUNAAN METODE']
    assert module().L10A_COLUMNS == ('Name', 'TIN', 'Country', 'RelationshipCode',
        'BusinessActivity', 'TypeOfTransaction', 'TransactionValue', 'PricingMethod',
        'ReasonPricingMethod')


def test_every_template_cell_comes_from_one_proven_grid_column():
    result = project()
    assert result['rows'] == [['SYNTHETIC RELATED PARTY', '0000000000000002', 'ID', '01',
                               'SYNTHETIC ACTIVITY', '01', '1.234,5', '01', 'SYNTHETIC REASON']]
    assert [entry['path'] for entry in result['provenance']] == [
        ['Payload', 'Data', 0, field] for field in module().L10A_COLUMNS]
    assert [entry['destination']['column'] for entry in result['provenance']] == list(range(1, 10))
    assert all(entry['rule'] in ('literal-source', 'number-id-fraction-2')
               for entry in result['provenance'])


def test_reference_typed_columns_keep_their_literal_source_codes():
    # No catalog is captured for this panel: a resolved label would be invented.
    result = project([row(Country='SGP', RelationshipCode='02', TypeOfTransaction='03',
                          PricingMethod='04')])
    assert result['rows'][0][2:4] == ['SGP', '02']
    assert result['rows'][0][5] == '03'
    assert result['rows'][0][7] == '04'


def test_a_row_without_its_identifier_is_still_the_reviewed_shape():
    value = row()
    value.pop('RecordId')
    assert project([value])['rows'][0][0] == 'SYNTHETIC RELATED PARTY'


def test_an_absent_transaction_value_stays_blank():
    assert project([row(TransactionValue=None)])['rows'][0][6] == ''


@pytest.mark.parametrize('mutation,reason', [
    ({'TransactionValue': '1234.5'}, 'unsupported_corporate_l10a_amount_type'),
    ({'TransactionValue': True}, 'unsupported_corporate_l10a_amount_type'),
    ({'TransactionValue': _CorporateNumber('-1')}, 'unsupported_corporate_l10a_negative_amount'),
    ({'Name': 7}, 'unsupported_corporate_l10a_text_type'),
    ({'Synthetic': 'EXTRA'}, 'unsupported_corporate_l10a_row'),
])
def test_unreviewed_row_shapes_refuse(mutation, reason):
    from coretax_json import _UnsupportedMetadata
    with pytest.raises(_UnsupportedMetadata) as error:
        project([row(**mutation)])
    assert str(error.value) == reason


def test_a_missing_column_refuses_the_row():
    from coretax_json import _UnsupportedMetadata
    value = row()
    value.pop('ReasonPricingMethod')
    with pytest.raises(_UnsupportedMetadata) as error:
        project([value])
    assert str(error.value) == 'unsupported_corporate_l10a_row'


def test_headers_must_be_the_template_header_row():
    from coretax_json import _UnsupportedMetadata
    with pytest.raises(_UnsupportedMetadata) as error:
        project(headers=list(module().L10A_HEADERS)[:-1])
    assert str(error.value) == 'unverified_corporate_l10a_structure'


def test_absent_declared_root_still_projects_the_grid_table():
    result = adapt(packets=[primary(included=False), grid_packet([wire_row()])])
    assert result['eligible'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L10-A']
    table, = section['tables']
    assert table['headers'] == module().L10A_HEADERS
    assert table['body_row_count'] == 1 and table['complete'] is True


def test_the_empty_declared_root_dump_is_replaced_by_the_approved_table():
    result = adapt()
    assert result['eligible'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L10-A']
    assert section['fields'] == []
    table, = section['tables']
    assert table['name'] == 'L10-A/l10a-grid'
    assert table['headers'] == module().L10A_HEADERS
    assert table['rows'] == [['SYNTHETIC RELATED PARTY', '0000000000000002', 'ID', '01',
                              'SYNTHETIC ACTIVITY', '01', '1.234,5', '01', 'SYNTHETIC REASON']]
    assert table['footer'] == [] and table['footer_spans'] == []
    assert table['body_row_count'] == table['source_total'] == 1
    assert not any(item.get('headers') == ['JSON path', 'JSON type', 'Source value']
                   for item in section['tables'])


def test_each_page_keeps_the_sequence_that_carried_its_rows():
    pages = [{'request_json': request(0), 'offset': 0},
             {'request_json': request(10), 'offset': 10}]
    packets = [primary(),
               grid_packet([wire_row(Name='PARTY %d' % index, TransactionValue=str(100 + index))
                            for index in range(10)], 2, total=12),
               grid_packet([wire_row(Name='PARTY %d' % index, TransactionValue=str(100 + index))
                            for index in range(10, 12)], 3, total=12, first=10)]
    result = adapt(observed(pages=pages), packets)
    assert result['eligible'], result['reason']
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L10-A']
    sequences = {}
    for entry in projected['values']:
        sequences.setdefault(entry['path'][2], entry['response_sequence'])
    assert {index: sequences[index] for index in (0, 9, 10, 11)} == {0: 2, 9: 2, 10: 3, 11: 3}


def test_a_root_that_carries_its_own_body_is_not_silently_dropped():
    result = adapt(packets=[primary([{'Name': 'SYNTHETIC UNREVIEWED PARTY'}]),
                            grid_packet([wire_row()])])
    assert result['eligible'] is False
    assert 'unsupported_corporate_l10a_source_root' in result['reason']


@pytest.mark.parametrize('projection', [
    {'kind': 'corporate-l10a-v0'},
    {'kind': 'corporate-l10a-v1', 'builds': {}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l10a-v1',
     'builds': {module().CIT_SOURCE: 'APPROVED'}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l10a-v1', 'builds': {module().CIT_SOURCE: 'a' * 64},
     'route': corpus.FRAME_URL, 'locale': 'id-ID'},
])
def test_projection_proof_must_match_the_reviewed_shape(projection):
    result = adapt(observed(projection))
    assert result['eligible'] is False
    assert 'unverified_corporate_l10a_binding' in result['reason']


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    result = adapt(observed(proof(corpus.FRAME_URL + '/changed')))
    assert result['eligible'] is False
    assert 'unverified_corporate_l10a_binding' in result['reason']
    forms = observed()
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert result['eligible'] is False
    assert 'unverified_corporate_l10a_submitted_lifecycle' in result['reason']


def test_the_grid_binding_must_be_the_single_reviewed_page_set():
    forms = observed()
    binding = [item for item in forms if item['name'] == 'L10-A'][0]
    binding['grids'][0]['endpoint'] = corpus.ORIGIN + '/returnsheet/api/loadcit/synthetic'
    result = adapt(forms)
    assert result['eligible'] is False
    assert 'unverified_corporate_l10a_grid_binding' in result['reason']


def test_grid_rows_must_come_from_the_reviewed_payload_paths():
    from coretax_json import _UnsupportedMetadata
    table = {'headers': ['JSON path', 'JSON type', 'Source value'],
             'rows': [['/Payload/Data/0/UnreviewedField', 'string', 'X']], 'complete': True}
    with pytest.raises(_UnsupportedMetadata) as error:
        module()._l10a_grid_rows(table)
    assert str(error.value) == 'unsupported_corporate_l10a_grid_path'


def test_projected_l10a_binds_every_template_cell(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import section, source_run
    result = project([row(), row(Name='SYNTHETIC SECOND PARTY',
                                 TransactionValue=_CorporateNumber('0'))])
    table = {'name': 'L10-A/l10a-grid', 'headers': list(module().L10A_HEADERS),
             'rows': result['rows'], 'footer': [], 'footer_spans': [],
             'body_row_count': len(result['rows']), 'source_total': len(result['rows']),
             'complete': True}
    run = source_run('PPh Badan', [section('L10-A', tables=[table])])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L10-A']
        assert [sheet.cell(2, column).value for column in range(1, 10)] == module().L10A_HEADERS
        assert sheet['A3'].value == 'SYNTHETIC RELATED PARTY'
        assert sheet['B3'].value == '0000000000000002'
        assert sheet['G3'].value == 1234.5 and sheet['G3'].data_type == 'n'
        assert sheet['G4'].value == 0 and sheet['G4'].data_type == 'n'
        assert reports[0]['complete'] is True
        assert reports[0]['unmapped_fields'] == reports[0]['unmapped_tables'] == 0
    finally:
        book.close()
