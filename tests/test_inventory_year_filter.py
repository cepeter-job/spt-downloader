"""Synthetic whole-year planning and owned-request contracts; runner-only."""
import copy
from datetime import datetime, timezone
import importlib
import importlib.util

import pytest

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def feature():
    assert importlib.util.find_spec('coretax_inventory') is not None, 'Whole-year inventory planner missing'
    return importlib.import_module('coretax_inventory')


def catalog():
    return {
        'ReferenceDataType': 'PERIOD', 'language': 'id-ID',
        'Checksum': 'synthetic-catalog-v1', 'ExpiryDate': '2026-01-02T00:00:00Z',
        'Details': [
            {'Code': '01122024', 'CodeDescription': 'Januari - Desember 2024'},
            {'Code': '02012023', 'CodeDescription': 'Februari 2023 - Januari 2024'},
            {'Code': '12112025', 'CodeDescription': 'Desember 2024 - November 2025'},
            {'Code': '01122023', 'CodeDescription': 'Januari - Desember 2023'},
            {'Code': '00002026', 'CodeDescription': 'Undetermined source period'},
        ],
    }


def condition(mode='contains', value='2024'):
    return {'PropertyName': 'TaxPeriodCode', 'Value': value, 'MatchMode': mode,
            'CaseSensitive': True, 'AsString': False}


def request():
    return {'TaxpayerAggregateIdentifier': 'synthetic-taxpayer', 'isArchieved': False,
            'First': 0, 'Rows': 50, 'Filters': [], 'LanguageId': 1,
            'SortField': '', 'SortOrder': 1}


def plan(value=None, **kwargs):
    return feature().plan_year_filters(catalog() if value is None else value,
                                       kwargs.pop('year', 2024), kwargs.pop('basis', 'period'),
                                       now=NOW, **kwargs)


def test_year_plan_keeps_raw_codes_cross_year_and_unknown_label_candidates():
    result = plan()
    assert result['eligible'] is True
    assert result['filters'] == [condition(), condition('any-equals-equals-equals',
        ['00002026', '02012023', '12112025'])]
    assert len(result['catalog_sha256']) == 64
    assert result['catalog_checksum'] == 'synthetic-catalog-v1'


def test_partitions_are_disjoint_and_never_invent_month_codes():
    original = catalog()
    original['Details'].append({'Code': 'LITERAL-CROSS-RANGE',
                                'CodeDescription': 'Oktober 2024 - September 2025'})
    result = plan(original)
    codes = result['filters'][1]['Value']
    assert all('2024' not in code for code in codes)
    assert set(codes) <= {r['Code'] for r in original['Details']}
    assert 'LITERAL-CROSS-RANGE' in codes


def test_plain_year_needs_no_empty_second_partition():
    value = catalog()
    value['Details'] = value['Details'][:1]
    assert plan(value)['filters'] == [condition()]


def test_single_cross_year_candidate_uses_scalar_equality():
    value = catalog()
    value['Details'] = value['Details'][:2]
    assert plan(value)['filters'][1] == condition('equals', '02012023')


def test_catalog_and_label_order_do_not_mutate_source():
    original = catalog()
    before = copy.deepcopy(original)
    first = plan(original)
    assert original == before
    original['Details'].reverse()
    second = plan(original)
    assert first['filters'] == second['filters']
    assert first['catalog_sha256'] != second['catalog_sha256']


@pytest.mark.parametrize('field,value', [
    ('ReferenceDataType', 'OTHER'), ('language', 'en-US'), ('Checksum', ''),
    ('ExpiryDate', '2025-12-31T23:59:59Z'), ('ExpiryDate', '2026-01-02T00:00:00'),
    ('ExpiryDate', None), ('Details', []), ('Details', None),
])
def test_unusable_catalog_preserves_explicit_unfiltered_fallback(field, value):
    source = catalog()
    source[field] = value
    result = plan(source)
    assert result['eligible'] is False
    assert result['filters'] == []
    assert result['reason']


def test_duplicate_codes_fail_catalog_eligibility_even_when_labels_agree():
    source = catalog()
    source['Details'].append(copy.deepcopy(source['Details'][0]))
    assert plan(source)['eligible'] is False


@pytest.mark.parametrize('basis', ['submission', 'unsupported'])
def test_planner_never_substitutes_submission_date_for_period_year(basis):
    result = plan(basis=basis)
    assert result['eligible'] is False and result['filters'] == []


def test_owned_request_rewrite_preserves_original_and_pagination():
    original = request()
    original['First'] = 100
    before = copy.deepcopy(original)
    filt = condition('any-equals-equals', ['01122024', '12112025'])
    rewritten = feature().rewrite_inventory_request(original, filt, taxpayer_id='synthetic-taxpayer')
    assert original == before
    assert rewritten == {**before, 'Filters': [filt]}
    rewritten['Filters'][0]['Value'].append('must-not-mutate-input')
    assert filt['Value'] == ['01122024', '12112025']


@pytest.mark.parametrize('field,value', [
    ('TaxpayerAggregateIdentifier', 'different-taxpayer'), ('isArchieved', True),
    ('First', -1), ('First', 1), ('Rows', 0), ('Rows', True),
    ('Filters', [condition('equals', '01122023')]),
])
def test_rewrite_rejects_wrong_or_pre_filtered_request(field, value):
    original = request()
    original[field] = value
    with pytest.raises(ValueError):
        feature().rewrite_inventory_request(original, condition(), taxpayer_id='synthetic-taxpayer')


def test_rewrite_rejects_unverified_operator_instead_of_loosening_scope():
    with pytest.raises(ValueError):
        feature().rewrite_inventory_request(request(), condition('any-in-equals', ['2024', '01122024']),
                                             taxpayer_id='synthetic-taxpayer')
