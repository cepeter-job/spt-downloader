"""A delayed already-supported form, not an invented portal/login selector."""

import pytest

from spt_desktop import auth
from spt_desktop.credentials import Login
import support_login_browser as flow

# Reuse the real routed Edge fixture; every non-fixture request is aborted.
browser = flow.browser


@pytest.mark.parametrize('operation', ['check', 'export'])
def test_supported_async_form_is_ready_before_any_credential_read(browser, tmp_path, monkeypatch, operation):
    known_form = flow.FORM
    monkeypatch.setattr(flow, 'FORM', '<main>SYNTHETIC LOGIN SHELL; NO FORM YET</main>')
    engine = flow.Engine(browser, 'saved', marker_delay_ms=250)
    polls = []
    scheduled = []
    reads = []
    original_fields = auth._login_fields

    def inspect_and_schedule_known_form(page):
        fields = original_fields(page)
        polls.append('ready' if fields is not None else 'pending')
        if fields is None and page.url == flow.LOGIN and not scheduled:
            # The first real inspection MUST see the incomplete DOM. Schedule
            # its supported form afterwards, so slow CI cannot erase the race.
            scheduled.append(page.url)
            page.evaluate('(form)=>setTimeout(()=>{document.body.innerHTML=form;},20)', known_form)
        return fields

    def saved_login(origin):
        reads.append((origin, polls[-1]))
        assert polls[-1] == 'ready', 'Credentials must not be read for an incomplete form'
        return Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY')

    monkeypatch.setattr(auth, '_login_fields', inspect_and_schedule_known_form)
    monkeypatch.setattr(auth, 'read_login', saved_login)
    if operation == 'check':
        status, message = auth.check_saved_credentials(
            engine, tmp_path, auth.ALLOWED_ORIGINS[0], 'SYNTHETIC_ACCOUNT',
            'msedge', True, lambda: None, timeout=flow.ASYNC_LOGIN_TIMEOUT)
        assert status == 'LOGIN_OK', (status, engine.navigation_errors)
        assert 'SYNTHETIC_PASSWORD_ONLY' not in message
    else:
        events = []
        context, page = auth.authenticate_owned(
            engine, tmp_path / 'profile', 'msedge', True,
            lambda *args: events.append(args), lambda: None, manual_timeout=1)
        try:
            assert page.url == flow.SEARCH and auth.authenticated(page)
            assert not any(kind == 'login_required' for kind, _ in events), (
                'A supported delayed form must not fall back to manual authentication')
            assert len(engine.contexts) == 1
        finally:
            context.close()
    assert scheduled == [flow.LOGIN] and polls[0] == 'pending' and 'ready' in polls
    assert reads == [(auth.ALLOWED_ORIGINS[0], 'ready')]
    assert len(engine.posts) == 1, 'No credential retries or duplicate submissions are authorized'
    assert all(context.closed for context in engine.contexts)
