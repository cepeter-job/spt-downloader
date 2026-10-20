"""Synthetic saved-workbook border regression; no private input data."""
from copy import copy
import pytest

from support_templates import run_for, section, table
from test_pph21_template import export, row


@pytest.mark.parametrize('count', [7, 11, 40])
def test_lia_row_eleven_and_grown_rows_keep_all_body_borders(tmp_path, count):
    source = row(ia=True)
    book = export(run_for([section('L-IA', tables=[table('L-IA', [source] * count, ia=True)])]), tmp_path)
    try:
        sheet = book['L-IA']
        for row_number in range(5, max(12, count + 5)):
            for column in range(1, 15):
                cell = sheet.cell(row_number, column)
                assert copy(cell.border) == copy(sheet.cell(5, column).border)
                for edge in ('left', 'right', 'top', 'bottom'):
                    assert getattr(cell.border, edge).style == 'thin', (cell.coordinate, edge)
    finally:
        book.close()
