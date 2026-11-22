"""Conservative L11-B projection. GitHub-runner execution only."""
from copy import deepcopy
import importlib
from pathlib import Path

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus

RESOURCE = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'


def module():
    return importlib.import_module('coretax_corporate_projection')


def form(**overrides):
    value = {'CommercialNettIncome': _CorporateNumber('1000000'),
             'DepreciationAndAmortizationExpenses': _CorporateNumber('200000'),
             'IncomeTaxExpense': _CorporateNumber('50000'),
             'BorrowingCostExpense': _CorporateNumber('80000'),
             # Inconsistent omitted controls: an editor identity is not View proof.
             'Ebitda': _CorporateNumber('7'), 'Ebitda25': _CorporateNumber('9'),
             'DebtBalanceAverage': None, 'TotalDebtBalanceAverage': None,
             'EquityBalanceAverage': None, 'TotalEquityBalanceAverage': None,
             'DebtToEquityRatio': None, 'BorrowingCosts': [
                 {'Name': 'SYNTHETIC LENDER', 'AverageDebtBalances': _CorporateNumber('1000'),
                  'BorrowingCostAmount': _CorporateNumber('80'),
                  'BorrowingCostThatCanBeDeducted': _CorporateNumber('50'),
                  'BorrowingCostThatAreNotDeductible': _CorporateNumber('30')}],
             'IsDocumentListForm': True, 'IsEbitdaManuallyEdited': True}
    value.update(overrides)
    return value


def project(value=None, **overrides):
    return module().project_l11b(form() if value is None else value,
                                **{'tax_type': 'ICT_RCIT', 'locale': 'id-ID', **overrides})


def selected():
    record = corpus.selected_record()
    record['source_fields']['ReturnSheetModel'] = 'Normal'
    return record


def route():
    fields = selected()['source_fields']
    return (corpus.ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/'
            + '/'.join((fields['TaxpayerAggregateIdentifier'], corpus.RECORD_ID,
                        fields['TaxTypeCode'], fields['AggregateIdentifier'])) + '?view=true')


def observed():
    forms = corpus.observed()
    forms[0]['projection']['route'] = route()
    forms.append({'name': 'L11-B', 'paths': [['L11BFormData']], 'grids': [],
                  'responses': [], 'dependencies': [],
                  'projection': {'kind': 'corporate-l11b-v1',
                                 'builds': dict(module().BUILD_DIGESTS), 'route': route()}})
    return forms


def primary(value=None, *, previous=None):
    def numbers(item):
        if type(item) is _CorporateNumber:
            return corpus.Number(item)
        if isinstance(item, dict):
            return {key: numbers(child) for key, child in item.items()}
        if isinstance(item, list):
            return [numbers(child) for child in item]
        return item
    current = corpus.current_form()
    current['L11BFormData'] = numbers(form() if value is None else value)
    packet = corpus.packet({'IsSuccessful': True, 'ErrorCode': 0, 'Payload': {
        'TIN': corpus.NPWP, 'PeriodYear': 2025, 'IsDraft': True,
        'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PreviousFormData': previous, 'LastSubmittedFormData': None,
        'CurrentFormData': corpus.wire(current)}})
    packet['context']['frame_url'] = route()
    return packet


def adapt(forms=None, packet=None, record=None):
    return adapt_corporate_detail(iter([primary() if packet is None else packet]),
                                  selected() if record is None else record, corpus.SCOPE,
                                  observed() if forms is None else forms)


def test_only_four_stable_scalar_controls_are_projected():
    result = project()
    assert [field['field'] for field in result['fields']] == [
        'CommercialNettIncome', 'DepreciationAndAmortizationExpenses',
        'IncomeTaxExpense', 'BorrowingCostExpense']
    assert [field['value'] for field in result['fields']] == [
        '1.000.000', '200.000', '50.000', '80.000']
    assert [entry['path'] for entry in result['provenance'][:4]] == [
        ['L11BFormData', field['field']] for field in result['fields']]


def test_only_unconditional_grid_uses_the_exact_template_header():
    from openpyxl import load_workbook
    table, = project()['tables']
    book = load_workbook(RESOURCE, read_only=True)
    try:
        headers = [cell.value for cell in book['L11-B'][30]]
    finally:
        book.close()
    while headers and headers[-1] is None:
        headers.pop()
    assert table['headers'] == headers == module().L11B_COST_HEADERS
    assert table['rows'] == [['SYNTHETIC LENDER', '1.000', '80', '50', '30'],
                             ['JUMLAH', '1.000', '80', '50', '30']]
    assert table['footer'] == [table['rows'][-1]]
    assert table['footer_spans'] == [[1] * 5]
    assert table['body_row_count'] == table['source_total'] == 1


@pytest.mark.parametrize('rows', [None, []])
def test_empty_grid_zero_footer_retains_its_source(rows):
    result = project(form(BorrowingCosts=rows))
    table, = result['tables']
    assert table['rows'] == [['JUMLAH', '0', '0', '0', '0']]
    assert table['body_row_count'] == 0
    evidence = [entry for entry in result['provenance'] if entry['rule'] == 'empty-grid-total']
    assert len(evidence) == 4
    assert all(entry['path'] == ['L11BFormData', 'BorrowingCosts'] for entry in evidence)
    assert all(entry['type'] == ('null' if rows is None else 'array')
               and entry['value'] == rows for entry in evidence)


def test_ordered_sum_preserves_duplicate_operands():
    value = form()
    value['BorrowingCosts'] *= 2
    result = project(value)
    assert result['tables'][0]['footer'] == [['JUMLAH', '2.000', '160', '100', '60']]
    operands = [entry for entry in result['provenance']
                if entry['rule'] == 'checked-model-ordered-sum-operand']
    assert len(operands) == 8
    assert {entry['path'][2] for entry in operands} == {0, 1}


@pytest.mark.parametrize('mutation,reason', [
    ({'Extra': None}, 'source_shape'),
    ({'IsDocumentListForm': 'true'}, 'source_shape'),
    ({'CommercialNettIncome': None}, 'amount_type'),
    ({'CommercialNettIncome': '1000000'}, 'amount_type'),
    ({'CommercialNettIncome': True}, 'amount_type'),
    ({'CommercialNettIncome': _CorporateNumber('NaN')}, 'amount_type'),
    ({'BorrowingCostExpense': _CorporateNumber('1.1')}, 'amount_precision'),
    ({'BorrowingCostExpense': _CorporateNumber('1000000000000000')}, 'amount_precision'),
    ({'BorrowingCosts': {}}, 'cost_body'),
    ({'BorrowingCosts': [None]}, 'cost_row'),
    ({'BorrowingCosts': [{'Name': 'X'}]}, 'cost_row'),
    ({'BorrowingCosts': [{**form()['BorrowingCosts'][0], 'Name': None}]}, 'text'),
    ({'BorrowingCosts': [{**form()['BorrowingCosts'][0], 'Name': _CorporateNumber('1')}]}, 'text'),
    ({'BorrowingCosts': [{**form()['BorrowingCosts'][0], 'BorrowingCostAmount': None}]}, 'amount_type'),
    ({'BorrowingCosts': [{**form()['BorrowingCosts'][0], 'BorrowingCostAmount': _CorporateNumber('-1')}]}, 'negative_amount'),
])
def test_unreviewed_source_refuses(mutation, reason):
    with pytest.raises(_UnsupportedMetadata, match='^unsupported_corporate_l11b_' + reason + '$'):
        project(form(**mutation))


def test_live_explicit_null_totals_are_admitted():
    """Live shape: TotalBorrowingCosts and the optional averages are explicit
    nulls; the four scalar controls and the cost grid still project."""
    value = form(TotalBorrowingCosts=None, DebtBalanceAverage=None,
                 EquityBalanceAverage=None, BorrowingCosts=None)
    result = project(value)
    assert [field['field'] for field in result['fields']] == [
        'CommercialNettIncome', 'DepreciationAndAmortizationExpenses',
        'IncomeTaxExpense', 'BorrowingCostExpense']
    table, = result['tables']
    assert table['body_row_count'] == 0 and table['complete'] is True
    assert table['footer'][0][0] == 'JUMLAH'


@pytest.mark.parametrize('alias', ['omitted', 'null'])
def test_borrowing_cost_total_alias_is_optional_and_null_only(alias):
    """The alias is optional: an omitted key and an explicit null project the
    same values and footer (the live Amendment omits it, the Normal nulls it)."""
    value = form()
    if alias == 'null':
        value['TotalBorrowingCosts'] = None
    else:
        value.pop('TotalBorrowingCosts', None)
    result = project(value)
    assert [field['value'] for field in result['fields']] == ['1.000.000', '200.000', '50.000', '80.000']
    table, = result['tables']
    assert table['footer'][0] == ['JUMLAH', '1.000', '80', '50', '30']


@pytest.mark.parametrize('value', [
    _CorporateNumber('0'), _CorporateNumber('80'), False, True, '', '80', [], {}, [0], {'Total': 0},
])
def test_non_null_borrowing_cost_total_alias_refuses(value):
    with pytest.raises(_UnsupportedMetadata, match='^unsupported_corporate_l11b_source_shape$'):
        project(form(TotalBorrowingCosts=value))


@pytest.mark.parametrize('manual', [False, _CorporateNumber('0'), '1', None])
def test_auto_or_untyped_manual_lifecycle_refuses(manual):
    with pytest.raises(_UnsupportedMetadata, match='^unverified_corporate_l11b_manual_lifecycle$'):
        project(form(IsEbitdaManuallyEdited=manual))


@pytest.mark.parametrize('options', [{'tax_type': 'ICT_ROGCIT'}, {'locale': 'en-US'}])
def test_unreviewed_environment_refuses(options):
    with pytest.raises(_UnsupportedMetadata, match='^unsupported_corporate_l11b_structure$'):
        project(**options)


def test_numeric_one_manual_marker_is_reviewed():
    assert project(form(IsEbitdaManuallyEdited=_CorporateNumber('1')))['fields']


def test_every_ordered_sum_is_bounded():
    value = form()
    value['BorrowingCosts'] = [{**value['BorrowingCosts'][0],
                               'BorrowingCostAmount': _CorporateNumber('999999999999999')}] * 2
    with pytest.raises(_UnsupportedMetadata, match='^unsafe_corporate_l11b_ordered_total$'):
        project(value)


@pytest.mark.parametrize('defect', ['wrong-pin', 'missing-pin', 'bad-pin', 'extra-pin',
                                    'route', 'kind', 'extra', 'path', 'grids'])
def test_proof_requires_exact_pins_route_and_shape(defect):
    forms = observed()
    binding = forms[-1]
    proof = binding['projection']
    if defect == 'wrong-pin':
        proof['builds'][module().CIT_SOURCE] = 'a' * 64
    elif defect == 'missing-pin':
        proof['builds'].pop(module().MAIN_SOURCE)
    elif defect == 'bad-pin':
        proof['builds'][module().CIT_SOURCE] = None
    elif defect == 'extra-pin':
        proof['builds']['https://example.invalid/other.js'] = 'a' * 64
    elif defect == 'route':
        proof['route'] += '&other=true'
    elif defect == 'kind':
        proof['kind'] = 'corporate-l11b-v0'
    elif defect == 'extra':
        proof['timezone'] = 'Asia/Jakarta'
    elif defect == 'path':
        binding['paths'].append(['OTHER'])
    else:
        binding['grids'] = [1]
    with pytest.raises(_UnsupportedMetadata, match='^unverified_corporate_l11b_binding$'):
        module()._apply_l11b(binding, {}, forms, root={}, payload={}, record=selected(),
                            event={'frame_url': route(), 'sequence': 1})


@pytest.mark.parametrize('missing', ['CIT_SOURCE', 'MAIN_SOURCE'])
def test_missing_pin_never_matches_missing_asset(monkeypatch, missing):
    forms = observed()
    url = getattr(module(), missing)
    forms[-1]['projection']['builds'][url] = None
    monkeypatch.setattr(module(), 'BUILD_DIGESTS', {key: value for key, value in
                       module().BUILD_DIGESTS.items() if key != url})
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l11b_binding'


@pytest.mark.parametrize('defect', ['model', 'status', 'native-model', 'induk-order', 'legacy-route', 'previous'])
def test_selected_submitted_lifecycle_is_required(defect):
    forms, record, packet = observed(), selected(), primary()
    forms[0].pop('projection')
    if defect == 'model':
        record['meta']['Model SPT'] = 'Amendment 002'
    elif defect == 'status':
        record['source_status'] = 'SPT Draft'
    elif defect == 'native-model':
        record['source_fields']['ReturnSheetModel'] = 'Amendment 002'
    elif defect == 'induk-order':
        forms.reverse()
    elif defect == 'legacy-route':
        packet['context']['frame_url'] = corpus.FRAME_URL
        forms[-1]['projection']['route'] = corpus.FRAME_URL
    else:
        packet = primary(previous='not-json')
    result = adapt(forms, packet, record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l11b_submitted_lifecycle'


@pytest.mark.parametrize('previous', [None, 'null', '{}'])
def test_explicit_previous_encoding_preserves_current_only_form(previous):
    result = adapt(packet=primary(previous=previous))
    assert result['eligible'], result['reason']


@pytest.mark.parametrize('previous', [False, '[]', 'not-json'])
def test_bad_previous_encoding_refuses(previous):
    result = adapt(packet=primary(previous=previous))
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l11b_submitted_lifecycle'


def test_missing_required_source_key_is_not_an_empty_control():
    value = form()
    value.pop('Ebitda')
    with pytest.raises(_UnsupportedMetadata, match='^unsupported_corporate_l11b_source_shape$'):
        project(value)


def test_absent_body_tables_project_as_empty_not_refusal():
    value = form()
    for key in ('BorrowingCosts', 'DebtBalanceAverage', 'EquityBalanceAverage'):
        value.pop(key)
    result = project(value)
    assert result['tables'] and all(t['body_row_count'] == 0 for t in result['tables'])


def test_adapter_preserves_custody_and_explicit_omissions():
    forms, packet = observed(), primary()
    before, raw = deepcopy(forms), packet['body']
    result = adapt(forms, packet)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert forms == before and packet['body'] == raw
    section, = [item for item in result['sections'] if item['name'] == 'L11-B']
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_l11b_lifecycle'
    assert len(section['fields']) == 4 and section['tables'][-1]['name'] == 'L11-B/costs'
    assert section['tables'][0]['headers'] == ['JSON path', 'JSON type', 'Source value']
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L11-B']
    assert all(entry['response_sequence'] == 1 and
               entry['container'] == ['Payload', 'CurrentFormData'] for entry in projected['values'])
    assert any(entry['path'] == ['L11BFormData', 'IsEbitdaManuallyEdited']
               and entry['type'] == 'boolean' and entry['value'] is True
               for entry in projected['values'])


def test_adapter_to_saved_workbook_keeps_partial_audit(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    result = adapt()
    assert result['eligible'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L11-B']
    run = source_run('PPh Badan', [section])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L11-B']
        assert [sheet.cell(row, 2).value for row in range(2, 6)] == [1000000, 200000, 50000, 80000]
        assert sheet['B6'].value is None and sheet['B7'].value is None
        assert not any(cell.data_type == 'f' for row in sheet for cell in row)
        assert any(row[0].value == 'SYNTHETIC LENDER' and row[1].value == 1000
                   and row[4].value == 30 for row in sheet)
        report, = reports
        assert report['complete'] is False and report['derived_complete'] is False
        assert report['derived_reason'] == 'unprojected_l11b_lifecycle'
        assert report['unmapped_rows'] > 0
    finally:
        book.close()
    resume = load_workbook(tmp_path / 'resume.xlsx')
    try:
        assert any('L11-B diproyeksikan sebagian' in str(cell.value)
                   for sheet in resume for row in sheet for cell in row)
    finally:
        resume.close()
