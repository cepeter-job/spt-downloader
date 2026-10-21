"""Hitung checksum dan baca kembali daftar berkas artefak Windows yang diizinkan."""
import argparse
import hashlib
import json
from pathlib import Path

from build_desktop import validate_report
from spt_desktop.runtime import PYTHON_PROFILES


PAYLOAD = ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json')
MANIFEST = 'SHA256SUMS.txt'


def checked_report(folder, python_version):
    for name in PAYLOAD:
        path = folder / name
        if path.is_symlink() or not path.is_file():
            raise ValueError('Artifact file is missing or not a regular file: ' + name)
    report = json.loads((folder / 'build-selftest.json').read_text(encoding='utf-8'))
    if report.get('python') != python_version or report.get('python_implementation') != 'CPython':
        raise ValueError('Artifact reports the wrong Python version or implementation.')
    expected = {'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
                'credentials_accessed': False, 'live_scrape': False, 'free_threaded': False}
    # JSON angka 1/0 tidak boleh menyamar sebagai boolean bukti self-test,
    # walaupun perbandingan nilai Python menganggapnya sama dengan True/False.
    if any(type(report.get(key)) is not type(value) or report[key] != value
           for key, value in expected.items()):
        raise ValueError('Artifact has an unsuccessful or unsafe frozen self-test report.')
    profile = next((name for name, version in PYTHON_PROFILES.items() if version == python_version), None)
    if not profile or report.get('build_profile') != profile:
        raise ValueError('Artifact build profile does not match its Python version.')
    try:
        validate_report(report, profile)
    except RuntimeError as error:
        raise ValueError('Artifact lacks the required frozen GUI, Tcl/Tk or worker evidence.') from error


def checksums(folder):
    lines = []
    for name in PAYLOAD:
        with (folder / name).open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        lines.append(f'{digest}  {name}\n')
    return ''.join(lines)


def write_checksums(folder, python_version):
    folder = Path(folder)
    checked_report(folder, python_version)
    (folder / MANIFEST).write_text(checksums(folder), encoding='ascii')


def verify(folder, python_version):
    folder = Path(folder)
    # Periksa isi arsip sebelum hash: manifest yang benar tidak mengesahkan
    # berkas tambahan seperti profil browser atau log pribadi.
    if {path.name for path in folder.iterdir()} != set(PAYLOAD) | {MANIFEST}:
        raise ValueError('Downloaded artifact differs from the exact five-file allowlist.')
    checked_report(folder, python_version)
    path = folder / MANIFEST
    if path.is_symlink() or not path.is_file() or path.read_text(encoding='ascii') != checksums(folder):
        raise ValueError('Artifact SHA256SUMS is incomplete or does not match the downloaded bytes.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('write-checksums', 'verify'))
    parser.add_argument('folder', type=Path)
    parser.add_argument('--python-version', required=True)
    args = parser.parse_args(argv)
    (write_checksums if args.command == 'write-checksums' else verify)(args.folder, args.python_version)
    print('Verified Windows payload and frozen self-test for Python ' + args.python_version)


if __name__ == '__main__':
    main()
