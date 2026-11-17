"""Complete L2 owner semantic slice; execution is hosted-only.

Pinned offline Number is DecimalPipe's default 1.0-3, not NumberInteger.
"""
from copy import deepcopy

import pytest

import coretax_corporate_projection as projection
from coretax_json import _CorporateNumber as N, _UnsupportedMetadata
from test_corporate_l2_projection import affiliate, form, shareholder


def owner(value, **overrides):
    helper = getattr(projection, 'project_l2_owner', None)
    assert callable(helper), 'Missing whole-owner L2 renderer'
    kwargs = {'tax_type': 'ICT_RCIT', 'locale': 'id-ID',
              'country_labels': {'ID': 'SYNTHETIC INDONESIA', 'SG': 'SYNTHETIC SINGAPORE'},
              'position_labels': {'01': 'SYNTHETIC DIRECTOR'}}
    kwargs.update(overrides)
    return helper(value, **kwargs)


def populated():
    # Duplicates are occurrences, not identities to collapse. Stored percentage
    # zero is getFormData's literal alias, NOT the displayed 100.0000 footer.
    a = shareholder(PaidInCapital=N('1000.125'), PaidInCapitalPercentage=N('50'), Dividend=None)
    b = affiliate(1, Investment=N('2000.5'), InvestmentPercentage=N('12.0625'),
                  Debt=N('500.125'), DebtInterest=N('4.125'), Receivable=N('250.5'),
                  ReceivableYear='02024', ReceivableInterest=N('1.5'), IsEditable=False)
    return form(ListOfShareholders=[a, deepcopy(a)], InvestmentList=[b, deepcopy(b)],
                TotalPaidInCapital=N('2000.25'), TotalDividend=N('0'),
                TotalDebt=N('1000.25'), TotalReceivable=N('501'))


def test_populated_whole_owner_keeps_both_blocks_labels_duplicates_and_number_types():
    value = populated()
    before = deepcopy(value)
    result = owner(value)
    a, b = result['tables']
    assert value == before
    assert a['body_row_count'] == b['body_row_count'] == 2
    assert a['rows'][0] == ['1', 'SYNTHETIC OWNER', 'SYNTHETIC ADDRESS',
        'SYNTHETIC INDONESIA', '0000000000000009', 'SYNTHETIC DIRECTOR',
        '1.000,125', '50,0000', '0']
    assert a['rows'][1][1:] == a['rows'][0][1:]
    assert a['footer'] == [['', 'JUMLAH', '2.000,25', '100,0000', '0']]
    assert b['rows'][0] == ['1', 'SYNTHETIC AFFILIATE 1', 'SYNTHETIC SINGAPORE',
        '0000000000000002', '2.000,5', '12,0625', '500,125', '2025', '4,125',
        '250,5', '02024', '1,5']
    assert b['rows'][1][1:] == b['rows'][0][1:]
    assert b['footer'] == [['', 'JUMLAH', '1.000,25', '', '501', '']]
    assert a['complete'] is b['complete'] is True
    assert len(result['provenance']) >= 50
    assert any(e['path'][-1] == 'TotalPaidInCapitalPercentage'
               and e['value'] == '0' and e['rule'] == 'saved-percentage-alias-not-rendered'
               for e in result['provenance'])


@pytest.mark.parametrize('block,key,value', [
    ('ListOfShareholders', 'CountryCode', 'UNKNOWN'),
    ('ListOfShareholders', 'Position', 'UNKNOWN'),
    ('InvestmentList', 'CountryCode', 'UNKNOWN'),
    ('InvestmentList', 'Debt', N('0.1')),
    ('InvestmentList', 'DebtInterest', N('4.38')),
    ('InvestmentList', 'DebtInterest', N('0.0625')),
    ('InvestmentList', 'Debt', N('1000000000000000')),
    ('InvestmentList', 'InvestmentPercentage', N('1.00001')),
    ('ListOfShareholders', 'PaidInCapital', True),
    ('ListOfShareholders', 'Name', N('123')),
])
def test_unproved_reference_number_or_literal_type_refuses_entire_owner(block, key, value):
    source = populated()
    source[block][0][key] = value
    with pytest.raises(_UnsupportedMetadata):
        owner(source)


@pytest.mark.parametrize('count,footer', [(0, '0'), (1, ''), (2, '0')])
def test_affiliate_null_singleton_is_not_an_initial_zero_reduce(count, footer):
    row = affiliate(1, CountryCode=None, TIN=None, Investment=None,
                    InvestmentPercentage=None, Debt=None, DebtInterest=None,
                    Receivable=None, ReceivableInterest=None,
                    DebtYear=None, ReceivableYear=None)
    result = owner(form(InvestmentList=[deepcopy(row) for _ in range(count)]))
    a, b = result['tables']
    assert a['footer'] == [['', 'JUMLAH', '0', '0,0000', '0']]
    assert b['footer'] == [['', 'JUMLAH', footer, '', footer, '']]
    if count:
        assert b['rows'][0][2:] == [''] * 10


def test_shareholder_null_defaults_differ_from_affiliate_nulls_and_subposition_is_unused():
    row = shareholder(CountryCode=None, TIN=None, Position=None,
                      SubPosition='NOT A DISPLAY LABEL', PaidInCapital=None,
                      PaidInCapitalPercentage=None, Dividend=None)
    result = owner(form(ListOfShareholders=[row]), position_labels={})
    a, _ = result['tables']
    assert a['rows'][0] == ['1', 'SYNTHETIC OWNER', 'SYNTHETIC ADDRESS',
                             '', '', '', '0', '0,0000', '0']
    assert any(e['path'][-1] == 'SubPosition' and e['value'] == 'NOT A DISPLAY LABEL'
               and e['rule'] == 'unused-subposition' for e in result['provenance'])


def test_displayed_totals_are_ordered_model_getters_not_stale_saved_aliases():
    value = populated()
    for key in projection.L2_TOTALS:
        value[key] = N('999')
    result = owner(value)
    a, b = result['tables']
    assert a['footer'] == [['', 'JUMLAH', '2.000,25', '100,0000', '0']]
    assert b['footer'] == [['', 'JUMLAH', '1.000,25', '', '501', '']]
    assert {e['path'][-1] for e in result['provenance']
            if e['rule'] == 'overwritten-saved-total/ordered-model-getter'} == {
                'TotalPaidInCapital', 'TotalDividend', 'TotalDebt', 'TotalReceivable'}


@pytest.mark.parametrize('value', [N('-0'), N('0e0'), N('1e3'), N('NaN'),
                                    N('1e100000'), '1', 1, True, {}, []])
def test_unreviewed_number_representations_never_coerce(value):
    source = populated()
    source['InvestmentList'][0]['Debt'] = value
    with pytest.raises(_UnsupportedMetadata):
        owner(source)


@pytest.mark.parametrize('block', ['ListOfShareholders', 'InvestmentList'])
@pytest.mark.parametrize('value', [True, '', 1, {}, [None], [{}]])
def test_closed_row_and_container_inventory_refuses_drift(block, value):
    with pytest.raises(_UnsupportedMetadata):
        owner(form(**{block: value}))


def test_each_ordered_partial_sum_must_stay_exact_and_within_bound():
    row = shareholder(PaidInCapital=N('999999999999999'), PaidInCapitalPercentage=N('0'))
    small = shareholder(PaidInCapital=N('0.125'), PaidInCapitalPercentage=N('0'))
    # Even exact fractional operands cannot authorize an ordered partial total
    # above the reviewed 15-digit magnitude bound.
    with pytest.raises(_UnsupportedMetadata):
        owner(form(ListOfShareholders=[row, small]))


@pytest.mark.parametrize('tax_type', ['ICT_ROGCIT', 'ICT_FCIT', 'ICT_FOGCIT'])
def test_unapproved_currency_or_oil_gas_never_fills_rupiah_template(tax_type):
    with pytest.raises(_UnsupportedMetadata):
        owner(populated(), tax_type=tax_type)
