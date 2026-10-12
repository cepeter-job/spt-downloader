"""Small filesystem primitives for the Windows desktop output transaction.

Windows sharing restrictions last until the owning handle is closed. Directory
handles here deny delete sharing, which blocks rename/delete of those
directories. Write sharing permits Windows to open a destination directory
with add-child access during a rename. These handles do not prohibit every
FILE_WRITE_ATTRIBUTES operation.
Callers retain all ancestors throughout mutation and release only their own
empty leaves or staged subtree when a directory itself must be removed/moved.

Other platforms retain checked reads and ordinary fresh-folder publication.
Their directory guard does not pin paths, and their checked directory rename
does not provide the Windows protection against concurrent namespace changes.

API contracts:
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-movefileexw
https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/open-osfhandle
https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-fsa/87f86c9b-6c2a-4803-84b7-131a74a434fa
"""
from contextlib import contextmanager
import ctypes.wintypes
import errno
import os
from pathlib import Path
import stat
import sys


_GENERIC_READ = 0x80000000
_FILE_SHARE_READ = 0x00000001
_FILE_SHARE_WRITE = 0x00000002
_OPEN_EXISTING = 3
_FILE_FLAG_BACKUP_SEMANTICS = 0x02000000
_FILE_FLAG_OPEN_REPARSE_POINT = 0x00200000
_FILE_ATTRIBUTE_REPARSE_POINT = 0x00000400


def _kernel():
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = [
        ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.c_void_p,
        ctypes.wintypes.DWORD, ctypes.wintypes.DWORD, ctypes.wintypes.HANDLE,
    ]
    kernel.CreateFileW.restype = ctypes.wintypes.HANDLE
    kernel.CloseHandle.argtypes = [ctypes.wintypes.HANDLE]
    kernel.CloseHandle.restype = ctypes.wintypes.BOOL
    kernel.MoveFileExW.argtypes = [
        ctypes.wintypes.LPCWSTR, ctypes.wintypes.LPCWSTR, ctypes.wintypes.DWORD,
    ]
    kernel.MoveFileExW.restype = ctypes.wintypes.BOOL
    return kernel


def _absolute(path):
    path = Path(path)
    # Do not let normalization conceal a symlink/junction followed by "..".
    if '..' in path.parts:
        raise ValueError('Output path cannot contain parent traversal')
    return path.absolute()


def _native_path(path):
    name = str(path)
    if name.startswith('\\\\?\\'):
        return name
    if name.startswith('\\\\'):
        return '\\\\?\\UNC\\' + name[2:]
    # Preserve the trailing slash of a drive root: this opens its directory,
    # never the raw volume device. Extended paths also avoid MAX_PATH truncation.
    return '\\\\?\\' + name


def _identity(info):
    return info.st_dev, info.st_ino


def _state(info):
    return (*_identity(info), info.st_size, info.st_mtime_ns)


def _check_type(info, *, directory):
    correct_type = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if (not correct_type or stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & _FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError('Output path must be an ordinary directory or regular file')
    if not info.st_ino:
        raise ValueError('Output filesystem does not provide a usable file identity')


def _file_info(path):
    for parent in reversed(path.parents):
        _check_type(parent.lstat(), directory=True)
    info = path.lstat()
    _check_type(info, directory=False)
    return info


def _open_windows_fd(path, *, directory):
    import msvcrt

    kernel = _kernel()
    flags = _FILE_FLAG_OPEN_REPARSE_POINT
    sharing = _FILE_SHARE_READ
    if directory:
        flags |= _FILE_FLAG_BACKUP_SEMANTICS
        # MS-FSA 2.1.5.15.12 opens the rename target's parent with
        # FILE_ADD_FILE / FILE_ADD_SUBDIRECTORY. Permit those writes while
        # still denying DELETE on the held directory itself.
        sharing |= _FILE_SHARE_WRITE
    # GENERIC_READ includes directory-list access, not just attribute access.
    # No security attributes means the native handle is not inheritable.
    handle = kernel.CreateFileW(
        _native_path(path), _GENERIC_READ, sharing, None,
        _OPEN_EXISTING, flags, None,
    )
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        # The CRT descriptor takes ownership on success. os.close/fdopen.close
        # then closes the native handle; never CloseHandle it a second time.
        return msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY | os.O_NOINHERIT)
    except BaseException:
        kernel.CloseHandle(handle)
        raise


class DirectoryGuard:
    """Pin and revalidate the expected directory identities on Windows.

    include() requires every lexical ancestor to be supplied or already owned.
    A successful acquisition remains owned even if a later acquisition fails.
    release() affects only the named leaf; it never closes an ancestor or a
    descendant implicitly. On other platforms the same checks run without
    native handles, so they cannot prevent concurrent rename or deletion.
    """

    def __init__(self):
        self._entries = {}
        self._closed = False

    def include(self, expected):
        if self._closed:
            raise RuntimeError('Output directory guard is closed')
        identities = {path: entry[0] for path, entry in self._entries.items()}
        for name, identity in expected.items():
            path = _absolute(name)
            if path in identities and identities[path] != identity:
                raise ValueError('Output directory identity changed')
            identities[path] = identity
        if any(parent not in identities for path in identities for parent in path.parents):
            raise ValueError('Output directory guard requires every ancestor')
        for path in sorted(identities, key=lambda item: len(item.parts)):
            identity = identities[path]
            before = path.lstat()
            _check_type(before, directory=True)
            if _identity(before) != identity:
                raise ValueError('Output directory changed since inspection')
            if path in self._entries:
                descriptor = self._entries[path][1]
                if descriptor is not None:
                    opened = os.fstat(descriptor)
                    _check_type(opened, directory=True)
                    if _identity(opened) != identity:
                        raise ValueError('Held output directory identity changed')
                continue
            descriptor = None
            try:
                if sys.platform == 'win32':
                    descriptor = _open_windows_fd(path, directory=True)
                    # Use CPython's normalization for both sides. Windows file
                    # IDs can be represented differently in 3.11 and 3.14.
                    opened = os.fstat(descriptor)
                    _check_type(opened, directory=True)
                    if _identity(opened) != identity:
                        raise ValueError('Output directory changed while opening')
                after = path.lstat()
                _check_type(after, directory=True)
                if _identity(after) != identity:
                    raise ValueError('Output directory changed while opening')
            except BaseException:
                if descriptor is not None:
                    os.close(descriptor)
                raise
            self._entries[path] = (identity, descriptor)

    def release(self, path):
        """Close one owned leaf before its caller-controlled rmdir or rename."""
        path = _absolute(path)
        if any(path in held.parents for held in self._entries):
            raise ValueError('Release owned output directory descendants first')
        entry = self._entries.pop(path, None)
        if entry is not None and entry[1] is not None:
            os.close(entry[1])

    def close(self):
        entries, self._entries = self._entries, {}
        self._closed = True
        first_error = None
        for path in sorted(entries, key=lambda item: len(item.parts), reverse=True):
            descriptor = entries[path][1]
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError as error:
                    if first_error is None:
                        first_error = error
        if first_error is not None:
            raise first_error

    def __enter__(self):
        if self._closed:
            raise RuntimeError('Output directory guard is closed')
        return self

    def __exit__(self, *args):
        self.close()


@contextmanager
def locked_file(path):
    """Yield a checked binary reader, denying write/delete sharing on Windows.

    The caller must keep DirectoryGuard ancestors held when path stability is
    required during mutation. Other platforms use checked ordinary file reads;
    they do not acquire the native Windows sharing restrictions.
    """
    path = _absolute(path)
    before = _file_info(path)
    if sys.platform == 'win32':
        descriptor = _open_windows_fd(path, directory=False)
        try:
            stream = os.fdopen(descriptor, 'rb')
        except BaseException:
            os.close(descriptor)
            raise
    else:
        stream = path.open('rb')
    with stream:
        opened = os.fstat(stream.fileno())
        _check_type(opened, directory=False)
        if _state(opened) != _state(before) or _state(_file_info(path)) != _state(before):
            raise ValueError('Output file changed while opening')
        yield stream
        after = os.fstat(stream.fileno())
        _check_type(after, directory=False)
        if _state(after) != _state(before) or _state(_file_info(path)) != _state(before):
            raise ValueError('Output file changed while being read')


def move_no_replace(source, target):
    """Move without replacing a Windows destination or copying across volumes.

    Callers hold directory guards and release any handle to the source object
    before moving it. Portable file moves use link/unlink: if unlink fails the
    two names remain for caller recovery. Portable directory moves retain only
    a precheck and ordinary rename, with no concurrent no-clobber guarantee.
    """
    source, target = _absolute(source), _absolute(target)
    if sys.platform == 'win32':
        if not _kernel().MoveFileExW(_native_path(source), _native_path(target), 0):
            raise ctypes.WinError(ctypes.get_last_error())
        return
    info = source.lstat()
    directory = stat.S_ISDIR(info.st_mode)
    _check_type(info, directory=directory)
    if directory:
        if os.path.lexists(target):
            raise FileExistsError(errno.EEXIST, 'Output move destination already exists')
        os.rename(source, target)
    else:
        # link() refuses an existing target; there is no overwrite/copy fallback.
        os.link(source, target, follow_symlinks=False)
        if (_identity(source.lstat()) != _identity(info)
                or _identity(target.lstat()) != _identity(info)):
            raise ValueError('Output file changed during portable move')
        source.unlink()
