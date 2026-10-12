"""Credential checks use intercepted synthetic pages, never a live account."""
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


def check_function():
    assert hasattr(auth,'check_saved_credentials'), 'Cek Kredensial does not exist'
    return auth.check_saved_credentials


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


def saved(monkeypatch):
    reads=[]
    monkeypatch.setattr(auth,'read_login',lambda origin:(reads.append(origin) or Login(ACCOUNT,SECRET)))
    return reads


def run_check(browser,tmp_path,monkeypatch,mode='success',form=FORM,origin=ORIGIN,account=ACCOUNT,cancelled=lambda:None):
    function=check_function()
    monkeypatch.setattr(auth,'SEARCH_URL',READY_URL if mode=='already' else ORIGIN+'/login')
    engine=RoutedPlaywright(browser,mode,form)
    reads=saved(monkeypatch)
    status,message=function(engine,tmp_path,origin,account,'msedge',True,cancelled,timeout=0.4 if mode=='reject' else 5)
    assert all(not context.pages for context in engine.contexts)
    assert all(not path.exists() for path in engine.paths)
    assert not (tmp_path/'profile').exists()
    assert SECRET not in message and ACCOUNT not in message
    return status,message,engine,reads


def test_saved_password_verified_only_after_one_real_form_submission(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch)
    assert status=='LOGIN_OK' and 'Login berhasil' in message
    assert reads==[ORIGIN] and len(engine.posts)==1
    assert 'username=SYNTHETIC_ACCOUNT' in engine.posts[0]
    assert 'password=SYNTHETIC_PASSWORD_ONLY' in engine.posts[0]


def test_already_authenticated_sso_does_not_certify_saved_password(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,mode='already')
    assert status=='LOGIN_UNVERIFIED' and 'belum diuji' in message
    assert reads==[] and engine.posts==[]


def test_timeout_is_not_wrong_password_and_never_retries(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,mode='reject')
    assert status=='LOGIN_UNVERIFIED' and 'belum terverifikasi' in message
    assert len(engine.posts)==1 and reads==[ORIGIN]
    assert 'password salah' not in message.lower()


@pytest.mark.parametrize('form',[FORM+'<input id="captcha">',FORM+'<input autocomplete="one-time-code">'])
def test_challenge_requires_manual_without_reading_password(browser,tmp_path,monkeypatch,form):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,form=form)
    assert status=='LOGIN_MANUAL' and 'CAPTCHA/MFA' in message
    assert reads==[] and engine.posts==[]


def test_post_password_mfa_is_not_success(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,mode='challenge')
    assert status=='LOGIN_MANUAL' and len(engine.posts)==1


def test_origin_mismatch_does_not_read_any_password(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,origin=auth.CORETAX_ORIGIN)
    assert status=='LOGIN_BLOCKED' and 'Origin' in message
    assert ORIGIN in message and reads==[] and engine.posts==[]


def test_saved_account_mismatch_never_submits(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,account='OTHER_SYNTHETIC_ACCOUNT')
    assert status=='LOGIN_BLOCKED' and 'Akun' in message
    assert reads==[ORIGIN] and engine.posts==[]


def test_missing_credential_has_explicit_status(browser,tmp_path,monkeypatch):
    function=check_function();engine=RoutedPlaywright(browser)
    monkeypatch.setattr(auth,'SEARCH_URL',ORIGIN+'/login')
    monkeypatch.setattr(auth,'read_login',lambda origin:None)
    status,message=function(engine,tmp_path,ORIGIN,ACCOUNT,'msedge',True,lambda:None,timeout=0.4)
    assert status=='LOGIN_BLOCKED' and 'belum disimpan' in message
    assert not engine.posts and all(not context.pages for context in engine.contexts)


def test_unknown_layout_does_not_read_or_guess_submit(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,form=FORM.replace('>Login<','>Submit SPT<'))
    assert status=='LOGIN_MANUAL' and 'Form' in message
    assert reads==[] and engine.posts==[]


def test_same_origin_formaction_tax_submit_never_reads_password(browser,tmp_path,monkeypatch):
    html=FORM.replace('<button type="submit"','<button formaction="/returnsheets/submit" type="submit"')
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,form=html)
    assert status=='LOGIN_MANUAL' and reads==[] and not engine.posts


def test_network_failure_is_distinct_and_secret_free(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,mode='network')
    assert status=='LOGIN_ERROR' and 'koneksi' in message.lower() and reads==[]


def test_cancelled_check_closes_fresh_context_and_removes_owned_profile(browser,tmp_path,monkeypatch):
    from coretax_browser import CaptureCancelled
    function=check_function();engine=RoutedPlaywright(browser,mode='reject');saved(monkeypatch)
    monkeypatch.setattr(auth,'SEARCH_URL',ORIGIN+'/login')
    def cancelled():
        if engine.posts:raise CaptureCancelled('synthetic cancellation')
    with pytest.raises(CaptureCancelled):
        function(engine,tmp_path,ORIGIN,ACCOUNT,'msedge',True,cancelled,timeout=1)
    assert all(not context.pages for context in engine.contexts)
    assert all(not path.exists() for path in engine.paths)


def test_every_check_uses_a_new_profile(browser,tmp_path,monkeypatch):
    function=check_function();engine=RoutedPlaywright(browser);saved(monkeypatch)
    monkeypatch.setattr(auth,'SEARCH_URL',ORIGIN+'/login')
    for _ in range(2):
        assert function(engine,tmp_path,ORIGIN,ACCOUNT,'msedge',True,lambda:None,timeout=5)[0]=='LOGIN_OK'
    assert len(set(engine.paths))==2


def test_compound_masuk_button_still_logs_in_automatically(browser,tmp_path,monkeypatch):
    form=FORM.replace('>Login</button>','><span class="indicator-label">Masuk</span><span class="indicator-progress">Please wait...</span></button>')
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,form=form)
    assert status=='LOGIN_OK' and len(engine.posts)==1 and reads==[ORIGIN]



@pytest.mark.parametrize('failure',['read','fill','click'])
def test_internal_secret_bearing_errors_never_reach_result(browser,tmp_path,monkeypatch,failure):
    function=check_function();engine=RoutedPlaywright(browser)
    monkeypatch.setattr(auth,'SEARCH_URL',ORIGIN+'/login')
    def unsafe_error(*args,**kwargs):raise RuntimeError(ACCOUNT+' '+SECRET+' synthetic private call log')
    if failure=='read':monkeypatch.setattr(auth,'read_login',unsafe_error)
    else:
        saved(monkeypatch)
        original=auth._login_fields
        class Broken:
            fill=unsafe_error
            click=unsafe_error
        def controls(page):
            origin,identifier,password,button=original(page)
            return (origin,Broken(),password,button) if failure=='fill' else (origin,identifier,password,Broken())
        monkeypatch.setattr(auth,'_login_fields',controls)
    status,message=function(engine,tmp_path,ORIGIN,ACCOUNT,'msedge',True,lambda:None,timeout=0.4)
    assert status=='LOGIN_ERROR'
    assert SECRET not in message and ACCOUNT not in message and 'private call log' not in message
    assert all(not context.pages for context in engine.contexts)
    assert all(not path.exists() for path in engine.paths)


def test_asynchronous_success_is_not_bound_to_a_subsecond_fixture_deadline(browser,tmp_path,monkeypatch):
    status,message,engine,reads=run_check(browser,tmp_path,monkeypatch,mode='slow_success')
    assert status=='LOGIN_OK' and len(engine.posts)==1 and reads==[ORIGIN]
