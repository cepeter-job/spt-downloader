"""Two-block L4 custody regressions; GitHub-runner execution only."""
from copy import deepcopy
import json

import pytest

import coretax_corporate_projection as projection
from coretax_json import (_UnsupportedMetadata, _corporate_json, _corporate_request_key,
                          adapt_corporate_detail, has_audit_dump_tables)
import support_json_corpus as corpus
from support_templates import section, source_run

GRID = projection.CORPORATE_L4_GRID_URL
FOOTER = projection.CORPORATE_L4_FOOTER_URL
ROOT = projection.L4_ROOT
A_HEADERS = ['NPWP PEMOTONG/PEMUNGUT', 'NAMA PEMOTONG/PEMUNGUT', 'KODE OBJEK PAJAK',
             'OBJEK PAJAK', 'DASAR PENGENAAN PAJAK (Rupiah)', 'TINGKAT (%)',
             'PPH FINAL TERUTANG (Rupiah)']
B_HEADERS = ['NO.', 'KODE', 'JENIS PENGHASILAN', 'SUMBER PENGHASILAN', 'PENGHASILAN BRUTO(Rp)']
ROW = {'TIN': '0000000000000002', 'Name': 'SYNTHETIC PAYER', 'TaxObjectCode': '28-423-99',
       'TaxObject': 'SAVED TEXT IS NOT THE RENDERED CATALOG LABEL', 'TaxBase': 1000,
       'TaxRate': 2, 'IncomeTax': 20, 'TaxBaseUsd': 0, 'IncomeTaxUsd': 0, 'Index': 0}
B_ROW = {'TaxObjectCode': '1', 'TypeOfIncome': '1', 'IncomeSource': 'SYNTHETIC SOURCE',
         'GrossIncome': 500}


def root(**overrides):
    return {'TotalTaxBase': 0, 'TotalFinalIncomeTaxPayable': 0,
            'TotalFinalIncomeTaxPayableUsd': 0, 'TotalGrossIncome': 0,
            'ListOfIncomeExcludedFromIncomeTax': [], **overrides}


def footer(**overrides):
    return {'TaxBase': 0, 'IncomeTax': 0, 'TaxBaseUsd': 0, 'IncomeTaxUsd': 0, **overrides}


def project(form=None, *, rows=None, footer_value=None, **options):
    return projection.project_l4(_corporate_json(json.dumps(root() if form is None else form)),
        footer=_corporate_json(json.dumps(footer() if footer_value is None else footer_value)),
        pages=[{'offset': 0, 'rows': 10, 'total': len(rows or []),
                'data': _corporate_json(json.dumps(rows or []))}],
        **{'tax_type': 'ICT_RCIT', 'locale': 'id-ID', **options})


def request(**overrides):
    return {'ReturnSheetRecordId': corpus.RECORD_ID, 'LanguageId': 'id-ID', 'First': 0,
            'Rows': 10, 'SortField': '', 'SortOrder': 1, 'Filters': [],
            'PeriodYear': str(corpus.SCOPE[1]), **overrides}


def table_proofs():
    return [{'component': 'rshshr-citr-l4-grid1', 'headers': A_HEADERS,
             'footer_spans': [[4, 1, 1, 1]]},
            {'component': 'rsh-citr-l4-grid2', 'headers': B_HEADERS,
             'footer_spans': [[1, 3, 1]]}]


def bindings():
    return [{'name': 'L4', 'paths': [[ROOT]], 'grids': [
        {'name': 'L4/l4-table-a-grid', 'endpoint': GRID,
         'pages': [{'request_json': request(), 'offset': 0}]}], 'responses': [],
        'dependencies': [{'endpoint': FOOTER,
                          'request_json': {'ReturnSheetRecordId': corpus.RECORD_ID}}],
        'projection': {'kind': 'corporate-l4-v1', 'builds': {
            projection.CIT_SOURCE: projection.BUILD_DIGESTS[projection.CIT_SOURCE]},
            'route': corpus.FRAME_URL, 'tables': table_proofs()}}]


def observed():
    return corpus.observed() + bindings()


def packets(form=None, *, rows=None):
    rows = [] if rows is None else rows
    current = corpus.current_form()
    current[ROOT] = json.loads(json.dumps(root() if form is None else form),
                               parse_int=corpus.Number, parse_float=corpus.Number)
    return [corpus.primary(current), corpus.packet({'IsSuccessful': True, 'Payload': {
        'TotalRecords': len(rows), 'Data': rows, 'Index': None}}, 2,
        endpoint=GRID, request=request()), corpus.packet({
            'IsSuccessful': True, 'Payload': footer()}, 3,
            endpoint=FOOTER, request={'ReturnSheetRecordId': corpus.RECORD_ID})]


def adapt(forms=None, raw=None, record=None):
    return adapt_corporate_detail(iter(packets() if raw is None else raw),
        corpus.selected_record() if record is None else record, corpus.SCOPE,
        observed() if forms is None else forms)


def packet_map():
    return {(GRID, _corporate_request_key(request())): {
        'payload': _corporate_json('{"TotalRecords":0,"Data":[],"Index":null}'),
        'event': {'sequence': 2}},
        (FOOTER, _corporate_request_key({'ReturnSheetRecordId': corpus.RECORD_ID})): {
            'payload': _corporate_json(json.dumps(footer())), 'event': {'sequence': 3}}}


def apply(binding=None, *, form=None, auxiliary=None):
    binding = bindings()[0] if binding is None else binding
    value = {'name': 'L4', 'fields': [], 'tables': [{'headers': [
        'JSON path', 'JSON type', 'Source value'], 'rows': [['/SYNTHETIC', 'null', '']]}]}
    before = deepcopy(value)
    try:
        result = projection._apply_l4(binding, value, [binding],
            root={ROOT: _corporate_json(json.dumps(root() if form is None else form))},
            payload={'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL'},
            record=corpus.selected_record(), event={'frame_url': corpus.FRAME_URL, 'sequence': 1},
            auxiliary_packets=packet_map() if auxiliary is None else auxiliary)
    except _UnsupportedMetadata:
        assert value == before  # Refusal must never erase either custody block.
        raise
    return value, result


def test_empty_projection_keeps_both_zero_footers_and_no_guessed_body_rows():
    result = project()
    a, b = result['tables']
    assert a['headers'] == A_HEADERS and b['headers'] == B_HEADERS
    assert a['rows'] == a['footer'] == [['TOTAL', '0', '', '0']]
    assert a['footer_spans'] == [[4, 1, 1, 1]]
    assert b['rows'] == b['footer'] == [['', 'JUMLAH', '0']]
    assert b['footer_spans'] == [[1, 3, 1]]
    assert all(t['complete'] and t['body_row_count'] == t['source_total'] == 0
               for t in result['tables'])
    assert result['fields'] == []


@pytest.mark.parametrize('excluded', [[], None])
@pytest.mark.parametrize('extra', [{}, {'TotalTaxBaseUsd': 0}])
def test_reviewed_root_profiles_and_inert_b_encodings(excluded, extra):
    assert project(root(ListOfIncomeExcludedFromIncomeTax=excluded, **extra))['tables'][1]['complete']


@pytest.mark.parametrize('values', [[ROW], [ROW, ROW]])
def test_populated_a_refuses_instead_of_copying_saved_taxobject(values):
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l4_tax_object_labels'):
        project(rows=values)


@pytest.mark.parametrize('values', [[B_ROW], [B_ROW, B_ROW]])
def test_populated_b_refuses_instead_of_erasing_original_duplicate_rows(values):
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l4_income_type_labels'):
        project(root(ListOfIncomeExcludedFromIncomeTax=values, TotalGrossIncome=500 * len(values)))


@pytest.mark.parametrize('key', ['TotalTaxBase', 'TotalFinalIncomeTaxPayable',
                                'TotalFinalIncomeTaxPayableUsd', 'TotalGrossIncome', 'TotalTaxBaseUsd'])
@pytest.mark.parametrize('value', [None, True, '0', 1, -1, 0.5, 1000000000000000])
def test_nonzero_or_non_numeric_stored_totals_cannot_certify_empty(key, value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l4_empty_total'):
        project(root(**{key: value}))


@pytest.mark.parametrize('key', ['TaxBase', 'IncomeTax', 'TaxBaseUsd', 'IncomeTaxUsd'])
@pytest.mark.parametrize('value', [None, True, '0', 1, 0.25])
def test_every_footer_total_is_explicit_numeric_zero(key, value):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l4_empty_total'):
        project(footer_value=footer(**{key: value}))


@pytest.mark.parametrize('excluded', [{}, '', 0, False])
def test_unreviewed_block_b_shapes_refuse(excluded):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l4_excluded_body'):
        project(root(ListOfIncomeExcludedFromIncomeTax=excluded))


@pytest.mark.parametrize('options', [{'tax_type': 'ICT_ROGCIT'}, {'locale': 'en-US'}])
def test_unreviewed_currency_or_locale_refuses(options):
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l4_source_shape'):
        project(**options)


@pytest.mark.parametrize('changes', [{'offset': 1}, {'rows': 7}, {'total': 1}, {'data': None},
                                   {'unreviewed': 0}])
def test_empty_grid_shape_stays_closed(changes):
    page = {'offset': 0, 'rows': 10, 'total': 0, 'data': [], **changes}
    with pytest.raises(_UnsupportedMetadata, match='incomplete_corporate_l4_pages'):
        projection.project_l4(_corporate_json(json.dumps(root())),
            footer=_corporate_json(json.dumps(footer())), pages=[page],
            tax_type='ICT_RCIT', locale='id-ID')


@pytest.mark.parametrize('changes', [{'Unknown': 0}, {'TotalTaxBase': None}])
def test_unknown_or_missing_root_contract_stays_unsupported(changes):
    with pytest.raises(_UnsupportedMetadata):
        project(root(**changes))


def test_zero_lexemes_are_retained_and_signed_zero_refuses():
    form = _corporate_json(json.dumps(root()))
    form['TotalTaxBase'] = _corporate_json('0.000e+2')
    result = projection.project_l4(form, footer=_corporate_json(json.dumps(footer())),
        pages=[{'offset': 0, 'rows': 10, 'total': 0, 'data': []}], tax_type='ICT_RCIT', locale='id-ID')
    assert next(e for e in result['provenance'] if e['path'] == [ROOT, 'TotalTaxBase'])['value'] == '0.000e+2'
    form['TotalTaxBase'] = _corporate_json('-0')
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l4_empty_total'):
        projection.project_l4(form, footer=_corporate_json(json.dumps(footer())),
            pages=[{'offset': 0, 'rows': 10, 'total': 0, 'data': []}], tax_type='ICT_RCIT', locale='id-ID')


def test_pin_requires_exact_configured_digest(monkeypatch):
    binding = bindings()[0]
    valid_binding = deepcopy(binding)
    binding['projection']['builds'][projection.CIT_SOURCE] = 'a' * 64
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l4_binding'):
        apply(binding)
    monkeypatch.setattr(projection, 'BUILD_DIGESTS', {})
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l4_binding'):
        apply(valid_binding)


@pytest.mark.parametrize('case', ['missing', 'kind', 'route', 'extra', 'headers', 'spans', 'component'])
def test_binding_and_both_rendered_owners_are_required(case):
    binding = bindings()[0]
    proof = binding['projection']
    if case == 'missing':
        proof.pop('tables')
    elif case == 'kind':
        proof['kind'] = 'corporate-l4-v0'
    elif case == 'route':
        proof['route'] += '/changed'
    elif case == 'extra':
        proof['unreviewed'] = True
    else:
        proof['tables'][1][{'headers': 'headers', 'spans': 'footer_spans',
                            'component': 'component'}[case]] = []
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l4_binding'):
        apply(binding)


@pytest.mark.parametrize('case', ['no-grid', 'no-footer', 'duplicate-footer', 'responses', 'page-shape',
                                 'page-query', 'duplicate-page', 'wrong-year', 'footer-year', 'packets'])
def test_declared_request_custody_cannot_be_weakened(case):
    binding, auxiliary = bindings()[0], packet_map()
    if case == 'no-grid':
        binding['grids'] = []
    elif case == 'no-footer':
        binding['dependencies'] = []
    elif case == 'duplicate-footer':
        binding['dependencies'] *= 2
    elif case == 'responses':
        binding['responses'] = [{}]
    elif case == 'page-shape':
        binding['grids'][0]['pages'][0]['extra'] = True
    elif case == 'page-query':
        binding['grids'][0]['pages'][0]['request_json']['SortField'] = 'TIN'
    elif case == 'duplicate-page':
        binding['grids'][0]['pages'] *= 2
    elif case == 'wrong-year':
        binding['grids'][0]['pages'][0]['request_json']['PeriodYear'] = '2024'
    elif case == 'footer-year':
        binding['dependencies'][0]['request_json']['PeriodYear'] = '2024'
    else:
        auxiliary.pop(next(iter(auxiliary)))
    with pytest.raises(_UnsupportedMetadata):
        apply(binding, auxiliary=auxiliary)


@pytest.mark.parametrize('case', ['page-index', 'page-shape', 'total', 'extra-footer'])
def test_auxiliary_packet_shapes_remain_closed(case):
    auxiliary = packet_map()
    grid = auxiliary[next(key for key in auxiliary if key[0] == GRID)]['payload']
    if case == 'page-index':
        grid['Index'] = '0'
    elif case == 'page-shape':
        grid['Unreviewed'] = None
    elif case == 'total':
        grid['TotalRecords'] = _corporate_json('1')
    else:
        auxiliary[next(key for key in auxiliary if key[0] == FOOTER)]['payload']['Extra'] = 0
    with pytest.raises(_UnsupportedMetadata):
        apply(auxiliary=auxiliary)


def test_lifecycle_refusal_is_independent_of_other_form_projections():
    forms = observed()
    forms[0].pop('projection')
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    assert adapt(forms, record=record)['reason'] == 'unverified_corporate_l4_submitted_lifecycle'


def test_accepted_empty_form_needs_no_fields_bypass_and_preserves_sources():
    forms, raw, record = observed(), packets(), corpus.selected_record()
    before = deepcopy((forms, raw, record))
    result = adapt(forms, raw=raw, record=record)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    value, = [s for s in result['sections'] if s['name'] == 'L4']
    assert not value['fields'] and not has_audit_dump_tables([value])
    assert (forms, raw, record) == before
    proof, = [p for p in result['provenance']['projections'] if p['form'] == 'L4']
    assert proof['scope'] == 'empty-both-blocks-only'
    entries = proof['values']
    assert {(e['response_sequence'], tuple(e['container']), tuple(e['path'])) for e in entries} >= {
        (1, ('Payload', 'CurrentFormData'), (ROOT, 'TotalTaxBase')),
        (1, ('Payload', 'CurrentFormData'), (ROOT, 'TotalGrossIncome')),
        (1, ('Payload', 'CurrentFormData'), (ROOT, 'ListOfIncomeExcludedFromIncomeTax')),
        (2, ('Payload',), ('TotalRecords',)), (2, ('Payload',), ('Data',)),
        (2, ('Payload',), ('Index',)),
        (3, ('Payload',), ('TaxBase',)), (3, ('Payload',), ('IncomeTax',))}
    assert not any(e['path'][:1] == [ROOT] for e in entries if e['response_sequence'] == 3)


def test_refused_b_keeps_source_bytes_and_binding_metadata_untouched():
    form = root(ListOfIncomeExcludedFromIncomeTax=[B_ROW, B_ROW], TotalGrossIncome=1000)
    raw, forms = packets(form), observed()
    before = deepcopy((raw, forms))
    result = adapt(forms, raw=raw)
    assert not result['eligible'] and not result['sections']
    assert result['reason'] == 'unverified_corporate_l4_income_type_labels'
    assert (raw, forms) == before
    with pytest.raises(_UnsupportedMetadata):
        apply(form=form)


def test_populated_a_adapter_preserves_duplicate_packet_rows_on_refusal():
    raw, forms = packets(rows=[ROW, ROW]), observed()
    before = deepcopy((raw, forms))
    result = adapt(forms, raw=raw)
    assert not result['eligible'] and result['sections'] == []
    assert result['reason'] == 'unverified_corporate_l4_tax_object_labels'
    assert (raw, forms) == before


def test_repeated_identical_grid_packet_retains_first_source_sequence():
    raw = packets()
    raw.append(corpus.packet({'IsSuccessful': True, 'Payload': {
        'TotalRecords': 0, 'Data': [], 'Index': None}}, 4, endpoint=GRID, request=request()))
    result = adapt(raw=raw)
    assert result['eligible'], result['reason']
    proof, = [p for p in result['provenance']['projections'] if p['form'] == 'L4']
    assert {e['response_sequence'] for e in proof['values'] if e['source'] == 'grid'} == {2}


def test_legacy_dump_keeps_all_b_leaves_and_mapping_partial(tmp_path):
    import coretax_exporter as exporter
    form = root(ListOfIncomeExcludedFromIncomeTax=[B_ROW, B_ROW], TotalGrossIncome=1000)
    forms = observed()
    forms[-1].pop('projection')
    result = adapt(forms, raw=packets(form))
    assert result['eligible']
    value, = [s for s in result['sections'] if s['name'] == 'L4']
    assert has_audit_dump_tables([value]) and value['fields'] == []
    for index in (0, 1):
        assert [f'/{ROOT}/ListOfIncomeExcludedFromIncomeTax/{index}/GrossIncome',
                'number', '500'] in value['tables'][0]['rows']
    run = source_run('PPh Badan', [value])
    run['records'][0]['capture_complete'] = True
    reports = []
    exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    assert reports[0]['complete'] is False and reports[0]['unmapped_rows'] >= 8


def test_every_declared_footer_keeps_its_own_original_paths_and_sequence():
    binding, auxiliary = bindings()[0], packet_map()
    request_value = {'ReturnSheetRecordId': corpus.RECORD_ID, 'PeriodYear': '2025'}
    binding['dependencies'].append({'endpoint': FOOTER, 'request_json': request_value})
    auxiliary[(FOOTER, _corporate_request_key(request_value))] = {
        'payload': _corporate_json(json.dumps(footer())), 'event': {'sequence': 4}}
    _, result = apply(binding, auxiliary=auxiliary)
    assert {e['response_sequence'] for e in result['values'] if e['path'] == ['TaxBase']} == {3, 4}
    auxiliary[(FOOTER, _corporate_request_key(request_value))]['payload']['IncomeTaxUsd'] = '0'
    with pytest.raises(_UnsupportedMetadata):
        apply(binding, auxiliary=auxiliary)


def test_l4_owner_structure_refuses_foreign_headers_or_missing_hosts():
    import coretax_corporate as observer

    class Locator:
        def __init__(self, *, count=1, metadata=None, chain=True):
            self.total, self.metadata, self.chain = count, metadata, chain

        def count(self):
            return self.total

        def locator(self, selector):
            return self

        def evaluate(self, script, *args):
            return self.metadata if 'footer_spans' in script else self.chain

    class Form:
        def __init__(self, *, broken=False, chain=True):
            self.broken, self.chain = broken, chain

        def locator(self, selector):
            if selector == 'table':
                return Locator(count=2)
            value = deepcopy(table_proofs()[0 if 'grid1' in selector else 1])
            value.pop('component')
            if self.broken:
                value['headers'] = ['FOREIGN']
            return Locator(metadata=value, chain=self.chain)

    assert observer._l4_tables(Form()) == table_proofs()
    assert observer._l4_tables(Form(broken=True)) is None
    assert observer._l4_tables(Form(chain=False)) is None


def test_empty_workbook_keeps_both_totals_numeric_and_mapping_truthful(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    result = project()
    run = source_run('PPh Badan', [section('L4', tables=result['tables'], fields=[])])
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [p for p in paths if p != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L4']
        assert sheet['A4'].value == 'TOTAL' and sheet['A10'].value == 'JUMLAH'
        assert all(sheet[cell].value == 0 and sheet[cell].data_type == 'n'
                   for cell in ('E4', 'G4', 'E10'))
        assert sheet['A3'].value is None and sheet['A9'].value is None
        assert reports[0]['complete'] is True
        assert reports[0]['unmapped_rows'] == reports[0]['unmapped_tables'] == 0
    finally:
        book.close()
