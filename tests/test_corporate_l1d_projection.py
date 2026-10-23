"""Synthetic source-only L1-D contracts; execution belongs to GitHub runners."""
from copy import deepcopy
import importlib
import json

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata

TREE_FIELDS = ('Amount', 'NonTaxableObject', 'SubjectToFinalTax', 'NonFinal',
               'PositiveFiscalCorrection', 'NegativeFiscalCorrection', 'FinalAmount')
ORDER = ['Pendapatan:', '4021', '4013', '5020', '4300', '4199', 'Beban Usaha',
    *[str(code) for code in range(5311, 5323)], '5399', '5400', '4500',
    'Pendapatan Non Usaha', '4501', '4503', '4511', '4599', '4600',
    'Beban Non Usaha', '5405', '5409', '5421', '5499', '5500', '4700']
CODES = [value for value in ORDER if value.isdecimal()]
ASSETS = ['1101', '1122', '1123', '1124', '1125', '1131', '1181', '1200', '1401',
    '1421', '1422', '1423', '1499', '1501', '1521', '1522', '1551', '1599',
    '1600', '1601', '1611', '1651', '1658', '1698']
ASSET_CALC = ['1101', '1122', '1123', '1124', '1125', '-1131', '1181', '1200', '1401',
    '1421', '1423', '1422', '1499', '1501', '1521', '-1522', '1551', '1599',
    '1600', '-1601', '1611', '1651', '-1658', '1698']
DEBTS = ['2102', '2103', '2111', '2186', '2187', '2191', '2192', '2195', '2201',
    '2202', '2203', '2228', '2301', '2303', '2304', '2312', '2321', '2322', '2998']
DEBT_CALC = DEBTS[:16] + ['2322', '2321', '2998']
EQUITY = ['3102', '3120', '3200', '3297', '3298']
HEADERS = [['KODE AKUN', 'NAMA AKUN', 'NILAI KOMERSIAL', 'TIDAK TERMASUK OBJEK PAJAK',
    'DIKENAKAN PPh BERSIFAT FINAL', 'OBJEK PAJAK TIDAK FINAL',
    'PENYESUAIAN FISKAL POSITIF', 'PENYESUAIAN FISKAL NEGATIF',
    'KODE PENYESUAIAN FISKAL', 'NILAI FISKAL'],
    ['KODE AKUN', 'NAMA AKUN', 'NILAI'], ['KODE AKUN', 'NAMA AKUN', 'NILAI']]
SPANS = [[[1] * 10], [[1, 1, 1]], [[1, 1, 1]]]


def source():
    rows = []
    for code in CODES:
        data = {'AccountCode': code, 'Description': 'SYNTHETIC ' + code,
                'CorrectionCode': ['0001', '0001'], 'BlockFields': {}}
        data.update({field: 0 for field in TREE_FIELDS})
        rows.append({'Data': data, 'Expanded': True, 'Children': []})
    assets = {'AC' + code: 0 for code in [*ASSETS, '1700']}
    debts = {'AC' + code: 0 for code in [*DEBTS, *EQUITY, '2999', '3299', '3300']}
    return {'L1dTreeData': rows, 'L1dAssets': assets, 'L1dLiabilitiesAndEquity': debts,
            'L1dTreeTotalRow': {field: 0 for field in TREE_FIELDS}}


def project(raw=None, *, migrated=False, headers=None, spans=None):
    helper = getattr(importlib.import_module('coretax_corporate_projection'), 'project_l1d', None)
    assert callable(helper), 'Source-bound L1-D projector is absent'
    return helper(_corporate_json(json.dumps(source() if raw is None else raw)),
        migrated=migrated, headers=deepcopy(HEADERS if headers is None else headers),
        footer_spans=deepcopy(SPANS if spans is None else spans),
        tax_type='ICT_RCIT', locale='id-ID', timezone_name='Asia/Jakarta')


def tree_row(raw, code):
    return next(row['Data'] for row in raw['L1dTreeData'] if row['Data']['AccountCode'] == code)


def test_flatten_order_uses_unique_codes_not_source_order_and_keeps_5322():
    raw = source()
    raw['L1dTreeData'].reverse()
    before = deepcopy(raw)
    result = project(raw)
    table, assets, debts = result['tables']
    assert raw == before
    actual = [row[0] if row[0] else row[1] for row in table['rows'][:table['body_row_count']]]
    assert actual == ORDER
    assert table['body_row_count'] == 35 and table['source_total'] == 35
    assert table['footer_spans'] == SPANS[0]
    assert table['footer'] == [['4800', 'Laba (Rugi) Sebelum Pajak', *(['0'] * 6), '', '0']]
    for index, item in enumerate((table, assets, debts), 1):
        assert item['source_structure'] == {'form': 'L1-D', 'component': f'rsh-citr-l1d-grid{index}',
            'groups': ['A. LAPORAN LABA RUGI' if index == 1 else 'B. LAPORAN POSISI KEUANGAN']}
    assert any(entry['path'][-1] == 'AccountCode' and entry['value'] == '5322'
               for entry in result['provenance'])


@pytest.mark.parametrize('defect', ['missing-5322', 'duplicate-code', 'bad-children', 'empty-tree'])
def test_ambiguous_or_default_tree_does_not_get_an_invented_body(defect):
    raw = source()
    if defect == 'missing-5322':
        raw['L1dTreeData'] = [r for r in raw['L1dTreeData'] if r['Data']['AccountCode'] != '5322']
    elif defect == 'duplicate-code':
        raw['L1dTreeData'].append(deepcopy(raw['L1dTreeData'][0]))
    elif defect == 'bad-children':
        raw['L1dTreeData'][0]['Children'] = {}
    else:
        raw['L1dTreeData'] = []
    with pytest.raises(_UnsupportedMetadata):
        project(raw)


def test_four_masks_match_consumer_while_correction_codes_keep_order_and_duplicates():
    raw = source()
    for code in ('4021', '4013', '4300'):
        tree_row(raw, code).update({field: 7 for field in TREE_FIELDS})
    tree_row(raw, '4021')['BlockFields'] = {'NonTaxableObject': True, 'CorrectionCode': True}
    result = project(raw)
    rows = {row[0]: row for row in result['tables'][0]['rows']}
    assert rows['4021'][2:] == ['7', '', '7', '7', '7', '7', '0001; 0001', '7']
    assert rows['4013'][2:] == ['7', '', '', '7', '7', '7', '0001; 0001', '7']
    assert rows['4300'][2:] == ['7', '', '', '7', '', '', '0001; 0001', '7']


@pytest.mark.parametrize('migrated', [False, True])
def test_tree_footer_has_seven_captured_totals_and_separate_migration_rule(migrated):
    raw = source()
    for field in TREE_FIELDS:
        tree_row(raw, '4500')[field] = 4
        tree_row(raw, '4700')[field] = 9
        raw['L1dTreeTotalRow'][field] = 101 if migrated else 13
    result = project(raw, migrated=migrated)
    footer = result['tables'][0]['footer'][0]
    assert [footer[i] for i in (2, 3, 4, 5, 6, 7, 9)] == ['101' if migrated else '13'] * 7
    assert sum(entry['path'][:2] == ['L1dFormData', 'L1dTreeTotalRow']
               for entry in result['provenance']) == 7


@pytest.mark.parametrize('field', TREE_FIELDS)
def test_nonmigrated_reported_tree_total_must_reconcile(field):
    raw = source()
    raw['L1dTreeTotalRow'][field] = 1
    with pytest.raises(_UnsupportedMetadata):
        project(raw)


def test_balance_sheet_totals_keep_captured_values_after_exact_signed_reconciliation():
    raw = source()
    assets = raw['L1dAssets']
    for number, code in enumerate(ASSETS, 1):
        assets['AC' + code] = number
    assets['AC1700'] = sum((-1 if c.startswith('-') else 1) * assets['AC' + c.lstrip('-')]
                          for c in ASSET_CALC)
    debts = raw['L1dLiabilitiesAndEquity']
    for number, code in enumerate([*DEBTS, *EQUITY], 1):
        debts['AC' + code] = number
    debts['AC2999'] = sum(debts['AC' + code] for code in DEBT_CALC)
    debts['AC3299'] = sum(debts['AC' + code] for code in EQUITY)
    debts['AC3300'] = debts['AC2999'] + debts['AC3299']
    result = project(raw)
    assert result['tables'][1]['footer'][0] == ['1700', 'Jumlah Aset', str(assets['AC1700'])]
    assert result['tables'][2]['footer'][0] == ['3300', 'Jumlah Liabilitas dan Ekuitas', str(debts['AC3300'])]
    for field in ('AC1700', 'AC2999', 'AC3299', 'AC3300'):
        assert any(entry['path'][-1] == field for entry in result['provenance'])


@pytest.mark.parametrize('container,field', [('L1dAssets', 'AC1700'),
    ('L1dLiabilitiesAndEquity', 'AC2999'), ('L1dLiabilitiesAndEquity', 'AC3299'),
    ('L1dLiabilitiesAndEquity', 'AC3300')])
def test_missing_or_mismatched_reported_balance_sheet_total_is_unsupported(container, field):
    raw = source()
    raw[container][field] = 1
    with pytest.raises(_UnsupportedMetadata):
        project(raw)
    del raw[container][field]
    with pytest.raises(_UnsupportedMetadata):
        project(raw)


@pytest.mark.parametrize('value', [True, '7', 1.5, 1000000000000000])
def test_unsupported_arithmetic_types_never_become_tax_values(value):
    raw = source()
    raw['L1dAssets']['AC1101'] = value
    with pytest.raises(_UnsupportedMetadata):
        project(raw)


def test_ordered_asset_overflow_is_not_hidden_by_a_safe_final_total():
    raw = source()
    raw['L1dAssets'].update(AC1101=999999999999999, AC1122=1, AC1131=1,
                          AC1700=999999999999999)
    with pytest.raises(_UnsupportedMetadata):
        project(raw)


@pytest.mark.parametrize('migrated', [None, 0, 'false'])
def test_migration_flag_is_never_inferred(migrated):
    with pytest.raises(_UnsupportedMetadata):
        project(migrated=migrated)
