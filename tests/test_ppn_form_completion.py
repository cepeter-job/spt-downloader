"""PPN-only completion contracts: synthetic values, GitHub-runner execution."""
from copy import deepcopy
from pathlib import Path

import pytest
from openpyxl import load_workbook

import coretax_exporter as exporter
from test_pph21_template import assert_format, run_for, section

RESOURCE = Path(__file__).resolve().parents[1] / 'resources' / 'ppn_format.xlsx'
# form, header, first body row, original total row, monetary columns
APPENDICES = [
    ('A1', 3, 4, 7, (5,)),
    ('A2', 4, 5, 16, (6, 7, 8, 9)),
    ('B1', 4, 5, 7, (6, 7, 8)),
    ('B2', 3, 4, 8, (6, 7, 8, 9)),
    ('B3', 3, 4, 8, (6, 7, 8, 9)),
    ('C', 3, 4, 8, (10, 11, 12, 13)),
]
RAW_MARKER = 'Data sumber tambahan / belum dipetakan'
GROUP_III = 'III. PENGHITUNGAN PPN KURANG BAYAR / LEBIH BAYAR'


def export_ppn(tmp_path, sections):
    run = run_for(sections)
    run['records'][0]['meta']['Jenis Pajak'] = 'PPN'
    before = deepcopy(run)
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == before, 'Display projection must not rewrite captured values or identity'
    path = next(path for path in paths if path != 'resume.xlsx')
    return load_workbook(tmp_path / path), reports, before


def source_appendix(form, header, first, total, columns, count=0):
    reference = load_workbook(RESOURCE)
    try:
        headers = [reference[form].cell(header, c).value
                   for c in range(1, reference[form].max_column + 1)]
        while headers and headers[-1] is None:
            headers.pop()
    finally:
        reference.close()
    if form == 'B3':
        headers[1] = 'Nama Penjual BKP/BKP Tidak Berwujud/Pemberi JKP'
    rows = [[str(i + 1)] + [f'SYNTHETIC-{i}-{c}' for c in range(2, len(headers) + 1)]
            for i in range(count)]
    amounts = ['0', '-17,00', '1.234,50', '29,00'][:len(columns)]
    footer = ['TOTAL'] + amounts + [''] * (len(headers) - columns[-1])
    spans = [columns[0] - 1] + [1] * (len(footer) - 1)
    return {'name': 'Tabel 1', 'headers': headers, 'rows': rows + [footer],
            'body_row_count': count, 'source_total': count, 'complete': True,
            'footer': [footer], 'footer_spans': [spans]}, amounts


@pytest.mark.parametrize('case', APPENDICES, ids=[x[0] for x in APPENDICES])
@pytest.mark.parametrize('count', [0, 17])
def test_appendix_footer_reaches_the_styled_total_after_row_growth(tmp_path, case, count):
    form, header, first, total, columns = case
    table, amounts = source_appendix(*case, count=count)
    workbook, reports, _ = export_ppn(tmp_path, [section(form, tables=[table])])
    reference = load_workbook(RESOURCE)
    try:
        sheet = workbook[form]
        target = total + max(0, count - (total - first))
        assert sheet.cell(target, 1).value == 'TOTAL'
        assert [sheet.cell(target, c).value for c in columns] == amounts
        for c in columns:
            assert_format(sheet.cell(target, c), reference[form].cell(total, c))
            assert sheet.cell(target, c).data_type == 's'
        assert [sheet.cell(first + i, 2).value for i in range(count)] == [
            f'SYNTHETIC-{i}-2' for i in range(count)]
        for row in range(first, first + count):
            assert_format(sheet.cell(row, 2), reference[form].cell(first, 2))
        assert sheet.max_row == target
        assert RAW_MARKER not in [cell.value for row in sheet for cell in row]
        assert all(report['complete'] for report in reports)
        if form == 'C':
            assert sheet.cell(target, 9).value is None, 'Column I is an invoice ID, not money'
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('bad_spans', [[True, 1, 1], [0, 1, 1], [4, 2], [3, 1, 1], [4, 1, 1, 1]])
def test_invalid_footer_spans_never_shift_amount_into_wrong_cell(tmp_path, bad_spans):
    table, _ = source_appendix(*APPENDICES[0])
    table['footer_spans'] = [bad_spans]
    workbook, reports, _ = export_ppn(tmp_path, [section('A1', tables=[table])])
    try:
        assert workbook['A1']['E7'].value is None
        assert not all(report['complete'] for report in reports)
        assert workbook['A1'].max_row == 7
    finally:
        workbook.close()


def test_footer_conflict_is_not_arbitrarily_selected_or_added(tmp_path):
    first, _ = source_appendix(*APPENDICES[0])
    second = deepcopy(first)
    second['footer'][0][1] = '999'
    workbook, reports, _ = export_ppn(tmp_path, [section('A1', tables=[first, second])])
    try:
        assert workbook['A1']['E7'].value is None
        assert not all(report['complete'] for report in reports)
        assert workbook['A1'].max_row == 7
    finally:
        workbook.close()


def test_footer_must_match_captured_row_suffix(tmp_path):
    table, _ = source_appendix(*APPENDICES[0])
    table['rows'] = [['TOTAL', '19', '']]
    workbook, reports, _ = export_ppn(tmp_path, [section('A1', tables=[table])])
    try:
        assert workbook['A1']['E7'].value is None
        assert not all(report['complete'] for report in reports)
    finally:
        workbook.close()
