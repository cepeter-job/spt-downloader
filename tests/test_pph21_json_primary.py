"""PPh21 primary safety uses its own source keys, not PPN/Unifikasi aliases."""
from copy import deepcopy
import json

import pytest

from coretax_json import JsonSafetyError, ORIGIN
from coretax_masa_json import adapt_masa_detail, check_masa_request_identities
from masa_json_fixtures import RECORD, AGGREGATE, FOREIGN, NPWP, SCOPE, packet, selected

TAX = 'PPh Pasal 21/26'
ENDPOINT = ORIGIN + '/returnsheet/api/prefillreturnsheet/article-2126'


def case():
    record = selected(TAX)
    # Public main offsets 2732403/2733134 declare ICT_WIT / ICT_WITR.
    # Identifiers and all records here remain synthetic.
    record['source_fields'].update(TaxTypeCode='ICT_WIT', ReturnSheetTypeCode='ICT_WITR',
                                   ReturnSheetStatusCode='SUBMITTED', ReturnSheetModel='Normal')
    form = {'RecordId': RECORD, 'ReturnSheetAggregateIdentifier': AGGREGATE,
            'TIN': NPWP, 'TaxType': 'ICT_WIT',
            'TaxPeriodMonth': 1, 'TaxPeriodYear': 2025, 'Status': 'NORMAL',
            'Form1A': {}, 'Form1B': {}, 'Form2': {}, 'Form3': {}}
    outer = {'TIN': NPWP, 'PeriodMonth': 1, 'PeriodYear': 2025,
             'ReturnSheetModel': 'NORMAL', 'ReturnSheetStatusCode': 'SUBMITTED',
             'IsMigrated': False, 'FormData': json.dumps(form), 'PreviousFormData': None}
    return record, outer, form


def source(outer):
    item = packet(TAX, outer, request={'RecordId': RECORD, 'onManualClick': False})
    item['context']['url'] = ENDPOINT
    return item


@pytest.mark.parametrize('identity', [FOREIGN, ' ' + RECORD, None, True, 1])
def test_primary_request_rejects_foreign_or_nonliteral_record_before_projection(identity):
    record, _, _ = case()
    event = {'url': ENDPOINT, 'method': 'POST', 'request_json': {'RecordId': identity}}
    with pytest.raises(JsonSafetyError):
        check_masa_request_identities([event], record, SCOPE)


@pytest.mark.parametrize('key,value', [
    ('RecordId', FOREIGN), ('RecordId', None), ('RecordId', True),
    ('ReturnSheetAggregateIdentifier', FOREIGN), ('TIN', '0000000000000099'),
    ('TIN', 1), ('TaxType', 'FOREIGN_TAX_KIND'), ('TaxPeriodMonth', 2),
    ('TaxPeriodMonth', True), ('TaxPeriodYear', 2024), ('Status', 'AMENDMENT'),
])
def test_inner_form_identity_contradictions_are_fatal_even_without_observed_forms(key, value):
    record, outer, form = case()
    form[key] = value
    outer['FormData'] = json.dumps(form)
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([source(outer)], record=record, scope=SCOPE, observed_forms=[])


@pytest.mark.parametrize('key,value', [
    ('TIN', '0000000000000099'), ('TIN', True), ('PeriodMonth', 2),
    ('PeriodMonth', True), ('PeriodYear', 2024), ('ReturnSheetModel', 'AMENDMENT'),
])
def test_outer_header_identity_contradictions_are_fatal_before_unsupported_form(key, value):
    record, outer, _ = case()
    outer[key] = value
    outer['FormData'] = None
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([source(outer)], record=record, scope=SCOPE, observed_forms=[])


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_pph21_primary_cannot_bind_to_other_masa_family(tax):
    _, outer, _ = case()
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([source(outer)], record=selected(tax), scope=SCOPE, observed_forms=[])


def test_valid_pph21_primary_identity_is_not_complete_form_coverage():
    record, outer, _ = case()
    item = source(outer)
    before = deepcopy(item)
    result = adapt_masa_detail([item], record=record, scope=SCOPE, observed_forms=[])
    assert result['eligible'] is False and result['coverage']['complete'] is False
    assert item == before


def test_missing_primary_identity_cannot_be_repaired_from_ppn_alias():
    record, outer, form = case()
    del form['RecordId']
    form['ReturnSheetRecordIdentifier'] = RECORD
    outer['FormData'] = json.dumps(form)
    result = adapt_masa_detail([source(outer)], record=record, scope=SCOPE, observed_forms=[])
    assert result['eligible'] is False
    assert 'missing_masa_identity_RecordId' in result['reason']
