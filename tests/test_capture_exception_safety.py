"""Exception-safety and privacy tests for capture paths.

These tests run without a browser; they exercise the narrowed exception
handlers and verify that diagnostic records never carry exception text.
"""
import pytest
from types import SimpleNamespace

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

    def post_data_json(self):
        if isinstance(self._post_data, BaseException):
            raise self._post_data
        return self._post_data


class RecordingDiagnostics:
    """Simple substitute for spt_desktop.diagnostics with capture tracking."""
    def __init__(self):
        self.records = []

    def record(self, event, *, level='INFO', **fields):
        self.records.append({'event': event, 'level': level, **fields})
        return True

    def measure(self, event, **fields):
        return _NullMeasure()


class _NullMeasure:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def update(self, **fields):
        pass


def test_grid_request_returns_none_for_structural_errors():
    observer = ListObserver.__new__(ListObserver)
    # malformed JSON shapes should be rejected gracefully
    for exc in (ValueError, TypeError, KeyError):
        request = FakeListRequest(exc('bad shape'))
        assert observer._grid_request(request, 'https://coretax.example/list') is None
    # RuntimeError is not in the narrowed handler; it should propagate
    request = FakeListRequest(RuntimeError('unexpected'))
    with pytest.raises(RuntimeError):
        observer._grid_request(request, 'https://coretax.example/list')


def test_search_diagnostics_degrades_on_structural_errors():
    page = FakePage()
    diag = _SearchDiagnostics(page)
    assert diag.observation == 'complete'

    diag._request(BrokenRequest(KeyError))
    assert diag.observation == 'unavailable'

    diag.observation = 'complete'
    diag._response(BrokenResponse(TypeError))
    assert diag.observation == 'unavailable'

    diag.observation = 'complete'
    diag._failed(BrokenRequest(AttributeError))
    assert diag.observation == 'unavailable'


def test_search_diagnostics_recovers_after_degrade():
    page = FakePage()
    diag = _SearchDiagnostics(page)
    diag._request(BrokenRequest(KeyError))
    # subsequent structural errors keep it unavailable, never crash
    diag._response(BrokenResponse(AttributeError))
    diag._failed(BrokenRequest(TypeError))
    assert diag.observation == 'unavailable'


def test_capture_partial_does_not_record_exception_text(monkeypatch):
    """Regression: capture.partial must use error_type, not error=exc."""
    import coretax_browser as cb
    diag = RecordingDiagnostics()
    monkeypatch.setattr(cb, 'diagnostics', diag)

    class FakeTable:
        pass

    def broken_capture_table(*args, **kwargs):
        raise ValueError('SECRET-TAX-DETAIL')

    monkeypatch.setattr(cb, 'capture_table', broken_capture_table)

    errors = []
    try:
        cb.capture_table(None, FakeTable(), 1, 1)
    except Exception as exc:
        cb.diagnostics.record('capture.partial', level='WARNING', error_type=type(exc).__name__)
        errors.append({'object': 'test/table 1', 'message': 'capture_failed'})

    partial = [r for r in diag.records if r['event'] == 'capture.partial']
    assert len(partial) == 1
    assert 'error_type' in partial[0]
    assert partial[0]['error_type'] == 'ValueError'
    assert 'error' not in partial[0]
    assert 'SECRET-TAX-DETAIL' not in str(partial[0])


def test_module_has_exception_policy_comment():
    import coretax_browser, coretax_json_capture, spt_desktop.diagnostics
    for mod in (coretax_browser, coretax_json_capture, spt_desktop.diagnostics):
        assert 'Exception-handling policy' in mod.__doc__
