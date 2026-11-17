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
    binding = {'name': 'L9',
               'paths': [['RecapitulationFiscalDepreciationAmortization']],
               'grids': grid_declarations() if grids is None else grids,
               'responses': [], 'dependencies': [],
               'projection': {'kind': 'corporate-l9-v1',
                              'builds': {module_or('CIT_SOURCE'):
                                         module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': corpus.FRAME_URL}}
    forms.insert(1, binding)
    return forms


def payload_form(l9=None):
    """Same amounts, but wired as raw JSON number tokens for the adapter."""
    value = dict(form() if l9 is None else l9)
    return {name: (corpus.Number(str(value[name])) if isinstance(value[name], str) else value[name])
            for name in value}


def adapted_root():
    """Decoded `CurrentFormData` shape `apply_projections` receives."""
    return {'MainFormData': corpus.current_form()['MainFormData'],
            'RecapitulationFiscalDepreciationAmortization': {
                name: _CorporateNumber(str(value)) for name, value in form().items()}}


def adapted_payload():
    return {'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL'}


def packets(**main):
    form_value = corpus.current_form()
    form_value['MainFormData'].update(main)
    form_value['RecapitulationFiscalDepreciationAmortization'] = payload_form()
    body = [corpus.primary(form_value)]
    for sequence, declaration in enumerate(grid_declarations(), start=2):
        body.append(corpus.packet({'IsSuccessful': True,
            'Payload': {'Data': [], 'TotalRecords': 0, 'Index': None}},
            sequence, endpoint=declaration['endpoint'],
            request=declaration['pages'][0]['request_json']))
    return body


def adapt(forms=None, payload=None, record=None):
    return adapt_corporate_detail(iter(packets() if payload is None else payload),
                                  corpus.selected_record() if record is None else record,
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
    assert [entry['path'] for entry in result['provenance']] == [
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


def test_migrated_returns_keep_the_payload_differences_unrecomputed():
    # `setFormData` skips both reductions for a migrated return, so the stored
    # difference is authoritative and must not be refused as "unreconciled".
    value = form(DiferencesDepreciationTangible=_CorporateNumber('4000000'),
                 DiferencesAmortization=_CorporateNumber('1000000'))
    result = project(value, migrated=True)
    assert [field['value'] for field in result['fields']][2] == '4.000.000'
    assert [field['value'] for field in result['fields']][5] == '1.000.000'
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
    {'kind': 'corporate-l9-v1', 'builds': {}, 'route': corpus.FRAME_URL},
    {'kind': 'corporate-l9-v1', 'builds': {module_or('CIT_SOURCE'): 'APPROVED'},
     'route': corpus.FRAME_URL},
    {'kind': 'corporate-l9-v1', 'builds': {module_or('CIT_SOURCE'): 'a' * 64},
     'route': corpus.FRAME_URL, 'timezone': 'Asia/Jakarta'},
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
               'projection': {'kind': 'corporate-l9-v1',
                              'builds': {module_or('CIT_SOURCE'):
                                         module_or('BUILD_DIGESTS')[module_or('CIT_SOURCE')]},
                              'route': corpus.FRAME_URL}}
    section = {'name': 'L9', 'fields': [], 'tables': [], 'text': ''}
    with pytest.raises(_UnsupportedMetadata) as error:
        module().apply_projections([section], [binding], root=adapted_root(),
                                   payload=adapted_payload(), record=corpus.selected_record(),
                                   event={'frame_url': corpus.FRAME_URL, 'sequence': 1})
    assert str(error.value) == 'unverified_corporate_l9_binding'


def test_route_or_lifecycle_contradiction_refuses_the_projection():
    forms = observed()
    binding, = [item for item in forms if item['name'] == 'L9']
    binding['projection'] = {**binding['projection'], 'route': corpus.FRAME_URL + '/changed'}
    result = adapt(forms)
    assert not result['eligible'] and result['reason'] == 'unverified_corporate_l9_binding'
    forms = observed()
    # Drop the Induk projection so this isolates the L9 lifecycle gate.
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    result = adapt(forms, record=record)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_l9_submitted_lifecycle'


def test_an_unreviewed_migrated_flag_refuses_the_capture():
    forms = observed()
    result = adapt_corporate_detail(iter(packets(IsMigrated='yes')), corpus.selected_record(),
                                    corpus.SCOPE, forms)
    assert not result['eligible']
    assert result['reason'] == 'unsupported_corporate_l9_migrated_flag'


def test_a_migrated_return_skips_only_the_recomputed_differences():
    forms = observed()
    result = adapt_corporate_detail(iter(packets(IsMigrated=True)), corpus.selected_record(),
                                    corpus.SCOPE, forms)
    assert result['eligible'], result['reason']


@pytest.mark.parametrize('flag,eligible', [(corpus.Number('0'), True), (corpus.Number('1'), True)])
def test_numeric_migrated_flag_encodings_are_read_as_booleans(flag, eligible):
    forms = observed()
    result = adapt_corporate_detail(iter(packets(IsMigrated=flag)), corpus.selected_record(),
                                    corpus.SCOPE, forms)
    assert result['eligible'] is eligible, result['reason']


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


def test_projected_l9_section_replaces_the_dump_and_reports_partial():
    from coretax_json import has_audit_dump_tables
    result = adapt()
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L9']
    assert section['tables'] == []
    assert [field['field'] for field in section['fields']] == [
        name for name, _ in module_or('L9_FIELDS')]
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_l9_grid_rows'
    assert has_audit_dump_tables(result['sections']) is False
    projected, = [item for item in result['provenance']['projections'] if item['form'] == 'L9']
    assert projected['kind'] == 'corporate-l9-v1'
    assert len(projected['values']) == len(module_or('L9_FIELDS'))
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
