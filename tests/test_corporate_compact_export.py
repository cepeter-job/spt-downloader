"""Clean corporate presentation through the public exporter; synthetic data only."""
from copy import deepcopy
from pathlib import Path

from openpyxl import load_workbook
import pytest

import coretax
import coretax_exporter as exporter
from support_templates import section, source_run


RESOURCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'


def table(form, header, rows, *, footer=None, spans=None, **extra):
    reference = load_workbook(RESOURCE)
    try:
        headers = [cell.value for cell in reference[form][header]]
        while headers and headers[-1] is None:
            headers.pop()
    finally:
        reference.close()
    return {'name': 'SYNTHETIC TABLE', 'headers': headers,
            'rows': rows + (footer or []), 'body_row_count': len(rows),
            'source_total': len(rows), 'complete': True,
            'footer': footer or [], 'footer_spans': spans or [], **extra}


def export(tmp_path, sections):
    run = source_run('PPh Badan', sections)
    before = deepcopy(run)
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == before
    coretax.verify_outputs(run, tmp_path)
    name, = [name for name in paths if name != 'resume.xlsx']
    return load_workbook(tmp_path / name), reports


@pytest.mark.parametrize('count', [1, 2, 32])
def test_only_populated_rows_extend_related_party_table(tmp_path, count):
    rows = [['SYNTHETIC PARTY', '0000000000000002', 'COUNTRY', 'RELATION',
             'ACTIVITY', 'TRANSACTION', '0', 'METHOD', 'REASON'] for _ in range(count)]
    rows.insert(1, [''] * 9)
    book, reports = export(tmp_path, [section('L10-A', tables=[table('L10-A', 2, rows)])])
    try:
        sheet = book['L10-A']
        assert sheet.max_row == count + 2
        assert [sheet.cell(row, 2).value for row in range(3, count + 3)] == ['0000000000000002'] * count
        assert [sheet.cell(row, 7).value for row in range(3, count + 3)] == [0] * count
        assert reports[0]['complete'] and reports[0]['unmapped_rows'] == 0
    finally:
        book.close()


def test_empty_tables_keep_one_body_slot_and_intentional_separator(tmp_path):
    book, reports = export(tmp_path, [section('L2')])
    try:
        sheet = book['L2']
        assert sheet.max_row == 9
        assert sheet['A2'].value is not None and sheet['A7'].value is not None
        assert all(cell.value is None for cell in sheet[5])
        assert reports[0]['complete']
    finally:
        book.close()


def test_induk_uses_bound_fields_in_clean_two_column_layout(tmp_path):
    fields = [
        {'label': 'Tahun Pajak/Bagian Tahun Pajak', 'field': 'TaxYear', 'group': 'HEADER', 'value': '2025'},
        {'label': '1. NPWP', 'field': 'Tin', 'group': 'A. IDENTITAS WAJIB PAJAK', 'value': '0000000000000002'},
        {'label': '14. Angsuran PPh Pasal 25', 'field': '', 'group': 'E. PENGURANG PPh TERUTANG', 'value': '0'},
        {'label': 'SYNTHETIC UNBOUND', 'field': 'Unknown', 'group': 'HEADER', 'value': 'UNMAPPED SOURCE'},
    ]
    book, reports = export(tmp_path, [section('Induk', fields=fields, text='SYNTHETIC RAW TEXT')])
    try:
        sheet = book['Induk']
        assert sheet.max_column == 2
        rows = list(sheet.values)
        assert rows[:3] == [('INDUK', None), ('Tahun Pajak/Bagian Tahun Pajak', '2025'), ('1. NPWP', '0000000000000002')]
        assert rows[-1] == ('Angsuran PPh Pasal 25', '0')
        assert rows[3:6] == [(None, None)] * 3
        assert sheet.max_row == 7
        assert reports[0]['unmapped_fields'] == 1 and not reports[0]['complete']
        assert all('Data sumber tambahan' not in str(cell.value) for row in sheet for cell in row)
    finally:
        book.close()


def test_induk_duplicate_owner_is_unresolved_instead_of_choosing_value(tmp_path):
    fields = [{'label': '1. NPWP', 'field': 'Tin', 'group': 'A. IDENTITAS WAJIB PAJAK', 'value': value}
              for value in ('0000000000000002', '0000000000000003')]
    book, reports = export(tmp_path, [section('Induk', fields=fields)])
    try:
        assert book['Induk'].max_column == 2
        assert all(cell.value not in {field['value'] for field in fields}
                   for row in book['Induk'] for cell in row)
        assert reports[0]['unmapped_fields'] == 2 and not reports[0]['complete']
    finally:
        book.close()


def test_l8_clean_table_retains_footer_codes_and_safe_amounts(tmp_path):
    source = {'name': 'SYNTHETIC L8', 'group': 'PERHITUNGAN FASILITAS PENGURANGAN TARIF PPh BAGI WAJIB PAJAK BADAN DALAM NEGERI BERDASARKAN PASAL 31E AYAT (1) UNDANG-UNDANG PPh',
              'headers': ['NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)'],
              'rows': [['01', 'SYNTHETIC DESCRIPTION', '1.234'], ['02', 'SYNTHETIC ZERO', '0'],
                       ['JUMLAH', '', '1.234']],
              'body_row_count': 2, 'source_total': 2, 'complete': True,
              'footer': [['JUMLAH', '', '1.234']], 'footer_spans': [[1, 1, 1]]}
    book, reports = export(tmp_path, [section('L8', tables=[source])])
    try:
        sheet = book['L8']
        assert sheet.max_row == 4 and sheet.max_column == 3
        assert sheet['A2'].value == '01' and sheet['C2'].value == 1234
        assert sheet['C3'].value == 0 and sheet['A4'].value == 'JUMLAH'
        assert sheet['C4'].value == 1234
        assert 'Rp' in sheet['C4'].number_format and '0.00' not in sheet['C4'].number_format
        assert reports[0]['complete']
    finally:
        book.close()
