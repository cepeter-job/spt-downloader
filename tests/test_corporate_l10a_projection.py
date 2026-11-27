from conftest import pin_override
"""L10-A empty-only custody; populated descriptions remain unproved (CI-only)."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import JsonSafetyError, _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus

GRID = corpus.ORIGIN + '/returnsheet/api/loadcit/l10a-grid'
ROOT = 'DeclarationTransactionRelatedParties'
FRAME = (corpus.ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' +
         '/'.join((corpus.TAXPAYER_ID, corpus.RECORD_ID, 'ICT_RCIT', corpus.AGGREGATE_ID)) + '?view=true')
ABSENT = object()


def module():
    return importlib.import_module('coretax_corporate_projection')


def row(**overrides):
    value = {'RecordId': '00000000-0000-4000-8000-000000000010',
             'Name': 'SYNTHETIC RELATED PARTY', 'TIN': '0000000000000002',
             'Country': 'IDN', 'RelationshipCode': '01',
             'BusinessActivity': 'SYNTHETIC ACTIVITY', 'TypeOfTransaction': '01',
             'TransactionValue': corpus.Number('1234'),
             'PricingMethod': '01', 'ReasonPricingMethod': 'SYNTHETIC REASON'}
    value.update(overrides)
    return value


def project(rows, **overrides):
    options = {'headers': list(module().L10A_HEADERS), 'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    return module().project_l10a(rows, **options)


def request(first=0):
    return {'ReturnSheetRecordId': corpus.RECORD_ID, 'First': first, 'Rows': 10,
            'SortField': '', 'SortOrder': 1, 'Filters': [], 'LanguageId': 'id-ID'}


def owned(packet, route=FRAME):
    packet['context'].update(frame_url=route, component_lifetime={
        'kind': 'corporate-submitted-spa-v1', 'attempt': corpus.ATTEMPT,
        'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': route,
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True})
    return packet


def grid_packet(rows=(), sequence=2, *, total=None, query=None, endpoint=GRID,
                successful=True, status=200):
    rows = list(rows) if isinstance(rows, tuple) else rows
    return owned(corpus.packet({'IsSuccessful': successful, 'Payload': {
        'TotalRecords': (len(rows) if rows is not None else 0) if total is None else total,
        'Data': rows, 'Index': None}}, sequence, endpoint=endpoint,
        request=request() if query is None else query, status=status))


def proof():
    return {'kind': 'corporate-l10a-empty-v1',
            'builds': {module().CIT_SOURCE: module().BUILD_DIGESTS[module().CIT_SOURCE]}, 'route': FRAME}


def observed(projection=None, *, query=None, endpoint=GRID):
    forms = corpus.observed()
    forms[0]['projection']['route'] = FRAME
    forms.append({'name': 'L10-A', 'paths': [[ROOT]],
        'grids': [{'name': 'L10-A/l10a-grid', 'endpoint': endpoint,
                  'pages': [{'request_json': request() if query is None else query, 'offset': 0}]}],
        'responses': [], 'dependencies': [], 'projection': proof() if projection is None else projection})
    return forms


def primary(value=ABSENT):
    form = corpus.current_form()
    if value is not ABSENT:
        form[ROOT] = value
    return owned(corpus.primary(form))


def selected():
    record = corpus.selected_record()
    record['source_fields'].update(ReturnSheetTypeCode='ICT_RCITR', ReturnSheetStatusCode='SUBMITTED',
                                  ReturnSheetModel='Normal')
    return record


def adapt(forms=None, packets=None, record=None):
    return adapt_corporate_detail(iter([primary(), grid_packet()] if packets is None else packets),
        selected() if record is None else record, corpus.SCOPE, observed() if forms is None else forms)


def test_caption_row_is_the_reviewed_grid_column_order():
    assert module().L10A_HEADERS == [
        'Nama', 'NPWP/TIN', 'Negara', 'BENTUK HUBUNGAN', 'Kegiatan Usaha', 'Jenis Transaksi',
        'NILAI TRANSAKSI (Rupiah)', 'METODE PENENTUAN HARGA TRANSFER YANG DIGUNAKAN',
        'ALASAN PENGGUNAAN METODE']
    assert module().L10A_COLUMNS == ('Name', 'TIN', 'Country', 'RelationshipCode',
        'BusinessActivity', 'TypeOfTransaction', 'TransactionValue', 'PricingMethod', 'ReasonPricingMethod')


def test_empty_projector_emits_no_invented_rows_or_values():
    assert project([]) == {'rows': [], 'provenance': []}


@pytest.mark.parametrize('value', [None, 0, {}, [row()], [row(), row()],
    [row(Country=None, RelationshipCode=None, TypeOfTransaction=None, PricingMethod=None)],
    [row(TransactionValue=None)], [row(TransactionValue=corpus.Number('1234.5'))],
    [row(TransactionValue=corpus.Number('-0'))],
    [row(TransactionValue=corpus.Number('1000000000000000'))]])
def test_populated_or_unknown_projector_input_cannot_certify_display(value):
    with pytest.raises(_UnsupportedMetadata):
        project(value)


@pytest.mark.parametrize('options', [{'headers': []}, {'locale': 'en-US'}, {'tax_type': 'ICT_ROGCIT'}])
def test_empty_projector_still_requires_its_reviewed_structure(options):
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l10a_structure'):
        project([], **options)


@pytest.mark.parametrize('value', [ABSENT, None, [], {}])
@pytest.mark.parametrize('data', [[], None])
def test_only_original_inert_root_and_captured_zero_grid_are_admitted(value, data):
    packets = [primary(value), grid_packet(data)]
    before = deepcopy(packets)
    result = adapt(packets=packets)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert packets == before
    section, = [s for s in result['sections'] if s['name'] == 'L10-A']
    table, = section['tables']
    assert table == {'name': 'L10-A/l10a-grid', 'headers': module().L10A_HEADERS, 'rows': [],
        'footer': [], 'footer_spans': [], 'body_row_count': 0, 'source_total': 0, 'complete': True}
    projection, = [p for p in result['provenance']['projections'] if p['form'] == 'L10-A']
    root = projection['source_root']
    assert root['present'] is (value is not ABSENT)
    assert root['path'] == [ROOT] and root['response_sequence'] == 1
    assert root['container'] == ['Payload', 'CurrentFormData']
    if value is ABSENT:
        assert 'value' not in root and 'type' not in root
    else:
        assert root['value'] == value
        assert root['type'] == ('null' if value is None else 'array' if isinstance(value, list) else 'object')
    values = {tuple(v['path']): v for v in projection['values']}
    assert values[('Data',)]['value'] == data
    assert values[('Data',)]['type'] == ('null' if data is None else 'array')
    assert values[('TotalRecords',)]['type'] == 'number' and values[('TotalRecords',)]['value'] == '0'
    assert values[('Index',)]['type'] == 'null' and values[('Index',)]['value'] is None
    assert all(v['response_sequence'] == 2 and v['container'] == ['Payload'] for v in values.values())


@pytest.mark.parametrize('value', [[{}], {'Body': []}, {'Body': {}}, [None], {'Amount': 0},
                                 '', '[]', corpus.Number('0'), False])
def test_nonempty_decoded_root_cannot_hide_in_one_flattened_leaf(value):
    result = adapt(packets=[primary(value), grid_packet()])
    assert not result['eligible'] and result['sections'] == []
    assert 'unsupported_corporate_l10a_source_root' in result['reason']


@pytest.mark.parametrize('rows', [[row()], [row(), row()], [{}]])
def test_populated_grid_retains_whole_record_fallback_even_when_codes_look_displayable(rows):
    result = adapt(packets=[primary(), grid_packet(rows)])
    assert not result['eligible'] and result['sections'] == []
    assert 'unsupported_corporate_l10a_populated' in result['reason']


@pytest.mark.parametrize('digest', ['a' * 64, None, '', 'APPROVED', 'F' * 64])
def test_proof_digest_must_equal_the_configured_reviewed_pin(digest):
    marker = proof()
    marker['builds'][module().CIT_SOURCE] = digest
    result = adapt(observed(marker))
    assert not result['eligible'] and 'unverified_corporate_l10a_binding' in result['reason']


def test_missing_configured_pin_and_missing_observed_digest_do_not_equal_permission(monkeypatch):
    marker = proof()
    marker['builds'][module().CIT_SOURCE] = None
    forms = observed(marker)
    forms[0].pop('projection')  # Isolate L10-A from Induk's separate missing-pin gate.
    pin_override(monkeypatch, {})
    result = adapt(forms)
    assert not result['eligible'] and 'unverified_corporate_l10a_binding' in result['reason']


@pytest.mark.parametrize('kind', ['corporate-l10a-v1', 'corporate-l10a-v0', None])
def test_old_unsafe_capability_is_not_reinterpreted_as_empty_proof(kind):
    marker = proof()
    marker['kind'] = kind
    assert not adapt(observed(marker))['eligible']


@pytest.mark.parametrize('change', ['route', 'extra', 'build-extra', 'path'])
def test_proof_shape_and_declared_root_are_closed(change):
    forms = observed()
    marker = forms[-1]['projection']
    if change == 'route':
        marker['route'] += '/changed'
    elif change == 'extra':
        marker['locale'] = 'id-ID'
    elif change == 'build-extra':
        marker['builds'][module().MAIN_SOURCE] = 'a' * 64
    else:
        forms[-1]['paths'] = [[ROOT, 'Body']]
    assert not adapt(forms)['eligible']


@pytest.mark.parametrize('change', ['missing-lifetime', 'legacy-route', 'no-induk-order', 'model'])
def test_empty_projection_retains_submitted_rupiah_owned_lifecycle(change):
    forms, packets, record = observed(), [primary(), grid_packet()], selected()
    if change == 'missing-lifetime':
        for packet in packets:
            packet['context'].pop('component_lifetime')
    elif change == 'legacy-route':
        for packet in packets:
            owned(packet, FRAME.removesuffix('?view=true'))
        for form in forms:
            form['projection']['route'] = FRAME.removesuffix('?view=true')
    elif change == 'no-induk-order':
        forms.reverse()
    else:
        record['source_fields']['ReturnSheetModel'] = 'Amendment 002'
    if change == 'legacy-route':
        # A valid component lifetime cannot bind a legacy query-free route.
        # Preserve the packet decoder's earlier fatal refusal, not fallback.
        with pytest.raises(JsonSafetyError, match='Captured component lifetime route is unverified'):
            adapt(forms, packets, record)
    else:
        assert not adapt(forms, packets, record)['eligible']


def test_semantic_route_guard_is_separately_closed_before_page_consumption():
    # The packet decoder cannot produce a valid legacy-route lifetime. Exercise
    # the semantic defense directly without weakening that upstream contract.
    forms = observed()
    forms[-1]['projection']['route'] = FRAME.removesuffix('?view=true')
    event = {'frame_url': FRAME.removesuffix('?view=true'), 'component_lifetime': {}}
    with pytest.raises(_UnsupportedMetadata, match='unverified_corporate_l10a_submitted_lifecycle'):
        module()._apply_l10a(forms[-1], {}, forms, root={},
            payload={'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL'},
            record=selected(), event=event, grid_packets={})


@pytest.mark.parametrize('change', [{'Rows': 20}, {'Rows': True}, {'SortField': 'Name'},
    {'SortOrder': -1}, {'Filters': [{'Field': 'Name'}]}, {'LanguageId': 'en-US'},
    {'Language': 'id-ID'}, {'First': 10}])
def test_only_exact_reviewed_first_ten_row_query_can_be_projected(change):
    query = {**request(), **change}
    assert not adapt(observed(query=query), [primary(), grid_packet(query=query)])['eligible']


def test_early_packet_binding_refusal_precedes_semantic_endpoint_guard():
    forms = observed(endpoint=corpus.ORIGIN + '/returnsheet/api/loadcit/synthetic')
    assert adapt(forms)['reason'] == 'unbound_corporate_source_response,incomplete_corporate_grid_source'


def test_aligned_packet_reaches_separate_reviewed_endpoint_guard():
    endpoint = corpus.ORIGIN + '/returnsheet/api/loadcit/synthetic'
    result = adapt(observed(endpoint=endpoint), [primary(), grid_packet(endpoint=endpoint)])
    assert not result['eligible'] and 'unverified_corporate_l10a_grid_binding' in result['reason']


@pytest.mark.parametrize('defect', ['missing', 'failed', 'http', 'incomplete'])
def test_empty_without_successful_complete_original_page_is_not_evidence(defect):
    packet = grid_packet(successful=defect != 'failed', status=500 if defect == 'http' else 200,
                         total=1 if defect == 'incomplete' else 0)
    assert not adapt(packets=[primary()] if defect == 'missing' else [primary(), packet])['eligible']


def test_page_provenance_uses_earliest_successful_sequence_not_iterator_order():
    result = adapt(packets=[primary(), grid_packet(sequence=7), grid_packet(sequence=2)])
    assert result['eligible'], result['reason']
    projection, = [p for p in result['provenance']['projections'] if p['form'] == 'L10-A']
    assert {v['response_sequence'] for v in projection['values']} == {2}


def test_page_source_requires_exact_query_and_success_not_just_same_offset():
    def source(sequence, *, query=None, successful=True, status=200):
        return {'payload': {'Data': [], 'TotalRecords': _CorporateNumber('0'), 'Index': None},
            'successful': successful, 'event': {'url': GRID, 'method': 'POST', 'sequence': sequence,
                'status': status, 'request_json': request() if query is None else query}}
    packets = {1: source(1, query={**request(), 'Rows': 20}), 2: source(2, successful=False),
               3: source(3, status=500), 9: source(9), 4: source(4)}
    assert module()._l10a_page_source(packets, request())['event']['sequence'] == 4
    with pytest.raises(_UnsupportedMetadata, match='missing_corporate_l10a_grid_response'):
        module()._l10a_page_source({k: v for k, v in packets.items() if k < 4}, request())


def test_changed_page_snapshot_remains_fatal_before_projection():
    with pytest.raises(JsonSafetyError):
        adapt(packets=[primary(), grid_packet(sequence=2), grid_packet([row()], sequence=3)])


def test_empty_l10a_saved_workbook_has_no_fabricated_body_value(tmp_path):
    from openpyxl import load_workbook
    import coretax_exporter as exporter
    from support_templates import source_run
    result = adapt(packets=[primary([]), grid_packet()])
    assert result['eligible'], result['reason']
    run = source_run('PPh Badan', [s for s in result['sections'] if s['name'] == 'L10-A'])
    run['year'] = 2025
    run['records'][0]['meta']['Masa Pajak'] = 'Januari - Desember 2025'
    run['records'][0]['capture_complete'] = True
    reports = []
    paths = exporter.export_split_workbooks(run, tmp_path, mapping_reports=reports)
    name, = [item for item in paths if item != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        sheet = book['L10-A']
        assert [sheet.cell(2, column).value for column in range(1, 10)] == module().L10A_HEADERS
        assert all(sheet.cell(3, column).value is None for column in range(1, 10))
        assert reports[0]['complete'] is True
        assert reports[0]['unmapped_fields'] == reports[0]['unmapped_tables'] == 0
    finally:
        book.close()


@pytest.mark.parametrize('route', [FRAME, FRAME.removesuffix('?view=true')])
def test_observer_emits_empty_only_capability_on_the_literal_selected_route(monkeypatch, route):
    from types import SimpleNamespace
    import coretax_corporate as observer

    class Element:
        def count(self):
            return 1

        def is_visible(self):
            return True

        def locator(self, selector):
            return self

        def nth(self, index):
            return self

    class Tab:
        def __init__(self, name):
            self.name = name

        def evaluate(self, script):
            return self.name not in ('Induk', 'L10-A')

        def inner_text(self):
            return self.name

    class Tabs:
        def __init__(self):
            self.tabs = [Tab(name) for name in observer.FORMS]

        def count(self):
            return len(self.tabs)

        def nth(self, index):
            return self.tabs[index]

    evaluations = []

    def evaluate(script, arg):
        # Exactly the original CIT asset read; no environment/cache/catalog probe.
        evaluations.append(arg)
        return observer.CIT_SOURCE_SHA256

    monkeypatch.setattr(observer, '_tabs', lambda page: (Element(), Tabs()))
    monkeypatch.setattr(observer, '_native_panel', lambda *args: Element())
    monkeypatch.setattr(observer, '_turn_grid', lambda *args: True)
    capture = SimpleNamespace(request_observations=lambda: [
        {'url': GRID, 'method': 'POST', 'sequence': 2, 'request_json': request()}])
    forms = observer.observe_forms(SimpleNamespace(url=route, evaluate=evaluate), selected(), corpus.SCOPE,
                                   capture, approved_digest=observer.CIT_SOURCE_SHA256)
    assert forms is not None
    binding, = [f for f in forms if f['name'] == 'L10-A']
    assert binding['grids'][0]['pages'] == [{'request_json': request(), 'offset': 0}]
    if route == FRAME:
        assert binding['projection'] == proof()
    else:
        assert 'projection' not in binding  # Legacy leaves grant no semantic mapping.
    assert evaluations == [observer.CIT_SOURCE_URL]
