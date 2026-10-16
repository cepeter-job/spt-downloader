"""Public component column contracts; synthetic data for all Unifikasi grids."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata, JsonSafetyError
from test_masa_json_grids import page, RECORD

COLUMNS = {
    'list-i-bpu': ['TaxIdentificationNumber', 'TaxpayerName', 'WithholdingSlipsNumber',
        'WithholdingSlipsDate', 'TaxArticle', 'TaxObjectCode', 'TaxObject', 'TaxBase',
        'TaxRate', 'IncomeTax', 'TaxCertificate', 'PaymentMethod', 'BranchId', 'Status', 'RevenueCode'],
    'list-i-bpnr': ['TaxIdentificationNumber', 'TaxpayerName', 'WithholdingSlipsNumber',
        'WithholdingSlipsDate', 'TaxArticle', 'TaxObjectCode', 'TaxObject', 'TaxBase',
        'TaxRate', 'IncomeTax', 'TaxCertificate', 'PaymentMethod', 'BranchId', 'Status', 'RevenueCode'],
    'list-ii-sp': ['TaxArticle', 'TaxObjectCode', 'TaxObject', 'TaxBase', 'TaxRate',
        'IncomeTax', 'TaxCertificate', 'BranchId', 'Status', 'RevenueCode'],
    'list-ii-cy': ['TaxArticle', 'TaxObjectCode', 'TaxObject', 'TaxBase', 'TaxRate',
        'IncomeTax', 'TaxCertificate', 'BranchId', 'Status', 'RevenueCode'],
    'attachment-i': ['RecipientIdentificationNumber', 'RecipientName', 'RecipientAccountId',
        'GiverIdentificationNumber', 'GiverName', 'GiverAccountId', 'TaxObjectCode',
        'BillingDocumentNumber', 'BillingDocumentDate', 'TaxBase', 'TaxRate', 'IncomeTax',
        'TaxCertificate', 'BranchId', 'Status', 'RevenueCode'],
}


def row(grid):
    result = {field: 'SYNTHETIC-' + field for field in COLUMNS[grid]}
    for field in ('WithholdingSlipsDate', 'BillingDocumentDate'):
        if field in result: result[field] = '2025-01-02T00:00:00'
    result.update(TaxBase=_corporate_json('1000'), TaxRate=_corporate_json('2.5'),
                  IncomeTax=_corporate_json('25'), TaxCertificate=None)
    if 'PaymentMethod' in result: result['PaymentMethod'] = None
    if grid in ('list-ii-sp', 'list-ii-cy'): result['TaxObject'] = None
    return result


def project(grid, pages, lookups=None):
    impl = getattr(importlib.import_module('coretax_masa_bindings'), 'project_unifikasi_grid', None)
    assert callable(impl), 'Unifikasi grid projection is not implemented'
    return impl(grid, pages, ['NO.'] + COLUMNS[grid], record_id=RECORD,
                timezone_name='Asia/Jakarta', lookups=lookups or {})


@pytest.mark.parametrize('grid', list(COLUMNS))
def test_each_unifikasi_grid_uses_observed_column_order_and_precision(grid):
    source = row(grid); before = deepcopy(source)
    result = project(grid, [page([source], 1)])
    values = result['table']['rows'][0]
    assert values[0] == '1.'
    assert values[1 + COLUMNS[grid].index('TaxBase')] == '1.000'
    assert values[1 + COLUMNS[grid].index('TaxRate')] == '2,50'
    assert values[1 + COLUMNS[grid].index('IncomeTax')] == '25'
    assert values[1 + COLUMNS[grid].index('TaxCertificate')] == ''
    assert len(values) == len(COLUMNS[grid]) + 1
    assert result['table']['complete'] is True and source == before


@pytest.mark.parametrize('grid', list(COLUMNS))
def test_empty_unifikasi_grids_keep_verified_zero_totals(grid):
    result = project(grid, [page([], 0)])
    assert result['table']['rows'] == [] and result['table']['source_total'] == 0


def test_unifikasi_ordinals_are_global_with_a_dot_unlike_ppn_page_local_numbers():
    source = row('list-i-bpu')
    result = project('list-i-bpu', [page([source, deepcopy(source)], 3),
                                  page([deepcopy(source)], 3, first=2)])
    assert [r[0] for r in result['table']['rows']] == ['1.', '2.', '3.']
    assert result['table']['rows'][0][1:] == result['table']['rows'][2][1:]


@pytest.mark.parametrize('grid,field', [('list-i-bpu', 'TaxCertificate'), ('list-i-bpnr', 'PaymentMethod'),
                                       ('list-ii-sp', 'TaxObject'), ('list-ii-cy', 'TaxObject')])
def test_nonempty_reference_codes_require_bound_display_labels(grid, field):
    source = row(grid); source[field] = 'SYNTHETIC-CODE'
    with pytest.raises(_UnsupportedMetadata):
        project(grid, [page([source], 1)])
    # The caller must bind reference evidence independently before projection.
    lookup = {field: {'SYNTHETIC-CODE': 'SYNTHETIC LABEL'}}
    result = project(grid, [page([source], 1)], lookup)
    assert result['table']['rows'][0][1+COLUMNS[grid].index(field)] == 'SYNTHETIC LABEL'
    assert any(p.get('lookup') == field and p['value'] == 'SYNTHETIC-CODE' for p in result['provenance'])


@pytest.mark.parametrize('kind', ['filtered', 'changed_sort', 'foreign_record'])
def test_unifikasi_coverage_cannot_claim_filtered_or_mixed_scope(kind):
    pages = [page([row('list-i-bpu'), row('list-i-bpu')], 3), page([row('list-i-bpu')], 3, first=2)]
    for item in pages: item['request'].update(Filters=[], SortField='', SortOrder=1)
    if kind == 'filtered': pages[0]['request']['Filters'] = [{'field': 'TaxArticle', 'value': 'SYNTHETIC'}]
    elif kind == 'changed_sort': pages[1]['request']['SortField'] = 'TaxBase'
    else: pages[1]['request']['ReturnSheetRecordId'] = 'OTHER'
    with pytest.raises((JsonSafetyError, _UnsupportedMetadata)):
        project('list-i-bpu', pages)
