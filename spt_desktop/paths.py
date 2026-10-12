"""Resolve Windows user folders without assuming where Downloads lives."""
import ctypes
from ctypes import wintypes
from pathlib import Path
import re
import sys
import uuid

DOWNLOADS = '374DE290-123F-4565-9164-39C4925E467B'
LOCAL_APP_DATA = 'F1B32785-6FBA-4FCF-9D55-7B8E7F157091'


class _GUID(ctypes.Structure):
    _fields_ = [('Data1', ctypes.c_uint32), ('Data2', ctypes.c_uint16),
                ('Data3', ctypes.c_uint16), ('Data4', ctypes.c_ubyte * 8)]


def _known_folder(identifier: str) -> Path:
    if sys.platform != 'win32':
        raise OSError('Windows Known Folder API is required')
    shell = ctypes.WinDLL('shell32', use_last_error=True)
    ole = ctypes.WinDLL('ole32', use_last_error=True)
    shell.SHGetKnownFolderPath.argtypes = [ctypes.POINTER(_GUID), wintypes.DWORD,
                                          wintypes.HANDLE, ctypes.POINTER(ctypes.c_void_p)]
    shell.SHGetKnownFolderPath.restype = ctypes.c_long
    ole.CoTaskMemFree.argtypes = [ctypes.c_void_p]
    ole.CoTaskMemFree.restype = None
    guid = _GUID.from_buffer_copy(uuid.UUID(identifier).bytes_le)
    allocated = ctypes.c_void_p()
    try:
        result = shell.SHGetKnownFolderPath(ctypes.byref(guid), 0, None, ctypes.byref(allocated))
        if result < 0 or not allocated.value:
            raise OSError(f'Windows Known Folder resolution failed: {result & 0xffffffff:#x}')
        path = Path(ctypes.wstring_at(allocated))
        if not path.is_absolute():
            raise OSError('Windows Known Folder returned a non-absolute path')
        return path
    finally:
        if allocated.value:
            ole.CoTaskMemFree(allocated)


def workspace_root() -> Path:
    return _known_folder(LOCAL_APP_DATA) / 'SPTDownloader'


def downloads_folder() -> Path:
    return _known_folder(DOWNLOADS)


def safe_taxpayer_name(name: str, max_length: int = 100) -> str:
    if not isinstance(name, str) or not name.strip() or not name.rstrip(' .'):
        raise ValueError('Nama WP is missing; retain the local job instead of inventing a folder name')
    if all(ord(char) < 32 for char in name) or max_length < 1:
        raise ValueError('Nama WP or maximum folder length is invalid')
    result = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', '_', name)
    result = result[:max_length].rstrip(' .')
    if not result:
        raise ValueError('Nama WP cannot be used as a Windows folder component')
    return result
