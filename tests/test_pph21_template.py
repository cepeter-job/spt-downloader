"""PPh21 format contracts use a sanitized reference and synthetic source only."""
from copy import copy, deepcopy
import hashlib
from pathlib import Path
import sys
import zipfile

import pytest
from openpyxl import load_workbook

import coretax
import coretax_exporter as exporter
from spt_desktop import runtime

REFERENCE = Path(__file__).parent / 'fixtures' / 'pph21_format.xlsx'
JANUARY = 'SPT Masa 21/SPT_21_Januari 2025.xlsx'
FORMS = ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III']
COMMON_HEADERS = ['NO.', 'NIK/NPWP', 'NAMA', 'NOMOR BUKTI POTONG',
                  'TANGGAL BUKTI PEMOTONGAN', 'KODE OBJEK PAJAK',
                  'PENGHASILAN BRUTO (Rp)', 'PAJAK PENGHASILAN (Rp)',
                  'FASILITAS PERPAJAKAN', 'Negara', 'ID TEMPAT KEGIATAN USAHA',
                  'KAP-KJS', 'STATUS']
IA_HEADERS = COMMON_HEADERS[:7] + ['TARIF PAJAK (%)'] + COMMON_HEADERS[7:]
INDUK_HEADERS = ['NO.', 'URAIAN', 'KAP-KJS', 'JUMLAH (Rp)']


def row(marker='SYNTHETIC EMPLOYEE', *, ia=False):
    values = ['1', '0000000000000002', marker, 'SYNTHETIC-WITHHOLDING-001',
              '02-01-2025', '21-100-01', '1.234,50', '123,45',
              'SYNTHETIC FACILITY', 'SYNTHETIC COUNTRY', '0000000000000002000001',
              '411121-100', 'SYNTHETIC STATUS']
    return values[:7] + ['10,00'] + values[7:] if ia else values


def table(name, values, *, ia=False, headers=None, complete=True):
    return {'name': name, 'headers': list(headers or (IA_HEADERS if ia else COMMON_HEADERS)),
            'rows': values, 'complete': complete}


def section(name, *, tables=None, fields=None, text=''):
    return {'name': name, 'fields': fields or [], 'tables': tables or [], 'text': text}


def run_for(sections, *, model='Normal', key='synthetic-21-normal'):
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'taxpayer_name': 'SYNTHETIC FIXTURE ONLY', 'complete': False,
            'started_at': 'fixture', 'audit': [], 'errors': [],
            'records': [{'key': key, 'record_id': key, 'source_status': 'Fixture',
                         'meta': {'Jenis Pajak': 'PPh Pasal 21/26',
                                  'Masa Pajak': 'Januari 2025', 'Model SPT': model},
                         'capture_complete': True, 'detail_url': '', 'sections': sections}]}


def export(run, folder):
    exporter.export_split_workbooks(run, folder)
    coretax.verify_outputs(run, folder)
    return load_workbook(folder / JANUARY)


def cells_with(workbook, value):
    return [c for ws in workbook for cells in ws for c in cells if c.value == value]


def assert_format(actual, reference):
    # Style IDs are workbook-local; compare rendered style components instead.
    for attribute in ('font', 'fill', 'border', 'alignment', 'protection'):
        assert copy(getattr(actual, attribute)) == copy(getattr(reference, attribute))
    assert actual.number_format == reference.number_format


def assert_layout(actual, reference):
    assert set(str(r) for r in actual.merged_cells.ranges) == set(str(r) for r in reference.merged_cells.ranges)
    for key, dimension in reference.column_dimensions.items():
        got = actual.column_dimensions[key]
        for attr in ('width', 'hidden', 'min', 'max', 'bestFit', 'outlineLevel', 'collapsed'):
            assert getattr(got, attr) == getattr(dimension, attr)
    for key, dimension in reference.row_dimensions.items():
        got = actual.row_dimensions[key]
        for attr in ('height', 'hidden', 'outlineLevel', 'collapsed'):
            assert getattr(got, attr) == getattr(dimension, attr)
    for attr in ('sheet_format', 'page_margins', 'print_options'):
        assert copy(getattr(actual, attr)) == copy(getattr(reference, attr))
    for attr in ('orientation', 'paperSize', 'fitToWidth', 'fitToHeight'):
        assert getattr(actual.page_setup, attr) == getattr(reference.page_setup, attr)
    for cells in reference:
        for c in cells:
            assert_format(actual[c.coordinate], c)


def test_empty_observed_forms_export_clean_template_without_sample_data(tmp_path):
    assert hashlib.sha256(REFERENCE.read_bytes()).hexdigest() == 'a0bac29353d75f4af644ad72169e46a8b882dac7f9874debbbb086f32bb16c5e'
    with zipfile.ZipFile(REFERENCE) as archive:
        assert hashlib.sha256(archive.read('xl/styles.xml')).hexdigest() == 'f824574321958fe2e858a66a1b9d1e60f5b897dc5a73f1573db0f9f9b7b842d0'
        assert not any(p.startswith(('docProps/', 'xl/printerSettings/')) for p in archive.namelist())
    with_ref = load_workbook(REFERENCE)
    exported = export(run_for([section(form) for form in FORMS]), tmp_path)
    try:
        assert with_ref.sheetnames == FORMS
        assert exported.sheetnames == FORMS
        assert [ws['A1'].value for ws in exported] == [ws['A1'].value for ws in with_ref]
        for coordinate in ['D4', 'D5', 'D6', 'D7', 'D12', 'D21', 'D26', 'D35']:
            assert with_ref['Induk'][coordinate].value is None
            assert exported['Induk'][coordinate].value is None
        for name, regions in [('L-IA', [(5, 15)]), ('L-IB', [(6, 8), (12, 14)]),
                              ('L-II', [(5, 7), (11, 14)]), ('L-III', [(5, 7), (11, 13)])]:
            for first, last in regions:
                assert all(c.value is None for cells in with_ref[name].iter_rows(min_row=first, max_row=last) for c in cells)
                assert all(c.value is None for cells in exported[name].iter_rows(min_row=first, max_row=last) for c in cells)
    finally:
        with_ref.close()
        exported.close()


@pytest.mark.parametrize('form', FORMS)
def test_observed_form_preserves_every_reference_cell_format_and_layout(tmp_path, form):
    wb = export(run_for([section(form)]), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        assert wb.sheetnames == [form], 'Do not invent unobserved forms'
        assert wb[form]['A1'].value == reference[form]['A1'].value
        assert_layout(wb[form], reference[form])
        assert exporter.read_workbook_proof(wb)['records'][0]['record_id'] == 'synthetic-21-normal'
    finally:
        wb.close()
        reference.close()


def test_induk_header_fields_and_amounts_fill_only_their_reference_slots(tmp_path):
    fields = [{'label': label, 'field': label, 'value': value} for label, value in
              [('Masa Pajak', 'Januari 2025'), ('Tahun Pajak', '2025'),
               ('Status SPT', 'Pembetulan ke-2'), ('Status Penyampaian', 'Dilaporkan')]]
    tables = [table('I. PAJAK PENGHASILAN PASAL 21 YANG DIPOTONG',
                    [['1', 'PPH PASAL 21 YANG DIPOTONG', '411121-100', '1.234,50']], headers=INDUK_HEADERS),
              table('II. PAJAK PENGHASILAN PASAL 21 YANG DITANGGUNG OLEH PEMERINTAH',
                    [['1', 'PPH PASAL 21 YANG DIPOTONG', '411121-100', '21,00']], headers=INDUK_HEADERS),
              table('I.PAJAK PENGHASILAN PASAL 26 YANG DIPOTONG',
                    [['1', 'PAJAK PENGHASILAN PASAL 26 YANG DIPOTONG', '411127-100', '26,00']], headers=INDUK_HEADERS),
              table('II.PAJAK PENGHASILAN PASAL 26 YANG DITANGGUNG OLEH PEMERINTAH',
                    [['1', 'PAJAK PENGHASILAN PASAL 26 YANG DIPOTONG', '411127-100', '126,00']], headers=INDUK_HEADERS)]
    wb = export(run_for([section('Induk', fields=fields, tables=tables)], model='Pembetulan ke-2'), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        sheet = wb['Induk']
        assert [sheet[f'D{r}'].value for r in [4, 5, 6, 7, 12, 21, 26, 35]] == [
            'Januari 2025', '2025', 'Pembetulan ke-2', 'Dilaporkan', '1.234,50', '21,00', '26,00', '126,00']
        assert sheet['D12'].data_type == 's'
        assert_layout(sheet, reference['Induk'])
        assert sheet['C12'].value == '411121-100'
        assert sheet['C26'].value == '411127-100'
    finally:
        wb.close()
        reference.close()


def test_lia_rows_keep_column_order_duplicates_identifiers_and_literal_amounts(tmp_path):
    source = row(ia=True)
    wb = export(run_for([section('L-IA', tables=[table('L-IA', [source, source], ia=True)])]), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        sheet = wb['L-IA']
        assert [sheet.cell(4, i).value for i in range(1, 15)] == IA_HEADERS
        assert [[sheet.cell(r, c).value for c in range(1, 15)] for r in [5, 6]] == [source, source]
        assert sheet['B5'].data_type == 's' and sheet['L5'].data_type == 's'
        assert sheet['G5'].value == '1.234,50' and sheet['E5'].value == '02-01-2025'
        assert_layout(sheet, reference['L-IA'])
    finally:
        wb.close()
        reference.close()


def test_reordered_visible_headers_are_mapped_without_changing_template_columns(tmp_path):
    source = row(ia=True)
    headers = list(reversed(IA_HEADERS))
    wb = export(run_for([section('L-IA', tables=[table('L-IA', [list(reversed(source))], headers=headers)])]), tmp_path)
    try:
        assert [wb['L-IA'].cell(5, c).value for c in range(1, 15)] == source
        assert [wb['L-IA'].cell(4, c).value for c in range(1, 15)] == IA_HEADERS
    finally:
        wb.close()


@pytest.mark.parametrize('form,first,second,first_row,second_row', [
    ('L-IB', 'BPA1', 'BPA2', 6, 12), ('L-II', 'BPA1', 'BPA2', 5, 11),
    ('L-III', 'BP21', 'BP26', 5, 11),
])
def test_two_groups_are_bound_to_captions_not_capture_order(tmp_path, form, first, second, first_row, second_row):
    first_values, second_values = row('SYNTHETIC FIRST'), row('SYNTHETIC SECOND')
    wb = export(run_for([section(form, tables=[table(second, [second_values]), table(first, [first_values])])]), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        sheet = wb[form]
        assert [sheet.cell(first_row, c).value for c in range(1, 14)] == first_values
        assert [sheet.cell(second_row, c).value for c in range(1, 14)] == second_values
        assert_layout(sheet, reference[form])
    finally:
        wb.close()
        reference.close()


def test_long_lia_table_grows_with_original_row_styles_without_losing_totals(tmp_path):
    rows = [row(f'SYNTHETIC EMPLOYEE {i}', ia=True) for i in range(18)]
    wb = export(run_for([section('L-IA', tables=[table('L-IA', rows, ia=True)])]), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        sheet = wb['L-IA']
        assert [[sheet.cell(r, c).value for c in range(1, 15)] for r in range(5, 23)] == rows
        assert sheet['A23'].value == 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH'
        for r in range(16, 23):
            for c in range(1, 15):
                assert_format(sheet.cell(r, c), reference['L-IA'].cell(5, c))
            assert sheet.row_dimensions[r].height == reference['L-IA'].row_dimensions[5].height
        assert sheet.row_dimensions[23].height == reference['L-IA'].row_dimensions[16].height
        assert set(str(m) for m in sheet.merged_cells.ranges) == {'A1:N1'}
    finally:
        wb.close()
        reference.close()


def test_first_group_growth_moves_second_group_and_preserves_its_format(tmp_path):
    first = [row(f'SYNTHETIC BPA1 {i}') for i in range(6)]
    second = [row('SYNTHETIC BPA2')]
    wb = export(run_for([section('L-IB', tables=[table('BPA2', second), table('BPA1', first)])]), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        sheet = wb['L-IB']
        assert [[sheet.cell(r, c).value for c in range(1, 14)] for r in range(6, 12)] == first
        assert sheet['B13'].value == 'BPA2'
        assert [sheet.cell(15, c).value for c in range(1, 14)] == second[0]
        assert sheet['A19'].value == reference['L-IB']['A16'].value
        for c in range(1, 15):
            assert_format(sheet.cell(15, c), reference['L-IB'].cell(12, c))
        assert sheet.row_dimensions[19].height == reference['L-IB'].row_dimensions[16].height
    finally:
        wb.close()
        reference.close()


def test_multiple_tables_for_same_group_append_rows_in_source_order(tmp_path):
    one, two = row('SYNTHETIC ONE'), row('SYNTHETIC TWO')
    wb = export(run_for([section('L-IB', tables=[table('BPA1', [one]), table('BPA1', [two])])]), tmp_path)
    try:
        assert [wb['L-IB'].cell(6, c).value for c in range(1, 14)] == one
        assert [wb['L-IB'].cell(7, c).value for c in range(1, 14)] == two
    finally:
        wb.close()


def test_unknown_fields_table_columns_and_page_context_are_not_silently_dropped(tmp_path):
    value = '=HYPERLINK("https://invalid.example", "SYNTHETIC RAW")'
    data = section('Induk', fields=[{'label': 'SYNTHETIC UNKNOWN FIELD', 'field': 'unknown', 'value': value}],
                   tables=[table('SYNTHETIC UNKNOWN TABLE', [['0000000000000003', '987,65'],
                                                            ['0000000000000003', '987,65']], headers=['SYNTHETIC ID', 'SYNTHETIC VALUE'])],
                   text='SYNTHETIC PAGE CONTEXT')
    wb = export(run_for([data]), tmp_path)
    reference = load_workbook(REFERENCE)
    try:
        assert len(cells_with(wb, value)) == 1 and cells_with(wb, value)[0].data_type == 's'
        assert len(cells_with(wb, '0000000000000003')) == 2
        assert len(cells_with(wb, '987,65')) == 2
        assert len(cells_with(wb, 'SYNTHETIC PAGE CONTEXT')) == 1
        assert all(c.row > 35 for c in cells_with(wb, value))
        assert_layout(wb['Induk'], reference['Induk'])
    finally:
        wb.close()
        reference.close()


def test_ambiguous_group_is_preserved_as_raw_evidence_not_guessed_as_bpa1(tmp_path):
    wb = export(run_for([section('L-IB', tables=[table('SYNTHETIC UNCLASSIFIED', [row()])])]), tmp_path)
    try:
        assert wb['L-IB']['B6'].value is None and wb['L-IB']['B12'].value is None
        assert len(cells_with(wb, 'SYNTHETIC EMPLOYEE')) == 1
        assert cells_with(wb, 'SYNTHETIC EMPLOYEE')[0].row > 18
    finally:
        wb.close()


def test_duplicate_header_fields_preserve_both_raw_values(tmp_path):
    fields = [{'label': 'Status SPT', 'field': 'status', 'value': 'SYNTHETIC FIRST STATUS'},
              {'label': 'Status SPT', 'field': 'status', 'value': 'SYNTHETIC SECOND STATUS'}]
    wb = export(run_for([section('Induk', fields=fields)]), tmp_path)
    try:
        assert len(cells_with(wb, 'SYNTHETIC FIRST STATUS')) == 1
        assert len(cells_with(wb, 'SYNTHETIC SECOND STATUS')) == 1
    finally:
        wb.close()


def test_normal_amendment_and_next_period_keep_separate_layouts_proof_and_resume_links(tmp_path):
    normal = run_for([section('Induk'), section('L-IA', tables=[table('L-IA', [row('SYNTHETIC NORMAL', ia=True)], ia=True)])])
    amendment = deepcopy(normal['records'][0])
    amendment['key'] = amendment['record_id'] = 'synthetic-21-amendment'
    amendment['meta']['Model SPT'] = 'Pembetulan ke-2'
    amendment['sections'][1]['tables'][0]['rows'][0][2] = 'SYNTHETIC AMENDMENT'
    february = deepcopy(amendment)
    february['key'] = february['record_id'] = 'synthetic-21-february'
    february['meta']['Masa Pajak'] = 'Februari 2025'
    normal['records'] += [amendment, february]
    wb = export(normal, tmp_path)
    reference = load_workbook(REFERENCE)
    resume = load_workbook(tmp_path / 'resume.xlsx')
    feb = load_workbook(tmp_path / 'SPT Masa 21/SPT_21_Februari 2025.xlsx')
    try:
        assert wb.sheetnames == ['Induk', 'L-IA', 'Induk (2)', 'L-IA (2)']
        assert wb['L-IA']['C5'].value == 'SYNTHETIC NORMAL'
        assert wb['L-IA (2)']['C5'].value == 'SYNTHETIC AMENDMENT'
        assert_layout(wb['L-IA (2)'], reference['L-IA'])
        assert feb.sheetnames == ['Induk', 'L-IA']
        proof = exporter.read_workbook_proof(wb)
        assert [r['record_id'] for r in proof['records']] == ['synthetic-21-normal', 'synthetic-21-amendment']
        assert [r['meta']['Model SPT'] for r in proof['records']] == ['Normal', 'Pembetulan ke-2']
        assert [(resume['Daftar SPT'].cell(r, 1).hyperlink.target,
                 resume['Daftar SPT'].cell(r, 1).hyperlink.location) for r in [5, 6, 7]] == [
            (JANUARY, "'Induk'!A1"), (JANUARY, "'Induk (2)'!A1"),
            ('SPT Masa 21/SPT_21_Februari 2025.xlsx', "'Induk'!A1")]
    finally:
        wb.close()
        reference.close()
        resume.close()
        feb.close()


def test_template_is_shipped_and_used_from_the_copied_worker_resource_tree(tmp_path):
    resources = {'coretax_pph21.py', 'resources/pph21_format.xlsx'}
    assert resources <= set(runtime.WORKER_FILES), 'Template renderer/resource missing from isolated worker'
    # Use the real copying boundary, then test public export in its app tree.
    # Provisioning another Python/network environment is outside this layout test.
    worker_root = tmp_path / 'worker'
    runtime._resources(Path(__file__).resolve().parents[1], worker_root)
    copied = worker_root / 'app'
    assert hashlib.sha256((copied / 'resources/pph21_format.xlsx').read_bytes()).hexdigest() == hashlib.sha256(REFERENCE.read_bytes()).hexdigest()
    # Exercise the real separate worker imports, not the already-loaded repo modules.
    import subprocess
    program = ('from pathlib import Path; from coretax_exporter import export_split_workbooks; '
               'import json; from openpyxl import load_workbook; '
               'r=json.loads(Path("fixture-input.json").read_text()); '
               'export_split_workbooks(r,Path("out")); '
               'w=load_workbook(Path("out")/"SPT Masa 21/SPT_21_Januari 2025.xlsx"); '
               'assert w["Induk"]["A1"].value=="Induk SPT PPh Pasal 21/26"; w.close()')
    import json
    (copied / 'fixture-input.json').write_text(json.dumps(run_for([section('Induk')])), encoding='utf-8')
    result = subprocess.run([sys.executable, '-c', program], cwd=copied, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


def test_other_tax_types_keep_the_existing_generic_form_output(tmp_path):
    run = run_for([section('Induk', fields=[{'label': 'Record marker', 'field': 'marker', 'value': 'SYNTHETIC CORPORATE'}])])
    run['records'][0]['meta']['Jenis Pajak'] = 'PPh Badan'
    exporter.export_split_workbooks(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    wb = load_workbook(tmp_path / 'SPT_Badan.xlsx')
    try:
        assert wb['Induk']['A1'].value == 'Induk'
        assert wb['Induk'].freeze_panes == 'A3'
        assert wb['Induk'].page_setup.orientation == 'landscape'
        assert cells_with(wb, 'SYNTHETIC CORPORATE')
    finally:
        wb.close()
