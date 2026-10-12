"""Bootstrap decisions use synthetic subprocess results, not live downloads."""
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess
import pytest


def runtime_module():
    assert importlib.util.find_spec('spt_desktop.runtime'), 'Portable runtime setup is not implemented'
    return importlib.import_module('spt_desktop.runtime')


class SyntheticCommands:
    def __init__(self, root, source):
        self.root = root
        self.source = source
        self.calls = []
        self.system = source / 'system-python.exe'
        self.system.touch()
        self.uv = source / 'uv.exe'
        self.uv.touch()
        self.system_version = [3, 11, 16]
        self.system_bits = 64
        self.imports_ok = True
        self.fail_install = False

    def run(self, argv, env, cancelled, timeout=900):
        argv = [str(v) for v in argv]
        self.calls.append(argv)
        if cancelled():
            raise RuntimeError('Setup dibatalkan')
        if '--version' in argv:
            return subprocess.CompletedProcess(argv, 0, 'uv 0.12.18 (synthetic)\n', '')
        if '-c' in argv:
            candidate = Path(argv[0])
            info = {'implementation': 'CPython', 'version': self.system_version if candidate == self.system else [3, 11, 16],
                    'bits': self.system_bits if candidate == self.system else 64,
                    'executable': str(candidate), 'packages': {}}
            if 'importlib.metadata' in argv[-1] and self.imports_ok:
                info['packages'] = {'playwright': '1.63.0', 'openpyxl': '3.1.5'}
            return subprocess.CompletedProcess(argv, 0, json.dumps(info), '')
        if argv[1:3] == ['python', 'install']:
            assert '--no-bin' in argv and '--no-registry' in argv
            managed = self.root / 'python' / 'python.exe'
            managed.parent.mkdir(parents=True, exist_ok=True)
            managed.touch()
        if argv[1:3] == ['python', 'find']:
            return subprocess.CompletedProcess(argv, 0, str(self.root / 'python' / 'python.exe') + '\n', '')
        if len(argv) > 1 and argv[1] == 'venv':
            environment = self.root / 'runtime' / 'Scripts' / 'python.exe'
            environment.parent.mkdir(parents=True, exist_ok=True)
            environment.touch()
        if argv[1:3] == ['pip', 'install'] and self.fail_install:
            raise RuntimeError('Synthetic dependency download failure')
        return subprocess.CompletedProcess(argv, 0, '', '')


@pytest.fixture
def setup(monkeypatch, tmp_path):
    if importlib.util.find_spec('spt_desktop.runtime') is None:
        pytest.skip('Runtime is absent; the resource-contract test establishes RED')
    runtime = runtime_module()
    source = tmp_path / 'bundled'
    source.mkdir()
    for relative in runtime.WORKER_FILES:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('playwright==1.63.0\nopenpyxl==3.1.5\n' if relative == 'requirements.txt'
                        else '# Synthetic resource payload, never a live worker\n', encoding='utf-8')
    tools = source / 'tools'
    tools.mkdir()
    (tools / 'uv.exe').write_bytes(b'synthetic bundled uv')
    root = tmp_path / 'Workspace 日本'
    commands = SyntheticCommands(root, source)
    monkeypatch.setattr(runtime, 'resource_root', lambda: source)
    monkeypatch.setattr(runtime, '_run', commands.run)
    monkeypatch.setattr(runtime, '_python_candidates', lambda: [commands.system])
    monkeypatch.setattr(runtime.shutil, 'which', lambda name: str(commands.uv) if name == 'uv' else None)
    return runtime, root, source, commands


def test_compatible_python_uses_isolated_environment_without_global_install(setup):
    runtime, root, source, commands = setup
    notices = []
    python = runtime.ensure_runtime(root, notices.append, lambda: False)
    assert python == root / 'runtime' / 'Scripts' / 'python.exe'
    assert runtime.worker_source(root) == root / 'app'
    assert (root / 'app' / 'requirements.txt').read_text() == (source / 'requirements.txt').read_text()
    assert any(c[1] == 'venv' and str(commands.system) in c for c in commands.calls)
    assert not any(c[1:3] == ['python', 'install'] for c in commands.calls)
    assert notices


@pytest.mark.parametrize('version,bits', [([3, 14, 7], 64), ([3, 11, 16], 32)])
def test_incompatible_system_python_uses_portable_no_registry_install(setup, version, bits):
    runtime, root, _, commands = setup
    commands.system_version, commands.system_bits = version, bits
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    installs = [c for c in commands.calls if c[1:3] == ['python', 'install']]
    assert len(installs) == 1
    assert installs[0][3:] == ['3.11', '--install-dir', str(root / 'python'), '--no-bin', '--no-registry']
    assert any(c[1:3] == ['python', 'find'] and '--managed-python' in c for c in commands.calls)


def test_missing_python_and_uv_use_only_bundled_and_managed_tools(setup, monkeypatch):
    runtime, root, source, commands = setup
    monkeypatch.setattr(runtime, '_python_candidates', lambda: [])
    monkeypatch.setattr(runtime.shutil, 'which', lambda _: None)
    python = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert python.is_relative_to(root)
    assert (root / 'tools' / 'uv.exe').read_bytes() == (source / 'tools' / 'uv.exe').read_bytes()
    assert any(c[1:3] == ['python', 'install'] for c in commands.calls)


def test_vulnerable_installed_uv_is_rejected_in_favor_of_patched_bundle(setup, monkeypatch):
    runtime, root, source, commands = setup
    original_run = commands.run

    def installed_old_uv(argv, env, cancelled, timeout=900):
        if Path(argv[0]) == commands.uv and '--version' in argv:
            commands.calls.append([str(value) for value in argv])
            return subprocess.CompletedProcess(argv, 0, 'uv 0.12.16 (synthetic vulnerable version)\n', '')
        return original_run(argv, env, cancelled, timeout)

    monkeypatch.setattr(runtime, '_run', installed_old_uv)
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    installations = [call for call in commands.calls if call[1:3] == ['pip', 'install']]
    assert installations and all(Path(call[0]) == root/'tools'/'uv.exe' for call in installations)


def test_ready_environment_is_reverified_and_does_not_reinstall(setup):
    runtime, root, _, commands = setup
    first = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    commands.calls.clear()
    second = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert first == second
    assert not any(len(c) > 1 and c[1] == 'venv' for c in commands.calls)
    assert not any(c[1:3] == ['pip', 'install'] for c in commands.calls)
    assert any('-c' in c and 'importlib.metadata' in c[-1] for c in commands.calls)


def test_changed_requirements_cannot_be_mistaken_for_ready(setup):
    runtime, root, source, commands = setup
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    commands.calls.clear()
    (source / 'requirements.txt').write_text('playwright==1.63.0\nopenpyxl==3.1.5\n# changed source\n', encoding='utf-8')
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert any(c[1:3] == ['pip', 'install'] for c in commands.calls)
    assert (root / 'app' / 'requirements.txt').read_bytes() == (source / 'requirements.txt').read_bytes()


def test_failed_dependency_setup_is_retryable_and_never_marked_ready(setup):
    runtime, root, _, commands = setup
    commands.fail_install = True
    with pytest.raises(RuntimeError, match='dependency'):
        runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert not (root / 'runtime-ready.txt').exists()
    commands.fail_install = False
    assert runtime.ensure_runtime(root, lambda _: None, lambda: False).exists()
    assert (root / 'runtime-ready.txt').exists()


def test_import_verification_failure_cannot_mark_ready(setup):
    runtime, root, _, commands = setup
    commands.imports_ok = False
    with pytest.raises(RuntimeError, match='dependensi|dependencies'):
        runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert not (root / 'runtime-ready.txt').exists()


def test_cancelled_setup_never_starts_installation(setup):
    runtime, root, _, commands = setup
    with pytest.raises(RuntimeError, match='dibatalkan'):
        runtime.ensure_runtime(root, lambda _: None, lambda: True)
    assert commands.calls == []
    assert not (root / 'runtime-ready.txt').exists()


def test_source_payload_is_explicit_and_excludes_outputs_profiles_and_gui():
    runtime = runtime_module()
    assert 'coretax.py' in runtime.WORKER_FILES
    assert 'requirements.txt' in runtime.WORKER_FILES
    assert not any(any(x in name for x in ['output/', 'profile/', '.venv/', 'tests/', 'app.py'])
                   for name in runtime.WORKER_FILES)
