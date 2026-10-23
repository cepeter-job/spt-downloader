"""Download authentication retains inspected readiness, never real accounts."""
from contextlib import nullcontext
from pathlib import Path
import json

import pytest
from coretax_browser import CaptureCancelled
from spt_desktop import auth, controller, diagnostics, worker
from spt_desktop.credentials import Login
from support_login_browser import ASYNC_LOGIN_TIMEOUT, browser
from support_login_redirect import Engine, SATU, ACCOUNT, SECRET


def saved(monkeypatch):
    reads = []
    def read(origin):
        reads.append(origin)
        assert origin == SATU
        return Login(ACCOUNT, SECRET)
    monkeypatch.setattr(auth, 'read_login', read)
    return reads


def test_saved_login_waits_for_coretax_to_satu_before_inspection(browser, tmp_path, monkeypatch):
    engine = Engine(browser, entry=auth.SEARCH_URL)
    reads = saved(monkeypatch)
    context = engine.launch_persistent_context(tmp_path / 'synthetic-profile')
    try:
        context.page.goto(auth.SEARCH_URL)
        assert auth.try_saved_login(context.page, lambda: None)
        assert reads == [SATU] and len(engine.posts) == 1
        assert engine.unknown == []
    finally:
        context.close()


def test_named_account_download_needs_no_preliminary_check_or_manual_login(browser, tmp_path, monkeypatch):
    reads = saved(monkeypatch)
    download_engine = Engine(browser, entry=auth.SEARCH_URL)
    events = []
    context, page = auth.authenticate_owned(download_engine, tmp_path / 'new-profile',
        'msedge', True, lambda *args: events.append(args), lambda: None,
        manual_timeout=0, account=ACCOUNT)
    try:
        assert auth.authenticated(page)
        assert reads == [SATU]
        assert len(download_engine.posts) == 1
        assert not any(kind == 'login_required' for kind, message in events)
        assert len(download_engine.contexts) == 1 and not download_engine.unknown
    finally:
        context.close()


@pytest.mark.parametrize('headless', [False, True])
def test_owned_download_display_environment_reaches_real_edge(browser, tmp_path, monkeypatch, headless):
    from types import SimpleNamespace

    saved(monkeypatch)
    engine = Engine(browser, entry=auth.SEARCH_URL)
    original_launch = engine.launch_persistent_context
    def launch(profile, **options):
        # Deliberately conflicting defaults expose dependence on the host's
        # ambient environment. Forward only actual owned-launch options.
        environment = {'locale': 'en-US', 'timezone_id': 'UTC'}
        environment.update({key: options[key] for key in environment if key in options})
        engine.browser = SimpleNamespace(new_context=lambda: browser.new_context(**environment))
        try:
            return original_launch(profile, **options)
        finally:
            engine.browser = browser
    monkeypatch.setattr(engine, 'launch_persistent_context', launch)
    context, page = auth.authenticate_owned(engine, tmp_path / 'new-profile', 'msedge', headless,
        lambda *args: None, lambda: None, manual_timeout=0, account=ACCOUNT)
    try:
        assert auth.authenticated(page)
        assert page.evaluate('() => ({locale:navigator.language,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})') == {
            'locale': 'id-ID', 'timezone': 'Asia/Jakarta'}
        assert engine.unknown == []
    finally:
        context.close()


@pytest.mark.parametrize('account', ['', 'OTHER_SYNTHETIC_ACCOUNT'])
def test_missing_or_different_selected_account_never_autofills(browser, tmp_path, monkeypatch, account):
    reads = saved(monkeypatch)
    engine = Engine(browser, entry=auth.SEARCH_URL)
    context = engine.launch_persistent_context(tmp_path / 'profile')
    try:
        context.page.goto(auth.SEARCH_URL)
        assert not auth.try_saved_login(context.page, lambda: None, account=account)
        assert reads == ([] if account == '' else [SATU])
        assert engine.posts == []
        if account:
            assert context.page.locator('input[type=password]').input_value() == ''
    finally:
        context.close()


def test_unbound_sso_is_not_accepted_for_a_named_saved_account(browser, tmp_path, monkeypatch):
    reads = saved(monkeypatch)
    engine = Engine(browser, mode='sso', entry=auth.SEARCH_URL)
    with pytest.raises(auth.AuthBlocked):
        auth.authenticate_owned(engine, tmp_path / 'fresh', 'msedge', True,
            lambda *args: None, lambda: None, manual_timeout=0, account=ACCOUNT)
    assert reads == [] and engine.posts == []
    assert all(c.closed for c in engine.contexts)


def test_export_controller_passes_account_without_any_password(tmp_path, monkeypatch):
    captured = []
    ctl = controller.JobController(tmp_path, lambda event: None)
    monkeypatch.setattr(ctl, '_start_worker', lambda *args: captured.append(args) or 'synthetic-job')
    assert ctl.start('0000000000000001', '2025', account=ACCOUNT) == 'synthetic-job'
    arguments = captured[0][0]
    assert arguments[arguments.index('--account') + 1] == ACCOUNT
    assert '--origin' not in arguments and SECRET not in repr(captured)


def test_named_account_worker_never_reuses_unknown_profile_and_cleans_temp(tmp_path, monkeypatch):
    old = tmp_path / 'profile'; old.mkdir()
    sentinel = old / 'SYNTHETIC_UNKNOWN_SESSION'; sentinel.write_text('preserve')
    observed = []; messages = []
    monkeypatch.setattr(worker, 'playwright_factory', lambda: nullcontext(object()))
    def authenticate(playwright, profile, *args, **kwargs):
        observed.append((Path(profile), kwargs))
        assert Path(profile).is_dir() and Path(profile) != old
        raise CaptureCancelled('synthetic stop before capture')
    monkeypatch.setattr(worker, 'authenticate_owned', authenticate)
    result = worker.run_job('0000000000000001', 2025, tmp_path, 'synthetic-named',
        'msedge', True, messages.append, lambda: False, account=ACCOUNT)
    assert result == 4 and messages[-1]['status'] == 'CANCELLED'
    assert len(observed) == 1 and observed[0][1]['account'] == ACCOUNT
    assert not observed[0][0].exists() and sentinel.read_text() == 'preserve'


@pytest.mark.parametrize('account', [' ', 'x' * 257, 'synthetic\0account'])
def test_worker_rejects_invalid_export_account_before_authorization(tmp_path, monkeypatch, account):
    entered = []
    monkeypatch.setattr(worker, '_authorized', lambda args: entered.append(args) or 0)
    result = worker.main(['--npwp', '0000000000000001', '--year', '2025',
        '--root', str(tmp_path), '--job-id', 'synthetic-invalid', '--account', account])
    assert result == 1 and entered == []





@pytest.mark.parametrize('field', ['target_origin', 'method', 'resource_type', 'request_kind'])
def test_network_diagnostic_categories_reject_arbitrary_values(tmp_path, field):
    private = 'SYNTHETIC_PRIVATE_VALUE'
    with diagnostics.session(tmp_path, 'worker') as log:
        assert diagnostics.record('auth.request_blocked', reason='cross_origin_write',
            target_origin='coretax', method='POST', resource_type='fetch')
        assert diagnostics.record('auth.request_blocked', **{field: private}, url=private, body=private)
        assert log.flush()
    text = '\n'.join(p.read_text(encoding='utf-8') for p in (tmp_path / 'logs').glob('*.jsonl'))
    rows = [json.loads(line) for line in text.splitlines()]
    blocked = [r for r in rows if r['event'] == 'auth.request_blocked']
    assert len(blocked) == 2 and blocked[0]['method'] == 'POST'
    assert field not in blocked[1] and private not in text
