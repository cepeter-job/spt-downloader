"""Hitung checksum dan baca kembali daftar berkas artefak Windows yang diizinkan."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from build_desktop import validate_report
from spt_desktop.runtime import PYTHON_PROFILES


BASE_PAYLOAD = ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json')
PAYLOAD = BASE_PAYLOAD + ('build-info.json', 'distribution-sbom.json')
MANIFEST = 'SHA256SUMS.txt'


def checked_report(folder, python_version):
    for name in BASE_PAYLOAD:
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
    return report


def validate_build_info(data):
    if (not isinstance(data, dict) or set(data) != {'schema', 'commit', 'run_id', 'run_attempt'}
            or type(data.get('schema')) is not int or data['schema'] != 1
            or not isinstance(data.get('commit'), str)
            or not re.fullmatch(r'[0-9a-f]{40}', data['commit'])
            or not isinstance(data.get('run_id'), str)
            or not re.fullmatch(r'[1-9][0-9]*', data['run_id'])
            or type(data.get('run_attempt')) is not int or data['run_attempt'] < 1):
        raise ValueError('Distribution build-info.json identity is missing or invalid.')
    return data


def checked_build_info(folder):
    path = Path(folder) / 'build-info.json'
    if path.is_symlink() or not path.is_file():
        raise ValueError('Distribution build-info.json is missing or not a regular file.')
    return validate_build_info(json.loads(path.read_text(encoding='utf-8')))


def write_build_info(folder, python_version):
    if python_version not in PYTHON_PROFILES.values():
        raise ValueError('Build identity requires a reviewed Python version.')
    attempt = os.environ.get('GITHUB_RUN_ATTEMPT', '')
    data = validate_build_info({
        'schema': 1, 'commit': os.environ.get('GITHUB_SHA', ''),
        'run_id': os.environ.get('GITHUB_RUN_ID', ''),
        'run_attempt': int(attempt) if attempt.isascii() and attempt.isdecimal() else None,
    })
    path = Path(folder) / 'build-info.json'
    if path.is_symlink():
        raise ValueError('Refusing a linked build-info.json destination.')
    path.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')


def checked_distribution(folder):
    from scripts.ci_sbom import validate_sbom

    identity = checked_build_info(folder)
    path = folder / 'distribution-sbom.json'
    if path.is_symlink() or not path.is_file():
        raise ValueError('Distribution SBOM is missing or not a regular file.')
    with (folder / 'SPTDownloader.exe').open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    validate_sbom(json.loads(path.read_text(encoding='utf-8')),
                  build_info=identity, executable_digest=digest)
    return identity


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
    checked_distribution(folder)
    (folder / MANIFEST).write_text(checksums(folder), encoding='ascii')


def verify(folder, python_version):
    folder = Path(folder)
    # Periksa isi arsip sebelum hash: manifest yang benar tidak mengesahkan
    # berkas tambahan seperti profil browser atau log pribadi.
    if {path.name for path in folder.iterdir()} != set(PAYLOAD) | {MANIFEST}:
        raise ValueError('Downloaded artifact differs from the exact seven-file allowlist.')
    checked_report(folder, python_version)
    checked_distribution(folder)
    path = folder / MANIFEST
    if path.is_symlink() or not path.is_file() or path.read_text(encoding='ascii') != checksums(folder):
        raise ValueError('Artifact SHA256SUMS is incomplete or does not match the downloaded bytes.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('build-info', 'write-checksums', 'verify'))
    parser.add_argument('folder', type=Path)
    parser.add_argument('--python-version', required=True)
    args = parser.parse_args(argv)
    functions = {'build-info': write_build_info, 'write-checksums': write_checksums, 'verify': verify}
    functions[args.command](args.folder, args.python_version)
    print('Completed ' + args.command + ' for Python ' + args.python_version)


if __name__ == '__main__':
    main()
