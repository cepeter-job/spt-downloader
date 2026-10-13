"""Bootstrap decisions use synthetic subprocess results, not live downloads."""
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest


PACKAGES = {'playwright': '1.63.0', 'openpyxl': '3.1.5', 'greenlet': '3.5.6',
            'pyee': '13.0.1', 'et-xmlfile': '2.0.0', 'typing-extensions': '4.16.0'}
LOCK = '\n'.join(f'{name}=={version} --hash=sha256:' + 'a' * 64
                 for name, version in PACKAGES.items()) + '\n'


def runtime_module():
    assert importlib.util.find_spec('spt_desktop.runtime'), 'Portable runtime setup is not implemented'
    return importlib.import_module('spt_desktop.runtime')


def test_python_314_is_the_only_release_profile():
    runtime = runtime_module()
    assert runtime.PYTHON_PROFILES == {'production': '3.14.8'}
    assert runtime.python_version() == '3.14.8'
    with pytest.raises(ValueError, match='profil'):
        runtime.python_version('candidate')


def test_windows_cli_setup_uses_the_same_exact_production_runtime():
    runtime = runtime_module()
    script = (Path(__file__).resolve().parents[1] / 'setup.cmd').read_text(encoding='utf-8')
    version = runtime.python_version()
    assert f'cpython-{version}-windows-x86_64-none' in script
    assert f'--python {version}+gil' in script
    assert 'cpython-3.11.17-' not in script


class SyntheticCommands:
    def __init__(self, root, source):
        self.root = root
        self.source = source
        self.calls = []
        self.system = source / 'system-python.exe'
        self.system.touch()
        self.uv = source / 'uv.exe'
        self.uv.touch()
        self.system_version = [3, 11, 17]
        self.system_bits = 64
        self.managed_version = [3, 11, 17]
        self.free_threaded = False
        self.base_outside = False
        self.package_versions = dict(PACKAGES)
        self.imports_ok = True
        self.fail_install = False

    def run(self, argv, env, cancelled, timeout=900):
        argv = [str(v) for v in argv]
        self.calls.append(argv)
        if cancelled():
            raise RuntimeError('Setup dibatalkan')
        if '--version' in argv:
            return subprocess.CompletedProcess(argv, 0, f'uv {runtime_module().UV_VERSION} (synthetic)\n', '')
        if '-c' in argv:
            candidate = Path(argv[0])
            info = {'implementation': 'CPython', 'version': self.system_version if candidate == self.system else self.managed_version,
                    'bits': self.system_bits if candidate == self.system else 64,
                    'free_threaded': self.free_threaded,
                    'base_executable': str(self.system if self.base_outside else self.root / 'python' / 'python.exe'),
                    'executable': str(candidate), 'packages': {}}
            if 'importlib.metadata' in argv[-1] and self.imports_ok:
                info['packages'] = dict(self.package_versions)
            return subprocess.CompletedProcess(argv, 0, json.dumps(info), '')
        if argv[1:3] == ['python', 'install']:
            assert '--no-bin' in argv and '--no-registry' in argv
            # Katalog unduhan uv 0.12.22 memakai varian default, bukan selector +gil.
            downloads = {'cpython-3.11.17-windows-x86_64-none': [3, 11, 17],
                         'cpython-3.14.8-windows-x86_64-none': [3, 14, 8]}
            if argv[3] not in downloads:
                raise RuntimeError('No download found for request: ' + argv[3])
            self.managed_version = downloads[argv[3]]
            self.base_outside = False
            managed = self.root / 'python' / 'python.exe'
            managed.parent.mkdir(parents=True, exist_ok=True)
            managed.touch()
        if argv[1:3] == ['python', 'find']:
            return subprocess.CompletedProcess(argv, 0, str(self.root / 'python' / 'python.exe') + '\n', '')
        if len(argv) > 1 and argv[1] == 'venv':
            environment = self.root / 'runtime' / 'Scripts' / 'python.exe'
            environment.parent.mkdir(parents=True, exist_ok=True)
            environment.touch()
        if argv[1:3] in (['pip', 'install'], ['pip', 'sync']) and self.fail_install:
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
                        else LOCK if relative == 'locks/runtime.txt'
                        else '# Synthetic resource payload, never a live worker\n', encoding='utf-8')
    (source / 'locks').mkdir(exist_ok=True)
    (source / 'locks' / 'runtime.txt').write_text(LOCK, encoding='utf-8')
    tools = source / 'tools'
    tools.mkdir()
    (tools / 'uv.exe').write_bytes(b'synthetic bundled uv')
    root = tmp_path / 'Workspace 日本'
    commands = SyntheticCommands(root, source)
    monkeypatch.setattr(runtime, 'resource_root', lambda: source)
    monkeypatch.setattr(runtime, '_run', commands.run)
    monkeypatch.setattr(runtime.shutil, 'which', lambda name: str(commands.uv) if name == 'uv' else None)
    return runtime, root, source, commands


def test_runtime_uses_managed_patched_python_and_hashed_isolated_dependencies(setup):
    runtime, root, source, commands = setup
    notices = []
    assert not (root / 'python').exists()
    python = runtime.ensure_runtime(root, notices.append, lambda: False)
    assert python == root / 'runtime' / 'Scripts' / 'python.exe'
    assert runtime.worker_source(root) == root / 'app'
    assert (root / 'app' / 'requirements.txt').read_text() == (source / 'requirements.txt').read_text()
    assert any(c[1] == 'venv' and str(root / 'python' / 'python.exe') in c for c in commands.calls)
    assert not any(str(commands.system) in c for c in commands.calls)
    installs = [c for c in commands.calls if c[1:3] == ['python', 'install']]
    assert len(installs) == 1
    assert installs[0][3:] == ['cpython-3.14.8-windows-x86_64-none', '--install-dir',
                              str(root / 'python'), '--no-bin', '--no-registry']
    syncs = [c for c in commands.calls if c[1:3] == ['pip', 'sync']]
    assert len(syncs) == 1 and '--require-hashes' in syncs[0] and '--only-binary' in syncs[0]
    assert str(root / 'app' / 'locks' / 'runtime.txt') in syncs[0]
    assert notices


def test_previously_ready_311_worker_is_rebuilt_for_314(setup):
    runtime, root, _, commands = setup
    previous = root / 'runtime' / 'Scripts' / 'python.exe'
    previous.parent.mkdir(parents=True)
    previous.touch()
    ready = root / 'runtime-ready.txt'
    ready.write_text('legacy-311-fingerprint', encoding='ascii')
    assert commands.managed_version == [3, 11, 17]

    result = runtime.ensure_runtime(root, lambda _: None, lambda: False)

    assert result == previous
    assert commands.managed_version == [3, 14, 8]
    assert ready.read_text(encoding='ascii') != 'legacy-311-fingerprint'
    assert any(call[1:3] == ['python', 'install'] and
               call[3] == 'cpython-3.14.8-windows-x86_64-none' for call in commands.calls)
    assert any(call[1] == 'venv' and '--clear' in call for call in commands.calls)


@pytest.mark.parametrize('version,bits', [([3, 11, 17], 64), ([3, 14, 7], 64),
                                        ([3, 14, 9], 64), ([3, 14, 8], 32)])
def test_unsupported_interpreter_is_rejected(version, bits):
    runtime = runtime_module()
    assert not runtime._compatible({'implementation': 'CPython', 'version': version,
                                    'bits': bits, 'free_threaded': False})


def test_retired_candidate_profile_never_creates_a_runtime(setup):
    runtime, root, _, commands = setup
    with pytest.raises(ValueError, match='profil'):
        runtime.ensure_runtime(root, lambda _: None, lambda: False, python_profile='candidate')
    assert commands.calls == [] and not root.exists()


def test_unknown_profile_never_creates_or_downloads_a_runtime(setup):
    runtime, root, _, commands = setup
    with pytest.raises(ValueError, match='profil'):
        runtime.ensure_runtime(root, lambda _: None, lambda: False, python_profile='3.15')
    assert commands.calls == [] and not root.exists()


def test_missing_python_and_uv_use_only_bundled_and_managed_tools(setup, monkeypatch):
    runtime, root, source, commands = setup
    monkeypatch.setattr(runtime.shutil, 'which', lambda _: None)
    python = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert python.is_relative_to(root)
    assert (root / 'tools' / 'uv.exe').read_bytes() == (source / 'tools' / 'uv.exe').read_bytes()
    assert any(c[1:3] == ['python', 'install'] for c in commands.calls)


def test_inherited_python_preference_cannot_conflict_with_owned_selection(setup, monkeypatch):
    runtime, root, _, commands = setup
    monkeypatch.setenv('UV_PYTHON_PREFERENCE', 'only-managed')
    original_run = commands.run

    def reject_conflicting_preference(argv, env, cancelled, timeout=900):
        # uv 0.12.22 menolak --managed-python jika opsi preferensi diwarisi dari environment.
        if '--managed-python' in argv and 'UV_PYTHON_PREFERENCE' in env:
            raise RuntimeError('the argument --managed-python cannot be used with --python-preference')
        return original_run(argv, env, cancelled, timeout)

    monkeypatch.setattr(runtime, '_run', reject_conflicting_preference)
    python = runtime.ensure_runtime(root, lambda _: None, lambda: False, python_profile='production')
    assert python.is_file()
    assert (root / 'runtime-ready.txt').is_file()


def test_active_developer_venv_cannot_shadow_the_owned_managed_python(setup, monkeypatch):
    runtime, root, source, commands = setup
    developer_venv = source / 'developer-venv'
    developer_venv.mkdir()
    monkeypatch.setenv('VIRTUAL_ENV', str(developer_venv))
    original_run = commands.run

    def find_with_active_venv(argv, env, cancelled, timeout=900):
        command = [str(value) for value in argv]
        # Perilaku uv 0.12.22: find tetap mengutamakan VIRTUAL_ENV tanpa --system,
        # sekalipun --managed-python sudah diberikan dan versi tepat tersedia.
        if (command[1:3] == ['python', 'find'] and env.get('VIRTUAL_ENV')
                and '--system' not in command):
            return subprocess.CompletedProcess(command, 0, str(commands.system) + '\n', '')
        return original_run(argv, env, cancelled, timeout)

    monkeypatch.setattr(runtime, '_run', find_with_active_venv)
    python = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert python == root / 'runtime' / 'Scripts' / 'python.exe'
    assert (root / 'runtime-ready.txt').is_file()


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
    installations = [call for call in commands.calls if call[1:3] == ['pip', 'sync']]
    assert installations and all(Path(call[0]) == root/'tools'/'uv.exe' for call in installations)


def test_ready_environment_is_reverified_and_does_not_reinstall(setup):
    runtime, root, _, commands = setup
    first = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    commands.calls.clear()
    second = runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert first == second
    assert not any(len(c) > 1 and c[1] == 'venv' for c in commands.calls)
    assert not any(c[1:3] in (['pip', 'install'], ['pip', 'sync']) for c in commands.calls)
    assert any('-c' in c and 'importlib.metadata' in c[-1] for c in commands.calls)


def test_changed_requirements_cannot_be_mistaken_for_ready(setup):
    runtime, root, source, commands = setup
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    commands.calls.clear()
    (source / 'requirements.txt').write_text('playwright==1.63.0\nopenpyxl==3.1.5\n# changed source\n', encoding='utf-8')
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert any(c[1:3] == ['pip', 'sync'] for c in commands.calls)
    assert (root / 'app' / 'requirements.txt').read_bytes() == (source / 'requirements.txt').read_bytes()


def test_changed_transitive_lock_invalidates_ready_fingerprint(setup):
    runtime, root, source, commands = setup
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    fingerprint = (root / 'runtime-ready.txt').read_text()
    commands.calls.clear()
    lock = source / 'locks' / 'runtime.txt'
    lock.write_text(LOCK.replace('a' * 64, 'b' * 64), encoding='utf-8')
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert (root / 'runtime-ready.txt').read_text() != fingerprint
    assert any(c[1:3] == ['pip', 'sync'] for c in commands.calls)
    assert (root / 'app' / 'locks' / 'runtime.txt').read_bytes() == lock.read_bytes()


@pytest.mark.parametrize('contents', ['playwright==1.63.0\n',
                                     'playwright>=1 --hash=sha256:' + 'a' * 64,
                                     '-r ../requirements.txt\n'])
def test_invalid_lock_fails_before_any_subprocess(setup, contents):
    runtime, root, source, commands = setup
    (source / 'locks' / 'runtime.txt').write_text(contents, encoding='utf-8')
    with pytest.raises(RuntimeError, match='lock|hash'):
        runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert commands.calls == []


def test_ready_runtime_rejects_transitive_version_drift(setup):
    runtime, root, _, commands = setup
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    commands.calls.clear()
    commands.package_versions['greenlet'] = '0.0.0'
    with pytest.raises(RuntimeError, match='dependensi'):
        runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert any(c[1:3] == ['pip', 'sync'] for c in commands.calls)
    assert not (root / 'runtime-ready.txt').exists()


def test_existing_runtime_backed_by_system_python_is_recreated(setup):
    runtime, root, _, commands = setup
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    commands.calls.clear()
    commands.base_outside = True
    runtime.ensure_runtime(root, lambda _: None, lambda: False)
    assert any(c[1] == 'venv' for c in commands.calls)


def test_free_threaded_python_is_not_an_approved_runtime():
    runtime = runtime_module()
    assert not runtime._compatible({'implementation': 'CPython', 'version': [3, 14, 8],
                                    'bits': 64, 'free_threaded': True}, 'production')


def test_probe_imports_transitive_distributions_with_hyphenated_names(monkeypatch):
    runtime = runtime_module()
    def run(argv, env, cancelled, timeout=900):
        return subprocess.run(argv, env=env, capture_output=True, text=True, check=True, timeout=timeout)
    monkeypatch.setattr(runtime, '_run', run)
    expected = {'et-xmlfile': 'unused', 'typing-extensions': 'unused'}
    info = runtime._probe_python(Path(sys.executable), expected, os.environ.copy(),
                                 lambda: False, packages=True)
    assert info is not None and all(info['packages'].values())
    assert info['base_executable'] and info['free_threaded'] is False


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
    assert 'locks/runtime.txt' in runtime.WORKER_FILES
    assert not any(any(x in name for x in ['output/', 'profile/', '.venv/', 'tests/', 'app.py'])
                   for name in runtime.WORKER_FILES)
