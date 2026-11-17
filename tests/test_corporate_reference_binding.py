"""Shared packet-binding seam reuses the existing Corporate catalog projector."""
from copy import deepcopy

import pytest

import coretax_corporate as observer
import coretax_corporate_projection as projection
import coretax_json as adapter
import support_json_corpus as corpus
from test_corporate_l11c_native import L11C_PINS
from test_corporate_l1d_native import packet as primary
from test_corporate_l3_native import packet, DETAIL
from test_corporate_l7_native import selected
from test_corporate_passive_catalogs import BASE, KINDS, catalog


def case():
    record = selected()
    lifetime = primary()['context']['component_lifetime']
    provider = {'kind': 'corporate-reference-providers-v1', 'attempt': corpus.ATTEMPT,
        'record_id': record['record_id'], 'source_url': record['list_url'],
        'detail_url': DETAIL, 'builds': dict(L11C_PINS)}
    clock = {'attempt': corpus.ATTEMPT, 'start_ms': 1800000000000,
             'end_ms': 1800000001000, 'timezone': 'Asia/Jakarta'}
    raw = [primary()]
    for index, kind in enumerate(KINDS, 2):
        raw.append(packet({'IsSuccessful': True, 'Payload': catalog(kind)}, index,
                          BASE + kind, None, method='GET'))
    for value in raw:
        value['context'].update(component_lifetime=deepcopy(lifetime),
            clock_interval=dict(clock), corporate_reference_providers=deepcopy(provider))
    decoded, sequences = {}, set()
    choice = adapter._corporate_selected(record, corpus.SCOPE)
    for item in raw:
        envelope, _, _, event = adapter._corporate_packet(item, choice, corpus.SCOPE,
            corpus.ATTEMPT, sequences, allow_corporate_reference=True)
        decoded[event['sequence']] = {'payload': envelope['Payload'], 'event': event, 'successful': True}
    refs = [{'endpoint': BASE + kind, 'method': 'GET', 'sequences': [index]}
            for index, kind in enumerate(KINDS, 2)]
    return decoded.pop(1)['event'], decoded, refs


def bind(event, packets, refs):
    method = getattr(projection, 'bind_corporate_reference_catalogs', None)
    assert callable(method), 'Source-only RED: shared original-packet binder absent'
    return method(refs, packets, kinds=KINDS, event=event, builds=L11C_PINS)


def test_populated_lookup_uses_full_snapshot_order_minimum_sequence_and_original_paths():
    event, packets, refs = case()
    repeated = deepcopy(packets[2])
    repeated['event']['sequence'] = 9
    packets[9] = repeated
    refs[0]['sequences'] = [9, 2]
    before = deepcopy((event, packets, refs))
    bound = bind(event, dict(reversed(list(packets.items()))), list(reversed(refs)))
    assert set(bound) == set(KINDS)
    for kind in KINDS:
        assert bound[kind]['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
        assert bound[kind]['selected']['SYN_CODE']['path'] == [0, 'Details', 1, 'CodeDescription']
    assert bound['COUNTRY_CODE']['source']['sequence'] == 2
    assert bound['COUNTRY_CODE']['sequences'] == [2, 9]
    assert (event, packets, refs) == before


@pytest.mark.parametrize('defect', ['missing', 'failed', 'omitted-sequence', 'extra-sequence',
    'duplicate', 'bool', 'method', 'alias', 'duplicate-endpoint', 'provider-missing',
    'clock', 'attempt', 'frame', 'body', 'changed-full-snapshot'])
def test_unproved_catalog_binding_never_supplies_a_label(defect):
    event, packets, refs = case()
    if defect == 'missing': packets.pop(2)
    elif defect == 'failed': packets[2]['successful'] = False
    elif defect == 'omitted-sequence':
        packets[9] = deepcopy(packets[2]); packets[9]['event']['sequence'] = 9
    elif defect == 'extra-sequence': refs[0]['sequences'].append(99)
    elif defect == 'duplicate': refs[0]['sequences'].append(2)
    elif defect == 'bool': refs[0]['sequences'] = [True]
    elif defect == 'method': refs[0]['method'] = 'POST'
    elif defect == 'alias': refs[0]['endpoint'] += '+SYNTHETIC'
    elif defect == 'duplicate-endpoint': refs[1] = deepcopy(refs[0])
    elif defect == 'provider-missing': del event['corporate_reference_providers']
    elif defect == 'clock': packets[2]['event']['clock_interval']['end_ms'] += 1
    elif defect == 'attempt': packets[2]['event']['attempt'] = 'b' * 32
    elif defect == 'frame': packets[2]['event']['frame_url'] += '#SYNTHETIC'
    elif defect == 'body': packets[2]['event']['request_json'] = {}
    else:
        packets[9] = deepcopy(packets[2]); packets[9]['event']['sequence'] = 9
        packets[9]['event']['sha256'] = '0' * 64
        refs[0]['sequences'].append(9)
    with pytest.raises((adapter._UnsupportedMetadata, adapter.JsonSafetyError)):
        bind(event, packets, refs)


def test_uniform_malformed_parent_lifetime_cannot_authorize_a_shared_catalog():
    event, packets, refs = case()
    incomplete = {'source_url': event['component_lifetime']['source_url']}
    event['component_lifetime'] = deepcopy(incomplete)
    for packet in packets.values(): packet['event']['component_lifetime'] = deepcopy(incomplete)
    with pytest.raises(adapter.JsonSafetyError): bind(event, packets, refs)


def test_observer_collects_only_original_exact_requests_without_any_catalog_fetch():
    event, packets, refs = case()
    class Capture:
        def observe_corporate_reference_providers(self, **kwargs): return dict(L11C_PINS)
        def request_observations(self):
            return [{**packet['event'], 'request_json': None} for packet in packets.values()]
    method = getattr(observer, 'corporate_reference_bindings', None)
    assert callable(method), 'Source-only RED: shared observer metadata collector absent'
    assert method(Capture(), KINDS) == {'builds': L11C_PINS, 'references': refs}
    assert method(Capture(), ('SYNTHETIC_UNREVIEWED',)) is None
    packets.pop(2)
    assert method(Capture(), KINDS) is None
    assert event['frame_url'] == DETAIL
