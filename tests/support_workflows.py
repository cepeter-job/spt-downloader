"""Parsed workflow contracts; actionlint remains the authority for Actions syntax."""
import json
import re
import shlex
from pathlib import Path

import yaml


class _WorkflowLoader(yaml.SafeLoader):
    # Actions uses the key `on`; YAML 1.1's yes/no/on/off booleans must not rename it.
    yaml_implicit_resolvers = {
        initial: [(tag, pattern) for tag, pattern in rules if tag != 'tag:yaml.org,2002:bool']
        for initial, rules in yaml.SafeLoader.yaml_implicit_resolvers.items()
    }

    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        result = {}
        for key_node, value_node in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in result:
                raise ValueError(f'Duplicate workflow key: {key}')
            result[key] = self.construct_object(value_node, deep=deep)
        return result


_WorkflowLoader.add_implicit_resolver(
    'tag:yaml.org,2002:bool', re.compile(r'^(?:true|false|True|False|TRUE|FALSE)$'), list('tTfF'))


def load_workflow(path):
    value = yaml.load(Path(path).read_text(encoding='utf-8'), Loader=_WorkflowLoader)
    assert isinstance(value, dict) and isinstance(value.get('jobs'), dict), 'Workflow must define jobs'
    return value


def _expression(value):
    assert isinstance(value, str), 'Expected an Actions expression'
    value = value.strip()
    if value.startswith('${{') and value.endswith('}}'):
        value = value[3:-2].strip()
    # Whitespace inside a quoted literal is semantically significant.
    return re.sub(r'''('[^']*(?:''[^']*)*'|"[^"]*")|(\s+)''',
                  lambda match: match.group(1) or '', value)


def _needs(job):
    value = job.get('needs', [])
    if isinstance(value, str):
        value = [value]
    assert isinstance(value, list) and len(value) == len(set(value))
    return set(value)


def _logical_lines(step):
    lines, pending = [], ''
    for physical in step.get('run', '').splitlines():
        line = physical.strip()
        if not line or line.startswith('#'):
            continue
        if line.endswith(('\\', '`')):
            pending += line[:-1] + ' '
            continue
        lines.append(pending + line)
        pending = ''
    assert not pending, 'Unfinished shell continuation'
    return lines


def _words(line):
    lexer = shlex.shlex(line, posix=True)
    lexer.whitespace_split = True
    lexer.escape = ''  # Windows separators remain literal; continuations are joined above.
    return list(lexer)


def _commands(step):
    # Only tokenize real Python starts, not arbitrary Bash/PowerShell statements.
    result = []
    for line in _logical_lines(step):
        prefix = line.split()
        if prefix and prefix[0] == '&':
            prefix = prefix[1:]
        if not prefix or not re.search(r'(?:^|/|\\)python(?:\d+(?:\.\d+)*)?(?:\.exe)?$', prefix[0]):
            continue
        words = _words(line)
        if words[0] == '&':
            words = words[1:]
        result.append(words[1:])
    return result


def _single_command(step):
    lines = _logical_lines(step)
    assert len(lines) == 1, 'Critical command must execute directly, without surrounding control flow'
    unquoted = re.sub(r'''('[^']*'|"[^"]*")''', '', lines[0]).lstrip('&').strip()
    assert not any(operator in unquoted for operator in (';', '|', '&')), 'Critical failure cannot be masked'
    commands = _commands(step)
    assert len(commands) == 1, 'Critical step must execute one Python command'
    return commands[0]


def _array_arguments(step, name):
    # Parse only quoted argv elements, not arbitrary PowerShell expressions.
    lines = _logical_lines(step)
    assert lines and _expression(lines[0]) == f'${name}=@('
    end = next((i for i, line in enumerate(lines) if line == ')'), None)
    assert end is not None
    source = ' '.join(lines[1:end])
    arguments, position = [], 0
    for match in re.finditer(r''' '([^']*)'|"([^"]*)" '''.strip(), source):
        assert not source[position:match.start()].strip(' ,\t'), 'Unsupported argument-array expression'
        arguments.append(match.group(1) if match.group(1) is not None else match.group(2))
        position = match.end()
    assert not source[position:].strip(' ,\t')
    return arguments, '\n'.join(lines[end + 1:])


def _benchmark_arguments(step):
    # Invocation, shard selection and native exit propagation stay bound together.
    arguments, tail = _array_arguments(step, 'pytestArgs')
    expected = """if ($env:BENCHMARK_MODE -ne 'serial') {
        $shardIndex = $env:BENCHMARK_MODE.Substring(6)
        $pytestArgs += @('--ci-shard', "$shardIndex/2")
    }
    & .venv/Scripts/python.exe @pytestArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"""
    assert _expression(tail) == _expression(expected), 'Benchmark must execute its guarded shard argv'
    assert arguments[:3] == ['-m', 'pytest', 'tests']
    assert arguments[arguments.index('--ci-workload') + 1] == 'windows'
    assert '--ci-benchmark' in arguments and '--ci-shard' not in arguments
    return arguments


def _windows_arguments(step):
    arguments, tail = _array_arguments(step, 'pytestArgs')
    expected = """if ($env:CI_SHARD) {
        $pytestArgs += @('--ci-shard', "$env:CI_SHARD")
    }
    & .venv/Scripts/python.exe @pytestArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"""
    assert _expression(tail) == _expression(expected), 'Windows must execute its bound shard argv and preserve failures'
    assert _expression(step['env']['CI_SHARD']) == 'matrix.shard'
    return arguments


def _inventory_command(step):
    # Keep the reviewed control flow fail-closed without pretending to interpret PowerShell.
    expected = """$inventoryArgs = @(
        '-m', 'scripts.ci_tests', "$env:RUNNER_TEMP/inventory-portable/test-inventory.json"
    )
    if ($env:WINDOWS_MODE -eq 'serial') {
        $inventoryArgs += @("$env:RUNNER_TEMP/inventory-windows-serial/test-inventory.json")
    } elseif ($env:WINDOWS_MODE -eq 'two-shards') {
        $inventoryArgs += @(
            "$env:RUNNER_TEMP/inventory-windows-shard-0/test-inventory.json",
            "$env:RUNNER_TEMP/inventory-windows-shard-1/test-inventory.json"
        )
    } else {
        throw 'Unknown Windows execution mode.'
    }
    $inventoryArgs += @(
        '--python-version', "$env:PYTHON_VERSION", '--commit', "$env:GITHUB_SHA",
        '--run-id', "$env:GITHUB_RUN_ID", '--run-attempt', "$env:GITHUB_RUN_ATTEMPT"
    )
    & .venv/Scripts/python.exe @inventoryArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }"""
    assert _expression('\n'.join(_logical_lines(step))) == _expression(expected), 'Coverage must verify both original shard manifests from this run before building'


def _complete_pytest_arguments(arguments, workload, *, benchmark=False):
    """A matching inventory must not certify collect-only or a common filtered subset."""
    assert arguments[:3] == ['-m', 'pytest', 'tests']
    temporary = '$RUNNER_TEMP' if workload == 'portable' else '$env:RUNNER_TEMP'
    suffix = 'benchmark' if benchmark else workload
    values = {
        '-p': {'scripts.ci_tests'}, '--ci-workload': {workload},
        '--basetemp': {temporary + '/spt-pytest-' + suffix},
        '--ci-manifest': {temporary + '/test-inventory.json'},
        '--junitxml': {temporary + '/test-results.xml'},
        '-o': {'junit_logging=no', 'junit_log_passing_tests=false'},
    }
    flags = {'-q', '--durations=10'} | ({'--ci-benchmark'} if benchmark else set())
    seen, index = set(), 3
    while index < len(arguments):
        option = arguments[index]
        if option in flags:
            key = (option,)
            index += 1
        else:
            assert option in values and index + 1 < len(arguments), 'Pytest selection or unsupported execution option is forbidden'
            value = arguments[index + 1]
            assert value in values[option], 'Pytest option is not bound to the reviewed full-suite invocation'
            key = (option, value)
            index += 2
        assert key not in seen, 'Duplicate pytest option'
        seen.add(key)
    expected = {(flag,) for flag in flags} | {
        (option, value) for option, allowed in values.items() for value in allowed}
    assert seen == expected, 'Complete pytest invocation is missing required evidence options'


def _runs(step, *prefix):
    return any(command[:len(prefix)] == list(prefix) for command in _commands(step))


def _action(step, name):
    return step.get('uses', '').split('@', 1)[0] == name


def _one(steps, condition):
    matches = [(index, step) for index, step in enumerate(steps) if condition(step)]
    assert len(matches) == 1, f'Expected one matching step, found {len(matches)}'
    return matches[0]


def _success_only(step, condition=None):
    assert step.get('continue-on-error', False) is False, 'Failure must propagate'
    if condition is not None:
        assert _expression(step.get('if')) == _expression(condition), 'Critical step has the wrong execution condition'
    elif 'if' in step:
        assert _expression(step['if']) == 'success()', 'Critical step cannot bypass prior failure'


def _permissions(document, overrides=None):
    default = {'contents': 'read'}
    assert document.get('permissions') == default
    for name, job in document['jobs'].items():
        expected = (overrides or {}).get(name, default)
        assert job.get('permissions', document['permissions']) == expected, name
        assert job.get('continue-on-error', False) is False, name
        for step in job.get('steps', []):
            if 'uses' in step:
                assert re.fullmatch(r'[^@]+@[0-9a-f]{40}', step['uses']), 'Action must be SHA-pinned'
            if _action(step, 'actions/checkout'):
                assert step.get('with', {}).get('persist-credentials') is False
            if _action(step, 'actions/upload-artifact'):
                assert step['with']['name'].endswith('-attempt${{ github.run_attempt }}')
                assert step['with'].get('overwrite', False) is False, 'Previous attempt evidence must be retained'
            if _action(step, 'actions/download-artifact') and 'name' in step.get('with', {}):
                assert step['with']['name'].endswith('-attempt${{ github.run_attempt }}')


def validate_production(document):
    jobs = document['jobs']
    triggers = document['on']
    assert set(triggers) == {'push', 'pull_request', 'workflow_dispatch', 'schedule'}
    for event in ('push', 'pull_request'):
        assert triggers[event]['branches'] == ['main']
        assert not {'paths', 'paths-ignore'} & triggers[event].keys()
    inputs = triggers['workflow_dispatch']['inputs']
    assert set(inputs) == {'windows_mode', 'cache_mode'}
    for name, default, options in (
            ('windows_mode', 'two-shards', ['serial', 'two-shards']),
            ('cache_mode', 'restore', ['restore', 'cold'])):
        assert inputs[name]['type'] == 'choice' and inputs[name]['default'] == default
        assert inputs[name]['options'] == options
    assert _expression(document['concurrency']['group']) == _expression(
        "windows-build-${{ github.event_name }}-${{ github.event_name == 'pull_request' && github.event.pull_request.number || github.run_id }}")
    assert _expression(document['concurrency']['cancel-in-progress']) == "github.event_name=='pull_request'"
    _permissions(document, {
        'attest': {'contents': 'read', 'id-token': 'write', 'attestations': 'write'},
        'cleanup': {'contents': 'write', 'pull-requests': 'read'},
    })
    assert 'secrets.' not in json.dumps(document) and 'coretax.intranet' not in json.dumps(document)
    route = jobs['route']
    for name in ('mode', 'python_matrix', 'production_python', 'windows_mode', 'cache_mode', 'windows_matrix'):
        assert _expression(route['outputs'][name]) == f'steps.route.outputs.{name}'
    _, route_step = _one(route['steps'], lambda s: s.get('id') == 'route')
    assert _single_command(route_step) == ['-m', 'scripts.ci_route', 'route']
    assert _expression(route_step['env']['WINDOWS_MODE_INPUT']) == 'inputs.windows_mode'
    assert _expression(route_step['env']['CACHE_MODE_INPUT']) == 'inputs.cache_mode'
    for name in ('portable', 'windows', 'dependency-audit', 'package'):
        _, uv = _one(jobs[name]['steps'], lambda s: _action(s, 'astral-sh/setup-uv'))
        assert _expression(uv['with']['restore-cache']) == "needs.route.outputs.cache_mode!='cold'"
        save = "github.event_name=='push'&&github.ref=='refs/heads/main'"
        if name == 'windows':
            save += "&&(matrix.mode=='serial'||matrix.mode=='shard-0')"
        assert _expression(uv['with']['save-cache']) == save
    package, aggregate = jobs['package'], jobs['validate']
    assert _needs(package) == {'route', 'portable', 'windows', 'dependency-audit'}
    assert _expression(package['if']) == "needs.route.outputs.mode=='full'"
    assert _needs(aggregate) == {'route', 'portable', 'windows', 'dependency-audit', 'package', 'attest'}
    assert aggregate['name'] == 'Windows tests and dependency audit'
    assert _expression(aggregate['if']) == 'always()'
    _, gate = _one(aggregate['steps'], lambda step: _runs(step, '-m', 'scripts.ci_route', 'gate'))
    assert _expression(gate['env']['CI_NEEDS']) == 'toJSON(needs)'
    _success_only(gate)
    _single_command(gate)
    assert _needs(jobs['attest']) == {'route', 'package'}
    assert _expression(jobs['attest']['if']) == (
        "github.event_name=='push'&&github.ref=='refs/heads/main'&&needs.route.outputs.mode=='full'")
    assert _needs(jobs['cleanup']) == {'route', 'validate'}
    assert _expression(jobs['cleanup']['if']) == (
        "!cancelled()&&github.event_name=='push'&&github.ref=='refs/heads/main'"
        "&&needs.route.result=='success'&&needs.validate.result=='success'")

    steps = package['steps']
    downloads = [(i, s) for i, s in enumerate(steps)
                 if _action(s, 'actions/download-artifact') and 'name' in s.get('with', {})]
    expected_downloads = {
        'portable': None,
        'windows-serial': "needs.route.outputs.windows_mode == 'serial'",
        'windows-shard-0': "needs.route.outputs.windows_mode == 'two-shards'",
        'windows-shard-1': "needs.route.outputs.windows_mode == 'two-shards'",
    }
    assert len(downloads) == len(expected_downloads)
    assert {s['with']['name'].split('-python', 1)[0] for _, s in downloads} == {
        'test-inventory-' + name for name in expected_downloads}
    download_indices = {i for i, _ in downloads}
    for i, step in enumerate(steps):
        if i not in download_indices:
            _success_only(step)
    for _, step in downloads:
        label = step['with']['name'].split('-python', 1)[0].removeprefix('test-inventory-')
        _success_only(step, expected_downloads[label])
        assert set(step['with']) == {'name', 'path'}
        assert step['with']['name'] == 'test-inventory-' + label + '-python${{ matrix.python }}-${{ github.sha }}-attempt${{ github.run_attempt }}'
        assert step['with']['path'] == '${{ runner.temp }}/inventory-' + label
    assert _expression(package['env']['WINDOWS_MODE']) == 'needs.route.outputs.windows_mode'
    inventory_i, inventory = _one(steps, lambda s: s.get('id') == 'inventory')
    _inventory_command(inventory)
    identity_i, _ = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_artifact', 'build-info'))
    source_i, _ = _one(steps, lambda s: _runs(s, 'spt_gui.py', '--self-test'))
    build_i, _ = _one(steps, lambda s: _runs(s, 'build_desktop.py'))
    sbom_i, _ = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_sbom', 'create'))
    checksum_i, _ = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_artifact', 'write-checksums'))
    upload_i, upload = _one(steps, lambda s: _action(s, 'actions/upload-artifact') and s.get('id') == 'upload')
    assert upload.get('id') == 'upload'
    assert upload['with']['name'] == 'SPTDownloader-Windows-x64-${{ github.sha }}-python${{ matrix.python }}-attempt${{ github.run_attempt }}'
    assert upload['with']['if-no-files-found'] == 'error'
    assert set(upload['with']['path'].split()) == {
        'dist/SPTDownloader.exe', 'dist/LICENSE.txt', 'dist/README.txt',
        'dist/build-selftest.json', 'dist/build-info.json', 'dist/distribution-sbom.json',
        'dist/SHA256SUMS.txt'}
    readback_i, readback = _one(steps, lambda s: _action(s, 'actions/download-artifact')
                              and 'artifact-ids' in s.get('with', {}))
    assert _expression(readback['with']['artifact-ids']) == 'steps.upload.outputs.artifact-id'
    assert 'name' not in readback['with']
    verify_i, _ = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_artifact', 'verify'))
    smoke_i, smoke = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_runtime'))
    assert _expression(smoke['env']['ARTIFACT_ID']) == 'steps.upload.outputs.artifact-id'
    assert _single_command(smoke) == [
        '-m', 'scripts.ci_runtime', '--profile', '$env:PYTHON_PROFILE',
        '--executable', '$env:RUNNER_TEMP/artifact-readback/SPTDownloader.exe',
        '--artifact-id', '$env:ARTIFACT_ID', '--report', '$env:RUNNER_TEMP/packaged-bootstrap.json']
    smoke_upload_i, smoke_upload = _one(steps, lambda s: _action(s, 'actions/upload-artifact')
                                       and s.get('id') != 'upload')
    assert smoke_upload['with']['path'] == '${{ runner.temp }}/packaged-bootstrap.json'
    assert smoke_upload['with']['name'] == 'packaged-bootstrap-python${{ matrix.python }}-${{ github.sha }}-attempt${{ github.run_attempt }}'
    assert smoke_upload['with']['if-no-files-found'] == 'error'
    for index in (identity_i, source_i, build_i, sbom_i, checksum_i, verify_i):
        _single_command(steps[index])
    assert max(i for i, _ in downloads) < inventory_i < identity_i < source_i < build_i < sbom_i < checksum_i < upload_i < readback_i < verify_i < smoke_i < smoke_upload_i
    _, attest_download = _one(jobs['attest']['steps'], lambda s: _action(s, 'actions/download-artifact'))
    assert attest_download['with']['name'] == upload['with']['name']
    _, attest = _one(jobs['attest']['steps'], lambda s: _action(s, 'actions/attest') and 'subject-path' in s.get('with', {}))
    assert set(attest['with']['subject-path'].split()) == {
        'verified-artifact/SPTDownloader.exe', 'verified-artifact/SHA256SUMS.txt',
        'verified-artifact/build-info.json', 'verified-artifact/distribution-sbom.json'}
    _, archive_attest = _one(jobs['attest']['steps'], lambda s: _action(s, 'actions/attest') and 'subject-digest' in s.get('with', {}))
    assert archive_attest['with']['subject-name'] == 'SPTDownloader-Windows-x64.zip'
    assert archive_attest['with']['subject-digest'] == 'sha256:${{ needs.package.outputs.artifact_digest }}'
    assert package['outputs']['artifact_digest'] == '${{ steps.upload.outputs.artifact-digest }}'

    windows = jobs['windows']
    assert windows['runs-on'] == 'windows-2022' and _needs(windows) == {'route'}
    assert windows['timeout-minutes'] == 30 and package['timeout-minutes'] == 20
    assert windows['strategy']['fail-fast'] is False and windows['strategy']['max-parallel'] == 2
    assert _expression(windows['strategy']['matrix']) == 'fromJSON(needs.route.outputs.windows_matrix)'
    test_i, test = _one(windows['steps'], lambda s: s.get('id') == 'tests')
    _success_only(test)
    args = _windows_arguments(test)
    _complete_pytest_arguments(args, 'windows')
    assert args[:3] == ['-m', 'pytest', 'tests']
    assert args[args.index('--ci-workload') + 1] == 'windows'
    assert {'--ci-manifest', '--basetemp'} <= set(args)
    assert 'RUNNER_TEMP' in args[args.index('--basetemp') + 1]
    assert not any(a in {'-n', '--numprocesses', '--ci-shard', '--ci-benchmark', '&', ';'}
                   or a.startswith(('--ci-shard=', '--numprocesses=')) for a in args)
    fresh_i, fresh = _one(windows['steps'], lambda s: _runs(s, '-m', 'scripts.ci_runtime'))
    _success_only(fresh, "matrix.mode == 'serial' || matrix.mode == 'shard-0'")
    _single_command(fresh)
    assert fresh_i > test_i
    _, portable_tests = _one(jobs['portable']['steps'], lambda s: s.get('id') == 'tests')
    _complete_pytest_arguments(_single_command(portable_tests), 'portable')
    for step in windows['steps']:
        if _action(step, 'actions/upload-artifact'):
            prefix = 'test-inventory' if step['with']['path'].endswith('/test-inventory.json') else 'test-results'
            assert step['with']['name'] == prefix + '-windows-${{ matrix.mode }}-python${{ matrix.python }}-${{ github.sha }}-attempt${{ github.run_attempt }}'


def validate_measurements(document, job_names):
    expected_guard = "always()&&steps.tests.outcome!='skipped'"
    for name in job_names:
        steps = document['jobs'][name]['steps']
        start_i, _ = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_report', 'start'))
        uv_i, _ = _one(steps, lambda s: _action(s, 'astral-sh/setup-uv'))
        tests_i, tests = _one(steps, lambda s: s.get('id') == 'tests')
        _success_only(tests)
        args = (_benchmark_arguments(tests) if name == 'benchmark' else
                _windows_arguments(tests) if name == 'windows' else _single_command(tests))
        _complete_pytest_arguments(args, 'portable' if name == 'portable' else 'windows',
                                   benchmark=name == 'benchmark')
        assert args[:3] == ['-m', 'pytest', 'tests']
        assert all(option in args for option in ('--junitxml', 'junit_logging=no', 'junit_log_passing_tests=false'))
        report_i, report = _one(steps, lambda s: _runs(s, '-m', 'scripts.ci_report', 'report'))
        assert _expression(report.get('if')) == expected_guard
        _single_command(report)
        uploads = [(i, s) for i, s in enumerate(steps) if _action(s, 'actions/upload-artifact')]
        assert len(uploads) == 2
        paths = []
        for i, step in uploads:
            assert _expression(step.get('if')) == expected_guard
            assert step.get('continue-on-error', False) is False
            assert step['with']['if-no-files-found'] == 'error'
            paths.append({line.rsplit('/', 1)[-1] for line in step['with']['path'].splitlines() if line})
            assert report_i < i
        assert {'test-inventory.json'} in paths and {'test-results.xml', 'test-measurements.json'} in paths
        assert start_i < uv_i < tests_i < report_i


def validate_benchmark(document):
    _permissions(document)
    assert set(document['on']) == {'workflow_dispatch'}
    jobs = document['jobs']
    assert _needs(jobs['benchmark']) == {'profile'}
    assert jobs['benchmark']['runs-on'] == 'windows-2022'
    assert jobs['benchmark']['timeout-minutes'] == 30
    assert set(jobs['benchmark']['strategy']['matrix']['mode']) == {'serial', 'shard-0', 'shard-1'}
    assert _expression(jobs['benchmark']['env']['PYTHON_VERSION']) == 'needs.profile.outputs.production_python'
    assert _expression(jobs['benchmark']['env']['BENCHMARK_MODE']) == 'matrix.mode'
    _, profile = _one(jobs['profile']['steps'], lambda s: s.get('id') == 'profile')
    assert _runs(profile, '-m', 'scripts.ci_route', 'route')
    _, tests = _one(jobs['benchmark']['steps'], lambda s: s.get('id') == 'tests')
    _success_only(tests)
    _complete_pytest_arguments(_benchmark_arguments(tests), 'windows', benchmark=True)
    _, uv = _one(jobs['benchmark']['steps'], lambda s: _action(s, 'astral-sh/setup-uv'))
    assert uv['with']['save-cache'] is False
    assert _expression(uv['with']['restore-cache']) == "inputs.cache_mode!='cold'"
    compare = jobs['compare']
    assert _needs(compare) == {'profile', 'benchmark'}
    assert _expression(compare['if']) == 'always()'
    assert _expression(compare['env']['BENCHMARK_RESULT']) == 'needs.benchmark.result'
    guard = compare['steps'][0]
    assert shlex.split(guard['run']) == ['test', '$BENCHMARK_RESULT', '=', 'success']
    for step in compare['steps']:
        _success_only(step)
    downloads = [(i, s) for i, s in enumerate(compare['steps']) if _action(s, 'actions/download-artifact')]
    assert len(downloads) == 3
    assert {s['with']['name'].split('-${{', 1)[0] for _, s in downloads} == {
        'windows-benchmark-serial', 'windows-benchmark-shard-0', 'windows-benchmark-shard-1'}
    verify_i, verify = _one(compare['steps'], lambda s: _runs(s, '-m', 'scripts.ci_shard_benchmark'))
    assert max(i for i, _ in downloads) < verify_i
    assert {'--python-version', '--commit', '--run-id', '--run-attempt', '--output'} <= set(_single_command(verify))
