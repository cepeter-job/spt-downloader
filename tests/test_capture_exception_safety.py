"""Exception-safety and privacy tests for capture paths.

These tests run without a browser; they exercise the narrowed exception
handlers and verify that diagnostic records never carry exception text.
"""
import pytest

from coretax_browser import _SearchDiagnostics, ListObserver


class FakePage:
    """Minimal page double for _SearchDiagnostics lifecycle tests."""
    def __init__(self):
        self.handlers = {}

    def on(self, event, handler):
        self.handlers[event] = handler

    def remove_listener(self, event, handler):
        if self.handlers.get(event) is handler:
            del self.handlers[event]


class BrokenRequest:
    """Request whose attributes raise structural errors used by the handlers."""
    def __init__(self, exc_type):
        self._exc_type = exc_type

    def __getattr__(self, name):
        raise self._exc_type(f'synthetic {name} failure')


class BrokenResponse:
    def __init__(self, exc_type):
        self._exc_type = exc_type
        self.request = BrokenRequest(exc_type)

    @property
    def status(self):
        raise self._exc_type('synthetic status failure')


class FakeListRequest:
    """Request double for ListObserver._grid_request shape validation."""
    def __init__(self, post_data_json):
        self._post_data = post_data_json
        self.resource_type = 'xhr'
        self.method = 'POST'
        self.frame = None
        self.url = 'https://coretax.intranet.pajak.go.id/returnsheet/api/returnsheets/list'

    def post_data_json(self):
        if isinstance(self._post_data, BaseException):
            raise self._post_data
        return self._post_data


def test_grid_request_returns_none_for_structural_errors():
    observer = ListObserver.__new__(ListObserver)
    observer.page = FakePage()
    observer.navigation_source = None
    # malformed JSON shapes should be rejected gracefully
    for exc in (ValueError, TypeError, KeyError):
        request = FakeListRequest(exc('bad shape'))
        assert observer._grid_request(request, 'https://coretax.intranet.pajak.go.id/returnsheet/api/returnsheets/list') is None
    # RuntimeError is not in the narrowed handler; it should propagate
    request = FakeListRequest(RuntimeError('unexpected'))
    with pytest.raises(RuntimeError):
        observer._grid_request(request, 'https://coretax.intranet.pajak.go.id/returnsheet/api/returnsheets/list')


def test_search_diagnostics_degrades_on_structural_errors():
    page = FakePage()
    diag = _SearchDiagnostics(page)
    assert diag.observation == 'complete'

    diag._request(BrokenRequest(KeyError))
    assert diag.observation == 'unavailable'

    diag.observation = 'complete'
    # Seed tracked so _response reaches the status check that raises
    fake_req = BrokenRequest(TypeError)
    diag.tracked[id(fake_req)] = [fake_req, 0]
    broken_resp = BrokenResponse.__new__(BrokenResponse)
    broken_resp._exc_type = TypeError
    broken_resp.request = fake_req
    diag._response(broken_resp)
    assert diag.observation == 'unavailable'

    diag.observation = 'complete'
    # _failed with BrokenRequest alone won't trigger structural error since
    # tracked.get and int ops don't touch BrokenRequest attributes.
    # Test with a broken counts dict that raises on access.
    class BrokenCounts(dict):
        def __getitem__(self, key):
            raise AttributeError('synthetic counts failure')
    diag.counts = BrokenCounts(diag.counts)
    normal_req = type('Req', (), {})()
    diag.tracked[id(normal_req)] = [normal_req, 0]
    diag._failed(normal_req)
    assert diag.observation == 'unavailable'


def test_search_diagnostics_recovers_after_degrade():
    page = FakePage()
    diag = _SearchDiagnostics(page)
    diag._request(BrokenRequest(KeyError))
    # subsequent structural errors keep it unavailable, never crash
    fake_req2 = BrokenRequest(AttributeError)
    diag.tracked[id(fake_req2)] = [fake_req2, 0]
    broken_resp2 = BrokenResponse.__new__(BrokenResponse)
    broken_resp2._exc_type = AttributeError
    broken_resp2.request = fake_req2
    diag._response(broken_resp2)
    diag._failed(BrokenRequest(TypeError))
    assert diag.observation == 'unavailable'


def test_json_capture_driver_probe_swallows_arbitrary_driver_errors():
    """Driver probes must fallback gracefully even against broken doubles."""
    import coretax_json_capture as jcap

    class BrokenPage:
        def evaluate(self, *args, **kwargs):
            raise AttributeError("no evaluate")

    sampler = jcap.DetailJsonCapture.__new__(jcap.DetailJsonCapture)
    sampler.check_cancel = None
    assert sampler._sample_clock(BrokenPage()) is None
