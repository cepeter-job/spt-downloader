"""L2 safety quarantine contracts; GitHub-runner execution only.

Populated owners are not native-equivalent. Keep all source evidence and the
whole-record fallback gate even for the bounded empty-only candidate.
"""
import importlib
from copy import deepcopy

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus


def module():
    return importlib.import_module('coretax_corporate_projection')


def module_or(name):
    return getattr(module(), name)


def affiliate(index, **overrides):
    value = {
        'Name': f'SYNTHETIC AFFILIATE {index}',
        'CountryCode': 'SG',
        'TIN': '0000000000000002',
        'Investment': _CorporateNumber('1000.00'),
        'InvestmentPercentage': _CorporateNumber('25.0000'),
        'Debt': _CorporateNumber('2000.00'),
        'DebtYear': '2025',
        'DebtInterest': _CorporateNumber('3.5000'),
        'Receivable': _CorporateNumber('4000.00'),
        'ReceivableYear': _CorporateNumber('2024'),
        'ReceivableInterest': _CorporateNumber('1.2500'),
    }
    value.update(overrides)
    return value


def shareholder(**overrides):
    value = {
        'Name': 'SYNTHETIC OWNER',
        'Address': 'SYNTHETIC ADDRESS',
        'CountryCode': 'ID',
        'TIN': '0000000000000009',
        'Position': '01',
        'SubPosition': None,
        'PaidInCapital': _CorporateNumber('5000.00'),
        'PaidInCapitalPercentage': _CorporateNumber('100.0000'),
        'Dividend': _CorporateNumber('10000.00'),
    }
    value.update(overrides)
    return value


def form(**overrides):
    value = {'ListOfShareholders': None, 'InvestmentList': None,
             **{key: _CorporateNumber('0') for key in (
                'TotalPaidInCapital', 'TotalPaidInCapitalPercentage', 'TotalDividend',
                'TotalDebt', 'TotalReceivable')}}
    value.update(overrides)
    return value


def project(payload=None, **overrides):
    helper = getattr(module(), 'project_l2', None)
    assert callable(helper), 'Missing reviewed L2 projection'
    options = {'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    return helper(form() if payload is None else payload, **options)


def wire(value):
    """Re-encode projection values as raw JSON number tokens for the adapter."""
    if isinstance(value, _CorporateNumber):
        return corpus.Number(str(value))
    if isinstance(value, dict):
        return {key: wire(item) for key, item in value.items()}
    if isinstance(value, list):
        return [wire(item) for item in value]
    return value


def payload_form(l2=None):
    return wire(form() if l2 is None else l2)


def primary(l2=None):
    form_value = corpus.current_form()
    form_value['ListOfOwnership'] = payload_form(l2)
    return corpus.primary(form_value)


def observed():
    forms = corpus.observed()
    binding = {'name': 'L2', 'paths': [['ListOfOwnership']], 'grids': [],
               'responses': [], 'dependencies': [],
               'projection': {'kind': 'corporate-l2-v1',
                              'builds': {module_or('CIT_SOURCE'):
                                         module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': corpus.FRAME_URL}}
    forms.insert(1, binding)
    return forms


def adapt(forms=None, payload=None, record=None):
    return adapt_corporate_detail(iter([primary() if payload is None else payload]),
                                  corpus.selected_record() if record is None else record,
                                  corpus.SCOPE, observed() if forms is None else forms)


def l2_section(result):
    section, = [item for item in result['sections'] if item['name'] == 'L2']
    return section


def template_captions(form='L2', header=12):
    from openpyxl import load_workbook
    from pathlib import Path
    reference = load_workbook(Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx')
    try:
        captions = [cell.value for cell in reference[form][header]]
    finally:
        reference.close()
    while captions and captions[-1] is None:
        captions.pop()
    return captions


def test_every_affiliate_caption_is_the_approved_template_header():
    table, = project()['tables']
    assert table['headers'] == module().L2_AFFILIATE_HEADERS == template_captions()
    assert table['body_row_count'] == table['source_total'] == 0
    assert table['rows'] == table['footer'] == [['', 'JUMLAH', '0', '', '0', '']]
    assert table['footer_spans'] == [[1, 5, 1, 2, 1, 2]]


@pytest.mark.parametrize('row', [affiliate(1), affiliate(1, CountryCode=None),
    affiliate(1, CountryCode=''), affiliate(1, Investment=None),
    affiliate(1, Investment=_CorporateNumber('1.25')),
    affiliate(1, DebtInterest=_CorporateNumber('4.38')),
    affiliate(1, InvestmentPercentage=_CorporateNumber('1.23456')),
    affiliate(1, Debt=_CorporateNumber('999999999999999.99'))])
def test_no_country_null_currency_or_fraction_profile_grants_affiliate_permission(row):
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l2_affiliate_rendering'):
        project(form(InvestmentList=[row]))


@pytest.mark.parametrize('body', ['ListOfShareholders', 'InvestmentList'])
@pytest.mark.parametrize('value', [{}, '', True, 0])
def test_wrong_typed_owner_bodies_refuse(body, value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l2_body'):
        project(form(**{body: value}))


@pytest.mark.parametrize('field', ['TotalPaidInCapital', 'TotalPaidInCapitalPercentage',
    'TotalDividend', 'TotalDebt', 'TotalReceivable'])
@pytest.mark.parametrize('value', [None, True, 0, '0', _CorporateNumber('-0'),
    _CorporateNumber('0.001'), _CorporateNumber('1'), _CorporateNumber('NaN'),
    _CorporateNumber('1e100000'), _CorporateNumber('0e0')])
def test_empty_owner_requires_explicit_reviewed_numeric_zero_totals(field, value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l2_empty_total'):
        project(form(**{field: value}))


@pytest.mark.parametrize('shareholders,affiliates', [(None, None), ([], None), (None, []), ([], [])])
@pytest.mark.parametrize('lexeme', ['0', '0.0', '0.00'])
def test_empty_owner_preserves_zero_lexemes_without_synthesizing_source(shareholders, affiliates, lexeme):
    value = form(ListOfShareholders=shareholders, InvestmentList=affiliates,
                 **{key: _CorporateNumber(lexeme) for key in module().L2_TOTALS})
    before = deepcopy(value)
    projected = project(value)
    assert value == before
    assert [entry['path'] for entry in projected['provenance']] == [
        ['ListOfOwnership', key] for key in module().L2_TOTALS]
    assert all(entry['type'] == 'number' and entry['value'] == lexeme
               and entry['rule'] == 'validated-empty-owner-zero'
               for entry in projected['provenance'])


@pytest.mark.parametrize('option,value', [('tax_type', 'ICT_ROGCIT'), ('locale', 'en-US')])
def test_unreviewed_tax_or_locale_refuses(option, value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l2_structure'):
        project(**{option: value})


@pytest.mark.parametrize('value', [None, [], ''])
def test_nonobject_root_refuses(value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l2_structure'):
        module().project_l2(value, tax_type='ICT_RCIT', locale='id-ID')


@pytest.mark.parametrize('change', ['missing', 'extra'])
def test_closed_root_key_inventory_refuses_drift(change):
    value = form()
    if change == 'missing':
        value.pop('TotalDebt')
    else:
        value['SYNTHETIC'] = None
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l2_source_shape'):
        project(value)


def test_empty_only_candidate_preserves_entire_dump_and_cannot_bypass_capture_gate():
    from coretax_json import has_audit_dump_tables
    result = adapt()
    assert result['eligible'], result['reason']  # Adapter eligibility is NOT native capture.
    section = l2_section(result)
    table, dump = section['tables']
    assert table['body_row_count'] == 0
    assert dump['headers'] == ['JSON path', 'JSON type', 'Source value']
    assert {row[0] for row in dump['rows']} == {
        '/ListOfOwnership/' + key for key in (*module().L2_TOTALS, 'ListOfShareholders', 'InvestmentList')}
    assert section['fields'] == [] and section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_l2_owner_rendering'
    assert has_audit_dump_tables([section]) is True
    provenance, = [entry for entry in result['provenance']['projections'] if entry['form'] == 'L2']
    assert len(provenance['values']) == len(module().L2_TOTALS)
    assert all(entry['container'] == ['Payload', 'CurrentFormData']
               and entry['response_sequence'] == 1 for entry in provenance['values'])


def test_absent_l2_root_refuses_the_capture():
    forms = observed()
    result = adapt_corporate_detail(iter([corpus.primary(corpus.current_form())]),
                                    corpus.selected_record(), corpus.SCOPE, forms)
    assert not result['eligible']
    assert result['reason'] == 'missing_observed_corporate_source_path'


@pytest.mark.parametrize('projection', [
    {'kind': 'corporate-l2-v0'},
    {'kind': 'corporate-l2-v1', 'builds': {}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l2-v1', 'builds': {module_or('CIT_SOURCE'): 'APPROVED'},
     'route': corpus.FRAME_URL},
    {'kind': 'corporate-l2-v1', 'builds': {module_or('CIT_SOURCE'): 'a' * 64},
     'route': corpus.FRAME_URL, 'locale': 'id-ID'},
])
def test_projection_proof_must_match_the_reviewed_shape(projection):
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L2']
    binding['projection'] = projection
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l2_binding'


def test_a_l2_grid_binding_contradicts_the_payload_only_proof():
    binding, = [item for item in observed() if item['name'] == 'L2']
    binding['grids'] = [{'name': 'L2/synthetic', 'endpoint': corpus.PRIMARY_URL, 'pages': []}]
    section = {'name': 'L2', 'fields': [], 'tables': [], 'text': ''}
    with pytest.raises(_UnsupportedMetadata) as error:
        module()._apply_l2(binding, section, observed(),
                           root={'ListOfOwnership': form()},
                           payload={'ReturnSheetStatusCode': 'SUBMITTED',
                                    'ReturnSheetModel': 'NORMAL'},
                           record=corpus.selected_record(),
                           event={'frame_url': corpus.FRAME_URL, 'sequence': 1})
    assert str(error.value) == 'unverified_corporate_l2_binding'
    assert section['tables'] == [] and section['fields'] == []


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L2']
    binding['projection'] = {**binding['projection'], 'route': corpus.FRAME_URL + '/changed'}
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l2_binding'
    forms = observed()
    # Drop the Induk projection so this isolates the L2 lifecycle gate.
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l2_submitted_lifecycle'
    record = corpus.selected_record()
    record['source_status'] = 'Draft'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l2_submitted_lifecycle'


@pytest.mark.parametrize('body,reason', [
    ('ListOfShareholders', 'unprojected_corporate_l2_shareholder_body'),
    ('InvestmentList', 'unverified_corporate_l2_affiliate_rendering'),
])
def test_populated_owner_blocks_refuse_until_render_equivalence_is_proven(body, reason):
    value = form(ListOfShareholders=None, InvestmentList=None)
    value[body] = [shareholder() if body == 'ListOfShareholders' else affiliate(1)]
    with pytest.raises(_UnsupportedMetadata, match=reason):
        project(value)
    result = adapt(payload=primary(value))
    assert not result['eligible'] and result['reason'] == reason


@pytest.mark.parametrize('digest', ['a' * 64, None, 'APPROVED'])
def test_l2_positive_build_proof_requires_the_reviewed_configured_digest(digest):
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L2']
    binding['projection']['builds'] = {module_or('CIT_SOURCE'): digest}
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l2_binding'


def test_l2_missing_pin_and_missing_asset_never_form_a_positive_build_proof(monkeypatch):
    forms = observed()
    monkeypatch.setattr(module(), 'BUILD_DIGESTS', {})
    binding, = [item for item in forms if item['name'] == 'L2']
    binding['projection']['builds'] = {module_or('CIT_SOURCE'): None}
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l2_binding'


def test_l2_projection_does_not_mutate_source_bindings_or_payload():
    forms = observed()
    before = deepcopy(forms)
    payload = primary()
    raw = payload['body']
    adapt(forms, payload=payload)
    assert forms == before and payload['body'] == raw


def test_empty_candidate_workbook_selects_block_b_footer_and_stays_visibly_partial(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    section = l2_section(adapt())
    run = source_run('PPh Badan', [section])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    resume = load_workbook(tmp_path / 'resume.xlsx')
    try:
        sheet = book['L2']
        # Both A and B contain JUMLAH: scope the footer by the approved B header.
        header = next(row for row in range(1, sheet.max_row + 1)
            if [sheet.cell(row, column).value for column in range(1, 13)]
            == module().L2_AFFILIATE_HEADERS)
        total = next(row for row in range(header + 1, sheet.max_row + 1)
                     if sheet.cell(row, 1).value == 'JUMLAH')
        assert sheet.cell(total, 7).value == sheet.cell(total, 10).value == 0
        assert sheet.cell(total, 7).data_type == sheet.cell(total, 10).data_type == 'n'
        first_total = next(row for row in range(1, header) if sheet.cell(row, 1).value == 'JUMLAH')
        assert sheet.cell(first_total, 7).value is None
        report, = [item for item in reports if item['form'] == 'L2']
        assert report['complete'] is False and report['derived_complete'] is False
        assert report['derived_reason'] == 'unprojected_l2_owner_rendering'
        assert report['unmapped_tables'] == 1
        assert report['unmapped_rows'] == len(section['tables'][1]['rows'])
        audit_text = ' '.join(str(cell.value) for row in resume['Audit'] for cell in row)
        assert 'L2 belum setara dengan tampilan sumber' in audit_text
    finally:
        book.close()
        resume.close()
