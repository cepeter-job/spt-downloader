"""Synthetic Satu -> Coretax OIDC callback; never uses a live account/token."""
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from urllib.parse import parse_qs, urlencode

import pytest
from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from coretax_browser import CaptureCancelled
from spt_desktop import auth, diagnostics
from spt_desktop.credentials import Login
from support_login_browser import ASYNC_LOGIN_TIMEOUT, browser


SATU = auth.ALLOWED_ORIGINS[0]
LOGIN = SATU + '/login'
CODE = 'SYNTHETIC_CODE_ONLY'
STATE = 'SYNTHETIC_STATE_ONLY'
VERIFIER = 'SYNTHETIC_VERIFIER_' + 'x' * 48
ACCOUNT, PASSWORD = 'SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'
FORM = '<form method="post" action="/login"><input name="username"><input type="password" name="password"><button type="submit">Masuk</button></form>'


class Engine:
    def __init__(self, browser, case='success', app='home', *, login_response_delay=0, route_fault=None):
        self.browser, self.case, self.app = browser, case, app
        self.login_response_delay = login_response_delay
        self.route_fault = route_fault
        self.chromium = self
        self.posts, self.tokens, self.unknown, self.contexts = [], [], [], []
        self.redirected = []
        self.callback_frames = []
        self.fetch_options = []
        engine = self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                engine.redirected.append(self.path)
                self.send_response(400)
                self.send_header('Content-Length', '0')
                self.end_headers()

            def do_POST(self):
                body = self.rfile.read(int(self.headers.get('Content-Length', '0'))).decode('ascii')
                if self.path != '/identityprovider/connect/token':
                    engine.redirected.append(self.path)
                    self.send_response(400)
                else:
                    engine.tokens.append(body)
                    if engine.case.startswith('redirect_'):
                        self.send_response(int(engine.case.rsplit('_', 1)[-1]))
                        host = 'localhost' if '_foreign_' in engine.case else '127.0.0.1'
                        self.send_header('Location', f'http://{host}:{engine.server.server_port}/unapproved')
                    elif engine.case == 'network_failure':
                        self.close_connection = True
                        return
                    else:
                        self.send_response(400 if engine.case == 'rejected' else 200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', '18')
                self.end_headers()
                self.wfile.write(b'{"synthetic":true}')
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.coretax = f'http://127.0.0.1:{self.server.server_port}'
        self.token = self.coretax + '/identityprovider/connect/token'
        self.home = self.coretax + auth.HOME_PATH
        self.search = self.coretax + '/returnsheets/id-ID/taxpayer-search'

    def __enter__(self):
        self.thread = Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)

    def callback(self, app):
        return self.coretax + '/' + app + '/id-ID/auth-callback'

    def callback_url(self, app):
        query = urlencode({'code': CODE, 'state': STATE})
        if self.case == 'missing_state':
            query = urlencode({'code': CODE})
        elif self.case == 'empty_state':
            query = urlencode({'code': CODE, 'state': ''})
        elif self.case == 'empty_code':
            query = urlencode({'code': '', 'state': STATE})
        elif self.case == 'duplicate_state':
            query += '&state=' + STATE
        elif self.case == 'duplicate_code':
            query += '&code=' + CODE
        elif self.case == 'callback_error':
            query += '&error=synthetic_denied'
        elif self.case == 'malformed_query':
            query += '&broken'
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
        elif self.case == 'short_pkce':
            fields['code_verifier'] = 'x' * 42
        elif self.case == 'invalid_pkce':
            fields['code_verifier'] = '!' * 64
        body = urlencode(fields)
        if self.case == 'duplicate_field':
            body += '&client_id=cats-angular-client'
        target = self.token + ('/other' if self.case == 'wrong_endpoint' else '')
        if self.case == 'token_query':
            target += '?synthetic=extra'
        mime = 'application/json' if self.case == 'wrong_mime' else 'application/x-www-form-urlencoded'
        request = 'fetch(' + json.dumps(target) + ',{method:"POST",headers:{"Content-Type":' + json.dumps(mime) + '},body:' + json.dumps(body) + '})'
        repeat = ('await ' + request + '.catch(()=>{});') if self.case == 'replay' else ''
        destination = self.home if app == 'home' else self.search
        return '<script>(async()=>{try{const r=await ' + request + ';if(!r.ok)return;' + repeat + 'location.assign(' + json.dumps(destination) + ');}catch{}})();</script>'

    def launch_persistent_context(self, path, **kwargs):
        self.launch_kwargs = kwargs
        raw = self.browser.new_context(service_workers='block')
        page = raw.new_page()
        def observe(request):
            if request.url == self.token and request.resource_type in ('fetch', 'xhr'):
                self.callback_frames.append('owned' if request.frame == page.main_frame else (
                    'iframe' if request.frame.parent_frame is not None else 'popup'))
        raw.on('request', observe)
        class FaultRoute:
            """Inject boundary faults after the actual synthetic HTTP exchange."""
            def __init__(self, route):
                self.raw = route

            def __getattr__(self, name):
                return getattr(self.raw, name)

            def fetch(self, **options):
                engine.fetch_options.append(options.copy())
                if isinstance(engine.route_fault, Exception):
                    # TLS/DNS/proxy failures are injected only at the external
                    # transport boundary; the owned browser and checker stay real.
                    raise engine.route_fault
                response = self.raw.fetch(**options)
                if engine.route_fault == 'response_url_changed':
                    class ChangedResponse:
                        url = engine.coretax + '/synthetic-unapproved-response'

                        def __getattr__(self, name):
                            return getattr(response, name)
                    return ChangedResponse()
                if engine.route_fault == 'callback_changed':
                    page.evaluate('(path)=>history.replaceState(null,"",path)', auth.HOME_PATH)
                return response

            def fulfill(self, **options):
                if engine.route_fault == 'fulfill_exception':
                    raise RuntimeError('SYNTHETIC_PRIVATE_FULFILL_EXCEPTION ' + CODE + VERIFIER)
                return self.raw.fulfill(**options)

        engine = self
        def install_guard(pattern, handler):
            def guarded(route):
                handler(FaultRoute(route) if self.route_fault and route.request.url == self.token else route)
            raw.route(pattern, guarded)
        state = SimpleNamespace(pages=[page], route=install_guard, closed=False)
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
                if self.case in ('iframe', 'popup'):
                    destination = self.coretax + '/synthetic-frame-host'
                html = '<script>location.assign(' + json.dumps(destination) + ')</script>'
                if self.login_response_delay:
                    # Inject a slow credential response while the real click is pending.
                    time.sleep(self.login_response_delay)
                r.fulfill(body=html, content_type='text/html')
            elif url == LOGIN:
                r.fulfill(body=FORM, content_type='text/html')
            elif url in (self.callback_url('home'), self.callback_url('returnsheets')):
                app = 'home' if '/home/' in url else 'returnsheets'
                r.fulfill(body=self.callback_html(app), content_type='text/html')
            elif url == self.coretax + '/synthetic-frame-host':
                destination = self.callback_url(self.app)
                html = '<iframe src="' + destination + '"></iframe>' if self.case == 'iframe' else (
                    '<script>window.open(' + json.dumps(destination) + ')</script>')
                r.fulfill(body=html, content_type='text/html')
            elif url == self.token and request.method == 'POST':
                r.continue_()  # Only the loopback server can receive this request.
            elif url == self.home:
                r.fulfill(body='<h1>Synthetic home shell</h1>', content_type='text/html')
            else:
                self.unknown.append((request.method, url))
                r.abort('blockedbyclient')
        raw.route('**/*', route)
        return state


def check(browser, tmp_path, monkeypatch, case='success', app='home', *, login_response_delay=0, timeout=None,
          route_fault=None, on_failure=None, check_cancel=lambda: None):
    reads = []
    def saved(origin):
        reads.append(origin)
        return Login(ACCOUNT, PASSWORD)
    monkeypatch.setattr(auth, 'read_login', saved)
    if timeout is None:
        # The connection-close fault is exercised only after a valid token POST
        # reaches the server; give that transport the existing asynchronous budget.
        timeout = ASYNC_LOGIN_TIMEOUT if case in ('success', 'two_apps', 'replay', 'network_failure') else 3
    with Engine(browser, case, app, login_response_delay=login_response_delay, route_fault=route_fault) as engine:
        monkeypatch.setattr(auth, 'CORETAX_ORIGIN', engine.coretax)
        monkeypatch.setattr(auth, 'SEARCH_URL', engine.search)
        monkeypatch.setattr(auth, 'ALLOWED_ORIGINS', (SATU, engine.coretax))
        with monkeypatch.context() as scoped:
            record = diagnostics.record
            def observe(event, **fields):
                recorded = record(event, **fields)
                if event == 'auth.state' and fields.get('reason') == 'code_exchange_failed' and on_failure:
                    on_failure(engine)
                return recorded
            scoped.setattr(diagnostics, 'record', observe)
            with diagnostics.session(tmp_path / 'diagnostics', 'worker') as log:
                result = auth.check_saved_credentials(engine, tmp_path, SATU, ACCOUNT, 'msedge', True,
                                                     check_cancel, timeout=timeout)
                assert log.flush()
    text = '\n'.join(p.read_text(encoding='utf-8') for p in (tmp_path / 'diagnostics/logs').glob('*.jsonl'))
    for private in (CODE, STATE, VERIFIER, ACCOUNT, PASSWORD, engine.token):
        assert private not in text and private not in result[1]
    assert all(c.closed for c in engine.contexts) and not engine.unknown
    assert all(parse_qs(body) == {'username': [ACCOUNT], 'password': [PASSWORD]} for body in engine.posts)
    return engine, reads, result, [json.loads(line) for line in text.splitlines()]


def transport_observation(engine, rows):
    """Expose only synthetic counts and fixed diagnostic categories on failure."""
    return {
        'credential_posts': len(engine.posts),
        'token_posts': len(engine.tokens),
        'redirect_requests': len(engine.redirected),
        'callback_frames': engine.callback_frames,
        'auth_events': [(row.get('event'), row.get('reason'), row.get('request_kind'))
                        for row in rows if row.get('event', '').startswith('auth.')],
    }


def assert_transport_failure(engine, result, rows):
    observed = transport_observation(engine, rows)
    assert result[0] == 'LOGIN_UNVERIFIED', observed
    assert observed['token_posts'] == observed['credential_posts'] == 1, observed
    assert observed['redirect_requests'] == 0, observed
    assert observed['callback_frames'] == ['owned'], observed
    states = [row.get('reason') for row in rows if row.get('event') == 'auth.state']
    assert 'code_exchange_allowed' in states and 'code_exchange_failed' in states, observed
    assert states.index('code_exchange_allowed') < states.index('code_exchange_failed'), observed
    outcomes = [row.get('reason') for row in rows if row.get('event') == 'auth.result']
    assert outcomes == ['code_exchange_failed'], observed


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
    assert next(row for row in rows if row['event'] == 'auth.request_blocked')['request_kind'] == 'code_exchange'


@pytest.mark.parametrize('case', ['refresh', 'password', 'wrong_client', 'wrong_redirect',
    'wrong_code', 'extra_field', 'missing_pkce', 'duplicate_field', 'wrong_endpoint',
    'wrong_mime', 'missing_state', 'empty_state', 'empty_code', 'duplicate_state',
    'duplicate_code', 'callback_error', 'malformed_query', 'short_pkce', 'invalid_pkce',
    'token_query', 'iframe', 'popup', 'before_submit'])
def test_code_exchange_exception_does_not_authorize_other_posts(browser, tmp_path, monkeypatch, case):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, case)
    assert result[0] != 'LOGIN_OK' and engine.tokens == []
    assert len(engine.posts) == (0 if case == 'before_submit' else 1)
    if case in ('iframe', 'popup'):
        assert case in engine.callback_frames


def test_rejected_code_exchange_is_not_success_or_retried(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'rejected')
    assert result[0] == 'LOGIN_UNVERIFIED' and len(engine.tokens) == len(engine.posts) == 1


@pytest.mark.parametrize('case,fault,expected', [
    ('network_failure', None, 'fetch_exception'),
    ('rejected', None, 'http_rejected'),
    ('redirect_same_302', None, 'redirect_rejected'),
    ('success', 'response_url_changed', 'response_url_changed'),
    ('success', 'callback_changed', 'callback_changed'),
    ('success', 'fulfill_exception', 'fulfill_exception'),
])
def test_failed_exchange_identifies_only_its_safe_transport_category(browser, tmp_path, monkeypatch, case, fault, expected):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, case, route_fault=fault,
                                      timeout=ASYNC_LOGIN_TIMEOUT)
    assert_transport_failure(engine, result, rows)
    failures = [row for row in rows if row.get('event') == 'auth.state'
                and row.get('reason') == 'code_exchange_failed']
    assert [row.get('exchange_failure') for row in failures] == [expected]
    if expected != 'fetch_exception':
        assert all('transport_failure' not in row for row in failures)
    assert 'SYNTHETIC_PRIVATE_FULFILL_EXCEPTION' not in json.dumps(rows)


@pytest.mark.parametrize('error_type,message,expected', [
    (PlaywrightTimeoutError, 'Synthetic timeout without transport text', 'timeout'),
    (PlaywrightError, 'Route.fetch: Timeout 4321ms exceeded.', 'timeout'),
    (PlaywrightError, 'Route.fetch: self-signed certificate in certificate chain', 'tls'),
    (PlaywrightError, 'Route.fetch: getaddrinfo ENOTFOUND synthetic.invalid', 'dns'),
    (PlaywrightError, 'apiRequestContext.fetch: getaddrinfo EAI_AGAIN synthetic.invalid', 'dns'),
    (PlaywrightError, 'Route.fetch: net::ERR_PROXY_CONNECTION_FAILED', 'proxy'),
    (PlaywrightError, 'Route.fetch: Socks5 Authentication failed', 'proxy'),
    (PlaywrightError, 'Route.fetch: read ECONNRESET', 'connection'),
    (PlaywrightError, 'Route.fetch: Target page, context or browser has been closed', 'context_closed'),
    (PlaywrightError, 'Route.fetch: Request context disposed.', 'context_closed'),
    (PlaywrightError, 'Route.fetch: Unrecognized synthetic failure', 'unknown'),
    (RuntimeError, 'Route.fetch: read ECONNRESET', 'unknown'),
    (PlaywrightError, 'Route.fetch: https://synthetic.invalid/ECONNRESET?token=private', 'unknown'),
    (PlaywrightError, 'Route.fetch: Unrecognized synthetic failure\nCall log:\n - getaddrinfo ENOTFOUND private', 'unknown'),
    (PlaywrightError, 'Route.fetch: getaddrinfo ENOTFOUNDX synthetic.invalid', 'unknown'),
    (PlaywrightError, 'Route.fetch: ' + 'x' * 1024 + ' getaddrinfo ENOTFOUND private', 'unknown'),
], ids=['typed-timeout', 'timeout', 'tls', 'dns', 'dns-transient', 'proxy', 'socks-proxy',
        'connection', 'closed-page', 'disposed-context', 'unknown', 'non-playwright',
        'url-is-not-error-code', 'ignore-call-log', 'error-code-boundary', 'bounded-headline'])
def test_fetch_failure_reports_only_safe_transport_subcategory(browser, tmp_path, monkeypatch,
                                                               error_type, message, expected):
    private = 'SYNTHETIC_PRIVATE_FETCH_EXCEPTION ' + CODE + VERIFIER
    error = error_type(message + '\n' + private)
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, route_fault=error)
    assert result[0] == 'LOGIN_UNVERIFIED'
    assert len(engine.posts) == 1 and engine.tokens == engine.redirected == []
    assert len(engine.fetch_options) == 1
    assert engine.fetch_options[0]['max_redirects'] == engine.fetch_options[0]['max_retries'] == 0
    assert 0 < engine.fetch_options[0]['timeout'] <= 5000
    failures = [row for row in rows if row.get('event') == 'auth.state'
                and row.get('reason') == 'code_exchange_failed']
    assert [row.get('exchange_failure') for row in failures] == ['fetch_exception']
    assert [row.get('transport_failure') for row in failures] == [expected]
    assert private not in json.dumps(rows) and message not in json.dumps(rows)
    outcomes = [row for row in rows if row.get('event') == 'auth.result']
    assert [row.get('reason') for row in outcomes] == ['code_exchange_failed']
    assert outcomes[0]['blocked_requests'] == 0


@pytest.mark.parametrize('playwright_error', [False, True], ids=['arbitrary-exception', 'non-string-message'])
def test_fetch_diagnostics_do_not_stringify_unknown_exception_or_message(browser, tmp_path, monkeypatch,
                                                                        playwright_error):
    stringified = []
    class PrivateValue:
        def __str__(self):
            stringified.append(True)
            return 'SYNTHETIC_PRIVATE_TRANSPORT_VALUE'
    class PrivateError(RuntimeError):
        def __str__(self):
            return str(PrivateValue())
    error = PlaywrightError(PrivateValue()) if playwright_error else PrivateError()
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, route_fault=error)
    assert result[0] == 'LOGIN_UNVERIFIED' and len(engine.posts) == 1 and not engine.tokens
    assert len(engine.fetch_options) == 1
    failures = [row for row in rows if row.get('event') == 'auth.state'
                and row.get('reason') == 'code_exchange_failed']
    assert [row.get('transport_failure') for row in failures] == ['unknown']
    assert stringified == []
    assert 'SYNTHETIC_PRIVATE_TRANSPORT_VALUE' not in json.dumps(rows)


def test_real_connection_close_reports_connection_subcategory(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'network_failure')
    assert_transport_failure(engine, result, rows)
    failures = [row for row in rows if row.get('event') == 'auth.state'
                and row.get('reason') == 'code_exchange_failed']
    assert [row.get('transport_failure') for row in failures] == ['connection']


def test_failed_exchange_finishes_without_waiting_for_more_callback_attempts(browser, tmp_path, monkeypatch):
    failed = []
    waits_after_failure = []
    def sleep(seconds):
        if failed:
            waits_after_failure.append(seconds)
        time.sleep(seconds)
    # Keep real browser/time behavior; observe only the checker's wait boundary.
    monkeypatch.setattr(auth, 'time', SimpleNamespace(monotonic=time.monotonic, sleep=sleep))
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'rejected',
                                      on_failure=lambda engine: failed.append(True))
    assert_transport_failure(engine, result, rows)
    assert failed and waits_after_failure == [], 'A definitive failure must end the check before another polling wait'


def test_visible_search_marker_cannot_override_failed_exchange(browser, tmp_path, monkeypatch):
    def show_marker(engine):
        # A marker becomes visible after the failed exchange, in the actual owned
        # browser page. The checker must retain the prior definitive failure.
        engine.contexts[0].pages[0].evaluate('''(path)=>{
            history.replaceState(null,"",path);
            document.body.innerHTML='<input id="ObjectPermitNumber">';
        }''', '/returnsheets/id-ID/taxpayer-search')
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'rejected', on_failure=show_marker)
    assert_transport_failure(engine, result, rows)


@pytest.mark.parametrize('fault', [None, PlaywrightTimeoutError('Synthetic timeout')], ids=['http-rejection', 'fetch-timeout'])
def test_stop_after_failed_exchange_takes_precedence_over_unverified_result(browser, tmp_path, monkeypatch, fault):
    failed = []
    def stop():
        if failed:
            raise CaptureCancelled('Synthetic stop after exchange failure')
    with pytest.raises(CaptureCancelled):
        check(browser, tmp_path, monkeypatch, 'rejected' if fault is None else 'success',
              route_fault=fault, on_failure=lambda engine: failed.append(engine), check_cancel=stop)
    assert failed and all(context.closed for context in failed[0].contexts)
    rows = [json.loads(line) for path in (tmp_path / 'diagnostics/logs').glob('*.jsonl')
            for line in path.read_text(encoding='utf-8').splitlines()]
    outcomes = [row for row in rows if row.get('event') == 'auth.result']
    assert [row.get('status') for row in outcomes] == ['CANCELLED']
    assert [row.get('reason') for row in outcomes] == ['cancelled']


@pytest.mark.parametrize('case', ['redirect_same_302', 'redirect_foreign_303', 'redirect_same_307', 'redirect_same_308',
    'redirect_foreign_307', 'redirect_foreign_308', 'network_failure'])
def test_token_exchange_cannot_follow_redirects_or_retry_transport(browser, tmp_path, monkeypatch, case):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, case)
    assert_transport_failure(engine, result, rows)


def test_slow_login_response_preserves_exchange_deadline_boundary(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'network_failure',
                                      login_response_delay=3.25, timeout=3)
    observed = transport_observation(engine, rows)
    assert result[0] == 'LOGIN_UNVERIFIED', observed
    assert observed['credential_posts'] == 1, observed
    assert observed['token_posts'] == observed['redirect_requests'] == 0, observed
    assert observed['callback_frames'] == ['owned'], observed
    assert ('auth.request_blocked', 'cross_origin_write', 'code_exchange') in observed['auth_events'], observed
    assert not any(row.get('reason') == 'code_exchange_allowed' for row in rows), observed
    assert [row.get('reason') for row in rows if row.get('event') == 'auth.result'] == ['cross_origin_write'], observed


def test_transport_fixture_reaches_network_fault_after_slow_login_response(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'network_failure', login_response_delay=3.25)
    assert_transport_failure(engine, result, rows)


def test_credential_check_explicitly_blocks_service_workers(browser, tmp_path, monkeypatch):
    engine, reads, result, rows = check(browser, tmp_path, monkeypatch, 'wrong_client')
    assert engine.launch_kwargs.get('service_workers') == 'block'


def test_stop_after_code_exchange_closes_context_without_search_success(browser, tmp_path, monkeypatch):
    with Engine(browser) as engine:
        monkeypatch.setattr(auth, 'CORETAX_ORIGIN', engine.coretax)
        monkeypatch.setattr(auth, 'SEARCH_URL', engine.search)
        monkeypatch.setattr(auth, 'ALLOWED_ORIGINS', (SATU, engine.coretax))
        monkeypatch.setattr(auth, 'read_login', lambda origin: Login(ACCOUNT, PASSWORD))
        def stop():
            if engine.tokens:
                raise CaptureCancelled('Synthetic stop')
        with pytest.raises(CaptureCancelled):
            auth.check_saved_credentials(engine, tmp_path, SATU, ACCOUNT, 'msedge', True,
                                         stop, timeout=ASYNC_LOGIN_TIMEOUT)
        assert len(engine.tokens) == 1 and all(c.closed for c in engine.contexts)
