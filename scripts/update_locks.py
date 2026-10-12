"""Regenerasi lock universal dengan uv yang dipin, tanpa mengganti berkas saat --check."""
import argparse
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

from spt_desktop.runtime import UV_VERSION


LOCK_INPUTS = (
    ('runtime', 'requirements.txt', None),
    ('test', 'requirements-test.txt', 'runtime'),
    ('build', 'requirements-build.txt', 'test'),
    ('audit', 'requirements-audit.txt', None),
)


def update_locks(root, uv, *, check=False, upgrade=False, offline=False):
    root = Path(root).resolve()
    version = subprocess.run([str(uv), '--version'], check=True, capture_output=True, text=True)
    if not re.match(r'uv\s+' + re.escape(UV_VERSION) + r'(?:\s|$)', version.stdout):
        raise RuntimeError(f'Regenerasi lock membutuhkan uv {UV_VERSION}.')
    changed = []
    with tempfile.TemporaryDirectory(prefix='spt-locks-') as folder:
        temporary = Path(folder)
        for name, _, _ in LOCK_INPUTS:
            existing = root / 'locks' / f'{name}.txt'
            if existing.is_file():
                shutil.copy2(existing, temporary / f'{name}.txt')
        for name, source, constraint in LOCK_INPUTS:
            output = temporary / f'{name}.txt'
            command = [str(uv), 'pip', 'compile', source, '--python-version', '3.11',
                       '--universal', '--generate-hashes', '--only-binary', ':all:',
                       '--no-annotate', '--custom-compile-command', 'python -m scripts.update_locks',
                       '--output-file', str(output), '--quiet']
            if constraint:
                command.extend(['--constraint', str(temporary / f'{constraint}.txt')])
            if upgrade:
                command.append('--upgrade')
            if offline:
                command.append('--offline')
            subprocess.run(command, cwd=root, check=True, capture_output=True, text=True)
            existing = root / 'locks' / f'{name}.txt'
            if not existing.is_file() or existing.read_bytes() != output.read_bytes():
                changed.append(name)
        # Semua resolusi harus berhasil sebelum satu pun lock yang ada diganti.
        if not check:
            (root / 'locks').mkdir(exist_ok=True)
            for name in changed:
                shutil.copyfile(temporary / f'{name}.txt', root / 'locks' / f'{name}.txt')
    return changed


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='Gagal jika isi lock perlu diperbarui.')
    mode.add_argument('--upgrade', action='store_true', help='Perbarui versi transitif yang diizinkan pin utama.')
    parser.add_argument('--offline', action='store_true', help='Gunakan metadata yang sudah ada di cache uv.')
    parser.add_argument('--uv', default='uv', help='Lokasi executable uv yang dipin.')
    args = parser.parse_args(argv)
    changed = update_locks(Path(__file__).resolve().parents[1], args.uv,
                           check=args.check, upgrade=args.upgrade, offline=args.offline)
    if args.check and changed:
        print('Lock belum sesuai sumber: ' + ', '.join(changed))
        return 1
    print('Lock diperbarui: ' + ', '.join(changed) if changed else 'Semua lock sesuai sumber dan pin uv.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
