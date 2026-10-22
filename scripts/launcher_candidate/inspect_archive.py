"""Inspect onefile members with locked PyInstaller on the packaging runner."""
import hashlib
import json
from pathlib import Path
import sys

from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from spt_desktop.runtime import WORKER_FILES


def inspect(executable, runtime, output):
    inventory = json.loads((runtime / 'inventory.json').read_text(encoding='utf-8'))
    reader = CArchiveReader(str(executable))
    files = {}
    expected_data = {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in (*WORKER_FILES, 'LICENSE')}
    expected_data.update({'candidate-licenses/' + name.removeprefix('licenses/'): value
                          for name, value in inventory['files'].items() if name.startswith('licenses/')})
    for kind, prefix in inventory['libraries'].items():
        expected_data.update({('_tcl_data/' if kind == 'tcl' else '_tk_data/') + name[len(prefix)+1:]: value
                              for name, value in inventory['files'].items() if name.startswith(prefix + '/')})
    for name, record in reader.toc.items():
        canonical = name.replace('\\', '/')
        data = reader.extract(name)
        if record[-1] == 'o':
            continue
        digest = hashlib.sha256(data).hexdigest()
        files[canonical] = {'sha256': digest, 'type': record[-1]}
        if record[-1] == 'x' and canonical != 'base_library.zip' and expected_data.get(canonical) != digest:
            raise ValueError('unapproved or changed embedded data: ' + canonical)
    for name, digest in expected_data.items():
        if files.get(name, {}).get('sha256') != digest:
            raise ValueError('missing approved embedded resource: ' + name)
    if not any(name == 'tools/uv.exe' for name in files):
        raise ValueError('missing bundled pinned uv')
    output.write_text(json.dumps({'files': files, 'approved_data': expected_data}, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    inspect(*map(Path, sys.argv[1:]))
