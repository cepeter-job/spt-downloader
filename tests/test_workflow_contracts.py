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
    'privileged-tests', 'ignored-test-failure', 'unbound-shard-arguments',
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
    elif mutation == 'unbound-shard-arguments':
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


@pytest.mark.parametrize('mutation', [
    'missing-lint', 'comment-only-lint', 'masked-lint-exit', 'ignored-lint-failure',
    'skipped-lint', 'narrowed-lint', 'lint-after-tests', 'missing-coverage-wrapper',
    'different-coverage-config', 'extra-coverage-selection', 'masked-portable-exit',
    'ignored-portable-failure',
])
def test_portable_quality_cannot_bypass_lint_or_change_test_execution(mutation):
    document = deepcopy(production())
    steps = document['jobs']['portable']['steps']
    lint = next(s for s in steps if s.get('id') == 'lint')
    tests = next(s for s in steps if s.get('id') == 'tests')
    if mutation == 'missing-lint':
        steps.remove(lint)
    elif mutation == 'comment-only-lint':
        lint['run'] = '# ' + lint['run']
    elif mutation == 'masked-lint-exit':
        lint['run'] += ' || true'
    elif mutation == 'ignored-lint-failure':
        lint['continue-on-error'] = True
    elif mutation == 'skipped-lint':
        lint['if'] = 'false'
    elif mutation == 'narrowed-lint':
        lint['run'] = lint['run'].rstrip().removesuffix('.') + 'scripts/'
    elif mutation == 'lint-after-tests':
        steps.remove(lint)
        steps.insert(steps.index(tests) + 1, lint)
    elif mutation == 'missing-coverage-wrapper':
        tests['run'] = tests['run'].replace('-m coverage run --rcfile=.coveragerc ', '')
    elif mutation == 'different-coverage-config':
        tests['run'] = tests['run'].replace('--rcfile=.coveragerc', '--rcfile=/dev/null')
    elif mutation == 'extra-coverage-selection':
        tests['run'] = tests['run'].replace('--rcfile=.coveragerc', '--rcfile=.coveragerc --include=scripts/*')
    elif mutation == 'masked-portable-exit':
        tests['run'] += ' || true'
    else:
        tests['continue-on-error'] = True
    with pytest.raises(AssertionError):
        contract().validate_production(document)


@pytest.mark.parametrize('format_name', ['xml', 'json'])
@pytest.mark.parametrize('mutation', [
    'missing-report', 'missing-failure-guard', 'ignored-report-failure',
    'masked-report-exit', 'wrong-output-directory', 'upload-before-report',
])
def test_portable_coverage_reports_must_survive_failure_and_precede_upload(format_name, mutation):
    document = deepcopy(production())
    steps = document['jobs']['portable']['steps']
    report = next(s for s in steps if s.get('id') == 'coverage-' + format_name)
    upload = next(s for s in steps if 'test-results-portable-' in s.get('with', {}).get('name', ''))
    if mutation == 'missing-report':
        steps.remove(report)
    elif mutation == 'missing-failure-guard':
        report.pop('if')
    elif mutation == 'ignored-report-failure':
        report['continue-on-error'] = True
    elif mutation == 'masked-report-exit':
        report['run'] += ' || true'
    elif mutation == 'wrong-output-directory':
        report['run'] = report['run'].replace('$RUNNER_TEMP/', './')
    else:
        steps.remove(report)
        steps.insert(steps.index(upload) + 1, report)
    with pytest.raises(AssertionError):
        contract().validate_measurements(document, ('portable',))


@pytest.mark.parametrize('mutation', ['missing-xml', 'missing-json', 'wildcard', 'wrong-directory'])
def test_portable_coverage_artifact_keeps_only_the_declared_report_paths(mutation):
    document = deepcopy(production())
    upload = next(s for s in document['jobs']['portable']['steps']
                  if 'test-results-portable-' in s.get('with', {}).get('name', ''))
    lines = upload['with']['path'].splitlines()
    if mutation in {'missing-xml', 'missing-json'}:
        suffix = mutation.removeprefix('missing-')
        lines = [line for line in lines if not line.endswith('coverage-portable.' + suffix)]
    elif mutation == 'wildcard':
        lines.append('${{ runner.temp }}/**')
    else:
        lines = [line.replace('${{ runner.temp }}/coverage-', 'private-output/coverage-') for line in lines]
    upload['with']['path'] = '\n'.join(lines)
    with pytest.raises(AssertionError):
        contract().validate_measurements(document, ('portable',))


@pytest.mark.parametrize('mutation', [
    'serial-default', 'repository-variable-mode', 'shared-dispatch-concurrency',
    'disabled-pr-supersession', 'unbound-windows-matrix', 'missing-shard-download',
    'colliding-shard-directories', 'wrong-shard-download-condition',
    'single-shard-verification', 'unbound-inventory-run', 'unbound-inventory-attempt',
    'masked-inventory-exit', 'unbound-shard-selection', 'missing-shard-selection',
    'masked-pytest-exit', 'duplicated-worker-bootstrap', 'missing-shard-worker-bootstrap',
    'cold-build-restores-cache', 'both-shards-save-cache', 'colliding-shard-artifacts',
    'missing-attempt-suffix', 'overwrite-old-attempt', 'wrong-attestation-artifact',
    'fail-fast-shards',
])
def test_dispatch_pilot_contract_rejects_incomplete_or_unbound_pipeline(mutation):
    document = deepcopy(production())
    jobs = document['jobs']
    windows, package = jobs['windows'], jobs['package']
    tests = next(s for s in windows['steps'] if s.get('id') == 'tests')
    inventory = next(s for s in package['steps'] if s.get('id') == 'inventory')
    shard_one = next(s for s in package['steps'] if
                     'test-inventory-windows-shard-1-' in s.get('with', {}).get('name', ''))
    fresh = next(s for s in windows['steps'] if 'scripts.ci_runtime' in s.get('run', ''))
    windows_uv = next(s for s in windows['steps'] if s.get('uses', '').startswith('astral-sh/setup-uv@'))
    upload = next(s for s in windows['steps'] if s.get('uses', '').startswith('actions/upload-artifact@'))
    if mutation == 'serial-default':
        document['on']['workflow_dispatch']['inputs']['windows_mode']['default'] = 'serial'
    elif mutation == 'repository-variable-mode':
        step = next(s for s in jobs['route']['steps'] if s.get('id') == 'route')
        step['env']['WINDOWS_MODE_INPUT'] = '${{ vars.WINDOWS_MODE }}'
    elif mutation == 'shared-dispatch-concurrency':
        document['concurrency']['group'] = 'windows-build-${{ github.event_name }}-${{ github.event.pull_request.number || github.ref }}'
    elif mutation == 'disabled-pr-supersession':
        document['concurrency']['cancel-in-progress'] = False
    elif mutation == 'unbound-windows-matrix':
        windows['strategy']['matrix'] = '${{ fromJSON(needs.route.outputs.python_matrix) }}'
    elif mutation == 'missing-shard-download':
        package['steps'].remove(shard_one)
    elif mutation == 'colliding-shard-directories':
        shard_one['with']['path'] = '${{ runner.temp }}/inventory-windows-shard-0'
    elif mutation == 'wrong-shard-download-condition':
        shard_one['if'] = "needs.route.outputs.windows_mode == 'serial'"
    elif mutation == 'single-shard-verification':
        inventory['run'] = inventory['run'].replace(
            '"$env:RUNNER_TEMP/inventory-windows-shard-1/test-inventory.json"', '')
    elif mutation == 'unbound-inventory-run':
        inventory['run'] = inventory['run'].replace('$env:GITHUB_RUN_ID', '123')
    elif mutation == 'unbound-inventory-attempt':
        inventory['run'] = inventory['run'].replace('$env:GITHUB_RUN_ATTEMPT', '1')
    elif mutation == 'masked-inventory-exit':
        inventory['run'] = inventory['run'].replace('exit $LASTEXITCODE', 'exit 0')
    elif mutation == 'unbound-shard-selection':
        tests['env']['CI_SHARD'] = '0/2'
    elif mutation == 'missing-shard-selection':
        tests['run'] = tests['run'].replace("$pytestArgs += @('--ci-shard', \"$env:CI_SHARD\")",
                                             "# $pytestArgs += @('--ci-shard', \"$env:CI_SHARD\")")
    elif mutation == 'masked-pytest-exit':
        tests['run'] = tests['run'].replace('exit $LASTEXITCODE', 'exit 0')
    elif mutation == 'duplicated-worker-bootstrap':
        fresh.pop('if')
    elif mutation == 'missing-shard-worker-bootstrap':
        fresh['if'] = "matrix.mode == 'serial'"
    elif mutation == 'cold-build-restores-cache':
        step = next(s for s in package['steps'] if s.get('uses', '').startswith('astral-sh/setup-uv@'))
        step['with']['restore-cache'] = True
    elif mutation == 'both-shards-save-cache':
        windows_uv['with']['save-cache'] = "${{ github.event_name == 'push' && github.ref == 'refs/heads/main' }}"
    elif mutation == 'colliding-shard-artifacts':
        upload['with']['name'] = upload['with']['name'].replace('-${{ matrix.mode }}', '')
    elif mutation == 'missing-attempt-suffix':
        upload['with']['name'] = upload['with']['name'].replace('-attempt${{ github.run_attempt }}', '')
    elif mutation == 'overwrite-old-attempt':
        upload['with']['overwrite'] = True
    elif mutation == 'wrong-attestation-artifact':
        step = next(s for s in jobs['attest']['steps'] if s.get('uses', '').startswith('actions/download-artifact@'))
        step['with']['name'] = 'unrelated-${{ github.sha }}-attempt${{ github.run_attempt }}'
    else:
        windows['strategy']['fail-fast'] = True
    with pytest.raises(AssertionError):
        contract().validate_production(document)


@pytest.mark.parametrize('job', ['portable', 'windows', 'benchmark'])
def test_each_diagnostic_upload_needs_its_own_failure_guard(job):
    document = deepcopy(benchmark() if job == 'benchmark' else production())
    uploads = [s for s in document['jobs'][job]['steps'] if s.get('uses', '').startswith('actions/upload-artifact@')]
    assert len(uploads) == (3 if job == 'portable' else 2)
    for index in range(len(uploads)):
        broken = deepcopy(document)
        selected = [s for s in broken['jobs'][job]['steps'] if s.get('uses', '').startswith('actions/upload-artifact@')]
        selected[index].pop('if')
        with pytest.raises(AssertionError):
            contract().validate_measurements(broken, (job,))


@pytest.mark.parametrize('job', ['portable', 'windows', 'benchmark'])
@pytest.mark.parametrize('option', ['--collect-only', '--ignore=tests/test_unified_login_flow.py'])
def test_matching_manifests_cannot_hide_unexecuted_or_common_filtered_tests(job, option):
    document = deepcopy(benchmark() if job == 'benchmark' else production())
    step = next(s for s in document['jobs'][job]['steps'] if s.get('id') == 'tests')
    if job == 'portable':
        step['run'] += ' ' + option
    else:
        step['run'] = step['run'].replace("'-q'", "'-q', '" + option + "'", 1)
    with pytest.raises(AssertionError):
        contract().validate_measurements(document, (job,))
    with pytest.raises(AssertionError):
        (contract().validate_benchmark if job == 'benchmark' else contract().validate_production)(document)


@pytest.mark.parametrize('mutation', [
    'automatic-push', 'automatic-pull-request', 'automatic-schedule',
    'missing-shard', 'different-python', 'ignored-comparison',
    'comment-only-arguments', 'removed-shard-branch', 'unbound-shard-mode',
])
def test_benchmark_contract_rejects_unscoped_or_incomplete_execution(mutation):
    document = deepcopy(benchmark())
    if mutation == 'automatic-push':
        document['on']['push'] = {'branches': ['main']}
    elif mutation == 'automatic-pull-request':
        document['on']['pull_request'] = {'branches': ['main']}
    elif mutation == 'automatic-schedule':
        document['on']['schedule'] = [{'cron': '0 0 * * 1'}]
    elif mutation == 'missing-shard':
        document['jobs']['benchmark']['strategy']['matrix']['mode'].remove('shard-1')
    elif mutation == 'different-python':
        document['jobs']['benchmark']['env']['PYTHON_VERSION'] = '3.11.0'
    elif mutation == 'ignored-comparison':
        document['jobs']['compare']['steps'][0]['continue-on-error'] = True
    elif mutation == 'unbound-shard-mode':
        document['jobs']['benchmark']['env']['BENCHMARK_MODE'] = 'serial'
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
