"""Contain the external native probe and all inherited children before it starts."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time


def record_probe_exit(output, code, *, timed_out):
    """Only called after this invocation has reserved a new probe output path."""
    output.mkdir(exist_ok=True)
    (output / 'probe-exit.json').write_text(json.dumps({
        'schema': 1, 'exit_code': code, 'timed_out': timed_out,
        'phase_retained': (output / 'probe-phase.json').is_file(),
        'report_retained': (output / 'report.json').is_file(),
        'failure_retained': (output / 'probe-failure.json').is_file(),
    }), encoding='utf-8')


def close_owned(kernel, job, pids, last_error):
    """Request termination and certify only exits actually observed on handles."""
    handles, unverified = [], []
    for pid in pids:
        handle = kernel.OpenProcess(0x00100000, False, pid)
        if handle:
            handles.append((pid, handle))
        else:
            unverified.append({'pid': pid, 'operation': 'OpenProcess', 'winerror': last_error()})
    job.close()
    deadline = time.monotonic() + 15
    for pid, handle in handles:
        try:
            wait = kernel.WaitForSingleObject(handle, max(0, int((deadline - time.monotonic()) * 1000)))
            if wait != 0:
                unverified.append({'pid': pid, 'operation': 'WaitForSingleObject', 'result': int(wait)})
        finally:
            kernel.CloseHandle(handle)
    return {'contained_before_resume': True, 'remaining_owned_processes_at_close': len(pids),
            'cleanup_complete': not unverified, 'unverified_processes': unverified}


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
    code = None
    timed_out = False
    try:
        process = job.spawn(['powershell', '-NoProfile', '-STA', '-File',
                             str(Path(__file__).with_name('reader_probe.ps1')), *sys.argv[1:]])
        code = process.wait(timeout=240)
    except subprocess.TimeoutExpired:
        timed_out = True
        raise
    finally:
        buffer = ctypes.create_string_buffer(8 + ctypes.sizeof(ctypes.c_size_t) * 1024)
        if not kernel.QueryInformationJobObject(job._handle, 3, buffer, len(buffer), None):
            job.close()
            raise ctypes.WinError(ctypes.get_last_error())
        count = ctypes.c_uint32.from_buffer(buffer, 4).value
        if count > 1024:
            job.close()
            raise RuntimeError('owned process inventory overflow')
        pids = [ctypes.c_size_t.from_buffer(buffer, 8 + index * ctypes.sizeof(ctypes.c_size_t)).value
                for index in range(count)]
        cleanup = close_owned(kernel, job, pids, ctypes.get_last_error)
        record_probe_exit(output, code, timed_out=timed_out)
        if process is not None:
            process.wait(timeout=15)
        if output.exists():
            (output / 'owned-tree.json').write_text(json.dumps(cleanup), encoding='utf-8')
        if not cleanup['cleanup_complete']:
            raise RuntimeError('owned reader tree cleanup incomplete')
    return code


if __name__ == '__main__':
    raise SystemExit(main())
