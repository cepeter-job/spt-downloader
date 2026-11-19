"""Saved multi-form corporate presentation contract; synthetic evidence only.

The 12-sheet XLSX is the approved reference for its existing appendices.
Induk and L8 are code-generated approved layouts. Compare the *saved* combined
workbook rather than changing the sanitized source or relying on style IDs.
Runtime verification belongs to GitHub Actions, not local taxpayer machines.
"""
from copy import copy, deepcopy
from pathlib import Path

from openpyxl import load_workbook
import pytest

import coretax
import coretax_exporter as exporter
from support_templates import section, source_run
from test_badan_shouldbe_presentation import fields as induk_fields
from test_corporate_compact_export import table


REFERENCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'
L8_GROUP = (
    'PERHITUNGAN FASILITAS PENGURANGAN TARIF PPh BAGI WAJIB PAJAK BADAN '
    'DALAM NEGERI BERDASARKAN PASAL 31E AYAT (1) UNDANG-UNDANG PPh'
)


def _l8_table():
    footer = ['JUMLAH', '', '1.234,50']
    return {
        'name': 'SYNTHETIC L8', 'group': L8_GROUP,
        'headers': ['NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)'],
        'rows': [
            ['01', 'SYNTHETIC FACILITY', '1.234,50'],
            ['02', 'SYNTHETIC ZERO', '0'],
            footer,
        ],
        'body_row_count': 2, 'source_total': 2, 'complete': True,
        'footer': [footer], 'footer_spans': [[1, 1, 1]],
    }


def _l11b_tables(capital_rows):
    debt = table(
        'L11-B', 11,
        [['0000000000000002', 'SYNTHETIC LENDER', 'RELATION'] + ['1,00'] * 13],
        footer=[['JUMLAH'] + ['4,00'] * 12 + ['9.000,00']],
        spans=[[3] + [1] * 13],
    )
    capital = table(
        'L11-B', 17,
        [['SYNTHETIC CAPITAL'] + ['2,00'] * 13 for _ in range(capital_rows)],
        footer=[['JUMLAH'] + ['5,00'] * 12 + ['3.000,00']],
        spans=[[1] * 14],
    )
    return [capital, debt]


def _whole_rupiah(cell, value):
    # Excel retains the original number, even when its display is whole rupiah.
    assert cell.value == value and cell.data_type == 'n'
    assert 'Rp' in cell.number_format
    assert '#,##0.' not in cell.number_format
    assert '0.00' not in cell.number_format


@pytest.mark.parametrize('capital_rows', [1, 7])
def test_final_saved_induk_l8_der_visual_contract_in_one_workbook(tmp_path, capital_rows):
    sections = [
        section('Induk', fields=induk_fields()),
        section('L8', tables=[_l8_table()]),
        section('L11-B', tables=_l11b_tables(capital_rows)),
    ]
    run = source_run('PPh Badan', sections)
    source_before = deepcopy(run)
    reference_before = REFERENCE.read_bytes()
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert run == source_before
    assert REFERENCE.read_bytes() == reference_before
    coretax.verify_outputs(run, tmp_path)
    filename, = [item for item in paths if item != 'resume.xlsx']

    workbook = load_workbook(tmp_path / filename)
    approved = load_workbook(REFERENCE)
    try:
        assert workbook.sheetnames == ['Induk', 'L8', 'L11-B']
        assert len(reports) == 3
        assert all(report['complete'] for report in reports)
        assert all(report['unmapped_fields'] == report['unmapped_tables'] ==
                   report['unmapped_rows'] == 0 for report in reports)

        # Approved dynamic Induk: text identifiers, two columns, clean heading.
        induk = workbook['Induk']
        assert induk.max_column == 2 and induk.max_row == 30
        assert induk['B2'].value == '2025' and induk['B2'].data_type == 's'
        assert induk['B6'].value == '0000000000000002'
        assert induk['B6'].data_type == 's'
        assert induk['A13'].value == 'PENGHITUNGAN PPh'
        assert induk['A13'].font.bold
        assert all(cell.value is None for cell in induk[12])
        assert induk.column_dimensions['A'].width == 110.7109375
        assert induk.column_dimensions['B'].width == 49.7109375
        _whole_rupiah(induk['B16'], 1234.5)

        # Approved dynamic L8: three columns, preserved footer and thin grid.
        l8 = workbook['L8']
        assert (l8.max_row, l8.max_column) == (4, 3)
        assert [cell.value for cell in l8[1]] == [
            'NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)']
        assert [l8[f'A{row}'].value for row in (2, 3, 4)] == [
            '01', '02', 'JUMLAH']
        for address, value in [('C2', 1234.5), ('C3', 0), ('C4', 1234.5)]:
            _whole_rupiah(l8[address], value)
            assert l8[address].border.top.style == 'thin'
            assert l8[address].border.bottom.style == 'thin'
        assert [l8.column_dimensions[c].width for c in 'ABC'] == [
            4.42578125, 96.28515625, 36]
        assert l8.page_setup.orientation == 'landscape'

        # Template-backed L11-B: original heading/format, compacting-aware DER.
        der = workbook['L11-B']
        reference = approved['L11-B']
        assert [der.cell(11, c).value for c in range(1, 17)] == [
            reference.cell(11, c).value for c in range(1, 17)]
        for c in 'ABC':
            assert der.column_dimensions[c].width == reference.column_dimensions[c].width
        assert 'A13:C13' in der.merged_cells
        _whole_rupiah(der['P13'], 9000)
        capital_total_row = 18 + capital_rows
        _whole_rupiah(der[f'N{capital_total_row}'], 3000)
        ratio_row = 21 + capital_rows
        assert der[f'A{ratio_row}'].value == 'PERHITUNGAN DER'
        assert der[f'C{ratio_row}'].value == '=P13'
        assert der[f'C{ratio_row + 1}'].value == f'=N{capital_total_row}'
        assert der[f'D{ratio_row}'].value == (
            f'=C{ratio_row}/C{ratio_row + 1}')
        assert der[f'D{ratio_row}'].number_format == '0.00'
        assert f'A{ratio_row}:A{ratio_row + 1}' in der.merged_cells
        assert f'D{ratio_row}:D{ratio_row + 1}' in der.merged_cells
        assert copy(der['A11'].font) == copy(reference['A11'].font)

        # Formatting must be checked in the persisted XLSX, not only in memory.
        for sheet in workbook:
            for row in sheet:
                for cell in row:
                    if 'Rp' in cell.number_format and '*' in cell.number_format:
                        assert '#,##0.' not in cell.number_format
                        assert '0.00' not in cell.number_format
    finally:
        workbook.close()
        approved.close()
