"""Siapkan worker terisolasi dengan Python dan dependency yang dikunci."""
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
from . import diagnostics

UV_VERSION = '0.13.4'
PYTHON_PROFILES = {'production': '3.14.8'}
RUNTIME_LOCK = 'locks/runtime.txt'
WORKER_FILES = (
    'coretax.py', 'coretax_browser.py', 'coretax_exporter.py', 'coretax_json.py', 'coretax_inventory.py',
    'coretax_json_capture.py', 'coretax_corporate.py', 'coretax_pph21.py', 'resources/pph21_format.xlsx',
    'coretax_pph21_json_bindings.py', 'coretax_pph21_observer.py', 'coretax_pph21_projection.py',
    'coretax_template_cells.py', 'coretax_masa_templates.py',
    'coretax_badan_template.py', 'resources/corporate_format.xlsx',
    'coretax_masa_json.py', 'coretax_masa_bindings.py',
    'coretax_masa_observer.py', 'coretax_masa_projection.py', 'coretax_unifikasi_json.py',
    'resources/ppn_format.xlsx', 'resources/unifikasi_format.xlsx',
    'coretax_attachments.py', 'coretax_pdf.py', 'requirements.txt',
    RUNTIME_LOCK,
    'spt_desktop/__init__.py', 'spt_desktop/paths.py',
    'spt_desktop/credentials.py', 'spt_desktop/windows.py',
    'spt_desktop/events.py', 'spt_desktop/auth.py', 'spt_desktop/output.py',
    'spt_desktop/worker.py', 'spt_desktop/interaction.py', 'spt_desktop/output_windows.py',
    'spt_desktop/diagnostics.py', 'spt_desktop/diagnostic_store.py',
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


@diagnostics.traced('runtime')
def _run(argv, env, cancelled, timeout=900):
    _cancel(cancelled)
    # Simpan diagnostik besar di berkas sementara agar RAM tetap terbatas.
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
        diagnostics.record('runtime.command', exit_code=process.returncode)
        if process.returncode:
            # URL indeks dan diagnostik proxy bisa berisi rahasia; jangan teruskan stderr mentah.
            raise RuntimeError(f'Persiapan gagal (kode {process.returncode}). Periksa koneksi/proxy, lalu coba lagi.')
        return subprocess.CompletedProcess(argv, process.returncode, out, err)


def _probe_python(python, expected, env, cancelled, packages=False):
    if not Path(python).is_file() or 'windowsapps' in str(python).casefold():
        return None
    script = (
        'import sys,struct,json,platform,sysconfig; from pathlib import Path; '
        'info={"implementation":platform.python_implementation(),'
        '"version":list(sys.version_info[:3]),"bits":struct.calcsize("P")*8,'
        '"free_threaded":bool(sysconfig.get_config_var("Py_GIL_DISABLED")),'
        '"base_executable":str(Path(getattr(sys,"_base_executable",sys.executable)).resolve()),'
        '"executable":sys.executable,"packages":{}}; '
    )
    if packages:
        script += 'import importlib.metadata\n'
        script += 'for name in ' + repr(tuple(expected)) + ':\n'
        script += ' try: info["packages"][name]=importlib.metadata.version(name); __import__(name.replace("-","_"))\n'
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


def python_version(profile='production'):
    try:
        return PYTHON_PROFILES[profile]
    except KeyError:
        raise ValueError('Nama profil Python tidak dikenal.') from None


def _compatible(info, profile='production'):
    version = [int(part) for part in python_version(profile).split('.')]
    return bool(info and info.get('implementation') == 'CPython'
                and info.get('version') == version and info.get('bits') == 64
                and info.get('free_threaded') is False)


def _managed(info, root):
    if not info or not isinstance(info.get('base_executable'), str):
        return False
    base = Path(info['base_executable'])
    return base.is_absolute() and base.resolve().is_relative_to((root / 'python').resolve())


def locked_requirements(path):
    """Baca pin universal worker; tolak lock tanpa hash atau sintaks instalasi tambahan."""
    contents = Path(path).read_text(encoding='utf-8')
    lines = '\n'.join(line.split('#', 1)[0] for line in contents.splitlines())
    lines = lines.replace('\\\n', ' ')
    expected = {}
    for line in lines.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.fullmatch(r'([A-Za-z0-9_.-]+)==([A-Za-z0-9.+_-]+)'
                             r'(?:\s+--hash=sha256:[0-9a-f]{64})+', line)
        if not match:
            raise RuntimeError('Format lock worker tidak valid; setiap pin harus memiliki hash SHA-256.')
        name = re.sub(r'[-_.]+', '-', match[1]).lower()
        if name in expected:
            raise RuntimeError('Paket duplikat dalam lock worker.')
        expected[name] = match[2]
    if not expected:
        raise RuntimeError('Lock worker kosong.')
    return expected


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
    expected = locked_requirements(app / RUNTIME_LOCK)
    direct = {}
    for line in (app / 'requirements.txt').read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        match = re.fullmatch(r'([A-Za-z0-9_-]+)==([A-Za-z0-9.+_-]+)', line)
        if not match:
            raise RuntimeError('Requirements worker harus berisi versi paket yang dipin secara eksplisit.')
        direct[match[1]] = match[2]
    if not direct:
        raise RuntimeError('Requirements worker kosong.')
    if any(expected.get(name) != version for name, version in direct.items()):
        raise RuntimeError('Lock worker tidak sesuai requirements. Perbarui lock sebelum build.')
    return digest.hexdigest(), expected


@diagnostics.traced('runtime')
def ensure_runtime(root: Path, on_status, cancelled, *, python_profile='production') -> Path:
    _cancel(cancelled)
    version = python_version(python_profile)
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    source = resource_root()
    on_status('Memeriksa resource dan Python worker…')
    fingerprint, expected = _resources(source, root)
    fingerprint = hashlib.sha256(f'{fingerprint}\0{version}\0{UV_VERSION}'.encode('ascii')).hexdigest()
    environment = os.environ.copy()
    environment.update({'UV_PYTHON_INSTALL_DIR': str(root / 'python'),
                        'UV_CACHE_DIR': str(root / 'cache'), 'PYTHONUTF8': '1',
                        'PYTHONIOENCODING': 'utf-8'})
    environment.pop('UV_INSECURE_HOST', None)
    # Worker memilih interpreter sendiri; preferensi shell bertabrakan dengan --managed-python.
    environment.pop('UV_PYTHON_PREFERENCE', None)
    environment.pop('PYTHONHOME', None)
    environment.pop('PYTHONPATH', None)
    python = root / 'runtime' / 'Scripts' / 'python.exe'
    ready = root / 'runtime-ready.txt'
    info = _probe_python(python, expected, environment, cancelled, packages=True)
    if (_compatible(info, python_profile) and _managed(info, root)
            and info.get('packages') == expected and ready.is_file()
            and ready.read_text(encoding='ascii').strip() == fingerprint):
        diagnostics.record('runtime.reused')
        on_status('Python dan dependensi siap.')
        return python
    diagnostics.record('runtime.install')
    ready.unlink(missing_ok=True)
    uv = _uv(root, source, environment, cancelled)
    if not _compatible(info, python_profile) or not _managed(info, root):
        # Gunakan versi patch terkelola yang tepat, termasuk saat mengganti worker 3.11 lama.
        request = version + '+gil'
        # +gil berlaku untuk pencarian instalasi; katalog unduhan uv memakai kunci varian default.
        download = f'cpython-{version}-windows-x86_64-none'
        on_status(f'Memasang Python portable {version} x64 di workspace…')
        _run([uv, 'python', 'install', download, '--install-dir', str(root / 'python'),
              '--no-bin', '--no-registry'], environment, cancelled)
        # Abaikan virtualenv shell pengembang; hanya interpreter managed dasar yang dicari.
        result = _run([uv, 'python', 'find', request, '--managed-python', '--system', '--no-python-downloads'],
                      environment, cancelled, timeout=30)
        base = Path(result.stdout.strip())
        if not base.is_absolute() or not base.resolve().is_relative_to((root / 'python').resolve()):
            raise RuntimeError('Python portable berada di luar workspace; persiapan dihentikan.')
        if not _compatible(_probe_python(base, expected, environment, cancelled), python_profile):
            raise RuntimeError(f'Python portable tidak memenuhi CPython {version} x64 dengan GIL.')
        on_status('Menyiapkan environment worker terisolasi…')
        _run([uv, 'venv', str(root / 'runtime'), '--python', str(base), '--clear'],
             environment, cancelled, timeout=60)
    on_status('Memasang dependensi menggunakan uv…')
    _run([uv, 'pip', 'sync', '--python', str(python), '--require-hashes', '--only-binary', ':all:',
          str(root / 'app' / RUNTIME_LOCK)],
         environment, cancelled)
    _cancel(cancelled)
    info = _probe_python(python, expected, environment, cancelled, packages=True)
    if (not _compatible(info, python_profile) or not _managed(info, root)
            or info.get('packages') != expected):
        raise RuntimeError('Verifikasi Python/dependensi gagal; persiapan belum selesai.')
    temporary = root / 'runtime-ready.tmp'
    temporary.write_text(fingerprint, encoding='ascii')
    temporary.replace(ready)
    on_status('Python dan dependensi siap.')
    return python
