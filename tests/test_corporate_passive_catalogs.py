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


def test_only_reviewed_singleton_types_extend_the_existing_catalog_registry():
    urls = getattr(adapter, 'CORPORATE_L10_REFERENCE_URLS', None)
    assert urls == {kind: BASE + kind for kind in KINDS}
    assert all(adapter.CORPORATE_REFERENCE_REQUESTS[url] == (kind,) for kind, url in urls.items())
    before = deepcopy(catalog('TRANSACTION_TYPE'))
    projection._project_corporate_catalog(before, kind='TRANSACTION_TYPE')
    assert before == catalog('TRANSACTION_TYPE')
