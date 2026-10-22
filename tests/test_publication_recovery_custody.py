"""Recovery deletes only the exact verified file through a held native handle.

Windows cases exercise real sharing/deletion semantics on synthetic files.
The API wrapper only adds a race/failure barrier before the real native call.
"""
import ctypes
import errno
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from spt_desktop import output_windows


native = pytest.mark.skipif(sys.platform != 'win32', reason='Native verified Windows deletion')


def deleter():
    remove = getattr(output_windows, 'delete_verified', None)
    assert callable(remove), 'Recovery deletion needs custody through the native delete boundary'
    return remove


def fingerprint(path):
    info = path.lstat()
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            hashlib.sha256(path.read_bytes()).hexdigest())


def sample(tmp_path):
    path = tmp_path / '.spt-synthetic.recovery'
    path.write_bytes(b'SYNTHETIC RECOVERY BYTES A')
    return path, fingerprint(path)


class NativeBoundary:
    def __init__(self, real, boundary):
        self.real, self.boundary = real, boundary

    def __getattr__(self, name):
        return getattr(self.real, name)

    def SetFileInformationByHandle(self, *args):
        return self.boundary(self.real.SetFileInformationByHandle, args)


@native
def test_exact_recovery_file_is_deleted_without_path_based_unlink(tmp_path, monkeypatch):
    remove = deleter()
    path, expected = sample(tmp_path)
    keep = tmp_path / 'keep.txt'
    keep.write_bytes(b'SYNTHETIC UNRELATED BYTES')
    original_unlink = Path.unlink

    def deny_path_delete(value, *args, **kwargs):
        assert value != path, 'A verified handle must stay held through deletion'
        return original_unlink(value, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', deny_path_delete)
    remove(path, expected)
    assert not path.exists()
    assert keep.read_bytes() == b'SYNTHETIC UNRELATED BYTES'


@native
@pytest.mark.parametrize('change', ['bytes', 'identity', 'mtime'])
def test_changed_recovery_version_is_preserved_even_if_bytes_or_metadata_match(tmp_path, change):
    remove = deleter()
    path, expected = sample(tmp_path)
    previous = path.stat()
    original = path.read_bytes()
    moved = tmp_path / 'preserved-original'
    if change == 'identity':
        path.rename(moved)
        path.write_bytes(original)
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        assert fingerprint(path)[1] != expected[1]
    elif change == 'bytes':
        path.write_bytes(b'SYNTHETIC RECOVERY BYTES B')
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns))
        assert fingerprint(path)[:4] == expected[:4]
    else:
        os.utime(path, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000))
    actual = path.read_bytes()
    with pytest.raises(ValueError, match='changed|identity|state|fingerprint|bytes'):
        remove(path, expected)
    assert path.read_bytes() == actual
    if change == 'identity':
        assert moved.read_bytes() == original


@native
def test_write_rename_and_replacement_are_blocked_at_native_delete_boundary(tmp_path, monkeypatch):
    remove = deleter()
    path, expected = sample(tmp_path)
    other = tmp_path / 'unapproved-version'
    other.write_bytes(b'SYNTHETIC CONCURRENT VERSION')
    moved = tmp_path / 'raced-name'
    calls = []

    def boundary(real_call, args):
        calls.append(True)
        # These are real filesystem attempts while the verified handle is held.
        with pytest.raises(OSError):
            path.write_bytes(b'SYNTHETIC UNAPPROVED WRITE')
        with pytest.raises(OSError):
            path.rename(moved)
        with pytest.raises(OSError):
            os.replace(other, path)
        return real_call(*args)

    kernel = NativeBoundary(output_windows._kernel(), boundary)
    monkeypatch.setattr(output_windows, '_kernel', lambda: kernel)
    remove(path, expected)
    assert calls == [True]
    assert not path.exists() and not moved.exists()
    assert other.read_bytes() == b'SYNTHETIC CONCURRENT VERSION'


@native
def test_failed_native_disposition_retains_bytes_and_releases_its_handle(tmp_path, monkeypatch):
    remove = deleter()
    path, expected = sample(tmp_path)
    original = path.read_bytes()
    calls = []

    def reject(real_call, args):
        calls.append(True)
        ctypes.set_last_error(5)  # ERROR_ACCESS_DENIED; no actual delete requested.
        return 0

    kernel = NativeBoundary(output_windows._kernel(), reject)
    monkeypatch.setattr(output_windows, '_kernel', lambda: kernel)
    with pytest.raises(OSError):
        remove(path, expected)
    assert calls == [True] and path.read_bytes() == original
    renamed = path.with_name('retained-after-native-failure')
    path.rename(renamed)
    assert renamed.read_bytes() == original


@native
def test_existing_deny_delete_reader_preserves_file_until_reader_releases(tmp_path):
    remove = deleter()
    path, expected = sample(tmp_path)
    original = path.read_bytes()
    with path.open('rb') as held:
        with pytest.raises(OSError):
            remove(path, expected)
        assert held.read() == original and path.exists()
    remove(path, expected)
    assert not path.exists()


@native
def test_shared_hardlink_is_retained_without_removing_either_name(tmp_path):
    remove = deleter()
    path, expected = sample(tmp_path)
    alias = tmp_path / 'outside-copy'
    os.link(path, alias)
    with pytest.raises(ValueError, match='[Ss]hared|link|ordinary'):
        remove(path, expected)
    assert path.read_bytes() == alias.read_bytes() == b'SYNTHETIC RECOVERY BYTES A'


@native
def test_redirected_ancestor_never_deletes_link_target(tmp_path):
    remove = deleter()
    outside = tmp_path / 'outside'
    outside.mkdir()
    path, expected = sample(outside)
    alias = tmp_path / 'redirected'
    subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(alias), str(outside)],
                   check=True, capture_output=True, timeout=10)
    try:
        with pytest.raises(ValueError, match='reparse|ordinary|directory|path'):
            remove(alias / path.name, expected)
        assert path.read_bytes() == b'SYNTHETIC RECOVERY BYTES A'
    finally:
        alias.rmdir()


def test_unsupported_platform_retains_recovery_file_without_fallback_unlink(tmp_path, monkeypatch):
    remove = deleter()
    path, expected = sample(tmp_path)
    monkeypatch.setattr(output_windows, 'sys', SimpleNamespace(platform='unsupported'))
    with pytest.raises(OSError) as caught:
        remove(path, expected)
    assert caught.value.errno == errno.ENOTSUP
    assert path.read_bytes() == b'SYNTHETIC RECOVERY BYTES A'
