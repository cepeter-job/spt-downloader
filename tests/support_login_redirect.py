"""Synthetic routed login shells shared by check/start regressions."""
import json
from pathlib import Path
from spt_desktop import auth

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
        if self.waits == 1 and mode in ('blocked_before', 'blocked_both'):
            # Complete these intercepted requests before the login form appears.
            self.raw.evaluate('''async (url) => {
                for (let i = 0; i < 3; i++) {
                    await fetch(url, {method: 'POST', body: 'SYNTHETIC_POST_ONLY'}).catch(() => {});
                }
            }''', auth.CORETAX_ORIGIN + '/synthetic-readiness?token=SYNTHETIC_PRIVATE_QUERY')
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
                if self.posts and self.mode in ('blocked', 'blocked_both', 'blocked_optional'):
                    target = auth.CORETAX_ORIGIN + '/synthetic-readiness?token=SYNTHETIC_PRIVATE_QUERY'
                    after = ('document.body.innerHTML="<input id=ObjectPermitNumber>";'
                             if self.mode == 'blocked_optional' else '')
                    html = ('<script>(async()=>{for(let i=0;i<3;i++)await fetch(' + json.dumps(target)
                            + ',{method:"POST",body:"SYNTHETIC_POST_ONLY"}).catch(()=>{});'
                            + after + '})();</script>')
                r.fulfill(body=html, content_type='text/html')
            elif request.url == LOGIN + '?trace=SYNTHETIC_TOKEN_ONLY':
                r.fulfill(body='<main>SYNTHETIC LOGIN SHELL</main>', content_type='text/html')
            elif request.url == LOGIN and request.method == 'POST':
                self.posts.append(request.post_data)
                if self.mode in ('reject', 'blocked_before'):
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

