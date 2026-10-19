"""Unifikasi catalogs must have exact endpoint, owner and byte custody."""
from copy import deepcopy
import pytest
from coretax_json import JsonSafetyError, ORIGIN
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from coretax_masa_json import adapt_masa_detail
from masa_json_fixtures import packet
from support_json_network import Context
from test_json_capture import Page, DETAIL_URL, SCOPE
from test_pph21_reference_capture import RAW, exchange, selected
from test_unifikasi_json_identity import source_case
from test_unifikasi_json_references import TYPES, catalogs

URL = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + ','.join(TYPES)
TAX = 'PPh Unifikasi'


def reference():
    item = packet(TAX, catalogs(), sequence=100)
    item['context'].update(url=URL, method='GET', request_json=None)
    return item


def test_exact_get_preserves_bytes_and_checkpoint(tmp_path):
    context = Context()
    page = Page(context, DETAIL_URL)
    record = selected(TAX)
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        response = exchange(context, page, url=URL)
        assert response.reads == 0
        capture.bind_detail_page(page)
        result = capture.drain()
        assert result['complete'] and result['counts']['accepted'] == 1
        bodies = list(capture.iter_bodies())
        assert bodies[0]['body'] == RAW and bodies[0]['context']['url'] == URL
        assert response.reads == 1
        assert list(checkpoint_bodies(tmp_path, result, record, SCOPE)) == bodies


def test_reference_admission_does_not_invent_form_coverage():
    case = source_case()
    bodies = [case['packets'][0], reference()]
    before = deepcopy(bodies)
    result = adapt_masa_detail(bodies, record=case['record'], scope=case['scope'], observed_forms=[])
    assert not result['eligible'] and not result['coverage']['complete']
    assert len(result['provenance']['events']) == 2
    assert bodies == before


@pytest.mark.parametrize('defect', ['hash', 'scope', 'method', 'request-body', 'query', 'authorization'])
def test_reference_contradictions_are_fatal_without_observer(defect):
    case = source_case()
    item = reference()
    context = item['context']
    if defect == 'hash':
        context['sha256'] = '0' * 64
    elif defect == 'scope':
        context['scope'][1] = 2024
    elif defect == 'method':
        context['method'] = 'POST'
    elif defect == 'request-body':
        context['request_json'] = {'unexpected': True}
    elif defect == 'query':
        context['url'] += '?other=1'
    else:
        context['status'] = 403
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([case['packets'][0], item], record=case['record'],
                          scope=case['scope'], observed_forms=[])
