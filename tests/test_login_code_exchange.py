"""Synthetic Satu -> Coretax OIDC callback; never uses a live account/token."""
import json
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from spt_desktop import auth, diagnostics
from spt_desktop.credentials import Login
from support_login_browser import browser


SATU = auth.ALLOWED_ORIGINS[0]
LOGIN = SATU + '/login'
TOKEN = auth.CORETAX_ORIGIN + '/identityprovider/connect/token'
HOME = auth.CORETAX_ORIGIN + auth.HOME_PATH
CODE = 'SYNTHETIC_CODE_ONLY'
STATE = 'SYNTHETIC_STATE_ONLY'
VERIFIER = 'SYNTHETIC_VERIFIER_' + 'x' * 48
ACCOUNT, PASSWORD = 'SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'
FORM = '<form method="post" action="/login"><input name="username"><input type="password"><button type="submit">Masuk</button></form>'


class Engine:
    def __init__(self, browser, case='success', app='home'):
        self.browser, self.case, self.app = browser, case, app
        self.chromium = self
        self.posts, self.tokens, self.unknown, self.contexts = [], [], [], []

    def callback(self, app):
        return auth.CORETAX_ORIGIN + '/' + app + '/id-ID/auth-callback'

    def callback_url(self, app):
        query = urlencode({'code': CODE, 'state': STATE})
        if self.case == 'missing_state':
            query = urlencode({'code': CODE})
        return self.callback(app) + '?' + query

    def callback_html(self, app):
        fields = {'grant_type': 'authorization_code', 'client_id': 'cats-angular-client',
                  'redirect_uri': self.callback(app), 'code': CODE, 'code_verifier': VERIFIER}
        if self.case == 'refresh':
            fields['grant_type'] = 'refresh_token'
        elif self.case == 'password':
            fields['grant_type'] = 'password'
        elif self.case == 'wrong_client':
            fields['client_id'] = 'OTHER_SYNTHETIC_CLIENT'
        elif self.case == 'wrong_redirect':
            fields['redirect_uri'] = auth.CORETAX_ORIGIN + '/uninspected/callback'
        elif self.case == 'wrong_code':
            fields['code'] = 'OTHER_SYNTHETIC_CODE'
        elif self.case == 'extra_field':
            fields['client_secret'] = 'SYNTHETIC_SECRET_ONLY'
        elif self.case == 'missing_pkce':
            fields.pop('code_verifier')
        body = urlencode(fields)
        if self.case == 'duplicate_field':
            body += '&client_id=cats-angular-client'
        target = TOKEN + ('/other' if self.case == 'wrong_endpoint' else '')
        mime = 'application/json' if self.case == 'wrong_mime' else 'application/x-www-form-urlencoded'
        request = 'fetch(' + json.dumps(target) + ',{method:"POST",headers:{"Content-Type":' + json.dumps(mime) + '},body:' + json.dumps(body) + '})'
        repeat = ('await ' + request + '.catch(()=>{});') if self.case == 'replay' else ''
        return '<script>(async()=>{try{const r=await ' + request + ';if(!r.ok)return;' + repeat + 'location.assign(' + json.dumps(HOME) + ');}catch{}})();</script>'

    def launch_persistent_context(self, path, **kwargs):
        raw = self.browser.new_context(service_workers='block')
        page = raw.new_page()
        state = SimpleNamespace(pages=[page], route=raw.route, closed=False)
        def close():
            state.closed = True
            raw.close()
        state.close = close
        self.contexts.append(state)

        def route(r):
            request = r.request
            url = request.url
            if url == auth.SEARCH_URL:
                if not self.posts:
                    destination = self.callback_url(self.app) if self.case == 'before_submit' else LOGIN
                    html = '<script>location.assign(' + json.dumps(destination) + ')</script>'
                elif self.case == 'two_apps' and len(self.tokens) == 1:
                    html = '<script>location.assign(' + json.dumps(self.callback_url('returnsheets')) + ')</script>'
                elif self.tokens:
                    html = '<input id="ObjectPermitNumber">'
                else:
                    html = '<p>Synthetic unverified shell</p>'
                r.fulfill(body=html, content_type='text/html')
            elif url == LOGIN and request.method == 'POST':
                self.posts.append(request.post_data)
                destination = self.callback_url(self.app)
                html = ('<iframe src="' + destination + '"></iframe>') if self.case == 'iframe' else (
                    '<script>location.assign(' + json.dumps(destination) + ')</script>')
                r.fulfill(body=html, content_type='text/html')
            elif url == LOGIN:
                r.fulfill(body=FORM, content_type='text/html')
            elif url in (self.callback_url('home'), self.callback_url('returnsheets')):
                app = 'home' if '/home/' in url else 'returnsheets'
                r.fulfill(body=self.callback_html(app), content_type='text/html')
            elif url == TOKEN and request.method == 'POST':
                self.tokens.append(request.post_data)
                r.fulfill(status=400 if self.case == 'rejected' else 200,
                          body='{"synthetic":true}', content_type='application/json')
            elif url == HOME:
                r.fulfill(body='<h1>Synthetic home shell</h1>', content_type='text/html')
            else:
                self.unknown.append((request.method, url))
                r.abort('blockedbyclient')
        raw.route('**/*', route)
        return state


def check(browser, tmp_path, monkeypatch, case='success', app='home'):
    engine = Engine(browser, case, app)
    reads = []
    def saved(origin):
        reads.append(origin)
        return Login(ACCOUNT, PASSWORD)
    monkeypatch.setattr(auth, 'read_login', saved)
    with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
        result = auth.check_saved_credentials(engine, tmp_path, SATU, ACCOUNT, 'msedge', True,
                                             lambda: None, timeout=3)
        assert log.flush()
    text = '\n'.join(p.read_text(encoding='utf-8') for p in (tmp_path / 'diagnostics/logs').glob('*.jsonl'))
    for private in (CODE, STATE, VERIFIER, ACCOUNT, PASSWORD, TOKEN):
        assert private not in text and private not in result[1]
    assert all(c.closed for c in engine.contexts) and not engine.unknown
    return engine, reads, result, [json.loads(line) for line in text.splitlines()]


@pytest.mark.parametrize('app', ['home', 'returnsheets'])
def test_inspected_code_exchange_allows_satu_home_search_verification(browser, tmp_path, monkeypatch, app):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, app=app)
    assert result[0] == 'LOGIN_OK'
    assert reads == [SATU] and len(engine.posts) == len(engine.tokens) == 1
    assert any(row.get('reason') == 'code_exchange_allowed' for row in rows)


def test_home_then_search_can_each_complete_one_callback(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'two_apps')
    assert result[0] == 'LOGIN_OK' and len(engine.posts) == 1 and len(engine.tokens) == 2


def test_same_callback_cannot_repeat_a_token_post(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'replay')
    assert result[0] == 'LOGIN_OK' and len(engine.tokens) == 1
    assert next(row for row in rows if row['event'] == 'auth.result')['blocked_requests'] == 1


@pytest.mark.parametrize('case', ['refresh', 'password', 'wrong_client', 'wrong_redirect',
    'wrong_code', 'extra_field', 'missing_pkce', 'duplicate_field', 'wrong_endpoint',
    'wrong_mime', 'missing_state', 'iframe', 'before_submit'])
def test_code_exchange_exception_does_not_authorize_other_posts(browser, tmp_path, monkeypatch, case):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, case)
    assert result[0] != 'LOGIN_OK' and engine.tokens == []
    assert len(engine.posts) == (0 if case == 'before_submit' else 1)


def test_rejected_code_exchange_is_not_success_or_retried(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'rejected')
    assert result[0] == 'LOGIN_UNVERIFIED' and len(engine.tokens) == len(engine.posts) == 1
