"""Build and exercise the Windows GUI without bundling private workspace data."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from spt_desktop.runtime import WORKER_FILES,UV_VERSION
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


def build(output):
    if sys.platform!='win32' or struct.calcsize('P')!=8 or sys.version_info[:2]!=(3,11):
        raise RuntimeError('Build requires Windows CPython 3.11 x64.')
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
    if not (data['ok'] and data['frozen'] and data['uv_bundled'] and data['bits']==64
            and data['worker_resources']==list(WORKER_FILES)
            and not data['credentials_accessed'] and not data['live_scrape']):
        raise RuntimeError('Packaged application self-test failed')
    shutil.copy2(ROOT/'LICENSE',output/'LICENSE.txt')
    (output/'README.txt').write_text(
        'SPT Downloader — Windows 10/11 x64\n'
        'Source/license: https://github.com/cepeter-job/spt-downloader (GPL-3.0)\n\n'
        'Run SPTDownloader.exe without administrator rights. The GUI includes its Python/Tcl runtime and uv.\n'
        'Worker setup uses compatible installed Python or portable CPython 3.11 in LocalAppData\\SPTDownloader.\n'
        'First setup may require internet access; exporting requires authorized intranet access and Edge/Chrome.\n'
        'Enter your account/password only in Pengaturan; the password is stored in Windows Credential Manager.\n'
        'NPWP is exactly 16 ASCII digits; tax year is four digits. Mulai runs one read-only job.\n'
        'CAPTCHA/MFA and unknown login layouts require completing login in the application browser.\n'
        'Stop preserves local PARTIAL checkpoints; only owned browser processes are closed.\n'
        'Output: resolved Downloads\\NPWP - NAMA WP\\TAHUN PAJAK\\WAKTU EKSPOR. Keep all Excel files together.\n'
        '100% means verified COMPLETE. Partial/blocked/cancelled jobs do not report success.\n'
        'This executable is unsigned. Verify its GitHub build/source; do not disable Defender or TLS validation.\n',
        encoding='utf-8')
    print('Built and self-tested:',executable)
    return executable


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    args=parser.parse_args(argv)
    build(args.output)


if __name__=='__main__':main()
