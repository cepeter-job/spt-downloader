"""Synthetic contracts for source-bound Unifikasi labels and submitted controls."""
from copy import deepcopy
import importlib
import importlib.util
import pytest
from coretax_json import JsonSafetyError, _UnsupportedMetadata

TYPES = ('EBUPOT_TAX_CERTIFICATE', 'EBUPOT_PAYMENT_METHOD', 'EBUPOTSP_TAX_OBJECT',
         'EBUPOTCY_TAX_OBJECT', 'PERIOD')


def feature():
    assert importlib.util.find_spec('coretax_unifikasi_json'), 'Unifikasi source bindings are not implemented'
    return importlib.import_module('coretax_unifikasi_json')


def catalogs():
    return [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
        {'Code': '01012025' if kind == 'PERIOD' else 'SYNTHETIC',
         'CodeDescription': 'Januari 2025' if kind == 'PERIOD' else 'SYNTHETIC LABEL',
         'ValidTo': None}]} for kind in TYPES]


def test_complete_catalogs_are_immutable_with_original_paths():
    payload = catalogs()
    before = deepcopy(payload)
    result = feature().project_references(payload)
    assert payload == before
    assert set(result['lookups']) == set(TYPES)
    assert result['lookups']['PERIOD'] == {'01012025': 'Januari 2025'}
    assert result['lookups']['EBUPOT_TAX_CERTIFICATE']['SYNTHETIC'] == 'SYNTHETIC LABEL'
    assert any(e['path'] == [0, 'Details', 0, 'CodeDescription']
               and e['value'] == 'SYNTHETIC LABEL' and e['type'] == 'string'
               for e in result['provenance'])


@pytest.mark.parametrize('kind', TYPES[:-1])
def test_grid_catalog_chooses_first_explicit_active_version(kind):
    payload = catalogs()
    index = TYPES.index(kind)
    payload[index]['Details'] = [
        {'Code': 'SYNTHETIC', 'CodeDescription': 'DATED', 'ValidTo': '2099-01-01'},
        {'Code': 'SYNTHETIC', 'CodeDescription': 'FIRST ACTIVE', 'ValidTo': ''},
        {'Code': 'SYNTHETIC', 'CodeDescription': 'SECOND ACTIVE', 'ValidTo': None}]
    result = feature().project_references(payload)
    assert result['lookups'][kind]['SYNTHETIC'] == 'FIRST ACTIVE'
    assert any(e['path'] == [index, 'Details', 1, 'CodeDescription'] for e in result['provenance'])


def test_single_dated_version_is_clock_independent():
    payload = catalogs()
    payload[0]['Details'][0]['ValidTo'] = '2099-01-01'
    assert feature().project_references(payload)['lookups'][TYPES[0]]['SYNTHETIC'] == 'SYNTHETIC LABEL'


@pytest.mark.parametrize('defect', ['missing-catalog', 'unknown-catalog', 'duplicate-catalog',
    'numeric-code', 'null-description', 'missing-details', 'ambiguous-dates', 'duplicate-period'])
def test_unsupported_catalogs_never_supply_guessed_labels(defect):
    payload = catalogs()
    if defect == 'missing-catalog':
        payload.pop()
    elif defect == 'unknown-catalog':
        payload[0]['ReferenceDataType'] = 'UNKNOWN'
    elif defect == 'duplicate-catalog':
        payload[-1] = deepcopy(payload[0])
    elif defect == 'numeric-code':
        payload[0]['Details'][0]['Code'] = 1
    elif defect == 'null-description':
        payload[0]['Details'][0]['CodeDescription'] = None
    elif defect == 'missing-details':
        del payload[0]['Details']
    elif defect == 'ambiguous-dates':
        payload[0]['Details'][0]['ValidTo'] = '2098-01-01'
        duplicate = deepcopy(payload[0]['Details'][0])
        duplicate['ValidTo'] = '2099-01-01'
        payload[0]['Details'].append(duplicate)
    else:
        payload[-1]['Details'].append(deepcopy(payload[-1]['Details'][0]))
    with pytest.raises(_UnsupportedMetadata):
        feature().project_references(payload)


def test_reference_locale_contradiction_is_fatal():
    payload = catalogs()
    payload[0]['language'] = 'en-US'
    with pytest.raises(JsonSafetyError):
        feature().project_references(payload)


def test_period_label_comes_from_source_catalog_not_dom():
    module = feature()
    form = {'TaxPeriodCode': '01012025'}
    lookups = module.project_references(catalogs())['lookups']
    before = deepcopy((form, lookups))
    result = module.project_field(form, {'ReturnSheetStatusCode': 'SUBMITTED'}, 'TaxPeriodCode', lookups)
    assert result['value'] == 'Januari 2025'
    assert any(e['path'] == ['TaxPeriodCode'] and e['value'] == '01012025' for e in result['provenance'])
    assert (form, lookups) == before
    with pytest.raises(_UnsupportedMetadata):
        module.project_field({'TaxPeriodCode': '02022025'}, {}, 'TaxPeriodCode', lookups)


@pytest.mark.parametrize('flag,status,expected', [(True, 'DRAFT', 'In Progress'),
    (False, 'SUBMITTED', 'Submitted'), (None, 'SUBMITTED', 'Submitted'), (False, 'DRAFT', '-')])
def test_status_uses_inner_prefill_not_conflicting_outer(flag, status, expected):
    result = feature().project_field({'SubmitInProgressStatus': flag, 'ReturnSheetStatusCode': status},
                                    {'ReturnSheetStatusCode': 'SUBMITTED'}, 'SubmitInProgressStatus', {})
    assert result['value'] == expected


def test_missing_status_flag_and_wrong_flag_type():
    module = feature()
    result = module.project_field({'ReturnSheetStatusCode': 'SUBMITTED'}, {}, 'SubmitInProgressStatus', {})
    assert result['value'] == 'Submitted'
    assert any(e['path'] == ['SubmitInProgressStatus'] and e['type'] == 'missing' for e in result['provenance'])
    with pytest.raises(_UnsupportedMetadata):
        module.project_field({'SubmitInProgressStatus': 'false'}, {}, 'SubmitInProgressStatus', {})


@pytest.mark.parametrize('control,value', [('MyCheckBox', 'true'), ('DeclarationBy', '0')])
def test_final_submitted_controls_never_read_claims(control, value):
    module = feature()
    result = module.project_field({}, {'ReturnSheetStatusCode': 'SUBMITTED'}, control, {})
    assert result['value'] == value
    assert result['container_path'] == ['Payload']
    assert result['provenance']
    with pytest.raises(_UnsupportedMetadata):
        module.project_field({}, {'ReturnSheetStatusCode': 'DRAFT'}, control, {})


def test_text_and_explicit_signer_values_preserve_strings():
    module = feature()
    assert module.project_field({'Name': 'SYNTHETIC NAME'}, {}, 'FullName', {})['value'] == 'SYNTHETIC NAME'
    for value, expected in [('SYNTHETIC SIGNATURE', 'SYNTHETIC SIGNATURE'), ('', ''), (None, '')]:
        result = module.project_field({'StatementSignature': value}, {}, 'StatementSignature', {})
        assert result['value'] == expected
        assert result['provenance'][0]['path'] == ['StatementSignature']
        assert result['provenance'][0]['value'] == value
    with pytest.raises(_UnsupportedMetadata):
        module.project_field({'StatementSignature': {'unknown': 'shape'}}, {}, 'StatementSignature', {})
    for value in ('', '0000000000000001'):
        result = module.project_field({'Signer': {'StatementTIN': value}}, {}, 'StatementTIN', {})
        assert result['value'] == value
    for form in ({}, {'Signer': {}}, {'Signer': {'StatementTIN': None}}):
        with pytest.raises(_UnsupportedMetadata):
            module.project_field(form, {}, 'StatementTIN', {})
