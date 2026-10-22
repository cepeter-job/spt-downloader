"""Leased ownership and conservative recovery for temporary login profiles.

Only a matching, ordinary ownership record authorizes removal. A byte-range
lease survives for the owner's lifetime and is released by Windows on abrupt
exit; directory names, timestamps and reusable process IDs are not ownership.
Unmarked legacy profiles and unverifiable trees are retained for manual review.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import stat
import sys
import time
import uuid

from .output_windows import DirectoryGuard


_MARKER = re.compile(r'\.spt-profile-([0-9a-f]{32})\.json')
_KINDS = frozenset({'login-check', 'login-run'})
_RECORD_LIMIT = 2048
_LEASE_OFFSET = 4096  # Outside the JSON bytes, so active metadata stays readable.
_SCAN_LIMIT = 4096
_TREE_LIMIT = 16384
_REAP_SECONDS = 5


def _identity(info):
    return info.st_dev, info.st_ino


def _ordinary(info, *, directory=False):
    valid = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    return (valid and info.st_ino and not getattr(info, 'st_file_attributes', 0) & 0x400
            and (directory or info.st_nlink == 1))


def _open_record(path, *, exclusive=False):
    flags = os.O_RDWR | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    if exclusive:
        flags |= os.O_CREAT | os.O_EXCL
    before = None if exclusive else path.lstat()
    if before is not None and not _ordinary(before):
        raise ValueError('Profile ownership file is redirected or shared')
    fd = os.open(path, flags, 0o600)
    try:
        opened, after = os.fstat(fd), path.lstat()
        if (not _ordinary(opened) or not _ordinary(after)
                or _identity(opened) != _identity(after)
                or before is not None and _identity(before) != _identity(opened)):
            raise ValueError('Profile ownership file identity changed')
        return fd
    except BaseException:
        os.close(fd)
        raise


def _lock(fd, *, unlock=False):
    # Windows permits a lock beyond EOF. Unlike byte zero, this does not block
    # a support tool reading the small nonsecret ownership record while active.
    os.lseek(fd, _LEASE_OFFSET, os.SEEK_SET)
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_UNLCK if unlock else msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN if unlock else fcntl.LOCK_EX | fcntl.LOCK_NB)


@contextmanager
def _cache(root, *, create=False):
    path = Path(root)
    if '..' in path.parts:
        raise ValueError('Profile workspace cannot contain parent traversal')
    folder = path.absolute() / 'cache'
    expected = {}
    with DirectoryGuard() as guard:
        for directory in reversed((folder, *folder.parents)):
            try:
                info = directory.lstat()
            except FileNotFoundError:
                if not create:
                    raise
                directory.mkdir(mode=0o700, exist_ok=True)
                info = directory.lstat()
            if not _ordinary(info, directory=True):
                raise ValueError('Profile workspace is redirected')
            expected[directory] = _identity(info)
            guard.include(expected)
        yield folder, guard, expected


@contextmanager
def _namespace(folder):
    path = folder / '.spt-profiles.lock'
    try:
        fd = _open_record(path, exclusive=True)
    except FileExistsError:
        fd = _open_record(path)
    locked = False
    try:
        for attempt in range(40):
            try:
                _lock(fd)
                locked = True
                break
            except OSError:
                if attempt == 39:
                    raise
                time.sleep(0.005)
        yield
    finally:
        try:
            if locked:
                _lock(fd, unlock=True)
        finally:
            os.close(fd)


def _read_ownership(fd, marker):
    if os.fstat(fd).st_size > _RECORD_LIMIT:
        raise ValueError('Profile ownership record exceeds its bound')
    os.lseek(fd, 0, os.SEEK_SET)
    record = json.loads(os.read(fd, _RECORD_LIMIT + 1))
    match = _MARKER.fullmatch(marker.name)
    if (not isinstance(record, dict)
            or set(record) != {'schema', 'kind', 'profile', 'device', 'inode'}
            or type(record['schema']) is not int or record['schema'] != 1
            or not isinstance(record['kind'], str) or record['kind'] not in _KINDS
            or match is None or record['profile'] != record['kind'] + '-' + match[1]
            or type(record['device']) is not int or record['device'] < 0
            or type(record['inode']) is not int or record['inode'] <= 0):
        raise ValueError('Profile ownership record is invalid')
    return record


def _tree(folder, identity, guard, expected, deadline):
    """Inspect the complete tree before mutation; never follow a link target."""
    directories, files = [], []
    pending = [(folder, identity)]
    count = 0
    while pending:
        if time.monotonic() >= deadline:
            raise TimeoutError('Profile recovery inspection budget exceeded')
        directory, wanted = pending.pop()
        info = directory.lstat()
        if not _ordinary(info, directory=True) or _identity(info) != wanted:
            raise ValueError('Owned profile directory identity changed')
        expected[directory] = wanted
        guard.include(expected)
        directories.append((directory, wanted))
        with os.scandir(directory) as entries:
            for entry in entries:
                count += 1
                if count > _TREE_LIMIT or time.monotonic() >= deadline:
                    raise TimeoutError('Profile recovery inspection budget exceeded')
                path = directory / entry.name
                # DirEntry.stat has incomplete Windows identity/link fields.
                info = path.lstat()
                if _ordinary(info, directory=True):
                    pending.append((path, _identity(info)))
                elif _ordinary(info):
                    files.append((path, _identity(info)))
                else:
                    raise ValueError('Owned profile contains a redirected or shared entry')
    return directories, files


def _remove_tree(folder, identity, guard, expected, deadline):
    try:
        info = folder.lstat()
    except FileNotFoundError:
        return
    if not _ordinary(info, directory=True) or _identity(info) != identity:
        raise ValueError('Owned profile directory identity changed')
    directories, files = _tree(folder, identity, guard, expected, deadline)
    for path, wanted in files:
        if time.monotonic() >= deadline:
            raise TimeoutError('Profile recovery removal budget exceeded')
        info = path.lstat()
        if not _ordinary(info) or _identity(info) != wanted:
            raise ValueError('Owned profile file identity changed')
        path.unlink()
    for path, wanted in reversed(directories):
        if time.monotonic() >= deadline:
            raise TimeoutError('Profile recovery removal budget exceeded')
        info = path.lstat()
        if not _ordinary(info, directory=True) or _identity(info) != wanted:
            raise ValueError('Owned profile directory identity changed')
        guard.release(path)
        expected.pop(path)
        path.rmdir()


def _reap_one(folder, marker, deadline):
    fd = _open_record(marker)
    removed = False
    try:
        _lock(fd)  # A live owner or unprovable lease always retains the tree.
        record = _read_ownership(fd, marker)
        marker_identity = _identity(os.fstat(fd))
        profile = folder / record['profile']
        # A separate guard confines a failed candidate to its own held paths.
        with _cache(folder.parent) as (_, guard, expected):
            _remove_tree(profile, (record['device'], record['inode']), guard, expected, deadline)
        removed = True
    finally:
        os.close(fd)  # Release before unlinking the marker on Windows.
    if removed:
        info = marker.lstat()
        if _ordinary(info) and _identity(info) == marker_identity:
            marker.unlink()


def _reap(root, marker_name=None):
    deadline = time.monotonic() + _REAP_SECONDS
    try:
        with _cache(root) as (folder, _, _), _namespace(folder):
            if marker_name is None:
                candidates = []
                with os.scandir(folder) as entries:
                    for ordinal, entry in enumerate(entries):
                        if ordinal >= _SCAN_LIMIT or time.monotonic() >= deadline:
                            return
                        if _MARKER.fullmatch(entry.name):
                            candidates.append(folder / entry.name)
            else:
                candidates = [folder / marker_name]
            for marker in candidates:
                if time.monotonic() >= deadline:
                    return
                try:
                    _reap_one(folder, marker, deadline)
                except (OSError, ValueError, TypeError, RecursionError):
                    # Preserve uncertain ownership, live locks and in-use files.
                    # The marker remains available for the next bounded attempt.
                    continue
    except (OSError, ValueError, TypeError, RecursionError):
        return


def reap_profiles(root):
    """Best-effort recovery of abandoned managed profiles, without creating root."""
    _reap(root)


@contextmanager
def temporary_profile(root, kind):
    """Publish durable ownership and acquire its active lease before browser use."""
    if not isinstance(kind, str) or kind not in _KINDS:
        raise ValueError('Unsupported temporary profile kind')
    lease = None
    marker = None
    try:
        with _cache(root, create=True) as (folder, guard, expected):
            with _namespace(folder):
                token = uuid.uuid4().hex
                profile = folder / (kind + '-' + token)
                marker = folder / ('.spt-profile-' + token + '.json')
                lease = _open_record(marker, exclusive=True)
                _lock(lease)
                profile.mkdir(mode=0o700)
                info = profile.lstat()
                if not _ordinary(info, directory=True):
                    raise ValueError('New profile directory is redirected')
                expected[profile] = _identity(info)
                guard.include(expected)
                record = {'schema': 1, 'kind': kind, 'profile': profile.name,
                          'device': info.st_dev, 'inode': info.st_ino}
                data = json.dumps(record, ensure_ascii=True).encode('utf-8')
                os.lseek(lease, 0, os.SEEK_SET)
                if os.write(lease, data) != len(data):
                    raise OSError('Incomplete profile ownership write')
                os.fsync(lease)
            yield profile
    finally:
        if lease is not None:
            try:
                os.close(lease)
            except OSError:
                pass
        if marker is not None:
            # Cleanup may fail while Chromium closes a file. It must never
            # replace CaptureCancelled or another original operation result.
            _reap(root, marker.name)
