"""Gate complete Windows coverage separately from portable measurement.

This CI-only module validates original test inventories before combining the
selected run's raw coverage files. It grants no product or live acceptance.
"""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys

from scripts.ci_tests import check_windows_inventories


COUNTS = ('covered_lines', 'num_statements', 'missing_lines',
          'covered_branches', 'num_branches', 'missing_branches')


def _path(value):
    if not isinstance(value, str) or not value or '\x00' in value or ':' in value:
        raise ValueError('Invalid coverage path')
    name = value.replace('\\', '/')
    path = PurePosixPath(name)
    if path.is_absolute() or any(p in ('', '.', '..') for p in name.split('/')):
        raise ValueError('Coverage paths must be canonical repository-relative paths')
    return name


def _paths(values):
    result, aliases = {}, set()
    for name, item in values.items():
        name = _path(name)
        if name.casefold() in aliases:
            raise ValueError('Duplicate coverage path')
        aliases.add(name.casefold())
        result[name] = item
    return result


def _floors(value):
    if not isinstance(value, dict) or set(value) != {'line', 'branch'}:
        raise ValueError('Expected separate line and branch floors')
    for floor in value.values():
        if type(floor) is not int or not 0 <= floor <= 100:
            raise ValueError('Coverage floors must be integer percentages')
    return value


def _policy(value):
    if (not isinstance(value, dict) or set(value) != {'schema', 'totals', 'modules', 'diff_line'}
            or type(value['schema']) is not int or value['schema'] != 1):
        raise ValueError('Unknown coverage policy')
    _floors(value['totals'])
    if not isinstance(value['modules'], dict) or not value['modules']:
        raise ValueError('Coverage policy must adopt modules')
    modules = _paths(value['modules'])
    for floors in modules.values():
        _floors(floors)
    _floors({'line': value['diff_line'], 'branch': 0})
    return modules


def _counts(value):
    if not isinstance(value, dict):
        raise ValueError('Missing coverage summary')
    result = {}
    for name in COUNTS:
        count = value.get(name)
        if type(count) is not int or count < 0:
            raise ValueError('Invalid coverage counter')
        result[name] = count
    if (result['covered_lines'] + result['missing_lines'] != result['num_statements']
            or result['covered_branches'] + result['missing_branches'] != result['num_branches']):
        raise ValueError('Contradictory coverage summary')
    return result


def _lines(value):
    if (not isinstance(value, (list, set))
            or any(type(line) is not int or line <= 0 for line in value)
            or len(value) != len(set(value))):
        raise ValueError('Invalid coverage line list')
    return set(value)


def _file(value):
    if not isinstance(value, dict):
        raise ValueError('Missing coverage file')
    counts = _counts(value.get('summary'))
    executed, missing = _lines(value.get('executed_lines')), _lines(value.get('missing_lines'))
    excluded = _lines(value.get('excluded_lines', []))
    if (executed & missing or (executed | missing) & excluded
            or len(executed) != counts['covered_lines'] or len(missing) != counts['missing_lines']):
        raise ValueError('Coverage line lists disagree with summary')
    return counts, executed, missing, excluded


def _ratio(covered, total, floor):
    if not total:
        if floor:
            raise ValueError('Coverage floor has no denominator')
        return None
    if covered * 100 < floor * total:
        raise ValueError('Coverage regressed below its floor')
    return round(covered * 100 / total, 4)


def _measure(counts, floors):
    if not counts['num_statements']:
        raise ValueError('Adopted coverage scope has no statements')
    return {'line': _ratio(counts['covered_lines'], counts['num_statements'], floors['line']),
            'branch': _ratio(counts['covered_branches'], counts['num_branches'], floors['branch'])}


def evaluate(report, policy, changed=None):
    """Return measured ratios, refusing malformed, incomplete or regressed data.

    Floors use exact integer products; display rounding cannot admit a result.
    Changed lines count executable statements only. New exclusions are refused.
    """
    modules = _policy(policy)
    if (not isinstance(report, dict) or not isinstance(report.get('meta'), dict)
            or report['meta'].get('branch_coverage') is not True
            or not isinstance(report.get('files'), dict) or not report['files']):
        raise ValueError('A complete branch coverage report is required')
    files = {name: _file(value) for name, value in _paths(report['files']).items()}
    totals = _counts(report.get('totals'))
    if any(totals[key] != sum(item[0][key] for item in files.values()) for key in COUNTS):
        raise ValueError('Coverage totals disagree with measured files')
    result = {'totals': _measure(totals, policy['totals']), 'modules': {}, 'diff': None}
    for name, floors in modules.items():
        if name not in files:
            raise ValueError('An adopted module is absent from coverage')
        result['modules'][name] = _measure(files[name][0], floors)
    if changed is not None:
        covered = statements = 0
        for name, lines in _paths(changed).items():
            lines = _lines(lines)
            if name not in files:
                raise ValueError('Changed production module is unmeasured')
            _, executed, missing, excluded = files[name]
            if lines & excluded:
                raise ValueError('Changed production lines cannot bypass coverage by exclusion')
            covered += len(lines & executed)
            statements += len(lines & (executed | missing))
        result['diff'] = {'covered': covered, 'statements': statements,
                          'line': _ratio(covered, statements, policy['diff_line']) if statements else None}
    return result


def _slots(mode):
    if mode == 'serial':
        return ('serial',)
    if mode == 'two-shards':
        return ('shard-0', 'shard-1')
    raise ValueError('Unknown Windows coverage mode')


def check_windows_inputs(inventories, *, mode, python_version, commit, run_id, run_attempt):
    """Require the complete passing fixed Windows partition from this run."""
    if not isinstance(inventories, list) or len(inventories) != len(_slots(mode)):
        raise ValueError('Missing Windows coverage inventory')
    return check_windows_inventories(inventories, python_version, commit,
                                    run_id=run_id, run_attempt=run_attempt)


def data_files(root, mode):
    """Select exact nonempty raw files; never glob old or portable coverage."""
    root = Path(root)
    result = []
    for slot in _slots(mode):
        folder = root / slot
        path = folder / ('.coverage.' + slot)
        if (root.is_symlink() or folder.is_symlink() or path.is_symlink()
                or not path.is_file() or path.stat().st_size == 0):
            raise ValueError('Missing ordinary Windows coverage file')
        result.append(path)
    return result


def _git(*args):
    return subprocess.check_output(['git', '--no-pager', *args]).decode('utf-8')


def changed_lines(base, head):
    """Read added production lines from literal validated commit objects."""
    for revision in (base, head):
        if not re.fullmatch('[0-9a-f]{40}', revision):
            raise ValueError('Coverage diff needs exact commit identities')
        if _git('rev-parse', '--verify', revision + '^{commit}').strip() != revision:
            raise ValueError('Coverage revision is not the exact commit')
    result = {}
    names = _git('diff', '--no-ext-diff', '--no-textconv', '--no-renames',
                 '--name-only', '-z', base, head).split('\x00')
    for name in filter(None, names):
        path = _path(name)
        if not ((path.startswith('coretax') and '/' not in path and path.endswith('.py'))
                or (path.startswith('spt_desktop/') and path.endswith('.py'))):
            continue
        diff = _git('diff', '--no-ext-diff', '--no-textconv', '--no-renames',
                    '--unified=0', base, head, '--', path)
        lines = set()
        for start, size in re.findall(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', diff, re.MULTILINE):
            lines.update(range(int(start), int(start) + (int(size) if size else 1)))
        if lines:
            result[path] = lines
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--mode', choices=('serial', 'two-shards'), required=True)
    parser.add_argument('--python-version', required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--run-attempt', required=True)
    parser.add_argument('--base', default='')
    parser.add_argument('--policy', type=Path, default=Path('coverage-policy.json'))
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    inventories = [json.loads((args.root / slot / 'test-inventory.json').read_text(encoding='utf-8'))
                   for slot in _slots(args.mode)]
    check_windows_inputs(inventories, mode=args.mode, python_version=args.python_version,
                         commit=args.commit, run_id=args.run_id, run_attempt=args.run_attempt)
    paths = data_files(args.root, args.mode)
    args.output.mkdir(parents=True, exist_ok=True)
    data = args.output / '.coverage-windows'
    env = dict(os.environ, COVERAGE_FILE=str(data))
    command = [sys.executable, '-m', 'coverage']
    subprocess.run([*command, 'combine', '--rcfile=.coveragerc', '--keep',
                    '--data-file', str(data), *map(str, paths)], check=True, env=env)
    for format_name in ('json', 'xml'):
        subprocess.run([*command, format_name, '--rcfile=.coveragerc',
                        '-o', str(args.output / ('coverage-windows.' + format_name))], check=True, env=env)
    report = json.loads((args.output / 'coverage-windows.json').read_text(encoding='utf-8'))
    policy = json.loads(args.policy.read_text(encoding='utf-8'))
    measured = evaluate(report, policy, changed_lines(args.base, args.commit) if args.base else None)
    proof = {'commit': args.commit, 'run_id': args.run_id, 'run_attempt': args.run_attempt,
             'mode': args.mode, 'base': args.base or None, 'policy': policy, 'measured': measured}
    (args.output / 'coverage-gate.json').write_text(json.dumps(proof, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
