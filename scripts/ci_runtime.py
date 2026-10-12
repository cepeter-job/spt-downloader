"""Uji persiapan worker Windows managed dan pemakaian ulang tanpa akun nyata."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from spt_desktop.runtime import ensure_runtime, locked_requirements, python_version, resource_root
from spt_desktop.windows import ProcessJob


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', choices=('production', 'candidate'), required=True)
    args = parser.parse_args(argv)
    if sys.platform != 'win32':
        raise RuntimeError('The real worker setup smoke test requires Windows.')
    expected = locked_requirements(resource_root() / 'locks/runtime.txt')
    with tempfile.TemporaryDirectory(prefix='spt-ci-worker-', dir=os.environ['RUNNER_TEMP']) as temporary:
        root = Path(temporary)
        worker = ensure_runtime(root, print, lambda: False, python_profile=args.profile)
        ready = root / 'runtime-ready.txt'
        stamp = ready.stat().st_mtime_ns
        again = ensure_runtime(root, print, lambda: False, python_profile=args.profile)
        if again != worker or ready.stat().st_mtime_ns != stamp:
            raise RuntimeError('Worker setup did not reuse the verified environment.')
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
        environment = os.environ.copy()
        for name in ('PYTHONHOME', 'PYTHONPATH', 'DEBUG', 'PWDEBUG', 'UV_INSECURE_HOST'):
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
        report = json.loads(output)
        if (report.get('python') != python_version(args.profile)
                or report.get('implementation') != 'CPython' or report.get('bits') != 64
                or report.get('free_threaded') is not False or report.get('packages') != expected
                or not Path(report['base']).is_relative_to(root / 'python')
                or Path(report['worker_source']) != root / 'app' / 'spt_desktop' / 'worker.py'):
            raise RuntimeError('The prepared worker does not match the managed runtime contract.')
        print(f'Verified fresh managed worker and ready-state reuse: {args.profile}, Python {report["python"]}.')


if __name__ == '__main__':
    main()
