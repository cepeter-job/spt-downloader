"""Own application instances and worker process trees, never personal browsers."""
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import subprocess
import sys


class _ThreadEntry(ctypes.Structure):
    _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                ('th32ThreadID', wintypes.DWORD), ('th32OwnerProcessID', wintypes.DWORD),
                ('tpBasePri', wintypes.LONG), ('tpDeltaPri', wintypes.LONG), ('dwFlags', wintypes.DWORD)]


class _BasicLimits(ctypes.Structure):
    _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64), ('PerJobUserTimeLimit', ctypes.c_int64),
                ('LimitFlags', wintypes.DWORD), ('MinimumWorkingSetSize', ctypes.c_size_t),
                ('MaximumWorkingSetSize', ctypes.c_size_t), ('ActiveProcessLimit', wintypes.DWORD),
                ('Affinity', ctypes.c_size_t), ('PriorityClass', wintypes.DWORD),
                ('SchedulingClass', wintypes.DWORD)]


class _IoCounters(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint64) for name in ('ReadOperationCount', 'WriteOperationCount',
                'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount', 'OtherTransferCount')]


class _ExtendedLimits(ctypes.Structure):
    _fields_ = [('BasicLimitInformation', _BasicLimits), ('IoInfo', _IoCounters),
                ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                ('PeakProcessMemoryUsed', ctypes.c_size_t), ('PeakJobMemoryUsed', ctypes.c_size_t)]


def _kernel():
    if sys.platform != 'win32':
        raise OSError('Native Windows process ownership is required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel.CreateMutexW.restype = wintypes.HANDLE
    kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    kernel.CreateJobObjectW.restype = wintypes.HANDLE
    kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    kernel.SetInformationJobObject.restype = wintypes.BOOL
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    kernel.AssignProcessToJobObject.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Thread32First.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
    kernel.Thread32First.restype = wintypes.BOOL
    kernel.Thread32Next.argtypes = [wintypes.HANDLE, ctypes.POINTER(_ThreadEntry)]
    kernel.Thread32Next.restype = wintypes.BOOL
    kernel.OpenThread.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenThread.restype = wintypes.HANDLE
    kernel.ResumeThread.argtypes = [wintypes.HANDLE]
    kernel.ResumeThread.restype = wintypes.DWORD
    return kernel


def _resume_primary(kernel, pid: int) -> None:
    # Popen closes the original thread handle. A still-suspended process has one primary thread.
    snapshot = kernel.CreateToolhelp32Snapshot(0x4, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = _ThreadEntry()
        entry.dwSize = ctypes.sizeof(entry)
        threads = []
        found = kernel.Thread32First(snapshot, ctypes.byref(entry))
        while found:
            if entry.th32OwnerProcessID == pid:
                threads.append(entry.th32ThreadID)
            entry.dwSize = ctypes.sizeof(entry)
            found = kernel.Thread32Next(snapshot, ctypes.byref(entry))
        error = ctypes.get_last_error()
        if error != 18:
            raise ctypes.WinError(error)
    finally:
        kernel.CloseHandle(snapshot)
    if len(threads) != 1:
        raise OSError('Could not identify the suspended worker primary thread')
    thread = kernel.OpenThread(0x2, False, threads[0])
    if not thread:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        count = kernel.ResumeThread(thread)
        if count == 0xffffffff:
            raise ctypes.WinError(ctypes.get_last_error())
        if count != 1:
            raise OSError('Unexpected worker suspension count; refusing unsafe startup')
    finally:
        kernel.CloseHandle(thread)


class InstanceLock:
    def __init__(self, root: Path):
        self._kernel = _kernel()
        digest = hashlib.sha256(str(Path(root).resolve()).casefold().encode('utf-8')).hexdigest()
        self._handle = self._kernel.CreateMutexW(None, False, 'Local\\SPTDownloader-' + digest)
        error = ctypes.get_last_error()
        if not self._handle:
            raise ctypes.WinError(error)
        if error == 183:
            self.close()
            raise RuntimeError('SPT Downloader is already running / aplikasi sudah berjalan')

    def close(self) -> None:
        handle, self._handle = self._handle, None
        if handle and not self._kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class ProcessJob:
    def __init__(self):
        self._kernel = _kernel()
        self._handle = self._kernel.CreateJobObjectW(None, None)
        if not self._handle:
            raise ctypes.WinError(ctypes.get_last_error())
        limits = _ExtendedLimits()
        limits.BasicLimitInformation.LimitFlags = 0x2000  # KILL_ON_JOB_CLOSE; parent owns the handle.
        if not self._kernel.SetInformationJobObject(self._handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
            error = ctypes.get_last_error()
            self.close()
            raise ctypes.WinError(error)

    def spawn(self, argv: list[str], **kwargs) -> subprocess.Popen:
        if not self._handle:
            raise RuntimeError('Worker process job is already closed')
        flags = kwargs.pop('creationflags', 0) | 0x4 | 0x08000000
        process = subprocess.Popen(argv, creationflags=flags, **kwargs)
        try:
            # uv venv launchers spawn interpreters before Python-level handshakes can run.
            self.assign(process.pid)
            _resume_primary(self._kernel, process.pid)
        except BaseException:
            try:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
                process.wait(timeout=10)
            finally:
                for stream in (process.stdin, process.stdout, process.stderr):
                    if stream is not None:
                        stream.close()
            raise
        return process

    def assign(self, pid: int) -> None:
        if not self._handle:
            raise RuntimeError('Worker process job is already closed')
        process = self._kernel.OpenProcess(0x0101, False, pid)
        if not process:
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            if not self._kernel.AssignProcessToJobObject(self._handle, process):
                raise ctypes.WinError(ctypes.get_last_error())
        finally:
            self._kernel.CloseHandle(process)

    def close(self) -> None:
        handle, self._handle = self._handle, None
        if handle and not self._kernel.CloseHandle(handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
