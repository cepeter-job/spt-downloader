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
    expected_paths = {('ListOfOwnership', body, index, key)
        for body in ('ListOfShareholders', 'InvestmentList')
        for index, row in enumerate(value[body]) for key in row}
    expected_paths.update(('ListOfOwnership', key) for key in projection.L2_TOTALS)
    assert {tuple(e['path']) for e in result['provenance']} == expected_paths
    assert len(result['provenance']) == len(expected_paths)
    assert any(e['path'][-1] == 'TotalPaidInCapitalPercentage'
               and e['value'] == '0' and e['rule'] == 'saved-percentage-alias-not-rendered'
               for e in result['provenance'])


@pytest.mark.parametrize('block,key,value', [
    ('ListOfShareholders', 'CountryCode', 'UNKNOWN'),
    ('ListOfShareholders', 'Position', 'UNKNOWN'),
    ('InvestmentList', 'CountryCode', 'UNKNOWN'),
    ('InvestmentList', 'DebtInterest', N('0.0625')),
    ('InvestmentList', 'Debt', N('1000000000000000')),
    ('InvestmentList', 'Investment', N('999999999999998.125')),
    ('InvestmentList', 'InvestmentPercentage', N('1.00001')),
    ('ListOfShareholders', 'PaidInCapital', True),
    ('ListOfShareholders', 'Name', N('123')),
])
def test_unproved_reference_number_or_literal_type_refuses_entire_owner(block, key, value):
    source = populated()
    source[block][0][key] = value
    with pytest.raises(_UnsupportedMetadata):
        owner(source)


def test_affiliate_numeric_year_uses_js_string_without_grouping_and_keeps_original_token():
    value = populated()
    value['InvestmentList'][0]['DebtYear'] = N('2025.0')
    value['InvestmentList'][0]['ReceivableYear'] = N('2024')
    result = owner(value)
    assert result['tables'][1]['rows'][0][7:11:3] == ['2025', '2024']
    entry, = [e for e in result['provenance'] if e['path'] ==
              ['ListOfOwnership', 'InvestmentList', 0, 'DebtYear']]
    assert entry['type'] == 'number' and entry['value'] == '2025.0'
    assert entry['rule'] == 'integral-year/JS-String'


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


def test_absent_investment_list_projects_empty_affiliate_table():
    # A company with no affiliates omits InvestmentList entirely; that is an
    # empty affiliate table, not a shape drift. Shareholders + the five totals
    # stay mandatory and unknown extras still refuse (closed-inventory guard).
    value = form(ListOfShareholders=[shareholder()])
    del value['InvestmentList']
    result = owner(value)
    a, b = result['tables']
    assert a['body_row_count'] == 1
    assert b['body_row_count'] == 0


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


def test_shareholder_row_omitting_subposition_still_projects():
    # Live evidence (job baae8d60): the current portal omits SubPosition from
    # every shareholder row. It is copied-but-unused metadata, so its absence
    # must not refuse the whole owner block.
    row = shareholder(PaidInCapital=None, PaidInCapitalPercentage=None, Dividend=None)
    del row['SubPosition']
    result = owner(form(ListOfShareholders=[row]))
    a, _ = result['tables']
    assert a['body_row_count'] == 1
    assert a['rows'][0] == ['1', 'SYNTHETIC OWNER', 'SYNTHETIC ADDRESS',
                             'SYNTHETIC INDONESIA', '0000000000000009',
                             'SYNTHETIC DIRECTOR', '0', '0,0000', '0']
    assert not any(e['path'][-1] == 'SubPosition' for e in result['provenance'])


@pytest.mark.parametrize('token,rendered', [('2.9', '2,9'), ('0.1', '0,1'), ('4.38', '4,38')])
def test_affiliate_fractional_rate_is_not_refused_for_binary_inexactness(token, rendered):
    # Live evidence (job 2ce7ad8f): a real saved DebtInterest of 2.9 is not
    # binary-exact but renders exactly as 2,9. The browser only needs the
    # double's shortest round-trip repr, not binary64 exactness.
    row = affiliate(1, DebtInterest=N(token))
    result = owner(form(InvestmentList=[row]))
    _, b = result['tables']
    assert b['rows'][0][8] == rendered


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


def test_ordered_total_does_not_exceed_excel_significant_precision():
    row = shareholder(PaidInCapital=N('999999999999.875'), PaidInCapitalPercentage=N('0'))
    small = shareholder(PaidInCapital=N('0.25'), PaidInCapitalPercentage=N('0'))
    with pytest.raises(_UnsupportedMetadata):
        owner(form(ListOfShareholders=[row, small]))


@pytest.mark.parametrize('text,expected,safe', [
    ('1.000,125', 1000.125, True), ('4,125', 4.125, True), ('0', 0, True),
    ('', None, True), (None, None, True), ('1,0001', '1,0001', False),
    ('1.00,125', '1.00,125', False), ('1e3', '1e3', False),
    ('999999999999998,125', '999999999999998,125', False),
])
@pytest.mark.parametrize('monetary', [False, True])
def test_l2_excel_number_writer_preserves_three_digit_values_without_changing_other_types(text, expected, safe, monetary, tmp_path):
    from openpyxl import Workbook, load_workbook
    import coretax_badan_template as template
    helper = getattr(template, '_write_l2_number', None)
    assert callable(helper), 'Missing source-scoped L2 Number writer'
    book = Workbook()
    try:
        sheet = book.active
        sheet['A1'].number_format = 'General'
        assert helper(sheet, 1, 1, text, monetary=monetary) is safe
        # Shared _write deliberately stores a literal blank in memory; the
        # serialized/reopened empty Excel cell is None. Do not alter production
        # blank normalization to satisfy an in-memory-only test expectation.
        assert sheet['A1'].value == ('' if expected is None else expected)
        assert sheet['A1'].number_format == (template.ACCOUNTING if monetary else 'General')
        path = tmp_path / 'l2-number.xlsx'
        book.save(path)
        reopened = load_workbook(path)
        try:
            assert reopened.active['A1'].value == expected
            assert reopened.active['A1'].number_format == sheet['A1'].number_format
        finally:
            reopened.close()
    finally:
        book.close()


@pytest.mark.parametrize('tax_type', ['ICT_ROGCIT', 'ICT_FCIT', 'ICT_FOGCIT'])
def test_unapproved_currency_or_oil_gas_never_fills_rupiah_template(tax_type):
    with pytest.raises(_UnsupportedMetadata):
        owner(populated(), tax_type=tax_type)
