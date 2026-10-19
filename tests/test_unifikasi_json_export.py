"""Synthetic native Unifikasi packet-to-Excel contracts; runner-only."""
from copy import deepcopy

import pytest

from coretax_masa_json import adapt_masa_detail
from masa_projection_fixture import native_case
from support_masa_native import exported

TAX = 'PPh Unifikasi'
ACCOUNTING_RP = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"??_-;_-@_-'


@pytest.mark.parametrize('populated', [False, True])
def test_native_unifikasi_packets_export_four_approved_numeric_forms(tmp_path, populated):
    case = native_case(TAX, populated=populated)
    before = deepcopy(case)
    result = adapt_masa_detail(case['packets'], record=case['record'],
                               scope=case['scope'], observed_forms=case['forms'])
    assert result['eligible'], result['reason']
    assert result['coverage']['complete']
    assert len(result['coverage']['grids']) == 5
    assert case == before
    book = exported(tmp_path, TAX, result['sections'])
    try:
        assert book.sheetnames == ['INDUK', 'DAFTAR-I', 'DAFTAR-II', 'LAMPIRAN-I']
        induk = book['INDUK']
        assert induk['B10'].value == 'Pasal 4 Ayat 2'
        for coordinate, value in [('D10', 17), ('E10', 19), ('E25', 23)]:
            cell = induk[coordinate]
            assert cell.value == value
            assert cell.data_type == 'n'
            assert cell.number_format == ACCOUNTING_RP
        # Reported totals need not equal the sum of the captured body.
        assert induk['E25'].value != induk['E10'].value
        daftar = book['DAFTAR-I']
        assert daftar['I4'].value == 'DASAR PENGENAAN PAJAK (Rp)'
        assert daftar['A1'].value is not None
        if populated:
            for row in range(5, 11):
                assert daftar.cell(row, 2).value == '0000000000000002'
                assert daftar.cell(row, 2).data_type == 's'
                assert daftar.cell(row, 4).value == '0000123'
                assert daftar.cell(row, 4).data_type == 's'
                for column, amount in [(9, 1200), (10, 30)]:
                    cell = daftar.cell(row, column)
                    assert cell.value == amount and cell.data_type == 'n'
                    assert cell.number_format == ACCOUNTING_RP
        for name in ['DAFTAR-II', 'LAMPIRAN-I']:
            assert book[name]['A1'].value is not None
            projected = next(section for section in result['sections'] if section['name'] == name)
            assert all(table['body_row_count'] == 0 and table['source_total'] == 0
                       and table['complete'] for table in projected['tables'])
            assert all(table['footer'] for table in projected['tables'])
    finally:
        book.close()
