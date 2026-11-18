"""Synthetic DOM L11-C footer/worksheet custody contracts; CI runners only."""
from copy import deepcopy

from openpyxl import load_workbook
import pytest

import coretax
import coretax_exporter as exporter
from support_templates import section, source_run


HEADERS = [
    'NO.', 'PEMBERI PINJAMAN / NAMA', 'PEMBERI PINJAMAN / ALAMAT',
    'PEMBERI PINJAMAN / NEGARA/YURISDIKSI', 'MATA UANG / KODE',
    'MATA UANG / KURS AKHIR TAHUN', 'POKOK UTANG (Rp) / AWAL TAHUN',
    'POKOK UTANG (Rp) / MUTASI / PENAMBAHAN',
    'POKOK UTANG (Rp) / MUTASI / PENGURANGAN',
    'POKOK UTANG (Rp) / AKHIR TAHUN',
    'JANGKA WAKTU PINJAMAN / Tanggal Mulai',
    'JANGKA WAKTU PINJAMAN / Tanggal Jatuh Tempo',
    'BUNGA / TINGKAT (%)', 'BUNGA / JUMLAH (Rp)',
    'BIAYA TERKAIT PEROLEHAN PINJAMAN SELAIN BUNGA (Rp)',
    'PERUNTUKAN PINJAMAN',
]
BODY = [
    '1', 'SYNTHETIC CREDITOR', 'SYNTHETIC ADDRESS', 'SYNTHETIC COUNTRY',
    'IDR', '1', '1.000.000', '200.000', '0', '1.200.000,00',
    '01-01-2025', '01-01-2026', '4,38', '12.500', '0', 'SYNTHETIC PURPOSE',
]
FOOTER = ['', 'TOTAL', '1.000.000', '200.000', '0', '1.200.000,00',
          '', '', '', '12.500', '0', '']
HEADER_FIELDS = [
    {'group': 'HEADER', 'label': 'Tahun Pajak/Bagian Tahun Pajak',
     'field': 'TaxPeriodYear', 'value': '2025'},
    {'group': 'HEADER', 'label': 'Nomor Identitas WP',
     'field': 'CollectorTin', 'value': '0000000000000002'},
]


def saved_dom(tmp_path, *, footer=None, spans=None, fields=None, complete=True):
    row = list(BODY)
    total = list(FOOTER if footer is None else footer)
    table = {
        'name': 'Tabel 1', 'group': 'LAPORAN UTANG SWASTA LUAR NEGERI',
        'headers': list(HEADERS), 'rows': [row, total],
        'body_row_count': 1, 'source_total': 1, 'pages': 1,
        'complete': complete, 'footer': [total],
        'footer_spans': [list(spans if spans is not None else [1, 5, *([1] * 10)])],
    }
    sections = [section('L11-C', fields=HEADER_FIELDS if fields is None else fields,
                        tables=[table], text='SYNTHETIC READ-ONLY DOM PAGE CONTEXT')]
    run = source_run('PPh Badan', sections)
    before = deepcopy(run)
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == before  # Raw DOM custody never changes during rendering.
    coretax.verify_outputs(run, tmp_path)
    saved, = [name for name in paths if name != 'resume.xlsx']
    return load_workbook(tmp_path / saved), reports[0]


@pytest.mark.parametrize('label', ['TOTAL', 'JUMLAH'])
def test_observed_dom_l11c_footer_is_bound_to_reviewed_merged_total(tmp_path, label):
    footer = list(FOOTER)
    footer[1] = label
    book, report = saved_dom(tmp_path, footer=footer)
    try:
        sheet = book['L11-C']
        assert sheet.max_row == 4
        assert sheet.max_column == 16
        assert 'A4:F4' in sheet.merged_cells
        assert sheet['A3'].value == '1'
        assert sheet['B3'].value == 'SYNTHETIC CREDITOR'
        assert sheet['P3'].value == 'SYNTHETIC PURPOSE'
        assert [sheet[f'{column}3'].value for column in 'GHIJ'] == [
            1000000, 200000, 0, 1200000]
        assert sheet['N3'].value == 12500 and sheet['O3'].value == 0
        assert sheet['A4'].value == 'JUMLAH'
        assert [sheet[f'{column}4'].value for column in 'GHIJ'] == [
            1000000, 200000, 0, 1200000]
        assert sheet['N4'].value == 12500 and sheet['O4'].value == 0
        assert sheet['M3'].value == '4,38'
        assert not any('Data sumber tambahan' in str(cell.value)
                       for row in sheet for cell in row)
        assert not any('SYNTHETIC READ-ONLY DOM PAGE CONTEXT' in str(cell.value)
                       for row in sheet for cell in row)
        assert report['unmapped_tables'] == report['unmapped_rows'] == 0
        assert report['unmapped_fields'] == report['reviewed_redundant_fields'] == 2
        assert not report['complete']  # Redundant metadata remains audited.
    finally:
        book.close()


@pytest.mark.parametrize('footer,spans', [
    (['', 'UNREVIEWED TOTAL', *FOOTER[2:]], None),
    (['', 'total', *FOOTER[2:]], None),
    (FOOTER, [1, 4, 2, *([1] * 9)]),
    ([None, *FOOTER[1:]], None),
    (['UNEXPECTED PREFIX', *FOOTER[1:]], None),
])
def test_unproved_l11c_footer_keeps_raw_and_does_not_claim_mapping(tmp_path, footer, spans):
    book, report = saved_dom(tmp_path, footer=footer, spans=spans)
    try:
        sheet = book['L11-C']
        assert sheet['A3'].value in (None, '')
        assert any(cell.value == 'Data sumber tambahan / belum dipetakan'
                   for row in sheet for cell in row)
        assert any('SYNTHETIC READ-ONLY DOM PAGE CONTEXT' in str(cell.value)
                   for row in sheet for cell in row)
        assert not report['complete'] and report['unmapped_tables'] == 1
        assert report['unmapped_rows'] == 2
    finally:
        book.close()


def test_incomplete_capture_does_not_become_complete_due_to_footer_alias(tmp_path):
    book, report = saved_dom(tmp_path, complete=False)
    try:
        assert book['L11-C']['A3'].value in (None, '')
        assert report['unmapped_tables'] == 1 and not report['complete']
    finally:
        book.close()


def test_unreviewed_l11c_field_is_not_silently_hidden_from_sheet(tmp_path):
    extra = {'group': 'HEADER', 'label': 'SYNTHETIC NEW CONTROL',
             'field': 'UnreviewedControl', 'value': 'SYNTHETIC UNMAPPED'}
    book, report = saved_dom(tmp_path, fields=[*HEADER_FIELDS, extra])
    try:
        sheet = book['L11-C']
        assert sheet['B3'].value == 'SYNTHETIC CREDITOR'
        assert any(cell.value == 'Data sumber tambahan / belum dipetakan'
                   for row in sheet for cell in row)
        assert report['unmapped_fields'] == 3 and report['reviewed_redundant_fields'] == 2
        assert not report['complete']
    finally:
        book.close()
