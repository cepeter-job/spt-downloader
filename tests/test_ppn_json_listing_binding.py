"""Synthetic source-bound PPN identity contracts; execute on CI only."""
from copy import deepcopy
import hashlib
import importlib
import importlib.util
import json

import pytest

from coretax_json import JsonSafetyError, ORIGIN

TAXPAYER = '00000000-0000-4000-8000-000000000003'
RECORD = '00000000-0000-4000-8000-000000000001'
AGGREGATE = '00000000-0000-4000-8000-000000000002'
SOURCE = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER
SCOPE = ['0000000000000001', 2026, 'period']


def case():
    row = {'RecordId': RECORD, 'AggregateIdentifier': AGGREGATE,
           'TaxpayerAggregateIdentifier': TAXPAYER, 'TaxPeriodCode': '02022026',
           'TaxTypeCode': 'VAT_VAT', 'ReturnSheetTypeCode': 'VAT_VATR',
           'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'Amendment 002'}
    response = {'rows': [row], 'total': 1, 'sequence': 7, 'after_sequence': 6,
        'binding': {'response_url': ORIGIN + '/returnsheet/api/returnsheetssubmitted',
                    'method': 'POST', 'http_status': 200, 'frame_url': SOURCE,
                    'request': {'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0,
                                'Rows': 50, 'Filters': [], 'isArchieved': False,
                                'LanguageId': 1, 'SortField': None, 'SortOrder': None}}}
    seal(response)
    record = {'record_id': RECORD, 'list_url': SOURCE, 'list_page': 1,
              'source_status': 'SPT Dilaporkan', 'scope': list(SCOPE),
              'meta': {'Jenis Pajak': 'PPN', 'Masa Pajak': 'Februari 2026',
                       'Model SPT': 'Amendment 002'}}
    return response, record


def seal(response):
    response['body'] = json.dumps({'IsSuccessful': True, 'Payload': {
        'Data': response['rows'], 'TotalRecords': response['total']}}).encode()


def bind(response, record):
    assert importlib.util.find_spec('coretax_masa_json') is not None, 'Native PPN identity binding is absent'
    module = importlib.import_module('coretax_masa_json')
    function = getattr(module, 'bind_ppn_listing_identity', None)
    assert callable(function), 'Native PPN identity binding is absent'
    return function(response, record=record, scope=SCOPE)


def test_ppn_identity_binds_raw_amendment_without_rendering_other_tax_metadata():
    response, record = case()
    before = deepcopy((response, record))
    result = bind(response, record)
    assert result['eligible'] is True
    assert result['source_fields']['TaxPeriodCode'] == '02022026'
    assert result['source_fields']['ReturnSheetModel'] == 'Amendment 002'
    assert result['source_fields']['RecordId'] == RECORD
    assert result['source_identity']['aggregate_id'] == AGGREGATE
    assert result['source_identity']['taxpayer_id'] == TAXPAYER
    assert result['source_identity']['body_sha256'] == hashlib.sha256(response['body']).hexdigest()
    assert result['source_identity']['sequence'] == 7
    assert (response, record) == before


@pytest.mark.parametrize('key,value', [
    ('TaxpayerAggregateIdentifier', '00000000-0000-4000-8000-000000000099'),
    ('TaxPeriodCode', '03032026'), ('TaxPeriodCode', '02022025'),
    ('ReturnSheetModel', 'Amendment 001'), ('ReturnSheetModel', 'Amendment 2'),
    ('TaxTypeCode', 'ICT_RCIT'), ('ReturnSheetTypeCode', 'ICT_RCITR'),
    ('ReturnSheetStatusCode', 'DRAFT'),
])
def test_ppn_identity_rejects_conflicting_literal_selection(key, value):
    response, record = case()
    response['rows'][0][key] = value
    seal(response)
    with pytest.raises(JsonSafetyError):
        bind(response, record)


def test_ppn_identity_requires_original_bytes_not_mutated_observer_rows():
    response, record = case()
    response['rows'][0]['AggregateIdentifier'] = 'changed-after-response'
    with pytest.raises(JsonSafetyError):
        bind(response, record)


def test_ppn_identity_rejects_stale_response_sequence():
    response, record = case()
    response['after_sequence'] = response['sequence']
    with pytest.raises(JsonSafetyError):
        bind(response, record)


def test_ppn_identity_requires_exact_selected_record_in_verified_response():
    response, record = case()
    response['rows'][0]['RecordId'] = '00000000-0000-4000-8000-000000000099'
    seal(response)
    with pytest.raises(JsonSafetyError):
        bind(response, record)


def test_ppn_identity_failed_source_envelope_cannot_grant_eligibility():
    response, record = case()
    envelope = json.loads(response['body'])
    envelope['IsSuccessful'] = False
    response['body'] = json.dumps(envelope).encode()
    with pytest.raises(JsonSafetyError, match='explicit success'):
        bind(response, record)


def test_ppn_identity_unknown_filter_cannot_grant_eligibility():
    response, record = case()
    response['binding']['request']['Filters'] = [{'Field': 'UnknownField', 'Value': 'SYNTHETIC'}]
    assert bind(response, record)['eligible'] is False


def test_ppn_identity_missing_aggregate_cannot_grant_eligibility():
    response, record = case()
    del response['rows'][0]['AggregateIdentifier']
    seal(response)
    result = bind(response, record)
    assert result['eligible'] is False
    assert 'source_fields' not in result


def test_ppn_identity_is_not_enabled_for_unifikasi():
    response, record = case()
    record['meta']['Jenis Pajak'] = 'PPh Unifikasi'
    result = bind(response, record)
    assert result['eligible'] is False
    assert 'source_fields' not in result


def test_ppn_identity_rejects_changed_previously_bound_aggregate():
    response, record = case()
    record['source_identity'] = {'record_id': RECORD, 'aggregate_id': 'changed-old-identity',
                                 'taxpayer_id': TAXPAYER, 'source_url': SOURCE}
    with pytest.raises(JsonSafetyError):
        bind(response, record)
