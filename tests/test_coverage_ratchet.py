"""Coverage gates require the complete Windows union and exact integer ratios."""
from copy import deepcopy
import importlib
import importlib.util
import json
import sys

import pytest

from test_ci_sharding import evidence, VERSION, COMMIT, RUN_ID, RUN_ATTEMPT


def gate():
    assert importlib.util.find_spec('scripts.coverage_ratchet'), 'Windows coverage ratchet is not implemented'
    return importlib.import_module('scripts.coverage_ratchet')


def report():
    counts = dict(covered_lines=9, num_statements=10, missing_lines=1,
                  covered_branches=3, num_branches=4, missing_branches=1)
    return {'meta': {'branch_coverage': True}, 'totals': dict(counts),
            'files': {'coretax_fixture.py': {'summary': dict(counts),
                      'executed_lines': list(range(1, 10)), 'missing_lines': [10]}}}


def policy():
    return {'schema': 1, 'totals': {'line': 90, 'branch': 75},
            'modules': {'coretax_fixture.py': {'line': 90, 'branch': 75}}, 'diff_line': 80}


def test_line_and_branch_floors_are_distinct_and_allow_the_exact_boundary():
    observed = gate().evaluate(report(), policy())
    assert observed['totals']['line'] == 90
    assert observed['totals']['branch'] == 75
    assert observed['modules']['coretax_fixture.py'] == observed['totals']


@pytest.mark.parametrize('field', ['line', 'branch'])
def test_regression_in_either_ratio_blocks_the_gate(field):
    rules = policy()
    rules['modules']['coretax_fixture.py'][field] += 1
    with pytest.raises(ValueError):
        gate().evaluate(report(), rules)


@pytest.mark.parametrize('mutation', [
    'not-branch', 'empty-files', 'missing-module', 'bool-counter',
    'contradictory-count', 'wrong-totals', 'duplicate-path', 'missing-summary',
    'unknown-policy', 'bool-policy', 'missing-line-list',
])
def test_partial_or_malformed_reports_cannot_satisfy_the_ratchet(mutation):
    observed, rules = report(), policy()
    if mutation == 'not-branch':
        observed['meta']['branch_coverage'] = False
    elif mutation == 'empty-files':
        observed['files'] = {}
    elif mutation == 'missing-module':
        rules['modules']['coretax_missing.py'] = {'line': 1, 'branch': 1}
    elif mutation == 'bool-counter':
        observed['files']['coretax_fixture.py']['summary']['covered_lines'] = True
    elif mutation == 'contradictory-count':
        observed['files']['coretax_fixture.py']['summary']['missing_lines'] = 0
    elif mutation == 'wrong-totals':
        observed['totals']['covered_lines'] = 8
        observed['totals']['missing_lines'] = 2
    elif mutation == 'duplicate-path':
        observed['files']['CORETAX_fixture.py'] = deepcopy(observed['files']['coretax_fixture.py'])
    elif mutation == 'missing-summary':
        del observed['files']['coretax_fixture.py']['summary']
    elif mutation == 'unknown-policy':
        rules['ignore_missing'] = True
    elif mutation == 'bool-policy':
        rules['totals']['line'] = True
    else:
        del observed['files']['coretax_fixture.py']['missing_lines']
    with pytest.raises(ValueError):
        gate().evaluate(observed, rules)


def test_fractional_percentage_is_never_rounded_up_to_pass():
    observed = report()
    counts = dict(covered_lines=799, num_statements=1000, missing_lines=201,
                  covered_branches=3, num_branches=4, missing_branches=1)
    observed['totals'] = dict(counts)
    observed['files']['coretax_fixture.py'] = {'summary': dict(counts),
        'executed_lines': list(range(1, 800)), 'missing_lines': list(range(800, 1001))}
    rules = policy()
    rules['totals']['line'] = rules['modules']['coretax_fixture.py']['line'] = 80
    with pytest.raises(ValueError):
        gate().evaluate(observed, rules)


def test_diff_gate_counts_only_changed_executable_production_lines():
    with pytest.raises(ValueError):
        gate().evaluate(report(), policy(), changed={'coretax_fixture.py': {9, 10, 999}})
    observed = gate().evaluate(report(), policy(), changed={'coretax_fixture.py': {1, 2, 999}})
    assert observed['diff']['covered'] == observed['diff']['statements'] == 2
    assert observed['diff']['line'] == 100


def test_unmeasured_changed_production_module_is_refused():
    with pytest.raises(ValueError):
        gate().evaluate(report(), policy(), changed={'coretax_new.py': {1}})


def test_new_excluded_production_line_cannot_hide_a_diff_regression():
    observed = report()
    observed['files']['coretax_fixture.py']['excluded_lines'] = [11]
    with pytest.raises(ValueError):
        gate().evaluate(observed, policy(), changed={'coretax_fixture.py': {11}})


@pytest.mark.parametrize('mutation', ['missing-shard', 'previous-run', 'failed-case', 'reversed'])
def test_missing_failed_or_foreign_windows_evidence_cannot_pass(mutation):
    _, shards = evidence()
    if mutation == 'missing-shard':
        shards.pop()
    elif mutation == 'previous-run':
        shards[1]['run_id'] = '122'
    elif mutation == 'failed-case':
        shards[1]['exitstatus'] = 1
    else:
        shards.reverse()
    with pytest.raises(ValueError):
        gate().check_windows_inputs(shards, mode='two-shards', python_version=VERSION,
                                    commit=COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


def test_complete_windows_shards_and_serial_are_both_supported():
    serial, shards = evidence()
    assert gate().check_windows_inputs(shards, mode='two-shards', python_version=VERSION,
        commit=COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT) == set(serial['all'])
    assert gate().check_windows_inputs([serial], mode='serial', python_version=VERSION,
        commit=COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT) == set(serial['all'])


def test_data_file_slots_must_match_the_selected_windows_mode(tmp_path):
    for name in ('shard-0', 'shard-1'):
        folder = tmp_path / name
        folder.mkdir()
        (folder / ('.coverage.' + name)).write_bytes(b'synthetic source data')
    assert len(gate().data_files(tmp_path, 'two-shards')) == 2
    (tmp_path / 'shard-1' / '.coverage.shard-1').unlink()
    with pytest.raises(ValueError):
        gate().data_files(tmp_path, 'two-shards')


def test_git_diff_keeps_added_production_lines_and_ignores_deleted_or_test_lines(monkeypatch):
    base, head = 'a' * 40, 'b' * 40

    def git(*args):
        if args[0] == 'rev-parse':
            return args[-1].split('^')[0] + '\n'
        if '--name-only' in args:
            return 'coretax_example.py\x00tests/test_example.py\x00spt_desktop/example.py\x00'
        assert '--no-ext-diff' in args and '--no-textconv' in args and '--no-renames' in args
        if args[-1].startswith('coretax'):
            return '@@ -1 +2,2 @@\n@@ -9,2 +10,0 @@\n'
        return '@@ -3 +4 @@\n'

    monkeypatch.setattr(gate(), '_git', git)
    assert gate().changed_lines(base, head) == {
        'coretax_example.py': {2, 3}, 'spt_desktop/example.py': {4}}
    with pytest.raises(ValueError):
        gate().changed_lines('--option', head)


def raw_inputs(tmp_path, monkeypatch, bad=None):
    """Real pinned coverage databases, without executing the synthetic source."""
    from coverage import CoverageData

    monkeypatch.chdir(tmp_path)
    (tmp_path / '.coveragerc').write_text('[run]\nbranch=True\nrelative_files=True\nsource=.\n', encoding='utf-8')
    (tmp_path / 'coretax_fixture.py').write_text('value = 1\nvalue += 1\n', encoding='utf-8')
    _, shards = evidence()
    for index in (0, 1):
        folder = tmp_path / ('shard-' + str(index))
        folder.mkdir()
        (folder / 'test-inventory.json').write_text(json.dumps(shards[index]), encoding='utf-8')
        path = folder / ('.coverage.shard-' + str(index))
        if index == 1 and bad == 'corrupt':
            path.write_bytes(b'nonempty corrupt coverage input')
            continue
        data = CoverageData(basename=str(path))
        if index == 1 and bad == 'line-only':
            data.add_lines({'coretax_fixture.py': [2]})
        elif index == 1 and bad == 'empty':
            data.add_arcs({})
        else:
            line = index + 1
            data.add_arcs({'coretax_fixture.py': [(-1, line), (line, -1)]})
        data.write()
    rules = {'schema': 1, 'totals': {'line': 1, 'branch': 0},
             'modules': {'coretax_fixture.py': {'line': 1, 'branch': 0}}, 'diff_line': 80}
    (tmp_path / 'policy.json').write_text(json.dumps(rules), encoding='utf-8')
    monkeypatch.setattr(sys, 'argv', ['coverage_ratchet', '--root', str(tmp_path),
        '--mode', 'two-shards', '--python-version', VERSION, '--commit', COMMIT,
        '--run-id', RUN_ID, '--run-attempt', RUN_ATTEMPT,
        '--policy', str(tmp_path / 'policy.json'), '--output', str(tmp_path / 'proof')])


@pytest.mark.parametrize('bad', ['corrupt', 'empty', 'line-only'])
def test_passing_inventories_cannot_hide_an_unreadable_or_unmeasured_raw_shard(tmp_path, monkeypatch, bad):
    raw_inputs(tmp_path, monkeypatch, bad)
    # One surviving half exceeds the intentionally low floor. Input custody must
    # reject the bad second half, regardless of that partial report's percentage.
    with pytest.raises(ValueError):
        gate().main()
    assert not (tmp_path / 'proof' / 'coverage-gate.json').exists()


def test_both_real_raw_shards_contribute_to_the_published_gate(tmp_path, monkeypatch):
    raw_inputs(tmp_path, monkeypatch)
    gate().main()
    result = json.loads((tmp_path / 'proof' / 'coverage-gate.json').read_text(encoding='utf-8'))
    assert result['measured']['totals']['line'] == 100
    combined = json.loads((tmp_path / 'proof' / 'coverage-windows.json').read_text(encoding='utf-8'))
    assert combined['files']['coretax_fixture.py']['executed_lines'] == [1, 2]
