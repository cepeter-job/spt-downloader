"""Populated L9 grid presentation, precision and closed-shape regressions."""
from copy import deepcopy

import pytest

from coretax_json import _UnsupportedMetadata
from test_corporate_l9_grids import Number, HEADERS, asset, pages, project


@pytest.mark.parametrize('index', range(12))
def test_each_grid_maps_and_reopens_every_populated_slot_without_raw_appendix(tmp_path, index):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import section, source_run
    detail = project(index)['table']
    run = source_run('PPh Badan', [section('L9', tables=[detail])])
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [name for name in paths if name != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L9']
        matched = [row for row in sheet if row[0].value == 'SYNTHETIC-001']
        assert len(matched) == 2
        expected = ['SYNTHETIC-001', detail['rows'][0][1], '02-2024', 1235, 987,
            'Synthetic commercial label', 'Synthetic fiscal label', 26, 'SYNTHETIC literal note']
        assert [[cell.value for cell in row[:9]] for row in matched] == [expected, expected]
        assert all(row[c].data_type == 'n' for row in matched for c in (3, 4, 7))
        assert reports[0]['complete'], reports[0]
        assert reports[0]['unmapped_tables'] == 0
    finally:
        book.close()


@pytest.mark.parametrize('value,text', [('0', '0'), ('0.1', '0'), ('0.5', '1'),
    ('1.49999999999999', '1'), ('1234.50', '1.235'), ('999999999999999', '999.999.999.999.999')])
def test_numeric_body_uses_zero_fraction_angular_rounding_not_raw_decimal(value, text):
    result = project(pages=pages(rows=[asset(AcquisitionPrice=Number(value))]))
    assert result['table']['rows'][0][3] == text
    entry, = [v for v in result['provenance'] if v['path'] == ['Data', 0, 'AcquisitionPrice']]
    assert entry['value'] == value and entry['type'] == 'number'


@pytest.mark.parametrize('value', [None, '1234', True, 12, Number('-0'), Number('-1'),
    Number('1000000000000000'), Number('999999999999999.5'), Number('0.1234567890123456'),
    Number('1e999999999999999999'), Number('1e-999999999999999999')])
def test_null_coercive_negative_unsafe_numeric_inputs_refuse(value):
    with pytest.raises(_UnsupportedMetadata):
        project(pages=pages(rows=[asset(FiscalYearValue=value)]))


@pytest.mark.parametrize('value,text', [(None, ''), ('2024-02-29', '02-2024'),
    ('2024-02-29T00:00:00', '02-2024'), ('2024-02-29T00:00:00Z', '02-2024'),
    ('2024-02-29T00:00:00.000+07:00', '02-2024'), ('0001-01-01T00:00:00', '')])
def test_month_is_pinned_dayjs_month_year_not_full_date(value, text):
    result = project(pages=pages(rows=[asset(MonthYearAcquisition=value, Notes=None)]))
    assert result['table']['rows'][0][2] == text
    assert result['table']['rows'][0][8] == ''


@pytest.mark.parametrize('value', ['', '02-2024', '2023-02-29', '1969-12-01', '2101-01-01',
    '2024-02-01T23:00:00Z', '2024-02-01T00:00:00-01:00', Number('202402'), True])
def test_unproved_month_time_or_encoding_refuses(value):
    with pytest.raises(_UnsupportedMetadata):
        project(pages=pages(rows=[asset(MonthYearAcquisition=value)]))


@pytest.mark.parametrize('changes', [{'GroupType': 'Foreign'}, {'CodeOfAsset': 'not-null'},
    {'Action': 'Edit'}, {'RecordId': Number('1')}, {'Index': '1'}, {'Index': Number('-0')},
    {'Index': Number('0.1')}, {'Synthetic': 'extra'}, {'Notes': Number('1')},
    {'GroupAssetType': 'missing'}, {'MethodCommercial': 'missing'}, {'MethodFiscal': None}])
def test_metadata_and_description_custody_are_closed(changes):
    with pytest.raises(_UnsupportedMetadata):
        project(pages=pages(rows=[asset(**changes)]))


@pytest.mark.parametrize('options', [{'headers': HEADERS[:-1]}, {'footer_spans': [[], [7, 1, 1]]},
    {'tax_type': 'ICT_RUS'}, {'locale': 'en-US'}, {'timezone_name': 'UTC'}, {'labels': {}},
    {'index': -1}, {'index': True}, {'index': 12}, {'pages': []}, {'total': Number('1.5')}])
def test_structure_currency_pagination_and_footer_contract_refuse(options):
    with pytest.raises(_UnsupportedMetadata):
        project(**options)


def test_original_footer_is_not_invented_from_body_or_rounded_row_sum():
    result = project(total=Number('1000'))
    assert result['table']['footer'] == [['TOTAL', '1.000', '']]


def test_original_two_page_coordinates_and_terminal_bounds():
    first = pages(rows=[asset()] * 10)[0]
    first['payload']['TotalRecords'] = Number('12')
    second = deepcopy(first)
    second.update(offset=10)
    second['payload']['Data'] = [asset()] * 2
    result = project(pages=[first, second])
    assert result['table']['body_row_count'] == 12
    last = [v for v in result['provenance'] if v.get('page_index') == 1 and v['path'][:2] == ['Data', 0]]
    assert last and all(v['source_row'] == 10 for v in last)
    second['offset'] = 11
    with pytest.raises(_UnsupportedMetadata):
        project(pages=[first, second])


@pytest.mark.parametrize('data,kind', [(None, 'null'), ([], 'array')])
def test_empty_container_type_is_retained_and_no_repeated_terminal_page(data, kind):
    value = pages(rows=[])
    value[0]['payload']['Data'] = data
    result = project(pages=value, total=Number('0'))
    entry, = [v for v in result['provenance'] if v['path'] == ['Data']]
    assert entry['type'] == kind
    assert result['table']['body_row_count'] == 0
    with pytest.raises(_UnsupportedMetadata):
        project(pages=value * 2, total=Number('0'))


@pytest.mark.parametrize('footer,spans', [([['SYNTHETIC NOT A SPACER'], ['TOTAL', '51', '']],
    [[9], [7, 1, 1]]), ([[], ['TOTAL', '51', '']], [[9], [7, 1, 1]])])
def test_only_exact_zero_cell_l9_spacer_may_map_to_single_total_row(tmp_path, footer, spans):
    import coretax_exporter as exporter
    from support_templates import section, source_run
    detail = project()['table']
    detail.update(footer=footer, footer_spans=spans, rows=detail['rows'][:2] + footer)
    run = source_run('PPh Badan', [section('L9', tables=[detail])])
    reports = []
    exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert reports[0]['complete'] is False
    assert reports[0]['unmapped_tables'] == 1
