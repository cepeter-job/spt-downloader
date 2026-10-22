"""Contain the external native probe and all inherited children before it starts."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    if sys.platform != 'win32' or os.environ.get('GITHUB_ACTIONS') != 'true':
        raise RuntimeError('GitHub Windows runner required')
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from spt_desktop.windows import ProcessJob
    output = Path(sys.argv[sys.argv.index('-OutputDirectory') + 1])
    if output.exists():
        raise ValueError('new probe directory required')
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.QueryInformationJobObject.argtypes = (wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p)
    kernel.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.WaitForSingleObject.argtypes = (wintypes.HANDLE, wintypes.DWORD)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    job = ProcessJob()
    process = None
    handles = []
    try:
        process = job.spawn(['powershell', '-NoProfile', '-STA', '-File',
                             str(Path(__file__).with_name('reader_probe.ps1')), *sys.argv[1:]])
        code = process.wait(timeout=240)
    finally:
        buffer = ctypes.create_string_buffer(8 + ctypes.sizeof(ctypes.c_size_t) * 1024)
        if not kernel.QueryInformationJobObject(job._handle, 3, buffer, len(buffer), None):
            job.close()
            raise ctypes.WinError(ctypes.get_last_error())
        count = ctypes.c_uint32.from_buffer(buffer, 4).value
        if count > 1024:
            job.close()
            raise RuntimeError('owned process inventory overflow')
        for index in range(count):
            pid = ctypes.c_size_t.from_buffer(buffer, 8 + index * ctypes.sizeof(ctypes.c_size_t)).value
            handle = kernel.OpenProcess(0x00100000, False, pid)
            if handle:
                handles.append(handle)
        job.close()
        cleaned = True
        for handle in handles:
            cleaned = kernel.WaitForSingleObject(handle, 15000) == 0 and cleaned
            kernel.CloseHandle(handle)
        if process is not None:
            process.wait(timeout=15)
        if output.exists():
            (output / 'owned-tree.json').write_text(json.dumps({'contained_before_resume': True,
                'remaining_owned_processes_at_close': count, 'cleanup_complete': cleaned}), encoding='utf-8')
        if not cleaned:
            raise RuntimeError('owned reader tree cleanup incomplete')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
