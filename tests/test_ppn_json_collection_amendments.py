"""VII/VIII final amendment bindings from public source and LC callback."""
import hashlib
import json

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from coretax_masa_bindings import project_ppn_amount
from masa_projection_fixture import field
from test_ppn_json_amendment import amend_case, decode, reseal

COLUMNS = [('SellingPrice', 'SellingPrice', 'TaxBase'), ('OtherTaxBase', 'OtherTaxBase', 'OtherTaxBase'),
           ('VAT', 'VAT', 'VAT'), ('STLG', 'SalesTaxLuxuryGoods', 'STLG')]


@pytest.mark.parametrize('suffix,leaf,footer_key', COLUMNS)
@pytest.mark.parametrize('prefix,root,default', [
    ('VATandSTLGUnderOverpaidOnAmmendedVAT', 'VATAndSTLGUnderOrOverPaidOnAmmended', ''),
    ('VATandSTLGUnderOverpaidDueAmmendment', 'VATAndSTLGUnderOfOverPaidDueToAmmendment', '0'),
    ('VATandSTLGCollectedByOtherPartiesUnderOverpaidOnAmmendedVAT', 'VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended', '0'),
])
def test_final_stored_prior_and_vii_due_bind_exact_literals(suffix, leaf, footer_key, prefix, root, default):
    data = {'A1FormListOfExportTaxableGoodsOrServices': {'ReturnSheetModel': 'AMENDMENT'},
            root: {leaf: 1234}, 'TotalVATAndSTLGCollected': {leaf: 888}}
    result = project_ppn_amount(_corporate_json(json.dumps(data)), prefix + suffix, model='AMENDMENT')
    assert result['value'] == '1.234'
    assert any(p['path'] == [root, leaf] for p in result['provenance'])
    assert not any(p['path'] == ['TotalVATAndSTLGCollected', leaf] for p in result['provenance'])
    data[root][leaf] = None
    result = project_ppn_amount(_corporate_json(json.dumps(data)), prefix + suffix, model='AMENDMENT')
    assert result['value'] == default
    assert any(p['path'] == [root, leaf] and p['type'] == 'null' for p in result['provenance'])


@pytest.mark.parametrize('suffix,leaf,footer_key', COLUMNS)
def test_viii_due_uses_final_independent_footer_and_preserves_both_packet_provenances(suffix, leaf, footer_key):
    case = amend_case()
    envelope = json.loads(case['packets'][0]['body'])
    data = json.loads(envelope['Payload']['FormData'])
    data['VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended'] = {leaf: 3}
    data['TotalVATAndSTLGCollectedByOtherParties'] = {leaf: 999}
    envelope['Payload']['FormData'] = json.dumps(data)
    reseal(case, envelope)
    footer = next(p for p in case['packets'] if p['context']['url'].endswith('/lc-grid/footer'))
    body = json.loads(footer['body'])
    body['Payload'][footer_key] = 10
    raw = json.dumps(body).encode()
    footer['body'] = raw
    footer['context'].update(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    control = 'VATandSTLGCollectedByOtherPartiesUnderOverpaidDueAmmendment' + suffix
    case['forms'][0]['fields'].append(field(control, 'Synthetic amendment difference'))
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    values = {f['field']: f['value'] for f in result['sections'][0]['fields']}
    assert values[control] == '7'
    evidence = [p for p in result['provenance']['bindings'] if p.get('destination', {}).get('field') == control]
    assert any(p['container_path'] == ['Payload'] and p['path'] == [footer_key] for p in evidence)
    assert any(p['container_path'] == ['Payload', 'FormData'] and
               p['path'] == ['VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended', leaf] for p in evidence)
    assert all(p['projection_rule'] == 'floor_lc_footer_minus_previous' for p in evidence)


def test_merged_distinct_subscription_cannot_prove_an_equal_prior_footer_overwrite():
    data = _corporate_json('{"A1FormListOfExportTaxableGoodsOrServices":{"ReturnSheetModel":"AMENDMENT"},"VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended":{"VAT":5},"TotalVATAndSTLGCollectedByOtherParties":{"VAT":99}}')
    footer = _corporate_json('{"VAT":5}')
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(data, 'VATandSTLGCollectedByOtherPartiesUnderOverpaidDueAmmendmentVAT', model='AMENDMENT', lc_footer=footer)


def test_equal_footer_prior_and_initial_total_prove_zero_despite_distinct_suppression():
    data = _corporate_json('{"A1FormListOfExportTaxableGoodsOrServices":{"ReturnSheetModel":"AMENDMENT"},"VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended":{"VAT":5},"TotalVATAndSTLGCollectedByOtherParties":{"VAT":5}}')
    result = project_ppn_amount(data, 'VATandSTLGCollectedByOtherPartiesUnderOverpaidDueAmmendmentVAT',
                               model='AMENDMENT', lc_footer=_corporate_json('{"VAT":5}'))
    assert result['value'] == '0'
    assert any(p['path'] == ['TotalVATAndSTLGCollectedByOtherParties', 'VAT'] for p in result['provenance'])


def test_footer_before_a_later_primary_patch_cannot_prove_final_viii_difference():
    case = amend_case()
    primary = case['packets'].pop(0)
    sequence = max(p['context']['sequence'] for p in case['packets']) + 1
    primary['context']['sequence'] = sequence
    case['packets'].append(primary)
    case['forms'][0]['primary']['requests'][0]['sequences'] = [sequence]
    case['forms'][0]['fields'].append(field(
        'VATandSTLGCollectedByOtherPartiesUnderOverpaidDueAmmendmentVAT', 'Synthetic difference'))
    result = decode(case)
    assert result['eligible'] is False
    assert 'unverified_ppn_footer_lifecycle' in result['reason']


def test_nested_amendment_condition_is_not_inferred_from_outer_model():
    data = _corporate_json('{"A1FormListOfExportTaxableGoodsOrServices":{"ReturnSheetModel":"NORMAL"},"VATAndSTLGUnderOfOverPaidDueToAmmendment":{"VAT":123}}')
    with pytest.raises(_UnsupportedMetadata):
        project_ppn_amount(data, 'VATandSTLGUnderOverpaidDueAmmendmentVAT', model='AMENDMENT')
