"""Submitted amendment contracts from reviewed public PPN bindings."""
from copy import deepcopy
import hashlib
import importlib
import json

import pytest

from coretax_json import JsonSafetyError, _corporate_json
from coretax_masa_json import adapt_masa_detail
from coretax_masa_bindings import project_ppn_amount
from masa_projection_fixture import field, native_case


def amend_case():
    case = native_case('PPN')
    case['record']['meta']['Model SPT'] = 'Amendment 002'
    case['record']['source_fields']['ReturnSheetModel'] = 'Amendment 002'
    envelope = json.loads(case['packets'][0]['body'])
    outer = envelope['Payload']
    outer['ReturnSheetModel'] = 'AMENDMENT'
    outer['ReturnSheetStatusCode'] = 'SUBMITTED'
    form = json.loads(outer['FormData'])
    form['ReturnSheetModel'] = 'AMENDMENT'
    form['A1FormListOfExportTaxableGoodsOrServices']['ReturnSheetModel'] = 'AMENDMENT'
    outer['FormData'] = json.dumps(form)
    reseal(case, envelope)
    return case


def reseal(case, envelope):
    raw = json.dumps(envelope).encode()
    case['packets'][0]['body'] = raw
    case['packets'][0]['context'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def decode(case):
    return adapt_masa_detail(case['packets'], record=case['record'],
        scope=case['scope'], observed_forms=case['forms'])


def test_submitted_amendment_is_eligible_with_bound_literal_listing_model():
    case = amend_case()
    before = deepcopy(case)
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    assert result['coverage']['complete'] is True
    assert case == before


def test_amendment_number_is_not_inferred_from_primary_enum_alone():
    case = amend_case()
    del case['record']['source_fields']['ReturnSheetModel']
    result = decode(case)
    assert result['eligible'] is False


def test_conflicting_literal_amendment_number_is_fatal_without_observer():
    case = amend_case()
    case['record']['source_fields']['ReturnSheetModel'] = 'Amendment 001'
    case['forms'] = []
    with pytest.raises(JsonSafetyError):
        decode(case)


def test_amendment_primary_enum_cannot_override_normal_selection():
    case = amend_case()
    case['record']['meta']['Model SPT'] = 'Normal'
    case['record']['source_fields']['ReturnSheetModel'] = 'Normal'
    with pytest.raises(JsonSafetyError):
        decode(case)


def test_submitted_amendment_direct_money_is_not_rejected_as_unknown_model():
    source = _corporate_json('{"A1FormListOfExportTaxableGoodsOrServices":{"Total":17}}')
    result = project_ppn_amount(source, 'ExportOfTangibleGoods', model='AMENDMENT')
    assert result['value'] == '17'
    assert result['provenance'][0]['path'] == ['A1FormListOfExportTaxableGoodsOrServices','Total']


def test_submitted_amendment_vat_due_preserves_final_stored_value_not_difference():
    source = _corporate_json('{"BasedOnType":null,"VATUnderOrOverPaidDueToAmendment":{"VAT":123},"VATUnderOrOverPaid":{"VAT":800},"VATUnderOrOverPaidOnPrevious":{"VAT":100}}')
    result = project_ppn_amount(source, 'VATIsUnderOrOverpaidAmandment', model='AMENDMENT')
    assert result['value'] == '123'
    assert any(p['path']==['VATUnderOrOverPaidDueToAmendment','VAT'] for p in result['provenance'])
    assert not any(p['path'] in [['VATUnderOrOverPaid','VAT'],['VATUnderOrOverPaidOnPrevious','VAT']] for p in result['provenance'])


def test_submitted_amendment_stlg_due_uses_final_explicit_callback_not_stored_total():
    source = _corporate_json('{"DomesticDeliveriesUsingOtherValue":{"SalesTaxLuxuryGoods":10.8},"DomesticDeliveriesToTourist":{"SalesTaxLuxuryGoods":1.2},"DomesticDeliveriesOtherThanOtherValue":{"SalesTaxLuxuryGoods":0.1},"DomesticDeliveriesSelfCollected":{"SalesTaxLuxuryGoods":null},"STLGCollectedByVATCollector":{"SalesTaxLuxuryGoods":2.7},"STLGUnderOrOverPaidOnPrevious":{"SalesTaxLuxuryGoods":3.1},"STLGUnderOrOverPaidDueToAmendment":{"SalesTaxLuxuryGoods":999}}')
    result = project_ppn_amount(source, 'STLGUnderOverpaidDueAmmendment', model='AMENDMENT')
    assert result['value'] == '5'
    assert not any(p['path']==['STLGUnderOrOverPaidDueToAmendment','SalesTaxLuxuryGoods'] for p in result['provenance'])


def test_amendment_header_period_and_presentation_are_response_backed():
    helper = getattr(importlib.import_module('coretax_masa_bindings'), 'project_ppn_header', None)
    assert callable(helper), 'PPN native header projection is absent'
    payload = {'PeriodCode': '01012025', 'ReturnSheetModel': 'AMENDMENT'}
    period = helper(payload, 'Period')
    model = helper(payload, 'Model')
    assert period['value'] == '012025'
    assert model['value'] == 'Pembetulan'
    assert period['provenance'][0]['path'] == ['PeriodCode']
    assert model['provenance'][0]['path'] == ['ReturnSheetModel']


def test_amendment_projector_binds_header_evidence_to_outer_payload_not_formdata():
    case = amend_case()
    case['forms'][0]['fields'] += [field('Period','Periode','HEADER'), field('Model','Normal/Pembetulan','HEADER')]
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    values = {x['field']:x['value'] for x in result['sections'][0]['fields']}
    assert values['Period'] == '012025' and values['Model'] == 'Pembetulan'
    for control, path in [('Period',['PeriodCode']),('Model',['ReturnSheetModel'])]:
        matches = [p for p in result['provenance']['bindings'] if p.get('field')==control]
        assert matches and all(p['container_path']==['Payload'] and p['path']==path for p in matches)
