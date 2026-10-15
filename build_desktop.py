"""Build GUI Windows dengan resource terbatas dan verifikasi runtime executable."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
from spt_desktop.runtime import WORKER_FILES, UV_VERSION, PYTHON_PROFILES, python_version
from spt_desktop.windows import ProcessJob

ROOT=Path(__file__).resolve().parent


def build_command(root,output,uv_binary):
    root,output=Path(root),Path(output)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile',
             '--windowed','--noupx','--name','SPTDownloader',
             '--distpath',str(output),'--workpath',str(output/'_build'),
             '--specpath',str(output/'_spec')]
    for name in WORKER_FILES+('LICENSE',):
        parent=str(Path(name).parent)
        command.extend(['--add-data',str(root/name)+';'+parent])
    command.extend(['--add-binary',str(uv_binary)+';tools'])
    for name in ('playwright','openpyxl','pytest','uv'):
        command.extend(['--exclude-module',name])
    command.append(str(root/'spt_gui.py'))
    return command


def validate_report(data, python_profile='production'):
    expected = python_version(python_profile)
    diagnostic = data.get('diagnostics')
    if not (type(diagnostic) is dict and type(diagnostic.get('schema')) is int
            and diagnostic.get('schema') == 1 and diagnostic.get('safe_logging') is True
            and data.get('ok') is True and data.get('frozen') is True and data.get('uv_bundled') is True
            and data.get('bits') == 64 and data.get('python') == expected
            and data.get('python_implementation') == 'CPython' and data.get('free_threaded') is False
            and all(re.fullmatch(r'\d+\.\d+\.\d+', str(data.get(name, ''))) for name in ('tcl', 'tk'))
            and data.get('worker_python') == python_version()
            and data.get('worker_resources') == list(WORKER_FILES)
            and data.get('credential_check_controls') and 'Cek Kredensial' in data.get('gui_controls', [])
            and data.get('personal_use_labels') == ['Coretax → Excel · for personal use only']
            and data.get('ui_text') == {
                'title':'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
                'background':'jalankan proses sedot di background',
                'results':'Hasil Sedot berada di folder Downloads Windows'}
            and data.get('credentials_accessed') is False and data.get('live_scrape') is False):
        raise RuntimeError('Packaged application self-test failed')


def build(output, python_profile='production'):
    expected = python_version(python_profile)
    if (sys.platform != 'win32' or struct.calcsize('P') != 8
            or platform.python_implementation() != 'CPython'
            or tuple(sys.version_info[:3]) != tuple(int(v) for v in expected.split('.'))
            or sysconfig.get_config_var('Py_GIL_DISABLED')):
        raise RuntimeError(f'Build requires Windows CPython {expected} x64 with GIL.')
    if importlib.metadata.version('uv')!=UV_VERSION:
        raise RuntimeError('Build uv version differs from the application pin.')
    import uv
    uv_binary=Path(uv.find_uv_bin())
    version=subprocess.run([str(uv_binary),'--version'],capture_output=True,text=True,check=True,timeout=15)
    if not version.stdout.startswith('uv '+UV_VERSION+' '):raise RuntimeError('Bundled uv binary version mismatch')
    for name in WORKER_FILES+('LICENSE',):
        if not (ROOT/name).is_file():raise FileNotFoundError('Missing allowed build resource: '+name)
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    subprocess.run(build_command(ROOT,output,uv_binary),cwd=ROOT,check=True)
    executable=output/'SPTDownloader.exe'
    if not executable.is_file():raise FileNotFoundError('PyInstaller did not create the executable')
    report=output/'build-selftest.json'
    report.unlink(missing_ok=True)
    with ProcessJob() as owned:
        process=owned.spawn([str(executable),'--self-test','--report',str(report)])
        try:
            code=process.wait(timeout=60)
            if code:raise subprocess.CalledProcessError(code,process.args)
        finally:
            owned.close()
            process.wait(timeout=10)
    data=json.loads(report.read_text(encoding='utf-8'))
    validate_report(data, python_profile)
    data['build_profile'] = python_profile
    report.write_text(json.dumps(data, indent=2), encoding='utf-8')
    shutil.copy2(ROOT/'LICENSE',output/'LICENSE.txt')
    (output/'README.txt').write_text(
        'SPT Downloader — Windows 10/11 x64\n'
        'Sumber/lisensi: https://github.com/cepeter-job/spt-downloader (GPL-3.0)\n\n'
        'Jalankan SPTDownloader.exe tanpa hak administrator. Python/Tcl dan uv untuk GUI sudah disertakan.\n'
        f'Runtime GUI: CPython {expected} x64; profil build: {python_profile}.\n'
        f'Persiapan worker memasang CPython managed {python_version()} x64 di LocalAppData\\SPTDownloader.\n'
        'Dependency worker memakai lock SHA-256 yang disertakan; Python sistem dan registry tidak diubah.\n'
        'Persiapan pertama memerlukan internet; ekspor membutuhkan akses intranet yang sah dan Edge/Chrome.\n'
        'Masukkan akun/sandi melalui Pengaturan; sandi disimpan di Windows Credential Manager.\n'
        'Simpan pengaturan, lalu pilih Cek Kredensial: sesi terisolasi baru, satu upaya login, tanpa ekspor.\n'
        'Login berhasil hanya muncul setelah pengiriman sandi tersimpan terverifikasi.\n'
        'NPWP harus tepat 16 digit ASCII; tahun pajak empat digit. Mulai menjalankan satu pekerjaan baca-saja.\n'
        'Setelah inventaris, pilih SPT lalu klik Sedot SPT terpilih. Tidak ada pilihan otomatis.\n'
        'resume.xlsx diperbarui otomatis setelah verifikasi scope; file SPT/PDF yang sudah ada tetap memerlukan konfirmasi.\n'
        'Periksa folder dan daftar SPT/PDF pada konfirmasi; setiap file disetujui diganti seluruhnya sesuai pilihan saat ini.\n'
        'Jangan ganti mempertahankan file lama. Workbook masa lain tetap tersimpan; resume.xlsx mengindeks seluruh workbook dalam folder yang scope-nya terverifikasi.\n'
        'Selesaikan CAPTCHA/MFA dan halaman login yang belum dikenali secara manual di browser aplikasi.\n'
        'Stop mempertahankan checkpoint PARTIAL lokal; hanya proses browser milik aplikasi yang ditutup.\n'
        'Hasil: folder Downloads\\NPWP - NAMA WP\\TAHUN PAJAK\\WAKTU EKSPOR. Simpan semua Excel bersama.\n'
        '100% berarti COMPLETE terverifikasi untuk pilihan yang dikonfirmasi. Pekerjaan parsial, terhalang, atau dibatalkan tidak dinyatakan berhasil.\n'
        'Diagnostik lokal: Pengaturan > Buka folder log. INFO default; SPT_LOG_LEVEL=DEBUG menambah detail tanpa data pajak.\n'
        'Executable belum bertanda tangan. Verifikasi build/sumber GitHub; jangan nonaktifkan Defender atau TLS.\n',
        encoding='utf-8')
    print('Built and self-tested:',executable)
    return executable


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--python-profile', choices=tuple(PYTHON_PROFILES), default='production',
                        help='Profil build terverifikasi; kandidat belum mengubah default worker.')
    args=parser.parse_args(argv)
    build(args.output, args.python_profile)


if __name__=='__main__':main()
