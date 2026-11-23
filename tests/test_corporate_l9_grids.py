"""Populated L9 detail projections; runtime execution belongs to hosted CI."""
from copy import deepcopy

import pytest

import coretax_corporate_projection as projection
from coretax_json import _CorporateNumber as Number

HEADERS = ['KODE HARTA', 'KELOMPOK/JENIS HARTA', 'BULAN/TAHUN PEROLEHAN',
    'BIAYA PEROLEHAN (Rp)', 'NILAI SISA BUKU FISKAL PADA AWAL TAHUN (Rp)',
    'METODE PENYUSUTAN/AMORTISASI / KOMERSIAL', 'METODE PENYUSUTAN/AMORTISASI / FISKAL',
    'PENYUSUTAN/AMORTISASI FISKAL TAHUN INI (Rp)', 'KETERANGAN']
LABELS = {'TANGIBLE_ASSET': {'SYNTHETIC-001': 'Synthetic tangible label'},
    'GROUP_OF_BUILDINGS': {'SYNTHETIC-001': 'Synthetic building label'},
    'INTANGIBLE_ASSET': {'SYNTHETIC-001': 'Synthetic intangible label'},
    'COMMERCIAL_METHOD': {'SYNTHETIC-C': 'Synthetic commercial label'},
    'FISCAL_METHOD': {'SYNTHETIC-F': 'Synthetic fiscal label'}}


def asset(index=0, **changes):
    row = {'GroupAssetType': 'SYNTHETIC-001',
        'MonthYearAcquisition': '2024-02-01T00:00:00+07:00',
        'AcquisitionPrice': Number('1234.5'), 'RemainingBeginningValue': Number('987.25'),
        'MethodCommercial': 'SYNTHETIC-C', 'MethodFiscal': 'SYNTHETIC-F',
        'FiscalYearValue': Number('25.5'), 'Notes': 'SYNTHETIC literal note',
        'GroupType': projection.L9_GRIDS[index][0].rsplit('/', 1)[1],
        'CodeOfAsset': None, 'RecordId': '11111111-1111-4111-8111-111111111111',
        'Index': Number('0'), 'Action': None}
    row.update(changes)
    return row


def pages(index=0, rows=None):
    data = [asset(index), asset(index)] if rows is None else rows
    return [{'offset': 0, 'rows': 10, 'payload': {'Data': data,
        'TotalRecords': Number(str(len(data))), 'Index': None}}]


def project(index=0, **changes):
    helper = getattr(projection, 'project_l9_grid', None)
    assert callable(helper), 'Missing source-proven populated L9 grid projector'
    source_index = index if type(index) is int and 0 <= index < 12 else 0
    options = {'index': index, 'pages': pages(source_index), 'total': Number('51'),
        'headers': HEADERS, 'footer_spans': [[7, 1, 1]],
        'tax_type': 'ICT_RCIT', 'locale': 'id-ID', 'timezone_name': 'Asia/Jakarta',
        'labels': deepcopy(LABELS)}
    options.update(changes)
    return helper(**options)


@pytest.mark.parametrize('index', range(5))
def test_tangible_group1_populated_rows_keep_duplicates_and_original_coordinates(index):
    original = pages(index)
    before = deepcopy(original)
    result = project(index, pages=original)
    table = result['table']
    expected = ['SYNTHETIC-001', 'Synthetic tangible label', '02-2024', '1.235', '987',
        'Synthetic commercial label', 'Synthetic fiscal label', '26', 'SYNTHETIC literal note']
    assert table['headers'] == HEADERS
    assert table['rows'] == [expected, expected, ['TOTAL', '51', '']]
    assert table['footer'] == [['TOTAL', '51', '']]
    assert table['footer_spans'] == [[7, 1, 1]]
    assert table['body_row_count'] == table['source_total'] == 2
    assert table['source_structure'] == {'form': 'L9', 'component': 'rshshr-citr-l9-form-grid1',
        'groups': ['HARTA BERWUJUD', 'KELOMPOK ' + str(index + 1) if index < 4 else 'KELOMPOK LAINNYA']}
    # GroupAssetType drives two different representations, not CodeOfAsset.
    entries = [v for v in result['provenance'] if v['path'] == ['Data', 0, 'GroupAssetType']]
    assert {v['destination']['column'] for v in entries} == {0, 1}
    assert {v['rule'] for v in entries} == {'literal-grid-text', 'bound-reference-label'}
    assert all(v['page_index'] == 0 for v in result['provenance'] if v['source'] == 'grid')
    for row_index in (0, 1):
        retained = [v for v in result['provenance'] if v['source'] == 'grid'
                    and v['path'][:2] == ['Data', row_index]]
        assert {v['path'][-1] for v in retained} == set(asset())
    assert original == before


@pytest.mark.parametrize('index', [5, 6])
def test_both_building_groups_use_building_catalog_and_approved_owner(index):
    result = project(index)
    assert result['table']['rows'][0][1] == 'Synthetic building label'
    assert result['table']['source_structure'] == {'form': 'L9',
        'component': 'rshshr-citr-l9-form-grid2',
        'groups': ['BANGUNAN', 'PERMANEN' if index == 5 else 'TIDAK PERMANEN']}
    assert result['provenance'][-1]['path'] == [projection.L9_ROOT, 'TotalTable' + str(index + 1)]


@pytest.mark.parametrize('index', range(7, 12))
def test_all_intangible_groups_use_intangible_catalog_not_tangible_alias(index):
    result = project(index)
    assert result['table']['rows'][0][1] == 'Synthetic intangible label'
    assert result['table']['source_structure'] == {'form': 'L9',
        'component': 'rshshr-citr-l9-form-grid3', 'groups': ['HARTA TIDAK BERWUJUD',
            'KELOMPOK ' + str(index - 6) if index < 11 else 'KELOMPOK LAINNYA']}
    assert result['provenance'][-1]['path'] == [projection.L9_ROOT, 'TotalTable' + str(index + 1)]
