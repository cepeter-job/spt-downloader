"""Status dropdown catalogs do not use grid active-version selection."""
from copy import deepcopy
import importlib
import pytest
from coretax_json import JsonSafetyError, _UnsupportedMetadata


def project(payload):
    function = getattr(importlib.import_module('coretax_pph21_json_bindings'),
                       'project_pph21_model_references', None)
    assert callable(function), 'PPh21 model catalog projection is not implemented'
    return function(payload, locale='id-ID')


def catalog():
    return [{'ReferenceDataType': 'RETURN_SHEET_MODEL', 'language': 'id-ID', 'Details': [
        {'Code': 'NORMAL', 'CodeDescription': 'SYNTHETIC NORMAL LABEL', 'ValidTo': None}]}]


def test_model_label_has_literal_code_and_response_path():
    payload = catalog()
    before = deepcopy(payload)
    result = project(payload)
    assert result['lookups'] == {'ReturnSheetModel': {'NORMAL': 'SYNTHETIC NORMAL LABEL'}}
    assert [0, 'Details', 0, 'CodeDescription'] in [p['path'] for p in result['provenance']]
    assert payload == before


def test_duplicate_model_versions_are_unsupported_not_grid_version_selected():
    payload = catalog()
    old = deepcopy(payload[0]['Details'][0])
    old.update(CodeDescription='OLD SYNTHETIC LABEL', ValidTo='2020-01-01')
    payload[0]['Details'].insert(0, old)
    with pytest.raises(_UnsupportedMetadata):
        project(payload)


def test_model_catalog_language_contradiction_is_fatal():
    payload = catalog()
    payload[0]['language'] = 'en-US'
    with pytest.raises(JsonSafetyError):
        project(payload)
