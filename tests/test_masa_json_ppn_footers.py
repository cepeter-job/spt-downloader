"""PPN footer values and C-to-Induk callbacks from the pinned public UI.

Grid rows are not summed: the UI binds these independently supplied totals.
"""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _corporate_json, _UnsupportedMetadata

ROOTS = {
    'A-1': 'A1FormListOfExportTaxableGoodsOrServices',
    'A-2': 'A2FormListOfOutputTaxesOnDomesticDeliveries',
    'B-1': 'B1FormListTaxesCreditedOnTheImportTaxableGoods',
    'B-2': 'B2FormListTaxesThatCanBeCreditedForDomesticTaxableGoods',
    'B-3': 'B3FormListOfInputTaxesUncredit',
}


def project(form_name, form, lc_footer=None):
    implementation = getattr(importlib.import_module('coretax_masa_bindings'), 'project_ppn_footer', None)
    assert callable(implementation), 'PPN footer projection is not implemented'
    return implementation(form_name, form, lc_footer=lc_footer)


def data():
    return _corporate_json('''{"Total":101,"TotalTaxBase":202,"TotalSellingPrice":303,
        "TotalOtherTaxBase":404,"TotalVAT":505,"TotalSTLG":606}''')


@pytest.mark.parametrize('name,expected,spans,fields', [
    ('A-1', ['TOTAL', '101', ''], [4,1,1], ['Total']),
    ('A-2', ['TOTAL', '202', '404', '505', '606', ''], [5,1,1,1,1,1], ['TotalTaxBase','TotalOtherTaxBase','TotalVAT','TotalSTLG']),
    ('B-1', ['TOTAL', '202', '505', '606', ''], [5,1,1,1,1], ['TotalTaxBase','TotalVAT','TotalSTLG']),
    ('B-2', ['TOTAL', '303', '404', '505', '606', ''], [5,1,1,1,1,1], ['TotalSellingPrice','TotalOtherTaxBase','TotalVAT','TotalSTLG']),
    ('B-3', ['TOTAL', '303', '404', '505', '606', ''], [5,1,1,1,1,1], ['TotalSellingPrice','TotalOtherTaxBase','TotalVAT','TotalSTLG']),
])
def test_footer_paths_and_spans_follow_each_component_not_similar_key_names(name, expected, spans, fields):
    form = {ROOTS[name]: data()}
    before = deepcopy(form)
    result = project(name, form)
    assert result['footer'] == [expected]
    assert result['footer_spans'] == [spans]
    assert [p['path'] for p in result['provenance']] == [[ROOTS[name], key] for key in fields]
    assert all(p['source'] == 'prefill_form' for p in result['provenance'])
    assert result['induk_values'] == {}
    assert form == before


@pytest.mark.parametrize('name', list(ROOTS))
@pytest.mark.parametrize('shape', ['null', 'missing'])
def test_b2_other_tax_base_is_blank_while_other_footer_nullish_values_display_zero(name, shape):
    source = {key: None for key in data()} if shape == 'null' else {}
    result = project(name, {ROOTS[name]: source})
    expected = {'A-1': ['TOTAL','0',''], 'A-2': ['TOTAL','0','0','0','0',''],
                'B-1': ['TOTAL','0','0','0',''], 'B-2': ['TOTAL','0','','0','0',''],
                'B-3': ['TOTAL','0','0','0','0','']}[name]
    assert result['footer'] == [expected]
    assert all(p['type'] == ('null' if shape == 'null' else 'missing') and p['value'] is None
               for p in result['provenance'])


def test_null_footer_parent_does_not_fabricate_explicit_child_nulls():
    result = project('B-2', {ROOTS['B-2']: None})
    assert result['footer'] == [['TOTAL','0','','0','0','']]
    assert all(p['path'] == [ROOTS['B-2']] and len(p['requested_path']) == 2
               for p in result['provenance'])


def test_lc_response_replaces_stored_induk_and_c_totals_without_mutating_sources():
    form = _corporate_json('''{"TotalVATAndSTLGCollectedByOtherParties":
        {"SellingPrice":999,"OtherTaxBase":998,"VAT":997,"SalesTaxLuxuryGoods":996},
        "CFormListOfVatAndStlgCollectedByOtherParties":
        {"TotalTaxBase":899,"TotalOtherTaxBase":898,"TotalVAT":897,"TotalSTLG":896}}''')
    footer = _corporate_json('{"TaxBase":1234.5,"OtherTaxBase":1000,"VAT":-2.5,"STLG":0}')
    before = deepcopy((form, footer))
    result = project('C', form, footer)
    assert result['footer'] == [['TOTAL','1.235','1.000','-3','0','']]
    assert result['footer_spans'] == [[9,1,1,1,1,1]]
    assert result['induk_values'] == {
        'TotalVATandSTLGCollectedByOtherPartiesSellingPrice': '1.235',
        'TotalVATandSTLGCollectedByOtherPartiesOtherTaxBase': '1.000',
        'TotalVATandSTLGCollectedByOtherPartiesVAT': '-3',
        'TotalVATandSTLGCollectedByOtherPartiesSTLG': '0',
    }
    assert [p['path'] for p in result['provenance']] == [['TaxBase'],['OtherTaxBase'],['VAT'],['STLG']]
    assert all(p['source'] == 'lc_footer' for p in result['provenance'])
    assert result['provenance'][0]['value'] == '1234.5'
    assert (form, footer) == before


@pytest.mark.parametrize('footer', [None, [], 'unbound'])
def test_c_requires_separate_footer_evidence_not_prefill_substitution(footer):
    with pytest.raises(_UnsupportedMetadata):
        project('C', {'CFormListOfVatAndStlgCollectedByOtherParties': data()}, footer)


@pytest.mark.parametrize('shape', ['null','missing'])
def test_lc_nullish_zero_callback_preserves_original_source_evidence(shape):
    footer = {'TaxBase': None, 'OtherTaxBase': None, 'VAT': None, 'STLG': None} if shape == 'null' else {}
    result = project('C', {}, footer)
    assert result['footer'] == [['TOTAL','0','0','0','0','']]
    assert set(result['induk_values'].values()) == {'0'}
    assert all(p['type'] == ('null' if shape == 'null' else 'missing') and p['value'] is None
               for p in result['provenance'])


@pytest.mark.parametrize('raw,expected', [('"001234.50"','1.235'), ('"-1234.50"','-1.235'), ('""','')])
def test_footer_numeric_strings_use_number_pipe_instead_of_body_string_passthrough(raw, expected):
    source = {'Total': _corporate_json(raw)}
    result = project('A-1', {ROOTS['A-1']: source})
    assert result['footer'] == [['TOTAL', expected, '']]
    assert result['provenance'][0]['type'] == 'string'
    assert result['provenance'][0]['value'] == source['Total']


@pytest.mark.parametrize('raw', ['true','[]','{}','"1_000"','"NaN"','"unknown"'])
def test_footer_cannot_coerce_invalid_source_into_an_amount(raw):
    with pytest.raises(_UnsupportedMetadata):
        project('A-1', {ROOTS['A-1']: {'Total': _corporate_json(raw)}})


@pytest.mark.parametrize('name,form', [('INVENTED', {}), ('A-1', []), ('B-2', {'B2FormListTaxesThatCanBeCreditedForDomesticTaxableGoods': 'invalid'})])
def test_unknown_footer_binding_or_parent_shape_stays_unsupported(name, form):
    with pytest.raises(_UnsupportedMetadata):
        project(name, form)
