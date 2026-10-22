"""Normal download login uses intercepted synthetic pages, never a live account."""
from pathlib import Path
import pytest
from playwright.sync_api import sync_playwright
from spt_desktop import auth
from spt_desktop.credentials import Login

ORIGIN='https://satu.intranet.pajak.go.id'
ACCOUNT='SYNTHETIC_ACCOUNT'
SECRET='SYNTHETIC_PASSWORD_ONLY'
FORM='<form method="post" action="/session"><input autocomplete="username" name="username"><input type="password" name="password"><button type="submit">Login</button></form>'
READY='<input id="ObjectPermitNumber">'
READY_URL='https://coretax.intranet.pajak.go.id/returnsheets/id-ID/taxpayer-search'


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='msedge',headless=True)
        yield browser
        browser.close()


class RoutedPlaywright:
    def __init__(self,browser,mode='success',form=FORM):
        self.browser=browser;self.mode=mode;self.form=form
        self.chromium=self;self.contexts=[];self.paths=[];self.posts=[]
    def launch_persistent_context(self,path,**kwargs):
        self.paths.append(Path(path))
        context=self.browser.new_context()
        self.contexts.append(context)
        def route(request):
            url=request.request.url
            if self.mode=='network':request.abort('connectionrefused');return
            if url==auth.SEARCH_URL:
                request.fulfill(body=READY if self.mode=='already' else self.form,content_type='text/html')
            elif url==ORIGIN+'/session':
                self.posts.append(request.request.post_data)
                if self.mode in ('success','slow_success'):
                    delay=750 if self.mode=='slow_success' else 0
                    request.fulfill(body='<script>setTimeout(()=>location.assign("'+READY_URL+'"),'+str(delay)+');</script>',content_type='text/html')
                elif self.mode=='challenge':request.fulfill(body='<input autocomplete="one-time-code">',content_type='text/html')
                else:request.fulfill(body=self.form,content_type='text/html')
            elif url==READY_URL:request.fulfill(body=READY,content_type='text/html')
            else:request.abort('blockedbyclient')
        context.route('**/*',route)
        return context


def run_login(browser, tmp_path, monkeypatch, mode='success', form=FORM, account=ACCOUNT):
    monkeypatch.setattr(auth, 'SEARCH_URL', READY_URL if mode == 'already' else ORIGIN + '/login')
    engine = RoutedPlaywright(browser, mode, form)
    reads, events = [], []
    monkeypatch.setattr(auth, 'read_login', lambda origin: (reads.append(origin) or Login(ACCOUNT, SECRET)))
    if mode in ('reject', 'challenge'):
        wait = auth._wait_ready
        monkeypatch.setattr(auth, '_wait_ready', lambda page, deadline, cancel, emit=None:
            wait(page, auth.time.monotonic() + 0.2, cancel, emit=emit))
    try:
        context, page = auth.authenticate_owned(engine, tmp_path / 'profile', 'msedge', False,
            lambda *args: events.append(args), lambda: None, manual_timeout=0, account=account)
    except auth.AuthBlocked as error:
        message = str(error)
        assert SECRET not in message and ACCOUNT not in message
        return False, message, engine, reads, events
    else:
        try:
            assert auth.authenticated(page)
            return True, '', engine, reads, events
        finally:
            context.close()
    finally:
        assert all(not context.pages for context in engine.contexts)


@pytest.mark.parametrize('mode', ['success', 'slow_success'])
def test_named_download_submits_saved_password_once_without_a_preliminary_check(browser, tmp_path, monkeypatch, mode):
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, mode=mode)
    assert ready and reads == [ORIGIN] and len(engine.posts) == 1
    assert 'username=SYNTHETIC_ACCOUNT' in engine.posts[0]
    assert 'password=SYNTHETIC_PASSWORD_ONLY' in engine.posts[0]
    assert not any(kind == 'login_required' for kind, _ in events)


def test_unbound_sso_cannot_start_named_download_or_read_password(browser, tmp_path, monkeypatch):
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, mode='already')
    assert not ready and 'SSO' in message
    assert not reads and not engine.posts


def test_rejected_password_is_not_retried_during_download_login(browser, tmp_path, monkeypatch):
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, mode='reject')
    assert not ready and len(engine.posts) == 1 and reads == [ORIGIN]
    assert 'password salah' not in message.lower()
    assert any(kind == 'login_required' for kind, _ in events)


@pytest.mark.parametrize('form', [FORM + '<input id="captcha">', FORM + '<input autocomplete="one-time-code">',
    FORM.replace('>Login<', '>Submit SPT<'),
    FORM.replace('<button type="submit"', '<button formaction="/returnsheets/submit" type="submit"')])
def test_challenged_or_unsafe_download_login_stays_manual_without_reading_password(browser, tmp_path, monkeypatch, form):
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, form=form)
    assert not ready and not reads and not engine.posts
    assert any(kind == 'login_required' for kind, _ in events)


def test_post_password_mfa_stays_manual_and_never_resubmits(browser, tmp_path, monkeypatch):
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, mode='challenge')
    assert not ready and len(engine.posts) == 1 and reads == [ORIGIN]
    assert any(kind == 'login_required' for kind, _ in events)


def test_selected_account_mismatch_never_submits_during_download(browser, tmp_path, monkeypatch):
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, account='OTHER_SYNTHETIC_ACCOUNT')
    assert not ready and reads == [ORIGIN] and not engine.posts


def test_missing_credential_falls_back_to_manual_download_login(browser, tmp_path, monkeypatch):
    monkeypatch.setattr(auth, 'SEARCH_URL', ORIGIN + '/login')
    monkeypatch.setattr(auth, 'read_login', lambda origin: None)
    engine = RoutedPlaywright(browser)
    events = []
    with pytest.raises(auth.AuthBlocked):
        auth.authenticate_owned(engine, tmp_path / 'profile', 'msedge', False,
            lambda *args: events.append(args), lambda: None, manual_timeout=0, account=ACCOUNT)
    assert not engine.posts and all(not context.pages for context in engine.contexts)
    assert any(kind == 'login_required' for kind, _ in events)


def test_stop_after_submission_closes_download_browser(browser, tmp_path, monkeypatch):
    from coretax_browser import CaptureCancelled
    monkeypatch.setattr(auth, 'SEARCH_URL', ORIGIN + '/login')
    monkeypatch.setattr(auth, 'read_login', lambda origin: Login(ACCOUNT, SECRET))
    engine = RoutedPlaywright(browser, mode='reject')
    def cancelled():
        if engine.posts:
            raise CaptureCancelled('Synthetic cancellation after password submission')
    with pytest.raises(CaptureCancelled):
        auth.authenticate_owned(engine, tmp_path / 'profile', 'msedge', False,
            lambda *args: None, cancelled, manual_timeout=0, account=ACCOUNT)
    assert len(engine.posts) == 1 and all(not context.pages for context in engine.contexts)


def test_compound_masuk_button_is_still_bound_for_download_login(browser, tmp_path, monkeypatch):
    form = FORM.replace('>Login</button>', '><span class="indicator-label">Masuk</span><span style="display:none">Please wait</span></button>')
    ready, message, engine, reads, events = run_login(browser, tmp_path, monkeypatch, form=form)
    assert ready and reads == [ORIGIN] and len(engine.posts) == 1


@pytest.mark.parametrize('failure', ['read', 'fill', 'click'])
def test_secret_bearing_login_errors_do_not_escape_into_manual_download_messages(browser, tmp_path, monkeypatch, failure):
    monkeypatch.setattr(auth, 'SEARCH_URL', ORIGIN + '/login')
    engine = RoutedPlaywright(browser)
    def unsafe_error(*args, **kwargs):
        raise RuntimeError(ACCOUNT + ' ' + SECRET + ' synthetic private call log')
    if failure == 'read':
        monkeypatch.setattr(auth, 'read_login', unsafe_error)
    else:
        monkeypatch.setattr(auth, 'read_login', lambda origin: Login(ACCOUNT, SECRET))
        original = auth._bind_login_fields
        def controls(page, inspected):
            fields, current = original(page, inspected)
            origin, identifier, password, button = fields
            monkeypatch.setattr(identifier if failure == 'fill' else button,
                'fill' if failure == 'fill' else 'click', unsafe_error)
            return fields, current
        monkeypatch.setattr(auth, '_bind_login_fields', controls)
    events = []
    with pytest.raises(auth.AuthBlocked) as error:
        auth.authenticate_owned(engine, tmp_path / 'profile', 'msedge', False,
            lambda *args: events.append(args), lambda: None, manual_timeout=0, account=ACCOUNT)
    for private in (ACCOUNT, SECRET, 'synthetic private call log'):
        assert private not in str(error.value) and private not in repr(events)
    assert all(not context.pages for context in engine.contexts)
