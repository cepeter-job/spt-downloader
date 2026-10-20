"""Regenerasi lock tidak boleh mengubah pin ketika pemeriksaan atau resolusi gagal."""
import importlib
from pathlib import Path
import subprocess

import pytest


@pytest.fixture
def locks(tmp_path, monkeypatch):
    updater = importlib.import_module('scripts.update_locks')
    (tmp_path / 'locks').mkdir()
    for name in ('runtime', 'test', 'build', 'audit'):
        (tmp_path / 'locks' / f'{name}.txt').write_text('pin semula\n', encoding='utf-8')
    state = {'payload': 'pin semula\n', 'fail': None, 'commands': []}

    def resolve(command, **kwargs):
        if '--version' in command:
            return subprocess.CompletedProcess(command, 0, f'uv {updater.UV_VERSION} (synthetic)\n')
        state['commands'].append(command)
        output = Path(command[command.index('--output-file') + 1])
        if output.stem == state['fail']:
            raise subprocess.CalledProcessError(1, command)
        output.write_text(state['payload'], encoding='utf-8')
        return subprocess.CompletedProcess(command, 0, '')

    monkeypatch.setattr(updater.subprocess, 'run', resolve)
    return updater, tmp_path, state


def test_lock_check_detects_drift_without_modifying_committed_files(locks):
    updater, root, state = locks
    state['payload'] = 'pin hasil resolusi baru\n'
    before = {path.name: path.read_bytes() for path in (root / 'locks').iterdir()}
    changed = updater.update_locks(root, 'uv', check=True)
    assert set(changed) == {'runtime', 'test', 'build', 'audit'}
    assert {path.name: path.read_bytes() for path in (root / 'locks').iterdir()} == before


def test_failed_resolution_preserves_every_existing_lock(locks):
    updater, root, state = locks
    state.update(payload='pin baru\n', fail='build')
    with pytest.raises(subprocess.CalledProcessError):
        updater.update_locks(root, 'uv')
    assert all(path.read_text(encoding='utf-8') == 'pin semula\n'
               for path in (root / 'locks').iterdir())


def test_unchanged_lock_check_passes(locks):
    updater, root, _ = locks
    assert updater.update_locks(root, 'uv', check=True) == []


def test_successful_regeneration_updates_all_changed_locks(locks):
    updater, root, state = locks
    state['payload'] = 'pin baru\n'
    assert len(updater.update_locks(root, 'uv')) == 4
    assert all(path.read_text(encoding='utf-8') == 'pin baru\n'
               for path in (root / 'locks').iterdir())

def test_lock_resolver_uses_exact_production_python_with_universal_hashes(locks):
    updater, root, state = locks
    updater.update_locks(root, 'uv', check=True)
    assert len(state['commands']) == len(updater.LOCK_INPUTS)
    for command in state['commands']:
        assert command[command.index('--python-version') + 1] == updater.python_version()
        assert '--universal' in command
        assert '--generate-hashes' in command
        assert '--only-binary' in command
