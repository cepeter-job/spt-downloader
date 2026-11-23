"""C consumer seam. Shared TX producer substitution is explicit, not acceptance."""
from copy import deepcopy
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_corporate_projection as projection
import coretax_json as adapter
from coretax_json import JsonSafetyError
from test_corporate_l10c_candidate_export import envelope
from test_corporate_l7_native import selected, packet, bindings as legacy_bindings
from test_corporate_l10c_lifetime import proof as history
import support_json_corpus as corpus

COUNTRY = adapter.CORPORATE_COUNTRY_REFERENCE_URL
TRANSACTION = corpus.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/TRANSACTION_TYPE'
ROUTE = corpus.ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join((
    corpus.TAXPAYER_ID, corpus.RECORD_ID, 'ICT_RCIT', corpus.AGGREGATE_ID)) + '?view=true'


def catalog(kind, code, description):
    return [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
        {'Code': code, 'CodeDescription': description, 'ValidFrom': None, 'ValidTo': None}]}]


@pytest.fixture
def consumer_contract(monkeypatch):
    # The shared owner already registers TRANSACTION_TYPE as a reviewed
    # reference kind, so no producer substitution is needed. This fixture is
    # retained only to keep the existing test signatures stable.
    yield


def inputs():
    value = envelope()
    current = json.loads(value['Payload']['CurrentFormData'])
    current['MainFormData']['IsTransactionWithRelated'] = corpus.Number('1')
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    packets = [packet(value)]
    for sequence, endpoint, payload in (
        (2, COUNTRY, catalog('COUNTRY_CODE', 'SYN_COUNTRY', 'SYNTHETIC COUNTRY DESCRIPTION')),
        (3, TRANSACTION, catalog('TRANSACTION_TYPE', 'SYN_TRANSACTION', 'SYNTHETIC TRANSACTION DESCRIPTION'))):
        item = corpus.packet({'IsSuccessful': True, 'Payload': payload}, sequence, endpoint=endpoint)
        item['context'].update(method='GET', request_json=None)
        packets.append(item)
    record = selected()
    fact = history()
    fact.update(attempt=corpus.ATTEMPT, record_id=record['record_id'], source_url=record['list_url'], detail_url=ROUTE)
    component = {'kind': 'corporate-submitted-spa-v1', 'attempt': corpus.ATTEMPT,
        'record_id': record['record_id'], 'source_url': record['list_url'], 'detail_url': ROUTE,
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True}
    for item in packets:
        item['context'].update(frame_url=ROUTE, component_lifetime=deepcopy(component),
                               corporate_l10c_lifetime=deepcopy(fact))
    observed = [legacy_bindings()[0], {'name': 'L10-C', 'paths': [['L10cFormData']], 'grids': [],
        'projection': {'kind': 'corporate-l10c-v1', 'builds': dict(projection.L11C_BUILD_DIGESTS),
            'route': ROUTE, 'locale': 'id-ID', 'timezone': 'Asia/Jakarta',
            'visibility_binding': 'current-induk-enabled-v1',
            'references': [{'endpoint': COUNTRY, 'method': 'GET', 'sequences': [2]},
                           {'endpoint': TRANSACTION, 'method': 'GET', 'sequences': [3]}],
            'tables': [{'component': 'rsh-citr-l10c-grid1', 'headers': list(projection.L10C_HEADERS),
                        'footer_spans': []}]}}]
    return packets, record, observed


def test_populated_consumer_dispatch_binds_original_catalogs_and_keeps_control_mapping_partial(
        consumer_contract, tmp_path):
    packets, record, observed = inputs()
    before = deepcopy((packets, record, observed))
    result = adapter.adapt_corporate_detail(packets, record, corpus.SCOPE, observed)
    assert result['eligible'], result['reason']
    assert (packets, record, observed) == before
    section, = [section for section in result['sections'] if section['name'] == 'L10-C']
    assert section['tables'][0]['rows'][0][1:] == section['tables'][0]['rows'][1][1:]
    assert section['tables'][0]['rows'][0][-1] == '1.234,125'
    assert section['projection_complete'] is False
    report, = [p for p in result['provenance']['projections'] if p['form'] == 'L10-C']
    assert any(e['response_sequence'] == 3 and e['value'] == 'SYNTHETIC TRANSACTION DESCRIPTION'
               for e in report['values'])
    assert any(e['response_sequence'] == 1 and e['path'] == ['TIN'] for e in report['values'])
    assert any(e['response_sequence'] == 1 and e['path'] == ['PeriodYear'] for e in report['values'])
    record.update(capture_complete=True, sections=[section])
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
           'complete': True, 'errors': [], 'records': [record]}
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    name, = [name for name in run['output_files'] if name != 'resume.xlsx']
    book = load_workbook(tmp_path / name)
    try:
        assert book['L10-C']['E3'].value == book['L10-C']['E4'].value == 1234.125
        assert book['L10-C']['C3'].value == 'SYNTHETIC TRANSACTION DESCRIPTION'
        assert book['L10-C'].max_row == 4
    finally:
        book.close()
    mapping, = [r for r in run['template_mapping'] if r['form'] == 'L10-C']
    assert not mapping['complete'] and mapping['unmapped_fields'] == 3


@pytest.mark.parametrize('defect', ['labels-override', 'missing-history', 'pin-null', 'pin-mismatch',
    'locale', 'route', 'previous', 'main-choice', 'outer-choice', 'footer', 'missing-reference',
    'bad-sequence', 'induk-order', 'source-shape'])
def test_c_consumer_refuses_unproved_capabilities_without_label_or_control_loss(consumer_contract, defect):
    packets, record, observed = inputs()
    proof = observed[1]['projection']
    if defect == 'labels-override': proof['labels'] = {'SYN_TRANSACTION': 'FORGED DESCRIPTION'}
    elif defect == 'missing-history':
        for item in packets: del item['context']['corporate_l10c_lifetime']
    elif defect == 'pin-null': proof['builds'] = dict.fromkeys(proof['builds'])
    elif defect == 'pin-mismatch': proof['builds'][projection.MAIN_SOURCE] = '0' * 64
    elif defect == 'locale': proof['locale'] = 'en-US'
    elif defect == 'route': proof['route'] += '&history=true'
    elif defect == 'footer': proof['tables'][0]['footer_spans'] = [[4, 1]]
    elif defect == 'missing-reference': proof['references'].pop()
    elif defect == 'bad-sequence': proof['references'][1]['sequences'] = [99]
    elif defect == 'induk-order': observed.reverse()
    else:
        value = envelope()
        current = json.loads(value['Payload']['CurrentFormData'])
        current['MainFormData']['IsTransactionWithRelated'] = corpus.Number('0' if defect == 'main-choice' else '1')
        if defect == 'previous': value['Payload']['PreviousFormData'] = '{}'
        elif defect == 'outer-choice': value['Payload']['IsTransactionWithRelated'] = None
        elif defect == 'source-shape': current['L10cFormData']['SYNTHETIC_UNKNOWN'] = None
        value['Payload']['CurrentFormData'] = corpus.wire(current)
        changed = packet(value)
        changed['context'].update({key: deepcopy(packets[0]['context'][key]) for key in
            ('frame_url', 'component_lifetime', 'corporate_l10c_lifetime')})
        packets[0] = changed
    result = adapter.adapt_corporate_detail(packets, record, corpus.SCOPE, observed)
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('defect,expected', [
    ('capture_api', 'history_capture_api'),
    ('source_controls', 'history_source_controls'),
    ('grid_structure', 'history_grid_structure'),
    ('bind_start', 'history_bind_start_unknown'),
    ('bind_end', 'history_bind_end_unknown'),
    ('lifetime', 'history_lifetime'),
])
def test_l10c_history_subreason_matrix(tmp_path, defect, expected):
    """Each history predicate independently yields its fixed subreason, a None
    offer, and no downstream progression. Synthetic fixtures only."""
    import coretax_corporate as observer
    from spt_desktop import diagnostics
    inspect = getattr(observer, '_observe_l10c_projection', None)
    assert callable(inspect)

    class Node:
        def __init__(self, selector=''): self.selector = selector
        def locator(self, selector): return Node(selector)
        def count(self):
            if defect == 'source_controls' and 'PeriodYear' in self.selector:
                return 0
            if defect == 'grid_structure' and 'ui-grid-offline' in self.selector:
                return 0
            return 2 if self.selector.startswith('p-radiobutton') else 1
        def evaluate(self, script):
            return {'headers': list(projection.L10C_HEADERS), 'footer_spans': []}

    class Page:
        url = ROUTE
        def evaluate(self, script, url=None, **kwargs):
            if 'AbortController' in script:
                return None
            if url is not None:
                return projection.L10C_BUILD_DIGESTS[url]
            return {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}

    class Capture:
        def bind_l10c_structure(self, *args, **kwargs):
            phase = kwargs.get('phase')
            if defect == 'bind_start' and phase == 'start':
                return False
            if defect == 'bind_end' and phase == 'end':
                return False
            return True
        def observe_l10c_lifetime(self, **kwargs):
            return None if defect == 'lifetime' else {'kind': 'corporate-l10c-spa-v1'}
        def request_observations(self):
            return [{'url': endpoint, 'method': 'GET', 'request_json': None, 'sequence': sequence}
                    for endpoint, sequence in ((COUNTRY, 2), (TRANSACTION, 3))]

    capture = Capture()
    if defect == 'capture_api':
        capture = type('NoBind', (), {'observe_l10c_lifetime': lambda self, **kw: {'kind': 'x'}})()
    with diagnostics.session(tmp_path, 'worker') as log:
        result = inspect(Page(), Node(), Node(), Node(), capture, None)
        assert log.flush()
    assert result is None
    rows = [json.loads(line) for f in sorted((tmp_path / 'logs').glob('diag-*.jsonl'))
            for line in f.read_text(encoding='utf-8').splitlines()]
    gates = [r.get('corporate_l10c_detail_gate') for r in rows
             if r.get('event') == 'corporate.l10c_detail_gate']
    assert gates == [expected]


def test_l10c_history_success_emits_no_gate(tmp_path):
    """A clean history offers the proof and records no gate diagnostic."""
    import coretax_corporate as observer
    from spt_desktop import diagnostics
    inspect = getattr(observer, '_observe_l10c_projection', None)
    assert callable(inspect)

    class Node:
        def __init__(self, selector=''): self.selector = selector
        def locator(self, selector): return Node(selector)
        def count(self): return 2 if self.selector.startswith('p-radiobutton') else 1
        def evaluate(self, script):
            return {'headers': list(projection.L10C_HEADERS), 'footer_spans': []}

    class Page:
        url = ROUTE
        def evaluate(self, script, url=None, **kwargs):
            if 'AbortController' in script:
                return None
            if url is not None:
                return projection.L10C_BUILD_DIGESTS[url]
            return {'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}

    class Capture:
        def bind_l10c_structure(self, *args, **kwargs): return True
        def observe_l10c_lifetime(self, **kwargs): return {'kind': 'corporate-l10c-spa-v1'}
        def request_observations(self):
            return [{'url': endpoint, 'method': 'GET', 'request_json': None, 'sequence': sequence}
                    for endpoint, sequence in ((COUNTRY, 2), (TRANSACTION, 3))]

    with diagnostics.session(tmp_path, 'worker') as log:
        result = inspect(Page(), Node(), Node(), Node(), Capture(), None)
        assert log.flush()
    assert result is not None and result['kind'] == 'corporate-l10c-v1'
    rows = [json.loads(line) for f in sorted((tmp_path / 'logs').glob('diag-*.jsonl'))
            for line in f.read_text(encoding='utf-8').splitlines()]
    assert not [r for r in rows if r.get('event') == 'corporate.l10c_detail_gate']


@pytest.mark.parametrize('defect', [None, 'environment', 'provider', 'reference', 'history', 'table'])
def test_observer_descriptor_consumer_contract_without_claiming_loaded_portal_custody(
        consumer_contract, defect):
    import coretax_corporate as observer
    inspect = getattr(observer, '_observe_l10c_projection', None)
    assert callable(inspect), 'Source-only RED: no C projection observer dispatch'

    class Node:
        def __init__(self, selector=''): self.selector = selector
        def locator(self, selector): return Node(selector)
        def count(self):
            if defect == 'history' and 'PeriodYear' in self.selector:
                return 0
            return 2 if self.selector.startswith('p-radiobutton') else 1
        def evaluate(self, script):
            if defect == 'table':
                return {'headers': ['WRONG'], 'footer_spans': []}
            return {'headers': list(projection.L10C_HEADERS), 'footer_spans': []}

    class Page:
        url = ROUTE
        def evaluate(self, script, url=None, **kwargs):
            if 'AbortController' in script:
                return None
            if url is not None:
                return None if defect == 'provider' else projection.L10C_BUILD_DIGESTS[url]
            return {'locale': 'en-US' if defect == 'environment' else 'id-ID', 'timezone': 'Asia/Jakarta'}

    class Capture:
        def bind_l10c_structure(self, *args, **kwargs): return True
        def observe_l10c_lifetime(self, **kwargs): return {'kind': 'corporate-l10c-spa-v1'}
        def request_observations(self):
            return [{'url': endpoint, 'method': 'GET', 'request_json': None, 'sequence': sequence}
                    for endpoint, sequence in ((COUNTRY, 2), (TRANSACTION, 3))
                    if not (defect == 'reference' and endpoint == TRANSACTION)]

    result = inspect(Page(), Node(), Node(), Node(), Capture(), None)
    assert (result is not None) is (defect is None)
    if result is not None:
        assert result['kind'] == 'corporate-l10c-v1'
        assert {tuple(ref['sequences']) for ref in result['references']} == {(2,), (3,)}


def test_mixed_c_fact_is_fatal_before_consumer_fallback(consumer_contract):
    packets, record, observed = inputs()
    packets[2]['context']['corporate_l10c_lifetime']['attempt'] = 'b' * 32
    with pytest.raises(JsonSafetyError):
        adapter.adapt_corporate_detail(packets, record, corpus.SCOPE, observed)
