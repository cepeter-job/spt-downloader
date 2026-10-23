"""Final saved layouts use synthetic rows and hand-checked reference positions."""
from copy import deepcopy
from decimal import Decimal

import pytest
from openpyxl import load_workbook

import coretax
import coretax_exporter as exporter
from support_templates import section, run_for, source_appendix, APPENDICES
from support_pph21_dom import appendix_table


def saved(tmp_path, tax, sections):
    run = run_for(sections, model='Amendment 001')
    run['records'][0]['meta']['Jenis Pajak'] = tax
    before = deepcopy(run)
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    coretax.verify_outputs(run, tmp_path)
    assert run == before
    path, = [p for p in paths if p != 'resume.xlsx']
    book = load_workbook(tmp_path/path)
    proof = exporter.read_workbook_proof(book)
    assert proof['records'][0]['meta']['Model SPT'] == 'Amendment 001'
    return book, reports


@pytest.mark.parametrize('form,header,first,total,columns', APPENDICES)
@pytest.mark.parametrize('count', [0, 2, 18])
def test_ppn_keeps_only_used_body_or_one_empty_slot_and_captured_total(tmp_path, form, header, first, total, columns, count):
    table, amounts = source_appendix(form, header, first, total, columns, count=count)
    # Every body value is a real synthetic row, including a literal zero.
    for values in table['rows'][:count]:
        for col in columns:
            values[col-1] = '0'
    book, reports = saved(tmp_path, 'PPN', [section(form, tables=[table])])
    try:
        ws = book[form]
        target = first + max(1, count)
        assert ws.cell(target, 1).value == 'TOTAL'
        assert ws.max_row == target
        assert [ws.cell(target, col).value for col in columns] == [float(Decimal(v.replace('.', '').replace(',', '.'))) for v in amounts]
        assert len([r for r in range(first,target) if ws.cell(r,1).value is not None]) == count
        assert all(r['complete'] for r in reports)
        if count:
            assert ws.cell(first, columns[0]).value == 0
    finally:
        book.close()


def test_ppn_induk_removes_only_two_redundant_spacers_and_moves_merges(tmp_path):
    book, _ = saved(tmp_path, 'PPN', [section('Induk')])
    try:
        ws=book['Induk']
        assert ws.max_row == 76
        assert ws['A8'].value == 'I.'
        assert 'A9:D9' in {str(x) for x in ws.merged_cells.ranges}
        assert all(ws.cell(7,c).value is None for c in range(1,9))
    finally:
        book.close()


@pytest.mark.parametrize('form,groups,counts,total,headers', [
    ('L-IA', ['LIST-IA'], [7], 12, [3]),
    ('L-IB', ['BPA1','BPA2'], [0,0], 11, [4,8]),
    ('L-II', ['BPA1','BPA2'], [0,0], 11, [4,8]),
    ('L-III', ['BP21','BP26'], [3,0], 13, [4,10]),
])
def test_pph21_matches_reference_body_capacity_headers_spacers_and_totals(tmp_path,form,groups,counts,total,headers):
    tables=[]
    for index,(group,count) in enumerate(zip(groups,counts)):
        table,_=appendix_table(form,group,count,with_totals=index==len(groups)-1)
        tables.append(table)
    book,reports=saved(tmp_path,'PPh Pasal 21/26',[section(form,tables=tables)])
    try:
        ws=book[form]
        assert ws.cell(total,1).value.startswith('TOTAL' if form=='L-II' else 'JUMLAH')
        assert ws.max_row == total + (0 if form=='L-II' else 2)
        assert [ws.cell(r,1).value for r in headers] == ['NO.']*len(headers)
        assert all(r['complete'] for r in reports)
        if form=='L-IA':
            assert ws['B4'].value == '0000000000000002'
            assert ws['H4'].value == 0.1 and ws['H4'].data_type == 'n'
            assert ws['H4'].number_format == '0.00%'
            assert all(ws.cell(11,c).value is None for c in range(1,15))
    finally:
        book.close()


@pytest.mark.parametrize('rate,valid,expected', [('0',True,0),('2,50',True,0.025),('100,00',True,1),
    ('1.5',False,'1.5'),('1,234',True,0.01234),('999.999.999.999.999,99',False,'999.999.999.999.999,99')])
def test_lia_rate_fraction_is_strict_and_unsafe_source_stays_partial(tmp_path,rate,valid,expected):
    table,_=appendix_table('L-IA','LIST-IA',1)
    table['rows'][0][table['headers'].index('TARIF PAJAK (%)')]=rate
    book,reports=saved(tmp_path,'PPh Pasal 21/26',[section('L-IA',tables=[table])])
    try:
        assert book['L-IA']['H4'].value == expected
        assert reports[0]['complete'] is valid
        assert reports[0]['unmapped_tables'] == (0 if valid else 1)
    finally:
        book.close()


def test_pph21_accounting_uses_whole_display_without_rounding_saved_amounts(tmp_path):
    table,_=appendix_table('L-III','BP26',1,with_totals=True)
    book,_=saved(tmp_path,'PPh Pasal 21/26',[section('L-III',tables=[table])])
    try:
        money=[c for ws in book for row in ws for c in row if '"Rp"' in c.number_format]
        assert money
        assert all('.00' not in c.number_format.split(';')[0] for c in money)
        assert any(c.value==1234.5 for c in money)
    finally:
        book.close()
