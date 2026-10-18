"""Literal PPh21 listing identity, isolated from PPN and mixed-list rendering."""
from copy import deepcopy
import hashlib
import importlib
import pytest
from coretax_json import JsonSafetyError
from test_ppn_json_listing_binding import case as ppn_case, seal, SCOPE, RECORD


def case():
    response, record = ppn_case()
    response['rows'][0].update(TaxTypeCode='ICT_WIT', ReturnSheetTypeCode='ICT_WITR')
    record['meta']['Jenis Pajak'] = 'PPh Pasal 21/26'
    seal(response)
    return response, record


def bind(response, record):
    function = getattr(importlib.import_module('coretax_masa_json'), 'bind_pph21_listing_identity', None)
    assert callable(function), 'PPh21 listing identity binding is not implemented'
    return function(response, record=record, scope=SCOPE)


def test_original_listing_bytes_bind_literal_amendment_without_mutation():
    response, record = case()
    before = deepcopy((response, record))
    result = bind(response, record)
    assert result['eligible']
    assert result['source_fields']['TaxTypeCode'] == 'ICT_WIT'
    assert result['source_fields']['ReturnSheetTypeCode'] == 'ICT_WITR'
    assert result['source_fields']['ReturnSheetModel'] == 'Amendment 002'
    assert result['source_identity']['record_id'] == RECORD
    assert result['source_identity']['body_sha256'] == hashlib.sha256(response['body']).hexdigest()
    assert (response, record) == before


@pytest.mark.parametrize('key,value', [('TaxTypeCode', 'VAT_VAT'), ('ReturnSheetTypeCode', 'VAT_VATR'),
    ('ReturnSheetStatusCode', 'DRAFT'), ('ReturnSheetModel', 'Amendment 2'), ('TaxPeriodCode', '02022025'),
    ('TaxpayerAggregateIdentifier', '00000000-0000-4000-8000-000000000099')])
def test_contradictory_listing_identity_is_fatal(key, value):
    response, record = case()
    response['rows'][0][key] = value
    seal(response)
    with pytest.raises(JsonSafetyError):
        bind(response, record)


@pytest.mark.parametrize('defect', ['mutated-rows', 'stale-sequence', 'absent-record'])
def test_untrusted_or_stale_observations_cannot_repair_identity(defect):
    response, record = case()
    if defect == 'mutated-rows':
        response['rows'][0]['AggregateIdentifier'] = 'changed-after-response'
    elif defect == 'stale-sequence':
        response['after_sequence'] = response['sequence']
    else:
        record['record_id'] = '00000000-0000-4000-8000-000000000099'
    with pytest.raises(JsonSafetyError):
        bind(response, record)


@pytest.mark.parametrize('defect', ['missing-aggregate', 'unsupported-filter', 'other-tax'])
def test_incomplete_binding_is_not_eligible(defect):
    response, record = case()
    if defect == 'missing-aggregate':
        del response['rows'][0]['AggregateIdentifier']
        seal(response)
    elif defect == 'unsupported-filter':
        response['binding']['request']['Filters'] = [{'Field': 'Unreviewed', 'Value': 'SYNTHETIC'}]
    else:
        record['meta']['Jenis Pajak'] = 'PPh Unifikasi'
    result = bind(response, record)
    assert not result['eligible'] and 'source_fields' not in result
