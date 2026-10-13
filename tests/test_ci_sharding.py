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
