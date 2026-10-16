"""Workflow structure is executable policy, not a search for text in comments."""
from copy import deepcopy
import importlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def contract():
    assert importlib.util.find_spec('support_workflows') is not None, 'Structured workflow contracts are missing'
    return importlib.import_module('support_workflows')


def production():
    return contract().load_workflow(ROOT / '.github/workflows/windows-build.yml')


def benchmark():
    return contract().load_workflow(ROOT / '.github/workflows/windows-shard-benchmark.yml')


def test_current_production_workflow_preserves_real_gate_and_artifact_order():
    contract().validate_production(production())


def test_current_benchmark_is_isolated_and_keeps_the_complete_windows_contract():
    contract().validate_benchmark(benchmark())


def test_diagnostics_survive_attempted_test_failure_in_every_test_job():
    contract().validate_measurements(production(), ('portable', 'windows'))
    contract().validate_measurements(benchmark(), ('benchmark',))


@pytest.mark.parametrize('mutation', [
    'missing-test-dependency', 'wrong-job-dependency', 'upload-before-build',
    'comment-only-build', 'missing-readback', 'wrong-artifact-id', 'unverified-upload',
    'extra-payload-file', 'skipped-aggregate', 'wrong-needs-input',
    'privileged-tests', 'ignored-test-failure', 'production-sharding',
    'untrusted-attestation', 'disabled-fresh-worker', 'unreachable-gate',
    'masked-gate-exit', 'changed-literal-mode',
])
def test_production_contract_rejects_broken_pipeline(mutation):
    document = deepcopy(production())
    jobs = document['jobs']
    package = jobs['package']['steps']
    upload = next(s for s in package if s.get('id') == 'upload')
    build = next(s for s in package if 'build_desktop.py' in s.get('run', ''))
    readback = next(s for s in package if 'artifact-ids' in s.get('with', {}))
    tests = next(s for s in jobs['windows']['steps'] if s.get('id') == 'tests')
    if mutation == 'missing-test-dependency':
        jobs['package']['needs'].remove('windows')
    elif mutation == 'wrong-job-dependency':
        jobs['portable']['needs'] = jobs['package']['needs']
        jobs['package']['needs'] = ['route']
    elif mutation == 'upload-before-build':
        package.remove(upload)
        package.insert(0, upload)
    elif mutation == 'comment-only-build':
        build['run'] = '# ' + build['run']
    elif mutation == 'missing-readback':
        package.remove(readback)
    elif mutation == 'wrong-artifact-id':
        readback['with']['artifact-ids'] = '123456'
    elif mutation == 'unverified-upload':
        next(s for s in package if 'write-checksums' in s.get('run', ''))['continue-on-error'] = True
    elif mutation == 'extra-payload-file':
        upload['with']['path'] += '\nprivate-profile/**'
    elif mutation == 'skipped-aggregate':
        jobs['validate']['if'] = 'success()'
    elif mutation == 'wrong-needs-input':
        jobs['validate']['steps'][-1]['env']['CI_NEEDS'] = '{}'
    elif mutation == 'privileged-tests':
        jobs['windows']['permissions'] = {'contents': 'write'}
    elif mutation == 'ignored-test-failure':
        tests['continue-on-error'] = True
    elif mutation == 'production-sharding':
        tests['run'] += ' --ci-benchmark --ci-shard 0/2'
    elif mutation == 'untrusted-attestation':
        jobs['attest']['if'] = "needs.route.outputs.mode == 'full'"
    elif mutation == 'disabled-fresh-worker':
        next(s for s in jobs['windows']['steps'] if 'scripts.ci_runtime' in s.get('run', ''))['if'] = False
    elif mutation == 'unreachable-gate':
        gate = jobs['validate']['steps'][-1]
        gate['run'] = 'if false; then\n' + gate['run'] + '\nfi'
    elif mutation == 'masked-gate-exit':
        jobs['validate']['steps'][-1]['run'] += '\nexit 0'
    else:
        jobs['package']['if'] = "needs.route.outputs.mode == 'f ull'"
    with pytest.raises(AssertionError):
        contract().validate_production(document)


@pytest.mark.parametrize('job', ['portable', 'windows', 'benchmark'])
def test_each_diagnostic_upload_needs_its_own_failure_guard(job):
    document = deepcopy(benchmark() if job == 'benchmark' else production())
    uploads = [s for s in document['jobs'][job]['steps'] if s.get('uses', '').startswith('actions/upload-artifact@')]
    assert len(uploads) == 2
    for index in range(len(uploads)):
        broken = deepcopy(document)
        selected = [s for s in broken['jobs'][job]['steps'] if s.get('uses', '').startswith('actions/upload-artifact@')]
        selected[index].pop('if')
        with pytest.raises(AssertionError):
            contract().validate_measurements(broken, (job,))


@pytest.mark.parametrize('mutation', [
    'automatic-push', 'missing-shard', 'different-python', 'ignored-comparison',
    'comment-only-arguments', 'removed-shard-branch',
])
def test_benchmark_contract_rejects_unscoped_or_incomplete_execution(mutation):
    document = deepcopy(benchmark())
    if mutation == 'automatic-push':
        document['on']['push'] = {'branches': ['main']}
    elif mutation == 'missing-shard':
        document['jobs']['benchmark']['strategy']['matrix']['mode'].remove('shard-1')
    elif mutation == 'different-python':
        document['jobs']['benchmark']['env']['PYTHON_VERSION'] = '3.11.0'
    elif mutation == 'ignored-comparison':
        document['jobs']['compare']['steps'][0]['continue-on-error'] = True
    elif mutation == 'comment-only-arguments':
        step = next(s for s in document['jobs']['benchmark']['steps'] if s.get('id') == 'tests')
        original = step['run']
        step['run'] = "$pytestArgs = @('--version')\n& .venv/Scripts/python.exe @pytestArgs\n" + \
                      '\n'.join('# ' + line for line in original.splitlines())
    else:
        step = next(s for s in document['jobs']['benchmark']['steps'] if s.get('id') == 'tests')
        step['run'] = step['run'].replace("$pytestArgs += @('--ci-shard', \"$shardIndex/2\")",
                                          "# $pytestArgs += @('--ci-shard', \"$shardIndex/2\")")
    with pytest.raises(AssertionError):
        contract().validate_benchmark(document)


def test_equivalent_yaml_layout_does_not_break_workflow_contract(tmp_path):
    import yaml
    value = production()
    value['jobs']['package']['needs'].reverse()
    value['jobs']['validate']['needs'].reverse()
    value['jobs']['validate']['if'] = '${{ always() }}'
    value['on'] = {key: value['on'][key] for key in reversed(value['on'])}
    path = tmp_path / 'equivalent.yml'
    path.write_text('# Ignored explanatory text: --ci-shard upload-artifact\n' +
                    yaml.safe_dump(value, sort_keys=False, default_flow_style=False), encoding='utf-8')
    contract().validate_production(contract().load_workflow(path))


def test_workflow_loader_keeps_on_as_a_key_and_real_boolean_values(tmp_path):
    path = tmp_path / 'workflow.yml'
    path.write_text('on:\n  workflow_dispatch:\npermissions:\n  contents: read\njobs: {}\nvalue: false\n', encoding='utf-8')
    document = contract().load_workflow(path)
    assert 'on' in document and True not in document
    assert document['value'] is False


def test_workflow_loader_rejects_duplicate_keys(tmp_path):
    path = tmp_path / 'duplicate.yml'
    path.write_text('jobs:\n  package: {}\n  package: {needs: []}\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate'):
        contract().load_workflow(path)


@pytest.mark.parametrize('job', ['portable', 'windows'])
def test_echoed_diagnostic_arguments_do_not_replace_pytest_arguments(job):
    document = deepcopy(production())
    step = next(s for s in document['jobs'][job]['steps'] if s.get('id') == 'tests')
    step['run'] = 'echo "--junitxml junit_logging=no junit_log_passing_tests=false"'
    with pytest.raises(AssertionError):
        contract().validate_measurements(document, (job,))


def test_duplicate_workflow_keys_cannot_hide_behind_merge_overrides(tmp_path):
    path = tmp_path / 'merge.yml'
    path.write_text('base: &base {needs: [route]}\njobs:\n  package:\n    <<: *base\n    needs: []\n', encoding='utf-8')
    with pytest.raises(ValueError, match='Duplicate'):
        contract().load_workflow(path)
