"""Bounded local segments; never rotate a file shared by different processes."""
from contextlib import contextmanager
import os
from pathlib import Path
import re
import stat
import sys
import time

from .output_windows import DirectoryGuard

_NAME = re.compile(r'(diag-(?:gui|worker|cli)-[0-9a-f]{32})-[0-9]{5}\.jsonl')


def _regular(info):
    return (stat.S_ISREG(info.st_mode) and info.st_nlink == 1
            and not getattr(info, 'st_file_attributes', 0) & 0x400)


def _lock(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(fd):
    os.lseek(fd, 0, os.SEEK_SET)
    if sys.platform == 'win32':
        import msvcrt
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(fd, fcntl.LOCK_UN)


def _open_regular(path, *, exclusive=False):
    flags = os.O_RDWR | getattr(os, 'O_BINARY', 0) | getattr(os, 'O_NOFOLLOW', 0)
    if exclusive:
        flags |= os.O_CREAT | os.O_EXCL
    before = None if exclusive else path.lstat()
    if before is not None and not _regular(before):
        raise ValueError('Diagnostic file is redirected or shared')
    fd = os.open(path, flags, 0o600)
    try:
        opened, after = os.fstat(fd), path.lstat()
        if (not _regular(opened) or not _regular(after)
                or (opened.st_dev, opened.st_ino) != (after.st_dev, after.st_ino)
                or before is not None and (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino)):
            raise ValueError('Diagnostic file identity changed')
        return fd
    except BaseException:
        os.close(fd)
        raise


class SegmentStore:
    """Only the sink thread owns this instance and its native handles."""

    def __init__(self, root, role, session_id, *, max_bytes, backup_count, max_files, retention_days):
        root = Path(root)
        if not root.is_absolute() or '..' in root.parts:
            raise ValueError('Diagnostic root must be an absolute ordinary path')
        self.folder = root / 'logs'
        self.prefix = f'diag-{role}-{session_id}'
        self.max_bytes, self.backup_count = max_bytes, backup_count
        self.max_files, self.retention_days = max_files, retention_days
        self.guard = DirectoryGuard()
        self.expected = {}
        self.stream = None
        self.lease = None
        self.size = 0
        self.index = 0
        self.segments = []
        try:
            for path in reversed((self.folder, *self.folder.parents)):
                try:
                    info = path.lstat()
                except FileNotFoundError:
                    path.mkdir(mode=0o700)
                    info = path.lstat()
                if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
                    raise ValueError('Diagnostic directory is redirected')
                self.expected[path] = (info.st_dev, info.st_ino)
                self.guard.include(self.expected)
            with self._namespace():
                self.lease = _open_regular(self.folder / (self.prefix + '.active'), exclusive=True)
                _lock(self.lease)
        except BaseException:
            self.close()
            raise

    @contextmanager
    def _namespace(self):
        # Serialize creation/pruning, never product work. Contention waits only
        # on the private sink thread and has a short, bounded deadline.
        self.guard.include(self.expected)
        path = self.folder / '.diagnostics.lock'
        try:
            fd = _open_regular(path, exclusive=True)
        except FileExistsError:
            fd = _open_regular(path)
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
                    _unlock(fd)
            finally:
                os.close(fd)

    def _active(self, prefix):
        if prefix == self.prefix:
            return True
        path = self.folder / (prefix + '.active')
        try:
            fd = _open_regular(path)
        except FileNotFoundError:
            return False
        except (OSError, ValueError):
            return True
        try:
            try:
                _lock(fd)
            except OSError:
                return True
            _unlock(fd)
            return False
        finally:
            os.close(fd)

    @staticmethod
    def _remove(path, identity):
        try:
            info = path.lstat()
            if _regular(info) and (info.st_dev, info.st_ino) == identity:
                path.unlink()
                return True
        except OSError:
            pass  # Retention never grants permission to remove a different file.
        return False

    def _prune(self):
        while len(self.segments) >= self.backup_count:
            path, identity = self.segments[0]
            if not self._remove(path, identity):
                raise OSError('Diagnostic rotation cannot safely reclaim its segment')
            self.segments.pop(0)
        candidates = []
        # An unexpected huge directory cannot create an unbounded cleanup scan.
        with os.scandir(self.folder) as entries:
            for ordinal, entry in enumerate(entries):
                if ordinal >= 4096:
                    raise OSError('Diagnostic directory has too many entries')
                match = _NAME.fullmatch(entry.name)
                if match:
                    info = entry.stat(follow_symlinks=False)
                    if _regular(info):
                        candidates.append((info.st_mtime, Path(entry.path), info, match[1]))
        count = len(candidates)
        cutoff = time.time() - self.retention_days * 86400
        for modified, path, info, prefix in sorted(candidates):
            if (modified < cutoff or count >= self.max_files) and not self._active(prefix):
                if self._remove(path, (info.st_dev, info.st_ino)):
                    count -= 1
                    # A crashed session's unlocked lease must not accumulate.
                    lease = self.folder / (prefix + '.active')
                    try:
                        lease_info = lease.lstat()
                        self._remove(lease, (lease_info.st_dev, lease_info.st_ino))
                    except FileNotFoundError:
                        pass
        if count >= self.max_files:
            raise OSError('Diagnostic retention budget is occupied by active files')

    def write(self, line):
        data = line.encode('utf-8')
        if len(data) > min(self.max_bytes, 4096):
            raise ValueError('Diagnostic record exceeds its bound')
        if self.stream is None or self.size + len(data) > self.max_bytes:
            if self.stream is not None:
                self.stream.close()
                self.stream = None
            with self._namespace():
                self._prune()
                if self.index > 99999:
                    raise OSError('Diagnostic segment namespace exhausted')
                path = self.folder / f'{self.prefix}-{self.index:05d}.jsonl'
                self.index += 1
                fd = _open_regular(path, exclusive=True)
                info = os.fstat(fd)
                self.stream = os.fdopen(fd, 'wb', buffering=0)
                self.segments.append((path, (info.st_dev, info.st_ino)))
                self.size = 0
        written = self.stream.write(data)
        if written != len(data):
            self.stream.truncate(self.size)
            raise OSError('Incomplete diagnostic write')
        self.size += written

    def close(self):
        try:
            if self.stream is not None:
                self.stream.close()
                self.stream = None
        finally:
            try:
                if self.lease is not None:
                    info = os.fstat(self.lease)
                    os.close(self.lease)
                    self.lease = None
                    self._remove(self.folder / (self.prefix + '.active'), (info.st_dev, info.st_ino))
            finally:
                self.guard.close()
