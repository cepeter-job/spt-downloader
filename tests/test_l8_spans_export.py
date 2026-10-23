"""Owned colspan proof must resolve headings without fabricating money cells."""
from copy import deepcopy
import pytest
from support_templates import section
from test_corporate_compact_export import export
from support_l8_spans import source


def test_owned_l8_spans_export_all_rows_and_captured_footer(tmp_path):
    table = source()
    before = deepcopy(table)
    book, reports = export(tmp_path, [section('L8', tables=[table])])
    try:
        sheet = book['L8']
        assert sheet.max_row == 10 and sheet.max_column == 3
        assert list(sheet.values) == [
            ('NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)'),
            ('1.', 'SYNTHETIC TURNOVER', None), (None, 'SYNTHETIC TURNOVER', 8000),
            ('2.', 'SYNTHETIC TAXABLE', None), (None, 'SYNTHETIC GRANTED', 0),
            (None, 'SYNTHETIC NOT GRANTED', 200), ('3.', 'SYNTHETIC TAX', None),
            (None, 'SYNTHETIC TAX GRANTED', 0), (None, 'SYNTHETIC TAX OTHER', 44),
            (None, 'JUMLAH PPh Terutang', 44)]
        assert {str(r) for r in sheet.merged_cells.ranges} == {'B2:C2', 'B4:C4', 'B7:C7'}
        assert reports[0]['complete'] and reports[0]['unmapped_rows'] == 0
        for address in ('C3','C5','C6','C8','C9','C10'):
            assert sheet[address].data_type == 'n' and '#,##0' in sheet[address].number_format
        assert table == before
    finally:
        book.close()


@pytest.mark.parametrize('broken', ['missing_spans', 'missing_owner', 'foreign_owner', 'foreign_group',
    'missing_rowspans', 'rowspan', 'zero_span', 'bool_span', 'wide_span', 'reverse_span',
    'short_metadata', 'extra_metadata', 'wrong_count', 'multiple_pages', 'incomplete'])
def test_l8_invalid_span_proof_stays_unresolved_without_padding(tmp_path, broken):
    table = source()
    if broken == 'missing_spans': table.pop('body_spans')
    elif broken == 'missing_owner': table.pop('source_structure')
    elif broken == 'foreign_owner': table['source_structure']['component'] = 'synthetic-foreign-grid'
    elif broken == 'foreign_group': table['source_structure']['groups'] = ['SYNTHETIC OTHER OWNER']
    elif broken == 'missing_rowspans': table.pop('body_rowspans')
    elif broken == 'rowspan': table['body_rowspans'][0][1] = 2
    elif broken == 'zero_span': table['body_spans'][0][1] = 0
    elif broken == 'bool_span': table['body_spans'][0][0] = True
    elif broken == 'wide_span': table['body_spans'][0] = [2, 2]
    elif broken == 'reverse_span': table['body_spans'][0] = [2, 1]
    elif broken == 'short_metadata': table['body_spans'].pop()
    elif broken == 'extra_metadata': table['body_spans'].append([1, 1, 1])
    elif broken == 'wrong_count': table['body_row_count'] = 7
    elif broken == 'multiple_pages': table['pages'] = 2
    elif broken == 'incomplete': table['complete'] = False
    before = deepcopy(table)
    book, reports = export(tmp_path, [section('L8', tables=[table])])
    try:
        assert book['L8'].max_row == 2
        assert not book['L8'].merged_cells.ranges
        assert not reports[0]['complete'] and reports[0]['unmapped_rows'] == 9
        assert table == before
    finally:
        book.close()


def test_l8_unsafe_amount_keeps_literal_and_truthful_unmapped_count(tmp_path):
    table = source()
    table['rows'][1][2] = '1234567890123456'
    book, reports = export(tmp_path, [section('L8', tables=[table])])
    try:
        assert book['L8']['C3'].value == '1234567890123456'
        assert book['L8']['C3'].data_type == 's'
        assert not reports[0]['complete'] and reports[0]['unmapped_rows'] == 1
        assert book['L8']['C10'].value == 44
    finally:
        book.close()
