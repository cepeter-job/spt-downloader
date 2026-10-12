"""Perbaiki hanya alias minor uv, termasuk siklus arsip tar nyata pada Windows."""
import importlib.util
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def cache_module():
    path = ROOT / 'scripts' / 'ci_python_cache.py'
    assert path.is_file(), 'Windows cached Python aliases need a bootstrap repair.'
    spec = importlib.util.spec_from_file_location('ci_python_cache', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cache_paths(tmp_path, version='3.11.17'):
    runner_temp = tmp_path / 'runner-temp'
    runner_temp.mkdir()
    managed = runner_temp / 'uv-python-dir'
    managed.mkdir()
    minor = '.'.join(version.split('.')[:2])
    alias = managed / f'cpython-{minor}-windows-x86_64-none'
    return runner_temp, managed, alias


def symlink(link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError as error:
        if getattr(error, 'winerror', None) == 1314:
            pytest.skip('This local Windows account cannot create symbolic links.')
        raise


@pytest.mark.parametrize('version', ['3.11.17', '3.14.8'])
def test_cached_file_alias_is_removed_without_changing_the_exact_interpreter(tmp_path, version):
    runner_temp, managed, alias = cache_paths(tmp_path, version)
    patch = managed / f'cpython-{version}-windows-x86_64-none'
    patch.mkdir()
    executable = patch / 'python.exe'
    executable.write_bytes(b'synthetic exact interpreter')
    unrelated = managed / 'cpython-3.10-windows-x86_64-none'
    unrelated.write_bytes(b'unrelated cache entry')
    alias.write_bytes(b'synthetic restored file alias')
    # uv 0.12.22 memakai remove_dir untuk alias Windows; file tidak bisa dihapus dengannya.
    with pytest.raises(OSError):
        alias.rmdir()

    result = cache_module().prepare_windows_python_cache(managed, runner_temp, version)

    assert result['kind'] == 'file' and result['removed'] is True
    assert not alias.exists()
    assert executable.read_bytes() == b'synthetic exact interpreter'
    assert unrelated.read_bytes() == b'unrelated cache entry'
    alias.mkdir()  # Alias sekarang dapat dibuat kembali oleh operasi direktori asli.


@pytest.mark.parametrize('target_kind', ['missing', 'file', 'directory', 'file-link-to-directory'])
def test_cached_symlink_is_unlinked_without_following_its_target(tmp_path, target_kind):
    runner_temp, managed, alias = cache_paths(tmp_path)
    target = tmp_path / 'outside-cache'
    if 'directory' in target_kind:
        target.mkdir()
        (target / 'keep.txt').write_bytes(b'synthetic external directory content')
    elif target_kind == 'file':
        target.write_bytes(b'synthetic file outside managed cache')
    symlink(alias, target, directory=target_kind == 'directory')

    result = cache_module().prepare_windows_python_cache(managed, runner_temp, '3.11.17')

    assert result['kind'] == 'symlink' and result['removed'] is True
    assert not os.path.lexists(alias)
    assert target.exists() == (target_kind != 'missing')
    if 'directory' in target_kind:
        assert (target / 'keep.txt').read_bytes() == b'synthetic external directory content'
    elif target_kind == 'file':
        assert target.read_bytes() == b'synthetic file outside managed cache'


def test_real_alias_directory_and_its_contents_are_never_deleted(tmp_path):
    runner_temp, managed, alias = cache_paths(tmp_path)
    alias.mkdir()
    sentinel = alias / 'keep.txt'
    sentinel.write_text('synthetic directory content', encoding='utf-8')

    result = cache_module().prepare_windows_python_cache(managed, runner_temp, '3.11.17')

    assert result['kind'] == 'directory' and result['removed'] is False
    assert sentinel.read_text(encoding='utf-8') == 'synthetic directory content'


def test_empty_and_missing_cache_are_noops(tmp_path):
    runner_temp, managed, _ = cache_paths(tmp_path)
    prepare = cache_module().prepare_windows_python_cache
    assert prepare(managed, runner_temp, '3.11.17')['kind'] == 'missing'
    managed.rmdir()
    assert prepare(managed, runner_temp, '3.11.17')['kind'] == 'missing'
    assert not managed.exists()


@pytest.mark.parametrize('version', ['3.11', '3.11.17+gil', '../3.11.17', '', '3.11.17\\other'])
def test_non_exact_versions_are_rejected_before_touching_the_cache(tmp_path, version):
    runner_temp, managed, alias = cache_paths(tmp_path)
    alias.write_bytes(b'keep')
    with pytest.raises(ValueError, match='exact Python version'):
        cache_module().prepare_windows_python_cache(managed, runner_temp, version)
    assert alias.read_bytes() == b'keep'


@pytest.mark.parametrize('location', ['elsewhere', 'relative', 'traversal'])
def test_managed_root_must_be_the_exact_runner_cache_directory(tmp_path, location):
    runner_temp, managed, alias = cache_paths(tmp_path)
    alias.write_bytes(b'keep')
    selected = {'elsewhere': tmp_path / 'another-cache',
                'relative': Path('uv-python-dir'),
                'traversal': runner_temp / 'child' / '..' / 'uv-python-dir'}[location]
    with pytest.raises(ValueError, match='managed cache root'):
        cache_module().prepare_windows_python_cache(selected, runner_temp, '3.11.17')
    assert alias.read_bytes() == b'keep'


@pytest.mark.parametrize('redirect', ['managed', 'runner-temp', 'ancestor'])
def test_redirected_cache_roots_are_rejected_without_deleting_external_files(tmp_path, redirect):
    runner_temp, managed, alias = cache_paths(tmp_path)
    alias.write_bytes(b'keep')
    if redirect == 'managed':
        actual = tmp_path / 'real-managed'
        managed.rename(actual)
        symlink(managed, actual, directory=True)
        sentinel = actual / alias.name
    elif redirect == 'runner-temp':
        actual = tmp_path / 'real-runner-temp'
        runner_temp.rename(actual)
        symlink(runner_temp, actual, directory=True)
        sentinel = actual / 'uv-python-dir' / alias.name
    else:
        link = tmp_path / 'linked-parent'
        symlink(link, tmp_path, directory=True)
        runner_temp = link / runner_temp.name
        managed = runner_temp / 'uv-python-dir'
        sentinel = alias
    with pytest.raises(ValueError, match='directory|redirected'):
        cache_module().prepare_windows_python_cache(managed, runner_temp, '3.11.17')
    assert sentinel.read_bytes() == b'keep'


def test_bootstrap_uses_only_stdlib_and_reports_alias_type_without_target_paths(tmp_path):
    runner_temp, managed, alias = cache_paths(tmp_path)
    alias.write_bytes(b'synthetic restored alias')
    path = ROOT / 'scripts' / 'ci_python_cache.py'
    assert path.is_file(), 'The pre-environment bootstrap helper is missing.'
    environment = dict(os.environ, RUNNER_TEMP=str(runner_temp), UV_PYTHON_INSTALL_DIR=str(managed))

    result = subprocess.run([sys.executable, '-I', '-S', str(path), '--python-version', '3.11.17'],
                            env=environment, capture_output=True, text=True, timeout=15)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report['alias'] == alias.name and report['kind'] == 'file' and report['removed'] is True
    assert str(tmp_path) not in result.stdout + result.stderr


def test_windows_workloads_prepare_cache_aliases_before_installing_exact_python():
    workflow = (ROOT / '.github' / 'workflows' / 'windows-build.yml').read_text(encoding='utf-8')
    for job in ('windows', 'dependency-audit', 'package'):
        # Pisahkan pada job berikutnya, bukan properti di dalam job.
        body = workflow.split(f'\n  {job}:', 1)[1]
        body = re.split(r'\n  [a-z][a-z-]*:', body, maxsplit=1)[0]
        assert 'python -I -S scripts/ci_python_cache.py --python-version' in body
        assert body.index('python -I -S scripts/ci_python_cache.py') < body.index('uv python install')
        assert '--no-bin --no-registry' in body


def test_real_windows_cold_install_and_tar_restore_reuse_the_exact_python(tmp_path):
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        pytest.skip('Real uv/tar roundtrip runs once on Windows GitHub Actions.')
    from spt_desktop.runtime import PYTHON_PROFILES, UV_VERSION
    version = PYTHON_PROFILES['production']
    if platform.python_version() != version:
        pytest.skip('Production Windows job covers the shared tar alias format.')
    uv = shutil.which('uv')
    git = shutil.which('git')
    assert uv and git, 'The pinned uv and Git for Windows must be available.'
    tar = Path(git).resolve().parents[1] / 'usr' / 'bin' / 'tar.exe'
    assert tar.is_file(), 'Use the same Git for Windows GNU tar as Actions cache.'
    runner_temp = tmp_path / 'roundtrip-runner-temp'
    runner_temp.mkdir()
    managed = runner_temp / 'uv-python-dir'
    environment = dict(os.environ, UV_PYTHON_INSTALL_DIR=str(managed),
                       UV_CACHE_DIR=str(runner_temp / 'wheel-cache'), UV_PYTHON=version,
                       MSYS='winsymlinks:nativestrict')
    for name in ('UV_PYTHON_PREFERENCE', 'VIRTUAL_ENV', 'PYTHONHOME', 'PYTHONPATH'):
        environment.pop(name, None)

    def run(argv, *, check=True):
        result = subprocess.run([str(arg) for arg in argv], env=environment, cwd=tmp_path,
                                capture_output=True, text=True, timeout=120)
        if check:
            assert result.returncode == 0, result.stdout + result.stderr
        return result

    assert run([uv, '--version']).stdout.split()[:2] == ['uv', UV_VERSION]
    prepare = cache_module().prepare_windows_python_cache
    assert prepare(managed, runner_temp, version)['kind'] == 'missing'
    install = [uv, 'python', 'install', f'cpython-{version}-windows-x86_64-none',
               '--no-bin', '--no-registry']
    run(install)
    cold_alias = prepare(managed, runner_temp, version)
    assert cold_alias['kind'] == 'junction' and cold_alias['removed'] is False
    patch_name = f'cpython-{version}-windows-x86_64-none'
    executable = managed / patch_name / 'python.exe'
    cold_bytes = executable.read_bytes()
    archive = tmp_path / 'python-cache.tar'
    manifest = tmp_path / 'manifest.txt'
    manifest.write_text(managed.as_posix() + '\n', encoding='utf-8')
    run([tar, '--posix', '-cf', archive, '-P', '-C', tmp_path,
         '--files-from', manifest, '--force-local'])
    managed.rename(tmp_path / 'cold-python')
    run([tar, '-xf', archive, '-P', '-C', tmp_path, '--force-local'])
    assert executable.read_bytes() == cold_bytes

    # Tar yang mempertahankan tautan direktori dapat langsung meluluskan kontrol ini.
    # Jika gagal, wajib galat alias yang dikenal agar masalah baru tidak disembunyikan.
    control = run([*install, '--offline'], check=False)
    if control.returncode:
        assert 'Failed to create Python minor version link directory' in control.stderr
        assert 'os error 267' in control.stderr
    report = prepare(managed, runner_temp, version)
    print('Windows restored Python alias: ' + json.dumps(report, sort_keys=True))
    run([*install, '--offline'])
    venv = tmp_path / 'warm-venv'
    run([uv, 'venv', '--managed-python', '--python', version + '+gil', '--offline', venv])
    probe = run([venv / 'Scripts' / 'python.exe', '-I', '-c',
                 'import json,platform,struct,sys,sysconfig; '
                 'print(json.dumps({"implementation":platform.python_implementation(),'
                 '"version":platform.python_version(),"bits":struct.calcsize("P")*8,'
                 '"free_threaded":bool(sysconfig.get_config_var("Py_GIL_DISABLED")),'
                 '"base":sys.base_prefix}))'])
    info = json.loads(probe.stdout)
    assert {key: info[key] for key in ('implementation', 'version', 'bits', 'free_threaded')} == {
        'implementation': 'CPython', 'version': version, 'bits': 64, 'free_threaded': False}
    assert Path(info['base']).resolve().is_relative_to(managed.resolve())
