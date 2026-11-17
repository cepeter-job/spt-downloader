"""Source-rendered populated L4; synthetic, hosted-runner-only contracts."""
from copy import deepcopy
import json

import pytest

import coretax_corporate_projection as projection
from coretax_json import _UnsupportedMetadata, _corporate_json
from test_corporate_l4_projection import ROW, B_ROW, root, footer

KINDS = ('TAX_OBJECT_CODE', 'INCOME_EXCLUDED_FROM_TAX_FOR_CIT')
LABELS = {KINDS[0]: {ROW['TaxObjectCode']: 'SYNTHETIC ACTIVE TAX OBJECT'},
          KINDS[1]: {B_ROW['TypeOfIncome']: 'SYNTHETIC EXCLUDED INCOME'}}


def populated(*, a=None, b=None, form_changes=None, footer_changes=None, labels=None):
    a = [deepcopy(ROW), deepcopy(ROW)] if a is None else a
    b = [deepcopy(B_ROW), deepcopy(B_ROW)] if b is None else b
    form = root(**{'TotalTaxBase': 2000, 'TotalFinalIncomeTaxPayable': 40,
                   'TotalGrossIncome': 1000, 'ListOfIncomeExcludedFromIncomeTax': b,
                   **(form_changes or {})})
    foot = footer(**{'TaxBase': 2000, 'IncomeTax': 40, **(footer_changes or {})})
    return projection.project_l4(_corporate_json(json.dumps(form)),
        footer=_corporate_json(json.dumps(foot)),
        pages=[{'offset': 0, 'rows': 10, 'total': len(a), 'data': _corporate_json(json.dumps(a))}],
        tax_type='ICT_RCIT', locale='id-ID', labels=deepcopy(LABELS if labels is None else labels))


def test_populated_both_blocks_keep_labels_original_values_duplicates_and_captured_footer():
    result = populated()
    a, b = result['tables']
    assert a['rows'][:2] == [[ROW['TIN'], ROW['Name'], ROW['TaxObjectCode'],
        LABELS[KINDS[0]][ROW['TaxObjectCode']], '1.000', '2,00', '20']] * 2
    assert b['rows'][:2] == [['1', '1', LABELS[KINDS[1]]['1'], B_ROW['IncomeSource'], '500,00'],
                            ['2', '1', LABELS[KINDS[1]]['1'], B_ROW['IncomeSource'], '500,00']]
    assert a['footer'] == [['TOTAL', '2.000', '', '40']]
    assert b['footer'] == [['', 'JUMLAH', '1.000']]
    assert all(t['complete'] and t['body_row_count'] == t['source_total'] == 2 for t in (a, b))
    assert ROW['TaxObject'] not in str(result['tables'])
    evidence = result['provenance']
    assert any(e['path'] == ['Data', 1, 'TaxObject'] and e['value'] == ROW['TaxObject']
               and e['source'] == 'grid' and e['rule'] == 'original-unused-row-metadata' for e in evidence)
    assert any(e['path'] == [projection.L4_ROOT, 'ListOfIncomeExcludedFromIncomeTax', 1, 'GrossIncome']
               and e['source'] == 'current' and e['value'] == '500' for e in evidence)
    assert any(e['path'] == ['TaxBase'] and e['source'] == 'footer' and e['value'] == '2000'
               for e in evidence)


def test_self_paid_tax_does_not_apply_editor_tax_formula_or_borrow_footer_from_rows():
    row = {**ROW, 'TaxBase': 0, 'TaxRate': 0, 'IncomeTax': 73, 'IncomeTaxUsd': 73}
    # The active parent inserts this profile; the submitted renderer does not
    # recalculate IncomeTax as base*rate. Server footer is its own captured source.
    result = populated(a=[row], b=[], form_changes={'TotalTaxBase': 0,
        'TotalFinalIncomeTaxPayable': 73, 'TotalFinalIncomeTaxPayableUsd': 73, 'TotalGrossIncome': 0},
        footer_changes={'TaxBase': 0, 'IncomeTax': 73, 'IncomeTaxUsd': 73})
    assert result['tables'][0]['rows'][0][-3:] == ['0', '0,00', '73']
    assert result['tables'][0]['footer'] == [['TOTAL', '0', '', '73']]
    assert result['tables'][1]['rows'] == [['', 'JUMLAH', '0']]


@pytest.mark.parametrize('kind', KINDS)
def test_no_code_or_saved_text_substitutes_for_missing_catalog_label(kind):
    labels = deepcopy(LABELS)
    labels[kind] = {}
    with pytest.raises(_UnsupportedMetadata, match='labels'):
        populated(labels=labels)


@pytest.mark.parametrize('field', ['TaxBase', 'TaxRate', 'IncomeTax'])
def test_actual_submitted_checkisstring_null_branch_is_blank_not_numeric_zero(field):
    result = populated(a=[{**ROW, field: None}])
    column = {'TaxBase': 4, 'TaxRate': 5, 'IncomeTax': 6}[field]
    assert result['tables'][0]['rows'][0][column] == ''
    assert any(e['path'] == ['Data', 0, field] and e['type'] == 'null' for e in result['provenance'])


def test_rate_is_percentage_points_and_b_number2_is_not_integer_or_scaled():
    result = populated(a=[{**ROW, 'TaxRate': 4.38}], b=[{**B_ROW, 'GrossIncome': 500.25}] * 2,
                       form_changes={'TotalGrossIncome': 1000.5})
    assert result['tables'][0]['rows'][0][5] == '4,38'
    assert result['tables'][1]['rows'][0][-1] == '500,25'
    assert result['tables'][1]['footer'] == [['', 'JUMLAH', '1.000,5']]


@pytest.mark.parametrize('field,value', [('TaxBase', '1000'), ('TaxRate', '2'), ('TaxBase', True),
    ('IncomeTax', False), ('TaxRate', 4.381), ('TaxBase', 0.5), ('IncomeTax', 0.5),
    ('TaxBase', 1000000000000000), ('TaxRate', 101), ('TaxRate', -1)])
def test_unproved_a_numeric_representations_refuse(field, value):
    with pytest.raises(_UnsupportedMetadata):
        populated(a=[{**ROW, field: value}])


@pytest.mark.parametrize('value', ['500', True, 0.1, 0.001, 1000000000000000])
def test_unproved_b_sum_precision_and_numeric_types_refuse(value):
    with pytest.raises(_UnsupportedMetadata):
        populated(b=[{**B_ROW, 'GrossIncome': value}], form_changes={'TotalGrossIncome': value})


@pytest.mark.parametrize('field', ['TIN', 'Name', 'TaxObjectCode'])
def test_numeric_tokens_cannot_masquerade_as_literal_a_text(field):
    with pytest.raises(_UnsupportedMetadata):
        populated(a=[{**ROW, field: 12}])


@pytest.mark.parametrize('field', ['TaxObjectCode', 'TypeOfIncome', 'IncomeSource'])
def test_numeric_tokens_cannot_masquerade_as_literal_b_text(field):
    with pytest.raises(_UnsupportedMetadata):
        populated(b=[{**B_ROW, field: 12}])


@pytest.mark.parametrize('block', ['a', 'b'])
def test_unknown_missing_or_non_object_rows_refuse_without_modification(block):
    for row in (None, [], {'Unreviewed': 0}):
        values = {block: [row]}
        before = deepcopy(values)
        with pytest.raises(_UnsupportedMetadata):
            populated(**values)
        assert values == before


def test_b_total_must_equal_exact_original_reduce_and_captured_stored_total():
    with pytest.raises(_UnsupportedMetadata, match='total'):
        populated(form_changes={'TotalGrossIncome': 999})


def test_multiple_pages_retain_every_duplicate_and_page_local_original_coordinate():
    form = _corporate_json(json.dumps(root()))
    rows = _corporate_json(json.dumps([ROW] * 12))
    result = projection.project_l4(form, footer=_corporate_json(json.dumps(footer())),
        pages=[{'offset': 0, 'rows': 10, 'total': 12, 'data': rows[:10]},
               {'offset': 10, 'rows': 10, 'total': 12, 'data': rows[10:]}],
        tax_type='ICT_RCIT', locale='id-ID', labels=LABELS)
    assert result['tables'][0]['body_row_count'] == 12
    assert result['tables'][0]['rows'][0] == result['tables'][0]['rows'][10]
    assert any(e['page_index'] == 1 and e['path'] == ['Data', 0, 'TIN']
               and e.get('destination', {}).get('row') == 10 for e in result['provenance'])
