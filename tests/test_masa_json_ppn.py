"""Induk PPN final-value precedence from the pinned submitted-form code."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata


def project(form, control, model='NORMAL'):
    implementation = getattr(importlib.import_module('coretax_masa_bindings'), 'project_ppn_amount', None)
    assert callable(implementation), 'PPN scalar projection is not implemented'
    return implementation(form, control, model=model)


def test_ppn_export_override_uses_a1_total():
    form = _corporate_json('''{"ExportTangibleTaxableGoods":{"SellingPrice":999},
                            "A1FormListOfExportTaxableGoodsOrServices":{"Total":17}}''')
    before = deepcopy(form)
    result = project(form, 'ExportOfTangibleGoods')
    assert result['value'] == '17'
    assert result['provenance'] == [{'path': ['A1FormListOfExportTaxableGoodsOrServices', 'Total'],
                                    'type': 'number', 'value': '17'}]
    assert form == before


@pytest.mark.parametrize('control,root,leaf', [
    ('CarryForwardOfInputTax', 'CarryForwardOfInputTax', 'VAT'),
    ('VATNeedRepayVAT', 'VATNeedToRepay', 'VAT'),
    ('DomesticDeliveriesUsingOtherValueTaxBaseSTLG', 'DomesticDeliveriesUsingOtherValue', 'SalesTaxLuxuryGoods'),
    ('ImportOfTaxableGoodsFromOusideCustomsAreaImportValue', 'ImportOfTaxableGoods', 'SellingPrice'),
])
def test_ppn_amount_paths_are_explicit_and_do_not_collide(control, root, leaf):
    form = {root: {leaf: _corporate_json('1200')}, control: _corporate_json('999')}
    # Some controls intentionally have the same name as their source object.
    form[root] = {leaf: _corporate_json('1200')}
    result = project(form, control)
    assert result['value'] == '1.200'
    assert result['provenance'][0]['path'] == [root, leaf]


@pytest.mark.parametrize('control', ['STLGUnderOverOnPreviousVATReturn', 'STLGUnderOverpaidDueAmmendment',
                                    'VATIsUnderOrOverpaidAmandment'])
def test_normal_return_does_not_display_hidden_amendment_values(control):
    form = _corporate_json('''{"STLGUnderOrOverPaidOnPrevious":{"SalesTaxLuxuryGoods":17},
        "STLGUnderOrOverPaidDueToAmendment":{"SalesTaxLuxuryGoods":19},
        "VATUnderOrOverPaidDueToAmendment":{"VAT":23}}''')
    result = project(form, control)
    assert result['value'] == ''
    assert result['rule'] == 'normal_model_null'


def test_stlg_recalculation_follows_final_ui_override_and_retains_dependencies():
    form = _corporate_json('''{
      "DomesticDeliveriesUsingOtherValue":{"SalesTaxLuxuryGoods":10.8},
      "DomesticDeliveriesToTourist":{"SalesTaxLuxuryGoods":0},
      "DomesticDeliveriesOtherThanOtherValue":{"SalesTaxLuxuryGoods":2.8},
      "DomesticDeliveriesSelfCollected":{"SalesTaxLuxuryGoods":null},
      "STLGMustBeSelfCollected":{"SalesTaxLuxuryGoods":999},
      "STLGCollectedByVATCollector":{"SalesTaxLuxuryGoods":15.5},
      "STLGUnderOrOverPaid":{"SalesTaxLuxuryGoods":888}
    }''')
    before = deepcopy(form)
    self_collected = project(form, 'STLGSelfCollected')
    underpaid = project(form, 'STLGUnderOverpaid')
    assert self_collected['value'] == '13'
    assert underpaid['value'] == '-3'
    assert self_collected['rule'] == 'floor_sum_submitted_stlg'
    paths = [item['path'] for item in underpaid['provenance']]
    assert ['STLGCollectedByVATCollector', 'SalesTaxLuxuryGoods'] in paths
    assert ['STLGUnderOrOverPaid', 'SalesTaxLuxuryGoods'] not in paths
    assert form == before


@pytest.mark.parametrize('raw,expected', [('null', ''), ('0', '0'), ('-1000', '-1.000')])
def test_optional_inputnumber_without_coalescing_preserves_null(raw, expected):
    result = project({'CarryForwardOfInputTax': {'VAT': _corporate_json(raw)}}, 'CarryForwardOfInputTax')
    assert result['value'] == expected
    assert result['provenance'][0]['type'] == ('null' if raw == 'null' else 'number')


def test_observed_nullish_zero_rule_is_distinct_from_missing_unknown_path():
    form = {'DomesticDeliveriesUsingOtherValue': {'SalesTaxLuxuryGoods': None}}
    result = project(form, 'DomesticDeliveriesUsingOtherValueTaxBaseSTLG')
    assert result['value'] == '0'
    assert result['provenance'][0]['value'] is None


@pytest.mark.parametrize('control,model', [('InventedAlias', 'NORMAL'), ('VATNeedRepayVAT', 'UNKNOWN')])
def test_unknown_ppn_binding_cannot_guess_a_value(control, model):
    with pytest.raises(_UnsupportedMetadata):
        project({}, control, model)
