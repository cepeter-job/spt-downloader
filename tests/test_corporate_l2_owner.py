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


@pytest.mark.parametrize('tax_type', ['ICT_ROGCIT', 'ICT_FCIT', 'ICT_FOGCIT'])
def test_unapproved_currency_or_oil_gas_never_fills_rupiah_template(tax_type):
    with pytest.raises(_UnsupportedMetadata):
        owner(populated(), tax_type=tax_type)
