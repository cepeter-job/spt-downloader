"""Post-login home is a navigation cue, never proof of authenticated search."""
import pytest
from spt_desktop import auth

HOME='https://coretax.intranet.pajak.go.id/home/id-ID/'


class Marker:
    def __init__(self,page):self.page=page
    def count(self):return int(self.page.ready)


class Page:
    def __init__(self,url=HOME,ready_after=True):
        self.url=url;self.ready=False;self.ready_after=ready_after;self.navigations=[];self.waits=[]
    def locator(self,selector):
        assert selector=='#ObjectPermitNumber:visible'
        return Marker(self)
    def goto(self,url,**kwargs):
        self.navigations.append(url)
        if self.ready_after:self.url=url;self.ready=True
    def wait_for_timeout(self,ms):self.waits.append(ms)


def clock(monkeypatch):
    ticks=iter([0.0,0.0,0.0,0.0,1.0,2.0,3.0,4.0,5.0,6.0,7.0])
    monkeypatch.setattr(auth.time,'monotonic',lambda:next(ticks))


def test_manual_home_opens_only_known_search_and_finishes_immediately(monkeypatch):
    clock(monkeypatch);page=Page();events=[]
    assert auth._wait_ready(page,4,lambda:None,emit=lambda *args:events.append(args))
    assert page.navigations==[auth.SEARCH_URL]
    assert page.waits==[]
    assert any('Pencarian WP' in message for stage,message in events)


def test_home_alone_is_not_login_success_and_never_navigation_loop(monkeypatch):
    clock(monkeypatch);page=Page(ready_after=False)
    assert not auth._wait_ready(page,4,lambda:None)
    assert page.navigations==[auth.SEARCH_URL]


@pytest.mark.parametrize('url',['https://satu.intranet.pajak.go.id/login','https://example.com/home/id-ID/',
    'https://coretax.intranet.pajak.go.id/returnsheets/id-ID/unrecognized',
    'https://coretax.intranet.pajak.go.id/registration/id-ID/',
    'https://coretax.intranet.pajak.go.id/home/unknown/'])
def test_unknown_login_or_application_page_never_guesses_navigation(monkeypatch,url):
    clock(monkeypatch);page=Page(url=url)
    assert not auth._wait_ready(page,4,lambda:None)
    assert page.navigations==[]


def test_already_ready_search_is_reused_without_navigation(monkeypatch):
    clock(monkeypatch);page=Page(url=auth.SEARCH_URL);page.ready=True
    assert auth._wait_ready(page,4,lambda:None)
    assert page.navigations==[]


def test_cancellation_prevents_home_navigation(monkeypatch):
    from coretax_browser import CaptureCancelled
    clock(monkeypatch);page=Page()
    def stop():raise CaptureCancelled('synthetic stop')
    with pytest.raises(CaptureCancelled):auth._wait_ready(page,4,stop)
    assert page.navigations==[]
