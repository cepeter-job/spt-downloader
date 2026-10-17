"""Synthetic PPN grid contracts: exact columns, offsets and source provenance."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata, JsonSafetyError

RECORD = '00000000-0000-4000-8000-000000000001'


def project(form, pages, headers, **options):
    implementation = getattr(importlib.import_module('coretax_masa_bindings'), 'project_ppn_grid', None)
    assert callable(implementation), 'PPN grid projection is not implemented'
    return implementation(form, pages, headers, record_id=RECORD, timezone_name='Asia/Jakarta', **options)


from masa_json_fixtures import page


def row():
    return _corporate_json('''{"Name":"SYNTHETIC COUNTERPARTY","TIN":"0000000000000000",
      "DocumentNumberByBuyerInfor":"000000000099","DocumentNumber":"0000123",
      "DocumentDate":"2025-01-02T00:00:00","TaxBase":1200,"OtherTaxBase":null,
      "VAT":132,"STLG":0,"TaxInvoiceCode":"01","Information":"SYNTHETIC"}''')


@pytest.mark.parametrize('form', ['A-2', 'B-2', 'B-3'])
def test_ppn_grid_columns_and_buyer_identifier_override_are_form_specific(form):
    source = row(); before = deepcopy(source)
    headers = ['No.', 'Nama', 'TIN', 'Nomor', 'Tanggal', 'DPP', 'DPP Nilai Lain', 'PPN', 'PPnBM', 'Keterangan']
    result = project(form, [page([source], 1)], headers)
    assert result['table']['rows'] == [['1', 'SYNTHETIC COUNTERPARTY',
        '000000000099' if form == 'A-2' else '0000000000000000',
        '0000123', '02-01-2025', '1.200', '0', '132', '0', '01']]
    assert result['table']['headers'] == headers
    assert result['table']['complete'] is True
    assert source == before
    fields = [p['path'] for p in result['provenance']]
    assert ['Data', 0, 'OtherTaxBase'] in fields
    if form == 'A-2': assert ['Data', 0, 'DocumentNumberByBuyerInfor'] in fields


@pytest.mark.parametrize('form,columns', [('A-1', 6), ('B-1', 9)])
def test_ppn_import_export_grid_columns_do_not_shift_when_empty(form, columns):
    result = project(form, [page([row()], 1)], [f'COLUMN {i}' for i in range(columns)])
    values = result['table']['rows'][0]
    assert len(values) == columns
    assert values[-1] == 'SYNTHETIC'
    assert values[2 if form == 'A-1' else 3] == '0000123'


def test_ppn_grid_pages_preserve_duplicate_rows_and_page_local_ordinals():
    source = row()
    pages = [page([source, deepcopy(source)], 3), page([deepcopy(source)], 3, first=2)]
    before = deepcopy(pages)
    result = project('A-2', pages, ['column'] * 10)
    table = result['table']
    assert table['body_row_count'] == table['source_total'] == 3
    assert [r[0] for r in table['rows']] == ['1', '2', '1']
    assert table['rows'][0][1:] == table['rows'][1][1:] == table['rows'][2][1:]
    assert pages == before
    assert {p['sequence'] for p in result['provenance']} == {1, 3}


@pytest.mark.parametrize('kind', ['gap', 'overlap', 'changed_total', 'oversized_page', 'foreign_record'])
def test_grid_contradictions_fail_closed(kind):
    pages = [page([row(), row()], 3), page([row()], 3, first=2)]
    if kind == 'gap': pages[1]['request']['First'] = 3
    elif kind == 'overlap': pages[1]['request']['First'] = 1
    elif kind == 'changed_total': pages[1]['payload']['TotalRecords'] = _corporate_json('4')
    elif kind == 'oversized_page': pages[0]['request']['Rows'] = 1
    else: pages[1]['request']['ReturnSheetRecordId'] = '00000000-0000-4000-8000-000000000099'
    with pytest.raises(JsonSafetyError):
        project('A-2', pages, ['column'] * 10)


def test_truncated_grid_is_not_complete():
    with pytest.raises(_UnsupportedMetadata):
        project('A-2', [page([row(), row()], 3)], ['column'] * 10)


@pytest.mark.parametrize('kind', ['missing_column', 'missing_total', 'unknown_form', 'wrong_header_width'])
def test_unknown_grid_contract_cannot_invent_cells(kind):
    data = row(); pages = [page([data], 1)]; form = 'A-2'; headers = ['column'] * 10
    if kind == 'missing_column': data.pop('DocumentNumber')
    elif kind == 'missing_total': pages[0]['payload'].pop('TotalRecords')
    elif kind == 'unknown_form': form = 'INVENTED'
    else: headers = headers[:-1]
    with pytest.raises(_UnsupportedMetadata):
        project(form, pages, headers)


def test_explicit_zero_total_with_empty_grid_is_complete():
    result = project('A-2', [page([], 0)], ['column'] * 10)
    assert result['table']['rows'] == []
    assert result['table']['body_row_count'] == result['table']['source_total'] == 0
    assert result['table']['complete'] is True


def test_ppn_c_uses_buyer_seller_fields_and_bound_transaction_labels():
    source = _corporate_json('''{"SellerTin":"000001","SellerName":"SELLER",
        "BuyerTin":"000002","BuyerName":"BUYER","TypeOfVat":"SYNTHETIC-CODE",
        "BillingNumber":"000003","BillingDate":"2025-01-02","CodeAndSerialNumber":"000004",
        "TaxBase":1000,"OtherTaxBase":900,"VAT":100,"STLG":0,"Information":"INFO"}''')
    result = project('C', [page([source], 1)], ['column'] * 14,
                     lookups={'TypeOfVat': {'SYNTHETIC-CODE': 'SYNTHETIC LABEL'}})
    assert result['table']['rows'] == [['1', '000001', 'SELLER', '000002', 'BUYER',
        'SYNTHETIC LABEL', '000003', '02-01-2025', '000004', '1.000', '900', '100', '0', 'INFO']]


@pytest.mark.parametrize('kind', ['filtered', 'changed_sort'])
def test_ppn_filtered_or_changed_sort_pages_are_not_full_coverage(kind):
    pages = [page([row(), row()], 3), page([row()], 3, first=2)]
    for item in pages: item['request'].update(Filters=[], SortField='', SortOrder=1)
    if kind == 'filtered': pages[0]['request']['Filters'] = [{'field': 'TIN', 'value': 'SYNTHETIC'}]
    else: pages[1]['request']['SortField'] = 'TaxBase'
    with pytest.raises((JsonSafetyError, _UnsupportedMetadata)):
        project('A-2', pages, ['column'] * 10)
