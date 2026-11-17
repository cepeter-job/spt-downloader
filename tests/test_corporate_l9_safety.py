"""L9 recovery regressions; product execution is GitHub-runner-only."""
from copy import deepcopy

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, has_audit_dump_tables
from test_corporate_l9_projection import (ROUTE, module, observed, adapted_root,
    adapted_payload, selected, lifetime, form, project, adapt, packets)


def apply(*, forms=None, root=None, payload=None, event=None):
    bindings = deepcopy(observed() if forms is None else forms)
    # Direct guard tests use the unparsed data helper, not wire-decoded Induk
    # numbers. Isolate L9 without invoking the unrelated identity projector.
    for binding in bindings:
        if binding['name'] == 'Induk':
            binding.pop('projection', None)
    return module().apply_projections(
        [{'name': f['name'], 'fields': [], 'tables': [], 'text': ''} for f in bindings], bindings,
        root=adapted_root() if root is None else root,
        payload=adapted_payload() if payload is None else payload, record=selected(),
        event={'frame_url': ROUTE, 'sequence': 1, 'component_lifetime': lifetime()} if event is None else event)


@pytest.mark.parametrize('value,reason', [
    (None, 'unsupported_corporate_l9_amount_type'),
    (10000000, 'unsupported_corporate_l9_amount_type'),
    (10000000.0, 'unsupported_corporate_l9_amount_type'),
    (_CorporateNumber('-0'), 'unsupported_corporate_l9_amount_precision'),
    (_CorporateNumber('1000000000000000'), 'unsupported_corporate_l9_amount_precision'),
    (_CorporateNumber('1e999999999999999999'), 'unsupported_corporate_l9_amount_precision')])
def test_null_numbers_and_unsafe_precision_never_get_coerced(value, reason):
    with pytest.raises(_UnsupportedMetadata, match='^' + reason + '$'):
        project(form(TotalTable1=value))


def test_fifteen_digit_boundary_and_exact_exponent_tokens():
    value = form(TotalTable1=_CorporateNumber('999999979999999'),
        TotalFiscalDepreciationTangible=_CorporateNumber('999999999999999'),
        TotalCommercialDepreciationTangible=_CorporateNumber('999999999999999'),
        DiferencesDepreciationTangible=_CorporateNumber('0'), TotalTable8=_CorporateNumber('4e6'))
    result = project(value)
    assert result['fields'][0]['value'] == '999.999.999.999.999'
    assert result['fields'][2]['value'] == '0'


@pytest.mark.parametrize('defect', ['arbitrary_sha', 'missing_approved', 'malformed_approved',
    'locale', 'dependencies', 'responses', 'paths', 'non_object_grid'])
def test_pin_and_binding_checks_are_positive_and_closed(defect, monkeypatch):
    forms = observed()
    binding = forms[1]
    if defect == 'arbitrary_sha':
        binding['projection']['builds'][module().CIT_SOURCE] = 'a' * 64
    elif defect in ('missing_approved', 'malformed_approved'):
        monkeypatch.setattr(module(), 'BUILD_DIGESTS', {} if defect == 'missing_approved' else {
            module().CIT_SOURCE: 'APPROVED'})
    elif defect == 'locale':
        binding['projection']['locale'] = 'en-US'
    elif defect in ('dependencies', 'responses'):
        binding[defect] = [{}]
    elif defect == 'paths':
        binding['paths'].append(['Synthetic'])
    else:
        binding['grids'][0] = None
    with pytest.raises(_UnsupportedMetadata, match='^unverified_corporate_l9_binding$'):
        apply(forms=forms)


@pytest.mark.parametrize('defect', ['status', 'model', 'previous', 'last', 'missing_previous',
    'main', 'flag_missing', 'flag_null', 'flag_string', 'induk_order', 'no_lifetime', 'history', 'legacy_route'])
def test_only_owned_current_nonmigrated_normal_lifecycle_is_supported(defect):
    forms, root, payload = observed(), adapted_root(), adapted_payload()
    event = {'frame_url': ROUTE, 'sequence': 1, 'component_lifetime': lifetime()}
    if defect == 'status':
        payload['ReturnSheetStatusCode'] = 'DRAFT'
    elif defect == 'model':
        payload['ReturnSheetModel'] = 'AMENDMENT'
    elif defect in ('previous', 'last'):
        payload['PreviousFormData' if defect == 'previous' else 'LastSubmittedFormData'] = '{}'
    elif defect == 'missing_previous':
        payload.pop('PreviousFormData')
    elif defect == 'main':
        root['MainFormData'] = None
    elif defect == 'flag_missing':
        root['MainFormData'].pop('IsMigrated')
    elif defect in ('flag_null', 'flag_string'):
        root['MainFormData']['IsMigrated'] = None if defect == 'flag_null' else 'false'
    elif defect == 'induk_order':
        forms.reverse()
    elif defect == 'no_lifetime':
        event.pop('component_lifetime')
    else:
        route = ROUTE.replace('corporate-income-tax-return/', 'corporate-income-tax-return-history/') if defect == 'history' else ROUTE.removesuffix('?view=true')
        event['frame_url'] = route
        for binding in forms:
            binding['projection']['route'] = route
    with pytest.raises(_UnsupportedMetadata):
        apply(forms=forms, root=root, payload=payload, event=event)


def test_nonempty_duplicate_grid_leaves_survive_partial_projection_and_export(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    import support_json_corpus as corpus
    from support_templates import source_run
    body = packets()
    for item in body[1:]:
        context = deepcopy(item['context'])
        raw = corpus.packet({'IsSuccessful': True, 'Payload': {'TotalRecords': 2, 'Index': None,
            'Data': [{'AssetCode': 'SYNTHETIC-001', 'FiscalYearValue': 7}] * 2}},
            context['sequence'], endpoint=context['url'], request=context['request_json'])
        item.update(raw)
        item['context'].update(frame_url=ROUTE, component_lifetime=lifetime())
    before = deepcopy(body)
    result = adapt(payload=body)
    assert result['eligible'], result['reason']
    section = result['sections'][1]
    assert len(section['tables']) == 13
    assert all(len(t['rows']) == 4 for t in section['tables'][1:])
    assert has_audit_dump_tables([section]) and body == before
    run = source_run('PPh Badan', [section])
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    reports = []
    exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    report, = reports
    assert not report['complete'] and report['derived_reason'] == 'unprojected_l9_grid_rows'
    assert report['unmapped_tables'] == 13 and report['unmapped_rows'] == 66
    assert len(report['unmapped_table_identities']) == 13
    run['template_mapping'] = reports
    exporter.export_workbook(run, tmp_path / 'audit.xlsx', include_details=False)
    book = load_workbook(tmp_path / 'audit.xlsx')
    try:
        assert any('rincian dua belas grid belum dipetakan' in str(cell.value)
                   for row in book['Audit'] for cell in row)
    finally:
        book.close()
