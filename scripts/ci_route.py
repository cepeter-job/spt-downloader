"""Pilah perubahan secara konservatif dan periksa hasil gabungan GitHub Actions."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess


MAIN_REF = 'refs/heads/main'
DOC_FILES = frozenset({'README.md', 'AGENTS.md', 'CONTRIBUTING.md', 'SECURITY.md'})
JOBS = frozenset({'route', 'portable', 'windows', 'package', 'dependency-audit', 'attest'})


def is_documentation(path):
    parts = PurePosixPath(path).parts
    return path in DOC_FILES or (
        len(parts) > 1 and parts[0] == 'docs' and '..' not in parts
        and PurePosixPath(path).suffix == '.md'
    )


def choose_mode(event, paths, ref):
    if event == 'schedule':
        if ref != MAIN_REF:
            raise ValueError('The scheduled audit must use main.')
        return 'audit'
    if event in {'push', 'pull_request'} and paths and all(map(is_documentation, paths)):
        return 'docs'
    # Dispatch manual, pembanding kosong/tidak tersedia, dan path asing menjalankan seluruh CI.
    return 'full'


def execution_plan(event, profiles, windows_mode='', cache_mode=''):
    """Keep automatic runs serial; dispatch alone may select the bounded pilot."""
    windows_mode = windows_mode or 'serial'
    cache_mode = cache_mode or 'restore'
    if windows_mode not in {'serial', 'two-shards'} or cache_mode not in {'restore', 'cold'}:
        raise ValueError('Unknown Windows execution or cache mode.')
    if event != 'workflow_dispatch' and (windows_mode != 'serial' or cache_mode != 'restore'):
        raise ValueError('Only workflow_dispatch may select the Windows comparison pilot.')
    if (not isinstance(profiles, dict) or not profiles
            or any(not isinstance(value, str) or not value
                   for pair in profiles.items() for value in pair)):
        raise ValueError('The Windows matrix requires explicit Python profiles.')
    variants = [('serial', '')] if windows_mode == 'serial' else [('shard-0', '0/2'), ('shard-1', '1/2')]
    return {
        'windows_mode': windows_mode, 'cache_mode': cache_mode,
        'windows_matrix': {'include': [
            {'profile': profile, 'python': version, 'mode': label, 'shard': shard}
            for profile, version in profiles.items() for label, shard in variants
        ]},
    }


def validate_execution_plan(outputs, event):
    """Reject incomplete or forged matrix outputs even when a matrix job is green."""
    required = {'windows_mode', 'cache_mode', 'python_matrix', 'windows_matrix'}
    if not required <= outputs.keys() or any(not isinstance(outputs[key], str) for key in required):
        raise ValueError('CI execution-plan outputs are missing or malformed.')
    if not outputs['windows_mode'] or not outputs['cache_mode']:
        raise ValueError('CI execution-plan modes must be explicit.')
    try:
        matrix = json.loads(outputs['python_matrix'])
        windows = json.loads(outputs['windows_matrix'])
    except (TypeError, ValueError) as exc:
        raise ValueError('CI execution matrices are not valid JSON.') from exc
    if not isinstance(matrix, dict) or set(matrix) != {'include'}:
        raise ValueError('CI Python profiles are missing or malformed.')
    entries = matrix['include']
    if (not isinstance(entries, list) or not entries
            or any(not isinstance(entry, dict) or set(entry) != {'profile', 'python'}
                   or any(not isinstance(value, str) or not value for value in entry.values())
                   for entry in entries)):
        raise ValueError('CI Python profiles are missing or malformed.')
    profiles = {entry['profile']: entry['python'] for entry in entries}
    if len(profiles) != len(entries):
        raise ValueError('CI Python profiles are duplicated.')
    expected = execution_plan(event, profiles, outputs['windows_mode'], outputs['cache_mode'])
    if windows != expected['windows_matrix']:
        raise ValueError('CI Windows matrix does not match the complete execution plan.')


def changed_paths(repository, base, head):
    if not all(re.fullmatch(r'[0-9a-f]{40}', value or '') and set(value) != {'0'}
               for value in (base, head)):
        return None
    try:
        result = subprocess.run(
            ['git', 'diff', '--no-ext-diff', '--no-textconv', '--name-only',
             '--no-renames', '-z', base, head, '--'], cwd=repository,
            capture_output=True, check=True, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return [path.decode('utf-8', errors='surrogateescape')
            for path in result.stdout.split(b'\0') if path]


def validate_needs(needs, event, ref):
    if not isinstance(needs, dict) or set(needs) != JOBS:
        raise ValueError('CI returned a missing or unexpected workload result.')
    if needs['route'].get('result') != 'success':
        raise ValueError('CI routing did not succeed.')
    outputs = needs['route'].get('outputs', {})
    if not isinstance(outputs, dict):
        raise ValueError('CI routing outputs are missing or malformed.')
    mode = outputs.get('mode')
    if mode not in {'full', 'docs', 'audit'}:
        raise ValueError('CI routing returned an unknown mode.')
    if mode == 'docs' and event not in {'push', 'pull_request'}:
        raise ValueError('This event cannot skip validation as documentation.')
    if (mode == 'audit') != (event == 'schedule') or (event == 'schedule' and ref != MAIN_REF):
        raise ValueError('Only the main schedule may use audit-only routing.')
    validate_execution_plan(outputs, event)
    required = {'route'}
    if mode == 'full':
        required.update({'portable', 'windows', 'package', 'dependency-audit'})
        if event == 'push' and ref == MAIN_REF:
            required.add('attest')
    elif mode == 'audit':
        required.add('dependency-audit')
    for name in sorted(JOBS):
        expected = 'success' if name in required else 'skipped'
        actual = needs[name].get('result')
        if actual != expected:
            raise ValueError(f'{name} must be {expected}, received {actual!r}.')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('route', 'gate'))
    args = parser.parse_args(argv)
    event, ref = os.environ['GITHUB_EVENT_NAME'], os.environ['GITHUB_REF']
    if args.command == 'gate':
        validate_needs(json.loads(os.environ['CI_NEEDS']), event, ref)
        print('Every required CI workload succeeded.')
        return
    base = os.environ.get('PR_BASE_SHA' if event == 'pull_request' else 'PUSH_BEFORE_SHA', '')
    paths = changed_paths(Path.cwd(), base, os.environ.get('GITHUB_SHA', ''))
    mode = choose_mode(event, paths, ref)
    from spt_desktop.runtime import PYTHON_PROFILES
    matrix = {'include': [{'profile': profile, 'python': version}
                          for profile, version in PYTHON_PROFILES.items()]}
    plan = execution_plan(event, PYTHON_PROFILES, os.environ.get('WINDOWS_MODE_INPUT', ''),
                          os.environ.get('CACHE_MODE_INPUT', ''))
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        output.write(f'mode={mode}\n')
        output.write('python_matrix=' + json.dumps(matrix, separators=(',', ':')) + '\n')
        output.write('production_python=' + PYTHON_PROFILES['production'] + '\n')
        for key in ('windows_mode', 'cache_mode'):
            output.write(f'{key}={plan[key]}\n')
        output.write('windows_matrix=' + json.dumps(plan['windows_matrix'], separators=(',', ':')) + '\n')
    summary = (f'CI workload mode: {mode}. Windows: {plan["windows_mode"]}. '
               f'Cache: {plan["cache_mode"]}. Compared paths: {len(paths) if paths else "unavailable"}.')
    print(summary)
    if os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a', encoding='utf-8') as output:
            output.write(summary + '\n')


if __name__ == '__main__':
    main()
