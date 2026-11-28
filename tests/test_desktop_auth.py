"""Browser routes synthesize every response; no intranet login occurs."""
import importlib
import importlib.util
import pytest
from playwright.sync_api import sync_playwright
from spt_desktop.credentials import Login


def auth():
    assert importlib.util.find_spec('spt_desktop.auth'), 'Safe background authentication is missing'
    return importlib.import_module('spt_desktop.auth')


@pytest.fixture(scope='module')
def browser():
    if importlib.util.find_spec('spt_desktop.auth') is None:
        yield None
        return
    with sync_playwright() as p:
        b = p.chromium.launch(channel='msedge',headless=True)
        yield b
        b.close()


def form(method='post',action='/session',extra=''):
    return f'<html><body>{extra}<form method="{method}" action="{action}"><input name="username" autocomplete="username"><input type="password" name="password"><button type="submit">Login</button></form></body></html>'


def page(browser,html,origin='https://satu.intranet.pajak.go.id'):
    p=browser.new_page()
    p.route('**/*',lambda route:route.fulfill(status=200,content_type='text/html',body=html))
    p.goto(origin+'/login')
    return p


def test_saved_login_fills_only_inspected_same_origin_post_form(browser,monkeypatch):
    module=auth()
    p=page(browser,form())
    reads=[]
    monkeypatch.setattr(module,'read_login',lambda origin:(reads.append(origin) or Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY')))
    try:
        assert module.try_saved_login(p,lambda:None)
        assert reads == ['https://satu.intranet.pajak.go.id']
    finally:p.close()


@pytest.mark.parametrize('html',[form(method='get'),form(action='https://evil.invalid/session'),
    form(extra='<input id="captcha">'),form(extra='<input autocomplete="one-time-code">'),
    form()+form(),form().replace('name="password"','name="password" autocomplete="new-password"'),
    form().replace('<button','<button formmethod=""'),
    form(action='https://satu.intranet.pajak.go.id/session',extra='<base href="https://evil.invalid/">')
        .replace('<button','<button formaction="session"')])
def test_unsafe_or_challenged_layout_never_reads_stored_password(browser,monkeypatch,html):
    module=auth()
    p=page(browser,html)
    reads=[]
    monkeypatch.setattr(module,'read_login',lambda origin:reads.append(origin))
    try:
        assert not module.try_saved_login(p,lambda:None)
        assert reads == []
        assert p.locator('input[type=password]').first.input_value() == ''
    finally:p.close()


def test_non_allowlisted_origin_never_reads_credential(browser,monkeypatch):
    module=auth()
    p=page(browser,form(),origin='https://evil.invalid')
    reads=[]
    monkeypatch.setattr(module,'read_login',lambda origin:reads.append(origin))
    try:
        assert not module.try_saved_login(p,lambda:None)
        assert not reads
    finally:p.close()


@pytest.mark.parametrize('html',[form().replace('>Login<','>Submit SPT<'),
    form(action='/returnsheets/submit'),form(extra='').replace('<button','<input name="unknown_challenge"><button')])
def test_non_login_action_or_unknown_editable_field_never_uses_credentials(browser,monkeypatch,html):
    module=auth()
    p=page(browser,html)
    reads=[]
    monkeypatch.setattr(module,'read_login',lambda origin:(reads.append(origin) or Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY')))
    try:
        assert not module.try_saved_login(p,lambda:None)
        assert reads == []
    finally:p.close()


def test_root_action_on_non_login_page_never_reads_password(browser,monkeypatch):
    module=auth()
    p=page(browser,form(action='/'))
    p.goto('https://satu.intranet.pajak.go.id/returnsheets/id-ID/unknown-form')
    reads=[]
    monkeypatch.setattr(module,'read_login',lambda origin:(reads.append(origin) or Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY')))
    try:
        assert not module.try_saved_login(p,lambda:None)
        assert not reads
    finally:p.close()


@pytest.mark.parametrize('change',['origin','form'])
def test_changed_document_during_credential_read_never_receives_saved_login(browser,monkeypatch,change):
    module=auth()
    p=page(browser,form())
    submitted=[]
    p.on('request',lambda request:submitted.append(request.post_data) if request.method=='POST' else None)
    def read(origin):
        if change=='origin':p.goto('https://evil.invalid/login')
        else:p.evaluate('(html)=>document.body.innerHTML=html',form())
        return Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY')
    monkeypatch.setattr(module,'read_login',read)
    try:
        assert not module.try_saved_login(p,lambda:None)
        assert p.locator('input[type=password]').input_value()==''
        assert p.locator('input[name=username]').input_value()==''
        assert submitted==[]
    finally:p.close()


@pytest.mark.parametrize('field,target',[('username','https://evil.invalid/session'),
    ('password','/returnsheets/submit'),('password','/authentication')])
def test_input_handler_cannot_change_the_inspected_login_submission(browser,monkeypatch,field,target):
    module=auth()
    html=form().replace(f'name="{field}"',f'name="{field}" oninput="this.form.action=\'{target}\'"')
    p=page(browser,html)
    submitted=[]
    p.on('request',lambda request:submitted.append(request.post_data) if request.method=='POST' else None)
    monkeypatch.setattr(module,'read_login',lambda origin:Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY'))
    try:
        assert not module.try_saved_login(p,lambda:None)
        assert submitted==[]
        if field=='username':assert p.locator('input[type=password]').input_value()==''
    finally:p.close()



class _FakePage:
    """A page that is never authenticated, so the flow reaches manual login."""

    def __init__(self, headless):
        self.headless = headless
        self.url = auth().SEARCH_URL

    def goto(self, *a, **k):
        return None

    def evaluate(self, *a, **k):
        return False

    def locator(self, *a, **k):
        raise AssertionError('the fake page must not be inspected')


class _FakeContext:
    def __init__(self, headless):
        self.headless = headless
        self.closed = False
        self.pages = []

    def close(self):
        self.closed = True

    def new_page(self):
        return _FakePage(self.headless)


class _FakeChromium:
    """Headless launch fails per ``fail_headless``; visible always succeeds."""

    def __init__(self, fail_headless):
        self.headless_calls = 0
        self.fail_headless = fail_headless

    def launch_persistent_context(self, profile, channel=None, headless=True, **k):
        if headless:
            self.headless_calls += 1
            if self.fail_headless(self.headless_calls):
                raise RuntimeError('synthetic profile lock')
        return _FakeContext(headless)


def _run_auth(monkeypatch, chromium, tmp_path, emit=None):
    mod = auth()
    # The fake page carries no DOM; the flow only needs "not signed in yet".
    monkeypatch.setattr(mod, 'authenticated', lambda page: False)
    monkeypatch.setattr(mod, '_at_home', lambda page: False)
    monkeypatch.setattr(mod, 'try_saved_login', lambda *a, **k: False)
    monkeypatch.setattr(mod, '_wait_ready', lambda *a, **k: True)
    monkeypatch.setattr(mod, '_RELAUNCH_BACKOFF', 0)
    monkeypatch.setattr(mod.time, 'sleep', lambda s: None)

    class _Playwright:
        pass

    pw = _Playwright()
    pw.chromium = chromium
    return mod.authenticate_owned(pw, str(tmp_path), 'msedge', True,
                                  emit or (lambda *a: None), lambda: None, manual_timeout=1)


def test_headless_relaunch_retries_then_returns_headless(monkeypatch, tmp_path):
    """A transient profile-lock race clears on retry; no visible fallback.

    Headless call 1 is the initial launch; calls 2 and 3 are the first two
    relaunch attempts, which fail, and the third succeeds.
    """
    chromium = _FakeChromium(fail_headless=lambda n: n in (2, 3))
    context, page = _run_auth(monkeypatch, chromium, tmp_path)
    assert context.headless is True
    assert chromium.headless_calls == 4


def test_headless_relaunch_failure_keeps_the_visible_session(monkeypatch, tmp_path):
    """A failed headless relaunch must not discard a working manual login.

    Live 27 Nov: the profile had a valid session and the visible context was
    ready, then relaunching headless on the same persistent profile raised in
    page.goto and the whole job failed with a bare Error. The visible session
    is already authenticated, so the job must continue visibly instead.
    """
    chromium = _FakeChromium(fail_headless=lambda n: n >= 2)
    context, page = _run_auth(monkeypatch, chromium, tmp_path)
    assert context.headless is False
    assert context.closed is False


def test_headless_relaunch_failure_does_not_ask_for_a_new_login(monkeypatch, tmp_path):
    """The visible fallback keeps the authenticated session; no re-login prompt.

    The profile already holds a valid session, so the visible context reaches
    ready at once. Telling the user to log in again would be a false prompt.
    """
    events = []
    chromium = _FakeChromium(fail_headless=lambda n: n >= 2)
    context, page = _run_auth(monkeypatch, chromium, tmp_path,
                              emit=lambda *a: events.append(a))
    assert context.headless is False
    # The generic manual-login prompt already fired before the relaunch; the
    # fallback must not add a second, false "headless could not open" prompt.
    assert not [event for event in events if 'headless' in event[1]]


def test_relaunch_backoff_honours_cancellation(monkeypatch):
    """Stop during the relaunch backoff aborts instead of sleeping it out."""
    mod = auth()
    monkeypatch.setattr(mod.time, 'sleep', lambda seconds: None)
    calls = []

    def check_cancel():
        calls.append(1)
        if len(calls) == 2:
            raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        mod._backoff(5, check_cancel)
    assert len(calls) == 2
