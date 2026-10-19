"""Synthetic user-approved rate column and clean Induk regressions."""
from copy import deepcopy

import pytest
from openpyxl import load_workbook

import coretax_exporter as exporter
from support_templates import section, source_run


HEADERS = [
    'NO.', 'NIK/NPWP', 'NAMA', 'NOMOR BUKTI POTONG', 'TANGGAL BUKTI POTONG',
    'JENIS PAJAK', 'KODE OBJEK PAJAK', 'OBJEK PAJAK', 'DASAR PENGENAAN PAJAK (Rp)',
    'TINGKAT (%)', 'PAJAK PENGHASILAN', 'FASILITAS PERPAJAKAN',
    'UANG PERSEDIAAN / PEMBAYARAN LANGSUNG (UNTUK WP INSTANSI PEMERINTAH DENGAN DANA APBN)',
    'NITKU / NOMOR IDENTITAS SUBUNIT ORGANISASI', 'STATUS', 'KAP-KJS',
]


def export(tmp_path, sections):
    run = source_run('PPh Unifikasi', sections)
    original = deepcopy(run)
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == original
    path, = [path for path in paths if path != 'resume.xlsx']
    return load_workbook(tmp_path / path), reports


@pytest.mark.parametrize('count', [0, 26, 41])
def test_rate_column_precedes_tax_without_overwriting_money(tmp_path, count):
    body = [
        [str(i + 1), '0000000000000002', 'SYNTHETIC NAME', f'SYNTHETIC-{i}',
         '02-01-2025', 'PPh Pasal 23', '23-100-01', 'SYNTHETIC OBJECT',
         '1.234,50', '2,00', '24,69', '', 'SYNTHETIC PAYMENT METHOD',
         '0000000000000002000001', 'Normal', '411124-100']
        for i in range(count)
    ]
    table = {'name': 'Tabel 1', 'group': 'TABEL I. BPPU', 'headers': HEADERS,
             'rows': body, 'body_row_count': count, 'source_total': count,
             'complete': True, 'footer': [], 'footer_spans': []}
    book, reports = export(tmp_path, [section('DAFTAR-I', tables=[table])])
    try:
        sheet = book['DAFTAR-I']
        assert sheet['J4'].value == 'TINGKAT (%)'
        assert sheet['K4'].value == 'PAJAK PENGHASILAN (Rp)'
        assert 'A1:P1' in {str(merge) for merge in sheet.merged_cells.ranges}
        for row in range(5, count + 5):
            assert sheet.cell(row, 9).value == 1234.5
            assert sheet.cell(row, 10).value == '2,00'
            assert sheet.cell(row, 10).data_type == 's'
            assert 'Rp' not in sheet.cell(row, 10).number_format
            assert sheet.cell(row, 11).value == 24.69
            assert sheet.cell(row, 11).data_type == 'n'
            assert sheet.cell(row, 14).value == '0000000000000002000001'
        # Supplemental payment-method evidence remains; rate is now on the form.
        assert sum(c.value == '2,00' for cells in sheet for c in cells) == count
        assert reports and reports[0]['complete']
    finally:
        book.close()


def test_known_induk_extra_identity_block_is_not_duplicated_below_form(tmp_path):
    fields = [
        {'field': 'TaxIdentificationNumber', 'label': 'NPWP',
         'group': 'A. IDENTITAS PEMOTONG', 'value': ''},
        {'field': 'FullName', 'label': 'Nama Lengkap',
         'group': 'A. IDENTITAS PEMOTONG', 'value': ''},
        {'field': 'Address', 'label': 'Alamat',
         'group': 'A. IDENTITAS PEMOTONG', 'value': ''},
        {'field': 'PhoneNumber', 'label': 'Nomor Telepon',
         'group': 'A. IDENTITAS PEMOTONG', 'value': ''},
        {'field': 'StatementTIN', 'label': 'NPWP',
         'group': 'C. PERNYATAAN DAN TANDA TANGAN', 'value': ''},
        {'field': 'StatementFullName', 'label': 'Nama Tanda Tangan',
         'group': 'C. PERNYATAAN DAN TANDA TANGAN', 'value': ''},
    ]
    book, reports = export(tmp_path, [section('INDUK', fields=fields)])
    try:
        assert not any(c.value is not None for cells in book['INDUK'].iter_rows(min_row=27) for c in cells)
        # Display omission must not erase unresolved mapping diagnostics.
        assert reports and reports[0]['unmapped_fields'] == len(fields)
        assert reports[0]['complete'] is False
    finally:
        book.close()


@pytest.mark.parametrize('count', [0, 7])
def test_bpnr_rate_and_reported_footer_shift_with_body_growth(tmp_path, count):
    from pathlib import Path
    reference = load_workbook(Path(__file__).resolve().parents[1] / 'resources/unifikasi_format.xlsx')
    try:
        footer_label = reference['Daftar I']['A15'].value
    finally:
        reference.close()
    body = [[str(i + 1), '0000000000000002', 'SYNTHETIC NAME', 'SYNTHETIC-NR',
             '02-01-2025', 'PPh Pasal 26', 'SYNTHETIC-CODE', 'SYNTHETIC OBJECT',
             '1.234,50', '2,00', '24,69', '', 'SYNTHETIC METHOD',
             '0000000000000002000001', 'Normal', 'SYNTHETIC-KAP'] for i in range(count)]
    footer = [[footer_label, '987,65', '']]
    table = {'name': 'Tabel 2', 'group': 'TABEL II. BPNR', 'headers': HEADERS,
             'rows': body + footer, 'body_row_count': count, 'source_total': count,
             'complete': True, 'footer': footer, 'footer_spans': [[10, 1, 5]]}
    book, reports = export(tmp_path, [section('DAFTAR-I', tables=[table])])
    try:
        sheet = book['DAFTAR-I']
        assert sheet['J10'].value == 'TINGKAT (%)'
        assert sheet['K10'].value == 'PAJAK PENGHASILAN (Rp)'
        for row in range(11, 11 + count):
            assert sheet.cell(row, 10).value == '2,00'
            assert sheet.cell(row, 11).value == 24.69
            assert sheet.cell(row, 14).value == '0000000000000002000001'
        total_row = 15 + max(0, count - 4)
        assert sheet.cell(total_row, 11).value == 987.65
        assert sheet.cell(total_row, 11).data_type == 'n'
        assert sheet.cell(total_row, 10).value is None
        assert reports and reports[0]['complete']
    finally:
        book.close()


def test_native_rate_is_on_form_once_and_tax_remains_numeric(tmp_path):
    from coretax_masa_json import adapt_masa_detail
    from masa_projection_fixture import native_case
    from support_masa_native import exported
    case = native_case('PPh Unifikasi', populated=True)
    original = deepcopy(case)
    result = adapt_masa_detail(case['packets'], record=case['record'],
                              scope=case['scope'], observed_forms=case['forms'])
    assert result['eligible'], result['reason']
    assert case == original
    book = exported(tmp_path, 'PPh Unifikasi', result['sections'])
    try:
        sheet = book['DAFTAR-I']
        assert sheet['J4'].value == 'TINGKAT (%)'
        grid = next(s for s in result['sections'] if s['name'] == 'DAFTAR-I')['tables'][0]
        rate_index = grid['headers'].index('TINGKAT (%)')
        for index in range(grid['body_row_count']):
            assert sheet.cell(index + 5, 10).value == grid['rows'][index][rate_index]
            assert sheet.cell(index + 5, 10).data_type == 's'
            assert sheet.cell(index + 5, 11).value == 30
            assert sheet.cell(index + 5, 11).data_type == 'n'
            assert 'Rp' not in sheet.cell(index + 5, 10).number_format
    finally:
        book.close()


def test_unknown_induk_field_remains_unresolved_visible_evidence(tmp_path):
    field = {'field': 'UnexpectedAmount', 'label': 'NPWP',
             'group': 'A. IDENTITAS PEMOTONG', 'value': 'SYNTHETIC-UNRESOLVED'}
    book, reports = export(tmp_path, [section('INDUK', fields=[field])])
    try:
        assert reports and reports[0]['complete'] is False
        assert any(c.value == 'SYNTHETIC-UNRESOLVED' for row in book['INDUK'] for c in row)
    finally:
        book.close()
