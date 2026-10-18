"""Reference response labels are locale/type/code bound, never filter options."""
from copy import deepcopy
import importlib
import json

import pytest

from coretax_json import JsonSafetyError, _UnsupportedMetadata, _corporate_json

TYPES = ('EBUPOT_TAX_CERTIFICATE', 'COUNTRY_CODE', 'EBUPOT_STATUS')
FIELDS = ('TaxCertificate', 'CountryCode', 'Status')


def project(payload, *, types=TYPES, locale='id-ID'):
    module = importlib.import_module('coretax_pph21_json_bindings')
    function = getattr(module, 'project_pph21_references', None)
    assert callable(function), 'PPh21 reference projection is not implemented'
    return function(payload, requested_types=types, locale=locale)


def source():
    return _corporate_json(json.dumps([
        {'ReferenceDataType': kind, 'language': 'id-ID',
         'Details': [{'Code': '0001', 'CodeDescription': 'SYNTHETIC ' + field,
                      'ValidTo': None, 'ParameterData': '{}'}]}
        for kind, field in zip(TYPES, FIELDS)]))


def test_exact_reference_types_and_literal_codes_preserve_source_and_label_provenance():
    payload = source()
    before = deepcopy(payload)
    result = project(payload)
    assert result['lookups'] == {field: {'0001': 'SYNTHETIC ' + field} for field in FIELDS}
    paths = [p['path'] for p in result['provenance']]
    for index in range(3):
        assert [index, 'Details', 0, 'Code'] in paths
        assert [index, 'Details', 0, 'CodeDescription'] in paths
    assert payload == before


def test_open_ended_version_wins_over_first_historical_record_without_calendar_guessing():
    payload = source()
    payload[0]['Details'].insert(0, {'Code': '0001', 'CodeDescription': 'OLD SYNTHETIC LABEL',
                                   'ValidFrom': '2020-01-01', 'ValidTo': '2021-01-01'})
    result = project(payload)
    assert result['lookups']['TaxCertificate']['0001'] == 'SYNTHETIC TaxCertificate'
    assert [0, 'Details', 1, 'CodeDescription'] in [p['path'] for p in result['provenance']]


def test_time_dependent_duplicate_versions_without_open_end_are_unsupported():
    payload = source()
    payload[0]['Details'] = [
        {'Code': '0001', 'CodeDescription': 'A', 'ValidTo': '2029-01-01'},
        {'Code': '0001', 'CodeDescription': 'B', 'ValidTo': '2030-01-01'},
    ]
    with pytest.raises(_UnsupportedMetadata):
        project(payload)


def test_response_locale_contradiction_is_not_a_fallback_label():
    payload = source()
    payload[0]['language'] = 'en-US'
    with pytest.raises(JsonSafetyError):
        project(payload)


@pytest.mark.parametrize('mutation', ['missing_catalog', 'duplicate_catalog', 'wrong_catalog', 'numeric_code', 'nontext_label'])
def test_incomplete_or_ambiguous_reference_source_is_not_accepted(mutation):
    payload = source()
    if mutation == 'missing_catalog':
        payload.pop()
    elif mutation == 'duplicate_catalog':
        payload.append(deepcopy(payload[0]))
    elif mutation == 'wrong_catalog':
        payload[0]['ReferenceDataType'] = 'FILTER_ONLY_CATALOG'
    elif mutation == 'numeric_code':
        payload[0]['Details'][0]['Code'] = _corporate_json('1')
    else:
        payload[0]['Details'][0]['CodeDescription'] = True
    with pytest.raises(_UnsupportedMetadata):
        project(payload)


@pytest.mark.parametrize('kwargs', [{'types': ('COUNTRY_CODE',)}, {'locale': 'unknown'}])
def test_unbound_request_types_or_locale_do_not_grant_reference_eligibility(kwargs):
    with pytest.raises(_UnsupportedMetadata):
        project(source(), **kwargs)
