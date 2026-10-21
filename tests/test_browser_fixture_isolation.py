"""Isolasi context sintetis tetap berlaku saat proses browser dipakai ulang."""
import pytest

from support_isolated_browser import browser, isolated_context


ORIGIN = 'https://browser-fixture.synthetic.invalid'


def test_failed_case_closes_popups_and_does_not_leak_context_state(browser):
    old_requests = []

    def old_route(route):
        old_requests.append(route.request.url)
        route.fulfill(body='<title>Old context</title>', content_type='text/html')

    with pytest.raises(RuntimeError, match='synthetic case failure'):
        with isolated_context(browser) as previous:
            previous.route('**/*', old_route)
            page = previous.new_page()
            page.goto(ORIGIN + '/state')
            page.evaluate("""() => {
                document.cookie = 'fixture=old; path=/';
                localStorage.setItem('fixture', 'old');
                sessionStorage.setItem('fixture', 'old');
            }""")
            assert page.evaluate("""() => [
                document.cookie, localStorage.getItem('fixture'),
                sessionStorage.getItem('fixture')
            ]""") == ['fixture=old', 'old', 'old']
            with page.expect_popup() as pending:
                page.evaluate('(url) => { window.open(url); }', ORIGIN + '/popup')
            popup = pending.value
            popup.wait_for_load_state('load')
            assert len(previous.pages) == 2
            raise RuntimeError('synthetic case failure')

    assert page.is_closed() and popup.is_closed()
    assert previous not in browser.contexts
    assert browser.contexts == [] and browser.is_connected()
    old_request_count = len(old_requests)

    with isolated_context(browser) as fresh:
        assert fresh is not previous and fresh.cookies() == []
        fresh.route('**/*', lambda route: route.fulfill(
            body='<title>Fresh context</title>', content_type='text/html'))
        fresh_page = fresh.new_page()
        fresh_page.goto(ORIGIN + '/state')
        assert fresh_page.title() == 'Fresh context'
        assert fresh.pages == [fresh_page]
        assert fresh_page.evaluate("""() => [
            document.cookie, localStorage.getItem('fixture'),
            sessionStorage.getItem('fixture')
        ]""") == ['', None, None]
        assert len(old_requests) == old_request_count

    assert fresh_page.is_closed()
    assert browser.contexts == [] and browser.is_connected()
