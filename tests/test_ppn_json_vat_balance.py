"""The final normal-VAT balance may be overwritten after its stored patch.

Public source: percentages restored at 174606/174744; final onChangeBasedOnType
at 182845; subscriptions at 150304/150480; total->balance at 184344; normal-VAT
balance formula near 188660. Unsupported lifecycle paths must not be guessed.
"""
import json

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from coretax_masa_bindings import project_ppn_amount


def source(*, goods=0, services=0, basis=None):
    return _corporate_json(json.dumps({
        'BasedOnType': basis, 'InputTaxPercentageGoods': goods, 'InputTaxPercentageServices': services,
        'OutputTaxMustBeSelfCollected': {'VAT': 100},
        'VATIsDepositedInAdvance': {'VAT': 12},
        'InputTaxCanBeCalculated': {'VAT': 30},
        'VATCollectedByVATCollector': {'VAT': 3},
        'VATUnderOrOverPaid': {'VAT': 999},
    }))


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
    data = _corporate_json('{"BasedOnType":null,"InputTaxPercentageGoods":0,"InputTaxPercentageServices":0,"OutputTaxMustBeSelfCollected":{"VAT":10.2},"VATIsDepositedInAdvance":{"VAT":1.1},"InputTaxCanBeCalculated":{"VAT":10.5},"VATCollectedByVATCollector":{"VAT":0}}')
    result = project_ppn_amount(data, 'VATIsUnderOrOverPaid', model='AMENDMENT')
    assert result['value'] == '-2'


def test_unchanged_percentages_do_not_prove_the_reactive_lifecycle():
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(source(goods=90, services=0), 'VATIsUnderOrOverPaid', model='AMENDMENT')


def test_unbound_basis_profile_is_not_used_to_guess_final_balance():
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(source(basis='UNREVIEWED_BASIS'), 'VATIsUnderOrOverPaid', model='AMENDMENT')
