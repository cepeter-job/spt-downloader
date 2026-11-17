"""Populated L10-A consumer contracts. Execution belongs to hosted runners."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata
from test_corporate_l10a_projection import row

KINDS = {'Country': 'COUNTRY_CODE', 'RelationshipCode': 'RELATIONSHIP_TYPE',
         'TypeOfTransaction': 'TRANSACTION_TYPE', 'PricingMethod': 'PRICING_METHOD'}


def module():
    return importlib.import_module('coretax_corporate_projection')


def labels():
    return {kind: {code: 'SYNTHETIC ' + kind + ' DESCRIPTION'}
            for kind, code in [('COUNTRY_CODE', 'IDN'), ('RELATIONSHIP_TYPE', '01'),
                               ('TRANSACTION_TYPE', '01'), ('PRICING_METHOD', '01')]}


def project(rows, **overrides):
    options = {'headers': list(module().L10A_HEADERS), 'tax_type': 'ICT_RCIT',
               'locale': 'id-ID', 'labels': labels()}
    options.update(overrides)
    return module().project_l10a_populated(rows, **options)


def original_row(**overrides):
    return row(TransactionValue=_CorporateNumber('1234'), **overrides)


def test_populated_consumer_preserves_duplicate_rows_and_expands_only_four_codes():
    source = [original_row(), original_row()]
    before = deepcopy(source)
    result = project(source)
    expected = ['SYNTHETIC RELATED PARTY', '0000000000000002',
        'SYNTHETIC COUNTRY_CODE DESCRIPTION', 'SYNTHETIC RELATIONSHIP_TYPE DESCRIPTION',
        'SYNTHETIC ACTIVITY', 'SYNTHETIC TRANSACTION_TYPE DESCRIPTION', '1.234',
        'SYNTHETIC PRICING_METHOD DESCRIPTION', 'SYNTHETIC REASON']
    assert source == before
    assert result['rows'] == [expected, expected]
    assert {tuple(e['path']) for e in result['provenance']} == {
        ('Data', i, key) for i in range(2) for key in source[i]}
    assert all(e['destination']['table'] == 'L10-A/l10a-grid' for e in result['provenance'])


@pytest.mark.parametrize('token,expected', [('0', '0'), ('-0', '0'), ('1e3', '1.000'),
    ('1234.5', '1.235'), ('-1234.5', '-1.235'), ('0.5', '1'), ('-0.5', '-1'),
    ('0.25', '0'), ('-0.25', '0'), ('999999999999999', '999.999.999.999.999')])
def test_binary_exact_number_subset_uses_zero_digit_half_away_from_zero(token, expected):
    result = project([row(TransactionValue=_CorporateNumber(token))])
    assert result['rows'][0][6] == expected
    entry, = [e for e in result['provenance'] if e['path'][-1] == 'TransactionValue']
    assert entry['type'] == 'number' and entry['value'] == token
    assert entry['rule'] == 'angular-decimal-1.0-0-id/binary-exact'


@pytest.mark.parametrize('value,expected', [(None, ''), ('1234.50', '1234.50'),
    ('-0', '-0'), ('', ''), ('SYNTHETIC LITERAL', 'SYNTHETIC LITERAL')])
def test_active_grid_caller_bypasses_the_pipe_for_null_and_non_time_strings(value, expected):
    result = project([row(TransactionValue=value)])
    assert result['rows'][0][6] == expected
    entry, = [e for e in result['provenance'] if e['path'][-1] == 'TransactionValue']
    assert entry['rule'] == 'grid-checkIsString/literal-null-or-string'


@pytest.mark.parametrize('token', ['0.1', '1234.4999999999999', '1000000000000000',
    '-1000000000000000', '1e309', '1e-9999', '999999999999999.5'])
def test_unsafe_or_non_binary_exact_numeric_inputs_are_unsupported(token):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l10a_number_precision'):
        project([row(TransactionValue=_CorporateNumber(token))])


@pytest.mark.parametrize('value', [True, {}, [], 1234, 1234.5, '12:34', '23:59 trailing'])
def test_malformed_and_time_shaped_amounts_do_not_acquire_a_number_interpretation(value):
    with pytest.raises(_UnsupportedMetadata):
        project([row(TransactionValue=value)])


@pytest.mark.parametrize('key', KINDS)
def test_null_and_unknown_codes_need_the_complete_original_catalog_but_render_blank(key):
    source = [original_row(), original_row()]
    source[0][key], source[1][key] = None, 'SYNTHETIC ABSENT CODE'
    column = module().L10A_COLUMNS.index(key)
    assert [r[column] for r in project(source)['rows']] == ['', '']
    missing = labels()
    del missing[KINDS[key]]
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l10a_catalogs'):
        project(source, labels=missing)


@pytest.mark.parametrize('change', ['missing-column', 'unknown-column', 'number-code', 'bool-text',
    'object-text', 'bad-record-id', 'extra-label-kind', 'label-is-code'])
def test_populated_row_and_catalog_shape_remain_closed(change):
    source, catalog = original_row(), labels()
    if change == 'missing-column':
        del source['Name']
    elif change == 'unknown-column':
        source['SYNTHETIC UNKNOWN'] = None
    elif change == 'number-code':
        source['Country'] = _CorporateNumber('1')
    elif change == 'bool-text':
        source['Name'] = True
    elif change == 'object-text':
        source['ReasonPricingMethod'] = {}
    elif change == 'bad-record-id':
        source['RecordId'] = _CorporateNumber('1')
    elif change == 'extra-label-kind':
        catalog['SYNTHETIC UNKNOWN'] = {}
    else:
        # A caller-supplied empty label is never a substitute for catalog custody.
        catalog['COUNTRY_CODE']['IDN'] = ''
    with pytest.raises(_UnsupportedMetadata):
        project([source], labels=catalog)


@pytest.mark.parametrize('options', [{'headers': []}, {'locale': 'en-US'}, {'tax_type': 'ICT_ROGCIT'}])
def test_populated_structure_has_no_usd_or_foreign_locale_shortcut(options):
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l10a_structure'):
        project([original_row()], **options)
