"""Temporary dependency preparation; publish unreferenced objects, never branch refs."""
import argparse
import ast
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess
import urllib.request
import zipfile

MAIN = '198edafdd24f6fb37ac60b34caea60540ade72e3'
DEPENDENCY = '4f893e5fb0b1b509892eac0b25025671dc3506cd'
REPO = 'cepeter-job/spt-downloader'
PINS = {
    'spt_desktop/runtime.py': 1,
    '.github/workflows/windows-build.yml': 4,
    '.github/workflows/windows-shard-benchmark.yml': 1,
    'setup.cmd': 3,
    'docs/pengembangan.md': 1,
    'docs/python-314.md': 2,
}
ALLOWED = set(PINS) | {'requirements-build.txt', 'locks/build.txt', 'locks/audit.txt'}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def prepare(root, dependency, out):
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == MAIN
    assert git(dependency, 'rev-parse', 'HEAD').decode().strip() == DEPENDENCY
    for name in ('requirements-build.txt', 'locks/build.txt'):
        (root / name).write_bytes(git(dependency, 'show', 'HEAD:' + name))
    for name, count in PINS.items():
        value = git(root, 'show', 'HEAD:' + name)
        assert value.count(b'0.13.1') == count, name
        updated = value.replace(b'0.13.1', b'0.13.4')
        if name.endswith('.py'):
            ast.parse(updated, filename=name)
        (root / name).write_bytes(updated)
    path = root / 'locks/audit.txt'
    old = (b'certifi==2026.7.22 \\\n'
           b'    --hash=sha256:62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775 \\\n'
           b'    --hash=sha256:741e2c3b351ddf169a738da9f2c048608ff7f2c5cc02f1ebc6b118bb090d5d55')
    new = (b'certifi==2026.10.19 \\\n'
           b'    --hash=sha256:035c1e85572b141bf1c3a3eff0e33a8eb74917522f2559075ff8d2fea780a1ae \\\n'
           b'    --hash=sha256:42d35340cc5b9ba78e818ddbff0c5b1c2b779de448a340fd1b989f5fa8670e1b')
    value = git(root, 'show', 'HEAD:locks/audit.txt')
    assert value.count(old) == 1
    path.write_bytes(value.replace(old, new))
    subprocess.run(['git', '-C', str(root), 'diff', '--check'], check=True)
    changed = set(git(root, 'diff', '--name-only').decode().splitlines())
    assert changed == ALLOWED, changed
    (out / 'candidate.patch').write_bytes(git(root, 'diff', '--binary'))
    with zipfile.ZipFile(out / 'candidate-files.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(changed):
            archive.write(root / name, name)
    print('Prepared exact dependency delta; no product behavior or test assertions changed.')


def post(path, payload):
    assert path in ('git/blobs', 'git/trees')
    request = urllib.request.Request('https://api.github.com/repos/' + REPO + '/' + path,
        data=json.dumps(payload).encode(), method='POST', headers={
            'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
            'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28',
            'Content-Type': 'application/json'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def publish(root, out):
    assert os.environ['GITHUB_REPOSITORY'] == REPO
    assert git(root, 'rev-parse', 'HEAD').decode().strip() == MAIN
    changed = set(git(root, 'diff', '--name-only').decode().splitlines())
    assert changed == ALLOWED
    subprocess.run(['git', '-C', str(root), 'add', '--', *sorted(changed)], check=True)
    entries, proof = [], []
    for name in sorted(changed):
        data = git(root, 'show', ':' + name)
        sha = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        result = post('git/blobs', {'content': base64.b64encode(data).decode(), 'encoding': 'base64'})
        assert result['sha'] == sha
        entries.append({'path': name, 'mode': '100644', 'type': 'blob', 'sha': sha})
        proof.append({'path': name, 'blob': sha, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
    base = git(root, 'rev-parse', 'HEAD^{tree}').decode().strip()
    tree = post('git/trees', {'base_tree': base, 'tree': entries})['sha']
    assert tree == git(root, 'write-tree').decode().strip()
    report = {'base_commit': MAIN, 'dependency_commit': DEPENDENCY, 'base_tree': base,
              'candidate_tree': tree, 'entries': entries, 'files': proof,
              'branch_refs_changed': False, 'commits_created': False,
              'method': 'Unreferenced blobs/tree only; parent must review and explicitly publish commit'}
    (out / 'prepared-tree.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['prepare', 'publish'])
    parser.add_argument('--source', required=True)
    parser.add_argument('--dependency')
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    root, out = Path(args.source).resolve(), Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if args.mode == 'prepare':
        prepare(root, Path(args.dependency).resolve(), out)
    else:
        publish(root, out)


if __name__ == '__main__':
    main()
