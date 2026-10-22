"""Probe the actual candidate process; execute only on a GitHub Windows runner."""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import platform
import struct
import sys
import sysconfig
import tkinter
import _tkinter
import _ctypes
import _ssl
import zlib


def probe():
    root = Path(sys.base_prefix).resolve()
    if sysconfig.is_python_build() or 'sitecustomize' in sys.modules or 'usercustomize' in sys.modules:
        raise RuntimeError('candidate depends on build or customization context')
    window = tkinter.Tk()
    window.withdraw()
    try:
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
        modules = (wintypes.HMODULE * 2048)()
        needed = wintypes.DWORD()
        if not psapi.EnumProcessModules(kernel.GetCurrentProcess(), modules, ctypes.sizeof(modules), ctypes.byref(needed)) or needed.value > ctypes.sizeof(modules):
            raise RuntimeError("cannot inventory loaded process modules")
        paths = []
        for module in modules[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
            buffer = ctypes.create_unicode_buffer(32768)
            if not kernel.GetModuleFileNameW(module, buffer, len(buffer)):
                raise RuntimeError("cannot identify loaded library")
            paths.append(Path(buffer.value).resolve())
        expected = {"python": "python314.dll", "_tkinter": Path(_tkinter.__file__).name, "tcl": "tcl91.dll", "tk": "tcl9tk91.dll"}
        loaded = {}
        hashes = {}
        absolute = {}
        for role, basename in expected.items():
            matches = [path for path in paths if path.name.casefold() == basename.casefold()]
            if len(matches) != 1:
                raise RuntimeError(f"unexpected loaded {role} count")
            path = matches[0]
            loaded[role] = path.relative_to(root).as_posix()
            absolute[role] = str(path)
            hashes[role] = hashlib.sha256(path.read_bytes()).hexdigest()
        native_modules = {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths if path.is_relative_to(root)}
        for basename in ('libffi-8.dll', 'libcrypto-3.dll', 'libssl-3.dll', 'zlib1.dll', 'libtommath.dll'):
            matches = [path for path in paths if path.name.casefold() == basename.casefold()]
            if len(matches) != 1 or not matches[0].is_relative_to(root):
                raise RuntimeError(f'candidate dependency is not local: {basename}')
        libraries = {"tcl": Path(str(window.tk.call("info", "library"))).resolve(), "tk": Path(str(window.tk.getvar("tk_library"))).resolve()}
        return {"schema": 1, "python": platform.python_version(), "architecture": "x64" if struct.calcsize("P") == 8 and platform.machine().lower() in ("amd64", "x86_64") else platform.machine(), "gil": not bool(sysconfig.get_config_var("Py_GIL_DISABLED")), "tcl": str(window.tk.call("info", "patchlevel")), "tk": str(window.tk.call("package", "present", "Tk")), "loaded": loaded, "loaded_absolute": absolute, "loaded_sha256": hashes, "libraries": {key: value.relative_to(root).as_posix() for key, value in libraries.items()}, "library_absolute": {key: str(value) for key, value in libraries.items()}, "executable": str(Path(sys.executable).resolve()), "gil_enabled": sys._is_gil_enabled(), "native_modules": native_modules, "sys_path": sys.path, "prefix": sys.prefix, "base_prefix": sys.base_prefix, "is_python_build": sysconfig.is_python_build(), "tkinter_path": tkinter.__file__}
    finally:
        window.destroy()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.write_text(json.dumps(probe(), indent=2) + "\n", encoding="utf-8")


def application_probe(window):
    """Observe this source/frozen process without trusting attached inventory values."""
    frozen = bool(getattr(sys, 'frozen', False))
    root = Path(sys._MEIPASS if frozen else sys.base_prefix).resolve()
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    psapi = ctypes.WinDLL('psapi', use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.HMODULE), wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    modules = (wintypes.HMODULE * 2048)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcessModules(kernel.GetCurrentProcess(), modules, ctypes.sizeof(modules), ctypes.byref(needed)) or needed.value > ctypes.sizeof(modules):
        raise RuntimeError('cannot inventory candidate application modules')
    paths = []
    for module in modules[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        buffer = ctypes.create_unicode_buffer(32768)
        if not kernel.GetModuleFileNameW(module, buffer, len(buffer)):
            raise RuntimeError('cannot identify application module')
        paths.append(Path(buffer.value).resolve())
    loaded, hashes, absolute, resources = {}, {}, {}, {}
    names = {'python': 'python314.dll', '_tkinter': 'DLLs/_tkinter.pyd',
             'tcl': 'DLLs/tcl91.dll', 'tk': 'DLLs/tcl9tk91.dll'}
    for role, canonical in names.items():
        matches = [path for path in paths if path.name.casefold() == Path(canonical).name.casefold()]
        if len(matches) != 1 or not matches[0].is_relative_to(root):
            raise RuntimeError('candidate application native resource is external or ambiguous')
        path = matches[0]
        loaded[role], absolute[role] = canonical, str(path)
        hashes[role] = resources[canonical] = hashlib.sha256(path.read_bytes()).hexdigest()
    libraries = {'tcl': Path(str(window.tk.call('info', 'library'))).resolve(),
                 'tk': Path(str(window.tk.getvar('tk_library'))).resolve()}
    for kind, library in libraries.items():
        if not library.is_relative_to(root):
            raise RuntimeError('candidate application script library is external')
        canonical = 'tcl/' + ('tcl9.1' if kind == 'tcl' else 'tk9.1')
        for path in library.rglob('*'):
            if path.is_symlink() or path.is_junction():
                raise RuntimeError('linked candidate application resource')
            if path.is_file():
                resources[canonical + '/' + path.relative_to(library).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {'schema': 1, 'python': platform.python_version(), 'architecture': 'x64' if struct.calcsize('P') == 8 else platform.machine(),
            'gil': not bool(sysconfig.get_config_var('Py_GIL_DISABLED')), 'tcl': str(window.tk.call('info', 'patchlevel')),
            'tk': str(window.tk.call('package', 'present', 'Tk')), 'loaded': loaded,
            'loaded_sha256': hashes, 'loaded_absolute': absolute, 'resources': resources,
            'library_absolute': {key: str(value) for key, value in libraries.items()},
            'resource_root': str(root), 'executable': str(Path(sys.executable).resolve())}
