"""Submitted PPN totals restored after early reactive component calculations."""
import json
from copy import deepcopy

import pytest

from coretax_json import _corporate_json
from coretax_masa_bindings import project_ppn_amount

# Public mapResponseToFormData offsets 170727–173946. Tests intentionally
# distinguish the restored total from both its component fields and a UI alias.
TOTALS = [
    ('SumDeliveryOfTaxableGoodsSellingPrice', 'DeliveryOfTaxableGoodsSubjectToVAT', 'SellingPrice', ''),
    ('SumDeliveryOfTaxableGoodsVAT', 'DeliveryOfTaxableGoodsSubjectToVAT', 'VAT', ''),
    ('SumDeliveryOfTaxableGoodsSTLG', 'DeliveryOfTaxableGoodsSubjectToVAT', 'SalesTaxLuxuryGoods', ''),
    ('TotalDeliveryGoodsAndServices', 'TotalDeliveryOfGoodsAndServices', 'SellingPrice', '0'),
    ('AmountCalculatedInputTaxSellingPrice', 'AmountOfInputTaxCalculated', 'SellingPrice', ''),
    ('AmountCalculatedInputTaxVAT', 'AmountOfInputTaxCalculated', 'VAT', ''),
    ('TotalAcquisition', 'TotalAcquisition', 'SellingPrice', ''),
    ('SelfCollectedOutputTax', 'OutputTaxMustBeSelfCollected', 'VAT', ''),
    ('CalculatedInputTax', 'InputTaxCanBeCalculated', 'VAT', ''),
]


@pytest.mark.parametrize('control,root,leaf,blank', TOTALS)
def test_submitted_total_preserves_stored_source_instead_of_recalculating_components(control, root, leaf, blank):
    data = {control: 999, 'A1FormListOfExportTaxableGoodsOrServices': {'Total': 987},
            'DomesticDeliveriesSelfCollected': {'SellingPrice': 888, 'VAT': 777},
            root: {leaf: 1234}}
    source = _corporate_json(json.dumps(data))
    before = deepcopy(source)
    result = project_ppn_amount(source, control, model='AMENDMENT')
    assert result['value'] == '1.234'
    assert [entry['path'] for entry in result['provenance']] == [[root, leaf]]
    assert source == before


@pytest.mark.parametrize('control,root,leaf,blank', TOTALS)
def test_submitted_total_null_defaults_match_the_exact_source_binding(control, root, leaf, blank):
    source = _corporate_json(json.dumps({root: {leaf: None}}))
    result = project_ppn_amount(source, control, model='AMENDMENT')
    assert result['value'] == blank
    assert result['provenance'][0]['path'] == [root, leaf]
    assert result['provenance'][0]['type'] == 'null'
