"""Unifikasi text controls must use response fields, never session identities."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata


def project(form, control):
    implementation = getattr(importlib.import_module('coretax_masa_bindings'), 'project_unifikasi_text', None)
    assert callable(implementation), 'Unifikasi text projection is not implemented'
    return implementation(form, control)


@pytest.mark.parametrize('control,key', [
    ('TaxIdentificationNumber', 'TaxIdentificationNumber'), ('FullName', 'Name'),
    ('Address', 'Address'), ('PhoneNumber', 'PhoneNumber'),
])
def test_direct_text_preserves_literal_value_without_alias_guessing(control, key):
    form = {control: 'DECOY', key: ' 0000123 / SYNTHETIC\nLINE '}
    before = deepcopy(form)
    result = project(form, control)
    assert result['value'] == ' 0000123 / SYNTHETIC\nLINE '
    assert result['provenance'] == [{'path': [key], 'type': 'string', 'value': form[key]}]
    assert form == before


@pytest.mark.parametrize('shape', ['null','missing'])
def test_optional_text_blanks_keep_null_distinct_from_missing(shape):
    result = project({'Address': None} if shape == 'null' else {}, 'Address')
    assert result['value'] == ''
    assert result['provenance'] == [{'path': ['Address'], 'type': shape, 'value': None}]


@pytest.mark.parametrize('control', ['StatementTIN', 'StatementFullName'])
@pytest.mark.parametrize('text', ['0000123456', 'SYNTHETIC SIGNER', ''])
def test_signer_text_comes_only_from_nested_response_signer_including_explicit_empty(control, text):
    form = {'Signer': {control: text}, control: 'TOP-LEVEL DECOY',
            'RepresentativeTin': 'CLAIM DECOY', 'RepresentativeUsername': 'CLAIM DECOY'}
    before = deepcopy(form)
    result = project(form, control)
    assert result['value'] == text
    assert result['provenance'] == [{'path': ['Signer', control], 'type': 'string', 'value': text}]
    assert form == before


@pytest.mark.parametrize('control', ['StatementTIN', 'StatementFullName'])
@pytest.mark.parametrize('shape', ['missing_parent', 'null_parent', 'missing_leaf', 'null_leaf'])
def test_missing_signer_cannot_be_replaced_by_authenticated_representative_or_taxpayer_name(control, shape):
    form = {'Name': 'TAXPAYER DECOY', 'RepresentativeTin': 'CLAIM DECOY',
            'RepresentativeUsername': 'CLAIM DECOY', control: 'TOP-LEVEL DECOY'}
    if shape != 'missing_parent':
        form['Signer'] = None if shape == 'null_parent' else ({control: None} if shape == 'null_leaf' else {})
    with pytest.raises(_UnsupportedMetadata):
        project(form, control)


@pytest.mark.parametrize('control', ['DeclarationBy','StatementSignature','TaxPeriodCode','SubmitInProgressStatus','UnknownAlias'])
def test_nontext_or_context_dependent_controls_require_separate_verified_bindings(control):
    with pytest.raises(_UnsupportedMetadata):
        project({control: 'SYNTHETIC'}, control)


@pytest.mark.parametrize('raw', ['true', '0', '[]', '{}'])
def test_text_binding_rejects_nonstrings_instead_of_corrupting_identifiers(raw):
    with pytest.raises(_UnsupportedMetadata):
        project({'TaxIdentificationNumber': _corporate_json(raw)}, 'TaxIdentificationNumber')
