"""Packet and primary identity checks must run before eligibility fallback."""
from copy import deepcopy
import importlib
import json

import pytest

from coretax_json import JsonSafetyError
from masa_json_fixtures import FOREIGN, NPWP, SCOPE, packet, payload, selected


def adapt(bodies, tax, forms=None):
    module = importlib.import_module('coretax_masa_json')
    implementation = getattr(module, 'adapt_masa_detail', None)
    assert callable(implementation), 'Native Masa packet adapter is not implemented'
    return implementation(bodies, record=selected(tax), scope=SCOPE, observed_forms=forms)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('forms', [None, [], [{'name': 'UNKNOWN', 'build': 'unapproved'}]])
def test_valid_identity_without_bound_forms_never_grants_eligibility(tax, forms):
    source = packet(tax)
    before = deepcopy(source)
    result = adapt(iter([source]), tax, forms)
    assert result['eligible'] is False
    assert result['sections'] == []
    assert result['coverage']['complete'] is False
    assert result['reason']
    assert source == before


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('field,value', [
    ('TIN', '0000000000000099'), ('TIN', 1), ('TaxpayerIdentifier', FOREIGN),
    ('PeriodCode', '02022025'), ('PeriodCode', '01012024'), ('ReturnSheetModel', 'AMENDED'),
])
@pytest.mark.parametrize('remove_form', [False, True])
def test_outer_identity_conflict_cannot_hide_behind_missing_forms(tax, field, value, remove_form):
    data = payload(tax)
    data[field] = value
    if remove_form:
        data.pop('FormData')
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax, data)], tax)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('field,value', [
    ('ReturnSheetRecordIdentifier', FOREIGN), ('ReturnSheetAggregateIdentifier', FOREIGN),
    ('TaxPeriodCode', '02022025'), ('TaxPeriodCode', '01012024'),
])
@pytest.mark.parametrize('remove_tin', [False, True])
def test_inner_identity_conflict_cannot_hide_behind_missing_tin(tax, field, value, remove_tin):
    data = payload(tax)
    form = json.loads(data['FormData'])
    form[field] = value
    if remove_tin:
        form.pop('TIN' if tax == 'PPN' else 'TaxIdentificationNumber')
    data['FormData'] = json.dumps(form)
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax, data)], tax, [{'name': 'UNKNOWN'}])


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_inner_taxpayer_number_is_checked_separately_from_outer_tin(tax):
    data = payload(tax)
    form = json.loads(data['FormData'])
    form['TIN' if tax == 'PPN' else 'TaxIdentificationNumber'] = '0000000000000099'
    data['FormData'] = json.dumps(form)
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax, data)], tax)


@pytest.mark.parametrize('tax,field,value', [
    ('PPN', 'PeriodYear', 2024), ('PPN', 'PeriodMonth', 2),
    ('PPN', 'PeriodMonth', True), ('PPN', 'ReturnSheetType', 'ICT_RCITR'),
    ('PPh Unifikasi', 'PeriodYear', '2024'),
    ('PPh Unifikasi', 'PeriodStartMonth', '2'), ('PPh Unifikasi', 'PeriodEndMonth', '2'),
])
def test_native_period_and_type_contradictions_are_not_normalized(tax, field, value):
    data = payload(tax)
    data[field] = value
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax, data)], tax)


@pytest.mark.parametrize('field,value', [('TaxType', 'ICT_RCIT'), ('ReturnSheetModel', 'AMENDED')])
def test_ppn_native_type_and_model_cannot_be_replaced_by_corporate_rules(field, value):
    tax = 'PPN'
    data = payload(tax)
    form = json.loads(data['FormData']); form[field] = value
    data['FormData'] = json.dumps(form)
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax, data)], tax)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('status', [401, 403])
def test_unauthorized_masa_packet_never_falls_back(tax, status):
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax, status=status)], tax)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('field,value', [('sha256', '0'*64), ('record_id', FOREIGN),
    ('attempt', 'not-an-attempt'), ('frame_url', 'https://example.invalid/foreign')])
def test_masa_packet_custody_is_required_without_form_bindings(tax, field, value):
    source = packet(tax); source['context'][field] = value
    with pytest.raises(JsonSafetyError):
        adapt([source], tax)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('kind', ['missing_form', 'failed_envelope', 'malformed_form', 'unknown_shape'])
def test_unsupported_first_packet_never_masks_later_identity_conflict(tax, kind):
    first = payload(tax)
    if kind == 'missing_form': first.pop('FormData')
    elif kind == 'malformed_form': first['FormData'] = '{bad json'
    elif kind == 'unknown_shape': first['FormData'] = '[]'
    first_packet = packet(tax, first, successful=kind != 'failed_envelope')
    second = payload(tax); second['TIN'] = '0000000000000099'
    with pytest.raises(JsonSafetyError):
        adapt(iter([first_packet, packet(tax, second, sequence=2)]), tax)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_identical_primary_repetition_does_not_create_native_coverage(tax):
    result = adapt([packet(tax), packet(tax, sequence=2)], tax)
    assert result['eligible'] is False
    assert len(result['provenance']['events']) == 2


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_changed_primary_snapshot_is_rejected_even_when_identity_matches(tax):
    second = payload(tax)
    form = json.loads(second['FormData']); form['Name'] = 'DIFFERENT SYNTHETIC NAME'
    second['FormData'] = json.dumps(form)
    with pytest.raises(JsonSafetyError):
        adapt([packet(tax), packet(tax, second, sequence=2)], tax)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_secret_in_nested_form_is_rejected_without_echoing_it(tax):
    secret = 'SYNTHETIC-DO-NOT-LOG-SECRET'
    data = payload(tax)
    form = json.loads(data['FormData']); form['Password'] = secret
    data['FormData'] = json.dumps(form)
    with pytest.raises(JsonSafetyError) as error:
        adapt([packet(tax, data)], tax)
    assert secret not in str(error.value)
