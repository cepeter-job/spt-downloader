"""Prove the optional Windows benchmark cannot silently omit tests."""
import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import ci_tests

ROOT = Path(__file__).resolve().parents[1]
VERSION = '3.14.8'
COMMIT = 'a' * 40


def evidence():
    nodes = [f'tests/test_alpha.py::test_{i}' for i in range(12)]
    common = dict(all=nodes, workload='windows', platform='win32',
                  python=VERSION, commit=COMMIT, exitstatus=0)
    baseline = dict(common, selected=nodes, elapsed_seconds=120.0)
    shards = [dict(common,
                   selected=[node for node in nodes
                             if ci_tests.shard_for(node, 2) == index],
                   shard={'index': index, 'count': 2},
                   elapsed_seconds=75.0 + index)
              for index in (0, 1)]
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
    data = ci_shard_benchmark.verify(baseline, shards, VERSION, COMMIT)
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
    ('shard0', 'selected', []),
    ('shard0', 'platform', 'linux'),
    ('shard0', 'elapsed_seconds', 0),
    ('shard1', 'all', ['tests/test_fake.py::test_fake']),
    ('shard1', 'python', '3.11.17'),
    ('shard1', 'shard', {'index': 0, 'count': 2}),
    ('shard1', 'exitstatus', 5),
])
def test_evidence_rejects_missing_or_forged_run(target, key, wrong):
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    report = {'baseline': baseline, 'shard0': shards[0],
              'shard1': shards[1]}[target]
    report[key] = wrong
    with pytest.raises(ValueError):
        ci_shard_benchmark.verify(baseline, shards, VERSION, COMMIT)


def test_pytest_runs_serial_and_two_complete_shards(tmp_path):
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
            '--ci-workload', 'windows', '--ci-benchmark',
            *flags, '--ci-manifest', str(manifest),
            '--basetemp', str(tmp_path / ('temp-' + label)),
        ], cwd=tmp_path, capture_output=True, text=True)
        assert result.returncode == 0, result.stdout + result.stderr
        report = json.loads(manifest.read_text(encoding='utf-8'))
        assert report['exitstatus'] == 0
        assert report['elapsed_seconds'] > 0
        reports.append(report)
    assert len(reports[0]['selected']) == 18
    assert set(reports[1]['selected']).isdisjoint(reports[2]['selected'])
    assert set(reports[1]['selected']) | set(reports[2]['selected']) == set(reports[0]['all'])


@pytest.mark.parametrize('flags', [
    ['--ci-shard', '0/2'],
    ['--ci-benchmark', '--ci-workload', 'portable'],
    ['--ci-benchmark', '--ci-shard', '2/2'],
    ['--ci-benchmark', '--ci-shard', '0/3'],
    ['--ci-benchmark', '--ci-shard', 'broken'],
    ['--ci-benchmark'],
])
def test_sharding_rejects_invalid_or_unguarded_requests(tmp_path, flags):
    (tmp_path / 'test_fixture.py').write_text(
        'def test_synthetic():\n    assert True\n', encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'),
        encoding='utf-8')
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 'test_fixture.py', '-q', *flags,
        *([] if flags == ['--ci-benchmark'] else [
            '--ci-manifest', str(tmp_path / 'manifest.json')]),
    ], cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode != 0


def test_production_gate_and_artifact_validation_stay_in_place():
    workflow = (ROOT / '.github/workflows/windows-build.yml').read_text(encoding='utf-8')
    assert 'group: windows-build-' + '$' + '{{ github.event_name }}-' + '$' + '{{ github.event.pull_request.number || github.ref }}' in workflow
    assert 'name: Windows tests and dependency audit' in workflow
    assert 'needs: [route, portable, windows, dependency-audit]' in workflow
    assert 'artifact-ids: ' + '$' + '{{ steps.upload.outputs.artifact-id }}' in workflow
    assert 'scripts.ci_artifact verify' in workflow


def test_benchmark_workflow_is_opt_in_except_for_scoped_pr_validation():
    path = ROOT / '.github/workflows/windows-shard-benchmark.yml'
    workflow = path.read_text(encoding='utf-8')
    assert 'workflow_dispatch:' in workflow
    assert 'pull_request:' in workflow
    assert 'paths:' in workflow
    assert 'runs-on: windows-2022' in workflow
    assert 'name: Compare serial and 2-shard Windows tests' in workflow


@pytest.mark.parametrize('body, expected_status', [
    ('def test_ok():\n    assert True\n', 0),
    ('def test_failed():\n    assert False, "synthetic failure"\n', 1),
    ('import pytest\n@pytest.fixture\ndef broken():\n    raise RuntimeError("synthetic fixture")\ndef test_error(broken):\n    pass\n', 1),
    ('def test_invalid(:\n    pass\n', 2),
])
def test_production_inventory_retains_timing_and_failure_exit_status(tmp_path, body, expected_status):
    import os
    import time
    import xml.etree.ElementTree as ET

    (tmp_path / 'test_sample.py').write_text(body, encoding='utf-8')
    (tmp_path / 'conftest.py').write_text(
        (ROOT / 'scripts/ci_tests.py').read_text(encoding='utf-8'), encoding='utf-8')
    manifest, junit = tmp_path / 'inventory.json', tmp_path / 'junit.xml'
    env = dict(os.environ, CI_SETUP_STARTED=str(time.monotonic() - 1),
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


def test_report_summarizes_outcomes_without_copying_failure_values_or_logs():
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
    assert float(value) > 0


def test_benchmark_records_setup_and_runner_time_without_claiming_total_ci_savings():
    from scripts import ci_shard_benchmark

    baseline, shards = evidence()
    baseline['setup_seconds'] = 10.0
    shards[0]['setup_seconds'] = 20.0
    shards[1]['setup_seconds'] = 5.0
    data = ci_shard_benchmark.verify(baseline, shards, VERSION, COMMIT)
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
        ci_shard_benchmark.verify(baseline, shards, VERSION, COMMIT)


def test_measurement_workflows_keep_production_serial_and_publish_failed_diagnostics():
    production = (ROOT / '.github/workflows/windows-build.yml').read_text(encoding='utf-8')
    benchmark = (ROOT / '.github/workflows/windows-shard-benchmark.yml').read_text(encoding='utf-8')
    assert '--ci-shard' not in production and '--ci-benchmark' not in production
    for workflow in (production, benchmark):
        assert '--junitxml' in workflow
        assert 'junit_logging=no' in workflow
        assert 'scripts.ci_report start' in workflow
        assert 'scripts.ci_report report' in workflow
        assert "always() && steps.tests.outcome != 'skipped'" in workflow
    assert "PYTHON_VERSION: '3.14.8'" not in benchmark
    assert 'needs.profile.outputs.production_python' in benchmark
    assert 'spt_desktop/runtime.py' in benchmark
