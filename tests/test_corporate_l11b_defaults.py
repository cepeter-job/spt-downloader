"""Ordinary submitted manual L11-B null hydration; Actions-only execution."""
from copy import deepcopy

import pytest

from coretax_json import _CorporateNumber as Number, _UnsupportedMetadata
from coretax_masa_bindings import _evidence
from test_corporate_l11b_hydrated import populated, project, bindings, packet, adapt
from test_corporate_l11b_projection import project as restricted
import support_json_corpus as corpus


@pytest.mark.parametrize('key,expected,quarter', [
    ('CommercialNettIncome', ['0', '200.000', '50.000', '400.000', '250.000', '62.500'], '62500'),
    ('DepreciationAndAmortizationExpenses', ['1.000.000', '0', '50.000', '400.000', '1.050.000', '262.500'], '262500'),
    ('IncomeTaxExpense', ['1.000.000', '200.000', '0', '400.000', '1.200.000', '300.000'], '300000'),
    ('BorrowingCostExpense', ['1.000.000', '200.000', '50.000', '0', '1.250.000', '312.500'], '312500'),
])
def test_submitted_manual_hydration_defaults_only_explicit_null_scalars(key, expected, quarter):
    value = populated(**{key: None, 'Ebitda25': Number(quarter)})
    before = deepcopy(value)
    result = project(value, part_ii=key != 'BorrowingCostExpense')
    assert [f['value'] for f in result['fields']] == expected
    assert value == before
    entry, = [e for e in result['provenance'] if e.get('destination') == {'form': 'L11-B', 'field': key}]
    assert entry['type'] == 'null' and entry['value'] is None
    assert entry['path'] == ['L11BFormData', key] and entry['rule'] == 'submitted-null-default-zero'
    with pytest.raises(_UnsupportedMetadata):
        restricted(value)


def default_source():
    return populated(**{name: None for name in ('CommercialNettIncome',
        'DepreciationAndAmortizationExpenses', 'IncomeTaxExpense', 'BorrowingCostExpense', 'Ebitda25')})


def default_packet():
    source = packet(default_source())
    envelope = source['payload']
    envelope['Payload']['IsMigrated'] = False
    # Keep the original wire body authoritative, not the convenience payload.
    replacement = corpus.packet(envelope)
    replacement['context'].update({k: v for k, v in source['context'].items()
                                   if k not in ('bytes', 'sha256')})
    return replacement


def test_all_null_manual_scalars_and_quarter_retain_typed_original_zero_defaults():
    value = default_source()
    result = project(value)
    assert [f['value'] for f in result['fields']] == ['0'] * 6
    assert len(result['tables']) == 3 and result['der_operands'] == [2000, 800]
    source = default_packet()
    result = adapt(forms=bindings(), packet=source)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    values = next(p['values'] for p in result['provenance']['projections'] if p['form'] == 'L11-B')
    assert any(e['path'] == ['IsMigrated'] and e['type'] == 'boolean' and e['value'] is False
               and e['container'] == ['Payload'] for e in values)
    assert any(e['path'] == ['L11BFormData', 'Ebitda25'] and e['type'] == 'null'
               and e['value'] is None and e['rule'] == 'reconciled-quarter-null-default'
               for e in values)


@pytest.mark.parametrize('key,value', [('IsMigrated', True), ('IsMigrated', None),
                                     ('LastSubmittedFormData', '{}'), ('IsMigrated', 'false')])
def test_null_defaults_do_not_authorize_other_parent_profiles(key, value):
    source = default_packet()
    source['payload']['Payload'][key] = value
    replacement = corpus.packet(source['payload'])
    replacement['context'].update({k: v for k, v in source['context'].items()
                                   if k not in ('bytes', 'sha256')})
    result = adapt(forms=bindings(), packet=replacement)
    assert not result['eligible']


@pytest.mark.parametrize('manual', [False, None, Number('0'), '1'])
def test_null_defaults_never_grant_parent_auto_overwrite_permission(manual):
    with pytest.raises(_UnsupportedMetadata, match='manual_lifecycle'):
        project(default_source() | {'IsEbitdaManuallyEdited': manual})


def test_default_quarter_must_still_reconcile_and_missing_scalar_is_not_null():
    with pytest.raises(_UnsupportedMetadata, match='quarter_hydration'):
        project(populated(Ebitda25=None))
    source = default_source()
    del source['IncomeTaxExpense']
    with pytest.raises(_UnsupportedMetadata, match='source_shape'):
        project(source)


@pytest.mark.parametrize('value', [False, True])
def test_shared_evidence_preserves_literal_boolean_without_coercion(value):
    # PR #278 used a narrow typed-provenance literal; PR #287 centralizes it.
    assert _evidence(value, ['IsMigrated']) == {
        'path': ['IsMigrated'], 'type': 'boolean', 'value': value}


@pytest.mark.parametrize('value', [0, 1, 0.0, [], {}])
def test_shared_evidence_rejects_untyped_or_non_json_scalar_coercion(value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_masa_projected_scalar'):
        _evidence(value, ['IsMigrated'])


@pytest.mark.parametrize('key', [
    'CommercialNettIncome', 'DepreciationAndAmortizationExpenses',
    'IncomeTaxExpense', 'BorrowingCostExpense', 'Ebitda25',
])
def test_l11b_numeric_operands_still_reject_boolean_when_evidence_supports_it(key):
    # Typed provenance is not permission for a boolean to become 0 or 1.
    with pytest.raises(_UnsupportedMetadata):
        project(populated(**{key: True}))
