"""Portable orchestration checks model Playwright's lazy locators; browser tests
exercise the same document changes with real DOMs on Windows.
"""
from types import SimpleNamespace

import pytest

from spt_desktop import auth
from spt_desktop.credentials import Login


ORIGIN = 'https://satu.intranet.pajak.go.id'


def test_owned_download_context_blocks_service_worker_route_bypass(monkeypatch, tmp_path):
    launches = []
    page = SimpleNamespace(goto=lambda *args, **kwargs: None)
    context = SimpleNamespace(pages=[page], close=lambda: None)
    def launch(profile, **options):
        launches.append(options)
        return context
    engine = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))
    monkeypatch.setattr(auth, 'authenticated', lambda current: current is page)
    actual, selected = auth.authenticate_owned(engine, tmp_path / 'owned-profile', 'msedge', True,
        lambda *args: None, lambda: None)
    assert actual is context and selected is page
    assert len(launches) == 1 and launches[0].get('service_workers') == 'block'
    assert getattr(context, '_spt_financial_route_policy', None) == 'service_workers_blocked'


@pytest.mark.parametrize('browser', ['msedge', 'chrome'])
@pytest.mark.parametrize('headless', [False, True])
def test_owned_download_context_binds_native_display_environment(monkeypatch, tmp_path, browser, headless):
    launches = []
    page = SimpleNamespace(goto=lambda *args, **kwargs: None)
    context = SimpleNamespace(pages=[page], close=lambda: None)
    def launch(profile, **options):
        launches.append(options)
        return context
    engine = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))
    monkeypatch.setattr(auth, 'authenticated', lambda current: current is page)
    actual, selected = auth.authenticate_owned(engine, tmp_path / 'owned-profile', browser, headless,
        lambda *args: None, lambda: None)
    assert actual is context and selected is page
    options, = launches
    assert options.get('locale') == 'id-ID'
    assert options.get('timezone_id') == 'Asia/Jakarta'
    assert options['channel'] == browser and options['headless'] is headless
    assert options['service_workers'] == 'block'


@pytest.mark.parametrize('browser', ['msedge', 'chrome'])
def test_cli_owned_download_binds_same_native_display_environment(monkeypatch, tmp_path, browser):
    from contextlib import nullcontext
    import coretax

    class StopBeforeCapture(BaseException):
        pass
    launches, closed = [], []
    page = SimpleNamespace(set_viewport_size=lambda *args: None, is_closed=lambda: False,
                           close=lambda: closed.append('page'))
    context = SimpleNamespace(new_page=lambda: page, close=lambda: closed.append('context'))
    def launch(profile, **options):
        launches.append(options)
        return context
    engine = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=launch))
    monkeypatch.setattr(coretax, 'sync_playwright', lambda: nullcontext(engine))
    def stop(current, noninteractive):
        assert current is page and noninteractive is True
        raise StopBeforeCapture()
    monkeypatch.setattr(coretax, 'authenticate', stop)
    with pytest.raises(StopBeforeCapture):
        coretax._main(['--npwp', '0000000000000001', '--year', '2025', '--browser', browser,
            '--profile', str(tmp_path / 'owned-profile'), '--output', str(tmp_path / 'output'),
            '--non-interactive', '--detail-source', 'json-first'])
    options, = launches
    assert options.get('locale') == 'id-ID'
    assert options.get('timezone_id') == 'Asia/Jakarta'
    assert options['channel'] == browser and options['service_workers'] == 'block'
    assert closed == ['page', 'context']


class Form:
    def __init__(self, page):
        self.page = page
        self.action = ORIGIN + '/session'

    def evaluate(self, expression, button):
        return self.page.form is self and button.form is self


class Element:
    def __init__(self, page, form, name):
        self.page, self.form, self.name = page, form, name

    def evaluate_handle(self, expression):
        return self.form

    def evaluate(self, expression, other=None):
        if other is not None:
            return self.form is self.page.form and self is other
        return {'action': self.form.action, 'method': 'post'}

    def fill(self, value, **kwargs):
        self.page.actions.append(self.name)
        if self.name == self.page.mutate_on_fill:
            self.form.action = ORIGIN + '/authentication'

    def click(self, **kwargs):
        self.page.actions.append('submit')


class Locator:
    def __init__(self, page, name):
        self.page, self.name = page, name

    def element_handle(self):
        return self.page.elements[self.name]

    def fill(self, *args, **kwargs):
        self.element_handle().fill(*args, **kwargs)

    def click(self, **kwargs):
        self.element_handle().click(**kwargs)


def new_document(page):
    page.form = Form(page)
    page.elements = {name: Element(page, page.form, name) for name in ('identifier', 'password', 'button')}


@pytest.fixture
def login_page(monkeypatch):
    page = SimpleNamespace(url=ORIGIN + '/login', actions=[], mutate_on_fill=None)
    new_document(page)
    monkeypatch.setattr(auth, '_login_fields', lambda current: (
        auth._origin(current.url), *(Locator(current, name) for name in ('identifier', 'password', 'button'))))
    return page


@pytest.mark.parametrize('change', ['origin', 'form', 'action'])
def test_credential_read_cannot_rebind_the_inspected_document(login_page, monkeypatch, change):
    page = login_page

    def read(origin):
        assert origin == ORIGIN
        if change == 'origin':
            page.url = 'https://evil.invalid/login'
            new_document(page)
        elif change == 'form':
            new_document(page)
        else:
            page.form.action = ORIGIN + '/authentication'
        return Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY')

    monkeypatch.setattr(auth, 'read_login', read)
    assert not auth.try_saved_login(page, lambda: None)
    assert page.actions == []


@pytest.mark.parametrize('changed_by', ['identifier', 'password'])
def test_filling_a_field_cannot_change_the_next_inspected_action(login_page, monkeypatch, changed_by):
    page = login_page
    page.mutate_on_fill = changed_by
    monkeypatch.setattr(auth, 'read_login', lambda origin: Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'))
    assert not auth.try_saved_login(page, lambda: None)
    assert page.actions == (['identifier'] if changed_by == 'identifier' else ['identifier', 'password'])


def test_unchanged_inspected_login_can_submit_once(login_page, monkeypatch):
    monkeypatch.setattr(auth, 'read_login', lambda origin: Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'))
    assert auth.try_saved_login(login_page, lambda: None)
    assert login_page.actions == ['identifier', 'password', 'submit']


def test_initial_inspection_cannot_use_another_approved_origins_credential(login_page, monkeypatch, tmp_path):
    page = login_page
    other_origin = next(origin for origin in auth.ALLOWED_ORIGINS if origin != ORIGIN)
    inspected = auth._login_fields
    moved = False
    reads = []
    closed = []

    def inspect_after_origin_moves(current):
        nonlocal moved
        if not moved:
            moved = True
            current.url = other_origin + '/login'
            new_document(current)
            current.form.action = other_origin + '/session'
        return inspected(current)

    page.goto = lambda *args, **kwargs: None
    context = SimpleNamespace(pages=[page], route=lambda *args: None,
                              close=lambda: closed.append(True))
    engine = SimpleNamespace(chromium=SimpleNamespace(
        launch_persistent_context=lambda *args, **kwargs: context))
    monkeypatch.setattr(auth, '_login_fields', inspect_after_origin_moves)
    monkeypatch.setattr(auth, 'authenticated', lambda current: False)
    monkeypatch.setattr(auth, '_at_home', lambda current: False)
    monkeypatch.setattr(auth, '_has_challenge', lambda current: False)
    monkeypatch.setattr(auth, 'read_login', lambda origin: (
        reads.append(origin) or Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY')))
    with pytest.raises(auth.AuthBlocked):
        auth.authenticate_owned(engine, tmp_path / 'profile', 'msedge', False,
            lambda *args: None, lambda: None, manual_timeout=0, account='SYNTHETIC_ACCOUNT')
    assert moved and auth._origin(page.url) == other_origin
    assert reads == [] and page.actions == []
    assert closed == [True]
