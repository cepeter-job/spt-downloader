"""Read only this application's exact-origin Windows generic credentials."""
import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
import sys

LOGIN_ORIGIN = 'https://satu.intranet.pajak.go.id'
ALLOWED_ORIGINS = (LOGIN_ORIGIN,
                   'https://coretax.intranet.pajak.go.id')
_PREFIX = 'SPTDownloader:login:'
_NOT_FOUND = 1168
_MAX_BLOB = 2560


@dataclass(frozen=True)
class Login:
    identifier: str
    password: str = field(repr=False)


class _Credential(ctypes.Structure):
    _fields_ = [('Flags', wintypes.DWORD), ('Type', wintypes.DWORD),
                ('TargetName', wintypes.LPWSTR), ('Comment', wintypes.LPWSTR),
                ('LastWritten', wintypes.FILETIME), ('CredentialBlobSize', wintypes.DWORD),
                ('CredentialBlob', ctypes.POINTER(ctypes.c_ubyte)), ('Persist', wintypes.DWORD),
                ('AttributeCount', wintypes.DWORD), ('Attributes', ctypes.c_void_p),
                ('TargetAlias', wintypes.LPWSTR), ('UserName', wintypes.LPWSTR)]


def _target(origin: str) -> str:
    if origin not in ALLOWED_ORIGINS:
        raise ValueError('Credential origin must exactly match an approved HTTPS login origin')
    return _PREFIX + origin


def _api():
    if sys.platform != 'win32':
        raise OSError('Windows Credential Manager is required')
    api = ctypes.WinDLL('advapi32', use_last_error=True)
    api.CredWriteW.argtypes = [ctypes.POINTER(_Credential), wintypes.DWORD]
    api.CredWriteW.restype = wintypes.BOOL
    api.CredReadW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                             ctypes.POINTER(ctypes.POINTER(_Credential))]
    api.CredReadW.restype = wintypes.BOOL
    api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
    api.CredDeleteW.restype = wintypes.BOOL
    api.CredFree.argtypes = [ctypes.c_void_p]
    api.CredFree.restype = None
    return api


def _write_credential(target: str, username: str, blob: bytes) -> None:
    api = _api()
    buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
    credential = _Credential()
    credential.Type = 1  # Generic; this does not impersonate a Windows/network account.
    credential.TargetName = target
    credential.UserName = username
    credential.CredentialBlobSize = len(blob)
    credential.CredentialBlob = buffer
    credential.Persist = 2  # Local-machine persistence remains scoped to the current Windows user.
    try:
        if not api.CredWriteW(ctypes.byref(credential), 0):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        ctypes.memset(buffer, 0, len(blob))


def _read_credential(target: str) -> tuple[str, bytes] | None:
    api = _api()
    allocated = ctypes.POINTER(_Credential)()
    if not api.CredReadW(target, 1, 0, ctypes.byref(allocated)):
        error = ctypes.get_last_error()
        if error == _NOT_FOUND:
            return None
        raise ctypes.WinError(error)
    try:
        credential = allocated.contents
        if credential.CredentialBlobSize > _MAX_BLOB or credential.CredentialBlobSize % 2:
            raise OSError('Application credential data is invalid; replace it in Settings')
        blob = ctypes.string_at(credential.CredentialBlob, credential.CredentialBlobSize)
        return credential.UserName or '', blob
    finally:
        api.CredFree(allocated)


def _delete_credential(target: str) -> None:
    api = _api()
    if not api.CredDeleteW(target, 1, 0):
        error = ctypes.get_last_error()
        if error != _NOT_FOUND:
            raise ctypes.WinError(error)


def save_login(origin: str, identifier: str, password: str) -> None:
    target = _target(origin)
    if not isinstance(identifier, str) or not identifier.strip() or '\0' in identifier:
        raise ValueError('Account identifier is empty or invalid')
    if not isinstance(password, str) or not password or '\0' in password:
        raise ValueError('Password is empty or invalid')
    blob = password.encode('utf-16-le')
    if len(blob) > _MAX_BLOB:
        raise ValueError('Password exceeds the Windows credential storage limit')
    _write_credential(target, identifier, blob)


def read_login(origin: str) -> Login | None:
    saved = _read_credential(_target(origin))
    if saved is None:
        return None
    identifier, blob = saved
    try:
        return Login(identifier, blob.decode('utf-16-le'))
    except UnicodeError:
        raise OSError('Application credential data is invalid; replace it in Settings') from None


def delete_login(origin: str) -> None:
    _delete_credential(_target(origin))
