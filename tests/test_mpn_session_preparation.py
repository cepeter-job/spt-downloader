"""Value-free session preparation; every route and callback is synthetic."""
from types import SimpleNamespace

import pytest

from coretax_mpn import MpnSafetyError, MpnUnsupported, ORIGIN
from test_mpn import scope_run
from test_mpn_browser import SOURCE


class PreparingPage:
    def __init__(self, routes, *, ready=True, final_read=None):
        self.url = 'about:blank'
        self.main_frame = SimpleNamespace(url=self.url)
        self.context = SimpleNamespace(_spt_financial_route_policy='service_workers_blocked')
        self.handlers = {}
        self.routes, self.ready, self.final_read = routes, ready, final_read
        self.navigations = []
        self.clock = 0

    def on(self, event, callback):
        self.handlers.setdefault(event, []).append(callback)

    def remove_listener(self, event, callback):
        self.handlers[event].remove(callback)

    def navigate(self, url):
        self.url = self.main_frame.url = url
        for callback in list(self.handlers.get('framenavigated', [])):
            callback(self.main_frame)

    def goto(self, url, **kwargs):
        assert url == SOURCE and kwargs['timeout'] <= 60000
        self.navigations.append(url)
        for route in self.routes:
            self.navigate(route)

    def locator(self, selector):
        assert selector == 'acc-balance-sheet-light'
        page = self
        class Owner:
            def count(self):
                return int(page.ready)
            def is_visible(self):
                if page.final_read:
                    callback, page.final_read = page.final_read, None
                    callback(page)
                return True
        return Owner()

    def wait_for_timeout(self, milliseconds):
        self.clock += milliseconds / 1000


def prepare(page, monkeypatch, *, stop=None):
    import coretax_mpn_ui as module
    monkeypatch.setattr(module.time, 'monotonic', lambda: page.clock)
    return module.prepare_accounting_session(page, scope_run(), check_cancel=stop)


def assert_clean(page):
    assert all(not listeners for listeners in page.handlers.values())
    assert page.navigations == [SOURCE]


def test_full_observed_session_sequence_finishes_before_observer_construction(monkeypatch, tmp_path):
    import coretax_mpn_browser as browser
    import coretax_mpn_ui as module
    page = PreparingPage([SOURCE, ORIGIN + '/accounting/id-ID/',
        ORIGIN + '/accounting/id-ID/auth-callback?code=SYNTHETIC', ORIGIN + '/', SOURCE])
    monkeypatch.setattr(module.time, 'monotonic', lambda: page.clock)
    created = []
    def capture(*args, **kwargs):
        assert_clean(page)
        created.append(True)
        return 'SYNTHETIC-CAPTURE'
    monkeypatch.setattr(module, 'AccountingUI', capture)
    assert browser.AccountingUI(page, scope_run(), tmp_path) == 'SYNTHETIC-CAPTURE'
    assert created == [True]


@pytest.mark.parametrize('bad', [
    ORIGIN + '/accounting/id-ID/balancesheet/00000000-0000-4000-8000-000000000099',
    SOURCE + '?extra=1', SOURCE + '#fragment',
    ORIGIN + '/?extra=1', ORIGIN + '/#fragment',
    ORIGIN + '/accounting/id-ID/?extra=1', ORIGIN + '/accounting/id-ID/#fragment',
    ORIGIN + '/accounting/id-ID', ORIGIN + '/accounting/id-ID/auth-callback/',
    ORIGIN + '/accounting/id-ID/%61uth-callback',
    ORIGIN + '/accounting/id-ID/auth-callback#fragment',
    ORIGIN + ':443/accounting/id-ID/auth-callback',
    'https://synthetic.invalid/accounting/id-ID/auth-callback',
    ORIGIN + '/accounting/id-ID/unknown',
])
def test_forbidden_session_route_stays_fatal_after_return_to_selected_ledger(monkeypatch, tmp_path, bad):
    import coretax_mpn_browser as browser
    import coretax_mpn_ui as module
    page = PreparingPage([SOURCE, bad, SOURCE])
    monkeypatch.setattr(module.time, 'monotonic', lambda: page.clock)
    def forbidden(*args, **kwargs):
        raise AssertionError('Capture observer was constructed after session refusal')
    monkeypatch.setattr(module, 'AccountingUI', forbidden)
    with pytest.raises(MpnSafetyError):
        browser.AccountingUI(page, scope_run(), tmp_path)
    assert_clean(page)


@pytest.mark.parametrize('failure', ['route', 'deadline', 'stop'])
def test_final_read_cannot_authorize_after_route_deadline_or_stop(monkeypatch, failure):
    from coretax_browser import CaptureCancelled
    stopped = []
    def final(page):
        if failure == 'route':
            page.navigate(SOURCE + '?foreign=1')
        elif failure == 'deadline':
            page.clock = 100
        else:
            stopped.append(True)
    page = PreparingPage([SOURCE], final_read=final)
    def stop():
        if stopped:
            raise CaptureCancelled('Synthetic Stop')
    expected = {'route': MpnSafetyError, 'deadline': MpnUnsupported, 'stop': CaptureCancelled}[failure]
    with pytest.raises(expected):
        prepare(page, monkeypatch, stop=stop)
    assert_clean(page)


def test_missing_session_owner_has_one_finite_deadline_and_cleans_listener(monkeypatch):
    page = PreparingPage([SOURCE], ready=False)
    with pytest.raises(MpnUnsupported):
        prepare(page, monkeypatch)
    assert 0 < page.clock <= 61
    assert_clean(page)
