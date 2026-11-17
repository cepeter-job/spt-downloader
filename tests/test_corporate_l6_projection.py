"""Reviewed L6 (Angsuran PPh 25) projection contracts; GitHub-runner execution only.

Every displayed amount maps to one literal payload control of the pinned L6
owner, and the two subtractions that owner performs are re-checked exactly.
"""
import importlib

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus


def module():
    return importlib.import_module('coretax_corporate_projection')


def form(**overrides):
    value = {
        'IncomeAsTheBasisOfInstallment': _CorporateNumber('100000000'),
        'IncomeAsTheBasisOfInstallmentEdited': False,
        'FiscalLossCompensation': _CorporateNumber('25000000'),
        'TaxableIncome': _CorporateNumber('75000000'),
        'IncomeTaxPayable': _CorporateNumber('16500000'),
        'IncomeTaxPayableEdited': False,
        'TaxCreditWitheld': _CorporateNumber('1500000'),
        'TaxCreditWitheldEdited': False,
        'IncomeTaxSelfpaid': _CorporateNumber('15000000'),
        'FollowingFiscalYear': _CorporateNumber('1250000'),
    }
    value.update(overrides)
    return value


def project(payload=None, **overrides):
    helper = getattr(module(), 'project_l6', None)
    assert callable(helper), 'Missing reviewed L6 projection'
    options = {'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    return helper(form() if payload is None else payload, **options)


def module_or(name):
    return getattr(module(), name)


def observed():
    forms = corpus.observed()
    binding = {'name': 'L6', 'paths': [['FiscalYearIncomeTax']], 'grids': [],
               'responses': [], 'dependencies': [],
               'projection': {'kind': 'corporate-l6-v1',
                              'builds': {module_or('CIT_SOURCE'): module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': corpus.FRAME_URL}}
    forms.insert(1, binding)
    return forms


def payload_form(l6=None):
    """Same amounts, but wired as raw JSON number tokens for the adapter."""
    value = dict(form() if l6 is None else l6)
    for name, _ in module().L6_FIELDS:
        value[name] = corpus.Number(str(value[name]))
    return value


def primary(l6=None):
    form_value = corpus.current_form()
    form_value['FiscalYearIncomeTax'] = payload_form(l6)
    return corpus.primary(form_value)


def adapt(forms=None, payload=None, record=None):
    return adapt_corporate_detail(iter([primary() if payload is None else payload]),
                                  corpus.selected_record() if record is None else record,
                                  corpus.SCOPE, observed() if forms is None else forms)


def test_every_template_caption_comes_from_one_proven_payload_control():
    fields = getattr(module(), 'L6_FIELDS', None)
    assert fields is not None, 'Missing reviewed L6 caption map'
    result = project()
    assert [field['field'] for field in result['fields']] == [name for name, _ in fields]
    assert [field['label'] for field in result['fields']] == [caption for _, caption in fields]
    assert [field['value'] for field in result['fields']] == [
        '100.000.000', '25.000.000', '75.000.000', '16.500.000',
        '1.500.000', '15.000.000', '1.250.000']
    assert [entry['path'] for entry in result['provenance']] == [
        ['FiscalYearIncomeTax', name] for name, _ in fields]


def test_taxable_income_and_self_paid_tax_must_reconcile_exactly():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(TaxableIncome=_CorporateNumber('74999999')))
    assert str(error.value) == 'unreconciled_corporate_l6_taxable_income'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(IncomeTaxSelfpaid=_CorporateNumber('14000000')))
    assert str(error.value) == 'unreconciled_corporate_l6_self_paid_tax'


def test_loss_above_the_basis_floors_the_derived_amounts_at_zero():
    result = project(form(FiscalLossCompensation=_CorporateNumber('100000000'),
                          TaxableIncome=_CorporateNumber('0'),
                          IncomeTaxPayable=_CorporateNumber('0'),
                          TaxCreditWitheld=_CorporateNumber('0'),
                          IncomeTaxSelfpaid=_CorporateNumber('0'),
                          FollowingFiscalYear=_CorporateNumber('0')))
    assert [field['value'] for field in result['fields']][2] == '0'


@pytest.mark.parametrize('mutation,reason', [
    ({'TaxableIncome': '75000000'}, 'unsupported_corporate_l6_amount_type'),
    ({'FollowingFiscalYear': True}, 'unsupported_corporate_l6_amount_type'),
    ({'IncomeTaxPayable': _CorporateNumber('-1'),
      'IncomeTaxSelfpaid': _CorporateNumber('0')}, 'unsupported_corporate_l6_negative_amount'),
    ({'Synthetic': _CorporateNumber('0')}, 'unsupported_corporate_l6_source_shape'),
])
def test_unreviewed_l6_shapes_refuse(mutation, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(**mutation))
    assert str(error.value) == reason


def test_missing_edit_marker_refuses_the_source_shape():
    value = form()
    value.pop('IncomeTaxPayableEdited')
    with pytest.raises(_UnsupportedMetadata) as error:
        project(value)
    assert str(error.value) == 'unsupported_corporate_l6_source_shape'


def test_absent_l6_root_refuses_the_capture():
    forms = observed()
    form_value = corpus.current_form()
    result = adapt_corporate_detail(iter([corpus.primary(form_value)]), corpus.selected_record(),
                                    corpus.SCOPE, forms)
    assert not result['eligible']
    assert result['reason'] == 'missing_observed_corporate_source_path'


@pytest.mark.parametrize('projection', [
    {'kind': 'corporate-l6-v0'},
    {'kind': 'corporate-l6-v1', 'builds': {}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l6-v1', 'builds': {module_or('CIT_SOURCE'): 'APPROVED'}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l6-v1', 'builds': {module_or('CIT_SOURCE'): 'a' * 64},
     'route': corpus.FRAME_URL, 'timezone': 'Asia/Jakarta'},
])
def test_projection_proof_must_match_the_reviewed_shape(projection):
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L6']
    binding['projection'] = projection
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l6_binding'


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L6']
    binding['projection'] = {**binding['projection'], 'route': corpus.FRAME_URL + '/changed'}
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l6_binding'
    forms = observed()
    # Drop the Induk projection so this isolates the L6 lifecycle gate.
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l6_submitted_lifecycle'


def test_projected_l6_section_replaces_the_dump_and_reports_complete():
    forms = observed()
    result = adapt(forms)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L6']
    assert section['tables'] == []
    assert [field['field'] for field in section['fields']] == [name for name, _ in module().L6_FIELDS]
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L6']
    assert projected['kind'] == 'corporate-l6-v1'
    assert len(projected['values']) == len(module().L6_FIELDS)


def test_l6_projection_does_not_mutate_source_bindings_or_payload():
    from copy import deepcopy
    forms = observed()
    before = deepcopy(forms)
    payload = primary()
    raw = payload['body']
    adapt(forms, payload=payload)
    assert forms == before and payload['body'] == raw


def test_projected_l6_binds_every_template_amount_cell(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import section, source_run
    fields = project()['fields']
    run = source_run('PPh Badan', [section('L6', fields=fields)])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L6']
        assert [sheet.cell(row, 2).value for row in range(2, 9)] == [
            100_000_000, 25_000_000, 75_000_000, 16_500_000, 1_500_000, 15_000_000, 1_250_000]
        assert all(sheet.cell(row, 2).data_type == 'n' for row in range(2, 9))
        assert reports[0]['complete'] is True
        assert reports[0]['unmapped_fields'] == reports[0]['unmapped_tables'] == 0
    finally:
        book.close()
