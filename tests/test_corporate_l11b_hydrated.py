"""Bounded submitted L11-B View, not the edit-dialog monthly mean (Actions only)."""
from copy import deepcopy
from fractions import Fraction

import pytest

from coretax_json import _CorporateNumber as Number, _UnsupportedMetadata
import support_json_corpus as corpus
from test_corporate_l11b_projection import (module, form, primary, observed, adapt as legacy_adapt,
                                           route, selected)


DEBT_HEADERS = ['PEMBERI PINJAMAN / ' + label for label in ('Nomor Identitas', 'Nama', 'Hubungan')] + [
    'SALDO UTANG TIAP AKHIR BULAN (Rp) / ' + label for label in
    [*[f'Bulan - {month}' for month in range(1, 13)], 'RATA-RATA']]
EQUITY_HEADERS = ['RINCIAN MODAL'] + ['SALDO MODAL TIAP AKHIR BULAN (Rp) / ' + label for label in
    [*[f'Bulan - {month}' for month in range(1, 13)], 'RATA-RATA']]


def selected_hydrated():
    record = selected()
    # This source owner is mandatory for the manifest's existing SPA lifetime.
    # The restricted-v1 fixtures intentionally do not require that capability.
    record['source_fields']['ReturnSheetTypeCode'] = 'ICT_RCITR'
    return record


def adapt(forms=None, packet=None):
    return legacy_adapt(forms=forms, packet=packet, record=selected_hydrated())


def populated(**overrides):
    # Stored Average deliberately differs from BOTH sum/12 and populated mean.
    debt = {'IdentityNumber': '0007', 'Name': 'SYNTHETIC CREDITOR', 'Relationship': 'Independent',
            **{f'DebtMonth{month}': Number(str(month)) for month in range(1, 13)},
            'Average': Number('1000')}
    equity = {'TypeOfEquity': 'SYNTHETIC CAPITAL',
              **{f'EquityMonth{month}': Number(str(month * 2)) for month in range(1, 13)},
              'Average': Number('400')}
    return form(**{'BorrowingCostExpense': Number('400000'), 'DebtBalanceAverage': [debt, deepcopy(debt)],
        'EquityBalanceAverage': [equity, deepcopy(equity)],
        # These DTO controls are overwritten; they are NOT the View footer.
        'TotalDebtBalanceAverage': None, 'TotalEquityBalanceAverage': None,
        'DebtToEquityRatio': None, 'Ebitda': Number('7'), 'Ebitda25': Number('312500'), **overrides})


def tables(part_ii=True):
    labels = ([('rsh-citr-l11b-form-grid1', DEBT_HEADERS, [[3] + [1] * 13]),
               ('rsh-citr-l11b-form-grid2', EQUITY_HEADERS, [[1] * 14])] if part_ii else [])
    labels.append(('rsh-citr-l11b-form-grid3', module().L11B_COST_HEADERS, [[1] * 5]))
    groups = ([['II. PERBANDINGAN ANTARA UTANG DAN MODAL (DEBT TO EQUITY RATIO)', group]
        for group in ('A. PENGHITUNGAN RATA-RATA SALDO UTANG', 'B. PENGHITUNGAN SALDO RATA-RATA MODAL')]
        if part_ii else []) + [['III. PENGHITUNGAN BIAYA PINJAMAN']]
    return [{'component': component, 'headers': list(headers), 'footer_spans': spans,
             'source_structure': {'form': 'L11-B', 'component': component, 'groups': group}}
            for (component, headers, spans), group in zip(labels, groups)]


def bindings(part_ii=True):
    forms = observed()
    forms[-1]['projection'] = {'kind': 'corporate-l11b-hydrated-v2',
        'builds': dict(module().L11C_BUILD_DIGESTS), 'route': route(),
        'part_ii': part_ii, 'tables': tables(part_ii)}
    return forms


def packet(value=None):
    result = primary(populated() if value is None else value)
    result['context']['component_lifetime'] = {
        'attempt': corpus.ATTEMPT, 'kind': 'corporate-submitted-spa-v1',
        'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': route(),
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True}
    return result


def project(value=None, part_ii=True):
    helper = getattr(module(), 'project_l11b_hydrated', None)
    assert callable(helper), 'Missing submitted hydrated L11-B projection'
    return helper(populated() if value is None else value, tax_type='ICT_RCIT',
                  locale='id-ID', part_ii=part_ii)


def test_view_projects_hydrated_ebitda_and_actual_saved_row_averages():
    result = project()
    assert [field['value'] for field in result['fields']] == [
        '1.000.000', '200.000', '50.000', '400.000', '1.250.000', '312.500']
    debt, equity, cost = result['tables']
    assert debt['headers'] == DEBT_HEADERS and equity['headers'] == EQUITY_HEADERS
    assert debt['rows'][:2] == [['0007', 'SYNTHETIC CREDITOR', 'Independent',
        *map(str, range(1, 13)), '1.000']] * 2
    assert debt['footer'] == [['JUMLAH', *map(str, range(2, 25, 2)), '2.000']]
    assert len(debt['footer'][0]) == len(debt['footer_spans'][0]) == 14
    assert sum(debt['footer_spans'][0]) == len(debt['headers']) == 16
    assert equity['footer'] == [['JUMLAH', *map(str, range(4, 49, 4)), '800']]
    assert result['der_operands'] == [2000, 800]
    assert Fraction(*result['der_operands']) == Fraction(5, 2)
    assert cost['body_row_count'] == 1
    ebitda = [e for e in result['provenance'] if e['rule'] == 'submitted-disable-ebitda-operand']
    assert {tuple(e['path']) for e in ebitda} == {('L11BFormData', name) for name in (
        'CommercialNettIncome', 'DepreciationAndAmortizationExpenses', 'IncomeTaxExpense')}
    assert any(e['path'] == ['L11BFormData', 'DebtBalanceAverage', 1, 'Average']
               and e['rule'] == 'view-model-ordered-sum-operand' for e in result['provenance'])


def test_conditional_hidden_profile_never_fabricates_empty_monthly_tables():
    result = project(populated(BorrowingCostExpense=Number('1')), part_ii=False)
    assert [t['name'] for t in result['tables']] == ['L11-B/costs']
    assert result['der_operands'] is None
    assert [f['value'] for f in result['fields']][-2:] == ['1.250.000', '312.500']


@pytest.mark.parametrize('shown,cost', [(True, '1'), (False, '400000')])
def test_conditional_observation_must_match_source_predicate(shown, cost):
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l11b_conditional'):
        project(populated(BorrowingCostExpense=Number(cost)), part_ii=shown)


@pytest.mark.parametrize('value', [None, []])
def test_empty_monthly_getters_preserve_original_null_vs_array(value):
    result = project(populated(DebtBalanceAverage=value, EquityBalanceAverage=value))
    assert result['der_operands'] == [0, 0]
    assert result['tables'][0]['footer'] == [['JUMLAH', *(['0'] * 13)]]
    evidence = [e for e in result['provenance'] if e['rule'] == 'empty-view-model-total']
    assert len(evidence) == 26
    assert all(e['type'] == ('null' if value is None else 'array') and e['value'] == value for e in evidence)


@pytest.mark.parametrize('key,value,reason', [
    ('Average', Number('0.3333333333333333'), 'amount_precision'),
    ('Average', Number('1.25'), 'amount_precision'),
    ('Average', None, 'amount_type'), ('DebtMonth1', None, 'amount_type'),
    ('DebtMonth1', '', 'amount_type'), ('Average', True, 'amount_type'),
    ('Average', '1000', 'amount_type'), ('DebtMonth1', Number('-0'), 'signed_zero'),
    # The shared decimal validator refuses >binary64-safe before L11-B's bound.
    ('DebtMonth1', Number('9007199254740992'), 'amount_type'),
])
def test_monthly_precision_and_null_are_not_editor_mean_permission(key, value, reason):
    source = populated()
    source['DebtBalanceAverage'][0][key] = value
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l11b_' + reason):
        project(source)


def test_sum_and_ebitda_intermediates_are_checked_before_final_cancellation():
    source = populated()
    for row in source['DebtBalanceAverage']:
        row['Average'] = Number('999999999999999')
    with pytest.raises(_UnsupportedMetadata, match='unsafe_corporate_l11b_ordered_total'):
        project(source)
    source = populated(CommercialNettIncome=Number('999999999999999'),
                       DepreciationAndAmortizationExpenses=Number('1'), IncomeTaxExpense=Number('-1'))
    with pytest.raises(_UnsupportedMetadata, match='unsafe_corporate_l11b_ordered_total'):
        project(source)


@pytest.mark.parametrize('change', [
    {'Ebitda25': Number('1')}, {'IncomeTaxExpense': None},
    {'IsEbitdaManuallyEdited': False}, {'TotalBorrowingCosts': None},
])
def test_unproved_callback_profiles_remain_unsupported(change):
    with pytest.raises(_UnsupportedMetadata):
        project(populated(**change))


def test_der_does_not_round_an_unsupported_ratio_into_a_supported_operand():
    source = populated()
    source['EquityBalanceAverage'][0]['Average'] = Number('200')
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l11b_der_precision'):
        project(source)  # 2000/600 repeats; never round an operand or ratio.


def test_hydrated_adapter_retains_original_overwritten_controls_and_custody():
    forms, source = bindings(), packet()
    before = deepcopy((forms, source))
    result = adapt(forms=forms, packet=source)
    assert result['eligible'], result['reason']
    assert (forms, source) == before
    section = next(s for s in result['sections'] if s['name'] == 'L11-B')
    assert len(section['fields']) == 6 and len(section['tables']) == 4
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_l11b_header_question'
    projected = next(p for p in result['provenance']['projections'] if p['form'] == 'L11-B')
    assert all(e['response_sequence'] == 1 and e['container'] == (
        ['Payload'] if e['rule'] == 'submitted-hydration-predicate' else ['Payload', 'CurrentFormData'])
        for e in projected['values'])
    assert any(e['path'] == ['PreviousFormData'] and e['type'] == 'null' and e['value'] is None
               for e in projected['values'])
    assert any(e['path'] == ['L11BFormData', 'Ebitda'] and e['value'] == '7'
               and e['rule'] == 'unused-saved-control' for e in projected['values'])


@pytest.mark.parametrize('defect', ['lifetime', 'wrong-pin', 'missing-pin', 'header', 'footer', 'component',
                                   'part-ii', 'previous', 'induk-order'])
def test_hydrated_binding_rejects_missing_or_contradictory_proof(defect):
    forms, source = bindings(), packet()
    proof = forms[-1]['projection']
    if defect == 'lifetime': source['context'].pop('component_lifetime')
    elif defect == 'wrong-pin': proof['builds'][module().VENDOR_SOURCE] = 'a' * 64
    elif defect == 'missing-pin': proof['builds'].pop(module().VENDOR_SOURCE)
    elif defect == 'header': proof['tables'][0]['headers'][0] += ' FOREIGN'
    elif defect == 'footer': proof['tables'][1]['footer_spans'] = [[14]]
    elif defect == 'component': proof['tables'][0]['component'] = 'foreign-grid'
    elif defect == 'part-ii': proof['part_ii'] = None
    elif defect == 'previous':
        source = primary(populated(), previous='{}')
        source['context']['component_lifetime'] = packet()['context']['component_lifetime']
    else: forms.reverse()
    result = adapt(forms=forms, packet=source)
    assert not result['eligible']


def test_hydrated_saved_workbook_keeps_unrounded_der_references_and_partial_resume(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    result = adapt(forms=bindings(), packet=packet())
    assert result['eligible'], result['reason']
    section = next(s for s in result['sections'] if s['name'] == 'L11-B')
    run = source_run('PPh Badan', [section])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [p for p in paths if p != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L11-B']
        assert sheet['B6'].value == 1250000 and sheet['B7'].value == 312500
        assert sum(cell.value == '0007' for row in sheet for cell in row) == 2
        row, = [r for r in range(1, sheet.max_row + 1) if sheet.cell(r, 1).value == 'PERHITUNGAN DER']
        debt = sheet.cell(row, 3).value.removeprefix('=')
        capital = sheet.cell(row + 1, 3).value.removeprefix('=')
        assert sheet[debt].value == 2000 and sheet[capital].value == 800
        assert sheet.cell(row, 4).value == f'=C{row}/C{row + 1}'
        assert reports[0]['complete'] is False
        assert reports[0]['derived_reason'] == 'unprojected_l11b_header_question'
        assert reports[0]['unmapped_rows'] > 0
    finally:
        book.close()
    resume = load_workbook(tmp_path / 'resume.xlsx')
    try:
        assert any('header/pertanyaan L11-B' in str(cell.value)
                   for sheet in resume for row in sheet for cell in row)
    finally:
        resume.close()


@pytest.mark.parametrize('commercial,quarter', [('-200004', '-1'), ('-200001', '-1'), ('-200000', '0')])
def test_nonpositive_ebitda_uses_floor_not_truncation(commercial, quarter):
    source = populated(CommercialNettIncome=Number(commercial), IncomeTaxExpense=Number('0'),
                       BorrowingCostExpense=Number('0'), Ebitda25=Number(quarter))
    result = project(source)
    assert result['tables'][0]['name'] == 'L11-B/debt'
    assert result['fields'][-1]['value'] == quarter


def test_exact_quarter_boundary_hides_part_ii():
    result = project(populated(BorrowingCostExpense=Number('312500')), part_ii=False)
    assert len(result['tables']) == 1


@pytest.mark.parametrize('key,value', [('DebtBalanceAverage', {}), ('EquityBalanceAverage', [None]),
                                     ('DebtBalanceAverage', [{'Average': Number('1')}])])
def test_monthly_container_and_closed_row_contract(key, value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l11b_month_'):
        project(populated(**{key: value}))


def test_numeric_token_is_not_literal_identity_text():
    source = populated()
    source['DebtBalanceAverage'][0]['IdentityNumber'] = Number('7')
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l11b_text'):
        project(source)


@pytest.mark.parametrize('debt,equity', [('0', '1'), ('1', '0'), ('999999999999999', '1')])
def test_unrepresentable_der_does_not_emit_a_formula(debt, equity):
    source = populated()
    source['DebtBalanceAverage'] = [source['DebtBalanceAverage'][0]]
    source['EquityBalanceAverage'] = [source['EquityBalanceAverage'][0]]
    source['DebtBalanceAverage'][0]['Average'] = Number(debt)
    source['EquityBalanceAverage'][0]['Average'] = Number(equity)
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l11b_der_precision'):
        project(source)


def test_saved_totals_are_unused_metadata_not_captured_view_footer_aliases():
    source = populated(TotalDebtBalanceAverage={'Average': Number('999')},
                       TotalEquityBalanceAverage={'Average': Number('999')}, DebtToEquityRatio=Number('999'))
    before = deepcopy(source)
    result = project(source)
    assert result['der_operands'] == [2000, 800] and source == before
    raw = packet(source)
    result = adapt(forms=bindings(), packet=raw)
    assert result['eligible'], result['reason']
    section = next(s for s in result['sections'] if s['name'] == 'L11-B')
    assert any('TotalDebtBalanceAverage' in str(row[0]) for row in section['tables'][0]['rows'])


def test_hydrated_missing_configured_pin_never_matches_missing_provider(monkeypatch):
    forms = bindings()
    pins = dict(module().L11B_HYDRATED_BUILD_DIGESTS)
    pins[module().VENDOR_SOURCE] = None
    forms[-1]['projection']['builds'][module().VENDOR_SOURCE] = None
    monkeypatch.setattr(module(), 'L11B_HYDRATED_BUILD_DIGESTS', pins)
    result = adapt(forms=forms, packet=packet())
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l11b_binding'


def test_hydrated_headers_are_the_approved_existing_slots():
    from openpyxl import load_workbook
    from test_corporate_l11b_projection import RESOURCE
    book = load_workbook(RESOURCE, read_only=True)
    try:
        assert [cell.value for cell in book['L11-B'][11]][:16] == DEBT_HEADERS
        assert [cell.value for cell in book['L11-B'][17]][:14] == EQUITY_HEADERS
    finally: book.close()


def test_encoded_null_predecessor_retains_the_original_string_provenance():
    source = primary(populated(), previous='null')
    source['context']['component_lifetime'] = packet()['context']['component_lifetime']
    result = adapt(forms=bindings(), packet=source)
    assert result['eligible'], result['reason']
    values = next(p['values'] for p in result['provenance']['projections'] if p['form'] == 'L11-B')
    assert any(e['path'] == ['PreviousFormData'] and e['type'] == 'string' and e['value'] == 'null'
               and e['container'] == ['Payload'] for e in values)
