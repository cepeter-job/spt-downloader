"""Approved corporate layout contract, using synthetic captures only."""
from copy import deepcopy
from pathlib import Path

import pytest
from openpyxl import load_workbook
import coretax
import coretax_exporter as exporter
from support_templates import assert_layout, section, source_run

RESOURCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'
FORMS = ['L1-D', 'L2', 'L3', 'L4', 'L6', 'L7', 'L9', 'L10-A', 'L10-C',
         'L11-A', 'L11-B', 'L11-C']


def export(tmp_path, sections):
    run = source_run('PPh Badan', sections)
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
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
    reference = load_workbook(RESOURCE)
    try:
        assert reference.sheetnames == FORMS
        sheet = reference['L1-D']
        for row in range(44, 102):
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
