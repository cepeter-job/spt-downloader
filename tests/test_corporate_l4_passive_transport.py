"""Two source-reviewed L4 singleton transports; hosted execution only."""
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
from test_corporate_l7_native import bindings, packet as primary, selected as corpus_record
from test_corporate_l3_native import packet


BASE = corpus.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/'
KINDS = ('TAX_OBJECT_CODE', 'INCOME_EXCLUDED_FROM_TAX_FOR_CIT')


def catalog(kind):
    return [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
        {'Code': 'SYN_CODE', 'CodeDescription': 'Z SYNTHETIC', 'ValidTo': None},
        {'Code': 'SYN_CODE', 'CodeDescription': 'A SYNTHETIC', 'ValidTo': None}]}]


@pytest.mark.parametrize('kind', KINDS)
def test_l4_singleton_capture_and_shared_order_preserve_original_bytes(tmp_path, kind):
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
        assert response.reads == 1 and bodies[0]['body'] == raw
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == bodies
    other = packet({'IsSuccessful': True, 'Payload': catalog(kind)}, 2, BASE + kind, None, method='GET')
    other['context'].pop('component_lifetime')
    result = adapter.adapt_corporate_detail([primary(), other], corpus_record(), corpus.SCOPE, bindings())
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert adapter.CORPORATE_REFERENCE_REQUESTS[BASE + kind] == (kind,)
    value = adapter._corporate_json(raw)['Payload']
    before = deepcopy(value)
    projected = projection._project_corporate_catalog(value, kind=kind)
    assert projected['lookups'] == {'SYN_CODE': 'A SYNTHETIC'}
    assert projected['selected']['SYN_CODE']['path'] == [0, 'Details', 1, 'CodeDescription']
    assert projected['requires_vendor'] and value == before


@pytest.mark.parametrize('kind', KINDS)
@pytest.mark.parametrize('defect', ['batch', 'checksum', 'query', 'slash', 'encoded', 'locale',
    'post', 'body', 'subframe', 'other-tax', 'other-sheet', 'foreign-tab', 'resource', 'description'])
def test_l4_transport_variants_are_never_observed_or_read(tmp_path, kind, defect):
    context, record = Context(), selected()
    page = Page(context, DETAIL)
    url, target, options = BASE + kind, page, {}
    if defect == 'batch': url += ',COUNTRY_CODE'
    elif defect == 'checksum': url += '+SYNTHETIC'
    elif defect == 'query': url += '?SYNTHETIC=1'
    elif defect == 'slash': url += '/'
    elif defect == 'encoded': url = url.replace(kind, '%' + format(ord(kind[0]), '02X') + kind[1:])
    elif defect == 'locale': url = url.replace('/id-ID/', '/en-US/')
    elif defect == 'post': options['method'] = 'POST'
    elif defect == 'body': options['post'] = {'SYNTHETIC': True}
    elif defect == 'subframe': options['frame'] = Frame(page, parent=page.main_frame)
    elif defect == 'other-tax': record['source_fields']['TaxTypeCode'] = 'VAT_VAT'
    elif defect == 'other-sheet': record['source_fields']['ReturnSheetTypeCode'] = 'VAT_VATR'
    elif defect == 'foreign-tab': target = Page(context, DETAIL)
    elif defect == 'description': url = BASE.rsplit('/id-ID/', 1)[0] + '/getdescription'
    # exchange constructs the request before emitting it. The resource negative
    # uses its existing request helper to avoid changing the production capture.
    if defect == 'resource':
        from support_json_network import Request, Response
        req = Request(page, url=url, method='GET')
        req.resource_type = 'document'
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        if defect == 'resource':
            response = Response(req)
            context.emit('request', req)
            context.emit('response', response)
            context.emit('requestfinished', req)
        else:
            response = exchange(context, target, url=url, method=options.pop('method', 'GET'), **options)
        capture.bind_detail_page(page)
        assert capture.drain()['responses'] == []
        assert response.reads == 0 and capture.request_observations() == []


@pytest.mark.parametrize('kind', KINDS)
def test_l4_adapter_requires_explicit_original_no_body_fact(kind):
    other = packet({'IsSuccessful': True, 'Payload': catalog(kind)}, 2, BASE + kind, None, method='GET')
    other['context'].pop('component_lifetime')
    del other['context']['request_json']
    with pytest.raises(adapter.JsonSafetyError, match='unsafe'):
        adapter.adapt_corporate_detail([primary(), other], corpus_record(), corpus.SCOPE, [])
