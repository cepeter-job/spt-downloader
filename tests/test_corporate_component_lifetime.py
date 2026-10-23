"""Synthetic fresh-component attestations; runner execution only."""
import hashlib
import json

import pytest

from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import Context, Request, exchange
from test_json_capture import Page, ORIGIN, SCOPE, RAW, record as old_record
from support_json_network import API_URL

LIST = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/fixture-taxpayer'
DETAIL = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/fixture-taxpayer/fixture-record/ICT_RCIT/fixture-aggregate?view=true'


def selected():
    result = old_record()
    result['meta']['Jenis Pajak'] = 'PPh Badan'
    result['source_fields'] = {'TaxTypeCode': 'ICT_RCIT', 'ReturnSheetTypeCode': 'ICT_RCITR'}
    return result


class Document:
    def __init__(self, page):
        self.page = page
        self.generation = page.generation
        self.disposed = False
        self.on_read = None

    def evaluate(self, script):
        assert script.replace(' ', '') in ('(d)=>d===document', '(d)=>document===d')
        if self.on_read:
            self.on_read()
        return self.generation is self.page.generation

    def dispose(self):
        self.disposed = True


def setup(*, owned=True, url=LIST):
    context = Context()
    if owned:
        context._spt_financial_route_policy = 'service_workers_blocked'
    page = Page(context, url)
    page.generation = object()
    page.documents = []
    page.evaluate = lambda script: {'source_owner': page.url == LIST,
                                    'detail_owner': page.url == DETAIL} if 'source_owner' in script else None
    def handle(script):
        assert script.replace(' ', '') == '()=>document'
        document = Document(page)
        page.documents.append(document)
        return document
    page.evaluate_handle = handle
    return context, page


def begin(capture):
    method = getattr(capture, 'begin_readonly_view', None)
    assert callable(method), 'Inspected-View component lifetime capture is absent'
    method()


def observe(capture):
    method = getattr(capture, 'observe_component_lifetime', None)
    assert callable(method), 'Value-free component lifetime observation is absent'
    return method()


def navigate(page, url):
    page.url = url
    page.emit('framenavigated', page.main_frame)


def expected(capture):
    return {'attempt': capture.attempt, 'kind': 'corporate-submitted-spa-v1',
            'record_id': 'fixture-record', 'source_url': LIST, 'detail_url': DETAIL,
            'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True}


def test_controlled_submitted_view_attestation_is_sealed_once_and_replayed(tmp_path):
    context, page = setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        response = exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) == expected(capture)
        result = capture.drain()
        assert result['complete'] and result['component_lifetime'] == expected(capture)
        assert response.reads == 1 and 'component_lifetime' not in result['responses'][0]
        packets = list(capture.iter_bodies())
        assert packets[0]['context']['component_lifetime'] == result['component_lifetime']
        record['detail_url'] = DETAIL
        page.evaluate_handle = lambda _: pytest.fail('Replay must not observe the current browser')
        assert checkpoint_bodies(tmp_path, result, record, SCOPE) == packets
        assert capture.drain() == result
    assert all(document.disposed for document in page.documents)
    assert not any(context.listeners.values()) and not any(page.listeners.values())


@pytest.mark.parametrize('defect', ['external-context', 'start-on-detail', 'no-view',
    'missing-navigation', 'unavailable-document'])
def test_unavailable_proof_does_not_upgrade_legacy_capture_or_invent_freshness(tmp_path, defect):
    context, page = setup(owned=defect != 'external-context',
                          url=DETAIL if defect == 'start-on-detail' else LIST)
    if defect == 'unavailable-document':
        page.evaluate_handle = lambda _: (_ for _ in ()).throw(RuntimeError('private-driver-text'))
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        if defect != 'no-view':
            begin(capture)
        if defect == 'missing-navigation':
            page.url = DETAIL
        else:
            navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) is None
        result = capture.drain()
        assert result['complete'] and 'component_lifetime' not in result
        assert 'component_lifetime' not in list(capture.iter_bodies())[0]['context']
    assert all(b'private-driver-text' not in file.read_bytes() for file in tmp_path.rglob('*.json'))


@pytest.mark.parametrize('defect', ['detour-before-bind', 'detour-after-bind',
    'same-url-new-document', 'replacement-request'])
def test_known_changed_component_lifetime_is_fatal_even_after_url_returns(tmp_path, defect):
    context, page = setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        if defect == 'detour-before-bind':
            navigate(page, DETAIL.replace('fixture-record', 'foreign-record'))
            navigate(page, DETAIL)
        exchange(context, page)
        with pytest.raises(JsonSafetyError):
            capture.bind_detail_page(page)
            observe(capture)
            if defect == 'detour-after-bind':
                navigate(page, DETAIL.replace('fixture-record', 'foreign-record'))
                navigate(page, DETAIL)
            elif defect == 'same-url-new-document':
                page.generation = object()
            elif defect == 'replacement-request':
                request = Request(page, url=ORIGIN + '/returnsheet/api/returnsheetsfinancialstatements')
                context.emit('request', request)
            capture.drain()


def test_lifetime_evaluation_cannot_hide_a_late_json_response(tmp_path):
    context, page = setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        observe(capture)
        late = []
        page.documents[0].on_read = lambda: late.append(exchange(context, page))
        result = capture.drain()
        assert not result['complete'] and 'response-after-final-drain' in result['reasons']
        assert late and all(response.reads == 0 for response in late)


@pytest.mark.parametrize('defect', ['attempt', 'source', 'detail', 'record', 'kind', 'extra',
    'count-bool', 'count-extra', 'document-false', 'source-owner-false', 'detail-owner-false'])
def test_checkpoint_lifetime_schema_or_scope_contradictions_are_fatal(tmp_path, defect):
    context, page = setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        observe(capture)
        result = capture.drain()
    record['detail_url'] = DETAIL
    path = tmp_path / result['manifest']
    saved = json.loads(path.read_bytes())
    proof = saved['component_lifetime']
    if defect == 'attempt':
        proof['attempt'] = 'f' * 32
    elif defect == 'source':
        proof['source_url'] = LIST.replace('fixture-taxpayer', 'foreign-taxpayer')
    elif defect == 'detail':
        proof['detail_url'] = DETAIL.replace('fixture-record', 'foreign-record')
    elif defect == 'kind':
        proof['kind'] = 'guessed-lifetime'
    elif defect == 'record':
        proof['record_id'] = 'foreign-record'
    elif defect == 'count-bool':
        proof['transition_count'] = True
    elif defect == 'count-extra':
        proof['transition_count'] = 2
    elif defect == 'document-false':
        proof['same_document'] = False
    elif defect == 'source-owner-false':
        proof['source_owner'] = False
    elif defect == 'detail-owner-false':
        proof['detail_owner'] = False
    else:
        proof['observed_business_value'] = 'forbidden'
    raw = json.dumps(saved).encode()
    path.write_bytes(raw)
    capture_metadata = {**saved, 'manifest': result['manifest'],
                        'manifest_sha256': hashlib.sha256(raw).hexdigest()}
    with pytest.raises(JsonSafetyError):
        checkpoint_bodies(tmp_path, capture_metadata, record, SCOPE)


def test_actual_inspected_view_tracks_same_document_spa_without_business_reads(tmp_path):
    import coretax_browser as driver
    from playwright.sync_api import sync_playwright
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context(service_workers='block')
        context._spt_financial_route_policy = 'service_workers_blocked'
        script = ('history.pushState({},"",' + json.dumps(DETAIL) + ');'
                  'document.querySelector("rshshr-submitted-returnsheets").remove();'
                  'document.body.insertAdjacentHTML("beforeend","<rshshr-corporate-income-tax-return><h1>Fixture detail</h1></rshshr-corporate-income-tax-return>");'
                  'fetch(' + json.dumps(API_URL) + ',{method:"POST"}).then(r=>r.json())'
                  '.then(()=>document.body.dataset.ready="yes")')
        html = ('<style>rshshr-submitted-returnsheets,rshshr-corporate-income-tax-return{display:block}</style>'
                '<rshshr-submitted-returnsheets><table><tbody><tr><td><button id="ViewButton" onclick=\'' +
                script + '\'>View</button></td></tr></tbody></table></rshshr-submitted-returnsheets>')
        def route(item):
            if item.request.url == LIST:
                item.fulfill(body=html, content_type='text/html')
            elif item.request.url == API_URL:
                item.fulfill(body=RAW, content_type='application/json')
            else:
                item.abort()
        context.route('**/*', route)
        page = context.new_page()
        page.goto(LIST)
        try:
            with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
                detail, popup = driver.open_return_readonly(page, page.locator('tbody tr'),
                    'fixture-taxpayer', 'fixture-record', json_capture=capture)
                detail.wait_for_function('document.body.dataset.ready === "yes"')
                assert observe(capture) == expected(capture)
                result = capture.drain()
                assert not popup and result['complete']
                assert result['component_lifetime'] == expected(capture)
        finally:
            context.close()
            browser.close()
