"""Source-rendered populated L4; synthetic, hosted-runner-only contracts."""
from copy import deepcopy
import json

import pytest

import coretax_corporate_projection as projection
from coretax_json import _UnsupportedMetadata, _corporate_json
from test_corporate_l4_projection import A_HEADERS, ROW, B_ROW, root, footer

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
               and e['destination'] == {'table': projection.L4_FINAL_TABLE, 'footer': 0, 'column': 4}
               for e in evidence)
    assert any(e['path'] == [projection.L4_ROOT, 'TotalGrossIncome'] and e['source'] == 'current'
               and e['destination'] == {'table': projection.L4_EXCLUDED_TABLE, 'footer': 0, 'column': 4}
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


@pytest.mark.parametrize('values,expected', [([None], ''), ([None, None], '0'),
    ([None, 500.25], '500,25'), ([500.25, None], '500,25')])
def test_b_null_body_and_no_initializer_reduce_are_not_fabricated_zero_rows(values, expected):
    result = populated(b=[{**B_ROW, 'GrossIncome': amount} for amount in values],
        form_changes={'TotalGrossIncome': sum(amount or 0 for amount in values)})
    assert [row[-1] for row in result['tables'][1]['rows'][:-1]] == [
        '' if value is None else '500,25' for value in values]
    assert result['tables'][1]['footer'] == [['', 'JUMLAH', expected]]


def test_literal_null_text_and_reviewed_metadata_are_preserved_not_used_as_column_aliases():
    row = {**ROW, 'TIN': None, 'Name': None, 'TaxObject': None, 'RecordId': 'SYNTHETIC ROW',
           'IsManually': False, 'TableSource': 'TAXPAYER_ACCOUNTING', 'Action': None}
    result = populated(a=[row], b=[{**B_ROW, 'TaxObjectCode': None, 'IncomeSource': None}],
                       form_changes={'TotalGrossIncome': 500})
    assert result['tables'][0]['rows'][0][:2] == ['', '']
    assert result['tables'][1]['rows'][0][1:4] == ['', LABELS[KINDS[1]]['1'], '']
    assert any(e['path'] == ['Data', 0, 'IsManually'] and e['type'] == 'boolean'
               and e['value'] is False for e in result['provenance'])


@pytest.mark.parametrize('key,value', [('Index', None), ('Index', .5), ('IsManually', 1),
    ('Action', ''), ('TableSource', False), ('RecordId', 0), ('TaxObject', {})])
def test_malformed_nondisplayed_metadata_refuses_instead_of_disappearing(key, value):
    with pytest.raises(_UnsupportedMetadata):
        populated(a=[{**ROW, key: value}])


@pytest.mark.parametrize('key,value', [('TaxBaseUsd', 0), ('IncomeTaxUsd', 0.25),
    ('TaxBaseUsd', 62.08601963), ('IncomeTaxUsd', 12.41720393)])
def test_fractional_usd_row_metadata_projects_and_keeps_original_lexemes(key, value):
    # Non-displayed USD metadata legitimately carries up to eight decimal places
    # (exchange-rate conversion scale). It is validated, not rendered, and its
    # original lexeme must survive unchanged in provenance.
    result = populated(a=[{**ROW, key: value}])
    entry = next(e for e in result['provenance']
                 if e['path'] == ['Data', 0, key] and e['source'] == 'grid')
    assert entry['type'] == 'number' and entry['value'] == str(value)
    assert entry['rule'] == 'original-unused-row-metadata'


@pytest.mark.parametrize('key,value', [('TaxBaseUsd', -1), ('IncomeTaxUsd', -0.5),
    ('TaxBaseUsd', '-0'), ('IncomeTaxUsd', '12.123456789'),
    ('TaxBaseUsd', 'not-a-number')])
def test_fractional_usd_metadata_rejects_negative_signed_zero_overprecision_and_garbage(key, value):
    with pytest.raises(_UnsupportedMetadata):
        populated(a=[{**ROW, key: value}])


@pytest.mark.parametrize('key', ['TotalFinalIncomeTaxPayableUsd', 'TotalTaxBaseUsd'])
def test_fractional_usd_root_total_projects_and_keeps_original_lexemes(key):
    value = 12.41720393
    footer_key = 'IncomeTaxUsd' if key == 'TotalFinalIncomeTaxPayableUsd' else 'TaxBaseUsd'
    # Keep the footer USD at the same two-decimal rounded value so the root↔footer
    # reconciliation passes while the root lexeme keeps its full eight decimals.
    result = populated(form_changes={key: value}, footer_changes={footer_key: 12.42})
    entry = next(e for e in result['provenance']
                 if e['path'] == [projection.L4_ROOT, key] and e['source'] == 'current')
    assert entry['type'] == 'number' and entry['value'] == str(value)
    assert entry['rule'] == 'original-stored-total'


@pytest.mark.parametrize('key', ['TaxBaseUsd', 'IncomeTaxUsd'])
def test_fractional_usd_footer_reconciles_with_root_at_two_decimal_precision(key):
    # Footer USD carries full precision; root USD total is stored at two decimals.
    # Reconciliation compares at the root's proven two-decimal precision, so a
    # footer 12.41720393 and root 12.42 agree, while the original lexemes differ.
    form_changes = {'TotalFinalIncomeTaxPayableUsd': 12.42} if key == 'IncomeTaxUsd' else {}
    footer_changes = {key: 12.41720393} if key == 'IncomeTaxUsd' else {key: 62.08601963}
    result = populated(form_changes=form_changes, footer_changes=footer_changes)
    entry = next(e for e in result['provenance'] if e['path'] == [key] and e['source'] == 'footer')
    assert entry['value'] == str(footer_changes[key])


def test_fractional_usd_footer_root_disagreement_at_two_decimals_fails_closed():
    # Same integer/rounded part but different at the second decimal is a genuine
    # root/footer disagreement and must refuse even if both carry <=8 decimals.
    with pytest.raises(_UnsupportedMetadata, match='footer_total'):
        populated(form_changes={'TotalFinalIncomeTaxPayableUsd': 12.43},
                  footer_changes={'IncomeTaxUsd': 12.41720393})


def test_fractional_usd_overprecision_beyond_eight_decimals_fails_closed():
    with pytest.raises(_UnsupportedMetadata):
        populated(form_changes={'TotalFinalIncomeTaxPayableUsd': '12.123456789'},
                  footer_changes={'IncomeTaxUsd': '12.12345678'})


def test_withholding_slip_extra_row_metadata_is_evidenced_not_projected():
    # Withholding-slip-sourced A rows carry WithholdingDate and
    # WithholdingSlipsAggregateIdentifier. They are non-projected metadata: their
    # presence must not force a whole-record fallback, and they must be evidenced
    # with the original lexeme rather than dropped or rendered into a column.
    row = {**ROW, 'WithholdingDate': None,
           'WithholdingSlipsAggregateIdentifier': 'fad90500-5ee7-7a86-3ed2-450d8d54a8dd'}
    result = populated(a=[row])
    for key, expected in (('WithholdingDate', None),
                          ('WithholdingSlipsAggregateIdentifier', 'fad90500-5ee7-7a86-3ed2-450d8d54a8dd')):
        entry = next(e for e in result['provenance'] if e['path'] == ['Data', 0, key])
        assert entry['value'] == expected
        assert entry['rule'] == 'original-unused-row-metadata'
    # The rendered row keeps only the approved seven columns; no extra text leaks.
    assert len(result['tables'][0]['rows'][0]) == len(A_HEADERS)


def test_unknown_extra_row_metadata_still_fails_closed():
    # Only the approved withholding-slip fields are tolerated; any other extra
    # row key must still refuse the whole record.
    with pytest.raises(_UnsupportedMetadata):
        populated(a=[{**ROW, 'MysteryField': 'x'}])


@pytest.mark.parametrize('case', ['empty-pages', 'missing-data', 'gap', 'partial', 'count-change',
                                 'unsafe-count', 'extra-root', 'extra-footer', 'b-shape'])
def test_populated_collection_schema_and_pagination_stay_closed(case):
    form, foot = root(), footer()
    pages = [{'offset': 0, 'rows': 10, 'total': 1, 'data': [ROW]}]
    if case == 'empty-pages': pages = []
    elif case == 'missing-data': pages[0].pop('data')
    elif case == 'gap': pages[0]['offset'] = 10
    elif case == 'partial': pages[0]['total'] = 12
    elif case == 'count-change': pages += [{'offset': 1, 'rows': 10, 'total': 2, 'data': [ROW]}]
    elif case == 'unsafe-count': pages[0]['total'] = 10001
    elif case == 'extra-root': form['Unknown'] = None
    elif case == 'extra-footer': foot['Unknown'] = None
    else: form['ListOfIncomeExcludedFromIncomeTax'] = {}
    with pytest.raises(_UnsupportedMetadata):
        projection.project_l4(_corporate_json(json.dumps(form)), footer=_corporate_json(json.dumps(foot)),
            pages=[{**p, 'data': _corporate_json(json.dumps(p['data']))} if 'data' in p else p for p in pages],
            tax_type='ICT_RCIT', locale='id-ID', labels=LABELS)


@pytest.mark.parametrize('key', ['TaxBase', 'IncomeTax', 'TaxBaseUsd', 'IncomeTaxUsd'])
def test_footer_uses_original_values_and_corresponding_captured_root_ownership(key):
    changes = {'TotalTaxBaseUsd': 0} if key == 'TaxBaseUsd' else {}
    with pytest.raises(_UnsupportedMetadata, match='footer_total'):
        populated(form_changes=changes, footer_changes={key: 999})


def test_original_number_lexemes_remain_exact_and_signed_zero_is_unproved():
    form = _corporate_json(json.dumps(root()))
    rows = _corporate_json(json.dumps([ROW]))
    rows[0]['TaxRate'] = _corporate_json('4.3800e0')
    result = projection.project_l4(form, footer=_corporate_json(json.dumps(footer())),
        pages=[{'offset': 0, 'rows': 10, 'total': 1, 'data': rows}], tax_type='ICT_RCIT', locale='id-ID', labels=LABELS)
    assert result['tables'][0]['rows'][0][5] == '4,38'
    assert any(e['path'] == ['Data', 0, 'TaxRate'] and e['value'] == '4.3800e0' for e in result['provenance'])
    rows[0]['TaxBase'] = _corporate_json('-0')
    with pytest.raises(_UnsupportedMetadata):
        projection.project_l4(form, footer=_corporate_json(json.dumps(footer())),
            pages=[{'offset': 0, 'rows': 10, 'total': 1, 'data': rows}], tax_type='ICT_RCIT', locale='id-ID', labels=LABELS)


def test_optional_usd_root_absence_is_not_synthesized_as_an_original_zero():
    result = populated()
    assert any(e['path'] == [projection.L4_ROOT, 'TotalTaxBaseUsd'] and e['type'] == 'missing'
               and e['value'] is None for e in result['provenance'])
    result = populated(form_changes={'TotalTaxBaseUsd': 0})
    assert any(e['path'] == [projection.L4_ROOT, 'TotalTaxBaseUsd'] and e['type'] == 'number'
               and e['value'] == '0' for e in result['provenance'])
    with pytest.raises(_UnsupportedMetadata):
        populated(form_changes={'TotalTaxBaseUsd': None})
