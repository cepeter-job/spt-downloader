"""PPN numeric amount and requested row-style contracts; synthetic only."""
from copy import copy
from decimal import Decimal
import pytest
from support_templates import section, APPENDICES, export_ppn, source_appendix


@pytest.mark.parametrize('form,case,total', [('B1', APPENDICES[2], 6), ('C', APPENDICES[5], 7)])
def test_remove_only_unused_placeholder_before_total(tmp_path, form, case, total):
    table, _ = source_appendix(*case)
    wb, _, _ = export_ppn(tmp_path, [section(form, tables=[table])])
    try:
        assert wb[form].max_row == total
        assert wb[form].cell(total, 1).value == 'TOTAL'
    finally:
        wb.close()


@pytest.mark.parametrize('case', [APPENDICES[2], APPENDICES[5]], ids=['B1', 'C'])
def test_placeholder_removal_never_deletes_captured_body_rows(tmp_path, case):
    table, _ = source_appendix(*case, count=9)
    wb, _, _ = export_ppn(tmp_path, [section(case[0], tables=[table])])
    try:
        first = case[2]
        assert [wb[case[0]].cell(row, 2).value for row in range(first, first + 9)] == [
            f'SYNTHETIC-{i}-2' for i in range(9)]
        assert wb[case[0]].cell(first + 9, 1).value == 'TOTAL'
    finally:
        wb.close()


def test_b2_seventh_row_is_normal_bordered_data_not_bold_total(tmp_path):
    table, _ = source_appendix(*APPENDICES[3], count=9)
    wb, _, _ = export_ppn(tmp_path, [section('B2', tables=[table])])
    try:
        sheet = wb['B2']
        for column in range(1, 11):
            assert sheet.cell(7, column).font.bold is False
            assert copy(sheet.cell(7, column).border) == copy(sheet.cell(6, column).border)
        assert sheet['B7'].value == 'SYNTHETIC-3-2'
        assert sheet['F13'].font.bold is True
    finally:
        wb.close()


@pytest.mark.parametrize('case', APPENDICES, ids=[case[0] for case in APPENDICES])
def test_only_monetary_appendix_columns_become_numeric(tmp_path, case):
    table, amounts = source_appendix(*case, count=1)
    for column in case[4]:
        table['rows'][0][column - 1] = '1.234,50'
    # Digit-looking identities must remain literal, including leading zeroes.
    table['rows'][0][1] = '0000000000000001'
    wb, _, original = export_ppn(tmp_path, [section(case[0], tables=[table])])
    try:
        sheet = wb[case[0]]
        for column in case[4]:
            cell = sheet.cell(case[2], column)
            assert cell.data_type == 'n' and cell.value == 1234.5
        assert sheet.cell(case[2], 2).value == '0000000000000001'
        assert sheet.cell(case[2], 2).data_type == 's'
        total = next(row for row in range(case[2], sheet.max_row + 1)
                     if sheet.cell(row, 1).value == 'TOTAL')
        for column, raw in zip(case[4], amounts):
            value = Decimal(raw.replace('.', '').replace(',', '.'))
            assert Decimal(str(sheet.cell(total, column).value)) == value
            assert sheet.cell(total, column).data_type == 'n'
        assert original['records'][0]['sections'][0]['tables'][0]['rows'][0][case[4][0] - 1] == '1.234,50'
    finally:
        wb.close()


@pytest.mark.parametrize('raw,expected', [('0', 0), ('-17,25', -17.25), ('1.234.567,89', 1234567.89)])
def test_induk_amount_numeric_but_period_and_status_keep_text(tmp_path, raw, expected):
    fields = [
        {'field':'Period', 'label':'Periode * / Periode Pembukuan', 'group':'HEADER', 'value':'022031'},
        {'field':'', 'label':'Normal/Pembetulan', 'group':'HEADER', 'value':'Pembetulan'},
        {'field':'', 'label':'PPN kurang atau (lebih) bayar (III.A - III.B - III.C - III.D)', 'value':raw},
    ]
    wb, _, _ = export_ppn(tmp_path, [section('Induk', fields=fields)])
    try:
        assert wb['Induk']['E45'].data_type == 'n'
        assert wb['Induk']['E45'].value == expected
        for cell, value in [('D4','02'), ('D5','2031'), ('D6','Pembetulan')]:
            assert wb['Induk'][cell].value == value and wb['Induk'][cell].data_type == 's'
    finally:
        wb.close()


@pytest.mark.parametrize('raw', ['=1+1', '1.23.456', '1234567890123456,78', 'NaN', '1e99'])
def test_unsafe_or_precision_losing_amount_keeps_source_text(tmp_path, raw):
    field = {'field':'', 'label':'PPN kurang atau (lebih) bayar (III.A - III.B - III.C - III.D)', 'value':raw}
    wb, _, _ = export_ppn(tmp_path, [section('Induk', fields=[field])])
    try:
        assert wb['Induk']['E45'].value == raw and wb['Induk']['E45'].data_type == 's'
    finally:
        wb.close()
