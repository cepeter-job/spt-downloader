"""Owned driver startup policy; synthetic managers and environment only."""
import importlib
import os
import threading

import pytest

from test_cli_failure_recovery import cli as cli


def policy(monkeypatch, platform='win32'):
    module = importlib.import_module('coretax_transport')
    monkeypatch.setattr(module.sys, 'platform', platform)
    monkeypatch.delenv('NODE_USE_SYSTEM_CA', raising=False)
    return module


class Manager:
    def __init__(self, enter=None, exit_result=False):
        self.observed = []
        self.enter = enter
        self.exit_result = exit_result
        self.exit_args = None

    def __enter__(self):
        self.observed.append(os.environ.get('NODE_USE_SYSTEM_CA'))
        return self.enter() if self.enter else self

    def __exit__(self, *args):
        self.exit_args = args
        return self.exit_result


def test_windows_defaults_native_ca_only_during_owned_entry(monkeypatch):
    module = policy(monkeypatch)
    target = Manager()
    wrapper = module.system_ca_manager(target)
    assert 'NODE_USE_SYSTEM_CA' not in os.environ
    assert wrapper.__enter__() is target
    assert target.observed == ['1']
    assert 'NODE_USE_SYSTEM_CA' not in os.environ
    error = ValueError('SYNTHETIC')
    assert wrapper.__exit__(ValueError, error, None) is False
    assert target.exit_args == (ValueError, error, None)


@pytest.mark.parametrize('explicit', ['', '0', '1', 'SYNTHETIC-EXPLICIT'])
def test_explicit_policy_is_never_rewritten(monkeypatch, explicit):
    module = policy(monkeypatch)
    monkeypatch.setenv('NODE_USE_SYSTEM_CA', explicit)
    target = Manager()
    with module.system_ca_manager(target):
        assert os.environ['NODE_USE_SYSTEM_CA'] == explicit
    assert target.observed == [explicit]
    assert os.environ['NODE_USE_SYSTEM_CA'] == explicit


@pytest.mark.parametrize('platform', ['linux', 'darwin'])
def test_other_platforms_keep_their_existing_default(monkeypatch, platform):
    module = policy(monkeypatch, platform)
    target = Manager()
    with module.system_ca_manager(target):
        assert 'NODE_USE_SYSTEM_CA' not in os.environ
    assert target.observed == [None]


@pytest.mark.parametrize('failure', [RuntimeError, KeyboardInterrupt])
def test_failed_entry_restores_environment_and_keeps_cleanup_available(monkeypatch, failure):
    module = policy(monkeypatch)
    def fail():
        raise failure('SYNTHETIC STARTUP')
    target = Manager(enter=fail)
    wrapper = module.system_ca_manager(target)
    with pytest.raises(failure):
        wrapper.__enter__()
    assert 'NODE_USE_SYSTEM_CA' not in os.environ
    wrapper.__exit__(None, None, None)
    assert target.exit_args == (None, None, None)


def test_caller_update_during_entry_is_preserved(monkeypatch):
    module = policy(monkeypatch)
    def change():
        os.environ['NODE_USE_SYSTEM_CA'] = '0'
        return 'SYNTHETIC RESOURCE'
    target = Manager(enter=change)
    assert module.system_ca_manager(target).__enter__() == 'SYNTHETIC RESOURCE'
    assert os.environ['NODE_USE_SYSTEM_CA'] == '0'


def test_nested_starts_keep_the_outer_default_until_its_entry_finishes(monkeypatch):
    module = policy(monkeypatch)
    inner = Manager()
    def enter_outer():
        assert module.system_ca_manager(inner).__enter__() is inner
        assert os.environ['NODE_USE_SYSTEM_CA'] == '1'
        return 'OUTER'
    assert module.system_ca_manager(Manager(enter=enter_outer)).__enter__() == 'OUTER'
    assert inner.observed == ['1'] and 'NODE_USE_SYSTEM_CA' not in os.environ


def test_exit_suppression_contract_is_forwarded(monkeypatch):
    module = policy(monkeypatch)
    target = Manager(exit_result=True)
    with module.system_ca_manager(target):
        raise ValueError('SYNTHETIC SUPPRESSED')
    assert target.exit_args[0] is ValueError


def test_concurrent_starts_cannot_lose_the_temporary_default(monkeypatch):
    module = policy(monkeypatch)
    first_entered, first_release = threading.Event(), threading.Event()
    second_started, second_entered = threading.Event(), threading.Event()
    errors, seen = [], []
    def enter_first():
        first_entered.set()
        assert first_release.wait(3)
    def enter_second():
        seen.append(os.environ.get('NODE_USE_SYSTEM_CA'))
        second_entered.set()
    def run(manager, started=None):
        try:
            if started:
                started.set()
            module.system_ca_manager(manager).__enter__()
        except BaseException as error:
            errors.append(type(error).__name__)
    one = threading.Thread(target=run, args=(Manager(enter_first),))
    two = threading.Thread(target=run, args=(Manager(enter_second), second_started))
    one.start()
    try:
        assert first_entered.wait(3)
        two.start()
        assert second_started.wait(3)
        assert not second_entered.wait(.1)
    finally:
        first_release.set()
        one.join(3)
        if two.ident is not None:
            two.join(3)
    assert not one.is_alive() and not two.is_alive() and not errors
    assert seen == ['1'] and 'NODE_USE_SYSTEM_CA' not in os.environ


def test_unrelated_network_settings_remain_unchanged(monkeypatch):
    module = policy(monkeypatch)
    settings = {'NODE_TLS_REJECT_UNAUTHORIZED': '1', 'NODE_EXTRA_CA_CERTS': 'SYNTHETIC CA.pem',
                'HTTPS_PROXY': '', 'NODE_OPTIONS': '--SYNTHETIC-OPTION'}
    for key, value in settings.items():
        monkeypatch.setenv(key, value)
    with module.system_ca_manager(Manager()):
        assert {key: os.environ[key] for key in settings} == settings
    assert {key: os.environ[key] for key in settings} == settings


def test_cli_local_factory_and_partial_driver_cleanup_keep_native_trust(cli, monkeypatch):
    import coretax
    policy(monkeypatch)
    seen = []
    class PartialDriver:
        def __enter__(self):
            seen.append(os.environ.get('NODE_USE_SYSTEM_CA'))
            raise RuntimeError('SYNTHETIC PARTIAL DRIVER')
        def __exit__(self, *args):
            cli.closed.append('driver')
    monkeypatch.setattr(coretax, 'sync_playwright', PartialDriver)
    assert cli.invoke() == 1
    assert seen == ['1'] and cli.closed == ['driver']
    assert 'NODE_USE_SYSTEM_CA' not in os.environ


def test_desktop_local_factory_receives_native_trust_and_restores_it(tmp_path, monkeypatch):
    from spt_desktop import worker
    from spt_desktop.auth import AuthBlocked
    policy(monkeypatch)
    target = Manager()
    monkeypatch.setattr(worker, 'playwright_factory', lambda: target)
    def refuse(*args, **kwargs):
        raise AuthBlocked('SYNTHETIC AUTH REFUSAL')
    monkeypatch.setattr(worker, 'authenticate_owned', refuse)
    code = worker.run_job('0000000000000001', 2025, tmp_path, 'synthetic-trust-job',
                          'msedge', True, lambda event: None, lambda: False)
    assert code == 3 and target.observed == ['1']
    assert target.exit_args is not None and 'NODE_USE_SYSTEM_CA' not in os.environ


def test_worker_allowlist_contains_the_shared_trust_owner():
    from spt_desktop.runtime import WORKER_FILES
    assert 'coretax_transport.py' in WORKER_FILES
