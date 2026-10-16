"""Synthetic login browser helpers; no collected tests or shared mutable test state."""
import pytest
from playwright.sync_api import sync_playwright


LOGIN='https://satu.intranet.pajak.go.id/login'


HOME='https://coretax.intranet.pajak.go.id/home/id-ID/'


SEARCH='https://coretax.intranet.pajak.go.id/returnsheets/id-ID/taxpayer-search'


FORM='<form method="post" action="/session"><input name="username"><input type="password"><button type="submit">Masuk</button></form>'


ASYNC_LOGIN_TIMEOUT=10


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
            url=HOME if self.context.engine.mode=='sso_home' or restored else LOGIN
        try:
            return self.raw.goto(url,**kwargs)
        except Exception as error:
            # Hanya fase navigasi fixture; tidak mencatat isi exception atau data login.
            self.context.engine.navigation_errors.append({
                'url':url,'method':'GET','exception':type(error).__name__})
            raise
    def wait_for_timeout(self,ms):
        if self.context.engine.mode=='manual' and self.raw.url==LOGIN:
            self.goto(HOME,wait_until='domcontentloaded')
        else:self.raw.wait_for_timeout(ms)


class Context:
    def __init__(self,raw,engine):
        self.raw=raw;self.engine=engine;self.closed=False
        self.page=Page(raw.new_page(),self);self.pages=[self.page]
    def route(self,*args):return self.raw.route(*args)
    def close(self):self.closed=True;self.raw.close()


class Engine:
    def __init__(self,browser,mode,marker_delay_ms=250):
        self.browser=browser;self.mode=mode;self.chromium=self;self.contexts=[];self.posts=[]
        self.marker_delay_ms=marker_delay_ms;self.navigation_errors=[]
    def launch_persistent_context(self,path,**kwargs):
        raw=self.browser.new_context()
        def route(r):
            url=r.request.url
            if url==LOGIN:r.fulfill(body=FORM,content_type='text/html')
            elif url=='https://satu.intranet.pajak.go.id/session':
                self.posts.append(r.request.post_data)
                r.fulfill(body='<script>location.assign("'+HOME+'");</script>',content_type='text/html')
            elif url==HOME:r.fulfill(body='<h1>Synthetic Coretax home</h1>',content_type='text/html')
            elif url==SEARCH:r.fulfill(body='<script>setTimeout(()=>{document.body.innerHTML=\'<input id="ObjectPermitNumber">\';},'+str(self.marker_delay_ms)+');</script>',content_type='text/html')
            else:r.abort('blockedbyclient')
        raw.route('**/*',route)
        context=Context(raw,self);self.contexts.append(context)
        return context
