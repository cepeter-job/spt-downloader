"""The reported Satu->Coretax-home flow is reproduced with synthetic routes."""
import pytest
from playwright.sync_api import sync_playwright
from spt_desktop import auth
from spt_desktop.credentials import Login

from support_login_browser import (
    ASYNC_LOGIN_TIMEOUT, Context, Engine, FORM, HOME, LOGIN, Page, SEARCH, browser
)

# Alur sukses memberi ruang penjadwalan CI; batas waktu/Stop diuji dengan jam simulasi.
@pytest.mark.parametrize('marker_delay_ms',[250,3500])
def test_manual_satu_login_to_home_proceeds_without_five_minute_wait(browser,tmp_path,monkeypatch,marker_delay_ms):
    monkeypatch.setattr(auth,'try_saved_login',lambda *args:False)
    engine=Engine(browser,'manual',marker_delay_ms);events=[]
    context,page=auth.authenticate_owned(engine,tmp_path/'profile','msedge',False,
        lambda *args:events.append(args),lambda:None,manual_timeout=ASYNC_LOGIN_TIMEOUT)
    try:
        assert page.url==SEARCH and auth.authenticated(page)
        assert any('Pencarian WP' in message for kind,message in events)
        assert engine.posts==[]
    finally:context.close()
    assert all(context.closed for context in engine.contexts)


def test_manual_home_then_headless_restore_reuses_verified_search(browser,tmp_path,monkeypatch):
    monkeypatch.setattr(auth,'try_saved_login',lambda *args:False)
    engine=Engine(browser,'manual')
    context,page=auth.authenticate_owned(engine,tmp_path/'profile','msedge',True,lambda *args:None,lambda:None,manual_timeout=ASYNC_LOGIN_TIMEOUT)
    try:
        assert page.url==SEARCH and auth.authenticated(page)
        assert len(engine.contexts)==3
    finally:context.close()
    assert all(context.closed for context in engine.contexts)


@pytest.mark.parametrize('marker_delay_ms',[250,3500])
def test_saved_password_post_to_home_is_verified_by_check_without_retry(browser,tmp_path,monkeypatch,marker_delay_ms):
    engine=Engine(browser,'saved',marker_delay_ms)
    monkeypatch.setattr(auth,'read_login',lambda origin:Login('SYNTHETIC_ACCOUNT','SYNTHETIC_PASSWORD_ONLY'))
    verified_searches=[]
    original_authenticated=auth.authenticated
    def observe_authenticated(page):
        verified=original_authenticated(page)
        if verified:verified_searches.append(page.url)
        return verified
    monkeypatch.setattr(auth,'authenticated',observe_authenticated)
    status,message=auth.check_saved_credentials(engine,tmp_path,auth.ALLOWED_ORIGINS[0],'SYNTHETIC_ACCOUNT','msedge',True,lambda:None,timeout=ASYNC_LOGIN_TIMEOUT)
    assert status=='LOGIN_OK', (status,engine.navigation_errors)
    assert len(engine.posts)==1 and verified_searches==[SEARCH]
    assert 'SYNTHETIC_PASSWORD_ONLY' not in message
    assert all(context.closed for context in engine.contexts)


def test_sso_home_before_password_submission_does_not_certify_saved_password(browser,tmp_path,monkeypatch):
    engine=Engine(browser,'sso_home');reads=[]
    monkeypatch.setattr(auth,'read_login',lambda origin:reads.append(origin))
    status,message=auth.check_saved_credentials(engine,tmp_path,auth.ALLOWED_ORIGINS[0],'SYNTHETIC_ACCOUNT','msedge',True,lambda:None,timeout=ASYNC_LOGIN_TIMEOUT)
    assert status=='LOGIN_UNVERIFIED' and 'belum diuji' in message
    assert reads==[] and engine.posts==[] and all(context.closed for context in engine.contexts)
