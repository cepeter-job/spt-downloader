"""Package an isolated unsigned launcher; run only on a GitHub Windows runner."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.launcher_candidate.inventory import validate_inventory, validate_candidate_report


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def production_snapshot():
    from spt_desktop.paths import workspace_root
    root = workspace_root()
    return {'exists': root.exists(), 'files': {
        path.relative_to(root).as_posix(): digest(path) for path in root.rglob('*') if path.is_file()}}


def run_selftest(command, report):
    from spt_desktop.windows import ProcessJob
    with ProcessJob() as owned:
        process = owned.spawn([*map(str, command), '--self-test', '--candidate-report', '--report', str(report)])
        try:
            code = process.wait(timeout=90)
            if code:
                raise RuntimeError(f'Candidate self-test exited {code}')
        finally:
            owned.close()
            process.wait(timeout=10)
    return json.loads(report.read_text(encoding='utf-8'))


def package(runtime, output):
    runtime, output = runtime.resolve(strict=True), output.absolute()
    if output.exists():
        raise ValueError('candidate output must be a new directory')
    if digest(runtime / 'inventory.json') != '9758f2a63e8815952ca91178a9c20397f4292ad2aca8bfbff0feeb3c87b80239':
        raise ValueError('runtime inventory is not the exact qualified artifact')
    inventory = json.loads((runtime / 'inventory.json').read_text(encoding='utf-8'))
    validate_inventory(inventory, runtime)
    if Path(sys.base_prefix).resolve() != runtime:
        raise ValueError('packaging interpreter must use the exact candidate runtime')
    production_before = production_snapshot()
    # All setup/cache state belongs to this new output workspace, never the worker.
    output.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix='spt-candidate-package-') as scratch_name:
        scratch = Path(scratch_name)
        env = os.environ.copy()
        env.update(UV_CACHE_DIR=str(scratch / 'uv-cache'), UV_PYTHON_DOWNLOADS='never',
                   PYTHONDONTWRITEBYTECODE='1', LOCALAPPDATA=str(scratch / 'local-app-data'))
        production = scratch / 'local-app-data' / 'SPTDownloader'
        production.mkdir(parents=True)
        for name, value in {'preferences.json': '{"identifier":"SYNTHETIC_PRESERVED"}',
                            'worker-inventory.json': '{"python":"3.14.8","uv":"0.13.4","synthetic":true}',
                            'cache/synthetic-marker': 'preserve synthetic production cache'}.items():
            path = production / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding='utf-8')
        before = {path.relative_to(production).as_posix(): digest(path) for path in production.rglob('*') if path.is_file()}
        venv = scratch / 'build-env'
        subprocess.run(['uv', 'venv', '--python', str(runtime / 'python.exe'), str(venv)], env=env, check=True)
        python = venv / 'Scripts/python.exe'
        subprocess.run(['uv', 'pip', 'sync', '--python', str(python), '--require-hashes', '--only-binary', ':all:', str(ROOT / 'locks/build.txt')], env=env, check=True)
        # Re-enter through the candidate venv to reuse the production build validator.
        code = ('import sys; sys.path.insert(0,sys.argv[1]); import build_desktop; '
                'build_desktop.build(sys.argv[2],candidate_runtime=sys.argv[3])')
        source_report = output / 'source-selftest.json'
        subprocess.run([str(python), '-B', str(ROOT / 'spt_gui.py'), '--self-test', '--candidate-report', '--report', str(source_report)], cwd=scratch, env=env, check=True, timeout=90)
        validate_candidate_report(json.loads(source_report.read_text(encoding='utf-8')), inventory)
        subprocess.run([str(python), '-I', '-B', '-c', code, str(ROOT), str(scratch / 'build'), str(runtime)], cwd=scratch, env=env, check=True, timeout=600)
        subprocess.run([str(python), '-B', str(ROOT / 'scripts/launcher_candidate/inspect_archive.py'),
                        str(scratch / 'build/SPTDownloader.exe'), str(runtime), str(output / 'embedded-payload.json')],
                       cwd=scratch, env=env, check=True, timeout=90)
        for name in ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json'):
            shutil.copy2(scratch / 'build' / name, output / name)
        validate_candidate_report(json.loads((output / 'build-selftest.json').read_text(encoding='utf-8')), inventory)
        after = {path.relative_to(production).as_posix(): digest(path) for path in production.rglob('*') if path.is_file()}
        if before != after:
            raise RuntimeError('candidate preparation/startup changed synthetic production state')
        production_after = production_snapshot()
        if production_before != production_after:
            raise RuntimeError('candidate changed actual Known Folder production state')
        (output / 'worker-independence.json').write_text(json.dumps({
            'unchanged': True, 'before': before, 'after': after,
            'known_folder_unchanged': True, 'known_folder_before': production_before,
            'known_folder_after': production_after}, indent=2), encoding='utf-8')
    shutil.copytree(runtime / 'licenses', output / 'licenses')
    shutil.copy2(runtime / 'inventory.json', output / 'runtime-inventory.json')
    validate_inventory(inventory, runtime)
    manifest = {'schema': 1, 'head': os.environ['GITHUB_SHA'], 'run_id': os.environ['GITHUB_RUN_ID'],
                'attempt': os.environ['GITHUB_RUN_ATTEMPT'],
                'tree': subprocess.check_output(['git', 'rev-parse', 'HEAD^{tree}'], cwd=ROOT, text=True).strip(),
                'runtime_artifact': {'id': 12400037968, 'run': 39718421643,
                    'head': '0f699321614550c3d710cf66647878188d5f23ee',
                    'zip_sha256': '87b1ee844efa08398bb110f48335dfd68eeb2241da2bc6c38503e8448305fb4a'},
                'unsigned': True,
                'files': {path.relative_to(output).as_posix(): digest(path) for path in sorted(output.rglob('*')) if path.is_file()}}
    (output / 'candidate-manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('Verified isolated candidate application:', output)


def verify(output, report):
    """Validate exact read-back payload then run its bytes from outside the checkout."""
    if output.is_symlink() or output.is_junction():
        raise ValueError('linked candidate application directory')
    for path in output.rglob('*'):
        if path.is_symlink() or path.is_junction():
            raise ValueError('linked candidate application member')
    if report.is_relative_to(output):
        raise ValueError('read-back report must be outside immutable candidate')
    manifest = json.loads((output / 'candidate-manifest.json').read_text(encoding='utf-8'))
    expected = manifest['files']
    actual = {path.relative_to(output).as_posix(): digest(path) for path in output.rglob('*')
              if path.is_file() and path.relative_to(output).as_posix() != 'candidate-manifest.json'}
    if expected != actual or len({name.casefold() for name in actual}) != len(actual):
        raise ValueError('read-back application file set or hash mismatch')
    allowed = {'SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json',
               'source-selftest.json', 'worker-independence.json', 'runtime-inventory.json', 'embedded-payload.json'}
    if digest(output / 'runtime-inventory.json') != '9758f2a63e8815952ca91178a9c20397f4292ad2aca8bfbff0feeb3c87b80239':
        raise ValueError('read-back inventory is not the qualified runtime')
    inventory = json.loads((output / 'runtime-inventory.json').read_text(encoding='utf-8'))
    allowed.update(inventory['licenses'])
    if set(actual) != allowed:
        raise ValueError('read-back application allowlist mismatch')
    for name in inventory['licenses']:
        if actual[name] != inventory['files'][name]:
            raise ValueError('runtime license bytes changed')
    production_before = production_snapshot()
    with tempfile.TemporaryDirectory(prefix='spt-candidate-readback-') as folder:
        previous = Path.cwd()
        try:
            os.chdir(folder)
            result = run_selftest([output / 'SPTDownloader.exe'], report)
        finally:
            os.chdir(previous)
    if production_before != production_snapshot():
        raise RuntimeError('frozen readback changed production state')
    from build_desktop import validate_report
    validate_report(result)
    validate_candidate_report(result, inventory)
    print('Verified exact read-back candidate:', manifest['head'], manifest['run_id'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.verify:
        if args.report is None:
            parser.error('--verify requires --report outside the candidate directory')
        verify(args.output.resolve(strict=True), args.report.resolve())
    elif args.runtime is None:
        parser.error('--runtime is required for packaging')
    else:
        package(args.runtime, args.output)


def existing_workspace_fixture(root):
    raise NotImplementedError('connected existing workspace fixture is not implemented')
