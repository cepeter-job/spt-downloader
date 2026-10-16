"""Synthetic native Masa safety contracts; execution belongs on CI runners."""
from copy import deepcopy
import importlib
import importlib.util

import pytest

from coretax_json import JsonSafetyError, ORIGIN

RECORD = '00000000-0000-4000-8000-000000000001'
TAXPAYER = '00000000-0000-4000-8000-000000000003'
FOREIGN = '00000000-0000-4000-8000-000000000099'
SCOPE = ['0000000000000001', 2025, 'period']


def selected(tax):
    return {'record_id': RECORD, 'scope': list(SCOPE),
            'list_url': ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER,
            'meta': {'Jenis Pajak': tax, 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}}


def guard():
    # An absent feature is an assertion failure, not a collection error that
    # prevents the existing suite from exercising its own contracts.
    assert importlib.util.find_spec('coretax_masa_json') is not None, 'Native Masa guard is not implemented'
    module = importlib.import_module('coretax_masa_json')
    assert callable(getattr(module, 'check_masa_request_identities', None))
    return module.check_masa_request_identities


@pytest.mark.parametrize('tax,prefix', [('PPN', 'loadndvat'), ('PPh Unifikasi', 'loadwtr')])
@pytest.mark.parametrize('suffix', ['grid', 'grid/footer'])
def test_masa_request_guard_rejects_foreign_record_before_coverage(tax, prefix, suffix):
    event = {'url': ORIGIN + '/returnsheet/api/' + prefix + '/' + suffix,
             'method': 'POST', 'request_json': {'ReturnSheetRecordId': FOREIGN}}
    with pytest.raises(JsonSafetyError):
        guard()([event], selected(tax), SCOPE)


@pytest.mark.parametrize('tax,endpoint', [('PPN', 'nvat'), ('PPh Unifikasi', 'withholding-tax')])
@pytest.mark.parametrize('value', [FOREIGN, ' ' + RECORD, None, True, 1])
def test_masa_prefill_record_identity_is_literal(tax, endpoint, value):
    event = {'url': ORIGIN + '/returnsheet/api/prefillreturnsheet/' + endpoint,
             'method': 'POST', 'request_json': {'RecordId': value}}
    with pytest.raises(JsonSafetyError):
        guard()([event], selected(tax), SCOPE)


@pytest.mark.parametrize('tax,endpoint', [('PPN', 'nvat'), ('PPh Unifikasi', 'withholding-tax')])
def test_masa_matching_request_is_observation_not_native_eligibility(tax, endpoint):
    event = {'url': ORIGIN + '/returnsheet/api/prefillreturnsheet/' + endpoint,
             'method': 'POST', 'request_json': {'RecordId': RECORD}}
    before = deepcopy(event)
    assert guard()([event], selected(tax), SCOPE) is None
    assert event == before


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_missing_masa_observations_do_not_grant_native_eligibility(tax):
    assert guard()([], selected(tax), SCOPE) is None


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_masa_selected_scope_contradiction_fails_without_observations(tax):
    record = selected(tax)
    record['scope'][0] = '0000000000000099'
    with pytest.raises(JsonSafetyError):
        guard()([], record, SCOPE)


@pytest.mark.parametrize('tax,prefix', [('PPN', 'loadndvat'), ('PPh Unifikasi', 'loadwtr')])
def test_masa_guard_validates_every_event_after_missing_identity(tax, prefix):
    url = ORIGIN + '/returnsheet/api/' + prefix + '/grid'
    events = [{'url': url, 'method': 'POST', 'request_json': {}},
              {'url': url, 'method': 'POST', 'request_json': {'ReturnSheetRecordId': FOREIGN}}]
    with pytest.raises(JsonSafetyError):
        guard()(events, selected(tax), SCOPE)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_masa_guard_checks_other_masa_family_for_cross_return_contamination(tax):
    events = [{'url': ORIGIN + '/returnsheet/api/loadndvat/lb2-grid', 'method': 'POST',
               'request_json': {'ReturnSheetRecordId': RECORD}},
              {'url': ORIGIN + '/returnsheet/api/loadwtr/list-i-bpu-grid', 'method': 'POST',
               'request_json': {'ReturnSheetRecordId': FOREIGN}}]
    with pytest.raises(JsonSafetyError):
        guard()(events, selected(tax), SCOPE)
