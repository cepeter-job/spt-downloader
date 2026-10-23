"""Naturally observed corporate country catalogs; synthetic, runner-only."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import JsonSafetyError, _UnsupportedMetadata
from test_corporate_l11c_native import catalog


def project(payload=None, **options):
    helper = getattr(importlib.import_module('coretax_corporate_projection'), 'project_countries', None)
    assert callable(helper), 'Missing source-bound corporate country catalog projection'
    return helper(catalog() if payload is None else payload, **options)


def test_country_catalog_keeps_case_sensitive_literal_codes_labels_and_paths():
    raw = catalog()
    before = deepcopy(raw)
    result = project(raw)
    assert result['lookups'] == {'SYN_COUNTRY_A': 'SYNTHETIC COUNTRY LABEL'}
    assert raw == before
    entry, = [e for e in result['provenance'] if e['path'] == [0, 'Details', 0, 'CodeDescription']]
    assert entry['value'] == 'SYNTHETIC COUNTRY LABEL' and entry['type'] == 'string'
    assert entry['rule'] == 'reviewed-country-active-version:first-open-ended'


@pytest.mark.parametrize('defect', ['object', 'missing-type', 'foreign-type', 'multiple-types',
    'missing-details', 'missing-code', 'numeric-code', 'missing-description', 'empty-description',
    'numeric-description', 'invalid-validity'])
def test_unproved_country_catalog_shape_stays_unsupported(defect):
    raw = catalog()
    if defect == 'object':
        raw = raw[0]
    elif defect == 'missing-type':
        del raw[0]['ReferenceDataType']
    elif defect == 'foreign-type':
        raw[0]['ReferenceDataType'] = 'SYNTHETIC_OTHER'
    elif defect == 'multiple-types':
        raw.append(deepcopy(raw[0]))
    elif defect == 'missing-details':
        del raw[0]['Details']
    else:
        row = raw[0]['Details'][0]
        if defect.startswith('missing-'):
            del row['Code' if defect == 'missing-code' else 'CodeDescription']
        elif defect == 'numeric-code':
            row['Code'] = 1
        elif defect == 'empty-description':
            row['CodeDescription'] = ''
        elif defect == 'numeric-description':
            row['CodeDescription'] = 1
        else:
            row['ValidTo'] = 1
    with pytest.raises(_UnsupportedMetadata):
        project(raw)


@pytest.mark.parametrize('detail', [False, True])
def test_country_catalog_explicit_foreign_language_is_a_contradiction(detail):
    raw = catalog()
    (raw[0]['Details'][0] if detail else raw[0])['language'] = 'en-US'
    with pytest.raises(JsonSafetyError):
        project(raw)


def test_country_multiple_versions_need_one_stable_choice_across_owned_capture_interval():
    raw = catalog()
    raw[0]['Details'] = [
        {'Code': 'SYN_COUNTRY_A', 'CodeDescription': 'SYNTHETIC FIRST',
         'ValidFrom': '2024-01-01', 'ValidTo': '2025-01-01'},
        {'Code': 'SYN_COUNTRY_A', 'CodeDescription': 'SYNTHETIC SECOND',
         'ValidFrom': '2025-01-01', 'ValidTo': '2026-01-01'}]
    clock = {'attempt': 'a' * 32, 'start_ms': 1735689600000, 'end_ms': 1735689600001,
             'timezone': 'Asia/Jakarta'}
    assert project(raw, clock_interval=clock)['lookups']['SYN_COUNTRY_A'] == 'SYNTHETIC SECOND'
    with pytest.raises(_UnsupportedMetadata):
        project(raw)
    clock['start_ms'] -= 1
    with pytest.raises(_UnsupportedMetadata, match='unstable_grid_reference_version'):
        project(raw, clock_interval=clock)
