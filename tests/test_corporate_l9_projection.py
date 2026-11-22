"""Reviewed L9 (Daftar Penyusutan dan Amortisasi Fiskal) projection contracts.

Every projected amount is one literal recap control of the pinned L9 owner, and
the arithmetic that owner performs is re-checked exactly. The twelve detail
grids stay explicitly unprojected: their ``KELOMPOK/JENIS HARTA``, ``KOMERSIAL``
and ``FISKAL`` columns render provider reference catalogs this capture never
transports, so no proven cell value exists for them.

GitHub-runner execution only: this module needs the browser-free corpus helpers.
"""
import importlib

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus

ROUTE = (corpus.ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
    (corpus.TAXPAYER_ID, corpus.RECORD_ID, 'ICT_RCIT', corpus.AGGREGATE_ID)) + '?view=true')


def selected():
    record = corpus.selected_record()
    record['source_fields'].update(ReturnSheetTypeCode='ICT_RCITR', ReturnSheetModel='Normal')
    return record


def lifetime():
    # Synthetic packet evidence only; the browser test seals owned facts itself.
    return {'attempt': corpus.ATTEMPT, 'kind': 'corporate-submitted-spa-v1',
        'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': ROUTE,
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True}


def module():
    return importlib.import_module('coretax_corporate_projection')


def module_or(name):
    return getattr(module(), name)


def form(**overrides):
    """Synthetic payload root; totals match the owner's own reductions."""
    value = {name: _CorporateNumber('0') for name in module().L9_TABLE_TOTALS}
    value.update({
        'TotalTable1': _CorporateNumber('10000000'),
        'TotalTable2': _CorporateNumber('20000000'),
        'TotalTable8': _CorporateNumber('4000000'),
        'TotalTable9': _CorporateNumber('1000000'),
        'TotalFiscalDepreciationTangible': _CorporateNumber('30000000'),
        'TotalCommercialDepreciationTangible': _CorporateNumber('25000000'),
        'DiferencesDepreciationTangible': _CorporateNumber('5000000'),
        'TotalFiscalAmortization': _CorporateNumber('5000000'),
        'TotalCommercialAmortization': _CorporateNumber('3000000'),
        'DiferencesAmortization': _CorporateNumber('2000000'),
    })
    value.update(overrides)
    return value


def project(payload=None, **overrides):
    helper = getattr(module(), 'project_l9', None)
    assert callable(helper), 'Missing reviewed L9 projection'
    options = {'tax_type': 'ICT_RCIT', 'locale': 'id-ID', 'migrated': False}
    options.update(overrides)
    return helper(form() if payload is None else payload, **options)


def grid_declarations():
    declarations = []
    for name, endpoint in module().L9_GRIDS:
        request = {'ReturnSheetRecordId': corpus.RECORD_ID, 'GroupType': name.rsplit('/', 1)[1],
                   'First': 0, 'Rows': 10, 'SortField': '', 'SortOrder': 1,
                   'Filters': {}, 'LanguageId': 'id-ID'}
        declarations.append({'name': name, 'endpoint': endpoint,
                             'pages': [{'request_json': request, 'offset': 0}]})
    return declarations


def observed(grids=None):
    forms = corpus.observed()
    forms[0]['projection']['route'] = ROUTE
    binding = {'name': 'L9',
               'paths': [['RecapitulationFiscalDepreciationAmortization']],
               'grids': grid_declarations() if grids is None else grids,
               'responses': [], 'dependencies': [],
               'projection': {'kind': 'corporate-l9-v1', 'locale': 'id-ID',
                              'builds': {module_or('CIT_SOURCE'):
                                         module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': ROUTE}}
    forms.insert(1, binding)
    return forms


def payload_form(l9=None):
    """Same amounts, but wired as raw JSON number tokens for the adapter."""
    value = dict(form() if l9 is None else l9)
    return {name: (corpus.Number(str(value[name])) if isinstance(value[name], str) else value[name])
            for name in value}


def adapted_root():
    """Decoded `CurrentFormData` shape `apply_projections` receives."""
    return {'TaxType': 'ICT_RCIT',
            'MainFormData': {**corpus.current_form()['MainFormData'], 'IsMigrated': False},
            'RecapitulationFiscalDepreciationAmortization': {
                name: _CorporateNumber(str(value)) for name, value in form().items()}}


def adapted_payload():
    return {'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
            'PreviousFormData': None, 'LastSubmittedFormData': None}


def packets(**main):
    form_value = corpus.current_form()
    form_value['MainFormData']['IsMigrated'] = False
    form_value['MainFormData'].update(main)
    form_value['RecapitulationFiscalDepreciationAmortization'] = payload_form()
    body = [corpus.primary(form_value)]
    for sequence, declaration in enumerate(grid_declarations(), start=2):
        body.append(corpus.packet({'IsSuccessful': True,
            'Payload': {'Data': [], 'TotalRecords': 0, 'Index': None}},
            sequence, endpoint=declaration['endpoint'],
            request=declaration['pages'][0]['request_json']))
    for item in body:
        item['context'].update(frame_url=ROUTE, component_lifetime=lifetime())
    return body


def adapt(forms=None, payload=None, record=None):
    return adapt_corporate_detail(iter(packets() if payload is None else payload),
                                  selected() if record is None else record,
                                  corpus.SCOPE, observed() if forms is None else forms)


def test_every_template_caption_comes_from_one_proven_payload_control():
    fields = module_or('L9_FIELDS')
    assert [name for name, _ in fields] == [
        'TotalFiscalDepreciationTangible', 'TotalCommercialDepreciationTangible',
        'DiferencesDepreciationTangible', 'TotalFiscalAmortization',
        'TotalCommercialAmortization', 'DiferencesAmortization']
    assert [caption for _, caption in fields] == [
        'JUMLAH PENYUSUTAN FISKAL', 'JUMLAH PENYUSUTAN KOMERSIAL', 'SELISIH PENYUSUTAN',
        'JUMLAH AMORTISASI FISKAL', 'JUMLAH AMORTISASI KOMERSIAL', 'SELISIH AMORTISASI']
    result = project()
    assert [field['field'] for field in result['fields']] == [name for name, _ in fields]
    assert [field['label'] for field in result['fields']] == [caption for _, caption in fields]
    assert [field['value'] for field in result['fields']] == [
        '30.000.000', '25.000.000', '5.000.000', '5.000.000', '3.000.000', '2.000.000']
    assert [entry['path'] for entry in result['provenance'] if entry['path'][-1] in dict(fields)] == [
        ['RecapitulationFiscalDepreciationAmortization', name] for name, _ in fields]
    assert all(entry['type'] == 'number' for entry in result['provenance'])


def test_recap_totals_must_reconcile_with_the_per_group_totals():
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(TotalFiscalDepreciationTangible=_CorporateNumber('29999999'),
                     DiferencesDepreciationTangible=_CorporateNumber('4999999')))
    assert str(error.value) == 'unreconciled_corporate_l9_fiscal_depreciation'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(TotalFiscalAmortization=_CorporateNumber('4999999'),
                     DiferencesAmortization=_CorporateNumber('1999999')))
    assert str(error.value) == 'unreconciled_corporate_l9_fiscal_amortization'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(DiferencesDepreciationTangible=_CorporateNumber('5000001')))
    assert str(error.value) == 'unreconciled_corporate_l9_depreciation_difference'
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(DiferencesAmortization=_CorporateNumber('2000001')))
    assert str(error.value) == 'unreconciled_corporate_l9_amortization_difference'


def test_migrated_returns_cannot_copy_the_unpatched_intangible_difference():
    # `setFormData` patches only DifferenceDepreciation for migrated returns;
    # the intangible difference is not initialized from its stored value.
    value = form(DiferencesDepreciationTangible=_CorporateNumber('4000000'),
                 DiferencesAmortization=_CorporateNumber('1000000'))
    with pytest.raises(_UnsupportedMetadata):
        project(value, migrated=True)
    with pytest.raises(_UnsupportedMetadata) as error:
        project(value)
    assert str(error.value) == 'unreconciled_corporate_l9_depreciation_difference'


def test_a_negative_difference_is_a_reviewed_shape():
    result = project(form(TotalCommercialDepreciationTangible=_CorporateNumber('32000000'),
                          DiferencesDepreciationTangible=_CorporateNumber('-2000000')))
    assert [field['value'] for field in result['fields']][2] == '-2.000.000'


@pytest.mark.parametrize('mutation,reason', [
    ({'TotalTable1': '10000000'}, 'unsupported_corporate_l9_amount_type'),
    ({'DiferencesAmortization': True}, 'unsupported_corporate_l9_amount_type'),
    ({'TotalTable1': _CorporateNumber('10000000.5')}, 'unsupported_corporate_l9_amount_precision'),
    ({'TotalTable7': _CorporateNumber('-1')}, 'unsupported_corporate_l9_negative_amount'),
    ({'Synthetic': _CorporateNumber('0')}, 'unsupported_corporate_l9_source_shape'),
])
def test_unreviewed_l9_shapes_refuse(mutation, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(form(**mutation))
    assert str(error.value) == reason


def test_a_missing_table_total_refuses_the_source_shape():
    value = form()
    value.pop('TotalTable12')
    with pytest.raises(_UnsupportedMetadata) as error:
        project(value)
    assert str(error.value) == 'unsupported_corporate_l9_source_shape'


@pytest.mark.parametrize('projection', [
    {'kind': 'corporate-l9-v0'},
    {'kind': 'corporate-l9-v1', 'builds': {}, 'route': ROUTE},
    {'kind': 'corporate-l9-v1', 'builds': {module_or('CIT_SOURCE'): 'APPROVED'},
     'route': ROUTE},
    {'kind': 'corporate-l9-v1', 'builds': {module_or('CIT_SOURCE'): 'a' * 64},
     'route': ROUTE, 'timezone': 'Asia/Jakarta'},
])
def test_projection_proof_must_match_the_reviewed_shape(projection):
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L9']
    binding['projection'] = projection
    result = adapt(forms)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l9_binding'


@pytest.mark.parametrize('mutate', ['one_grid', 'no_pages', 'foreign_grid'])
def test_every_grid_request_binding_must_be_present(mutate):
    grids = grid_declarations()
    if mutate == 'one_grid':
        del grids[3]
    elif mutate == 'no_pages':
        grids[0]['pages'] = []
    else:
        grids[0]['name'] = 'L9/l9-table-1-grid/Group 9'
    binding = {'name': 'L9', 'paths': [['RecapitulationFiscalDepreciationAmortization']],
               'grids': grids, 'responses': [], 'dependencies': [],
               'projection': {'kind': 'corporate-l9-v1', 'locale': 'id-ID',
                              'builds': {module_or('CIT_SOURCE'):
                                         module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': ROUTE}}
    section = {'name': 'L9', 'fields': [], 'tables': [], 'text': ''}
    with pytest.raises(_UnsupportedMetadata) as error:
        module().apply_projections([section], [binding], root=adapted_root(),
                                   payload=adapted_payload(), record=corpus.selected_record(),
                                   event={'frame_url': ROUTE, 'sequence': 1})
    assert str(error.value) == 'unverified_corporate_l9_binding'


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L9']
    binding['projection'] = {**binding['projection'], 'route': ROUTE + '/changed'}
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l9_binding'
    forms = observed()
    # Drop the Induk projection so this isolates the L9 lifecycle gate.
    forms[0].pop('projection')
    record = selected()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l9_submitted_lifecycle'


def test_an_unreviewed_migrated_flag_refuses_the_capture():
    forms = observed()
    result = adapt_corporate_detail(iter(packets(IsMigrated='yes')), selected(),
                                    corpus.SCOPE, forms)
    assert not result['eligible']
    assert result['reason'] == 'unsupported_corporate_l9_migrated_flag'


def test_a_migrated_return_stays_unsupported():
    forms = observed()
    result = adapt_corporate_detail(iter(packets(IsMigrated=True)), selected(),
                                    corpus.SCOPE, forms)
    assert not result['eligible'] and result['reason'] == 'unsupported_corporate_l9_migrated_flag'


@pytest.mark.parametrize('flag,eligible', [(corpus.Number('0'), True), (corpus.Number('1'), False)])
def test_numeric_migrated_flag_encodings_are_read_as_booleans(flag, eligible):
    forms = observed()
    result = adapt_corporate_detail(iter(packets(IsMigrated=flag)), selected(),
                                    corpus.SCOPE, forms)
    assert result['eligible'] is eligible, result['reason']


def test_absent_main_migrated_flag_falls_back_to_the_outer_payload():
    """Live shape: MainFormData has no IsMigrated copy; the outer payload
    carries the authoritative non-migrated flag."""
    form_value = corpus.current_form()
    form_value['MainFormData'].pop('IsMigrated', None)
    form_value['RecapitulationFiscalDepreciationAmortization'] = payload_form()
    body = [corpus.packet({'IsSuccessful': True,
        'Payload': {'TIN': corpus.NPWP, 'PeriodYear': 2025, 'IsDraft': True,
            'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
            'PreviousFormData': None, 'LastSubmittedFormData': None,
            'IsMigrated': False, 'CurrentFormData': corpus.wire(form_value)}}, 1)]
    for sequence, declaration in enumerate(grid_declarations(), start=2):
        body.append(corpus.packet({'IsSuccessful': True,
            'Payload': {'Data': [], 'TotalRecords': 0, 'Index': None}},
            sequence, endpoint=declaration['endpoint'],
            request=declaration['pages'][0]['request_json']))
    for item in body:
        item['context'].update(frame_url=ROUTE, component_lifetime=lifetime())
    result = adapt_corporate_detail(iter(body), selected(), corpus.SCOPE, observed())
    assert result['eligible'], result['reason']


def test_absent_main_and_outer_migrated_flag_still_refuses():
    form_value = corpus.current_form()
    form_value['MainFormData'].pop('IsMigrated', None)
    form_value['RecapitulationFiscalDepreciationAmortization'] = payload_form()
    body = [corpus.packet({'IsSuccessful': True,
        'Payload': {'TIN': corpus.NPWP, 'PeriodYear': 2025, 'IsDraft': True,
            'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
            'PreviousFormData': None, 'LastSubmittedFormData': None,
            'CurrentFormData': corpus.wire(form_value)}}, 1)]
    for sequence, declaration in enumerate(grid_declarations(), start=2):
        body.append(corpus.packet({'IsSuccessful': True,
            'Payload': {'Data': [], 'TotalRecords': 0, 'Index': None}},
            sequence, endpoint=declaration['endpoint'],
            request=declaration['pages'][0]['request_json']))
    for item in body:
        item['context'].update(frame_url=ROUTE, component_lifetime=lifetime())
    result = adapt_corporate_detail(iter(body), selected(), corpus.SCOPE, observed())
    assert not result['eligible'] and result['reason'] == 'unsupported_corporate_l9_migrated_flag'


@pytest.mark.parametrize('options,reason', [
    ({'tax_type': 'ICT_PPN'}, 'unsupported_corporate_l9_structure'),
    ({'locale': 'en-US'}, 'unsupported_corporate_l9_structure'),
    ({'migrated': 'no'}, 'unsupported_corporate_l9_structure'),
    ({'migrated': None}, 'unsupported_corporate_l9_structure'),
])
def test_unreviewed_l9_binding_options_refuse(options, reason):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(None, **options)
    assert str(error.value) == reason


def test_unprojected_l9_section_is_still_the_audit_dump():
    from coretax_json import has_audit_dump_tables
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L9']
    binding.pop('projection')
    result = adapt(forms)
    assert result['eligible'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L9']
    assert len(section['tables']) == 13  # One declared root dump plus twelve grids.
    assert has_audit_dump_tables(result['sections']) is True


def test_projected_l9_keeps_all_custody_tables_and_reports_partial():
    from coretax_json import has_audit_dump_tables
    result = adapt()
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L9']
    assert len(section['tables']) == 13
    assert [t['name'] for t in section['tables'][1:]] == [name for name, _ in module().L9_GRIDS]
    assert [field['field'] for field in section['fields']] == [
        name for name, _ in module_or('L9_FIELDS')]
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_l9_grid_rows'
    assert has_audit_dump_tables(result['sections']) is True
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L9']
    assert projected['kind'] == 'corporate-l9-v1'
    assert len(projected['values']) == 19
    assert {tuple(value['container']) for value in projected['values']} == {
        ('Payload', 'CurrentFormData')}


def test_l9_projection_does_not_mutate_source_bindings_or_payload():
    from copy import deepcopy
    forms = observed()
    before = deepcopy(forms)
    payload = packets()
    raw = [item['body'] for item in payload]
    adapt(forms, payload=payload)
    assert forms == before
    assert [item['body'] for item in payload] == raw


def test_projected_l9_binds_every_template_amount_cell(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import section, source_run
    fields = project()['fields']
    # The real projected section shape: six proven totals, twelve unprojected grids.
    partial = {**section('L9', fields=fields), 'projection_complete': False,
               'projection_reason': 'unprojected_l9_grid_rows'}
    run = source_run('PPh Badan', [partial])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L9']
        # Row compaction moves every recap row; bind each caption, not its index.
        located = {}
        for row in range(1, sheet.max_row + 1):
            label = ' '.join(str(sheet.cell(row, 1).value or '').split()).casefold()
            if label:
                located[label] = row
        expected = {
            'jumlah penyusutan fiskal': 30_000_000,
            'jumlah penyusutan komersial': 25_000_000,
            'selisih penyusutan': 5_000_000,
            'jumlah amortisasi fiskal': 5_000_000,
            'jumlah amortisasi komersial': 3_000_000,
            'selisih amortisasi': 2_000_000,
        }
        for label, amount in expected.items():
            row = located[label]
            assert sheet.cell(row, 8).value == amount
            assert sheet.cell(row, 8).data_type == 'n'
        # The recap totals are complete; the twelve detail grids are not mapped,
        # so the worksheet report must say partial with the reviewed reason.
        assert reports[0]['complete'] is False
        assert reports[0]['derived_reason'] == 'unprojected_l9_grid_rows'
        assert reports[0]['unmapped_fields'] == reports[0]['unmapped_tables'] == 0
    finally:
        book.close()
