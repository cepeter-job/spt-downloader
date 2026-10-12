"""Bersihkan alias minor uv berbentuk file hasil pemulihan cache Windows."""
import argparse
import json
import os
from pathlib import Path
import re
import stat


def _require_plain_directory(path):
    metadata = path.lstat()
    if (not stat.S_ISDIR(metadata.st_mode)
            or getattr(metadata, 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
        raise ValueError('The Python cache must use a real, unredirected directory.')


def prepare_windows_python_cache(install_dir, runner_temp, python_version):
    """Perbaiki satu alias minor tepat tanpa mengikuti tautan atau menghapus direktori.

    setup-uv menyimpan direktori managed terpisah dari wheel. GNU tar dapat
    memulihkan junction NTFS versi minor uv sebagai entri berbentuk file.
    uv 0.12.22 selalu memanggil remove_dir pada alias sebelum membuat junction,
    termasuk saat interpreter exact tersedia (galat Windows 267).
    Hanya alias ini yang dibersihkan; instalasi tetap dilakukan uv yang dipin.
    """
    if not re.fullmatch(r'[1-9][0-9]*\.[0-9]+\.[0-9]+', python_version or ''):
        raise ValueError('An exact Python version is required for cache preparation.')
    managed, temporary = Path(install_dir), Path(runner_temp)
    if (not managed.is_absolute() or not temporary.is_absolute()
            or '..' in managed.parts or '..' in temporary.parts
            or managed != temporary / 'uv-python-dir'):
        raise ValueError('The managed cache root must be RUNNER_TEMP/uv-python-dir.')
    _require_plain_directory(temporary)
    if temporary.resolve(strict=True) != temporary:
        raise ValueError('The runner temporary directory has a redirected ancestor.')
    minor = '.'.join(python_version.split('.')[:2])
    alias = managed / f'cpython-{minor}-windows-x86_64-none'
    report = {'alias': alias.name, 'kind': 'missing', 'removed': False}
    try:
        _require_plain_directory(managed)
        metadata = alias.lstat()
    except FileNotFoundError:
        return report

    attributes = getattr(metadata, 'st_file_attributes', 0)
    reparse_tag = getattr(metadata, 'st_reparse_tag', 0)
    report.update(file_attributes=attributes, reparse_tag=reparse_tag)
    if stat.S_ISLNK(metadata.st_mode):
        report['kind'] = 'symlink'
    elif stat.S_ISDIR(metadata.st_mode):
        report['kind'] = 'junction' if attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT else 'directory'
        return report
    elif stat.S_ISREG(metadata.st_mode) and not attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT:
        report['kind'] = 'file'
    else:
        raise ValueError('The cached Python alias has an unsupported filesystem type.')

    # lstat dan unlink bekerja pada entri terakhir, termasuk tautan menggantung.
    # Jangan rekursif, mengikuti target alias, atau menghapus direktori versi patch.
    alias.unlink()
    report['removed'] = True
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python-version', required=True)
    args = parser.parse_args(argv)
    try:
        report = prepare_windows_python_cache(os.environ.get('UV_PYTHON_INSTALL_DIR', ''),
                                              os.environ.get('RUNNER_TEMP', ''), args.python_version)
    except ValueError as error:
        parser.exit(1, str(error) + '\n')
    except OSError as error:
        # Log bootstrap tidak mengungkap path lain atau nilai target tautan.
        parser.exit(1, f'Cannot prepare the cached Python alias ({type(error).__name__}).\n')
    print(json.dumps(report, sort_keys=True))


if __name__ == '__main__':
    main()
