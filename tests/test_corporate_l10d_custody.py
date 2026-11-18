"""Original-only L10-D evidence; execution belongs to hosted runners."""
from copy import deepcopy

import pytest

import coretax_corporate_l10d as l10d
from coretax_json import _CorporateNumber, _UnsupportedMetadata


CHECKS = tuple(f'{owner}Documentary{i}' for owner in ('Master', 'Local') for i in range(1, 6))
DATES = ('MasterDocumentAvailableDate', 'LocalDocumentAvailableDate')
ROOT = 'L10dFormData'


def source():
    return {ROOT: {**{key: i % 2 == 0 for i, key in enumerate(CHECKS)},
                   DATES[0]: None, DATES[1]: '2025-01-02T00:00:00+07:00'}}


def test_complete_original_root_retains_false_and_guarded_local_date_without_rendering():
    root = source()
    payload = {'TIN': '0000000000000001', 'PeriodYear': _CorporateNumber('2025')}
    before = deepcopy((root, payload))
    result = l10d.retain_originals(root, payload, sequence=7)
    assert (root, payload) == before
    assert result['kind'] == 'corporate-l10d-originals-v1'
    assert result['root'] == {'container': ['Payload', 'CurrentFormData'], 'path': [ROOT],
                              'present': True, 'type': 'object', 'keys': list(root[ROOT])}
    values = result['values']
    assert len(values) == 14
    children = [item for item in values if item['container'] == ['Payload', 'CurrentFormData']]
    assert [item['path'] for item in children] == [[ROOT, key] for key in root[ROOT]]
    for item in children:
        key = item['path'][-1]
        assert item['present'] is True and item['response_sequence'] == 7
        assert item['value'] == root[ROOT][key]
        assert item['type'] == ('boolean' if key in CHECKS else 'null' if root[ROOT][key] is None else 'string')
        assert item['rule'] == 'original-only-no-display'
    headers = [item for item in values if item['container'] == ['Payload']]
    assert [(item['path'], item['type'], item['value']) for item in headers] == [
        (['TIN'], 'string', payload['TIN']), (['PeriodYear'], 'number', '2025')]
    assert result['dependencies'] == [{'target': [ROOT, DATES[1]],
        'operands': [[ROOT, DATES[0]], [ROOT, DATES[1]]],
        'rule': 'pinned-local-date-guarded-by-master-originals-only'}]
    assert not ({'fields', 'rendered', 'calendar_value', 'complete'} & result.keys())


@pytest.mark.parametrize('key', CHECKS)
@pytest.mark.parametrize('value', [None, 0, 1, 'false', [], {}])
def test_checklist_requires_present_original_json_boolean(key, value):
    root = source()
    root[ROOT][key] = value
    with pytest.raises(_UnsupportedMetadata, match='l10d'):
        l10d.retain_originals(root, {'TIN': '0000000000000001', 'PeriodYear': _CorporateNumber('2025')}, sequence=1)


@pytest.mark.parametrize('key', (*CHECKS, *DATES))
def test_missing_leaf_is_not_null_or_false(key):
    root = source()
    del root[ROOT][key]
    with pytest.raises(_UnsupportedMetadata, match='l10d'):
        l10d.retain_originals(root, {'TIN': '0000000000000001', 'PeriodYear': _CorporateNumber('2025')}, sequence=1)


@pytest.mark.parametrize('value', [None, [], [{}], {}, {'Body': []}, {**source()[ROOT], 'Other': None}])
def test_original_root_shape_is_closed_not_a_flattened_leaf_count(value):
    with pytest.raises(_UnsupportedMetadata, match='l10d'):
        l10d.retain_originals({ROOT: value}, {'TIN': '0000000000000001', 'PeriodYear': _CorporateNumber('2025')}, sequence=1)


@pytest.mark.parametrize('key', DATES)
@pytest.mark.parametrize('value', [False, 0, _CorporateNumber('2025'), [], {}, '', 'not-a-date',
                                  '2025-02-30', '1969-01-01', '2101-01-01',
                                  '2025-01-02T12:00:00+03:00'])
def test_unreviewed_date_source_shape_is_not_coerced(key, value):
    root = source()
    root[ROOT][key] = value
    with pytest.raises(_UnsupportedMetadata, match='l10d'):
        l10d.retain_originals(root, {'TIN': '0000000000000001', 'PeriodYear': _CorporateNumber('2025')}, sequence=1)


@pytest.mark.parametrize('master', [None, '2025-01-02', '2025-01-02T00:00:00.000Z'])
@pytest.mark.parametrize('local', [None, '2025-01-03', '2025-01-03T00:00:00+07:00'])
def test_both_date_operands_remain_literal_even_when_master_guard_is_false(master, local):
    root = source()
    root[ROOT].update(zip(DATES, (master, local)))
    result = l10d.retain_originals(root, {'TIN': '0000000000000001', 'PeriodYear': _CorporateNumber('2025')}, sequence=1)
    assert [item['value'] for item in result['values'] if item['path'][-1] in DATES] == [master, local]
