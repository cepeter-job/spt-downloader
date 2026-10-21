"""Approved corporate layout contract, using synthetic captures only."""
from copy import deepcopy
from pathlib import Path
import hashlib

import pytest
from openpyxl import load_workbook
from openpyxl.cell.cell import MergedCell
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
        # Explicitly approved number-format exceptions; all other style and
        # layout attributes still compare against the untouched reference.
        accounting = reference['L1-D']['C44'].number_format
        for form, rows, columns in [('L6', range(2, 9), [2]),
                                    ('L7', range(1, 14), range(3, 10))]:
            for row in rows:
                for column in columns:
                    cell = reference[form].cell(row, column)
                    if not isinstance(cell, MergedCell):
                        cell.number_format = accounting
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


def test_l9_scalars_follow_labels_through_multiple_table_growths(tmp_path):
    specs = [('grid1', 'HARTA BERWUJUD', 'KELOMPOK 1', 184, 189),
             ('grid2', 'BANGUNAN', 'PERMANEN', 3, 221),
             ('grid2', 'BANGUNAN', 'TIDAK PERMANEN', 3, 229)]
    scalar_rows = (226, 227, 228, 259, 260, 261)
    reference = load_workbook(RESOURCE)
    try:
        headers = [cell.value for cell in reference['L9'][4]]
        fields = [{'label': reference['L9'].cell(row, 1).value,
                   'value': '1.234,50'} for row in scalar_rows]
    finally:
        reference.close()
    tables = []
    for grid, outer, inner, count, _ in specs:
        footer = [['TOTAL', '99,00', '']]
        rows = [['0001', f'SYNTHETIC ASSET {index}', '01/2025',
                 '1.234,50', '1.000,00', 'GL', 'GL', '34,50', '']
                for index in range(count)]
        tables.append({'name': 'Synthetic growth table', 'headers': headers,
                       'rows': rows + footer, 'body_row_count': count,
                       'source_total': count, 'complete': True,
                       'footer': footer, 'footer_spans': [[7, 1, 1]],
                       'source_structure': {'form': 'L9',
                                            'component': 'rshshr-citr-l9-form-' + grid,
                                            'groups': [outer, inner]}})
    book, reports = export(tmp_path, [section('L9', fields=fields, tables=list(reversed(tables)))])
    try:
        sheet = book['L9']
        for _, _, _, _, total_row in specs:
            assert sheet.cell(total_row, 8).value == 99
        # One added row in group 1 and two in each building block shift both
        # captions and values; fixed pre-growth coordinates are not the contract.
        for original, field in zip(scalar_rows, fields):
            shifted = original + 5
            assert sheet.cell(shifted, 1).value == field['label']
            assert sheet.cell(shifted, 8).value == 1234.5
            assert sheet.cell(shifted, 8).data_type == 'n'
            assert f'A{shifted}:G{shifted}' in sheet.merged_cells
        assert reports[0]['complete']
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


def captured_table(form, header, rows, footer, spans, **extra):
    reference = load_workbook(RESOURCE)
    try:
        headers = [cell.value for cell in reference[form][header]]
        while headers and headers[-1] is None:
            headers.pop()
    finally:
        reference.close()
    return {'name': 'Synthetic captured table', 'headers': headers,
            'rows': rows + footer, 'body_row_count': len(rows),
            'source_total': len(rows), 'complete': True,
            'footer': footer, 'footer_spans': spans, **extra}


@pytest.mark.parametrize('grid,header,first,count,total,label', [
    (1, 5, 6, 34, 40, 'Laba (Rugi) Sebelum Pajak'),
    (2, 42, 43, 26, 69, 'Jumlah Aset'),
    (3, 71, 72, 29, 101, 'Jumlah Liabilitas dan Ekuitas'),
])
def test_l1d_full_blocks_preserve_footer_account_codes(tmp_path, grid, header, first, count, total, label):
    reference = load_workbook(RESOURCE)
    width = 10 if grid == 1 else 3
    try:
        rows = []
        for index in range(count):
            merged = f'A{first + index}:B{first + index}' in reference['L1-D'].merged_cells
            rows.append(['' if merged else '0001', f'SYNTHETIC ACCOUNT {index}']
                        + ['0'] * (width - 2))
        if grid == 1:
            for row in rows:
                row[8] = ''
    finally:
        reference.close()
    footer = [['0099', label] + ['1.234,50'] * (width - 2)]
    if grid == 1:
        footer[0][8] = ''
    table = captured_table('L1-D', header, rows, footer, [[1] * width],
                           source_structure={'form': 'L1-D',
                               'component': f'rsh-citr-l1d-grid{grid}',
                               'groups': ['A. LAPORAN LABA RUGI' if grid == 1 else
                                          'B. LAPORAN POSISI KEUANGAN']})
    book, reports = export(tmp_path, [section('L1-D', tables=[table])])
    try:
        sheet = book['L1-D']
        assert sheet.cell(first, 1).value == 'SYNTHETIC ACCOUNT 0'
        assert sheet.cell(total - 1, 2).value == f'SYNTHETIC ACCOUNT {count - 1}'
        assert sheet.cell(total, 1).value == '0099'
        assert sheet.cell(total, 1).data_type == 's'
        assert sheet.cell(total, 2).value == label
        assert sheet.cell(total, 3).value == 1234.5
        assert reports[0]['complete']
        assert sheet.max_row == 101
    finally:
        book.close()


@pytest.mark.parametrize('form,header,count,target,footer,spans,amounts', [
    ('L2', 2, 6, 9, [['', 'JUMLAH', '1.234,50', '100,00', '9.876,50']],
     [[1, 5, 1, 1, 1]], {'G9': 1234.5, 'H9': 100, 'I9': 9876.5}),
    ('L2', 12, 9, 22, [['', 'JUMLAH', '1.234,50', '', '9.876,50', '']],
     [[1, 5, 1, 2, 1, 2]], {'G22': 1234.5, 'J22': 9876.5}),
    ('L4', 8, 1, 10, [['', 'JUMLAH', '1.234,50']],
     [[1, 3, 1]], {'E10': 1234.5}),
])
def test_footer_label_after_blank_prefix_binds_merged_total(tmp_path, form, header, count, target, footer, spans, amounts):
    table = captured_table(form, header, [], footer, spans)
    rows = [[''] * len(table['headers']) for _ in range(count)]
    rows[0][0] = '0001'
    table.update(rows=rows + footer, body_row_count=count, source_total=count)
    book, reports = export(tmp_path, [section(form, tables=[table])])
    try:
        sheet = book[form]
        assert sheet.cell(header + 1, 1).value == '0001'
        assert sheet.cell(target, 1).value == 'JUMLAH'
        for cell, value in amounts.items():
            assert sheet[cell].value == value
        assert reports[0]['complete']
    finally:
        book.close()


@pytest.mark.parametrize('count', [4654, 4656])
def test_l3_all_details_and_three_captured_totals_map_without_recalculation(tmp_path, count):
    rows = [[str(index), 'SYNTHETIC WITHHOLDER', '0000000000000002', 'SYNTHETIC TAX',
             '1.000,00', '20,00', f'000{index}', '01-01-2025'] for index in range(count)]
    footer = [['JUMLAH', '8.000,00', '900,00', ''],
              ['KREDIT PAJAK LUAR NEGERI', '', '100,00', ''],
              ['JUMLAH KREDIT PAJAK', '', '1.000,00', '']]
    table = captured_table('L3', 7, rows, footer, [[4, 1, 1, 2]] * 3)
    book, reports = export(tmp_path, [section('L3', tables=[table])])
    try:
        sheet = book['L3']
        last = 7 + count
        assert sheet['A8'].value == '0' and sheet.cell(last, 1).value == str(count - 1)
        assert sheet['C8'].value == '0000000000000002'
        assert sheet.cell(last, 7).value == f'000{count - 1}'
        assert sheet.cell(last + 1, 5).value == 8000
        assert sheet.cell(last + 1, 6).value == 900
        assert sheet.cell(last + 2, 1).value == 'KREDIT PAJAK LUAR NEGERI'
        assert sheet.cell(last + 2, 6).value == 100
        assert sheet.cell(last + 3, 6).value == 1000
        assert f'A{last + 3}:D{last + 3}' in sheet.merged_cells
        assert sheet.max_row == last + 3 and reports[0]['complete']
    finally:
        book.close()


@pytest.mark.parametrize('form,last', [('L6', 8), ('L7', 13), ('L10-A', 33), ('L10-C', 3)])
def test_requested_clean_forms_omit_raw_display_but_keep_truthful_audit(tmp_path, form, last):
    fields = [{'label': 'Synthetic unresolved field', 'value': '0009'}]
    table = {'name': 'Synthetic unknown table', 'headers': ['Unknown'],
             'rows': [['=SYNTHETIC()']], 'complete': True}
    book, reports = export(tmp_path, [section(form, fields=fields, tables=[table],
                                             text='Synthetic redundant page text')])
    try:
        sheet = book[form]
        assert sheet.max_row == last
        assert not any(cell.value == 'Data sumber tambahan / belum dipetakan'
                       for cells in sheet for cell in cells)
        assert reports[0]['unmapped_fields'] == 1
        assert reports[0]['unmapped_tables'] == 1 and reports[0]['unmapped_rows'] == 1
        assert reports[0]['complete'] is False
        resume = load_workbook(tmp_path / 'resume.xlsx')
        try:
            audit_rows = [row for row in resume['Audit'].iter_rows(values_only=True)
                          if row[0] == 'Pemetaan template']
            assert len(audit_rows) == 1
            assert audit_rows[0][1:5] == (1, 1, 1, 'PARTIAL')
            assert f' / {form}:' in audit_rows[0][5]
        finally:
            resume.close()
        if form in ('L6', 'L7'):
            cells = [sheet.cell(row, column) for row in (range(2, 9) if form == 'L6' else range(1, 14))
                     for column in ([2] if form == 'L6' else range(3, 10))]
            for cell in cells:
                # C13 belongs to the merged JUMLAH label and has no value slot.
                if cell.coordinate != 'C13':
                    assert 'Rp' in cell.number_format and '*' in cell.number_format
    finally:
        book.close()


@pytest.mark.parametrize('fault', ['unknown_label', 'conflicting_prefix', 'wrong_span', 'extra_footer'])
def test_unsupported_footer_stays_raw_without_partial_table_writes(tmp_path, fault):
    footer, spans = [['', 'JUMLAH', '1.234,50']], [[1, 3, 1]]
    if fault == 'unknown_label':
        footer[0][1] = 'SYNTHETIC UNKNOWN TOTAL'
    elif fault == 'conflicting_prefix':
        footer[0][0] = 'SYNTHETIC CONFLICT'
    elif fault == 'wrong_span':
        spans[0] = [1, 2, 1]
    else:
        footer *= 2
        spans *= 2
    table = captured_table('L4', 8, [['0001', '0002', 'SYNTHETIC TYPE', 'SYNTHETIC SOURCE', '1.000,00']],
                           footer, spans)
    book, reports = export(tmp_path, [section('L4', tables=[table])])
    try:
        assert book['L4']['A9'].value is None and book['L4']['E10'].value is None
        assert any(cell.value == '1.234,50' for cells in book['L4'] for cell in cells)
        assert reports[0]['unmapped_tables'] == 1
        assert not reports[0]['complete']
    finally:
        book.close()


def test_unsafe_footer_amount_stays_literal_and_unresolved(tmp_path):
    footer = [['', 'JUMLAH', '9.999.999.999.999.999,99']]
    table = captured_table('L4', 8, [['0001', '0002', 'SYNTHETIC TYPE', 'SYNTHETIC SOURCE', '1.000,00']],
                           footer, [[1, 3, 1]])
    book, reports = export(tmp_path, [section('L4', tables=[table])])
    try:
        assert book['L4']['A9'].value == '0001'
        assert book['L4']['E10'].value == footer[0][2]
        assert book['L4']['E10'].data_type == 's'
        assert reports[0]['unmapped_rows'] == 1 and not reports[0]['complete']
    finally:
        book.close()


def test_l7_ten_year_rows_and_total_use_accounting_without_raw_appendix(tmp_path):
    footer = [['JUMLAH'] + ['9.876,50'] * 6]
    rows = [[str(index), str(2015 + index)] + ['1.234,50'] * 7 for index in range(10)]
    table = captured_table('L7', 2, rows, footer, [[3, 1, 1, 1, 1, 1, 1]])
    table['headers'][7] = 'KOMPENSASI KERUGIAN FISKAL / 2025 / TAHUN PAJAK INI - NILAI (Rp)'
    book, reports = export(tmp_path, [section('L7', tables=[table], text='Synthetic duplicate page text')])
    try:
        sheet = book['L7']
        assert sheet['B3'].value == '2015' and sheet['B12'].value == '2024'
        assert sheet['C3'].value == sheet['I12'].value == 1234.5
        assert sheet['D13'].value == sheet['I13'].value == 9876.5
        assert sheet.max_row == 13 and reports[0]['complete']
        for cell in ('C3', 'I12', 'D13', 'I13'):
            assert 'Rp' in sheet[cell].number_format and '*' in sheet[cell].number_format
    finally:
        book.close()


@pytest.mark.parametrize('unsupported', [0, False])
def test_falsy_footer_value_cannot_match_an_empty_reference_label(tmp_path, unsupported):
    footer = [['TOTAL', '100,00', unsupported, '20,00']]
    rows = [['0000000000000002', 'SYNTHETIC WITHHOLDER', '0001', 'SYNTHETIC TAX',
             '1.000,00', '2,00', '20,00']]
    table = captured_table('L4', 2, rows, footer, [[4, 1, 1, 1]])
    book, reports = export(tmp_path, [section('L4', tables=[table])])
    try:
        assert book['L4']['A3'].value is None and book['L4']['F4'].value is None
        assert reports[0]['unmapped_tables'] == 1 and not reports[0]['complete']
    finally:
        book.close()
