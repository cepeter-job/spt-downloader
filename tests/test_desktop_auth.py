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
