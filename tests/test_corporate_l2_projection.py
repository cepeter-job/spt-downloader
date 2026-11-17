"""Reviewed L2 (Daftar Kepemilikan) projection contracts; GitHub-runner execution only.

Every writable caption of the affiliate block maps to one literal `InvestmentList`
control of the pinned L2 owner, and the two footers that owner derives are
re-checked exactly. The shareholder block stays on the generic evidence dump
because its `Jabatan` caption binds to `FullPosition`, a display-only
concatenation of two reference labels the submitted payload never carries.
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
    value = {
        'ListOfShareholders': [shareholder()],
        'TotalPaidInCapital': _CorporateNumber('5000.00'),
        'TotalPaidInCapitalPercentage': _CorporateNumber('0'),
        'TotalDividend': _CorporateNumber('10000.00'),
        'InvestmentList': [affiliate(1), affiliate(2, Debt=_CorporateNumber('500.00'))],
        'TotalDebt': _CorporateNumber('2500.00'),
        'TotalReceivable': _CorporateNumber('8000.00'),
    }
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
    headers = getattr(module(), 'L2_AFFILIATE_HEADERS', None)
    assert headers is not None, 'Missing reviewed L2 affiliate header map'
    table, = project()['tables']
    assert table['headers'] == headers
    assert headers == template_captions()


def test_body_cells_follow_the_proven_column_bindings_in_order():
    table, = project()['tables']
    assert table['body_row_count'] == table['source_total'] == 2
    assert table['rows'][0] == ['1', 'SYNTHETIC AFFILIATE 1', 'SG', '0000000000000002',
                                '1.000,00', '25,0000', '2.000,00', '2025', '3,5000',
                                '4.000,00', '2024', '1,2500']
    # The reviewed owner separates three money controls, two percentage
    # controls and two literal four-digit year controls.
    assert table['rows'][1][1:4] == ['SYNTHETIC AFFILIATE 2', 'SG', '0000000000000002']
    assert table['rows'][1][6] == '500,00'
    rows, footer = table['rows'][:2], table['rows'][2]
    assert table['footer'] == [footer] and footer == ['', 'JUMLAH', '2.500,00', '', '8.000,00', '']
    assert table['footer_spans'] == [[1, 5, 1, 2, 1, 2]]
    assert rows == [['1', 'SYNTHETIC AFFILIATE 1', 'SG', '0000000000000002', '1.000,00',
                     '25,0000', '2.000,00', '2025', '3,5000', '4.000,00', '2024', '1,2500'],
                    ['2', 'SYNTHETIC AFFILIATE 2', 'SG', '0000000000000002', '1.000,00',
                     '25,0000', '500,00', '2025', '3,5000', '4.000,00', '2024', '1,2500']]


def test_provenance_names_the_literal_control_of_every_written_cell():
    result = project()
    expected = {2: ('Name', 'literal-source'), 3: ('CountryCode', 'literal-source'),
                4: ('TIN', 'literal-source'), 5: ('Investment', 'number-id-fraction-2'),
                6: ('InvestmentPercentage', 'number-id-fraction-4'),
                7: ('Debt', 'number-id-fraction-2'), 8: ('DebtYear', 'literal-year-text'),
                9: ('DebtInterest', 'number-id-fraction-4'),
                10: ('Receivable', 'number-id-fraction-2'),
                11: ('ReceivableYear', 'literal-year-text'),
                12: ('ReceivableInterest', 'number-id-fraction-4')}
    bound = {}
    for entry in result['provenance']:
        destination = entry['destination']
        if 'row' not in destination:
            continue
        field, rule = expected[destination['column']]
        assert entry['path'] == ['ListOfOwnership', 'InvestmentList', destination['row'], field]
        assert entry['rule'] == rule
        bound[destination['column']] = field
    assert bound == {column: field for column, (field, _) in expected.items()}
    assert [entry['path'] for entry in result['provenance']
            if entry['rule'] == 'reconciled-model-ordered-sum'] == [
        ['ListOfOwnership', 'TotalDebt'], ['ListOfOwnership', 'TotalReceivable']]
    assert [entry['path'] for entry in result['provenance']
            if entry['rule'] == 'non-displayed-shareholder-total'] == [
        ['ListOfOwnership', 'TotalPaidInCapital'],
        ['ListOfOwnership', 'TotalPaidInCapitalPercentage'],
        ['ListOfOwnership', 'TotalDividend']]


@pytest.mark.parametrize('mutation,reason', [
    ({'TotalDebt': _CorporateNumber('2501.00')}, 'unreconciled_corporate_l2_total_debt'),
    ({'TotalReceivable': _CorporateNumber('7999.00')}, 'unreconciled_corporate_l2_total_receivable'),
])
def test_derived_footers_must_reconcile_with_the_ordered_rows(mutation, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(**mutation))
    assert str(error.value) == reason


def test_rows_that_disagree_with_the_footer_refuse_even_when_empty():
    value = form(InvestmentList=[], TotalDebt=_CorporateNumber('1.00'))
    with pytest.raises(_UnsupportedMetadata) as error:
        project(value)
    assert str(error.value) == 'unreconciled_corporate_l2_total_debt'


@pytest.mark.parametrize('mutation,reason', [
    ({'Synthetic': _CorporateNumber('0')}, 'unsupported_corporate_l2_source_shape'),
    ({'TotalDebt': _CorporateNumber('2500.005')}, 'unsupported_corporate_l2_total_type'),
    ({'InvestmentList': {}}, 'unsupported_corporate_l2_body'),
    ({'InvestmentList': [affiliate(1, Investment='1000.00')]},
     'unsupported_corporate_l2_amount_type'),
    ({'InvestmentList': [affiliate(1, Debt=_CorporateNumber('-1'))]},
     'unsupported_corporate_l2_negative_amount'),
    ({'InvestmentList': [affiliate(1, InvestmentPercentage=_CorporateNumber('1.23456'))]},
     'unsupported_corporate_l2_amount_precision'),
    ({'InvestmentList': [affiliate(1, RecordId='synthetic')]},
     'unsupported_corporate_l2_affiliate_row'),
    ({'InvestmentList': [affiliate(1, Name=7)]}, 'unsupported_corporate_l2_text'),
    ({'InvestmentList': [affiliate(1, DebtYear='20255')]}, 'unsupported_corporate_l2_year'),
    ({'InvestmentList': [affiliate(1, ReceivableYear=_CorporateNumber('1899'))]},
     'unsupported_corporate_l2_year'),
    ({'InvestmentList': [affiliate(1, IsEditable='yes')]},
     'unsupported_corporate_l2_affiliate_metadata'),
])
def test_unreviewed_l2_shapes_refuse(mutation, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(**mutation))
    assert str(error.value) == reason


def test_absent_affiliate_list_still_renders_the_approved_footer():
    result = project(form(InvestmentList=None, TotalDebt=_CorporateNumber('0'),
                          TotalReceivable=_CorporateNumber('0')))
    table, = result['tables']
    assert table['body_row_count'] == 0
    assert table['rows'] == [['', 'JUMLAH', '0,00', '', '0,00', '']]


def test_absent_cells_stay_blank_instead_of_inventing_a_zero():
    result = project(form(
        InvestmentList=[affiliate(1, Investment=None, DebtYear=None, Receivable=None,
                                  ReceivableInterest=None, IsEditable=None)],
        TotalDebt=_CorporateNumber('2000.00'), TotalReceivable=_CorporateNumber('0')))
    table, = result['tables']
    row = table['rows'][0]
    assert (row[4], row[7], row[9], row[11]) == ('', '', '', '')
    flags = [entry for entry in result['provenance']
             if entry['rule'] == 'non-displayed-row-metadata']
    assert [entry['type'] for entry in flags] == ['null']


def test_unsupported_structure_and_body_containers_refuse():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(tax_type='ICT_RCIT_OIL')
    assert str(error.value) == 'unsupported_corporate_l2_structure'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(ListOfShareholders={}))
    assert str(error.value) == 'unsupported_corporate_l2_body'


def test_an_overflowing_ordered_sum_refuses_before_any_total_comparison():
    value = form(InvestmentList=[affiliate(1, Debt=_CorporateNumber('500000000000000')),
                                 affiliate(2, Debt=_CorporateNumber('500000000000000'))],
                 TotalDebt=_CorporateNumber('999999999999999'))
    with pytest.raises(_UnsupportedMetadata) as error:
        project(value)
    assert str(error.value) == 'unsafe_corporate_l2_ordered_sum'


def test_the_shipped_prefill_flag_is_a_non_displayed_row_control():
    result = project(form(InvestmentList=[affiliate(1, IsEditable=False),
                                          affiliate(2, IsEditable=_CorporateNumber('1'),
                                                    Debt=_CorporateNumber('500.00'))]))
    flags = [entry for entry in result['provenance']
             if entry['rule'] == 'non-displayed-row-metadata']
    assert [entry['path'] for entry in flags] == [
        ['ListOfOwnership', 'InvestmentList', 0, 'IsEditable'],
        ['ListOfOwnership', 'InvestmentList', 1, 'IsEditable']]
    assert [entry['type'] for entry in flags] == ['boolean', 'number']


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


def test_projected_l2_section_replaces_the_affiliate_dump_leaves():
    result = adapt()
    assert result['eligible'], result['reason']
    section = l2_section(result)
    affiliate_table, dump = section['tables']
    assert affiliate_table['name'] == 'L2/affiliate'
    assert affiliate_table['headers'] == module().L2_AFFILIATE_HEADERS
    assert dump['name'] == '/ListOfOwnership'
    assert not any(str(row[0]).startswith('/ListOfOwnership/InvestmentList')
                   for row in dump['rows'])
    # The unprojected shareholder block keeps its own leaves as visible evidence.
    assert any(str(row[0]).startswith('/ListOfOwnership/ListOfShareholders')
               for row in dump['rows'])
    assert section['fields'] == []
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_l2_shareholder_full_position'
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L2']
    assert projected['kind'] == 'corporate-l2-v1'
    assert len(projected['values']) == len(project()['provenance'])


@pytest.mark.parametrize('body,reason', [
    ('ListOfShareholders', 'unprojected_corporate_l2_shareholder_body'),
    ('InvestmentList', 'unverified_corporate_l2_affiliate_rendering'),
])
def test_populated_owner_blocks_refuse_until_render_equivalence_is_proven(body, reason):
    value = form(ListOfShareholders=None, InvestmentList=None)
    value[body] = [shareholder() if body == 'ListOfShareholders' else affiliate(1)]
    with pytest.raises(_UnsupportedMetadata, match=reason):
        project(value)


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


def test_projected_l2_binds_every_affiliate_cell_and_reports_the_partial_block(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    result = adapt()
    assert result['eligible'], result['reason']
    section = l2_section(result)
    run = source_run('PPh Badan', [section])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L2']
        located = {sheet.cell(row, 2).value: row for row in range(1, sheet.max_row + 1)}
        first = located['SYNTHETIC AFFILIATE 1']
        assert [sheet.cell(first, column).value for column in range(1, 13)] == [
            '1', 'SYNTHETIC AFFILIATE 1', 'SG', '0000000000000002', 1000, 0.25,
            2000, '2025', '3,5000', 4000, '2024', '1,2500']
        for column in (5, 7, 10):
            assert sheet.cell(first, column).data_type == 'n'
        assert sheet.cell(first, 6).data_type == 'n'
        assert sheet.cell(first, 6).number_format == '0.00%'
        assert sheet.cell(first, 6).value == 0.25
        assert sheet.cell(first, 8).value == '2025' and sheet.cell(first, 8).data_type == 's'
        # The approved L2 sheet has two JUMLAH rows. Bind block B's
        # footer after its actual populated body, never block A's first total.
        total = next(row for row in range(first + 2, sheet.max_row + 1)
                     if sheet.cell(row, 1).value == 'JUMLAH')
        assert sheet.cell(total, 7).value == 2500
        assert sheet.cell(total, 10).value == 8000
        report, = [item for item in reports if item['form'] == 'L2']
        assert report['unmapped_tables'] == 1
        assert report['unmapped_rows'] == 14
        assert report['complete'] is False
    finally:
        book.close()
