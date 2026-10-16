"""Real routed login transitions; all identities, secrets and pages are synthetic."""
import json
from pathlib import Path

import pytest
from spt_desktop import auth, diagnostics
from spt_desktop.credentials import Login
from support_login_browser import browser

SATU = auth.ALLOWED_ORIGINS[0]
LOGIN = SATU + '/login'
ENTRY = auth.CORETAX_ORIGIN + '/returnsheets/id-ID/'
ACCOUNT = 'SYNTHETIC_ACCOUNT'
SECRET = 'SYNTHETIC_PASSWORD_ONLY'
FORM = ('<form method="post" action="/login"><input type="hidden" name="_csrf" '
        'value="SYNTHETIC_CSRF_ONLY"><input name="username" autocomplete="off">'
        '<input type="password" name="password" id="passwordInput" autocomplete="off">'
        '<button type="button" id="togglePassword">Show</button>'
        '<button type="submit"><span class="indicator-label">Masuk</span>'
        '<span style="display:none">Please wait</span></button></form>')


class Page:
    def __init__(self, raw, engine):
        self.raw, self.engine = raw, engine
        self.waits = 0

    def __getattr__(self, name):
        return getattr(self.raw, name)

    def wait_for_timeout(self, milliseconds):
        self.waits += 1
        mode = self.engine.mode
        # Release each transition only after the product has inspected the shell.
        # A slow CI runner cannot complete the redirect before the first check.
        if self.waits == 1 and mode not in ('stalled', 'cancelled'):
            if mode == 'sso':
                self.raw.evaluate("document.body.innerHTML='<input id=ObjectPermitNumber>'")
            else:
                self.raw.evaluate('(url)=>location.assign(url)', LOGIN + '?trace=SYNTHETIC_TOKEN_ONLY')
                self.raw.wait_for_url(LOGIN + '?trace=SYNTHETIC_TOKEN_ONLY', wait_until='domcontentloaded')
        elif self.waits == 2 and mode not in ('stalled', 'cancelled', 'sso'):
            html = FORM
            if mode == 'challenge':
                html += '<input autocomplete="one-time-code">'
            elif mode == 'unsafe':
                html = html.replace('>Masuk<', '>Submit SPT<')
            self.raw.evaluate('(html)=>document.body.innerHTML=html', html)
        self.raw.wait_for_timeout(min(milliseconds, 20))


class Context:
    def __init__(self, raw, engine):
        self.raw, self.engine, self.closed = raw, engine, False
        self.page = Page(raw.new_page(), engine)
        self.pages = [self.page]

    def route(self, *args):
        self.raw.route(*args)

    def close(self):
        self.closed = True
        self.raw.close()


class Engine:
    def __init__(self, browser, mode='success', entry=ENTRY):
        self.browser, self.mode, self.entry = browser, mode, entry
        self.chromium = self
        self.contexts, self.paths, self.posts, self.unknown = [], [], [], []

    def launch_persistent_context(self, path, **kwargs):
        self.paths.append(Path(path))
        raw = self.browser.new_context()
        def route(r):
            request = r.request
            if request.url == self.entry or request.url == auth.SEARCH_URL:
                html = '<input id="ObjectPermitNumber">' if self.posts else '<main>SYNTHETIC ENTRY SHELL</main>'
                r.fulfill(body=html, content_type='text/html')
            elif request.url == LOGIN + '?trace=SYNTHETIC_TOKEN_ONLY':
                r.fulfill(body='<main>SYNTHETIC LOGIN SHELL</main>', content_type='text/html')
            elif request.url == LOGIN and request.method == 'POST':
                self.posts.append(request.post_data)
                if self.mode == 'reject':
                    r.fulfill(body=FORM, content_type='text/html')
                else:
                    r.fulfill(body='<script>location.assign(' + json.dumps(auth.SEARCH_URL) + ')</script>', content_type='text/html')
            else:
                self.unknown.append((request.method, request.url))
                r.abort('blockedbyclient')
        raw.route('**/*', route)
        context = Context(raw, self)
        self.contexts.append(context)
        return context


def run_check(browser, tmp_path, monkeypatch, *, selected=SATU, mode='success', entry=ENTRY):
    engine = Engine(browser, mode, entry)
    monkeypatch.setattr(auth, 'SEARCH_URL', entry)
    reads = []
    def saved(origin):
        reads.append(origin)
        if mode == 'missing':
            return None
        if mode == 'error':
            raise RuntimeError(SECRET + ' cookie=SYNTHETIC_COOKIE_ONLY')
        return Login('OTHER_SYNTHETIC_ACCOUNT' if mode == 'account' else ACCOUNT, SECRET)
    monkeypatch.setattr(auth, 'read_login', saved)
    def cancel():
        if mode == 'cancelled' and engine.contexts and engine.contexts[-1].page.waits:
            from coretax_browser import CaptureCancelled
            raise CaptureCancelled('synthetic stop')
    root = tmp_path / 'diagnostics'
    try:
        with diagnostics.session(root, 'worker', job_id='synthetic-check') as log:
            outcome = auth.check_saved_credentials(engine, tmp_path / 'app', selected, ACCOUNT,
                'msedge', True, cancel, timeout=0.2 if mode == 'stalled' else 10)
            assert log.flush()
    finally:
        assert all(context.closed for context in engine.contexts)
        assert all(not path.exists() for path in engine.paths)
        assert engine.unknown == []
        if mode == 'cancelled':
            assert reads == [] and engine.posts == []
    text = '\n'.join(p.read_text(encoding='utf-8') for p in (root / 'logs').glob('*.jsonl'))
    for forbidden in (ACCOUNT, SECRET, 'SYNTHETIC_CSRF_ONLY', 'SYNTHETIC_TOKEN_ONLY',
                      'SYNTHETIC_COOKIE_ONLY', SATU, auth.CORETAX_ORIGIN, 'cookie='):
        assert forbidden not in text
        assert forbidden not in outcome[1] or forbidden in (SATU, auth.CORETAX_ORIGIN)
    return outcome, engine, reads, [json.loads(line) for line in text.splitlines()]


def auth_result(rows):
    results = [row for row in rows if row['event'] == 'auth.result']
    assert len(results) == 1, 'Every check needs one secret-free reason, not just phase.completed'
    return results[0]


@pytest.mark.parametrize('entry', [ENTRY, auth.SEARCH_URL])
def test_selected_satu_waits_for_real_coretax_redirect_before_one_login(browser, tmp_path, monkeypatch, entry):
    (status, message), engine, reads, rows = run_check(browser, tmp_path, monkeypatch, entry=entry)
    assert status == 'LOGIN_OK', (status, message)
    assert reads == [SATU] and len(engine.posts) == 1
    assert 'username=SYNTHETIC_ACCOUNT' in engine.posts[0]
    result = auth_result(rows)
    assert (result['reason'], result['expected_origin'], result['observed_origin'], result['submitted']) == (
        'verified', 'satu', 'coretax', True)
    states = [row for row in rows if row['event'] == 'auth.state']
    assert [(r['reason'], r['observed_origin']) for r in states] == [
        ('waiting_redirect', 'coretax'), ('waiting_form', 'satu'), ('login_form_ready', 'satu')]


def test_selected_coretax_waits_then_names_final_satu_without_reading_secret(browser, tmp_path, monkeypatch):
    (status, message), engine, reads, rows = run_check(browser, tmp_path, monkeypatch, selected=auth.CORETAX_ORIGIN)
    assert status == 'LOGIN_BLOCKED' and SATU in message
    assert not reads and not engine.posts
    result = auth_result(rows)
    assert (result['reason'], result['expected_origin'], result['observed_origin'], result['submitted']) == (
        'origin_mismatch', 'coretax', 'satu', False)


@pytest.mark.parametrize('mode,status,reason,read_count,post_count', [
    ('challenge', 'LOGIN_MANUAL', 'challenge', 0, 0),
    ('unsafe', 'LOGIN_MANUAL', 'unsafe_form', 0, 0),
    ('stalled', 'LOGIN_UNVERIFIED', 'readiness_timeout', 0, 0),
    ('sso', 'LOGIN_UNVERIFIED', 'existing_session', 0, 0),
    ('missing', 'LOGIN_BLOCKED', 'credential_missing', 1, 0),
    ('account', 'LOGIN_BLOCKED', 'account_mismatch', 1, 0),
    ('error', 'LOGIN_ERROR', 'check_error', 1, 0),
    ('reject', 'LOGIN_UNVERIFIED', 'verification_timeout', 1, 1),
])
def test_redirect_outcomes_have_distinct_private_reasons_without_retry(
        browser, tmp_path, monkeypatch, mode, status, reason, read_count, post_count):
    (actual, message), engine, reads, rows = run_check(browser, tmp_path, monkeypatch, mode=mode)
    assert actual == status, (actual, message)
    assert len(reads) == read_count and len(engine.posts) == post_count
    result = auth_result(rows)
    assert result['reason'] == reason and result['status'] == status
    assert result['submitted'] is bool(post_count)
    assert len([r for r in rows if r['event'] == 'auth.state']) <= 3
    assert 'password salah' not in message.lower()


def test_stop_during_redirect_wait_never_reads_credential_and_logs_cancellation(browser, tmp_path, monkeypatch):
    from coretax_browser import CaptureCancelled
    with pytest.raises(CaptureCancelled):
        run_check(browser, tmp_path, monkeypatch, mode='cancelled')
    rows = [json.loads(line) for p in (tmp_path / 'diagnostics/logs').glob('*.jsonl')
            for line in p.read_text(encoding='utf-8').splitlines()]
    result = auth_result(rows)
    assert result['reason'] == 'cancelled' and result['status'] == 'CANCELLED'
    assert result['submitted'] is False
