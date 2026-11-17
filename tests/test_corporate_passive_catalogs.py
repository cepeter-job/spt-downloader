"""Closed naturally emitted Corporate reference transports; synthetic CI only."""
from copy import deepcopy
import json

import pytest

import coretax_corporate_projection as projection
import coretax_json as adapter
import support_json_corpus as corpus
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import Context, Frame, exchange
from test_json_capture import Page, SCOPE
from test_corporate_component_lifetime import selected, DETAIL
from test_corporate_l7_native import bindings as legacy_bindings, packet as legacy_packet, selected as corpus_record
from test_corporate_l3_native import packet


BASE = adapter.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/'
KINDS = ('COUNTRY_CODE', 'RELATIONSHIP_TYPE', 'TRANSACTION_TYPE', 'PRICING_METHOD')
NEW_KINDS = KINDS[1:]


def catalog(kind):
    return [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
        {'Code': 'SYN_CODE', 'CodeDescription': 'Z SYNTHETIC LATER', 'ValidTo': None},
        {'Code': 'SYN_CODE', 'CodeDescription': 'A SYNTHETIC FIRST', 'ValidTo': None}]}]


@pytest.mark.parametrize('kind', NEW_KINDS)
def test_natural_singleton_retains_original_bytes_and_legacy_adapter_compatibility(tmp_path, kind):
    context, record = Context(), selected()
    page = Page(context, DETAIL)
    record['detail_url'] = DETAIL
    raw = json.dumps({'IsSuccessful': True, 'Payload': catalog(kind)}).encode()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        response = exchange(context, page, raw=raw, method='GET', url=BASE + kind)
        capture.bind_detail_page(page)
        saved = capture.drain()
        assert saved['complete'] and saved['counts']['accepted'] == 1
        bodies = list(capture.iter_bodies())
        assert bodies[0]['body'] == raw and response.reads == 1
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == bodies
    # Unused admitted catalogs remain custody, never an unbound business response.
    other = packet({'IsSuccessful': True, 'Payload': catalog(kind)}, 2, BASE + kind, None, method='GET')
    other['context'].pop('component_lifetime')
    result = adapter.adapt_corporate_detail([legacy_packet(), other], corpus_record(),
                                           corpus.SCOPE, legacy_bindings())
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert any(event.get('reference_catalog') == kind for event in result['provenance']['events'])
    parsed = adapter._corporate_json(raw)['Payload']
    projected = projection._project_corporate_catalog(parsed, kind=kind)
    assert projected['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
    assert projected['selected']['SYN_CODE']['path'] == [0, 'Details', 1, 'CodeDescription']
    assert projected['requires_vendor']


@pytest.mark.parametrize('defect', ['batch', 'checksum', 'query', 'slash', 'encoded', 'locale',
                                  'post', 'body', 'subframe', 'other-tax', 'foreign-tab'])
def test_unproved_reference_variants_are_not_observed_or_read(tmp_path, defect):
    context, record = Context(), selected()
    page = Page(context, DETAIL)
    url, target, options = BASE + 'TRANSACTION_TYPE', page, {}
    if defect == 'batch': url += ',COUNTRY_CODE'
    elif defect == 'checksum': url += '+SYNTHETIC'
    elif defect == 'query': url += '?SYNTHETIC=1'
    elif defect == 'slash': url += '/'
    elif defect == 'encoded': url = url.replace('TRANSACTION_TYPE', '%54RANSACTION_TYPE')
    elif defect == 'locale': url = url.replace('/id-ID/', '/en-US/')
    elif defect == 'post': options['method'] = 'POST'
    elif defect == 'body': options['post'] = {'SYNTHETIC': True}
    elif defect == 'subframe': options['frame'] = Frame(page, parent=page.main_frame)
    elif defect == 'other-tax': record['source_fields']['TaxTypeCode'] = 'VAT_VAT'
    elif defect == 'foreign-tab': target = Page(context, DETAIL)
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        response = exchange(context, target, url=url, method=options.pop('method', 'GET'), **options)
        capture.bind_detail_page(page)
        assert capture.drain()['responses'] == []
        assert response.reads == 0 and capture.request_observations() == []


@pytest.mark.parametrize('defect', ['method', 'missing-body-fact', 'body', 'attempt', 'clock', 'locale', 'snapshot'])
def test_new_transport_safety_is_fatal_before_any_semantic_binding(defect):
    raw = [legacy_packet(), packet({'IsSuccessful': True, 'Payload': catalog('TRANSACTION_TYPE')},
                                  2, BASE + 'TRANSACTION_TYPE', None, method='GET')]
    raw[1]['context'].pop('component_lifetime')
    if defect == 'method': raw[1]['context']['method'] = 'POST'
    elif defect == 'missing-body-fact': del raw[1]['context']['request_json']
    elif defect == 'body': raw[1]['context']['request_json'] = {}
    elif defect == 'attempt': raw[1]['context']['attempt'] = 'b' * 32
    elif defect == 'clock': raw[1]['context']['clock_interval'] = {
        'attempt': corpus.ATTEMPT, 'start_ms': 0, 'end_ms': 1, 'timezone': 'Asia/Jakarta'}
    elif defect == 'locale':
        value = catalog('TRANSACTION_TYPE')
        value[0]['Details'][0]['language'] = 'en-US'
        raw[1] = packet({'IsSuccessful': True, 'Payload': value}, 2, BASE + 'TRANSACTION_TYPE', None, method='GET')
        raw[1]['context'].pop('component_lifetime')
    else:
        value = catalog('TRANSACTION_TYPE')
        value[0]['SYNTHETIC_METADATA'] = 1
        changed = packet({'IsSuccessful': True, 'Payload': value}, 3, BASE + 'TRANSACTION_TYPE', None, method='GET')
        changed['context'].pop('component_lifetime')
        raw.append(changed)
    with pytest.raises(adapter.JsonSafetyError):
        adapter.adapt_corporate_detail(raw, corpus_record(), corpus.SCOPE, [])


@pytest.mark.parametrize('kind', NEW_KINDS)
def test_new_ordinary_catalogs_reuse_display_index_and_original_attempt_clock(kind):
    value = catalog(kind)
    details = value[0]['Details']
    details[0]['ParameterData'] = '{"DisplayIndex":1}'
    details[1]['ParameterData'] = '{"DisplayIndex":2}'
    assert projection._project_corporate_catalog(value, kind=kind)['lookups']['SYN_CODE'] == 'Z SYNTHETIC LATER'
    for row, until in zip(details, ('2027-01-01', '2028-01-01')):
        row['ValidTo'] = until
        row['ValidFrom'] = '2025-01-01'
    clock = {'attempt': 'a' * 32, 'start_ms': 1794873600000,
             'end_ms': 1794873601000, 'timezone': 'Asia/Jakarta'}
    bound = projection._project_corporate_catalog(value, kind=kind, clock_interval=clock)
    assert bound['lookups']['SYN_CODE'] == 'Z SYNTHETIC LATER'
    assert bound['selected']['SYN_CODE']['clock_interval'] == clock
    with pytest.raises(adapter._UnsupportedMetadata):
        projection._project_corporate_catalog(value, kind=kind)
    clock['end_ms'] = 1830000000000
    with pytest.raises(adapter._UnsupportedMetadata, match='unstable'):
        projection._project_corporate_catalog(value, kind=kind, clock_interval=clock)


def test_only_reviewed_singleton_types_extend_the_existing_catalog_registry():
    urls = getattr(adapter, 'CORPORATE_L10_REFERENCE_URLS', None)
    assert urls == {kind: BASE + kind for kind in KINDS}
    assert all(adapter.CORPORATE_REFERENCE_REQUESTS[url] == (kind,) for kind, url in urls.items())
    before = deepcopy(catalog('TRANSACTION_TYPE'))
    projection._project_corporate_catalog(before, kind='TRANSACTION_TYPE')
    assert before == catalog('TRANSACTION_TYPE')
