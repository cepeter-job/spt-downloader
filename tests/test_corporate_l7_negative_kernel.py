"""Closed negative calculation matrix; synthetic and runner-only."""
from copy import deepcopy

import pytest

from coretax_corporate_projection import project_l7
from coretax_json import _corporate_json, _UnsupportedMetadata
from support_json_corpus import Number, wire
from test_corporate_l7_projection import raw_source, BODY, SUFFIXES, HEADERS, SPANS


def source():
    form = raw_source()
    form[BODY][1]['FiscalNetProfitIncome'] = Number('-1234')
    main = {'NetIncomeBeforeTax': Number('-1234'), 'TaxYear': Number('2025'),
            'IsIncomeUnder': Number('0'), 'IsIncomeSolely': None, 'IsCarriedForward': Number('1')}
    return form, main


def project(form, main):
    values = _corporate_json(wire({'form': form, 'main': main, 'year': Number('2025')}))
    return project_l7(values['form'], main_form=values['main'], period_year=values['year'],
                      headers=list(HEADERS), footer_spans=deepcopy(SPANS), tax_type='ICT_RCIT', locale='id-ID')


@pytest.mark.parametrize('key', ['IsIncomeUnder', 'IsIncomeSolely', 'IsCarriedForward', 'TaxYear'])
@pytest.mark.parametrize('bad', ['missing', 'string', 'bool', 'null', 'wrong-number'])
def test_negative_current_selector_types_and_presence_are_not_defaulted(key, bad):
    form, main = source()
    if bad == 'missing': del main[key]
    elif bad == 'string': main[key] = '0' if key == 'IsIncomeUnder' else '1'
    elif bad == 'bool': main[key] = False if key == 'IsIncomeUnder' else True
    elif bad == 'null': main[key] = None
    else: main[key] = Number('2')
    if key == 'IsIncomeSolely' and bad == 'null':
        assert project(form, main)['table']['rows'][1][2] == '-1.234'
    else:
        with pytest.raises(_UnsupportedMetadata): project(form, main)


@pytest.mark.parametrize('first', ['0', '-1233', '-1235'])
def test_later_matching_profit_cannot_rescue_wrong_first_current_profit(first):
    form, main = source()
    form[BODY][0].update(TaxYear='2025', FiscalNetProfitIncome=Number(first))
    before = deepcopy((form, main))
    with pytest.raises(_UnsupportedMetadata): project(form, main)
    assert (form, main) == before


def test_duplicates_keep_original_profit_lexemes_years_and_first_match_order():
    form, main = source()
    form[BODY][0].update(TaxYear='2025', FiscalNetProfitIncome=Number('-1234.00'))
    form[BODY][1].update(TaxYear='02025', FiscalNetProfitIncome=Number('-0'))
    main['IsIncomeUnder'], main['IsCarriedForward'] = Number('-0.0'), Number('1e0')
    before = deepcopy((form, main))
    result = project(form, main)
    assert [row[1:3] for row in result['table']['rows'][:2]] == [['2025', '-1.234'], ['02025', '0']]
    assert (form, main) == before
    assert any(e['value'] == '-1234.00' and e['type'] == 'number' for e in result['provenance'])
    assert any(e['value'] == '-0' and e['type'] == 'number' for e in result['provenance'])


@pytest.mark.parametrize('suffix', SUFFIXES)
def test_every_compensation_column_keeps_ordered_intermediate_bound(suffix):
    form, main = source()
    form[BODY].append(deepcopy(form[BODY][1]))
    for index, name in enumerate(SUFFIXES):
        form['TotalFiscalLossCompensation' + name] = Number(str(300 * (index + 1)))
    key = 'FiscalLossCompensation' + suffix
    for row, value in zip(form[BODY], ['999999999999999', '1', '-1']): row[key] = Number(value)
    form['TotalFiscalLossCompensation' + suffix] = Number('999999999999999')
    with pytest.raises(_UnsupportedMetadata, match='unsafe_corporate_l7_ordered_total'):
        project(form, main)


@pytest.mark.parametrize('key,value', [('NetIncomeBeforeTax', '-1e9999999999'),
    ('IsIncomeUnder', '1e9999999999'), ('IsCarriedForward', '1e9999999999')])
def test_extreme_finite_json_exponents_refuse_as_unsupported_not_decimal_errors(key, value):
    # Source-only RED for L7's uncontained DecimalException conversion boundary.
    form, main = source()
    main[key] = Number(value)
    with pytest.raises(_UnsupportedMetadata): project(form, main)
