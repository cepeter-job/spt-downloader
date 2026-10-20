"""Approved corporate layout contract, using synthetic captures only."""
from copy import deepcopy
from pathlib import Path
import hashlib

import pytest
from openpyxl import load_workbook
import coretax
import coretax_exporter as exporter
from support_templates import assert_layout, section, source_run

RESOURCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'
FORMS = ['L1-D', 'L2', 'L3', 'L4', 'L6', 'L7', 'L9', 'L10-A', 'L10-C',
         'L11-A', 'L11-B', 'L11-C']


def export(tmp_path, sections, *, year=2025):
    run = source_run('PPh Badan', sections)
    run['year'] = year
    run['records'][0]['meta']['Masa Pajak'] = f'Januari - Desember {year}'
    before = deepcopy(run)
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == before
    name, = [name for name in paths if name != 'resume.xlsx']
    coretax.verify_outputs(run, tmp_path)
    return load_workbook(tmp_path / name), reports


def test_all_observed_reference_forms_preserve_approved_layout(tmp_path):
    book, _ = export(tmp_path, [section(name) for name in FORMS])
    reference = load_workbook(RESOURCE)
    try:
        assert book.sheetnames == reference.sheetnames == FORMS
        for name in FORMS:
            assert_layout(book[name], reference[name])
            assert book[name].max_row == reference[name].max_row
            for cells in reference[name]:
                for cell in cells:
                    assert book[name][cell.coordinate].value == cell.value
    finally:
        book.close()
        reference.close()


def test_resource_has_accounting_blanks_without_taxpayer_values():
    assert hashlib.sha256(RESOURCE.read_bytes()).hexdigest() == (
        '47770d95a613ed496c8f121cbe39f41ea17947855e709ab0f931adbe9ca58ab0')
    reference = load_workbook(RESOURCE)
    try:
        assert reference.sheetnames == FORMS
        sheet = reference['L1-D']
        for row in range(44, 102):
            if row == 70:  # Empty separator between the two balance-sheet tables.
                assert sheet.cell(row, 3).value is None
                continue
            if row == 71:  # The repeated NILAI header is not an amount slot.
                assert sheet.cell(row, 3).value == 'NILAI'
                continue
            cell = sheet.cell(row, 3)
            assert cell.value is None
            assert 'Rp' in cell.number_format and '*' in cell.number_format
        for name in FORMS:
            assert not any(cell.data_type == 'f' or isinstance(cell.value, (int, float))
                           for cells in reference[name] for cell in cells)
    finally:
        reference.close()


@pytest.mark.parametrize('count', [1, 32])
def test_unique_table_binds_headers_and_grows_without_changing_identifier(tmp_path, count):
    reference = load_workbook(RESOURCE)
    try:
        headers = [cell.value for cell in reference['L10-A'][2]]
    finally:
        reference.close()
    rows = [['SYNTHETIC NAME', '0000000000000002', 'SYNTHETIC COUNTRY',
             'SYNTHETIC RELATION', 'SYNTHETIC ACTIVITY', 'SYNTHETIC TRANSACTION',
             '1.234,50', 'SYNTHETIC METHOD', 'SYNTHETIC REASON'] for _ in range(count)]
    table = {'name': 'Synthetic source table', 'headers': headers, 'rows': rows,
             'body_row_count': count, 'source_total': count, 'complete': True,
             'footer': [], 'footer_spans': []}
    book, reports = export(tmp_path, [section('L10-A', tables=[table])])
    try:
        sheet = book['L10-A']
        assert sheet['A2'].value == 'Nama'
        assert sheet.max_row == max(33, count + 2)
        for row in range(3, count + 3):
            assert sheet.cell(row, 2).value == '0000000000000002'
            assert sheet.cell(row, 7).value == 1234.5
            assert sheet.cell(row, 7).data_type == 'n'
        assert reports and reports[0]['complete']
    finally:
        book.close()


def test_ambiguous_balance_table_stays_visible_and_unresolved(tmp_path):
    table = {'name': 'Synthetic ambiguous table', 'headers': ['KODE AKUN', 'NAMA AKUN', 'NILAI'],
             'rows': [['0001', 'SYNTHETIC UNBOUND', 'Rp. | 1.234,50']],
             'body_row_count': 1, 'source_total': 1, 'complete': True,
             'footer': [], 'footer_spans': []}
    book, reports = export(tmp_path, [section('L1-D', tables=[table])])
    try:
        sheet = book['L1-D']
        assert sheet['C44'].value is None and sheet['C73'].value is None
        assert any(cell.value == 'Rp. | 1.234,50' for cells in sheet for cell in cells)
        assert reports and reports[0]['complete'] is False
        assert reports[0]['unmapped_rows'] == 1
    finally:
        book.close()


def test_balance_roles_map_accounting_and_captured_total_without_recalculation(tmp_path):
    tables = []
    for component, marker, amount, total in (
            ('rsh-citr-l1d-grid3', 'SYNTHETIC LIABILITY', 'Rp. | 2.000,00', 'Rp. | 9.000,00'),
            ('rsh-citr-l1d-grid2', 'SYNTHETIC ASSET', 'Rp. | 1.234,50', 'Rp. | 8.000,00')):
        label = 'Jumlah Aset' if component.endswith('grid2') else 'Jumlah Liabilitas dan Ekuitas'
        footer = [['', label, total]]
        tables.append({'name': 'Same literal table name',
                       'headers': ['KODE AKUN', 'NAMA AKUN', 'NILAI'],
                       'rows': [['', marker, ''], ['0001', 'SYNTHETIC DETAIL', amount]] + footer,
                       'body_row_count': 2, 'source_total': 2, 'complete': True,
                       'footer': footer, 'footer_spans': [[1, 1, 1]],
                       'source_structure': {'form': 'L1-D', 'component': component,
                                            'groups': ['B. LAPORAN POSISI KEUANGAN']}})
    book, reports = export(tmp_path, [section('L1-D', tables=tables)])
    try:
        sheet = book['L1-D']
        assert sheet['A43'].value == 'SYNTHETIC ASSET'
        assert sheet['A72'].value == 'SYNTHETIC LIABILITY'
        assert sheet['A44'].value == sheet['A73'].value == '0001'
        for coordinate, value in [('C44', 1234.5), ('C73', 2000), ('C69', 8000), ('C101', 9000)]:
            assert sheet[coordinate].value == value
            assert sheet[coordinate].data_type == 'n'
            assert 'Rp' in sheet[coordinate].number_format and '*' in sheet[coordinate].number_format
        assert reports[0]['complete']
    finally:
        book.close()


@pytest.mark.parametrize('form,slots', [
    ('L6', [(f'A{row}', f'B{row}') for row in range(2, 9)]),
    ('L11-B', [(f'A{row}', f'B{row}') for row in range(2, 8)]),
    ('L9', [(f'A{row}', f'H{row}') for row in (226, 227, 228, 259, 260, 261)]),
])
def test_unique_scalar_labels_fill_their_numeric_slots(tmp_path, form, slots):
    reference = load_workbook(RESOURCE)
    try:
        fields = [{'label': reference[form][label].value, 'field': 'synthetic_scalar',
                   'value': 'Rp. | 1.234,50'} for label, _ in slots]
    finally:
        reference.close()
    book, reports = export(tmp_path, [section(form, fields=fields)])
    try:
        for _, destination in slots:
            assert book[form][destination].value == 1234.5
            assert book[form][destination].data_type == 'n'
        assert reports[0]['complete']
    finally:
        book.close()


def test_conflicting_scalar_duplicates_remain_unresolved_without_last_write_wins(tmp_path):
    label = '1. PENGHASILAN YANG MENJADI DASAR PENGHITUNGAN ANGSURAN'
    fields = [{'label': label, 'value': value} for value in ('1.234,50', '2.345,60')]
    book, reports = export(tmp_path, [section('L6', fields=fields)])
    try:
        assert book['L6']['B2'].value is None
        assert reports[0]['unmapped_fields'] == 2
        assert not reports[0]['complete']
    finally:
        book.close()


@pytest.mark.parametrize('duplicate', [False, True])
def test_l9_reordered_roles_bind_each_group_and_reject_duplicate_snapshots(tmp_path, duplicate):
    specs = [
        ('grid1', 'HARTA BERWUJUD', group, header, total)
        for group, header, total in [('KELOMPOK 1', 4, 188), ('KELOMPOK 2', 192, 194),
                                     ('KELOMPOK 3', 198, 200), ('KELOMPOK 4', 204, 206),
                                     ('LAINNYA', 210, 212)]]
    specs += [('grid2', 'BANGUNAN', 'PERMANEN', 216, 218),
              ('grid2', 'BANGUNAN', 'TIDAK PERMANEN', 222, 224)]
    specs += [('grid3', 'HARTA TIDAK BERWUJUD', group, header, total)
              for group, header, total in [('KELOMPOK 1', 231, 233), ('KELOMPOK 2', 237, 239),
                                           ('KELOMPOK 3', 243, 245), ('KELOMPOK 4', 249, 251),
                                           ('LAINNYA', 255, 257)]]
    reference = load_workbook(RESOURCE)
    tables = []
    try:
        headers = [cell.value for cell in reference['L9'][4]]
    finally:
        reference.close()
    for index, (grid, outer, inner, _, _) in enumerate(specs):
        footer = [['TOTAL', '99,00', '']]
        tables.append({'name': 'Same literal table name', 'headers': headers,
                       'rows': [['0001', f'SYNTHETIC ASSET {index}', '01/2025',
                                 '1.234,50', '1.000,00', 'GL', 'GL', '34,50', '']] + footer,
                       'complete': True, 'body_row_count': 1, 'source_total': 1,
                       'footer': footer, 'footer_spans': [[7, 1, 1]],
                       'source_structure': {'form': 'L9', 'component': 'rshshr-citr-l9-form-' + grid,
                                            'groups': [outer, inner]}})
    if duplicate:
        tables.append(deepcopy(tables[0]))
    book, reports = export(tmp_path, [section('L9', tables=list(reversed(tables)))])
    try:
        for index, (_, _, _, header, total) in enumerate(specs):
            if duplicate and index == 0:
                assert book['L9'].cell(header + 1, 2).value is None
                continue
            assert book['L9'].cell(header + 1, 2).value == f'SYNTHETIC ASSET {index}'
            assert book['L9'].cell(header + 1, 4).value == 1234.5
            assert book['L9'].cell(total, 8).value == 99
        assert reports[0]['complete'] is (not duplicate)
        assert reports[0]['unmapped_tables'] == (2 if duplicate else 0)
    finally:
        book.close()


def test_l1d_year_and_identifier_remain_literal_in_reference_identity_slots(tmp_path):
    fields = [{'label': 'Tahun Pajak', 'value': '2025'},
              {'label': 'Nomor Identitas WP', 'value': '0000000000000001'}]
    book, reports = export(tmp_path, [section('L1-D', fields=fields)])
    try:
        assert book['L1-D']['B2'].value == '2025'
        assert book['L1-D']['B3'].value == '0000000000000001'
        assert book['L1-D']['B3'].data_type == 's'
        assert reports[0]['complete']
    finally:
        book.close()


@pytest.mark.parametrize('year,header_year', [(2024, 2024), (2025, 2025), (2025, 2024)])
def test_l7_uses_only_current_captured_year_header_bound_to_record_period(tmp_path, year, header_year):
    reference = load_workbook(RESOURCE)
    try:
        headers = [cell.value for cell in reference['L7'][2]]
    finally:
        reference.close()
    caption = f'KOMPENSASI KERUGIAN FISKAL / {header_year} / TAHUN PAJAK INI - NILAI (Rp)'
    headers[7] = caption
    table = {'name': 'Synthetic L7', 'headers': headers,
             'rows': [['0001', str(year - 1), '1.234,50', '0', '0', '0', '0', '5.000,00', '0']],
             'complete': True, 'body_row_count': 1, 'source_total': 1,
             'footer': [], 'footer_spans': []}
    book, reports = export(tmp_path, [section('L7', tables=[table])], year=year)
    try:
        sheet = book['L7']
        if year == header_year:
            assert sheet['H2'].value == caption
            assert sheet['A3'].value == '0001'
            assert sheet['B3'].value == str(year - 1)
            assert sheet['H3'].value == 5000
            assert reports[0]['complete']
        else:
            assert sheet['H2'].value is None and sheet['H3'].value is None
            assert reports[0]['unmapped_tables'] == 1
            assert not reports[0]['complete']
    finally:
        book.close()
