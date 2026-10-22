"""Exercise real Windows worker setup without accounts, including the read-back EXE."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import tempfile

from spt_desktop import runtime
from spt_desktop.build_info import read_build_info
from spt_desktop.windows import ProcessJob


def _runner_temp():
    value = os.environ.get('RUNNER_TEMP', '')
    path = Path(value)
    if sys.platform != 'win32' or not value or not path.is_absolute() or not path.is_dir():
        raise RuntimeError('The real bootstrap smoke requires a Windows runner temporary directory.')
    return path.resolve()


def _sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _worker_report(worker, root, profile):
    expected = runtime.locked_requirements(runtime.resource_root() / runtime.RUNTIME_LOCK)
    probe = (
        'import json,platform,struct,sys,sysconfig,importlib.metadata;'
        'from pathlib import Path;'
        'import playwright.sync_api,openpyxl,greenlet,pyee,et_xmlfile,typing_extensions,spt_desktop.worker;'
        'print(json.dumps({'
        '"python":platform.python_version(),"bits":struct.calcsize("P")*8,'
        '"implementation":platform.python_implementation(),'
        '"free_threaded":bool(sysconfig.get_config_var("Py_GIL_DISABLED")),'
        '"base":str(Path(sys._base_executable).resolve()),'
        '"worker_source":str(Path(spt_desktop.worker.__file__).resolve()),'
        '"packages":{name:importlib.metadata.version(name) for name in ' + repr(tuple(expected)) + '}}))'
    )
    environment = runtime.bootstrap_environment(root)
    for name in ('DEBUG', 'PWDEBUG'):
        environment.pop(name, None)
    with ProcessJob() as owned:
        process = owned.spawn([str(worker), '-c', probe], stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              cwd=str(root / 'app'), env=environment)
        try:
            output, _ = process.communicate(timeout=30)
            if process.returncode:
                raise RuntimeError('The prepared worker could not import its locked dependencies.')
        finally:
            owned.close()
            process.wait(timeout=10)
    data = json.loads(output)
    if (type(data) is not dict or data.get('python') != runtime.python_version(profile)
            or data.get('implementation') != 'CPython' or data.get('bits') != 64
            or data.get('free_threaded') is not False or data.get('packages') != expected
            or not isinstance(data.get('base'), str)
            or not Path(data['base']).is_absolute()
            or not Path(data['base']).resolve().is_relative_to(root / 'python')
            or not isinstance(data.get('worker_source'), str)
            or Path(data['worker_source']).resolve() != root / 'app' / 'spt_desktop' / 'worker.py'):
        raise RuntimeError('The prepared worker does not match the managed runtime contract.')
    for name in runtime.WORKER_FILES:
        if (root / 'app' / name).read_bytes() != (runtime.resource_root() / name).read_bytes():
            raise RuntimeError('The prepared worker does not match its explicit packaged resources.')
    if read_build_info(root / 'app') != read_build_info():
        raise RuntimeError('The prepared worker did not retain its validated build identity.')
    return data


def _fresh_and_reused(root, profile, on_status):
    if root.exists() and any(root.iterdir()):
        raise RuntimeError('The bootstrap smoke requires a fresh, empty owned workspace.')
    worker = runtime.ensure_runtime(root, on_status, lambda: False, python_profile=profile)
    ready = root / 'runtime-ready.txt'
    before = (ready.stat().st_mtime_ns, ready.read_bytes())
    again = runtime.ensure_runtime(root, on_status, lambda: False, python_profile=profile)
    if again != worker or (ready.stat().st_mtime_ns, ready.read_bytes()) != before:
        raise RuntimeError('Worker setup did not reuse the verified environment.')
    return worker, _worker_report(worker, root, profile)


def check_owned_cancellation(python, root):
    """Cancel runtime._run only after its real interpreter and child are both alive."""
    if sys.platform != 'win32':
        raise RuntimeError('Owned bootstrap cancellation requires Windows Job Objects.')
    import ctypes

    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
    kernel.OpenProcess.restype = ctypes.c_void_p
    kernel.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
    kernel.WaitForSingleObject.restype = ctypes.c_ulong
    kernel.TerminateProcess.argtypes = [ctypes.c_void_p, ctypes.c_uint]
    kernel.TerminateProcess.restype = ctypes.c_int
    kernel.CloseHandle.argtypes = [ctypes.c_void_p]
    kernel.CloseHandle.restype = ctypes.c_int
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    handles = []
    with tempfile.TemporaryDirectory(prefix='cancel-', dir=root) as temporary:
        marker = Path(temporary) / 'ready.json'
        child = (
            'import json,os,sys,time;from pathlib import Path;'
            'marker=Path(sys.argv[1]);pending=marker.with_suffix(".tmp");'
            'pending.write_text(json.dumps({"parent":int(sys.argv[2]),"child":os.getpid()}),encoding="utf-8");'
            'pending.replace(marker);time.sleep(120)'
        )
        parent = (
            'import os,subprocess,sys,time;'
            'subprocess.Popen([sys._base_executable,"-I","-c",' + repr(child) + ',sys.argv[1],str(os.getpid())]);'
            'time.sleep(120)'
        )

        def ready_to_cancel():
            if not marker.is_file():
                return False
            pids = json.loads(marker.read_text(encoding='utf-8'))
            if (type(pids) is not dict or set(pids) != {'parent', 'child'}
                    or any(type(pid) is not int or pid <= 0 or pid == os.getpid() for pid in pids.values())
                    or pids['parent'] == pids['child']):
                raise RuntimeError('The synthetic cancellation readiness record is invalid.')
            for name in ('parent', 'child'):
                handle = kernel.OpenProcess(0x100001, False, pids[name])
                if not handle:
                    raise RuntimeError('The synthetic owned process could not be inspected.')
                handles.append(handle)
                if kernel.WaitForSingleObject(handle, 0) != 258:
                    raise RuntimeError('The synthetic owned process exited before cancellation.')
            return True

        try:
            try:
                runtime._run([str(python), '-I', '-c', parent, str(marker)],
                             runtime.bootstrap_environment(root), ready_to_cancel, timeout=30)
            except runtime.SetupCancelled:
                pass
            else:
                raise RuntimeError('The bootstrap process did not observe cancellation.')
            if len(handles) != 2 or any(kernel.WaitForSingleObject(handle, 5000) != 0 for handle in handles):
                raise RuntimeError('Bootstrap cancellation did not finish its owned process cleanup.')
            return {'cancelled': True, 'owned_cleanup': True}
        finally:
            for handle in handles:
                if kernel.WaitForSingleObject(handle, 0) == 258:
                    kernel.TerminateProcess(handle, 1)
                    kernel.WaitForSingleObject(handle, 5000)
                kernel.CloseHandle(handle)


def validate_packaged_report(data, executable, profile):
    expected = runtime.locked_requirements(runtime.resource_root() / runtime.RUNTIME_LOCK)
    executable = Path(executable)
    checks = data.get('checks') if type(data) is dict else None
    if (type(data) is not dict or type(data.get('schema')) is not int or data.get('schema') != 1
            or data.get('kind') != 'packaged-bootstrap' or data.get('ok') is not True
            or data.get('frozen') is not True or data.get('path_uv_absent') is not True
            or data.get('python') != runtime.python_version(profile)
            or data.get('worker_python') != runtime.python_version(profile)
            or data.get('implementation') != 'CPython' or type(data.get('bits')) is not int
            or data.get('bits') != 64 or data.get('free_threaded') is not False
            or data.get('uv_version') != runtime.UV_VERSION or data.get('uv_source') != 'bundled'
            or data.get('worker_resources') != list(runtime.WORKER_FILES)
            or data.get('packages') != expected or data.get('credentials_accessed') is not False
            or data.get('live_scrape') is not False or type(checks) is not dict
            or any(checks.get(name) is not True for name in ('cold_install', 'reuse', 'cancelled', 'owned_cleanup'))
            or executable.is_symlink() or not executable.is_file()
            or data.get('executable_sha256') != _sha256(executable)):
        raise ValueError('The packaged bootstrap evidence is incomplete or does not match the executable/runtime.')


def packaged_self_test(report):
    """Explicit frozen-only entry point. Never opens the GUI, accounts or a browser."""
    destination = None
    phase = 'preflight'
    try:
        runner = _runner_temp()
        destination = Path(report).resolve()
        if not destination.is_relative_to(runner):
            destination = None
            raise RuntimeError('The packaged bootstrap report must stay in the runner temporary directory.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.unlink(missing_ok=True)
        identity = read_build_info()
        if not getattr(sys, 'frozen', False) or identity is None or shutil.which('uv') is not None:
            raise RuntimeError('Packaged bootstrap requires a frozen build with no PATH uv.')
        with tempfile.TemporaryDirectory(prefix='spt-frozen-worker-', dir=runner) as temporary:
            root = Path(temporary).resolve()
            phase = 'bootstrap'
            worker, info = _fresh_and_reused(root, 'production', lambda _: None)
            copied_uv = root / 'tools' / 'uv.exe'
            if _sha256(copied_uv) != _sha256(runtime.resource_root() / 'tools' / 'uv.exe'):
                raise RuntimeError('The bootstrap tool differs from the packaged uv bytes.')
            result = runtime._run([copied_uv, '--version'], runtime.bootstrap_environment(root), lambda: False, timeout=15)
            if not re.match(r'uv\s+' + re.escape(runtime.UV_VERSION) + r'(?:\s|$)', result.stdout):
                raise RuntimeError('The packaged bootstrap tool version differs from its pin.')
            phase = 'cancellation'
            cancelled_root = root / 'cancel-before-setup'
            try:
                runtime.ensure_runtime(cancelled_root, lambda _: None, lambda: True)
            except runtime.SetupCancelled:
                pass
            else:
                raise RuntimeError('A cancelled bootstrap unexpectedly continued.')
            if cancelled_root.exists():
                raise RuntimeError('A cancelled bootstrap created worker state.')
            checks = {'cold_install': True, 'reuse': True, **check_owned_cancellation(worker, root)}
            data = {
                'schema': 1, 'kind': 'packaged-bootstrap', 'ok': True, 'frozen': True,
                'executable_sha256': _sha256(sys.executable), 'build_info': identity,
                'python': platform.python_version(), 'worker_python': info['python'],
                'implementation': platform.python_implementation(), 'bits': struct.calcsize('P') * 8,
                'free_threaded': bool(sysconfig.get_config_var('Py_GIL_DISABLED')),
                'uv_version': runtime.UV_VERSION, 'uv_source': 'bundled', 'path_uv_absent': True,
                'worker_resources': list(runtime.WORKER_FILES), 'packages': info['packages'],
                'checks': checks, 'credentials_accessed': False, 'live_scrape': False,
            }
            phase = 'report'
            validate_packaged_report(data, Path(sys.executable), 'production')
        destination.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        return 0
    except Exception as error:
        # A windowed EXE must exit on smoke failure, not leave an exception dialog open.
        # No exception text, environment values, process output or private paths enter evidence.
        if destination is not None:
            category = type(error).__name__
            if category not in {'RuntimeError', 'OSError', 'ValueError', 'FileNotFoundError',
                                'PermissionError', 'TimeoutExpired', 'SetupCancelled'}:
                category = 'Error'
            try:
                destination.write_text(json.dumps({'schema': 1, 'kind': 'packaged-bootstrap',
                    'ok': False, 'phase': phase, 'error_type': category}), encoding='utf-8')
            except OSError:
                pass
        return 1


def _packaged_from_runner(executable, artifact_id, report, profile):
    runner = _runner_temp()
    executable = Path(executable).resolve()
    identity = read_build_info(executable.parent)
    if (identity is None or not re.fullmatch(r'[1-9][0-9]*', artifact_id)
            or identity['commit'] != os.environ.get('GITHUB_SHA')
            or identity['run_id'] != os.environ.get('GITHUB_RUN_ID')
            or str(identity['run_attempt']) != os.environ.get('GITHUB_RUN_ATTEMPT')):
        raise RuntimeError('Packaged bootstrap must match the current immutable build and artifact coordinates.')
    destination = Path(report).resolve()
    if not destination.is_relative_to(runner):
        raise RuntimeError('Packaged bootstrap evidence must stay in the runner temporary directory.')
    destination.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix='spt-ci-frozen-', dir=runner) as temporary:
        cwd = Path(temporary)
        raw = cwd / 'packaged-bootstrap.json'
        config = cwd / 'uv.toml'
        config.write_text('[invalid synthetic configuration\n', encoding='utf-8')
        catalog = cwd / 'python-downloads.json'
        catalog.write_text('{}', encoding='utf-8')
        environment = os.environ.copy()
        for name in ('PYTHONHOME', 'PYTHONPATH', 'VIRTUAL_ENV', 'DEBUG', 'PWDEBUG'):
            environment.pop(name, None)
        environment['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')
        # Deliberately leave foreign policy for the product bootstrap to reject.
        environment.update({'UV_NO_CONFIG': '0', 'UV_CONFIG_FILE': str(config),
                            'UV_PYTHON_DOWNLOADS_JSON_URL': str(catalog),
                            'UV_INDEX_URL': 'https://127.0.0.1:1/unused-synthetic-index'})
        with ProcessJob() as owned:
            process = owned.spawn([str(executable), '--runtime-self-test', '--report', str(raw)],
                                  env=environment, cwd=str(cwd), stdin=subprocess.DEVNULL,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                code = process.wait(timeout=600)
            finally:
                owned.close()
                process.wait(timeout=10)
        if not raw.is_file() or raw.stat().st_size > 65536:
            raise RuntimeError('The packaged bootstrap did not produce bounded execution evidence.')
        data = json.loads(raw.read_text(encoding='utf-8'))
        if code:
            phase = data.get('phase') if type(data) is dict else None
            if phase not in {'preflight', 'bootstrap', 'cancellation', 'report'}:
                phase = 'unknown'
            raise RuntimeError('The packaged bootstrap failed during ' + phase + '.')
        validate_packaged_report(data, executable, profile)
        if data.get('build_info') != identity:
            raise RuntimeError('The embedded build identity differs from the verified distribution sidecar.')
        data.update({'artifact_id': artifact_id, 'commit': identity['commit'],
                     'run_id': identity['run_id'], 'run_attempt': identity['run_attempt'],
                     'external_uv_policy_ignored': True})
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    print('Verified packaged cold bootstrap, reuse and owned cancellation for artifact ' + artifact_id + '.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=tuple(runtime.PYTHON_PROFILES), required=True)
    parser.add_argument('--executable', type=Path)
    parser.add_argument('--artifact-id')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args(argv)
    if args.executable is not None:
        if args.artifact_id is None or args.report is None:
            parser.error('--executable requires --artifact-id and --report')
        _packaged_from_runner(args.executable, args.artifact_id, args.report, args.profile)
    else:
        if args.artifact_id is not None or args.report is not None:
            parser.error('--artifact-id and --report require --executable')
        with tempfile.TemporaryDirectory(prefix='spt-ci-worker-', dir=_runner_temp()) as temporary:
            _, info = _fresh_and_reused(Path(temporary).resolve(), args.profile, print)
            print(f'Verified fresh managed worker and ready-state reuse: {args.profile}, Python {info["python"]}.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
