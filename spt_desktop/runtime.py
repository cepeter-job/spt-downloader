"""Prepare an isolated worker runtime; the frozen GUI never installs globally."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from .windows import ProcessJob

UV_VERSION = '0.12.16'
WORKER_FILES = (
    'coretax.py', 'coretax_browser.py', 'coretax_exporter.py', 'requirements.txt',
    'spt_desktop/__init__.py', 'spt_desktop/paths.py',
    'spt_desktop/credentials.py', 'spt_desktop/windows.py',
)


class SetupCancelled(RuntimeError):
    pass


def resource_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def worker_source(root: Path) -> Path:
    source = Path(root) / 'app'
    if not all((source / name).is_file() for name in WORKER_FILES):
        raise RuntimeError('Sumber worker belum lengkap. Jalankan persiapan ulang.')
    return source


def _cancel(cancelled):
    if cancelled():
        raise SetupCancelled('Persiapan dibatalkan; dapat dicoba lagi.')


def _run(argv, env, cancelled, timeout=900):
    _cancel(cancelled)
    # Package managers can emit large diagnostics; spool instead of retaining logs in RAM.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        with ProcessJob() as job:
            process = job.spawn([str(value) for value in argv], env=env,
                                stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
            deadline = time.monotonic() + timeout
            try:
                while process.poll() is None:
                    _cancel(cancelled)
                    if time.monotonic() >= deadline:
                        raise RuntimeError('Persiapan melewati batas waktu. Periksa koneksi lalu coba lagi.')
                    try:
                        process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        pass
            finally:
                job.close()
                process.wait(timeout=10)
        stdout.seek(0)
        stderr.seek(0)
        out = stdout.read(65536).decode('utf-8', errors='replace')
        err = stderr.read(65536).decode('utf-8', errors='replace')
        if process.returncode:
            # Index URLs and proxy diagnostics may contain secrets; never forward raw stderr.
            raise RuntimeError(f'Persiapan gagal (kode {process.returncode}). Periksa koneksi/proxy, lalu coba lagi.')
        return subprocess.CompletedProcess(argv, process.returncode, out, err)


def _python_candidates():
    values = []
    if not getattr(sys, 'frozen', False):
        values.append(Path(sys.executable))
    for name in ('python3.11', 'python', 'python3'):
        found = shutil.which(name)
        if found:
            path = Path(found)
            if 'windowsapps' not in str(path).casefold():
                values.append(path)
    return list(dict.fromkeys(values))


def _probe_python(python, expected, env, cancelled, packages=False):
    if not Path(python).is_file() or 'windowsapps' in str(python).casefold():
        return None
    script = (
        'import sys,struct,json,platform; '
        'info={"implementation":platform.python_implementation(),'
        '"version":list(sys.version_info[:3]),"bits":struct.calcsize("P")*8,'
        '"executable":sys.executable,"packages":{}}; '
    )
    if packages:
        script += 'import importlib.metadata\n'
        script += 'for name in ' + repr(tuple(expected)) + ':\n'
        script += ' try: info["packages"][name]=importlib.metadata.version(name); __import__(name)\n'
        script += ' except (importlib.metadata.PackageNotFoundError,ImportError,OSError): info["packages"][name]=None\n'
    script += '\nprint(json.dumps(info))'
    try:
        result = _run([str(python), '-c', script], env, cancelled, timeout=30)
        info = json.loads(result.stdout)
        if not isinstance(info, dict):
            return None
        return info
    except (RuntimeError, OSError, ValueError):
        _cancel(cancelled)
        return None


def _compatible(info):
    return bool(info and info.get('implementation') == 'CPython'
                and info.get('version', [])[:2] == [3, 11] and info.get('bits') == 64)


def _uv(root, source, env, cancelled):
    installed = shutil.which('uv')
    candidates = [Path(installed)] if installed else []
    bundled = source / 'tools' / 'uv.exe'
    if bundled.is_file():
        target = root / 'tools' / 'uv.exe'
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.read_bytes() != bundled.read_bytes():
            shutil.copy2(bundled, target)
        candidates.append(target)
    for candidate in candidates:
        try:
            result = _run([str(candidate), '--version'], env, cancelled, timeout=15)
            if re.match(r'uv\s+' + re.escape(UV_VERSION) + r'(?:\s|$)', result.stdout):
                return candidate
        except (OSError, RuntimeError):
            _cancel(cancelled)
    raise RuntimeError('uv yang sesuai tidak tersedia. Gunakan executable resmi beserta resource-nya.')


def _resources(source, root):
    digest = hashlib.sha256()
    app = root / 'app'
    for name in WORKER_FILES:
        original = source / name
        if not original.is_file():
            raise RuntimeError(f'Resource aplikasi tidak lengkap: {name}')
        data = original.read_bytes()
        digest.update(name.encode('utf-8') + b'\0' + data)
        destination = app / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        if not destination.is_file() or destination.read_bytes() != data:
            destination.write_bytes(data)
    expected = {}
    for line in (app / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_-]+)==([A-Za-z0-9.+_-]+)', line)
        if not match:
            raise RuntimeError('Requirements worker harus berisi versi paket yang dipin secara eksplisit.')
        expected[match[1]] = match[2]
    if not expected:
        raise RuntimeError('Requirements worker kosong.')
    return digest.hexdigest(), expected


def ensure_runtime(root: Path, on_status, cancelled) -> Path:
    _cancel(cancelled)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = resource_root()
    on_status('Memeriksa resource dan Python worker…')
    fingerprint, expected = _resources(source, root)
    environment = os.environ.copy()
    environment.update({'UV_PYTHON_INSTALL_DIR': str(root / 'python'),
                        'UV_CACHE_DIR': str(root / 'cache'), 'PYTHONUTF8': '1',
                        'PYTHONIOENCODING': 'utf-8'})
    environment.pop('UV_INSECURE_HOST', None)
    python = root / 'runtime' / 'Scripts' / 'python.exe'
    ready = root / 'runtime-ready.txt'
    info = _probe_python(python, expected, environment, cancelled, packages=True)
    if (_compatible(info) and info.get('packages') == expected and ready.is_file()
            and ready.read_text(encoding='ascii').strip() == fingerprint):
        on_status('Python dan dependensi siap.')
        return python
    ready.unlink(missing_ok=True)
    uv = _uv(root, source, environment, cancelled)
    if not _compatible(info):
        base = None
        for candidate in _python_candidates():
            if _compatible(_probe_python(candidate, expected, environment, cancelled)):
                base = candidate
                break
        if base is None:
            on_status('Memasang Python portable 3.11 x64 di workspace…')
            _run([uv, 'python', 'install', '3.11', '--install-dir', str(root / 'python'),
                  '--no-bin', '--no-registry'], environment, cancelled)
            result = _run([uv, 'python', 'find', '3.11', '--managed-python', '--no-python-downloads'],
                          environment, cancelled, timeout=30)
            base = Path(result.stdout.strip())
            if not base.is_absolute() or not base.resolve().is_relative_to((root / 'python').resolve()):
                raise RuntimeError('Python portable berada di luar workspace; persiapan dihentikan.')
            if not _compatible(_probe_python(base, expected, environment, cancelled)):
                raise RuntimeError('Python portable tidak memenuhi CPython 3.11 x64.')
        on_status('Menyiapkan environment worker terisolasi…')
        _run([uv, 'venv', str(root / 'runtime'), '--python', str(base), '--clear'],
             environment, cancelled, timeout=60)
    on_status('Memasang dependensi menggunakan uv…')
    _run([uv, 'pip', 'install', '--python', str(python), '-r', str(root / 'app' / 'requirements.txt')],
         environment, cancelled)
    _cancel(cancelled)
    info = _probe_python(python, expected, environment, cancelled, packages=True)
    if not _compatible(info) or info.get('packages') != expected:
        raise RuntimeError('Verifikasi Python/dependensi gagal; persiapan belum selesai.')
    temporary = root / 'runtime-ready.tmp'
    temporary.write_text(fingerprint, encoding='ascii')
    temporary.replace(ready)
    on_status('Python dan dependensi siap.')
    return python
