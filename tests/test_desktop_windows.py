"""Windows integration uses only isolated dummy processes and scratch paths."""
import ctypes
import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import uuid
import subprocess
import sys
import pytest


def module(name):
    assert importlib.util.find_spec('spt_desktop'), 'Desktop Windows package is not implemented'
    return importlib.import_module('spt_desktop.' + name)


@pytest.mark.parametrize('name,want', [
    ('PT Fixture / Cabang: A*?', 'PT Fixture _ Cabang_ A__'),
    ('Fixture. ', 'Fixture'),
    ('日本 Fixture', '日本 Fixture'),
    ('..\\outside', '.._outside'),
])
def test_only_filesystem_name_is_sanitized(name, want):
    assert module('paths').safe_taxpayer_name(name) == want


@pytest.mark.parametrize('name', ['', '   ', '...', '\x00'])
def test_missing_source_name_cannot_create_a_finished_taxpayer_folder(name):
    with pytest.raises(ValueError):
        module('paths').safe_taxpayer_name(name)


def test_long_name_is_bounded_without_losing_unicode():
    assert module('paths').safe_taxpayer_name('日本' * 100, max_length=30) == '日本' * 15


def test_redirected_downloads_is_not_guessed_from_home(monkeypatch, tmp_path):
    paths = module('paths')
    redirected = tmp_path / 'OneDrive - Fixture' / '日本 Downloads'
    monkeypatch.setattr(paths, '_known_folder', lambda folder: redirected)
    assert paths.downloads_folder() == redirected
    assert paths.workspace_root() == redirected / 'SPTDownloader'


def test_known_folder_failure_is_not_hidden_by_fallback(monkeypatch):
    paths = module('paths')
    def unavailable(_):
        raise OSError('Synthetic Known Folder failure')
    monkeypatch.setattr(paths, '_known_folder', unavailable)
    with pytest.raises(OSError, match='Known Folder'):
        paths.downloads_folder()


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows boundary')
def test_native_known_folder_paths_are_absolute():
    paths = module('paths')
    assert paths.downloads_folder().is_absolute()
    assert paths.workspace_root().is_absolute()
    assert paths.workspace_root().name == 'SPTDownloader'


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows boundary')
def test_second_instance_cannot_share_profile(tmp_path):
    windows = module('windows')
    with windows.InstanceLock(tmp_path):
        with pytest.raises(RuntimeError, match='already|sudah'):
            windows.InstanceLock(tmp_path)
    with windows.InstanceLock(tmp_path):
        pass


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows boundary')
@pytest.mark.parametrize('result', [0, -1])
def test_known_folder_allocations_are_freed_even_on_error(monkeypatch, tmp_path, result):
    paths = module('paths')
    allocated = ctypes.create_unicode_buffer(str(tmp_path))
    address = ctypes.cast(allocated, ctypes.c_void_p).value
    freed = []
    def get_folder(guid, flags, token, output):
        value = ctypes.cast(guid, ctypes.POINTER(paths._GUID)).contents
        assert bytes(value) == uuid.UUID(paths.DOWNLOADS).bytes_le
        ctypes.cast(output, ctypes.POINTER(ctypes.c_void_p))[0] = address
        return result
    def free(pointer):
        freed.append(pointer.value)
    shell = SimpleNamespace(SHGetKnownFolderPath=get_folder)
    ole = SimpleNamespace(CoTaskMemFree=free)
    monkeypatch.setattr(ctypes, 'WinDLL', lambda name, **kwargs: shell if name == 'shell32' else ole)
    if result == 0:
        assert paths.downloads_folder() == tmp_path
    else:
        with pytest.raises(OSError, match='Known Folder'):
            paths.downloads_folder()
    assert freed == [address]


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows process ownership')
def test_failed_job_assignment_never_runs_the_dummy_payload(monkeypatch):
    windows = module('windows')
    real_popen = subprocess.Popen
    created = []
    def track(*args, **kwargs):
        process = real_popen(*args, **kwargs)
        created.append(process)
        return process
    def fail(_):
        raise OSError('Synthetic ownership failure')
    monkeypatch.setattr(windows.subprocess, 'Popen', track)
    with windows.ProcessJob() as job:
        monkeypatch.setattr(job, 'assign', fail)
        with pytest.raises(OSError, match='ownership failure'):
            job.spawn([sys.executable, '-c', 'print("SHOULD NOT RUN",flush=True)'],
                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert len(created) == 1
    assert created[0].poll() is not None
    assert created[0].stdout.closed
    assert created[0].stderr.closed


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows process ownership')
def test_closed_job_cannot_launch_a_new_process():
    windows = module('windows')
    job = windows.ProcessJob()
    job.close()
    job.close()
    with pytest.raises(RuntimeError, match='closed'):
        job.spawn([sys.executable, '-c', 'raise RuntimeError("must not start")'])


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows process ownership')
def test_job_spawn_contains_venv_launcher_before_it_can_create_descendants():
    windows = module('windows')
    # uv's venv launcher creates a real interpreter before Python's READY handshake.
    script = ('import subprocess,sys,time; print("READY",flush=True); '
              'sys.stdin.readline(); p=subprocess.Popen([sys._base_executable,"-c","import time; time.sleep(120)"]); '
              'print(p.pid,flush=True); time.sleep(120)')
    owned = unrelated = None
    job = windows.ProcessJob()
    try:
        owned = job.spawn([sys.executable, '-c', script], stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, text=True)
        assert owned.stdout.readline().strip() == 'READY'
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])
        owned.stdin.write('START\n')
        owned.stdin.flush()
        child_pid = int(owned.stdout.readline())
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        kernel.OpenProcess.restype = ctypes.c_void_p
        kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        kernel.WaitForSingleObject.restype = ctypes.c_ulong
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
        child_handle = kernel.OpenProcess(0x100001, False, child_pid)
        assert child_handle
        try:
            job.close()
            owned.wait(timeout=10)
            assert kernel.WaitForSingleObject(child_handle, 5000) == 0
            assert unrelated.poll() is None
        finally:
            if kernel.WaitForSingleObject(child_handle, 0) == 258:
                kernel.TerminateProcess(child_handle, 1)
            kernel.CloseHandle(child_handle)
    finally:
        if job is not None:
            job.close()
        for process in (owned, unrelated):
            if process is None:
                continue
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)
            if process.stdin:
                process.stdin.close()
            if process.stdout:
                process.stdout.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows process ownership')
def test_spawn_cleanup_closes_pipes_even_when_wait_fails(monkeypatch):
    import io
    windows = module('windows')
    class FailedChild:
        pid = 123
        stdin = io.StringIO()
        stdout = io.StringIO()
        stderr = io.StringIO()
        def kill(self):
            pass
        def wait(self, timeout):
            raise subprocess.TimeoutExpired('synthetic-child', timeout)
    child = FailedChild()
    monkeypatch.setattr(windows.subprocess, 'Popen', lambda *args, **kwargs: child)
    with windows.ProcessJob() as job:
        def reject_assignment(pid):
            raise OSError('Synthetic assignment failure')
        monkeypatch.setattr(job, 'assign', reject_assignment)
        with pytest.raises(subprocess.TimeoutExpired):
            job.spawn(['synthetic-only'])
    assert child.stdin.closed and child.stdout.closed and child.stderr.closed
