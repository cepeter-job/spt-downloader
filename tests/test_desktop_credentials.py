"""Credential tests mock native storage; they never read real saved accounts."""
import importlib
import importlib.util
import pytest

ORIGIN = 'https://satu.intranet.pajak.go.id'
OTHER = 'https://coretax.intranet.pajak.go.id'


def module():
    assert importlib.util.find_spec('spt_desktop'), 'Desktop credential package is not implemented'
    return importlib.import_module('spt_desktop.credentials')


@pytest.fixture
def vault(monkeypatch):
    if importlib.util.find_spec('spt_desktop') is None:
        return None
    credentials = module()
    values = {}
    monkeypatch.setattr(credentials, '_write_credential',
                        lambda target, username, blob: values.__setitem__(target, (username, blob)))
    monkeypatch.setattr(credentials, '_read_credential', lambda target: values.get(target))
    monkeypatch.setattr(credentials, '_delete_credential', lambda target: values.pop(target, None))
    return credentials


def test_saved_login_round_trips_without_reading_unrelated_origins(vault):
    assert vault is not None, 'Desktop credential implementation is missing'
    vault.save_login(ORIGIN, 'synthetic-user', 'synthetic-password-日本')
    login = vault.read_login(ORIGIN)
    assert login.identifier == 'synthetic-user'
    assert login.password == 'synthetic-password-日本'
    assert vault.read_login(OTHER) is None
    assert 'synthetic-password' not in repr(login)


def test_removing_application_login_is_idempotent(vault):
    assert vault is not None, 'Desktop credential implementation is missing'
    vault.save_login(ORIGIN, 'synthetic-user', 'synthetic-password')
    vault.delete_login(ORIGIN)
    vault.delete_login(ORIGIN)
    assert vault.read_login(ORIGIN) is None


@pytest.mark.parametrize('origin', [
    'http://satu.intranet.pajak.go.id',
    'https://satu.intranet.pajak.go.id.evil.test',
    'https://satu.intranet.pajak.go.id/login',
    'https://user@satu.intranet.pajak.go.id',
    'https://example.test',
])
def test_credential_binding_rejects_nonexact_origin(vault, origin):
    assert vault is not None, 'Desktop credential implementation is missing'
    for operation in [lambda: vault.save_login(origin, 'synthetic-user', 'synthetic-password'),
                      lambda: vault.read_login(origin), lambda: vault.delete_login(origin)]:
        with pytest.raises(ValueError, match='origin'):
            operation()


@pytest.mark.parametrize('identifier,password', [('', 'fixture'), ('user', ''),
                                                ('user\x00tail', 'fixture'), ('user', 'fixture\x00tail'),
                                                ('user', '日本' * 2000)],
                         ids=['empty-user', 'empty-password', 'null-user', 'null-password', 'oversize-password'])
def test_invalid_credential_is_rejected_before_native_write(vault, identifier, password):
    assert vault is not None, 'Desktop credential implementation is missing'
    with pytest.raises(ValueError):
        vault.save_login(ORIGIN, identifier, password)
    assert vault.read_login(ORIGIN) is None
