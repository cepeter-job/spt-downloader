"""Optional read-only CPU snapshots of worker descendants; never inspect browsers' data.

Windows Toolhelp gives only parent-child PIDs (not a trustworthy Node/Chromium
type label). No process names, paths, command lines, data or PIDs are logged.
This is diagnostic-only: it cannot authorize a capture result or infer an IPC
queue. A process that exits or spawns mid-call invalidates paired coverage.
"""
import os
import sys


MAX_OWNED_DESCENDANTS = 64


def _filetime_ticks(value):
    return (int(value.dwHighDateTime) << 32) | int(value.dwLowDateTime)


def supported():
    return sys.platform == 'win32'


def snapshot():
    """Return {pid: (creation_100ns, cpu_100ns, depth)} or None.

    Read only descendants of this *existing* worker PID. A failed query or
    process churn produces no fabricated complete CPU coverage.
    """
    if not supported():
        return None
    from ctypes import (Structure, WinDLL, POINTER, byref, c_size_t, c_void_p,
                        get_last_error, sizeof, wintypes)

    class ProcessEntry(Structure):
        _fields_ = [('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
                    ('th32ProcessID', wintypes.DWORD),
                    ('th32DefaultHeapID', c_size_t),
                    ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
                    ('th32ParentProcessID', wintypes.DWORD),
                    ('pcPriClassBase', wintypes.LONG), ('dwFlags', wintypes.DWORD),
                    ('szExeFile', wintypes.WCHAR * 260)]

    class FileTime(Structure):
        _fields_ = [('dwLowDateTime', wintypes.DWORD),
                    ('dwHighDateTime', wintypes.DWORD)]

    kernel = WinDLL('kernel32', use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    for name in ('Process32FirstW', 'Process32NextW'):
        func = getattr(kernel, name)
        func.argtypes = [wintypes.HANDLE, POINTER(ProcessEntry)]
        func.restype = wintypes.BOOL
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetProcessTimes.argtypes = [wintypes.HANDLE, POINTER(FileTime),
                                     POINTER(FileTime), POINTER(FileTime),
                                     POINTER(FileTime)]
    kernel.GetProcessTimes.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.CloseHandle.restype = wintypes.BOOL

    handle = kernel.CreateToolhelp32Snapshot(0x2, 0)  # TH32CS_SNAPPROCESS
    if not handle or handle == c_void_p(-1).value:
        return None
    parents = {}
    try:
        entry = ProcessEntry()
        entry.dwSize = sizeof(entry)
        ok = kernel.Process32FirstW(handle, byref(entry))
        if not ok:
            return None
        while ok:
            parents[int(entry.th32ProcessID)] = int(entry.th32ParentProcessID)
            entry.dwSize = sizeof(entry)
            ok = kernel.Process32NextW(handle, byref(entry))
        if get_last_error() not in (0, 18):  # ERROR_NO_MORE_FILES
            return None
    finally:
        kernel.CloseHandle(handle)

    root = os.getpid()
    descendants = {}
    frontier = {root}
    for depth in range(1, MAX_OWNED_DESCENDANTS + 1):
        children = {pid for pid, parent in parents.items()
                    if parent in frontier and pid != root and pid not in descendants}
        if not children:
            break
        for pid in children:
            descendants[pid] = depth
        if len(descendants) > MAX_OWNED_DESCENDANTS:
            return None
        frontier = children

    if not descendants:
        return None
    result = {}
    for pid, depth in descendants.items():
        child = kernel.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not child:
            return None
        try:
            created, exited, system, user = (FileTime(), FileTime(), FileTime(), FileTime())
            if not kernel.GetProcessTimes(child, byref(created), byref(exited),
                                          byref(system), byref(user)):
                return None
            result[pid] = (_filetime_ticks(created),
                           _filetime_ticks(system) + _filetime_ticks(user), depth)
        finally:
            kernel.CloseHandle(child)
    return result


def paired_cpu_delta(before, after):
    """CPU deltas in milliseconds for stable direct and nested descendants only."""
    if not before or not after:
        return None
    # Refuse to imply complete coverage for newly launched/exited or reused PIDs.
    if before.keys() != after.keys():
        return None
    direct = nested = 0
    for pid, (created, cpu, depth) in before.items():
        other_created, other_cpu, other_depth = after[pid]
        if created != other_created or depth != other_depth or other_cpu < cpu:
            return None
        if depth == 1:
            direct += other_cpu - cpu
        else:
            nested += other_cpu - cpu
    return direct / 10000, nested / 10000
