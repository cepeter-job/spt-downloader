"""Synthetic PPh21 grid contracts, including response-only label bindings."""
from copy import deepcopy
import importlib
import importlib.util
import json

import pytest

from coretax_json import JsonSafetyError, _UnsupportedMetadata, _corporate_json
from masa_json_fixtures import RECORD, FOREIGN, page
from support_pph21_dom import appendix_table

GRIDS = [('l1a', 'L-IA', 'LIST-IA'), ('l1b-bpa1', 'L-IB', 'BPA1'),
         ('l1b-bpa2', 'L-IB', 'BPA2'), ('l2-bpa1', 'L-II', 'BPA1'),
         ('l2-bpa2', 'L-II', 'BPA2'), ('l3-bp21', 'L-III', 'BP21'),
         ('l3-bp26', 'L-III', 'BP26')]
LOOKUPS = {'TaxCertificate': {'CERT': 'SYNTHETIC CERTIFICATE'},
           'CountryCode': {'ZZ': 'SYNTHETIC COUNTRY'}, 'Status': {'NORMAL': 'SYNTHETIC NORMAL'}}


def project(grid, pages, headers, *, lookups=LOOKUPS):
    name = 'coretax_pph21_json_bindings'
    assert importlib.util.find_spec(name) is not None
    function = getattr(importlib.import_module(name), 'project_pph21_grid', None)
    assert callable(function), 'PPh21 grid projection is not implemented'
    return function(grid, pages, headers, record_id=RECORD,
                    timezone_name='Asia/Jakarta', lookups=lookups)


def fixture(grid, form, group):
    headers = appendix_table(form, group, 0)[0]['headers']
    raw = {'No': '999', 'TIN': '0000000000000002', 'Name': 'SYNTHETIC NAME ',
           'WithholdingSlipsNumber': '000123', 'WithholdingNumber': '000123',
           'WithholdingSlipsDate': '2025-01-02T00:00:00', 'WithholdingDate': '2025-01-02T00:00:00',
           'TaxObjectCode': '00007', 'TaxObject': 'SYNTHETIC OBJECT', 'TaxArticle': 'SYNTHETIC ARTICLE',
           'GrossIncome': 1200, 'IncomeTax': -120, 'TaxRate': 2,
           'TaxCertificate': 'CERT', 'CountryCode': 'ZZ', 'PlaceOfBusinessID': '000009',
           'RevenueCode': '000005', 'Status': 'NORMAL', 'IncomePeriod': '01-12'}
    value = _corporate_json(json.dumps(raw))
    return headers, [page([deepcopy(value)], 2, first=0, size=1),
                     page([deepcopy(value)], 2, first=1, size=1)]


@pytest.mark.parametrize('grid,form,group', GRIDS)
def test_all_grids_preserve_duplicates_literal_identity_page_local_ordinals_and_source(grid, form, group):
    headers, pages = fixture(grid, form, group)
    before = deepcopy(pages)
    result = project(grid, pages, headers)
    table = result['table']
    assert table['complete'] and table['body_row_count'] == table['source_total'] == 2
    assert table['rows'][0] == table['rows'][1]  # Duplicates survive, No resets on each page.
    row = dict(zip(headers, table['rows'][0]))
    assert row['NO.'] == '1' and row['NIK/NPWP'] == '0000000000000002'
    assert row['NAMA'] == 'SYNTHETIC NAME '
    assert row['PENGHASILAN BRUTO (Rp)'] == '1.200'
    assert row['PAJAK PENGHASILAN (Rp)'] == '-120'
    assert '000123' in table['rows'][0] and '000009' in table['rows'][0]
    assert row['STATUS'] == 'SYNTHETIC NORMAL'
    if form != 'L-II':
        assert 'SYNTHETIC CERTIFICATE' in table['rows'][0]
    if form != 'L-III':
        assert 'SYNTHETIC COUNTRY' in table['rows'][0]
    if form == 'L-IA':
        assert '2,00' in table['rows'][0]
    if form == 'L-II':
        assert row['MASA PEEROLEHAN PENGHASILAN'] == '01-12'
    assert pages == before
    assert {p['sequence'] for p in result['provenance']} == {1, 2}


@pytest.mark.parametrize('grid,form,group', GRIDS[-2:])
def test_liii_date_callback_uses_source_date_prefix_before_timezone_rendering(grid, form, group):
    headers, pages = fixture(grid, form, group)
    raw = '2025-01-02T23:30:00Z'
    for item in pages:
        item['payload']['Data'][0]['WithholdingDate'] = raw
    result = project(grid, pages, headers)
    for row in result['table']['rows']:
        assert '02-01-2025' in row and '03-01-2025' not in row
    dates = [p for p in result['provenance'] if p['path'][-1] == 'WithholdingDate']
    assert len(dates) == 2 and all(p['value'] == raw for p in dates)


@pytest.mark.parametrize('lookups', [None, {}, {'Status': {'NORMAL': 'UNBOUND'}}])
def test_unbound_reference_values_are_not_guessed_from_codes_or_filter_dropdown(lookups):
    headers, pages = fixture(*GRIDS[0])
    with pytest.raises(_UnsupportedMetadata):
        project('l1a', pages, headers, lookups=lookups)


@pytest.mark.parametrize('mutation', ['foreign', 'gap', 'changed_total', 'changed_sort'])
def test_grid_identity_and_pagination_contradictions_fail_closed(mutation):
    headers, pages = fixture(*GRIDS[0])
    if mutation == 'foreign':
        pages[1]['request']['ReturnSheetRecordId'] = FOREIGN
    elif mutation == 'gap':
        pages[1]['request']['First'] = 2
    elif mutation == 'changed_total':
        pages[1]['payload']['TotalRecords'] = _corporate_json('3')
    else:
        pages[1]['request']['SortField'] = 'Name'
    with pytest.raises(JsonSafetyError):
        project('l1a', pages, headers)


def test_incomplete_grid_stays_unsupported_not_complete():
    headers, pages = fixture(*GRIDS[0])
    with pytest.raises(_UnsupportedMetadata):
        project('l1a', pages[:1], headers)


def test_reordered_or_foreign_headers_cannot_silently_relabel_json_values():
    headers, pages = fixture(*GRIDS[0])
    headers[1], headers[2] = headers[2], headers[1]
    with pytest.raises(_UnsupportedMetadata):
        project('l1a', pages, headers)
