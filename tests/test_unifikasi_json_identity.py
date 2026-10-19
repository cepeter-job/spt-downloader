"""Source-proven Unifikasi listing and submitted lifecycle contracts."""
from copy import deepcopy
import importlib
import json

import pytest

from coretax_json import JsonSafetyError
from coretax_masa_json import adapt_masa_detail
from masa_json_fixtures import SCOPE, packet
from masa_projection_fixture import native_case
from test_ppn_json_listing_binding import case as listing_case, seal


def listing():
    response, record = listing_case()
    response['rows'][0].update(TaxTypeCode='ICT_WT', ReturnSheetTypeCode='ICT_WTR')
    record['meta']['Jenis Pajak'] = 'PPh Unifikasi'
    seal(response)
    return response, record


def bind(response, record):
    function = getattr(importlib.import_module('coretax_masa_json'), 'bind_unifikasi_listing_identity', None)
    assert callable(function), 'Unifikasi listing identity is not implemented'
    return function(response, record=record, scope=SCOPE)


def test_unifikasi_listing_binds_exact_original_identity_and_literal_model():
    response, record = listing()
    before = deepcopy((response, record))
    result = bind(response, record)
    assert result['eligible']
    assert result['source_fields']['TaxTypeCode'] == 'ICT_WT'
    assert result['source_fields']['ReturnSheetTypeCode'] == 'ICT_WTR'
    assert result['source_fields']['ReturnSheetModel'] == 'Amendment 002'
    assert result['source_identity']['record_id'] == record['record_id']
    assert (response, record) == before


@pytest.mark.parametrize('key,value', [('TaxTypeCode', 'ICT_WIT'), ('ReturnSheetTypeCode', 'ICT_WITR'),
    ('ReturnSheetStatusCode', 'DRAFT'), ('ReturnSheetModel', 'Amendment 2'),
    ('TaxPeriodCode', '02022025'), ('TaxpayerAggregateIdentifier', '00000000-0000-4000-8000-000000000099')])
def test_unifikasi_contradictory_listing_stops(key, value):
    response, record = listing()
    response['rows'][0][key] = value
    seal(response)
    with pytest.raises(JsonSafetyError):
        bind(response, record)


@pytest.mark.parametrize('defect', ['mutated-rows', 'stale-sequence', 'absent-record'])
def test_unifikasi_listing_cannot_rebind_untrusted_evidence(defect):
    response, record = listing()
    if defect == 'mutated-rows':
        response['rows'][0]['AggregateIdentifier'] = 'changed-after-response'
    elif defect == 'stale-sequence':
        response['after_sequence'] = response['sequence']
    else:
        record['record_id'] = '00000000-0000-4000-8000-000000000099'
    with pytest.raises(JsonSafetyError):
        bind(response, record)


def source_case(model='Normal'):
    case = native_case('PPh Unifikasi')
    case['record']['meta']['Model SPT'] = model
    case['record']['source_fields'].update(ReturnSheetModel=model, ReturnSheetStatusCode='SUBMITTED',
                                          TaxTypeCode='ICT_WT', ReturnSheetTypeCode='ICT_WTR')
    data = json.loads(case['packets'][0]['body'])['Payload']
    data.update(ReturnSheetStatusCode='SUBMITTED', ReturnSheetType='ICT_WTR',
                ReturnSheetModel='NORMAL' if model == 'Normal' else 'AMENDMENT')
    case['packets'][0] = packet('PPh Unifikasi', data)
    return case


def adapt(case):
    return adapt_masa_detail(case['packets'], record=case['record'], scope=case['scope'],
                             observed_forms=case['forms'])


@pytest.mark.parametrize('model', ['Normal', 'Amendment 001', 'Amendment 002'])
def test_native_unifikasi_submitted_models(model):
    case = source_case(model)
    result = adapt(case)
    assert result['eligible'], result['reason']


@pytest.mark.parametrize('key,value', [('ReturnSheetStatusCode', 'DRAFT'), ('ReturnSheetType', 'ICT_WITR')])
def test_native_unifikasi_wrong_primary_lifecycle_stops(key, value):
    case = source_case()
    data = json.loads(case['packets'][0]['body'])['Payload']
    data[key] = value
    case['packets'][0] = packet('PPh Unifikasi', data)
    with pytest.raises(JsonSafetyError):
        adapt(case)


def test_native_unifikasi_missing_submitted_evidence_is_ineligible():
    case = source_case()
    data = json.loads(case['packets'][0]['body'])['Payload']
    del data['ReturnSheetStatusCode']
    case['packets'][0] = packet('PPh Unifikasi', data)
    result = adapt(case)
    assert not result['eligible']
    assert not result['coverage']['complete']
