"""Synthetic json network helpers; no collected tests or shared mutable test state."""
import json


ORIGIN = 'https://coretax.intranet.pajak.go.id'


API_URL = ORIGIN + '/returnsheet/api/prefillfixture'


RAW = b'{ "IsSuccessful": true, "Payload": {"ReturnSheetRecordIdentifier":"fixture-record", "Amount":1.2300e+03, "Empty":null, "Enabled":false} }\n'


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
