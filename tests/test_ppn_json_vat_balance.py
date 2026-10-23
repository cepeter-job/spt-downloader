"""The final normal-VAT balance may be overwritten after its stored patch.

Public source: percentages restored at 174606/174744; final onChangeBasedOnType
at 182845; subscriptions at 150304/150480; total->balance at 184344; normal-VAT
balance formula near 188660. Unsupported lifecycle paths must not be guessed.
"""
import json

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from coretax_masa_bindings import project_ppn_amount


def raw_source(*, goods=0, services=0, basis=None):
    return {
        'BasedOnType': basis, 'InputTaxPercentageGoods': goods, 'InputTaxPercentageServices': services,
        'OutputTaxMustBeSelfCollected': {'VAT': 100},
        'VATIsDepositedInAdvance': {'VAT': 12},
        'InputTaxCanBeCalculated': {'VAT': 30},
        'VATCollectedByVATCollector': {'VAT': 3},
        'VATUnderOrOverPaid': {'VAT': 999},
        'DomesticDeliveriesUsingOtherValue': {'VAT': 100},
        'DomesticDeliveriesToTourist': {'VAT': 0},
        'DomesticDeliveriesOtherThanOtherValue': {'VAT': 0},
        'DomesticDeliveriesSelfCollected': {'VAT': 0},
        'ImportOfTaxableGoods': {'VAT': 30},
        'DomesticTaxableGoodsUsingOtherValueTaxBase': {'VAT': 0},
        'DomesticTaxableGoodsWithInvoiceCode01': {'VAT': 0},
        'DomesticTaxableGoodsWithInvoiceCode02': {'VAT': 0},
        'CarryForwardOfInputTax': {'VAT': 0},
        'ResultsOfTheRecalculation': {'VAT': 0},
    }


def source(**options):
    return _corporate_json(json.dumps(raw_source(**options)))


@pytest.mark.parametrize('goods,services', [(0, 0), (90, 5), (None, None)])
def test_late_percentage_change_proves_balance_recalculation_without_using_stored_balance(goods, services):
    result = project_ppn_amount(source(goods=goods, services=services), 'VATIsUnderOrOverPaid', model='AMENDMENT')
    assert result['value'] == '55'
    paths = [entry['path'] for entry in result['provenance']]
    assert ['BasedOnType'] in paths
    assert ['InputTaxPercentageGoods'] in paths and ['InputTaxPercentageServices'] in paths
    assert ['OutputTaxMustBeSelfCollected', 'VAT'] in paths
    assert ['VATIsDepositedInAdvance', 'VAT'] in paths
    assert ['InputTaxCanBeCalculated', 'VAT'] in paths
    assert ['VATCollectedByVATCollector', 'VAT'] in paths
    assert ['VATUnderOrOverPaid', 'VAT'] not in paths


def test_final_balance_uses_floor_not_truncation_for_negative_fraction():
    # Only a directly mapped deposit is fractional. The two summed operands
    # reconcile to their integral component reductions before final floor.
    data = source()
    data['OutputTaxMustBeSelfCollected']['VAT'] = _corporate_json('10')
    data['DomesticDeliveriesUsingOtherValue']['VAT'] = _corporate_json('10')
    data['InputTaxCanBeCalculated']['VAT'] = _corporate_json('10')
    data['ImportOfTaxableGoods']['VAT'] = _corporate_json('10')
    data['VATIsDepositedInAdvance']['VAT'] = _corporate_json('1.5')
    data['VATCollectedByVATCollector']['VAT'] = _corporate_json('0')
    result = project_ppn_amount(data, 'VATIsUnderOrOverPaid', model='AMENDMENT')
    assert result['value'] == '-2'


def test_unchanged_percentages_do_not_prove_the_reactive_lifecycle():
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(source(goods=90, services=0), 'VATIsUnderOrOverPaid', model='AMENDMENT')


def test_unbound_basis_profile_is_not_used_to_guess_final_balance():
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(source(basis='UNREVIEWED_BASIS'), 'VATIsUnderOrOverPaid', model='AMENDMENT')


@pytest.mark.parametrize('field', ['DomesticDeliveriesUsingOtherValue', 'DomesticDeliveriesToTourist',
    'DomesticDeliveriesOtherThanOtherValue', 'DomesticDeliveriesSelfCollected',
    'ImportOfTaxableGoods', 'DomesticTaxableGoodsUsingOtherValueTaxBase',
    'DomesticTaxableGoodsWithInvoiceCode01', 'DomesticTaxableGoodsWithInvoiceCode02',
    'CarryForwardOfInputTax', 'ResultsOfTheRecalculation'])
def test_missing_reactive_component_cannot_prove_stored_operands_remain_final(field):
    data = source()
    del data[field]
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(data, 'VATIsUnderOrOverPaid', model='AMENDMENT')


@pytest.mark.parametrize('field', ['DomesticDeliveriesUsingOtherValue', 'ImportOfTaxableGoods'])
def test_stale_reported_balance_operands_do_not_override_later_component_sums(field):
    data = source()
    data[field]['VAT'] = _corporate_json('7')
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(data, 'VATIsUnderOrOverPaid', model='AMENDMENT')


def test_unsafe_component_partial_sum_is_not_hidden_by_safe_final_reported_total():
    data = source()
    for field, value in zip(('DomesticDeliveriesUsingOtherValue', 'DomesticDeliveriesToTourist',
                             'DomesticDeliveriesOtherThanOtherValue', 'DomesticDeliveriesSelfCollected'),
                            ('999999999999999', '1', '-1', '0')):
        data[field]['VAT'] = _corporate_json(value)
    data['OutputTaxMustBeSelfCollected']['VAT'] = _corporate_json('999999999999999')
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(data, 'VATIsUnderOrOverPaid', model='AMENDMENT')
