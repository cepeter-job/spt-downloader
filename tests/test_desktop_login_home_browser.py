"""The reported Satu->Coretax-home flow is reproduced with synthetic routes."""
import pytest
from playwright.sync_api import sync_playwright
from spt_desktop import auth
from spt_desktop.credentials import Login

LOGIN='https://satu.intranet.pajak.go.id/login'
HOME='https://coretax.intranet.pajak.go.id/home/id-ID/'
SEARCH='https://coretax.intranet.pajak.go.id/returnsheets/id-ID/taxpayer-search'
FORM='<form method="post" action="/session"><input name="username"><input type="password"><button type="submit">Masuk</button></form>'


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as p:
        owned=p.chromium.launch(channel='msedge',headless=True)
        yield owned
        owned.close()


class Page:
    def __init__(self,raw,context):self.raw=raw;self.context=context;self.first=True
    def __getattr__(self,name):return getattr(self.raw,name)
    def goto(self,url,**kwargs):
        # Simulate the initial SSO redirect without an HTTP302 that can escape routing.
        if self.first and url==SEARCH:
            self.first=False
            restored=self.context.engine.mode=='manual' and len(self.context.engine.contexts)>=3
            return self.raw.goto(HOME if self.context.engine.mode=='sso_home' or restored else LOGIN,**kwargs)
        return self.raw.goto(url,**kwargs)
    def wait_for_timeout(self,ms):
        if self.context.engine.mode=='manual' and self.raw.url==LOGIN:
            self.raw.goto(HOME,wait_until='domcontentloaded')
        else:self.raw.wait_for_timeout(ms)


class Context:
    def __init__(self,raw,engine):
        self.raw=raw;self.engine=engine;self.closed=False
        self.page=Page(raw.new_page(),self);self.pages=[self.page]
    def route(self,*args):return self.raw.route(*args)
    def close(self):self.closed=True;self.raw.close()


class Engine:
    def __init__(self,browser,mode):self.browser=browser;self.mode=mode;self.chromium=self;self.contexts=[];self.posts=[]
    def launch_persistent_context(self,path,**kwargs):
        raw=self.browser.new_context()
        def route(r):
            url=r.request.url
            if url==LOGIN:r.fulfill(body=FORM,content_type='text/html')
            elif url=='https://satu.intranet.pajak.go.id/session':
                self.posts.append(r.request.post_data)
                r.fulfill(body='<script>location.assign("'+HOME+'");</script>',content_type='text/html')
            elif url==HOME:r.fulfill(body='<h1>Synthetic Coretax home</h1>',content_type='text/html')
            elif url==SEARCH:r.fulfill(body='<script>setTimeout(()=>{document.body.innerHTML=\'<input id="ObjectPermitNumber">\';},250);</script>',content_type='text/html')
            else:r.abort('blockedbyclient')
        raw.route('**/*',route)
        context=Context(raw,self);self.contexts.append(context)
        return context


def test_manual_satu_login_to_home_proceeds_without_five_minute_wait(browser,tmp_path,monkeypatch):
    monkeypatch.setattr(auth,'try_saved_login',lambda *args:False)
    engine=Engine(browser,'manual');events=[]
    context,page=auth.authenticate_owned(engine,tmp_path/'profile','msedge',False,
        lambda *args:events.append(args),lambda:None,manual_timeout=3)
    try:
        assert page.url==SEARCH and auth.authenticated(page)
        assert any('Pencarian WP' in message for kind,message in events)
        assert engine.posts==[]
    finally:context.close()
    assert all(context.closed for context in engine.contexts)


def test_manual_home_then_headless_restore_reuses_verified_search(browser,tmp_path,monkeypatch):
    monkeypatch.setattr(auth,'try_saved_login',lambda *args:False)
    engine=Engine(browser,'manual')
    context,page=auth.authenticate_owned(engine,tmp_path/'profile','msedge',True,lambda *args:None,lambda:None,manual_timeout=3)
    try:
        assert page.url==SEARCH and auth.authenticated(page)
        assert len(engine.contexts)==3
    finally:context.close()
    assert all(context.closed for context in engine.contexts)


def test_saved_password_post_to_home_is_verified_by_check_without_retry(browser,tmp_path,monkeypatch):
    engine=Engine(browser,'saved')
    monkeypatch.setattr(auth,'read_login',lambda origin:Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY'))
    status,message=auth.check_saved_credentials(engine,tmp_path,auth.ALLOWED_ORIGINS[0],'SYNTHETIC_ACCOUNT','msedge',True,lambda:None,timeout=3)
    assert status=='LOGIN_OK' and len(engine.posts)==1
    assert 'SYNTHETIC_PASSWORD_ONLY' not in message
    assert all(context.closed for context in engine.contexts)


def test_sso_home_before_password_submission_does_not_certify_saved_password(browser,tmp_path,monkeypatch):
    engine=Engine(browser,'sso_home');reads=[]
    monkeypatch.setattr(auth,'read_login',lambda origin:reads.append(origin))
    status,message=auth.check_saved_credentials(engine,tmp_path,auth.ALLOWED_ORIGINS[0],'SYNTHETIC_ACCOUNT','msedge',True,lambda:None,timeout=3)
    assert status=='LOGIN_UNVERIFIED' and 'belum diuji' in message
    assert reads==[] and engine.posts==[] and all(context.closed for context in engine.contexts)
