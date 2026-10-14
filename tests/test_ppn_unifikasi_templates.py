"""Approved PPN/Unifikasi layout contracts; synthetic, GitHub-runner-only."""
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
from openpyxl import load_workbook

import coretax
import coretax_exporter as exporter
from spt_desktop import runtime
from test_pph21_template import assert_format, assert_layout, cells_with, run_for, section

FIXTURES = Path(__file__).parent / 'fixtures'
TYPES = {
    'PPN': {'reference': 'ppn_format.xlsx',
            'sha256': 'f426a2e428d62fa0af679024f8038195f6198780a2fc15817301982aa4d3fa16',
            'styles': 'c9bae8ced0551e1993d6d09c16fc304e0bc8bb98c1d2d7f6e06657ff7d5c3cc8',
            'forms': ['Induk', 'A1', 'A2', 'B1', 'B2', 'B3', 'C'],
            'path': 'SPT Masa PPN/SPT_PPN_Januari 2025.xlsx',
            'resource': 'resources/ppn_format.xlsx'},
    'PPh Unifikasi': {'reference': 'unifikasi_format.xlsx',
                     'sha256': '2ad49e997b6404a687c273dc7d895245e6d03593b8d76678b0928f8573efc7a2',
                     'styles': 'e4fb3f3684fc70914742af99a321fb17d950cc75b44b8b553df49ca071f37f0c',
                     'forms': ['Induk', 'Daftar I', 'Daftar II', 'Lampiran I'],
                     'path': 'SPT Masa Unifikasi/SPT_Unifikasi_Januari 2025.xlsx',
                     'resource': 'resources/unifikasi_format.xlsx'},
}
FORMS = [(tax, form) for tax, config in TYPES.items() for form in config['forms']]
# Headers/groups and slots come from visible reference captions, not native API aliases.
BLOCKS = [
    ('PPN', 'A1', 3, 4, 6, ''),
    ('PPN', 'A2', 4, 5, 15, 'B3'),
    ('PPN', 'B1', 4, 5, 6, ''),
    ('PPN', 'B2', 3, 4, 7, ''),
    ('PPN', 'B3', 3, 4, 7, ''),
    ('PPN', 'C', 3, 4, 7, ''),
    ('PPh Unifikasi', 'Daftar I', 4, 5, 8, 'B3'),
    ('PPh Unifikasi', 'Daftar I', 10, 11, 14, 'B9'),
    ('PPh Unifikasi', 'Daftar II', 4, 5, 8, 'B3'),
    ('PPh Unifikasi', 'Daftar II', 13, 14, 17, 'B12'),
    ('PPh Unifikasi', 'Lampiran I', 4, 5, 9, 'B3'),
]
BLANK_REGIONS = {
    'PPN': {'A1': [(4, 6)], 'A2': [(5, 15)], 'B1': [(5, 6)],
            'B2': [(4, 7)], 'B3': [(4, 7)], 'C': [(4, 7)]},
    'PPh Unifikasi': {'Daftar I': [(5, 8), (11, 14)],
                     'Daftar II': [(5, 8), (14, 17)], 'Lampiran I': [(5, 9)]},
}


def source_run(tax, sections):
    run = run_for(sections, key='synthetic-template-normal')
    run['records'][0]['meta']['Jenis Pajak'] = tax
    return run


def export(tax, run, folder):
    files = exporter.export_split_workbooks(run, folder)
    coretax.verify_outputs(run, folder)
    assert set(files) == {'resume.xlsx', TYPES[tax]['path']}
    return load_workbook(folder / TYPES[tax]['path'])


def source_table(name, headers, rows, *, complete=True):
    return {'name': name, 'headers': headers, 'rows': rows, 'complete': complete}


def headers_for(sheet, row):
    return [cell.value for cell in sheet[row] if cell.value is not None]


def synthetic_row(headers, marker):
    values = []
    for header in headers:
        normalized = header.casefold()
        if normalized.rstrip('.') == 'no':
            value = '1'
        elif any(token in normalized for token in ('npwp', 'nik', 'identitas wp', 'nitku', 'tempat kegiatan')):
            value = '0000000000000002000001' if 'nitku' in normalized or 'tempat kegiatan' in normalized else '0000000000000002'
        elif 'tanggal' in normalized:
            value = '02-01-2025'
        elif 'kap-kjs' in normalized:
            value = '411124-100'
        elif 'kode objek' in normalized:
            value = '23-100-01'
        elif '%' in normalized:
            value = '2,00'
        elif any(token in normalized for token in ('(rp)', '(rupiah)', 'dpp', 'harga jual')):
            value = '1.234,50'
        elif 'nomor' in normalized:
            value = 'SYNTHETIC-DOCUMENT-0001'
        else:
            value = marker + ' ' + header
        values.append(value)
    return values


@pytest.mark.parametrize('tax', list(TYPES))
def test_empty_observed_templates_contain_no_reference_taxpayer_or_amount_data(tmp_path, tax):
    config = TYPES[tax]
    reference_path = FIXTURES / config['reference']
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == config['sha256']
    with zipfile.ZipFile(reference_path) as archive:
        assert archive.testzip() is None
        assert hashlib.sha256(archive.read('xl/styles.xml')).hexdigest() == config['styles']
        assert not any(name.startswith(('docProps/', 'xl/printerSettings/')) for name in archive.namelist())
    reference = load_workbook(reference_path)
    workbook = export(tax, source_run(tax, [section(form) for form in config['forms']]), tmp_path)
    try:
        assert workbook.sheetnames == reference.sheetnames == config['forms']
        for sheet in reference:
            assert workbook[sheet.title]['A1'].value == sheet['A1'].value
            assert_layout(workbook[sheet.title], sheet)
        for coordinate in ['D4', 'D5', 'D6', 'D7']:
            assert reference['Induk'][coordinate].value is None
            assert workbook['Induk'][coordinate].value is None
        if tax == 'PPN':
            assert reference['Induk']['D48'].value is None
            assert workbook['Induk']['D48'].value is None
            amount_regions = [(12, 23, 5, 8), (28, 37, 5, 8), (41, 47, 5, 5),
                              (52, 52, 5, 6), (56, 56, 5, 5), (60, 65, 5, 5),
                              (69, 71, 5, 8), (75, 78, 5, 8)]
        else:
            amount_regions = [(12, 27, 3, 8)]
        for first, last, column, end in amount_regions:
            for sheet in [reference['Induk'], workbook['Induk']]:
                assert all(c.value is None for row in sheet.iter_rows(min_row=first, max_row=last,
                           min_col=column, max_col=end) for c in row)
        for name, regions in BLANK_REGIONS[tax].items():
            for first, last in regions:
                for sheet in [reference[name], workbook[name]]:
                    assert all(c.value is None for row in sheet.iter_rows(min_row=first, max_row=last) for c in row)
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('tax,form', FORMS)
def test_each_observed_form_retains_every_cell_style_and_reference_layout(tmp_path, tax, form):
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    workbook = export(tax, source_run(tax, [section(form)]), tmp_path)
    try:
        assert workbook.sheetnames == [form], 'Absent source forms must not be invented'
        assert workbook[form]['A1'].value == reference[form]['A1'].value
        assert_layout(workbook[form], reference[form])
        assert exporter.read_workbook_proof(workbook)['records'][0]['record_id'] == 'synthetic-template-normal'
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('tax', list(TYPES))
def test_induk_identity_fields_use_the_original_slots_without_reformatting(tmp_path, tax):
    fields = [{'label': label, 'value': value} for label, value in
              [('Masa Pajak', 'Januari 2025'), ('Tahun Pajak', '2025'),
               ('Status SPT', 'Pembetulan ke-2'), ('Status Penyampaian', 'Dilaporkan')]]
    workbook = export(tax, source_run(tax, [section('Induk', fields=fields)]), tmp_path)
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    try:
        for coordinate, field in zip(['D4', 'D5', 'D6', 'D7'], fields):
            cell = workbook['Induk'][coordinate]
            assert cell.value == field['value'] and cell.data_type == 's'
            assert_format(cell, reference['Induk'][coordinate])
        assert_layout(workbook['Induk'], reference['Induk'])
    finally:
        workbook.close()
        reference.close()


def test_ppn_induk_keeps_repeated_row_labels_bound_to_their_visible_section(tmp_path):
    reference = load_workbook(FIXTURES / TYPES['PPN']['reference'])
    ref = reference['Induk']
    groups = [(9, 10, 12, 'C12', '120,01'), (67, 68, 69, 'B69', '690,01'),
              (73, 74, 75, 'B75', '750,01')]
    tables = []
    for caption_row, header_row, value_row, label_cell, marker in groups:
        name = str(ref[f'A{caption_row}'].value).strip() + ' ' + str(ref[f'B{caption_row}'].value).strip()
        headers = [''] + [ref.cell(header_row, column).value for column in range(5, 9)]
        tables.append(source_table(name, headers, [[ref[label_cell].value, marker, '20,02', '30,03', '40,04']]))
    workbook = export('PPN', source_run('PPN', [section('Induk', tables=tables)]), tmp_path)
    try:
        for caption_row, header_row, value_row, label_cell, marker in groups:
            assert [workbook['Induk'].cell(value_row, col).value for col in range(5, 9)] == [marker, '20,02', '30,03', '40,04']
        assert_layout(workbook['Induk'], ref)
    finally:
        workbook.close()
        reference.close()


def test_ppn_compensation_choice_is_captured_data_not_a_reference_default(tmp_path):
    run = source_run('PPN', [section('Induk', fields=[
        {'label': 'Diminta Untuk', 'value': 'SYNTHETIC REQUESTED CHOICE'}])])
    workbook = export('PPN', run, tmp_path)
    reference = load_workbook(FIXTURES / TYPES['PPN']['reference'])
    try:
        assert workbook['Induk']['D48'].value == 'SYNTHETIC REQUESTED CHOICE'
        assert_format(workbook['Induk']['D48'], reference['Induk']['D48'])
        assert_layout(workbook['Induk'], reference['Induk'])
    finally:
        workbook.close()
        reference.close()


def test_unifikasi_induk_leaf_headers_fill_both_merged_income_tax_columns(tmp_path):
    reference = load_workbook(FIXTURES / TYPES['PPh Unifikasi']['reference'])
    ref = reference['Induk']
    headers = ['NO', 'DETIL', 'SETOR SENDIRI', 'PEMOTONGAN / PEMUNGUTAN'] + [ref.cell(10, col).value for col in range(5, 9)]
    values = ['1', 'Pasal 4 Ayat 2', '101,01', '102,02', '103,03', '104,04', '105,05', '106,06']
    run = source_run('PPh Unifikasi', [section('Induk', tables=[source_table('PAJAK PENGHASILAN', headers, [values])])])
    workbook = export('PPh Unifikasi', run, tmp_path)
    try:
        assert [workbook['Induk'].cell(12, col).value for col in range(3, 9)] == values[2:]
        assert workbook['Induk']['C10'].value == 'PAJAK PENGHASILAN'
        assert workbook['Induk']['C11'].value == 'SETOR SENDIRI'
        assert workbook['Induk']['D11'].value == 'PEMOTONGAN / PEMUNGUTAN'
        assert_layout(workbook['Induk'], ref)
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('tax,form,header_row,first,last,caption_cell', BLOCKS)
def test_appendix_columns_reorder_without_losing_ids_dates_or_duplicate_rows(tmp_path, tax, form, header_row, first, last, caption_cell):
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    ref = reference[form]
    headers = headers_for(ref, header_row)
    values = synthetic_row(headers, 'SYNTHETIC MATCHED')
    name = str(ref[caption_cell].value) if caption_cell else form
    table = source_table(name, list(reversed(headers)), [list(reversed(values)), list(reversed(values))])
    workbook = export(tax, source_run(tax, [section(form, tables=[table])]), tmp_path)
    try:
        for row_number in [first, first + 1]:
            for column, value in enumerate(values, 1):
                cell = workbook[form].cell(row_number, column)
                assert cell.value == value and cell.data_type == 's'
                assert_format(cell, ref.cell(row_number, column))
        assert_layout(workbook[form], ref)
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('tax,form,header_row,first,boundary,caption_cell', [
    ('PPN', 'A1', 3, 4, 7, ''),
    ('PPh Unifikasi', 'Daftar I', 4, 5, 9, 'B3'),
])
def test_row_growth_preserves_new_row_styles_and_every_shifted_header_and_total(tmp_path, tax, form, header_row, first, boundary, caption_cell):
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    ref = reference[form]
    headers = headers_for(ref, header_row)
    rows = [synthetic_row(headers, f'SYNTHETIC ROW {i:03d}') for i in range(11)]
    name = str(ref[caption_cell].value) if caption_cell else form
    run = source_run(tax, [section(form, tables=[source_table(name, headers, rows)])])
    workbook = export(tax, run, tmp_path)
    try:
        sheet = workbook[form]
        shift = len(rows) - (boundary - first)
        for index, values in enumerate(rows):
            for column, value in enumerate(values, 1):
                cell = sheet.cell(first + index, column)
                assert cell.value == value
                reference_row = first + index if first + index < boundary else first
                assert_format(cell, ref.cell(reference_row, column))
        for row_number in range(boundary, ref.max_row + 1):
            for column in range(1, ref.max_column + 1):
                expected = ref.cell(row_number, column)
                actual = sheet.cell(row_number + shift, column)
                assert_format(actual, expected)
                assert actual.value == expected.value
            before = ref.row_dimensions[row_number]
            after = sheet.row_dimensions[row_number + shift]
            assert (after.height, after.hidden, after.outlineLevel) == (before.height, before.hidden, before.outlineLevel)
        for coordinate in ['A1', f'A{header_row}']:
            assert_format(sheet[coordinate], ref[coordinate])
        assert {str(r) for r in sheet.merged_cells.ranges} == {str(r) for r in ref.merged_cells.ranges}
        assert sheet.column_dimensions['B'].width == ref.column_dimensions['B'].width
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('tax', list(TYPES))
def test_ambiguous_headers_partial_tables_and_unknown_fields_stay_visible_as_raw_source(tmp_path, tax):
    form, first = ('A1', 4) if tax == 'PPN' else ('Daftar I', 5)
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    ref = reference[form]
    headers = headers_for(ref, 3 if tax == 'PPN' else 4)
    values = synthetic_row(headers, 'SYNTHETIC PARTIAL')
    partial_name = form if tax == 'PPN' else str(ref['B3'].value)
    tables = [source_table(partial_name, headers, [values], complete=False),
              source_table('SYNTHETIC AMBIGUOUS TABLE', ['NIK/NPWP', 'NIK/NPWP', 'Nilai'],
                           [['0000000000000002', '0000000000000002', '9.876,50']] * 2)]
    fields = [{'label': 'SYNTHETIC UNMAPPED FIELD', 'value': '=SUM(1,2)'},
              {'label': 'SYNTHETIC UNMAPPED FIELD', 'value': '=SUM(1,2)'}]
    text = 'SYNTHETIC CONTEXT MUST REMAIN VISIBLE'
    workbook = export(tax, source_run(tax, [section(form, fields=fields, tables=tables, text=text)]), tmp_path)
    try:
        assert all(workbook[form].cell(first, col).value is None for col in range(1, len(headers) + 1))
        expected = Counter(value for table in tables for row in table['rows'] for value in row)
        expected.update(field['value'] for field in fields)
        actual = Counter(cell.value for sheet in workbook for row in sheet for cell in row
                         if cell.value in expected)
        assert actual == expected
        for value in ['=SUM(1,2)', '0000000000000002', '02-01-2025']:
            assert all(c.data_type == 's' for c in cells_with(workbook, value))
        assert len(cells_with(workbook, text)) == 1
        assert_layout(workbook[form], ref)
    finally:
        workbook.close()
        reference.close()


@pytest.mark.parametrize('tax', list(TYPES))
def test_each_amendment_uses_independent_templates_and_exact_resume_links(tmp_path, tax):
    run = source_run(tax, [section(form, fields=[{'label': 'SYNTHETIC MARKER',
           'value': 'SYNTHETIC NORMAL ' + form}]) for form in TYPES[tax]['forms']])
    amendment = deepcopy(run['records'][0])
    amendment.update(key='synthetic-template-amendment', record_id='synthetic-template-amendment')
    amendment['meta']['Model SPT'] = 'Pembetulan 2'
    for sec in amendment['sections']:
        sec['fields'][0]['value'] = 'SYNTHETIC AMENDMENT ' + sec['name']
    run['records'].append(amendment)
    workbook = export(tax, run, tmp_path)
    resume = load_workbook(tmp_path / 'resume.xlsx')
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    try:
        forms = TYPES[tax]['forms']
        assert workbook.sheetnames == forms + [form + ' (2)' for form in forms]
        assert all(sheet.sheet_state == 'visible' for sheet in workbook)
        proof = exporter.read_workbook_proof(workbook)
        assert [r['meta']['Model SPT'] for r in proof['records']] == ['Normal', 'Pembetulan 2']
        for ordinal, model in [(0, 'NORMAL'), (1, 'AMENDMENT')]:
            for form in forms:
                name = form if ordinal == 0 else form + ' (2)'
                assert len(cells_with(workbook, 'SYNTHETIC ' + model + ' ' + form)) == 1
                assert_layout(workbook[name], reference[form])
        links = [cell.hyperlink for sheet in resume for row in sheet for cell in row if cell.hyperlink]
        targets = {(link.target, link.location) for link in links if link.target == TYPES[tax]['path']}
        assert {(TYPES[tax]['path'], "'Induk'!A1"), (TYPES[tax]['path'], "'Induk (2)'!A1")} <= targets
    finally:
        workbook.close()
        resume.close()
        reference.close()


@pytest.mark.parametrize('tax', list(TYPES))
def test_copied_worker_exports_using_only_explicit_packaged_template_resources(tmp_path, tax):
    resource = TYPES[tax]['resource']
    assert resource in runtime.WORKER_FILES, 'Missing approved worker resource is intentional feature RED'
    root = Path(__file__).resolve().parent.parent
    assert (root / resource).is_file(), 'Missing approved resource is intentional feature RED'
    assert (root / resource).read_bytes() == (FIXTURES / TYPES[tax]['reference']).read_bytes()
    runtime._resources(root, tmp_path / 'runtime')
    app = tmp_path / 'runtime/app'
    assert (app / resource).read_bytes() == (root / resource).read_bytes()
    run = source_run(tax, [section('Induk')])
    script = ("import json;from pathlib import Path;import coretax,coretax_exporter as e;"
              "r=json.loads(Path('synthetic-run.json').read_text());"
              "e.export_split_workbooks(r,Path('output'));coretax.verify_outputs(r,Path('output'))")
    (app / 'synthetic-run.json').write_text(json.dumps(run), encoding='utf-8')
    subprocess.run([sys.executable, '-c', script], cwd=app, check=True, capture_output=True, timeout=60)
    workbook = load_workbook(app / 'output' / TYPES[tax]['path'])
    reference = load_workbook(FIXTURES / TYPES[tax]['reference'])
    try:
        assert workbook.sheetnames == ['Induk']
        assert_layout(workbook['Induk'], reference['Induk'])
    finally:
        workbook.close()
        reference.close()
