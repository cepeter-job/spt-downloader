"""Versioned synthetic source-to-XLSX contracts for issue #187.

The source workbook remains authoritative; a semantic golden pins literal
cells and types without depending on ZIP timestamps or workbook-local styles.
This first slice does not claim JSON/DOM or live Coretax equivalence.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest
from openpyxl import load_workbook

import coretax
import coretax_exporter as exporter
from support_runs import model_run


GOLDEN = json.loads(
    (Path(__file__).parent / 'fixtures' / 'workbook_contract_v1.json').read_text(encoding='utf-8')
)


@pytest.mark.parametrize('case', GOLDEN['cases'], ids=lambda case: case['tax'])
def test_semantic_golden_preserves_source_rows_and_workbook_proof(tmp_path, case):
    assert GOLDEN['version'] == 1
    run = model_run(case['tax'], case['period'], models=('Normal',))
    original = deepcopy(run)

    files = exporter.export_split_workbooks(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)

    assert run == original
    assert len(files) == 2 and 'resume.xlsx' in files
    filename, = set(files) - {'resume.xlsx'}
    with_workbook = files[filename]
    workbook = load_workbook(with_workbook)
    resume = load_workbook(files['resume.xlsx'])
    try:
        assert workbook.sheetnames == ['Induk', 'L-Z']
        assert resume['Ringkasan']['B6'].value == 'COMPLETE'
        proof = exporter.read_workbook_proof(workbook)
        assert proof == {
            'format': 'spt-downloader-forms',
            'version': 1,
            'npwp': run['npwp'],
            'year': run['year'],
            'year_basis': run['year_basis'],
            'complete': True,
            'records': [{
                'record_id': 'synthetic-model-return-1',
                'source_status': 'Fixture',
                'meta': run['records'][0]['meta'],
                'capture_complete': True,
                'sections': [{'name': 'Induk'}, {'name': 'L-Z'}],
            }],
        }

        sheet = workbook[GOLDEN['generic_sheet']]
        assert sheet.max_row == 10 and sheet.max_column == 3
        for coordinate, expected in GOLDEN['generic_cells'].items():
            assert sheet[coordinate].value == expected, (case['tax'], coordinate)
        assert all(sheet[coordinate].data_type == 's'
                   for coordinate in ('C3', 'A9', 'B9', 'A10', 'B10'))
        assert all(sheet[coordinate].data_type == 'n'
                   for coordinate in ('C9', 'C10'))
        assert sheet['B9'].value == sheet['B10'].value
        assert sheet['B9'].value != str(sheet['C9'].value)

        marker = 'SYNTHETIC synthetic-model-return-1 / Induk'
        visible_values = [cell.value for row in workbook['Induk'] for cell in row]
        assert (marker in visible_values) is case['induk_marker_visible']
        if 'induk_amount_cell' in case:
            assert workbook['Induk'][case['induk_amount_cell']].value == case['induk_amount']
    finally:
        workbook.close()
        resume.close()


def test_golden_distinguishes_ordered_rows_instead_of_deduplicating(tmp_path):
    run = model_run(models=('Normal',))
    table = run['records'][0]['sections'][1]['tables'][0]
    table['rows'][1] = ['00008', '2.345,67']
    original = deepcopy(run)

    files = exporter.export_split_workbooks(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    assert run == original
    filename, = set(files) - {'resume.xlsx'}
    workbook = load_workbook(files[filename])
    try:
        sheet = workbook['L-Z']
        assert [[sheet.cell(row, col).value for col in (1, 2, 3)]
                for row in (9, 10)] == [
                    ['00007', '1.234,50', 1234.5],
                    ['00008', '2.345,67', 2345.67],
                ]
        assert all(sheet.cell(row, 1).data_type == 's' for row in (9, 10))
    finally:
        workbook.close()


def test_partial_table_stays_partial_in_saved_proof_and_visible_result(tmp_path):
    run = model_run(models=('Normal',))
    run['complete'] = False
    record = run['records'][0]
    record['capture_complete'] = False
    record['sections'][1]['tables'][0]['complete'] = False
    original = deepcopy(run)

    files = exporter.export_split_workbooks(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)

    assert run == original
    filename, = set(files) - {'resume.xlsx'}
    workbook = load_workbook(files[filename])
    resume = load_workbook(files['resume.xlsx'])
    try:
        proof = exporter.read_workbook_proof(workbook)
        assert proof['complete'] is False
        assert proof['records'][0]['capture_complete'] is False
        assert workbook['L-Z']['A13'].value == 'PARTIAL: paginasi tidak selesai'
        assert resume['Ringkasan']['B6'].value == 'PARTIAL'
        assert resume['Daftar SPT']['I5'].value == 'PARTIAL'
    finally:
        workbook.close()
        resume.close()
