"""Synthetic DOM-only footer admission, workbook and DER custody contracts.

All source values are synthetic. Hosted CI runners own runtime verification.
"""
from copy import deepcopy
from pathlib import Path

from openpyxl import load_workbook
import pytest

import coretax
import coretax_exporter as exporter
from support_templates import section, source_run


REFERENCE = Path(__file__).resolve().parents[1] / 'resources' / 'corporate_format.xlsx'


def headers(form, row):
    with_ref = load_workbook(REFERENCE, read_only=True)
    try:
        return [cell.value for cell in with_ref[form][row] if cell.value is not None]
    finally:
        with_ref.close()


def synthetic_table(form, header_row, ordinal, body_count, footer, spans,
                    *, complete=True, source_total=None):
    columns = headers(form, header_row)
    body = [[str(index + 1), *(['0'] * (len(columns) - 1))]
            for index in range(body_count)]
    return {
        'name': f'Tabel {ordinal}', 'group': f'SYNTHETIC {form} FOOTER',
        'headers': columns,
        'rows': [*body, list(footer)],
        'body_row_count': body_count,
        'source_total': body_count if source_total is None else source_total,
        'pages': 1, 'complete': complete,
        'footer': [list(footer)],
        'footer_spans': [list(spans)],
    }


def workbook(tmp_path, form, tables, *, partial_capture=False):
    run = source_run('PPh Badan', [section(form, tables=tables)])
    if partial_capture:
        run['records'][0]['capture_complete'] = False
    before = deepcopy(run)
    reports = []
    files = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == before  # DOM source values, footer and spans are never rewritten.
    coretax.verify_outputs(run, tmp_path)
    book_name, = [item for item in files if item != 'resume.xlsx']
    return load_workbook(tmp_path / book_name), reports[0]


def test_dom_l2_two_verified_total_footers_restore_all_fifteen_body_rows(tmp_path):
    first = synthetic_table('L2', 2, 1, 6,
                            ['', 'TOTAL', '100', '12,5', '200'],
                            [1, 5, 1, 1, 1])
    second = synthetic_table('L2', 12, 2, 9,
                             ['', 'TOTAL', '300', '', '400', ''],
                             [1, 5, 1, 2, 1, 2])
    book, report = workbook(tmp_path, 'L2', [first, second])
    try:
        sheet = book['L2']
        assert sheet['A9'].value == 'JUMLAH'
        assert sheet['A22'].value == 'JUMLAH'
        assert 'A9:F9' in sheet.merged_cells
        assert 'A22:F22' in sheet.merged_cells
        assert [sheet[f'A{row}'].value for row in range(3, 9)] == [
            str(i) for i in range(1, 7)]
        assert [sheet[f'A{row}'].value for row in range(13, 22)] == [
            str(i) for i in range(1, 10)]
        assert sheet['G9'].value == 100
        assert sheet['H9'].value == 0.125
        assert sheet['I9'].value == 200
        assert sheet['G22'].value == 300
        assert sheet['J22'].value == 400
        assert report['unmapped_tables'] == report['unmapped_rows'] == 0
    finally:
        book.close()


def test_dom_l3a_empty_body_keeps_only_original_verified_footer(tmp_path):
    foreign = synthetic_table('L3', 2, 1, 0,
                              ['', 'TOTAL', '100', '200', '', '300'],
                              [1, 4, 1, 1, 2, 1])
    book, report = workbook(tmp_path, 'L3', [foreign])
    try:
        sheet = book['L3']
        assert sheet['A4'].value == 'JUMLAH'
        assert 'A4:E4' in sheet.merged_cells
        assert sheet['F4'].value == 100
        assert sheet['G4'].value == 200
        assert sheet['J4'].value == 300
        assert report['unmapped_tables'] == report['unmapped_rows'] == 0
    finally:
        book.close()


def test_dom_l3b_partial_capture_never_maps_missing_source_rows(tmp_path):
    partial = synthetic_table('L3', 7, 3, 2, ['TOTAL', '100', '200', ''],
                              [4, 1, 1, 2], complete=False, source_total=4654)
    partial['footer'] += [
        ['KREDIT PAJAK LUAR NEGERI', '', '100', ''],
        ['JUMLAH KREDIT PAJAK', '', '100', ''],
    ]
    partial['footer_spans'] += [[4, 1, 1, 2], [4, 1, 1, 2]]
    partial['rows'] = [*partial['rows'][:2], *partial['footer']]
    book, report = workbook(tmp_path, 'L3', [partial], partial_capture=True)
    try:
        assert report['complete'] is False
        assert report['unmapped_tables'] == 1
        assert report['unmapped_rows'] == 5
        # Unverified pages and the original footer rows remain Audit-only.
    finally:
        book.close()


def test_dom_l11b_verified_average_footers_restore_source_bound_der(tmp_path):
    debts = ['TOTAL', *(['0'] * 12), '75']
    equity = ['TOTAL', *(['0'] * 12), '25']
    expenses = ['TOTAL', *(['0'] * 4)]
    tables = [
        synthetic_table('L11-B', 11, 1, 1, debts, [3, *([1] * 13)]),
        synthetic_table('L11-B', 17, 2, 5, equity, [1] * 14),
        synthetic_table('L11-B', 30, 3, 1, expenses, [1] * 5),
    ]
    book, report = workbook(tmp_path, 'L11-B', tables)
    try:
        sheet = book['L11-B']
        assert 'A13:C13' in sheet.merged_cells
        assert [sheet[address].value for address in ('A13', 'A23', 'A32')] == [
            'JUMLAH', 'JUMLAH', 'JUMLAH']
        assert sheet['P13'].value == 75
        assert sheet['N23'].value == 25
        assert sheet['C26'].value == '=P13'
        assert sheet['C27'].value == '=N23'
        assert sheet['D26'].value == '=C26/C27'
        assert report['derived_complete'] is True
        assert report['unmapped_tables'] == report['unmapped_rows'] == 0
    finally:
        book.close()


@pytest.mark.parametrize('form,header,ordinal,footer,spans', [
    ('L2', 2, 1, ['', 'total', '100', '0', '0'], [1, 5, 1, 1, 1]),
    ('L2', 12, 2, ['', 'TOTAL', '300', '', '400', ''], [1, 4, 2, 2, 1, 2]),
    ('L3', 2, 1, [None, 'TOTAL', '100', '200', '', '300'], [1, 4, 1, 1, 2, 1]),
    ('L11-B', 11, 1, ['TOTAL', *(['0'] * 13)], [2, 2, *([1] * 12)]),
    ('L11-B', 17, 2, ['total', *(['0'] * 13)], [1] * 14),
    ('L11-B', 30, 3, ['TOTAL ', *(['0'] * 4)], [1] * 5),
])
def test_unreviewed_dom_total_footer_remains_unmapped(
        tmp_path, form, header, ordinal, footer, spans):
    table = synthetic_table(form, header, ordinal, 1, footer, spans)
    book, report = workbook(tmp_path, form, [table])
    try:
        assert report['complete'] is False
        assert report['unmapped_tables'] == 1
        assert report['unmapped_rows'] == 2
        if form == 'L11-B':
            assert report['derived_complete'] is False
    finally:
        book.close()
