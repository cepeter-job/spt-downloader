"""Submitted NORMAL PPN leaf amounts from the pinned public form bindings.

These fixtures deliberately distinguish sibling columns and same-name decoys.
Calculated totals, deemed-VAT percentages and claim-derived fields are excluded.
"""
from copy import deepcopy

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata
from test_masa_json_ppn import project

# Independently transcribed from mapResponseToFormData, reviewed against later
# setters/subscriptions. Last column is the displayed nullish value, not a value
# injected into the JSON evidence. The public asset hash is pinned in the spec.
DIRECT = [
    ('DomesticDeliveriesUsingOtherValueTaxBaseSellingPrice', 'DomesticDeliveriesUsingOtherValue', 'SellingPrice', '0'),
    ('DomesticDeliveriesUsingOtherValueTaxBaseOtherTaxBase', 'DomesticDeliveriesUsingOtherValue', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesUsingOtherValueTaxBaseVAT', 'DomesticDeliveriesUsingOtherValue', 'VAT', '0'),
    ('DomesticDeliveriesUsingTouristSellingPrice', 'DomesticDeliveriesToTourist', 'SellingPrice', '0'),
    ('DomesticDeliveriesUsingTouristOtherTaxBase', 'DomesticDeliveriesToTourist', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesUsingTouristVAT', 'DomesticDeliveriesToTourist', 'VAT', '0'),
    ('DomesticDeliveriesUsingTouristSTLG', 'DomesticDeliveriesToTourist', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticDeliveriesOtherThanWithOtherValueTaxBaseSellingPrice', 'DomesticDeliveriesOtherThanOtherValue', 'SellingPrice', '0'),
    ('DomesticDeliveriesOtherThanWithOtherValueTaxBaseVAT', 'DomesticDeliveriesOtherThanOtherValue', 'VAT', '0'),
    ('DomesticDeliveriesOtherThanWithOtherValueTaxBaseSTLG', 'DomesticDeliveriesOtherThanOtherValue', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticDeliveriesMustBeSelfCollectedSellingPrice', 'DomesticDeliveriesSelfCollected', 'SellingPrice', '0'),
    ('DomesticDeliveriesMustBeSelfCollectedOtherTaxBase', 'DomesticDeliveriesSelfCollected', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesMustBeSelfCollectedVAT', 'DomesticDeliveriesSelfCollected', 'VAT', '0'),
    ('DomesticDeliveriesMustBeSelfCollectedSTLG', 'DomesticDeliveriesSelfCollected', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticDeliveriesCollectedByVATCollectorSellingPrice', 'DomesticDeliveriesCollectedByVATCollector', 'SellingPrice', '0'),
    ('DomesticDeliveriesCollectedByVATCollectorOtherTaxBase', 'DomesticDeliveriesCollectedByVATCollector', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesCollectedByVATCollectorVAT', 'DomesticDeliveriesCollectedByVATCollector', 'VAT', '0'),
    ('DomesticDeliveriesCollectedByVATCollectorSTLG', 'DomesticDeliveriesCollectedByVATCollector', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticDeliveriesUncollectedVATFacilitiesSellingPrice', 'DomesticDeliveriesUncollectedVAT', 'SellingPrice', '0'),
    ('DomesticDeliveriesUncollectedVATFacilitiesOtherTaxBase', 'DomesticDeliveriesUncollectedVAT', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesUncollectedVATFacilitiesVAT', 'DomesticDeliveriesUncollectedVAT', 'VAT', '0'),
    ('DomesticDeliveriesUncollectedVATFacilitiesSTLG', 'DomesticDeliveriesUncollectedVAT', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticDeliveriesExemptedVATFacilitiesSellingPrice', 'DomesticDeliveriesExemptedVAT', 'SellingPrice', '0'),
    ('DomesticDeliveriesExemptedVATFacilitiesOtherTaxBase', 'DomesticDeliveriesExemptedVAT', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesExemptedVATFacilitiesVAT', 'DomesticDeliveriesExemptedVAT', 'VAT', '0'),
    ('DomesticDeliveriesExemptedVATFacilitiesSTLG', 'DomesticDeliveriesExemptedVAT', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticDeliveriesVATFacilitiesSellingPrice', 'DomesticDeliveriesVAT', 'SellingPrice', '0'),
    ('DomesticDeliveriesVATFacilitiesOtherTaxBase', 'DomesticDeliveriesVAT', 'OtherTaxBase', '0'),
    ('DomesticDeliveriesVATFacilitiesVAT', 'DomesticDeliveriesVAT', 'VAT', '0'),
    ('DomesticDeliveriesVATFacilitiesSTLG', 'DomesticDeliveriesVAT', 'SalesTaxLuxuryGoods', '0'),
    ('DeliveryOfGoodsNoVATPayable', 'DeliveriesOfGoodsNoVAT', 'SellingPrice', '0'),
    ('ImportOfTaxableGoodsFromOusideCustomsAreaVAT', 'ImportOfTaxableGoods', 'VAT', '0'),
    ('ImportOfTaxableGoodsFromOusideCustomsAreaSTLG', 'ImportOfTaxableGoods', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticTaxableCreditedUsingOtherValueTaxBaseSellingPrice', 'DomesticTaxableGoodsUsingOtherValueTaxBase', 'SellingPrice', '0'),
    ('DomesticTaxableCreditedUsingOtherValueTaxBaseOtherTaxBase', 'DomesticTaxableGoodsUsingOtherValueTaxBase', 'OtherTaxBase', '0'),
    ('DomesticTaxableCreditedUsingOtherValueTaxBaseVAT', 'DomesticTaxableGoodsUsingOtherValueTaxBase', 'VAT', '0'),
    ('DomesticTaxableCreditedUsingOtherValueTaxBaseSTLG', 'DomesticTaxableGoodsUsingOtherValueTaxBase', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticTaxableWhichTaxInputcanBeCreditedWithSellingPrice', 'DomesticTaxableGoodsWithInvoiceCode01', 'SellingPrice', '0'),
    ('DomesticTaxableWhichTaxInputcanBeCreditedWithVAT', 'DomesticTaxableGoodsWithInvoiceCode01', 'VAT', '0'),
    ('DomesticTaxableWhichTaxInputcanBeCreditedWithSTLG', 'DomesticTaxableGoodsWithInvoiceCode01', 'SalesTaxLuxuryGoods', '0'),
    ('DomesticTaxableFromWhichTaxInputcanBeCreditedWithSellingPrice', 'DomesticTaxableGoodsWithInvoiceCode02', 'SellingPrice', '0'),
    ('DomesticTaxableFromWhichTaxInputcanBeCreditedWithOtherTaxBase', 'DomesticTaxableGoodsWithInvoiceCode02', 'OtherTaxBase', '0'),
    ('DomesticTaxableFromWhichTaxInputcanBeCreditedWithVAT', 'DomesticTaxableGoodsWithInvoiceCode02', 'VAT', '0'),
    ('DomesticTaxableFromWhichTaxInputcanBeCreditedWithSTLG', 'DomesticTaxableGoodsWithInvoiceCode02', 'SalesTaxLuxuryGoods', '0'),
    ('ResultRecalculationCreditedTaxInput', 'ResultsOfTheRecalculation', 'VAT', ''),
    ('ImportOrAcquisitionsWithFacilitiesSellingPrice', 'ImportsOfUncreditedInput', 'SellingPrice', '0'),
    ('ImportOrAcquisitionsWithFacilitiesOtherTaxBase', 'ImportsOfUncreditedInput', 'OtherTaxBase', '0'),
    ('ImportOrAcquisitionsWithFacilitiesVAT', 'ImportsOfUncreditedInput', 'VAT', '0'),
    ('ImportOrAcquisitionsWithFacilitiesSTLG', 'ImportsOfUncreditedInput', 'SalesTaxLuxuryGoods', '0'),
    ('ImportOrAcquisitionsThatNotVATPayable', 'ImportsOfOtherTaxableGoods', 'SellingPrice', '0'),
    ('DepositedVATSAmePeriod', 'VATIsDepositedInAdvance', 'VAT', ''),
    ('OverPaidVATCollectedByVATCollector', 'VATCollectedByVATCollector', 'VAT', '0'),
    ('VATIsUnderOrOverpaidOnPrevious', 'VATUnderOrOverPaidOnPrevious', 'VAT', ''),
    ('VATPayableSellingPrice', 'VATPayable', 'SellingPrice', '0'),
    ('VATPayableVAT', 'VATPayable', 'VAT', ''),
    ('STLGCollectedByVATCollectorOverpaid', 'STLGCollectedByVATCollector', 'SalesTaxLuxuryGoods', '0'),
    ('TotalVATandSTLGCollectedSellingPrice', 'TotalVATAndSTLGCollected', 'SellingPrice', ''),
    ('TotalVATandSTLGCollectedOtherTaxBase', 'TotalVATAndSTLGCollected', 'OtherTaxBase', ''),
    ('TotalVATandSTLGCollectedVAT', 'TotalVATAndSTLGCollected', 'VAT', ''),
    ('TotalVATandSTLGCollectedSTLG', 'TotalVATAndSTLGCollected', 'SalesTaxLuxuryGoods', ''),
]


@pytest.mark.parametrize('control,root,leaf,nullish', DIRECT)
@pytest.mark.parametrize('raw,expected', [('1234.5', '1.235'), ('-1234.5', '-1.235'), ('0', '0')])
def test_direct_amount_uses_exact_response_path_not_control_alias_or_sibling(control, root, leaf, nullish, raw, expected):
    form = {control: _corporate_json('999'), root: {
        'SellingPrice': _corporate_json('701'), 'OtherTaxBase': _corporate_json('702'),
        'VAT': _corporate_json('703'), 'SalesTaxLuxuryGoods': _corporate_json('704')}}
    form[root][leaf] = _corporate_json(raw)
    before = deepcopy(form)
    result = project(form, control)
    assert result['value'] == expected
    assert result['provenance'] == [{'path': [root, leaf], 'type': 'number', 'value': raw}]
    assert form == before


@pytest.mark.parametrize('control,root,leaf,nullish', DIRECT)
@pytest.mark.parametrize('shape', ['null_leaf', 'missing_leaf', 'null_parent'])
def test_direct_amount_keeps_null_and_missing_evidence_even_when_display_is_zero(control, root, leaf, nullish, shape):
    form = {root: {leaf: None}} if shape == 'null_leaf' else {root: {} if shape == 'missing_leaf' else None}
    result = project(form, control)
    assert result['value'] == nullish
    if shape == 'null_parent':
        assert result['provenance'] == [{'path': [root], 'type': 'null', 'value': None,
                                        'requested_path': [root, leaf]}]
    else:
        assert result['provenance'] == [{'path': [root, leaf], 'type': 'missing' if shape == 'missing_leaf' else 'null', 'value': None}]


@pytest.mark.parametrize('control,root,leaf,unused', [
    item for item in DIRECT if item[0].startswith(('DomesticDeliveriesMustBeSelfCollected', 'DomesticDeliveriesVATFacilities'))
    or item[0] == 'DeliveryOfGoodsNoVATPayable'
])
def test_submitted_values_are_not_replaced_with_draft_only_attachment_totals(control, root, leaf, unused):
    form = {root: {leaf: _corporate_json('123')},
            'IA6FormListDomesticDeliveriesOfTaxableGoodsSelfCollected': {'TotalSellingPrice': _corporate_json('901'), 'TotalOtherTaxBase': _corporate_json('902'), 'TotalVAT': _corporate_json('903'), 'TotalSTLG': _corporate_json('904')},
            'IA9FormListDomesticDeliveriesOfTaxableGoodsFacilities': {'TotalSellingPrice': _corporate_json('801'), 'TotalOtherTaxBase': _corporate_json('802'), 'TotalVAT': _corporate_json('803'), 'TotalSTLG': _corporate_json('804')},
            'IBFormListDeliveriesOfGoodsWithNoVATPayable': {'TotalSellingPrice': _corporate_json('701')}}
    assert project(form, control)['value'] == '123'


@pytest.mark.parametrize('control', [
    'TotalVATandSTLGCollectedByOtherPartiesSellingPrice',
    'TotalVATandSTLGCollectedByOtherPartiesOtherTaxBase',
    'TotalVATandSTLGCollectedByOtherPartiesVAT',
    'TotalVATandSTLGCollectedByOtherPartiesSTLG',
])
def test_lc_callback_totals_cannot_be_guessed_from_induk_without_bound_lc_evidence(control):
    # onCallbackForm('LCForm', ...) replaces these after the initial mapping.
    form = _corporate_json('''{"TotalVATAndSTLGCollectedByOtherParties":
        {"SellingPrice":999,"OtherTaxBase":888,"VAT":777,"SalesTaxLuxuryGoods":666}}''')
    with pytest.raises(_UnsupportedMetadata):
        project(form, control)


def test_unknown_field_still_rejected_instead_of_guessing_after_expansion():
    with pytest.raises(_UnsupportedMetadata):
        project({'DomesticDeliveriesToTourist': {'SellingPrice': _corporate_json('1')}}, 'DomesticDeliveriesTouristSellingPrice')
