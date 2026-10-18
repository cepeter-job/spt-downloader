"""Final PPh21 header patches use outer prefill data, not embedded aliases."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json


def project(payload, control, **kwargs):
    module = importlib.import_module('coretax_pph21_json_bindings')
    function = getattr(module, 'project_pph21_header', None)
    assert callable(function), 'PPh21 header projection is not implemented'
    return function(payload, control, **kwargs)


def source():
    return _corporate_json('{"PeriodMonth":1,"PeriodYear":2025,"ReturnSheetModel":"NORMAL",'
                           '"ReturnSheetStatusCode":"SUBMITTED","SubmitInProgressStatus":false,'
                           '"FormData":"{\\"TaxPeriodMonth\\":12,\\"TaxPeriodYear\\":2024}"}')


@pytest.mark.parametrize('control,value,path', [('TaxPeriodMonth', '1', 'PeriodMonth'),
    ('TaxPeriodYear', '2025', 'PeriodYear'), ('SubmitInProgressStatus', 'Submitted', 'ReturnSheetStatusCode')])
def test_final_outer_patch_wins_without_numeric_locale_formatting(control, value, path):
    payload = source()
    before = deepcopy(payload)
    result = project(payload, control)
    assert result['value'] == value and type(result['value']) is str
    assert [path] in [p['path'] for p in result['provenance']]
    assert result['container_path'] == ['Payload']
    assert payload == before


def test_model_label_is_the_bound_catalog_description_not_a_guessed_translation():
    result = project(source(), 'Status', model_labels={'NORMAL': 'SYNTHETIC NORMAL LABEL'})
    assert result['value'] == 'SYNTHETIC NORMAL LABEL'
    assert result['reference'] == {'type': 'RETURN_SHEET_MODEL', 'code': 'NORMAL'}


@pytest.mark.parametrize('labels', [None, {}, {'OTHER': 'SYNTHETIC'}, {'NORMAL': True}])
def test_unbound_or_invalid_model_label_cannot_be_replaced_by_code_or_listing(labels):
    with pytest.raises(_UnsupportedMetadata):
        project(source(), 'Status', model_labels=labels)


@pytest.mark.parametrize('flag,status,expected', [(True, 'SUBMITTED', 'In Progress'),
    (False, 'CREATED', '-'), (None, 'SUBMITTED', 'Submitted')])
def test_submission_status_uses_final_outer_boolean_branch(flag, status, expected):
    payload = source()
    payload.update(SubmitInProgressStatus=flag, ReturnSheetStatusCode=status)
    result = project(payload, 'SubmitInProgressStatus')
    assert result['value'] == expected
    assert ['SubmitInProgressStatus'] in [p['path'] for p in result['provenance']]


@pytest.mark.parametrize('value,expected', [('01', '01'), (None, ''), (_corporate_json('1.0'), '1')])
def test_month_control_preserves_text_and_explicit_null_but_renders_json_number(value, expected):
    payload = source()
    payload['PeriodMonth'] = value
    assert project(payload, 'TaxPeriodMonth')['value'] == expected


@pytest.mark.parametrize('control,mutation', [('TaxPeriodMonth', 'missing'), ('TaxPeriodYear', 'boolean'),
    ('TaxPeriod', 'unknown'), ('SubmitInProgressStatus', 'nonboolean')])
def test_missing_wrong_type_and_unreviewed_controls_are_unsupported(control, mutation):
    payload = source()
    if mutation == 'missing':
        del payload['PeriodMonth']
    elif mutation == 'boolean':
        payload['PeriodYear'] = True
    elif mutation == 'nonboolean':
        payload['SubmitInProgressStatus'] = 'false'
    with pytest.raises(_UnsupportedMetadata):
        project(payload, control)
