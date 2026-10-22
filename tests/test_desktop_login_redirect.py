"""Normal download redirects use only routed synthetic pages and credentials."""
import json
import pytest
from spt_desktop import auth, diagnostics
from spt_desktop.credentials import Login
from support_login_browser import browser
from support_login_redirect import SATU, ACCOUNT, SECRET, ENTRY, Engine


def run_download_login(browser, tmp_path, monkeypatch, *, mode='success', entry=ENTRY):
    engine = Engine(browser, mode, entry)
    monkeypatch.setattr(auth, 'SEARCH_URL', entry)
    reads, messages = [], []
    def saved(origin):
        reads.append(origin)
        if mode == 'missing':
            return None
        if mode == 'error':
            raise RuntimeError(SECRET + ' cookie=SYNTHETIC_COOKIE_ONLY')
        return Login('OTHER_SYNTHETIC_ACCOUNT' if mode == 'account' else ACCOUNT, SECRET)
    monkeypatch.setattr(auth, 'read_login', saved)
    if mode in ('reject', 'stalled'):
        wait = auth._wait_ready
        monkeypatch.setattr(auth, '_wait_ready', lambda page, deadline, cancel, emit=None:
            wait(page, auth.time.monotonic() + 0.2, cancel, emit=emit))
    if mode == 'stalled':
        # Only this case tests a pre-form timeout. Rejection must reach the
        # inspected form and submit once before its short verification window.
        login_ready = auth._wait_login_ready
        monkeypatch.setattr(auth, '_wait_login_ready', lambda page, origin, cancel, timeout, observe:
            login_ready(page, origin, cancel, 0.2, observe))
    def cancel():
        if mode == 'cancelled' and engine.contexts and engine.contexts[-1].page.waits:
            from coretax_browser import CaptureCancelled
            raise CaptureCancelled('synthetic stop')
    root = tmp_path / 'diagnostics'
    with diagnostics.session(root, 'worker', job_id='synthetic-download-login') as log:
        try:
            context, page = auth.authenticate_owned(engine, tmp_path / 'profile', 'msedge', False,
                lambda *args: messages.append(args), cancel, manual_timeout=0, account=ACCOUNT)
        except auth.AuthBlocked as error:
            ready, message = False, str(error)
        else:
            try:
                ready, message = auth.authenticated(page), ''
            finally:
                context.close()
        finally:
            assert all(context.closed for context in engine.contexts)
            assert engine.unknown == []
            assert log.flush()
    text = '\n'.join(p.read_text(encoding='utf-8') for p in (root / 'logs').glob('*.jsonl'))
    for forbidden in (ACCOUNT, SECRET, 'SYNTHETIC_CSRF_ONLY', 'SYNTHETIC_TOKEN_ONLY',
                      'SYNTHETIC_COOKIE_ONLY', SATU, auth.CORETAX_ORIGIN, 'cookie='):
        assert forbidden not in text and forbidden not in message and forbidden not in repr(messages)
    assert all(row.get('operation') != 'login_check' for row in map(json.loads, text.splitlines()))
    return ready, message, engine, reads, messages


@pytest.mark.parametrize('entry', [ENTRY, auth.SEARCH_URL])
def test_download_waits_for_real_satu_redirect_before_one_login(browser, tmp_path, monkeypatch, entry):
    ready, message, engine, reads, messages = run_download_login(browser, tmp_path, monkeypatch, entry=entry)
    assert ready and reads == [SATU] and len(engine.posts) == 1
    assert 'username=SYNTHETIC_ACCOUNT' in engine.posts[0]
    assert not messages


@pytest.mark.parametrize('mode,read_count,post_count', [
    ('challenge', 0, 0), ('unsafe', 0, 0), ('stalled', 0, 0), ('sso', 0, 0),
    ('missing', 1, 0), ('account', 1, 0), ('error', 1, 0), ('reject', 1, 1),
])
def test_download_redirect_failure_never_retries_or_leaks_credentials(browser, tmp_path, monkeypatch, mode, read_count, post_count):
    ready, message, engine, reads, messages = run_download_login(browser, tmp_path, monkeypatch, mode=mode)
    assert not ready and len(reads) == read_count and len(engine.posts) == post_count
    assert 'password salah' not in message.lower()
    if mode != 'sso':
        assert any(kind == 'login_required' for kind, _ in messages)


def test_stop_during_download_redirect_wait_never_reads_credential(browser, tmp_path, monkeypatch):
    from coretax_browser import CaptureCancelled
    with pytest.raises(CaptureCancelled):
        run_download_login(browser, tmp_path, monkeypatch, mode='cancelled')
