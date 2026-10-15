"""Synthetic owned-detail capture contracts; execution is runner-only.

Protocol doubles isolate event ordering, budgets and failure injection. Native
Edge fixtures below verify initial prefill ownership against real Playwright.
"""
import gc
import hashlib
import importlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import sys
import weakref

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ORIGIN = 'https://coretax.intranet.pajak.go.id'
TAXPAYER = 'fixture-taxpayer'
RECORD = 'fixture-record'
LIST_URL = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER
DETAIL_URL = ORIGIN + '/returnsheets/id-ID/fixture-return/' + TAXPAYER + '/' + RECORD
API_URL = ORIGIN + '/returnsheet/api/prefillfixture'
SCOPE = ['0000000000000001', 2024, 'period']
RAW = b'{ "IsSuccessful": true, "Payload": {"ReturnSheetRecordIdentifier":"fixture-record", "Amount":1.2300e+03, "Empty":null, "Enabled":false} }\n'


def capture_module():
    # Missing feature must fail in the test body, not during collection/setup.
    assert importlib.util.find_spec('coretax_json_capture') is not None, 'Owned detail JSON capture is not implemented'
    module = importlib.import_module('coretax_json_capture')
    assert callable(getattr(module, 'DetailJsonCapture', None)), 'Public DetailJsonCapture contract is missing'
    return module


def record():
    return {'key': 'fixture-key', 'record_id': RECORD, 'list_url': LIST_URL,
            'list_page': 1, 'row_position': 0, 'source_status': 'SPT Dilaporkan',
            'meta': {'Jenis Pajak': 'Fixture', 'Masa Pajak': 'Januari 2024', 'Model SPT': 'Normal'}}


class Signals:
    def __init__(self):
        self.listeners = {}

    def on(self, event, callback):
        self.listeners.setdefault(event, []).append(callback)

    def remove_listener(self, event, callback):
        self.listeners[event].remove(callback)

    def emit(self, event, value):
        for callback in list(self.listeners.get(event, [])):
            callback(value)


class Context(Signals):
    def __init__(self):
        super().__init__()
        self.pages = []
        self.ticks = 0
        self.on_pump = None


class Frame:
    def __init__(self, page, *, parent=None):
        self.page = page
        self.parent_frame = parent

    @property
    def url(self):
        return self.page.url


class Page(Signals):
    def __init__(self, context, url=LIST_URL, *, opener=None):
        super().__init__()
        self.context = context
        self.url = url
        self.main_frame = Frame(self)
        self.frames = [self.main_frame]
        self._opener = opener
        self._closed = False
        context.pages.append(self)

    def opener(self):
        return self._opener

    def is_closed(self):
        return self._closed

    def wait_for_timeout(self, milliseconds):
        self.context.ticks += milliseconds / 1000
        callback, self.context.on_pump = self.context.on_pump, None
        if callback:
            callback()


class Request:
    def __init__(self, page, *, url=API_URL, frame=None, method='POST', post=None):
        self.url = url
        self.frame = frame or page.main_frame
        self.method = method
        self.resource_type = 'xhr'
        self.post_data = json.dumps(post) if post is not None else None
        self.post_data_json = post
        self.finished = False
        self._response = None
        self.failure = None
        self.redirected_from = None

    def response(self):
        return self._response

    @property
    def headers(self):
        raise AssertionError('Capture must never retrieve complete request headers')


class Response:
    def __init__(self, request, raw=RAW, *, status=200, content_type='application/json', declared=None):
        self.request = request
        self.url = request.url
        self.status = status
        self.raw = raw
        self.reads = 0
        self.content_type = content_type
        self.declared = str(len(raw)) if declared is None else declared
        self.on_read = None
        request._response = self

    def header_value(self, name):
        return {'content-type': self.content_type, 'content-length': self.declared}.get(name.lower())

    @property
    def headers(self):
        raise AssertionError('Capture must never retrieve complete response headers')

    def body(self):
        assert self.request.finished, 'Body read before requestfinished may block indefinitely'
        self.reads += 1
        if self.on_read:
            self.on_read()
        return self.raw


def exchange(context, page, *, raw=RAW, finish=True, url=API_URL, frame=None, status=200,
             content_type='application/json', declared=None, post=None):
    request = Request(page, url=url, frame=frame, post=post)
    response = Response(request, raw, status=status, content_type=content_type, declared=declared)
    context.emit('request', request)
    context.emit('response', response)
    if finish:
        request.finished = True
        context.emit('requestfinished', request)
    return response


def new_capture(module, context, page, folder, **kwargs):
    return module.DetailJsonCapture(context, page, record(), list(SCOPE), folder, ordinal=7, **kwargs)


def clock(module, context, monkeypatch):
    # Inject only time, not the production ownership/serialization decisions.
    monkeypatch.setattr(module.time, 'monotonic', lambda: context.ticks)


def stored(folder, result):
    manifest = Path(result['manifest'])
    assert not manifest.is_absolute() and '..' not in manifest.parts
    assert manifest.parts[:3] == ('returns', 'json', '0007')
    assert TAXPAYER not in str(manifest) and RECORD not in str(manifest)
    assert manifest.name == 'manifest.json'
    return json.loads((folder / manifest).read_text(encoding='utf-8'))


def test_completed_body_is_read_only_during_drain_and_saved_byte_for_byte(tmp_path):
    module = capture_module()
    context, page = Context(), None
    page = Page(context)
    with new_capture(module, context, page, tmp_path) as capture:
        page.url = DETAIL_URL
        response = exchange(context, page)
        assert response.reads == 0
        capture.bind_detail_page(page)
        result = capture.drain()
        assert response.reads == 1
        assert result['complete'] is True
        assert result['counts']['accepted'] == 1
        assert result['limits'] == {'responses': 1024, 'body_bytes': 33554432,
                                    'attempt_bytes': 134217728, 'drain_seconds': 20}
        saved = stored(tmp_path, result)
        descriptor = saved['responses'][0]
        assert (tmp_path / descriptor['relative_path']).read_bytes() == RAW
        assert descriptor['bytes'] == len(RAW)
        assert descriptor['sha256'] == hashlib.sha256(RAW).hexdigest()
        assert descriptor['url'] == API_URL and descriptor['method'] == 'POST'
        assert descriptor['status'] == 200 and descriptor['frame_url'] == DETAIL_URL
        assert descriptor['identity_validated'] is False, 'Navigation attribution is not payload identity proof'
        assert saved['record_id'] == RECORD and saved['scope'] == SCOPE
    assert not any(context.listeners.values()) and not any(page.listeners.values())


def test_headers_received_but_pending_body_is_not_read_or_certified_complete(tmp_path, monkeypatch):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    clock(module, context, monkeypatch)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page, finish=False)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert response.reads == 0 and not result['responses']
        assert result['complete'] is False and result['counts']['pending'] == 1
        assert 'response-pending' in result['reasons']
        assert 20 <= context.ticks <= 20.5


def test_pending_completion_during_event_pump_is_captured(tmp_path, monkeypatch):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    clock(module, context, monkeypatch)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page, finish=False)
        def finish():
            response.request.finished = True
            context.emit('requestfinished', response.request)
        context.on_pump = finish
        capture.bind_detail_page(page)
        result = capture.drain()
        assert result['complete'] is True and result['counts']['accepted'] == 1
        assert response.reads == 1


@pytest.mark.parametrize('foreign', ['tab', 'context', 'subframe', 'old-request', 'other-popup'])
def test_foreign_or_pre_epoch_requests_never_become_detail_evidence(tmp_path, foreign):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    target, frame = page, None
    if foreign == 'tab':
        target = Page(context, DETAIL_URL)
    elif foreign == 'context':
        target = Page(Context(), DETAIL_URL)
    elif foreign == 'subframe':
        frame = Frame(page, parent=page.main_frame)
    elif foreign == 'other-popup':
        target = Page(context, DETAIL_URL, opener=page)
    old = Request(page)
    old_response = Response(old)
    context.emit('request', old)
    with new_capture(module, context, page, tmp_path) as capture:
        if foreign == 'old-request':
            old.finished = True
            context.emit('response', old_response)
            context.emit('requestfinished', old)
            response = old_response
        else:
            response = exchange(context, target, frame=frame)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses'] and response.reads == 0
        assert result['counts']['accepted'] == 0


def test_old_attempt_is_not_replayed_into_new_attempt(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as first:
        delayed = exchange(context, page, finish=False)
        first.bind_detail_page(page)
    with new_capture(module, context, page, tmp_path) as second:
        delayed.request.finished = True
        context.emit('response', delayed)
        context.emit('requestfinished', delayed.request)
        second.bind_detail_page(page)
        result = second.drain()
        assert not result['responses'] and delayed.reads == 0


@pytest.mark.parametrize('url', [
    ORIGIN + '/returnsheet/api/returnsheetssubmitted',
    ORIGIN + '/identityprovider/api/token',
    API_URL + '?access_token=fixture-sensitive-marker',
    'https://untrusted.invalid/returnsheet/api/prefillfixture',
])
def test_listing_auth_and_secret_or_foreign_urls_are_excluded_without_body_read(tmp_path, url):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page, url=url)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses'] and response.reads == 0
    assert all(b'fixture-sensitive-marker' not in p.read_bytes() for p in tmp_path.rglob('*') if p.is_file())


@pytest.mark.parametrize('value', [
    {'Password': 'fixture-sensitive-marker'},
    {'nested': [{'authorization': 'fixture-sensitive-marker'}]},
    {'Payload': {'CurrentFormData': json.dumps({'refresh_token': 'fixture-sensitive-marker'})}},
    {'Payload': {'CurrentFormData': json.dumps(json.dumps({'ApiKey': 'fixture-sensitive-marker'}))}},
    {'Payload': {'Memo': 'Bearer fixture-sensitive-marker'}},
])
def test_secret_bearing_outer_or_embedded_json_is_rejected_whole_not_redacted(tmp_path, value):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    raw = json.dumps(value).encode('utf-8')
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page, raw=raw)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses'] and 'secret-body' in result['reasons']
        assert result['complete'] is False
    files = [p for p in tmp_path.rglob('*') if p.is_file()]
    assert files and all(b'fixture-sensitive-marker' not in p.read_bytes() for p in files)
    assert not any(p.suffix == '.json' and p.name != 'manifest.json' for p in files)


def test_sensitive_request_body_is_not_persisted_as_context(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page, post={'Password': 'fixture-sensitive-marker'})
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses']
    assert all(b'fixture-sensitive-marker' not in p.read_bytes() for p in tmp_path.rglob('*') if p.is_file())


@pytest.mark.parametrize('declared', [str(32 * 1024 * 1024 + 1), '-1', 'invalid'])
def test_declared_length_rejected_before_body_read(tmp_path, declared):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page, declared=declared)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert response.reads == 0 and not result['responses']
        assert result['complete'] is False and 'body-size-limit' in result['reasons']


def test_actual_oversized_body_cannot_evade_small_declared_length(tmp_path, monkeypatch):
    module = capture_module()
    monkeypatch.setattr(module, 'MAX_BODY_BYTES', 64)
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page, raw=b'{"Data":"' + b'x' * 65 + b'"}', declared='1')
        capture.bind_detail_page(page)
        result = capture.drain()
        assert response.reads == 1 and not result['responses']
        assert result['complete'] is False and 'body-size-limit' in result['reasons']


def test_attempt_budget_does_not_persist_over_budget_body(tmp_path, monkeypatch):
    module = capture_module()
    monkeypatch.setattr(module, 'MAX_TOTAL_BYTES', 50)
    context = Context()
    page = Page(context, DETAIL_URL)
    raw = b'{"Data":"' + b'x' * 20 + b'"}'
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page, raw=raw)
        exchange(context, page, raw=raw)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert len(result['responses']) == 1
        assert result['complete'] is False and 'attempt-byte-limit' in result['reasons']
        assert sum(d['bytes'] for d in result['responses']) <= 50


def test_more_than_1024_owned_responses_cannot_be_certified_complete(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        for _ in range(1025):
            exchange(context, page, raw=b'{}')
        capture.bind_detail_page(page)
        result = capture.drain()
        assert len(result['responses']) <= 1024
        assert result['complete'] is False and 'response-limit' in result['reasons']


def test_failed_request_is_partial_and_exception_text_never_reaches_manifest(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        request = Request(page)
        context.emit('request', request)
        request.failure = 'fixture-sensitive-marker in browser failure'
        context.emit('requestfailed', request)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert result['complete'] is False and 'request-failed' in result['reasons']
    assert all(b'fixture-sensitive-marker' not in p.read_bytes() for p in tmp_path.rglob('*') if p.is_file())


@pytest.mark.parametrize('raw', [b'not-json', b'{"bad":NaN}', b'{"bad":Infinity}', b'\xff'])
def test_invalid_json_cannot_be_persisted_as_safe_decoder_input(tmp_path, raw):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page, raw=raw)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses'] and result['complete'] is False
        assert 'invalid-json' in result['reasons']


@pytest.mark.parametrize('content_type', ['text/html', 'application/pdf'])
def test_non_json_responses_are_not_read_into_detail_json_capture(tmp_path, content_type):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page, content_type=content_type)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses'] and response.reads == 0


def test_same_shape_listing_body_is_excluded_by_source_not_used_as_detail(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    raw = json.dumps({'IsSuccessful': True, 'Payload': {'Data': [{'RecordId': RECORD}], 'TotalRecords': 1}}).encode('utf-8')
    with new_capture(module, context, page, tmp_path) as capture:
        listing = exchange(context, page, raw=raw, url=ORIGIN + '/returnsheet/api/returnsheetssubmitted')
        detail = exchange(context, page, raw=raw)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert listing.reads == 0 and detail.reads == 1
        assert len(result['responses']) == 1 and result['responses'][0]['url'] == API_URL
        assert result['responses'][0]['identity_validated'] is False


def test_safe_ancillary_http_error_preserves_observation_not_fake_identity(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    raw = b'{"IsSuccessful":false,"ErrorCode":0,"Payload":null}'
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page, raw=raw, status=400)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert result['responses'][0]['status'] == 400
        assert result['responses'][0]['identity_validated'] is False
        assert (tmp_path / result['responses'][0]['relative_path']).read_bytes() == raw


@pytest.mark.parametrize('bad', ['url', 'context', 'opener'])
def test_unowned_or_wrong_record_detail_cannot_be_bound(tmp_path, bad):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context)
    detail = Page(context, DETAIL_URL, opener=page)
    if bad == 'url':
        detail.url = DETAIL_URL.replace(RECORD, 'foreign-record')
    elif bad == 'context':
        detail = Page(Context(), DETAIL_URL, opener=page)
    else:
        detail = Page(context, DETAIL_URL, opener=None)
    with pytest.raises(JsonSafetyError):
        with new_capture(module, context, page, tmp_path) as capture:
            capture.bind_detail_page(detail)
    assert not any(context.listeners.values()) and not any(page.listeners.values())


def test_binding_drift_before_drain_fails_closed_without_reading_body(tmp_path):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context, DETAIL_URL)
    with pytest.raises(JsonSafetyError):
        with new_capture(module, context, page, tmp_path) as capture:
            response = exchange(context, page)
            capture.bind_detail_page(page)
            page.url = DETAIL_URL.replace(RECORD, 'foreign-record')
            capture.drain()
    assert response.reads == 0 and not any(context.listeners.values())


def test_body_read_failure_is_partial_secret_free_and_cleans_up(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page)
        def fail():
            raise RuntimeError('fixture-sensitive-marker from driver')
        response.on_read = fail
        capture.bind_detail_page(page)
        result = capture.drain()
        assert not result['responses'] and result['complete'] is False
        assert 'body-read-failed' in result['reasons']
    assert not any(context.listeners.values())
    assert all(b'fixture-sensitive-marker' not in p.read_bytes() for p in tmp_path.rglob('*') if p.is_file())


def test_stop_before_enter_leaves_no_listeners_or_attempt_files(tmp_path):
    module = capture_module()
    class FixtureStop(Exception):
        pass
    def stop():
        raise FixtureStop('fixture-stop')
    context = Context()
    page = Page(context)
    with pytest.raises(FixtureStop):
        with new_capture(module, context, page, tmp_path, check_cancel=stop):
            pytest.fail('Stop must precede listener installation')
    assert not any(context.listeners.values()) and not list(tmp_path.iterdir())


def test_stop_before_drain_reads_no_body_and_detaches_listeners(tmp_path):
    module = capture_module()
    class FixtureStop(Exception):
        pass
    def stop():
        raise FixtureStop('fixture-stop')
    context = Context()
    page = Page(context, DETAIL_URL)
    with pytest.raises(FixtureStop):
        with new_capture(module, context, page, tmp_path) as capture:
            response = exchange(context, page)
            capture.bind_detail_page(page)
            capture.drain(stop)
    assert response.reads == 0 and not any(context.listeners.values())


def test_stop_after_driver_body_read_never_persists_that_body(tmp_path):
    module = capture_module()
    class FixtureStop(Exception):
        pass
    stopped = [False]
    def check():
        if stopped[0]:
            raise FixtureStop('fixture-stop')
    context = Context()
    page = Page(context, DETAIL_URL)
    with pytest.raises(FixtureStop):
        with new_capture(module, context, page, tmp_path) as capture:
            response = exchange(context, page)
            response.on_read = lambda: stopped.__setitem__(0, True)
            capture.bind_detail_page(page)
            capture.drain(check)
    assert response.reads == 1 and not any(context.listeners.values())
    assert all(p.name == 'manifest.json' for p in tmp_path.rglob('*') if p.is_file())


def test_close_is_idempotent_and_removes_only_capture_owned_listeners(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    observed = []
    external = lambda item: observed.append(item)
    context.on('response', external)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page)
        capture.bind_detail_page(page)
        capture.drain()
    capture.close()
    assert context.listeners['response'] == [external]
    assert observed == [response]
    assert all(not callbacks for event, callbacks in context.listeners.items() if event != 'response')
    assert not any(page.listeners.values())


def test_drain_without_verified_detail_binding_refuses_body_read(tmp_path):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context, DETAIL_URL)
    with pytest.raises(JsonSafetyError):
        with new_capture(module, context, page, tmp_path) as capture:
            response = exchange(context, page)
            capture.drain()
    assert response.reads == 0 and not any(context.listeners.values())


def test_completed_response_wrappers_are_released_after_drain(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        response = exchange(context, page)
        reference = weakref.ref(response)
        capture.bind_detail_page(page)
        result = capture.drain()
        del response
        gc.collect()
        assert reference() is None, 'Processed driver responses must not accumulate in capture state'
        assert result['responses'] and all('body' not in d and 'payload' not in d for d in result['responses'])


def test_iter_bodies_is_lazy_lossless_and_rejects_changed_next_file(tmp_path):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page)
        exchange(context, page, raw=b'{"IsSuccessful":true,"Payload":{"Amount":0}}')
        capture.bind_detail_page(page)
        result = capture.drain()
        second = tmp_path / result['responses'][1]['relative_path']
        second.write_bytes(b'{"foreign":"changed-after-drain"}')
        stream = capture.iter_bodies()
        assert iter(stream) is stream
        first = next(stream)
        assert first['body'] == RAW
        assert first['payload']['Payload']['ReturnSheetRecordIdentifier'] == RECORD
        assert first['context']['sha256'] == hashlib.sha256(RAW).hexdigest()
        with pytest.raises(JsonSafetyError):
            next(stream)


def test_stop_during_lazy_iteration_does_not_read_next_body(tmp_path):
    module = capture_module()
    class FixtureStop(Exception):
        pass
    context = Context()
    page = Page(context, DETAIL_URL)
    with new_capture(module, context, page, tmp_path) as capture:
        exchange(context, page)
        capture.bind_detail_page(page)
        result = capture.drain()
        stopped = [False]
        def check():
            if stopped[0]:
                raise FixtureStop('fixture-stop')
        stream = capture.iter_bodies(check)
        stopped[0] = True
        (tmp_path / result['responses'][0]['relative_path']).write_bytes(b'changed')
        with pytest.raises(FixtureStop):
            next(stream)


def test_attempt_paths_never_overwrite_previous_evidence(tmp_path):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    manifests = []
    for raw in (RAW, b'{"Payload":{"Amount":0}}'):
        with new_capture(module, context, page, tmp_path) as capture:
            exchange(context, page, raw=raw)
            capture.bind_detail_page(page)
            result = capture.drain()
            manifests.append(result['manifest'])
    assert manifests[0] != manifests[1]
    saved = [stored(tmp_path, {'manifest': p}) for p in manifests]
    assert [len(item['responses']) for item in saved] == [1, 1]
    assert [(tmp_path / item['responses'][0]['relative_path']).read_bytes() for item in saved] == [RAW, b'{"Payload":{"Amount":0}}']


@pytest.mark.parametrize('ordinal', [1, 7, 23])
def test_numeric_ordinal_controls_only_private_namespace(tmp_path, ordinal):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    with module.DetailJsonCapture(context, page, record(), list(SCOPE), tmp_path, ordinal=ordinal) as capture:
        exchange(context, page)
        capture.bind_detail_page(page)
        result = capture.drain()
        manifest = Path(result['manifest'])
        assert manifest.parts[:3] == ('returns', 'json', f'{ordinal:04d}')
        assert RECORD not in str(manifest) and TAXPAYER not in str(manifest)
        saved = json.loads((tmp_path / manifest).read_text(encoding='utf-8'))
        assert (tmp_path / saved['responses'][0]['relative_path']).read_bytes() == RAW


@pytest.mark.parametrize('ordinal', [0, -1, True, '../escape', '0000000000000001'])
def test_invalid_ordinal_is_not_normalized_into_a_private_path(tmp_path, ordinal):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context)
    with pytest.raises(JsonSafetyError):
        with module.DetailJsonCapture(context, page, record(), list(SCOPE), tmp_path, ordinal=ordinal):
            pytest.fail('Invalid ordinal must fail before listener installation or writes')
    assert not any(context.listeners.values()) and not list(tmp_path.iterdir())


@pytest.mark.parametrize('scope', [
    ['0000000000000001', 2024, 'period'],
    ['0000000000000002', 2024, 'submission'],
])
def test_valid_scope_values_are_preserved_in_private_manifest(tmp_path, scope):
    module = capture_module()
    context = Context()
    page = Page(context, DETAIL_URL)
    item = record()
    item['meta']['Tanggal Submit SPT'] = '01-01-2024'
    with module.DetailJsonCapture(context, page, item, scope, tmp_path, ordinal=7) as capture:
        exchange(context, page)
        capture.bind_detail_page(page)
        result = capture.drain()
        assert stored(tmp_path, result)['scope'] == scope
        assert result['record_id'] == RECORD


@pytest.mark.parametrize('scope', [None, ['0000000000000001', 2024],
                                   ['1', 2024, 'period'],
                                   ['0000000000000001', True, 'period'],
                                   ['0000000000000001', 2024, 'posted']])
def test_invalid_scope_is_not_repaired_or_persisted(tmp_path, scope):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context)
    with pytest.raises(JsonSafetyError):
        with module.DetailJsonCapture(context, page, record(), scope, tmp_path, ordinal=7):
            pytest.fail('Invalid scope must not be normalized or registered')
    assert not any(context.listeners.values()) and not list(tmp_path.iterdir())


def test_folder_traversal_is_rejected_before_capture(tmp_path):
    module = capture_module()
    from coretax_json import JsonSafetyError
    context = Context()
    page = Page(context)
    folder = tmp_path / 'nested' / '..' / 'escape'
    with pytest.raises(JsonSafetyError):
        with new_capture(module, context, page, folder):
            pytest.fail('Traversal must not be normalized away')
    assert not any(context.listeners.values())


def test_native_junction_cannot_redirect_private_capture(tmp_path):
    module = capture_module()
    from coretax_json import JsonSafetyError
    outside = tmp_path / 'outside'
    outside.mkdir()
    job = tmp_path / 'job'
    job.mkdir()
    target = job / 'returns'
    result = subprocess.run(['cmd', '/c', 'mklink', '/J', str(target), str(outside)], capture_output=True, text=True)
    assert result.returncode == 0, 'Windows runner must create the controlled junction fixture'
    context = Context()
    page = Page(context)
    with pytest.raises(JsonSafetyError):
        with new_capture(module, context, page, job):
            pytest.fail('Capture must reject a linked private ancestor')
    assert not list(outside.iterdir()) and not any(context.listeners.values())


@pytest.mark.parametrize('popup', [False, True])
def test_real_initial_prefill_before_view_returns_is_bound_and_list_observer_unpolluted(tmp_path, popup):
    module = capture_module()
    import coretax_browser as driver
    from playwright.sync_api import sync_playwright
    assert 'json_capture' in inspect.signature(driver.open_return_readonly).parameters
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        context = browser.new_context()
        html = '<script>fetch("' + API_URL + '",{method:"POST"}).then(r=>r.json()).then(()=>document.body.dataset.ready="yes");</script><h1>Fixture detail</h1>'
        action = 'window.open("' + DETAIL_URL + '")' if popup else 'location.href="' + DETAIL_URL + '"'
        listing = '<table><tbody><tr><td><button id="ViewButton" onclick=\'' + action + '\'>View</button></td></tr></tbody></table>'
        def route(request_route):
            url = request_route.request.url
            if url == LIST_URL:
                request_route.fulfill(body=listing, content_type='text/html')
            elif url == DETAIL_URL:
                request_route.fulfill(body=html, content_type='text/html')
            elif url == API_URL:
                request_route.fulfill(body=RAW, content_type='application/json')
            else:
                request_route.abort()
        context.route('**/*', route)
        page = context.new_page()
        page.goto(LIST_URL)
        observer = driver.ListObserver(page)
        try:
            with new_capture(module, context, page, tmp_path) as capture:
                row = page.locator('tbody tr').first
                detail, is_popup = driver.open_return_readonly(page, row, TAXPAYER, RECORD, json_capture=capture)
                detail.wait_for_function('document.body.dataset.ready === "yes"')
                result = capture.drain()
                assert result['complete'] is True and result['counts']['accepted'] == 1
                assert observer.sequence == 0 and observer.latest is None
                assert is_popup is popup
                saved = stored(tmp_path, result)
                assert (tmp_path / saved['responses'][0]['relative_path']).read_bytes() == RAW
                assert saved['detail_url'] == DETAIL_URL
        finally:
            observer.close()
            context.close()
            browser.close()
