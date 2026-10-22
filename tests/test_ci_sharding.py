"""Prove serial and sharded Windows evidence cannot silently omit tests."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import ci_tests

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.14.8'
COMMIT = 'a' * 40
RUN_ID = '123'
RUN_ATTEMPT = '2'


def evidence():
    nodes = [f'tests/test_alpha.py::test_{i}' for i in range(12)]
    common = dict(all=nodes, workload='windows', platform='win32',
                  python=VERSION, commit=COMMIT, exitstatus=0,
                  run_id=RUN_ID, run_attempt=RUN_ATTEMPT)
    baseline = dict(common, selected=nodes, elapsed_seconds=120.0)
    shards = [dict(common,
                   selected=[node for node in nodes
                             if ci_tests.shard_for(node, 2) == index],
                   shard={'index': index, 'count': 2},
                   elapsed_seconds=75.0 + index)
              for index in (0, 1)]
    for report in (baseline, *shards):
        report['outcomes'] = completed_outcomes(report)
    return baseline, shards


def test_two_shards_partition_every_node():
    nodes = [f'tests/test_file_{i % 8}.py::test_case[{i}]'
             for i in range(100)]
    left = {node for node in nodes if ci_tests.shard_for(node, 2) == 0}
    right = {node for node in nodes if ci_tests.shard_for(node, 2) == 1}
    assert left and right
    assert left.isdisjoint(right)
    assert left | right == set(nodes)


def test_evidence_checks_exact_coverage_and_records_elapsed_time():
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    data = ci_shard_benchmark.verify(
        baseline, shards, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)
    assert data['total_tests'] == 12
    assert data['serial_seconds'] == 120.0
    assert data['parallel_seconds'] == 76.0
    assert data['saved_seconds'] == 44.0
    assert sum(data['shard_counts']) == 12


@pytest.mark.parametrize('target, key, wrong', [
    ('baseline', 'selected', []),
    ('baseline', 'all', []),
    ('baseline', 'commit', 'b' * 40),
    ('baseline', 'elapsed_seconds', float('nan')),
    ('baseline', 'exitstatus', 1),
    ('baseline', 'exitstatus', False),
    ('baseline', 'run_id', 'different-run'),
    ('baseline', 'run_attempt', None),
    ('shard0', 'selected', []),
    ('shard0', 'platform', 'linux'),
    ('shard0', 'elapsed_seconds', 0),
    ('shard1', 'all', ['tests/test_fake.py::test_fake']),
    ('shard1', 'python', '3.11.17'),
    ('shard1', 'shard', {'index': 0, 'count': 2}),
    ('shard1', 'shard', {'index': True, 'count': 2}),
    ('shard1', 'run_id', None),
    ('shard1', 'run_attempt', '1'),
    ('shard1', 'exitstatus', 5),
])
def test_evidence_rejects_missing_or_forged_run(target, key, wrong):
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    report = {'baseline': baseline, 'shard0': shards[0],
              'shard1': shards[1]}[target]
    report[key] = wrong
    with pytest.raises(ValueError):
        ci_shard_benchmark.verify(
            baseline, shards, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


def production_evidence():
    baseline, shards = evidence()
    portable_nodes = [f'tests/test_ci_sharding.py::test_synthetic[{i}]' for i in range(2)]
    nodes = [*baseline['all'], *portable_nodes,
             'tests/test_desktop_gui.py::test_simple_window_controls_and_partial_progress_are_real_tkinter']
    baseline = dict(baseline, all=list(nodes), selected=list(nodes))
    shards = [dict(report, all=list(nodes), selected=[
        node for node in nodes if ci_tests.shard_for(node, 2) == index])
        for index, report in enumerate(shards)]
    portable = dict(baseline, workload='portable', platform='linux',
                    all=list(nodes), selected=portable_nodes)
    for report in (portable, baseline, *shards):
        report['outcomes'] = completed_outcomes(report)
    return portable, baseline, shards


@pytest.mark.parametrize('mode', ['serial', 'serial-list', 'shards'])
def test_production_gate_accepts_full_serial_or_two_exact_shards(mode):
    portable, baseline, shards = production_evidence()
    windows = {'serial': baseline, 'serial-list': [baseline], 'shards': shards}[mode]
    assert ci_tests.check_inventories(
        portable, windows, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT) == 15


@pytest.mark.parametrize('target, key, wrong', [
    ('portable', 'platform', 'win32'),
    ('portable', 'workload', 'windows'),
    ('portable', 'selected', []),
    ('portable', 'shard', {'index': 0, 'count': 2}),
    ('serial', 'selected', []),
    ('serial', 'commit', 'b' * 40),
    ('serial', 'exitstatus', 1),
    ('serial', 'exitstatus', False),
    ('serial', 'exitstatus', 0.0),
    ('serial', 'shard', {'index': 0, 'count': 2}),
    ('shard0', 'run_id', 'different-run'),
    ('shard0', 'run_attempt', '1'),
    ('shard0', 'exitstatus', 1),
    ('shard0', 'shard', {'index': False, 'count': 2}),
    ('shard1', 'platform', 'linux'),
    ('shard1', 'python', '3.11.17'),
    ('shard1', 'shard', {'index': 1, 'count': 2.0}),
])
def test_production_gate_rejects_tampered_evidence(target, key, wrong):
    portable, baseline, shards = production_evidence()
    report = {'portable': portable, 'serial': baseline,
              'shard0': shards[0], 'shard1': shards[1]}[target]
    report[key] = wrong
    with pytest.raises(ValueError):
        ci_tests.check_inventories(
            portable, baseline if target == 'serial' else shards, VERSION, COMMIT,
            run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


@pytest.mark.parametrize('target', ['portable', 'serial', 'shard0', 'shard1'])
@pytest.mark.parametrize('missing', ['exitstatus', 'run_id', 'run_attempt'])
def test_production_gate_requires_completed_run_identity(target, missing):
    portable, baseline, shards = production_evidence()
    report = {'portable': portable, 'serial': baseline,
              'shard0': shards[0], 'shard1': shards[1]}[target]
    del report[missing]
    with pytest.raises(ValueError):
        ci_tests.check_inventories(
            portable, baseline if target == 'serial' else shards, VERSION, COMMIT,
            run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


@pytest.mark.parametrize('key, wrong', [('run_id', '999'), ('run_attempt', '1')])
@pytest.mark.parametrize('mode', ['serial', 'shards'])
def test_matching_manifests_still_must_belong_to_the_expected_run(key, wrong, mode):
    portable, baseline, shards = production_evidence()
    for report in (portable, baseline, *shards):
        report[key] = wrong
    with pytest.raises(ValueError):
        ci_tests.check_inventories(
            portable, baseline if mode == 'serial' else shards, VERSION, COMMIT,
            run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


@pytest.mark.parametrize('shape', ['absent', 'missing', 'extra', 'duplicate', 'reversed', 'mixed'])
def test_production_gate_requires_exactly_the_two_ordered_shards(shape):
    portable, baseline, shards = production_evidence()
    windows = {'absent': [], 'missing': shards[:1], 'extra': [*shards, shards[0]],
               'duplicate': [shards[0], shards[0]], 'reversed': shards[::-1],
               'mixed': [baseline, shards[1]]}[shape]
    with pytest.raises(ValueError):
        ci_tests.check_inventories(
            portable, windows, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


@pytest.mark.parametrize('tamper', ['missing', 'duplicate', 'overlap', 'wrong-partition',
                                  'collector-mismatch', 'both-collectors-mismatch'])
def test_production_gate_rejects_incomplete_or_incorrect_shard_partitions(tamper):
    portable, _, shards = production_evidence()
    if tamper == 'missing':
        shards[0]['selected'].pop()
    elif tamper == 'duplicate':
        shards[0]['selected'].append(shards[0]['selected'][0])
    elif tamper == 'overlap':
        shards[0]['selected'].append(shards[1]['selected'][0])
    elif tamper == 'wrong-partition':
        shards[0]['selected'][0], shards[1]['selected'][0] = (
            shards[1]['selected'][0], shards[0]['selected'][0])
        assert set(shards[0]['selected']) | set(shards[1]['selected']) == set(portable['all'])
        assert set(shards[0]['selected']).isdisjoint(shards[1]['selected'])
    elif tamper == 'collector-mismatch':
        shards[1]['all'].append('tests/test_extra.py::test_extra')
    else:
        removed = shards[0]['selected'][0]
        shards[0]['selected'].remove(removed)
        for report in shards:
            report['all'].remove(removed)
    with pytest.raises(ValueError):
        ci_tests.check_inventories(
            portable, shards, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


@pytest.mark.parametrize('key, invalid', [
    ('all', []), ('all', 'not-a-list'), ('all', [None]), ('all', ['']),
    ('all', [' ']), ('all', ['duplicate', 'duplicate']),
    ('selected', ['duplicate', 'duplicate']), ('selected', [1]),
])
def test_production_gate_rejects_malformed_node_inventories(key, invalid):
    portable, baseline, _ = production_evidence()
    baseline[key] = invalid
    with pytest.raises(ValueError):
        ci_tests.check_inventories(
            portable, baseline, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


@pytest.mark.parametrize('mode', ['serial', 'shards'])
def test_production_inventory_cli_reads_the_original_manifests(tmp_path, capsys, mode):
    portable, baseline, shards = production_evidence()
    reports = [portable, baseline] if mode == 'serial' else [portable, *shards]
    paths = [tmp_path / f'report-{index}.json' for index in range(len(reports))]
    for path, report in zip(paths, reports):
        path.write_text(json.dumps(report), encoding='utf-8')
    ci_tests.main([
        *map(str, paths), '--python-version', VERSION, '--commit', COMMIT,
        '--run-id', RUN_ID, '--run-attempt', RUN_ATTEMPT,
    ])
    assert '15 tests' in capsys.readouterr().out


@pytest.mark.parametrize('benchmark', [False, True], ids=['production', 'benchmark'])
def test_pytest_runs_serial_and_two_complete_shards(tmp_path, benchmark):
    tests = tmp_path / 'tests'
    tests.mkdir()
    (tests / 'test_sample.py').write_text(
        "import pytest\n"
        "@pytest.mark.parametrize('case', range(18))\n"
        "def test_synthetic(case):\n    assert case >= 0\n",
        encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'),
        encoding='utf-8')
    reports = []
    for label, flags in [
        ('serial', []), ('shard-0', ['--ci-shard', '0/2']),
        ('shard-1', ['--ci-shard', '1/2']),
    ]:
        manifest = tmp_path / (label + '.json')
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 'tests', '-q',
            '--ci-workload', 'windows', *(['--ci-benchmark'] if benchmark else []),
            *flags, '--ci-manifest', str(manifest),
            '--basetemp', str(tmp_path / ('temp-' + label)),
        ], cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(manifest.read_text(encoding='utf-8'))
        assert report['exitstatus'] == 0
        assert report['elapsed_seconds'] > 0
        reports.append(report)
    assert len(reports[0]['selected']) == 18
    assert reports[0]['selected'] == reports[0]['all']
    assert 'shard' not in reports[0]
    for index, report in enumerate(reports[1:]):
        assert report['all'] == reports[0]['all']
        assert report['shard'] == {'index': index, 'count': 2}
        assert set(report['selected']) == {
            node for node in report['all'] if ci_tests.shard_for(node, 2) == index}
    assert set(reports[1]['selected']).isdisjoint(reports[2]['selected'])
    assert set(reports[1]['selected']) | set(reports[2]['selected']) == set(reports[0]['all'])


@pytest.mark.parametrize('flags, manifest', [
    (['--ci-shard', '0/2'], True),
    (['--ci-shard', '0/2', '--ci-workload', 'portable'], True),
    (['--ci-shard', '0/2', '--ci-workload', 'windows'], False),
    (['--ci-benchmark', '--ci-workload', 'portable'], True),
    (['--ci-benchmark', '--ci-shard', '2/2'], True),
    (['--ci-benchmark', '--ci-shard', '0/3'], True),
    (['--ci-benchmark', '--ci-shard', 'broken'], True),
    (['--ci-benchmark'], False),
    (['--ci-benchmark', '--ci-workload', 'windows'], False),
])
def test_sharding_rejects_invalid_or_unguarded_requests(tmp_path, flags, manifest):
    (tmp_path / 'test_fixture.py').write_text(
        'def test_synthetic():\n    assert True\n', encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'),
        encoding='utf-8')
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'test_fixture.py', '-q', *flags,
        *(['--ci-manifest', str(tmp_path / 'manifest.json')] if manifest else []),
    ], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0






@pytest.mark.parametrize('body, expected_status', [
    ('def test_ok():\n    assert True\n', 0),
    ('def test_failed():\n    assert False, "synthetic failure"\n', 1),
    ('import pytest\n@pytest.fixture\ndef broken():\n    raise RuntimeError("synthetic fixture")\ndef test_error(broken):\n    pass\n', 1),
    ('def test_invalid(:\n    pass\n', 2),
    ('import pytest\ndef test_skip():\n    pytest.skip("synthetic skip")\n', 0),
], ids=['pass', 'assertion-failure', 'fixture-error', 'collection-error', 'skip'])
def test_production_inventory_retains_timing_and_failure_exit_status(tmp_path, body, expected_status):
    import os
    import time
    import xml.etree.ElementTree as ET

    (tmp_path / 'test_sample.py').write_text(body, encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'), encoding='utf-8')
    manifest, junit = tmp_path / 'inventory.json', tmp_path / 'junit.xml'
    env = dict(os.environ, CI_SETUP_STARTED=str(time.time() - 1),
               GITHUB_RUN_ID='123', GITHUB_RUN_ATTEMPT='2')
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'test_sample.py', '-q',
        '--ci-workload', 'windows', '--ci-manifest', str(manifest),
        '--junitxml', str(junit), '-o', 'junit_logging=no',
        '-o', 'junit_log_passing_tests=false',
        '--basetemp', str(tmp_path / 'scratch'),
    ], cwd=tmp_path, capture_output=True, text=True, env=env, timeout=45)
    assert result.returncode == expected_status, result.stdout + result.stderr
    report = json.loads(manifest.read_text(encoding='utf-8'))
    assert report.get('exitstatus') == expected_status
    assert report['elapsed_seconds'] > 0
    assert report['setup_seconds'] >= 1
    assert report['run_id'] == '123'
    assert report['run_attempt'] == '2'
    assert ET.parse(junit).find('.//testsuite') is not None


def report_module():
    import importlib.util

    path = ROOT / 'scripts/ci_report.py'
    assert path.is_file(), 'The synthetic CI measurement reporter is missing.'
    spec = importlib.util.spec_from_file_location('ci_report', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_report_summarizes_outcomes_without_copying_failure_values_or_logs(tmp_path, monkeypatch):
    report = report_module()
    inventory = dict(workload='windows', python=VERSION, commit=COMMIT,
                     all=['a', 'b', 'c', 'd'], selected=['a', 'b', 'c', 'd'],
                     exitstatus=1, elapsed_seconds=12.5, setup_seconds=3.0,
                     run_id='123', run_attempt='2')
    junit = '''<testsuites><testsuite tests="4" failures="1" errors="1" skipped="1">
      <testcase classname="tests.example" name="test_pass" time="1" />
      <testcase classname="tests.example" name="test_fail" time="4"><failure>DO_NOT_COPY_SYNTHETIC_VALUE</failure><system-out>DO_NOT_COPY_SYNTHETIC_LOG</system-out></testcase>
      <testcase classname="tests.example" name="test_error" time="2"><error>DO_NOT_COPY_SYNTHETIC_VALUE</error></testcase>
      <testcase classname="tests.example" name="test_skip" time="0"><skipped /></testcase>
    </testsuite></testsuites>'''
    data = report.summarize(inventory, junit)
    assert data['results'] == dict(tests=4, passed=1, failures=1, errors=1, skipped=1)
    assert data['pytest_seconds'] == 12.5
    assert data['setup_seconds'] == 3.0
    assert data['slowest'][0]['test'] == 'tests.example::test_fail'
    assert data['slowest'][0]['seconds'] == 4.0
    assert data['run_id'] == '123' and data['run_attempt'] == '2'
    assert 'DO_NOT_COPY' not in json.dumps(data)
    text = report.summary_text(data)
    assert '12.50' in text and '3.00' in text
    assert 'exit status' in text.lower()
    assert 'DO_NOT_COPY' not in text
    (tmp_path / 'test-inventory.json').write_text(json.dumps(inventory), encoding='utf-8')
    (tmp_path / 'test-results.xml').write_text(junit, encoding='utf-8')
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    report.main(['report', '--directory', str(tmp_path)])
    saved = json.loads((tmp_path / 'test-measurements.json').read_text(encoding='utf-8'))
    assert saved == data
    assert summary.read_text(encoding='utf-8') == text


def test_report_marks_missing_execution_evidence_as_unknown_not_success():
    report = report_module()
    data = report.summarize(None, None)
    assert data['exitstatus'] is None
    assert data['results'] is None
    assert data['pytest_seconds'] is None
    assert 'unavailable' in report.summary_text(data).lower()


def test_setup_measurement_is_written_to_the_environment_file(tmp_path, monkeypatch):
    report = report_module()
    target = tmp_path / 'environment'
    monkeypatch.setenv('GITHUB_ENV', str(target))
    report.main(['start'])
    key, value = target.read_text(encoding='utf-8').strip().split('=', 1)
    assert key == 'CI_SETUP_STARTED'
    import time
    assert abs(float(value) - time.time()) < 10


def test_benchmark_records_setup_and_runner_time_without_claiming_total_ci_savings():
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    baseline['setup_seconds'] = 10.0
    shards[0]['setup_seconds'] = 20.0
    shards[1]['setup_seconds'] = 5.0
    data = ci_shard_benchmark.verify(
        baseline, shards, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)
    assert data.get('serial_setup_pytest_seconds') == 130.0
    assert data['parallel_setup_pytest_seconds'] == 95.0
    assert data['shard_pytest_runner_seconds'] == 151.0
    text = ci_shard_benchmark.summary_text(data)
    assert 'setup + pytest' in text.lower()
    assert 'excludes' in text.lower() and 'queue' in text.lower()


@pytest.mark.parametrize('bad_setup', [-1, float('nan'), float('inf'), True])
def test_benchmark_rejects_invalid_setup_measurements(bad_setup):
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    baseline['setup_seconds'] = bad_setup
    for shard in shards:
        shard['setup_seconds'] = 1.0
    with pytest.raises(ValueError):
        ci_shard_benchmark.verify(
            baseline, shards, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)




@pytest.mark.parametrize('invalid', [-1, float('nan'), float('inf'), True, '12'])
def test_report_rejects_invalid_measurement_numbers(invalid):
    with pytest.raises(ValueError):
        report_module().summarize({'elapsed_seconds': invalid}, None)


def test_benchmark_comparison_json_is_tied_to_verified_inputs(tmp_path):
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    paths = [tmp_path / f'report-{index}.json' for index in range(3)]
    for path, report in zip(paths, [baseline, *shards]):
        path.write_text(json.dumps(report), encoding='utf-8')
    output, summary = tmp_path / 'comparison.json', tmp_path / 'summary.md'
    ci_shard_benchmark.main([
        *map(str, paths), '--python-version', VERSION, '--commit', COMMIT,
        '--run-id', RUN_ID, '--run-attempt', RUN_ATTEMPT,
        '--output', str(output), '--summary', str(summary),
    ])
    assert json.loads(output.read_text(encoding='utf-8')) == ci_shard_benchmark.verify(
        baseline, shards, VERSION, COMMIT, run_id=RUN_ID, run_attempt=RUN_ATTEMPT)
    assert 'non-production' in summary.read_text(encoding='utf-8')


def test_runner_bootstrap_python_and_managed_python_share_setup_epoch(tmp_path):
    import os
    import shutil
    import time

    bootstrap = shutil.which('python')
    assert bootstrap, 'The same runner Python used before setup-uv must be available.'
    environment = tmp_path / 'setup.env'
    env = dict(os.environ, GITHUB_ENV=str(environment))
    started = time.time()
    result = subprocess.run([
        bootstrap, str(ROOT / 'scripts/ci_report.py'), 'start',
    ], capture_output=True, text=True, env=env, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    key, marker = environment.read_text(encoding='utf-8').strip().split('=', 1)
    assert key == 'CI_SETUP_STARTED'
    assert started - 1 <= float(marker) <= time.time() + 1
    (tmp_path / 'test_sample.py').write_text('def test_ok():\n    assert True\n', encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'), encoding='utf-8')
    manifest = tmp_path / 'inventory.json'
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'test_sample.py', '-q',
        '--ci-workload', 'windows', '--ci-manifest', str(manifest),
        '--basetemp', str(tmp_path / 'scratch'),
    ], cwd=tmp_path, capture_output=True, text=True,
        env=dict(env, CI_SETUP_STARTED=marker), timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(manifest.read_text(encoding='utf-8'))
    assert 0 <= data['setup_seconds'] < 30
    assert data['exitstatus'] == 0


def completed_outcomes(report):
    return {node: {phase: ['passed'] for phase in ('setup', 'call', 'teardown')}
            for node in report['selected']}


@pytest.mark.parametrize('damage', ['absent', 'skipped', 'xfail', 'missing-call',
                                  'duplicate-call', 'extra-node'])
def test_completed_inventory_rejects_unexecuted_or_unexpected_skipped_nodes(damage):
    portable, baseline, _ = production_evidence()
    for report in (portable, baseline):
        report['outcomes'] = completed_outcomes(report)
    node = baseline['selected'][0]
    if damage == 'absent':
        del baseline['outcomes']
    elif damage == 'skipped':
        baseline['outcomes'][node] = {'setup': ['skipped'], 'teardown': ['passed']}
    elif damage == 'xfail':
        baseline['outcomes'][node]['call'] = ['xfailed']
    elif damage == 'missing-call':
        del baseline['outcomes'][node]['call']
    elif damage == 'duplicate-call':
        baseline['outcomes'][node]['call'] = ['passed', 'passed']
    else:
        baseline['outcomes']['tests/test_unselected.py::test_unknown'] = {
            phase: ['passed'] for phase in ('setup', 'call', 'teardown')}
    with pytest.raises(ValueError, match='outcome|phase|completed|skip'):
        ci_tests.check_inventories(portable, baseline, VERSION, COMMIT,
                                  run_id=RUN_ID, run_attempt=RUN_ATTEMPT)


def test_inventory_records_real_terminal_phases_without_failure_messages(tmp_path):
    (tmp_path / 'test_sample.py').write_text(
        'import pytest\n'
        'def test_pass():\n    assert True\n'
        'def test_skip():\n    pytest.skip("DO_NOT_RECORD_PRIVATE_REASON")\n', encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'), encoding='utf-8')
    manifest = tmp_path / 'inventory.json'
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'test_sample.py', '-q',
        '--ci-workload', 'windows', '--ci-manifest', str(manifest),
        '--basetemp', str(tmp_path / 'scratch'),
    ], cwd=tmp_path, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    data = json.loads(manifest.read_text(encoding='utf-8'))
    assert data.get('outcomes') == {
        'test_sample.py::test_pass': {'setup': ['passed'], 'call': ['passed'], 'teardown': ['passed']},
        'test_sample.py::test_skip': {'setup': ['passed'], 'call': ['skipped'], 'teardown': ['passed']},
    }
    assert 'DO_NOT_RECORD' not in json.dumps(data)
