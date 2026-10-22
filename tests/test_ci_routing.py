"""CI must not turn an unknown change or a missing workload into a green check."""
import importlib.util
import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


def ci_module(name):
    path = ROOT / 'scripts' / (name + '.py')
    assert path.is_file(), 'Fail-closed CI routing is missing: ' + name
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_matrix_and_audit_use_the_promoted_production_version(monkeypatch, tmp_path):
    route = ci_module('ci_route')
    monkeypatch.setattr(route, 'changed_paths', lambda *_: ['spt_desktop/runtime.py'])
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'pull_request')
    monkeypatch.setenv('GITHUB_REF', 'refs/pull/12/merge')
    monkeypatch.setenv('PR_BASE_SHA', 'a' * 40)
    monkeypatch.setenv('GITHUB_SHA', 'b' * 40)
    target = tmp_path / 'github-output'
    monkeypatch.setenv('GITHUB_OUTPUT', str(target))
    route.main(['route'])
    data = dict(line.split('=', 1) for line in target.read_text().splitlines())
    assert data['production_python'] == '3.14.8'
    assert json.loads(data['python_matrix']) == {
        'include': [{'profile': 'production', 'python': '3.14.8'}]
    }
    assert data['windows_mode'] == 'two-shards'
    assert data['cache_mode'] == 'restore'
    assert json.loads(data['windows_matrix']) == {'include': [
        {'profile': 'production', 'python': '3.14.8', 'mode': 'shard-0', 'shard': '0/2'},
        {'profile': 'production', 'python': '3.14.8', 'mode': 'shard-1', 'shard': '1/2'},
    ]}


@pytest.mark.parametrize('windows_mode,expected', [
    ('serial', [('serial', '')]),
    ('two-shards', [('shard-0', '0/2'), ('shard-1', '1/2')]),
])
@pytest.mark.parametrize('cache_mode', ['restore', 'cold'])
def test_dispatch_explicitly_selects_one_complete_serial_or_two_shard_plan(windows_mode, expected, cache_mode):
    plan = ci_module('ci_route').execution_plan(
        'workflow_dispatch', {'production': '3.14.8'}, windows_mode, cache_mode)
    assert plan == {
        'windows_mode': windows_mode, 'cache_mode': cache_mode,
        'windows_matrix': {'include': [
            {'profile': 'production', 'python': '3.14.8', 'mode': mode, 'shard': shard}
            for mode, shard in expected
        ]},
    }


@pytest.mark.parametrize('event', ['pull_request', 'push', 'schedule'])
def test_automatic_events_keep_two_shards_and_restore_caches(event):
    route = ci_module('ci_route')
    plan = route.execution_plan(event, {'production': '3.14.8'})
    assert plan['windows_mode'] == 'two-shards' and plan['cache_mode'] == 'restore'
    assert [entry['shard'] for entry in plan['windows_matrix']['include']] == ['0/2', '1/2']
    for windows_mode, cache_mode in [('serial', 'restore'), ('two-shards', 'cold'), ('serial', 'cold')]:
        with pytest.raises(ValueError, match='dispatch'):
            route.execution_plan(event, {'production': '3.14.8'}, windows_mode, cache_mode)


@pytest.mark.parametrize('windows_mode,cache_mode', [
    ('shard-0', 'restore'), ('three-shards', 'restore'),
    ('serial', 'warm'), ('serial ', 'restore'), ('serial', 'cold '),
])
def test_unknown_dispatch_settings_fail_closed(windows_mode, cache_mode):
    with pytest.raises(ValueError):
        ci_module('ci_route').execution_plan(
            'workflow_dispatch', {'production': '3.14.8'}, windows_mode, cache_mode)


def test_dispatch_outputs_bind_full_validation_to_the_selected_matrix(monkeypatch, tmp_path):
    route = ci_module('ci_route')
    monkeypatch.setattr(route, 'changed_paths', lambda *_: ['README.md'])
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'workflow_dispatch')
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/synthetic-pilot')
    monkeypatch.setenv('WINDOWS_MODE_INPUT', 'two-shards')
    monkeypatch.setenv('CACHE_MODE_INPUT', 'cold')
    target = tmp_path / 'github-output'
    monkeypatch.setenv('GITHUB_OUTPUT', str(target))
    route.main(['route'])
    data = dict(line.split('=', 1) for line in target.read_text().splitlines())
    assert data['mode'] == 'full'
    assert data['windows_mode'] == 'two-shards' and data['cache_mode'] == 'cold'
    assert json.loads(data['windows_matrix']) == {'include': [
        {'profile': 'production', 'python': '3.14.8', 'mode': 'shard-0', 'shard': '0/2'},
        {'profile': 'production', 'python': '3.14.8', 'mode': 'shard-1', 'shard': '1/2'},
    ]}
    # An explicit serial dispatch stays available after the automatic default changes.
    serial_target = tmp_path / 'github-output-serial'
    monkeypatch.setenv('GITHUB_OUTPUT', str(serial_target))
    monkeypatch.setenv('WINDOWS_MODE_INPUT', 'serial')
    route.main(['route'])
    serial = dict(line.split('=', 1) for line in serial_target.read_text().splitlines())
    assert serial['mode'] == 'full'
    assert serial['windows_mode'] == 'serial' and serial['cache_mode'] == 'cold'
    assert json.loads(serial['windows_matrix']) == {'include': [
        {'profile': 'production', 'python': '3.14.8', 'mode': 'serial', 'shard': ''},
    ]}


@pytest.mark.parametrize('paths, expected', [
    (['README.md', 'docs/development.md'], 'docs'),
    (['AGENTS.md', 'docs/audit/notes.md'], 'docs'),
    (['docs/new-guide.md', 'coretax.py'], 'full'),
    (['docs/run.py'], 'full'),
    (['spt_desktop/README.md'], 'full'),
    (['LICENSE'], 'full'),
    (['.github/workflows/windows-build.yml'], 'full'),
    (['locks/runtime.txt'], 'full'),
    (['tests/new_test.py'], 'full'),
    ([], 'full'),
    (None, 'full'),
])
def test_only_known_documentation_changes_may_skip_execution(paths, expected):
    assert ci_module('ci_route').choose_mode('pull_request', paths, 'refs/pull/1/merge') == expected


def test_manual_dispatch_forces_full_validation_and_schedule_only_audits_main():
    route = ci_module('ci_route')
    plan = route.execution_plan('workflow_dispatch', {'production': '3.14.8'})
    assert plan['windows_mode'] == 'two-shards' and plan['cache_mode'] == 'restore'
    assert route.choose_mode('workflow_dispatch', ['README.md'], 'refs/heads/main') == 'full'
    assert route.choose_mode('schedule', None, 'refs/heads/main') == 'audit'
    with pytest.raises(ValueError, match='main'):
        route.choose_mode('schedule', None, 'refs/heads/retired')


def git(repository, *args):
    return subprocess.run(['git', '-C', str(repository), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def test_renaming_runtime_code_to_documentation_cannot_hide_deleted_code(tmp_path):
    git(tmp_path, 'init')
    git(tmp_path, 'config', 'user.name', 'Synthetic CI fixture')
    git(tmp_path, 'config', 'user.email', 'ci@example.invalid')
    source = tmp_path / 'worker.py'
    source.write_text('SYNTHETIC = True\n')
    git(tmp_path, 'add', '--', 'worker.py')
    git(tmp_path, 'commit', '-m', 'Synthetic base')
    base = git(tmp_path, 'rev-parse', 'HEAD')
    (tmp_path / 'docs').mkdir()
    source.rename(tmp_path / 'docs' / 'notes.md')
    git(tmp_path, 'add', '--all')
    git(tmp_path, 'commit', '-m', 'Synthetic rename')
    head = git(tmp_path, 'rev-parse', 'HEAD')
    route = ci_module('ci_route')
    paths = route.changed_paths(tmp_path, base, head)
    assert set(paths) == {'worker.py', 'docs/notes.md'}
    assert route.choose_mode('push', paths, 'refs/heads/main') == 'full'
    assert route.changed_paths(tmp_path, '0' * 40, head) is None
    assert route.changed_paths(tmp_path, 'f' * 40, head) is None


def needs_for(mode, event='pull_request', windows_mode='two-shards', cache_mode='restore'):
    needs = {name: {'result': 'skipped'} for name in
             ('route', 'portable', 'windows', 'package', 'dependency-audit', 'attest')}
    entries = [('serial', '')] if windows_mode == 'serial' else [('shard-0', '0/2'), ('shard-1', '1/2')]
    needs['route'] = {'result': 'success', 'outputs': {
        'mode': mode, 'windows_mode': windows_mode, 'cache_mode': cache_mode,
        'python_matrix': json.dumps({'include': [{'profile': 'production', 'python': '3.14.8'}]}),
        'windows_matrix': json.dumps({'include': [
            {'profile': 'production', 'python': '3.14.8', 'mode': label, 'shard': shard}
            for label, shard in entries
        ]}),
    }}
    if mode == 'full':
        for name in ('portable', 'windows', 'package', 'dependency-audit'):
            needs[name]['result'] = 'success'
        if event == 'push':
            needs['attest']['result'] = 'success'
    elif mode == 'audit':
        needs['dependency-audit']['result'] = 'success'
    return needs


@pytest.mark.parametrize('mode,event,ref', [
    ('docs', 'pull_request', 'refs/pull/1/merge'),
    ('full', 'pull_request', 'refs/pull/1/merge'),
    ('full', 'push', 'refs/heads/main'),
    ('full', 'workflow_dispatch', 'refs/heads/main'),
    ('audit', 'schedule', 'refs/heads/main'),
])
def test_aggregate_accepts_only_the_workloads_required_by_the_actual_event(mode, event, ref):
    ci_module('ci_route').validate_needs(needs_for(mode, event), event, ref)


@pytest.mark.parametrize('result', ['failure', 'cancelled', 'skipped', ''])
def test_full_run_never_accepts_unsuccessful_or_missing_workloads(result):
    route = ci_module('ci_route')
    for name in ('route', 'portable', 'windows', 'package', 'dependency-audit'):
        needs = needs_for('full')
        needs[name]['result'] = result
        with pytest.raises(ValueError):
            route.validate_needs(needs, 'pull_request', 'refs/pull/1/merge')
    needs = needs_for('full')
    del needs['windows']
    with pytest.raises(ValueError):
        route.validate_needs(needs, 'pull_request', 'refs/pull/1/merge')


def test_aggregate_rejects_forged_routing_and_unattested_main_artifacts():
    route = ci_module('ci_route')
    for mode, event in [('docs', 'workflow_dispatch'), ('audit', 'pull_request'), ('unknown', 'push')]:
        with pytest.raises(ValueError):
            route.validate_needs(needs_for(mode), event, 'refs/heads/main')
    needs = needs_for('full', 'push')
    needs['attest']['result'] = 'skipped'
    with pytest.raises(ValueError, match='attest'):
        route.validate_needs(needs, 'push', 'refs/heads/main')
    for event, mode, ref in [('pull_request', 'full', 'refs/pull/1/merge'),
                             ('push', 'full', 'refs/heads/main'),
                             ('schedule', 'audit', 'refs/heads/main')]:
        for windows_mode, cache_mode in [('serial', 'restore'), ('two-shards', 'cold')]:
            forged = needs_for(mode, event, windows_mode, cache_mode)
            with pytest.raises(ValueError, match='dispatch'):
                route.validate_needs(forged, event, ref)


def test_dispatch_aggregate_requires_the_complete_declared_shard_plan():
    route = ci_module('ci_route')
    route.validate_needs(needs_for('full', 'workflow_dispatch', 'serial'),
                         'workflow_dispatch', 'refs/heads/synthetic-pilot')
    needs = needs_for('full', 'workflow_dispatch', 'two-shards', 'cold')
    route.validate_needs(needs, 'workflow_dispatch', 'refs/heads/synthetic-pilot')
    for replacement in [
        {'include': [{'profile': 'production', 'python': '3.14.8', 'mode': 'shard-0', 'shard': '0/2'}]},
        {'include': [
            {'profile': 'production', 'python': '3.14.8', 'mode': 'shard-0', 'shard': '0/2'},
            {'profile': 'production', 'python': '3.14.8', 'mode': 'shard-1', 'shard': '0/2'},
        ]},
        {'include': [{'profile': 'production', 'python': '3.14.8', 'mode': 'serial', 'shard': ''}]},
    ]:
        damaged = copy.deepcopy(needs)
        damaged['route']['outputs']['windows_matrix'] = json.dumps(replacement)
        with pytest.raises(ValueError):
            route.validate_needs(damaged, 'workflow_dispatch', 'refs/heads/synthetic-pilot')
    for key in ('windows_mode', 'cache_mode', 'windows_matrix', 'python_matrix'):
        damaged = copy.deepcopy(needs)
        del damaged['route']['outputs'][key]
        with pytest.raises(ValueError):
            route.validate_needs(damaged, 'workflow_dispatch', 'refs/heads/synthetic-pilot')
    for result in ('failure', 'cancelled', 'skipped'):
        damaged = copy.deepcopy(needs)
        damaged['windows']['result'] = result
        with pytest.raises(ValueError):
            route.validate_needs(damaged, 'workflow_dispatch', 'refs/heads/synthetic-pilot')
    with pytest.raises(ValueError, match='dispatch'):
        route.validate_needs(needs, 'pull_request', 'refs/pull/1/merge')


def test_unknown_tests_are_routed_to_windows_and_never_dropped():
    routing = ci_module('ci_tests')
    nodes = ['tests/test_exporter.py::test_literal',
             'tests/test_browser.py::test_local_html',
             'tests/test_desktop_gui.py::test_simple_window_controls_and_partial_progress_are_real_tkinter',
             'tests/test_desktop_gui.py::test_stale_malformed_and_false_success_events_are_rejected',
             'tests/test_new_platform_boundary.py::test_new_behavior']
    assert [routing.workload_for(node) for node in nodes] == [
        'portable', 'windows', 'windows', 'portable', 'windows']


def test_windows_executes_every_test_including_the_portable_subset(tmp_path):
    fixture = tmp_path / 'tests'
    fixture.mkdir()
    for name in ('test_exporter.py', 'test_new_platform_boundary.py'):
        (fixture / name).write_text('def test_synthetic():\n    assert 3 + 4 == 7\n')
    plugin = ROOT / 'scripts' / 'ci_tests.py'
    assert plugin.is_file(), 'The workload collector is missing'
    # Load the actual CI plugin while keeping the fixture inventory separate.
    (tmp_path / 'conftest.py').write_text(plugin.read_text())
    inventories = []
    for workload in ('portable', 'windows'):
        manifest = tmp_path / (workload + '.json')
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 'tests', '-q', '--ci-workload', workload,
            '--ci-manifest', str(manifest), '--basetemp', str(tmp_path / ('temp-' + workload)),
        ], cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        assert ('1 passed' if workload == 'portable' else '2 passed') in result.stdout
        inventories.append(json.loads(manifest.read_text()))
    assert set(inventories[0]['all']) == set(inventories[1]['all'])
    first, second = (set(entry['selected']) for entry in inventories)
    assert first < second
    assert second == set(inventories[0]['all'])


def test_inventory_check_rejects_incomplete_windows_tests_and_mixed_commit_evidence():
    module = ci_module('ci_tests')
    assert hasattr(module, 'check_inventories'), 'Cross-runner collection validation is missing'
    all_nodes = ['tests/test_exporter.py::test_synthetic', 'tests/test_new.py::test_synthetic']
    portable = {'all': all_nodes, 'selected': all_nodes[:1], 'workload': 'portable',
                'python': '3.14.8', 'commit': 'a' * 40, 'platform': 'linux',
                'run_id': '123', 'run_attempt': '1', 'exitstatus': 0}
    windows = dict(portable, selected=all_nodes, workload='windows', platform='win32')
    assert module.check_inventories(portable, windows, '3.14.8', 'a' * 40,
                                    run_id='123', run_attempt='1') == 2
    for key, value in [('selected', []), ('selected', all_nodes[1:]), ('all', all_nodes[1:]),
                       ('commit', 'b' * 40), ('python', '3.11.17'), ('platform', 'linux'),
                       ('run_id', '124'), ('run_attempt', '2'), ('exitstatus', 1)]:
        damaged = copy.deepcopy(windows)
        damaged[key] = value
        with pytest.raises(ValueError):
            module.check_inventories(portable, damaged, '3.14.8', 'a' * 40,
                                     run_id='123', run_attempt='1')


def test_documentation_push_cannot_cancel_or_replace_an_unfinished_main_code_build():
    from support_workflows import load_workflow, _expression

    workflow = load_workflow(ROOT / '.github/workflows/windows-build.yml')
    concurrency = workflow['concurrency']
    # A main push needs its own run identity, including when another main push
    # is still pending. Turning cancellation off alone preserves only one slot.
    assert _expression(concurrency['group']) == _expression(
        "windows-build-${{ github.event_name }}-${{ github.event_name == 'pull_request' "
        "&& github.event.pull_request.number || github.run_id }}")
    assert _expression(concurrency['cancel-in-progress']) == "github.event_name=='pull_request'"


def test_every_uv_bootstrap_checks_the_reviewed_platform_archive_bytes():
    from support_workflows import load_workflow

    # Official uv 0.13.4 release asset digests, recorded independently of the
    # setup action's remotely resolved release manifest.
    reviewed = {
        'ubuntu-24.04': '2b428396f12572d4429cf210ca234dd599a33b3af0958a4d5ed569d63e3f344f',
        'windows-2022': 'ccec7508a07d9933d7cb1261880633efcf1f30d6e6eddab21823f1dae6f23225',
    }
    checked = 0
    for path in sorted((ROOT / '.github/workflows').glob('*.yml')):
        for job in load_workflow(path)['jobs'].values():
            for step in job.get('steps', []):
                if step.get('uses', '').startswith('astral-sh/setup-uv@'):
                    assert step['with']['version'] == '0.13.4'
                    assert step['with'].get('checksum') == reviewed[job['runs-on']], (
                        'Bootstrap uv must fail if its reviewed archive bytes change')
                    checked += 1
    assert checked >= 5
