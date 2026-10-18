"""Exact PPh21 reference GET custody, not a broad reference-service scraper."""
import pytest

from coretax_json import ORIGIN
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import Context, Frame, Request, Response
from test_json_capture import Page, DETAIL_URL, SCOPE, record

URL = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/EBUPOT_TAX_CERTIFICATE,COUNTRY_CODE,EBUPOT_STATUS'
RAW = b'{"IsSuccessful":true,"Payload":[{"ReferenceDataType":"COUNTRY_CODE","Details":[]}]}'


def exchange(context, page, *, url=URL, method='GET', frame=None, status=200):
    request = Request(page, url=url, method=method, frame=frame)
    response = Response(request, RAW, status=status, content_type='text/html' if status != 200 else 'application/json')
    context.emit('request', request)
    context.emit('response', response)
    request.finished = True
    context.emit('requestfinished', request)
    return response


def selected(tax='PPh Pasal 21/26'):
    result = record()
    result['meta']['Jenis Pajak'] = tax
    return result


@pytest.mark.parametrize('url', [URL, URL.rsplit('/', 1)[0] + '/RETURN_SHEET_MODEL'])
def test_reference_get_is_saved_byte_for_byte_and_replayed_through_checkpoint(tmp_path, url):
    context = Context()
    page = Page(context, DETAIL_URL)
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        response = exchange(context, page, url=url)
        assert response.reads == 0
        capture.bind_detail_page(page)
        result = capture.drain()
        assert result['complete'] and result['counts']['accepted'] == 1
        bodies = list(capture.iter_bodies())
        assert bodies[0]['body'] == RAW and bodies[0]['context']['method'] == 'GET'
        assert bodies[0]['context']['url'] == url
        assert response.reads == 1
        assert list(checkpoint_bodies(tmp_path, result, selected(), SCOPE)) == bodies


@pytest.mark.parametrize('defect', ['other-tax', 'wrong-path', 'other-locale', 'query', 'post',
                                     'untrusted', 'subframe', 'foreign-tab', 'foreign-frame'])
def test_reference_admission_does_not_expand_endpoint_or_owner_scope(tmp_path, defect):
    context = Context()
    page = Page(context, DETAIL_URL)
    target, kwargs = page, {}
    if defect == 'wrong-path':
        kwargs['url'] = URL.replace('EBUPOT_STATUS', 'UNKNOWN_CATALOG')
    elif defect == 'other-locale':
        kwargs['url'] = URL.replace('/id-ID/', '/en-US/')
    elif defect == 'query':
        kwargs['url'] = URL + '?other=1'
    elif defect == 'post':
        kwargs['method'] = 'POST'
    elif defect == 'untrusted':
        kwargs['url'] = URL.replace(ORIGIN, 'https://untrusted.invalid')
    elif defect == 'subframe':
        kwargs['frame'] = Frame(page, parent=page.main_frame)
    elif defect == 'foreign-tab':
        target = Page(context, DETAIL_URL)
    elif defect == 'foreign-frame':
        page.url = DETAIL_URL.replace('fixture-record', 'other-record')
    with DetailJsonCapture(context, page, selected('PPN' if defect == 'other-tax' else 'PPh Pasal 21/26'), SCOPE, tmp_path) as capture:
        response = exchange(context, target, **kwargs)
        page.url = DETAIL_URL
        capture.bind_detail_page(page)
        result = capture.drain()
        assert response.reads == 0 and result['counts']['accepted'] == 0
        assert capture.request_observations() == []


@pytest.mark.parametrize('status', [401, 403])
def test_reference_authorization_failure_is_recorded_without_reading_body(tmp_path, status):
    context = Context()
    page = Page(context, DETAIL_URL)
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        response = exchange(context, page, status=status)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['complete'] and 'authorization-rejected' in result['reasons']
        assert response.reads == 0 and result['responses'] == []
        assert capture.request_observations()[0]['status'] == status
