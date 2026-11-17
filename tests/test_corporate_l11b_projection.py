"""Reviewed L11-B (Debt to Equity Ratio) projection contracts; GitHub-runner execution only.

Every displayed cell maps to one literal control of the pinned L11-B owner. The
submitted EBITDA and DER controls are copied, not recomputed; the two identities
the owner maintains are re-checked exactly.
"""
import importlib
from pathlib import Path

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus

RESOURCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'
# The approved workbook's header rows for the three L11-B blocks.
HEADER_ROWS = ((11, 'L11B_DEBT_HEADERS'), (17, 'L11B_EQUITY_HEADERS'), (30, 'L11B_COST_HEADERS'))


def module():
    return importlib.import_module('coretax_corporate_projection')


def months(prefix, value):
    return {f'{prefix}Month{month}': _CorporateNumber(value) for month in range(1, 13)}


def form(**overrides):
    debt = {'IdentityNumber': '0000000000000002', 'Name': 'SYNTHETIC LENDER',
            'Relationship': 'SYNTHETIC RELATION', **months('Debt', '1000'),
            'Average': _CorporateNumber('1000')}
    equity = {'TypeOfEquity': 'SYNTHETIC CAPITAL', **months('Equity', '500'),
              'Average': _CorporateNumber('500')}
    cost = {'Name': 'SYNTHETIC LENDER', 'AverageDebtBalances': _CorporateNumber('1000'),
            'BorrowingCostAmount': _CorporateNumber('80'),
            'BorrowingCostThatCanBeDeducted': _CorporateNumber('50'),
            'BorrowingCostThatAreNotDeductible': _CorporateNumber('30')}
    value = {
        'CommercialNettIncome': _CorporateNumber('1000000'),
        'DepreciationAndAmortizationExpenses': _CorporateNumber('200000'),
        'IncomeTaxExpense': _CorporateNumber('50000'),
        'BorrowingCostExpense': _CorporateNumber('80000'),
        'Ebitda': _CorporateNumber('1250000'),
        'Ebitda25': _CorporateNumber('312500'),
        'DebtBalanceAverage': [debt],
        'TotalDebtBalanceAverage': {**months('Debt', '1000'), 'Average': _CorporateNumber('1000')},
        'EquityBalanceAverage': [equity],
        'TotalEquityBalanceAverage': {**months('Equity', '500'), 'Average': _CorporateNumber('500')},
        'DebtToEquityRatio': _CorporateNumber('2'),
        'BorrowingCosts': [cost],
        'IsDocumentListForm': True,
        'IsEbitdaManuallyEdited': False,
    }
    value.update(overrides)
    return value


def project(payload=None, **overrides):
    helper = getattr(module(), 'project_l11b', None)
    assert callable(helper), 'Missing reviewed L11-B projection'
    options = {'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    return helper(form() if payload is None else payload, **options)


def module_or(name):
    return getattr(module(), name)


def observed():
    forms = corpus.observed()
    binding = {'name': 'L11-B', 'paths': [['L11BFormData']], 'grids': [], 'responses': [],
               'dependencies': [],
               'projection': {'kind': 'corporate-l11b-v1',
                              'builds': {module_or('CIT_SOURCE'):
                                         module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': corpus.FRAME_URL}}
    forms.insert(1, binding)
    return forms


def payload_form(l11b=None):
    """Same controls, but as raw JSON number tokens for the adapter."""
    value = dict(form() if l11b is None else l11b)
    for name, _ in module().L11B_FIELDS:
        value[name] = corpus.Number(str(value[name]))
    for row in value['DebtBalanceAverage'] or []:
        for key in ('Average', *(f'DebtMonth{month}' for month in range(1, 13))):
            row[key] = corpus.Number(str(row[key]))
    for row in value['EquityBalanceAverage'] or []:
        for key in ('Average', *(f'EquityMonth{month}' for month in range(1, 13))):
            row[key] = corpus.Number(str(row[key]))
    for row in value['BorrowingCosts'] or []:
        for key in ('AverageDebtBalances', 'BorrowingCostAmount',
                    'BorrowingCostThatCanBeDeducted', 'BorrowingCostThatAreNotDeductible'):
            row[key] = corpus.Number(str(row[key]))
    if value['DebtToEquityRatio'] is not None:
        value['DebtToEquityRatio'] = corpus.Number(str(value['DebtToEquityRatio']))
    for key in ('TotalDebtBalanceAverage', 'TotalEquityBalanceAverage'):
        if isinstance(value.get(key), dict):
            value[key] = {name: corpus.Number(str(token)) for name, token in value[key].items()}
    return value


def primary(l11b=None):
    form_value = corpus.current_form()
    form_value['L11BFormData'] = payload_form(l11b)
    return corpus.primary(form_value)


def adapt(forms=None, payload=None, record=None):
    return adapt_corporate_detail(iter([primary() if payload is None else payload]),
                                  corpus.selected_record() if record is None else record,
                                  corpus.SCOPE, observed() if forms is None else forms)


def template_headers(form_name, row):
    from openpyxl import load_workbook
    book = load_workbook(RESOURCE, read_only=True)
    try:
        values = [cell.value for cell in book[form_name][row]]
    finally:
        book.close()
    while values and values[-1] is None:
        values.pop()
    return values


def test_every_template_caption_comes_from_one_proven_payload_control():
    fields = getattr(module(), 'L11B_FIELDS', None)
    assert fields is not None, 'Missing reviewed L11-B caption map'
    result = project()
    assert [field['field'] for field in result['fields']] == [name for name, _ in fields]
    assert [field['label'] for field in result['fields']] == [caption for _, caption in fields]
    assert [field['value'] for field in result['fields']] == [
        '1.000.000', '200.000', '50.000', '80.000', '1.250.000', '312.500']
    assert [entry['path'] for entry in result['provenance'][:6]] == [
        ['L11BFormData', name] for name, _ in fields]


@pytest.mark.parametrize('header,attribute', HEADER_ROWS)
def test_every_projected_table_copies_one_template_header_row(header, attribute):
    headers = getattr(module(), attribute)
    assert template_headers('L11-B', header) == headers
    table = project()['tables'][HEADER_ROWS.index((header, attribute))]
    assert table['headers'] == headers
    spans, = table['footer_spans']
    assert sum(spans) == len(headers)
    assert len(table['footer'][0]) == len(spans)
    assert len(table['rows']) == table['body_row_count'] + 1
    assert table['source_total'] == table['body_row_count']


def test_projected_blocks_keep_the_template_reading_order():
    labels = [table['name'] for table in project()['tables']]
    assert labels == ['L11-B/debt', 'L11-B/equity', 'L11-B/costs']
    debt, equity, costs = project()['tables']
    assert debt['rows'][0][0] == '0000000000000002'
    assert debt['rows'][-1][0] == 'JUMLAH'
    assert equity['rows'][-1][0] == 'JUMLAH'
    assert costs['rows'][-1] == ['JUMLAH', '1.000', '80', '50', '30']


def test_the_submitted_der_average_controls_reach_both_footer_cells():
    debt, equity, _ = project()['tables']
    assert debt['rows'][-1][-1] == '1.000'
    assert equity['rows'][-1][-1] == '500'
    paths = {tuple(entry['path']) for entry in project()['provenance']}
    assert ('L11BFormData', 'TotalDebtBalanceAverage', 'Average') in paths
    assert ('L11BFormData', 'TotalEquityBalanceAverage', 'Average') in paths


def test_ebitda_quarter_and_capital_mean_must_reconcile_exactly():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(Ebitda25=_CorporateNumber('312499')))
    assert str(error.value) == 'unreconciled_corporate_l11b_ebitda_quarter'
    equity = dict(form()['EquityBalanceAverage'][0], Average=_CorporateNumber('501'))
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(EquityBalanceAverage=[equity]))
    assert str(error.value) == 'unreconciled_corporate_l11b_equity_average'
    total = dict(form()['TotalEquityBalanceAverage'], Average=_CorporateNumber('501'))
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(TotalEquityBalanceAverage=total))
    assert str(error.value) == 'unreconciled_corporate_l11b_equity_total'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(DebtToEquityRatio=_CorporateNumber('3')))
    assert str(error.value) == 'unreconciled_corporate_l11b_ratio'


def test_a_populated_month_mean_is_recomputed_from_the_source_values():
    filled = {1: '1000', 2: '1000', 3: '1001'}
    equity = {'TypeOfEquity': 'SYNTHETIC CAPITAL',
              **{f'EquityMonth{month}': (_CorporateNumber(filled[month]) if month in filled else None)
                 for month in range(1, 13)},
              'Average': _CorporateNumber('1000.3333333333334')}
    total = {f'EquityMonth{month}': _CorporateNumber(filled.get(month, '0'))
             for month in range(1, 13)}
    total['Average'] = _CorporateNumber('1000.3333333333334')
    ratio = _CorporateNumber(repr(1000 / 1000.3333333333334))
    result = project(form(EquityBalanceAverage=[equity], TotalEquityBalanceAverage=total,
                          DebtToEquityRatio=ratio))
    assert result['tables'][1]['rows'][0][-1] == '1.000,33'


def test_a_zero_capital_average_keeps_the_owner_null_ratio():
    total = {**months('Equity', '0'), 'Average': _CorporateNumber('0')}
    empty = {**months('Debt', '0'), 'Average': _CorporateNumber('0')}
    result = project(form(EquityBalanceAverage=None, TotalEquityBalanceAverage=total,
                          DebtBalanceAverage=None, TotalDebtBalanceAverage=empty,
                          DebtToEquityRatio=_CorporateNumber('0')))
    assert result['tables'][1]['body_row_count'] == 0
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(EquityBalanceAverage=None, TotalEquityBalanceAverage=total,
                     DebtToEquityRatio=_CorporateNumber('0')))
    assert str(error.value) == 'unreconciled_corporate_l11b_ratio'
    # x/0 is not representable in JSON, so the owner submits an explicit null.
    assert project(form(EquityBalanceAverage=None, TotalEquityBalanceAverage=total,
                        DebtToEquityRatio=None))['tables'][1]['body_row_count'] == 0


def test_part_three_total_is_the_ordered_sum_the_component_never_submits():
    result = project()
    assert 'TotalBorrowingCosts' not in form()
    rules = {entry['rule'] for entry in result['provenance']
             if entry['destination'].get('table') == 'L11-B/costs'
             and 'footer' in entry['destination']}
    assert rules == {'checked-model-ordered-sum-operand'}
    reported = {'AverageDebtBalances': _CorporateNumber('1000'),
                'BorrowingCostAmount': _CorporateNumber('80'),
                'BorrowingCostThatCanBeDeducted': _CorporateNumber('50'),
                'BorrowingCostThatAreNotDeductible': _CorporateNumber('30')}
    asserted = project(form(TotalBorrowingCosts=reported))
    assert asserted['tables'][2]['footer'] == result['tables'][2]['footer']
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(TotalBorrowingCosts={**reported, 'BorrowingCostAmount': _CorporateNumber('81')}))
    assert str(error.value) == 'unreconciled_corporate_l11b_cost_total'


@pytest.mark.parametrize('mutation,reason', [
    ({'TaxableIncome': _CorporateNumber('0')}, 'unsupported_corporate_l11b_source_shape'),
    ({'CommercialNettIncome': '1000000'}, 'unsupported_corporate_l11b_amount_type'),
    ({'Ebitda': True}, 'unsupported_corporate_l11b_amount_type'),
    ({'Ebitda25': _CorporateNumber('312500.5')}, 'unsupported_corporate_l11b_amount_precision'),
    ({'BorrowingCosts': [{'Name': 'X'}]}, 'unsupported_corporate_l11b_cost_row'),
    ({'BorrowingCosts': [{**form()['BorrowingCosts'][0],
                          'BorrowingCostAmount': _CorporateNumber('-1')}]},
     'unsupported_corporate_l11b_negative_amount'),
    ({'DebtBalanceAverage': [{'IdentityNumber': '1'}]}, 'unsupported_corporate_l11b_debt_row'),
    ({'IsDocumentListForm': 'true'}, 'unsupported_corporate_l11b_source_shape'),
    ({'DebtToEquityRatio': '2'}, 'unsupported_corporate_l11b_ratio_type'),
])
def test_unreviewed_l11b_shapes_refuse(mutation, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(**mutation))
    assert str(error.value) == reason


def test_absent_der_average_tuple_refuses_the_capture():
    value = form()
    value.pop('TotalEquityBalanceAverage')
    forms = observed()
    form_value = corpus.current_form()
    form_value['L11BFormData'] = payload_form(value)
    result = adapt_corporate_detail(iter([corpus.primary(form_value)]), corpus.selected_record(),
                                    corpus.SCOPE, forms)
    assert not result['eligible']
    assert result['reason'] == 'unsupported_corporate_l11b_source_shape'


def test_absent_l11b_root_refuses_the_capture():
    forms = observed()
    result = adapt_corporate_detail(iter([corpus.primary(corpus.current_form())]),
                                    corpus.selected_record(), corpus.SCOPE, forms)
    assert not result['eligible']
    assert result['reason'] == 'missing_observed_corporate_source_path'


@pytest.mark.parametrize('projection', [
    {'kind': 'corporate-l11b-v0'},
    {'kind': 'corporate-l11b-v1', 'builds': {}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l11b-v1', 'builds': {module_or('CIT_SOURCE'): 'APPROVED'},
     'route': corpus.FRAME_URL},
    {'kind': 'corporate-l11b-v1', 'builds': {module_or('CIT_SOURCE'): 'a' * 64},
     'route': corpus.FRAME_URL, 'timezone': 'Asia/Jakarta'},
])
def test_projection_proof_must_match_the_reviewed_shape(projection):
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L11-B']
    binding['projection'] = projection
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l11b_binding'


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L11-B']
    binding['projection'] = {**binding['projection'], 'route': corpus.FRAME_URL + '/changed'}
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l11b_binding'
    forms = observed()
    # Drop the Induk projection so this isolates the L11-B lifecycle gate.
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l11b_submitted_lifecycle'


def test_projected_l11b_section_replaces_the_dump_and_keeps_three_blocks():
    forms = observed()
    result = adapt(forms)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L11-B']
    assert [table['name'] for table in section['tables']] == ['L11-B/debt', 'L11-B/equity',
                                                              'L11-B/costs']
    assert all(table['headers'] and table['rows'] for table in section['tables'])
    assert [field['field'] for field in section['fields']] == [
        name for name, _ in module().L11B_FIELDS]
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L11-B']
    assert projected['kind'] == 'corporate-l11b-v1'
    assert all(entry['path'][0] == 'L11BFormData' and entry['rule'] for entry in projected['values'])
    paths = {tuple(entry['path']) for entry in projected['values']}
    for table, block in zip(section['tables'], ('DebtBalanceAverage', 'EquityBalanceAverage',
                                                'BorrowingCosts')):
        for index in range(table['body_row_count']):
            keys = {path[3] for path in paths if path[:2] == ('L11BFormData', block)
                    and len(path) == 4 and path[2] == index}
            assert len(keys) == len(table['headers'])


def test_l11b_projection_does_not_mutate_source_bindings_or_payload():
    from copy import deepcopy
    forms = observed()
    before = deepcopy(forms)
    payload = primary()
    raw = payload['body']
    adapt(forms, payload=payload)
    assert forms == before and payload['body'] == raw


def test_projected_l11b_binds_every_template_amount_cell(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import section, source_run
    result = project()
    run = source_run('PPh Badan', [section('L11-B', fields=result['fields'],
                                           tables=result['tables'])])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L11-B']
        assert [sheet.cell(row, 2).value for row in range(2, 8)] == [
            1_000_000, 200_000, 50_000, 80_000, 1_250_000, 312_500]
        assert all(sheet.cell(row, 2).data_type == 'n' for row in range(2, 8))
        assert sheet['A12'].value == '0000000000000002'
        assert sheet['P13'].value == 1000
        assert sheet['A18'].value == 'SYNTHETIC CAPITAL'
        assert sheet['N19'].value == 500
        # The reviewed DER block divides the two written average cells.
        assert sheet['A22'].value == 'PERHITUNGAN DER'
        assert sheet['C22'].value == '=P13' and sheet['C23'].value == '=N19'
        assert sheet['D22'].value == '=C22/C23'
        assert sheet['B27'].value == 1000 and sheet['E28'].value == 30
        assert reports[0]['complete'] is True
        assert reports[0]['unmapped_fields'] == reports[0]['unmapped_tables'] == 0
    finally:
        book.close()
