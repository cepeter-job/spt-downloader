"""Artifact verification rejects extra files, altered bytes and wrong build reports."""
import importlib.util
import hashlib
import json
from pathlib import Path

import pytest
from spt_desktop.runtime import WORKER_FILES, python_version
from support_build_reports import sorting_report


def verifier():
    source = Path(__file__).resolve().parents[1] / 'scripts' / 'ci_artifact.py'
    assert source.is_file(), 'Exact artifact verification is missing'
    spec = importlib.util.spec_from_file_location('ci_artifact', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def artifact(tmp_path):
    for name in ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt'):
        (tmp_path / name).write_bytes(b'SYNTHETIC CHECKSUM FIXTURE; NOT A REAL EXECUTABLE')
    (tmp_path / 'build-selftest.json').write_text(json.dumps({
        'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
        'diagnostics': {'schema': 1, 'safe_logging': True},
        'bugreport_footer': {'text': 'bugreport : sharmila@kemenkeu.go.id', 'bottom_right': True},
        'automatic_login_controls': {'origin_selector_present': False,
            'credential_origin': 'satu', 'account_forwarded': True},
        'selection_sorting_control': sorting_report(),
        'credentials_accessed': False, 'live_scrape': False,
        'python': '3.14.8', 'python_implementation': 'CPython', 'free_threaded': False,
        'tcl': '8.6.15', 'tk': '8.6.15', 'worker_python': python_version(),
        'worker_resources': list(WORKER_FILES), 'credential_check_controls': True,
        'gui_controls': ['Cek Kredensial'], 'build_profile': 'production',
        'personal_use_labels': ['Coretax → Excel · for personal use only'],
        'ui_text': {
            'title': 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
            'background': 'jalankan proses sedot di background',
            'results': 'Hasil Sedot berada di folder Downloads Windows'},
    }))
    identity = {'schema': 1, 'commit': 'a' * 40, 'run_id': '123', 'run_attempt': 2}
    (tmp_path / 'build-info.json').write_text(json.dumps(identity), encoding='utf-8')
    sbom = delivery_module('ci_sbom').make_sbom(
        build_info=identity,
        executable_digest=hashlib.sha256((tmp_path / 'SPTDownloader.exe').read_bytes()).hexdigest(),
        native_files=[{'path': path, 'sha256': str(index) * 64, 'size_bytes': 100 + index}
                      for index, path in enumerate(
                          ('python314.dll', 'tcl86t.dll', 'tk86t.dll', 'tools/uv.exe'), 1)],
        runtime_packages={'playwright': '1.64.0', 'openpyxl': '3.1.5'},
        runtime_lock_digest='f' * 64,
        versions={'python': '3.14.8', 'tcl': '8.6.15', 'tk': '8.6.15',
                  'uv': '0.13.4', 'pyinstaller': '6.22.3'})
    (tmp_path / 'distribution-sbom.json').write_text(json.dumps(sbom), encoding='utf-8')
    return tmp_path


def test_readback_checks_each_allowed_file_and_actual_selftest_version(artifact):
    module = verifier()
    module.write_checksums(artifact, '3.14.8')
    module.verify(artifact, '3.14.8')
    assert len((artifact / 'SHA256SUMS.txt').read_text().splitlines()) == 6
    with pytest.raises(ValueError, match='Python'):
        module.verify(artifact, '3.11.17')


@pytest.mark.parametrize('damage', ['extra_file', 'extra_directory', 'changed', 'missing',
                                   'unsafe_report', 'incomplete_checksums'])
def test_artifact_damage_cannot_receive_provenance(artifact, damage):
    module = verifier()
    module.write_checksums(artifact, '3.14.8')
    if damage == 'extra_file':
        (artifact / 'private.json').write_text('SYNTHETIC FORBIDDEN FILE')
    elif damage == 'extra_directory':
        (artifact / 'profile').mkdir()
    elif damage == 'changed':
        (artifact / 'SPTDownloader.exe').write_bytes(b'SYNTHETIC TAMPERED CONTENT')
    elif damage == 'missing':
        (artifact / 'LICENSE.txt').unlink()
    elif damage == 'unsafe_report':
        path = artifact / 'build-selftest.json'
        report = json.loads(path.read_text())
        report['credentials_accessed'] = True
        path.write_text(json.dumps(report))
        with pytest.raises(ValueError):
            module.write_checksums(artifact, '3.14.8')
    else:
        path = artifact / 'SHA256SUMS.txt'
        path.write_text(path.read_text().splitlines()[0] + '\n')
    with pytest.raises(ValueError):
        module.verify(artifact, '3.14.8')


@pytest.mark.parametrize('key,value', [('tk', ''), ('worker_resources', []),
                                      ('credential_check_controls', False),
                                      ('build_profile', 'candidate')])
def test_incomplete_frozen_runtime_evidence_cannot_be_checksummed(artifact, key, value):
    path = artifact / 'build-selftest.json'
    report = json.loads(path.read_text())
    report[key] = value
    path.write_text(json.dumps(report))
    with pytest.raises(ValueError):
        verifier().write_checksums(artifact, '3.14.8')


def delivery_module(name):
    source = Path(__file__).resolve().parents[1] / 'scripts' / (name + '.py')
    assert source.is_file(), 'Verified distribution delivery is missing: ' + name
    spec = importlib.util.spec_from_file_location(name, source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_evidence():
    commit = 'a' * 40
    run = {
        'id': 123, 'run_attempt': 2, 'head_sha': commit, 'head_branch': 'main',
        'event': 'push', 'status': 'completed', 'conclusion': 'success',
        'path': '.github/workflows/windows-build.yml',
        'repository': {'full_name': 'synthetic-owner/spt-downloader'},
        'head_repository': {'full_name': 'synthetic-owner/spt-downloader'},
    }
    names = [
        'Route changes and validate workflows', 'Portable tests (Python 3.14.8)',
        'Windows integration (Python 3.14.8, shard-0)',
        'Windows integration (Python 3.14.8, shard-1)',
        'Locked dependency audit', 'Windows package (Python 3.14.8)',
        'Artifact provenance (Python 3.14.8)', 'Windows tests and dependency audit',
    ]
    jobs = [{'name': name, 'run_id': 123, 'run_attempt': 2, 'head_sha': commit,
             'status': 'completed', 'conclusion': 'success'} for name in names]
    artifact = {
        'id': 456, 'name': f'SPTDownloader-Windows-x64-{commit}-python3.14.8-attempt2',
        'expired': False, 'size_in_bytes': 100, 'digest': 'sha256:' + 'b' * 64,
        'workflow_run': {'id': 123, 'head_sha': commit, 'head_branch': 'main'},
    }
    expected = dict(repository='synthetic-owner/spt-downloader', run_id=123, run_attempt=2,
                    commit=commit, artifact_id=456, python_version='3.14.8')
    return run, jobs, artifact, expected


def test_release_source_requires_exact_successful_main_run_and_artifact():
    run, jobs, artifact_data, expected = source_evidence()
    result = delivery_module('ci_release').validate_source(run, jobs, artifact_data, **expected)
    assert result == dict(expected, artifact_digest=artifact_data['digest'],
                         artifact_size=100, artifact_name=artifact_data['name'])


@pytest.mark.parametrize('endpoint,accept', [
    ('repos/synthetic-owner/spt-downloader/actions/artifacts/456/zip', 'application/vnd.github+json'),
    ('repos/synthetic-owner/spt-downloader/releases/assets/789', 'application/octet-stream'),
])
def test_release_download_preserves_bytes_with_the_endpoint_media_type(tmp_path, monkeypatch, endpoint, accept):
    module = delivery_module('ci_release')
    payload = b'PK\x03\x04SYNTHETIC BINARY DOWNLOAD\x00\xff'

    def command(argv, *, output):
        assert argv == ['gh', 'api', '--method', 'GET', '-H', 'Accept: ' + accept, endpoint]
        output.write(payload)

    monkeypatch.setattr(module, '_command', command)
    target = tmp_path / 'download.zip'
    module._download(endpoint, target, accept=accept)
    assert target.read_bytes() == payload


@pytest.mark.parametrize('damage', [
    'pr', 'dispatch', 'wrong-workflow', 'failed-run', 'incomplete-run', 'fork',
    'wrong-commit', 'wrong-attempt', 'wrong-artifact', 'wrong-artifact-run',
    'wrong-artifact-sha', 'expired', 'missing-digest', 'missing-package',
    'missing-provenance', 'failed-gate', 'old-job-attempt', 'duplicate-job',
])
def test_release_source_cannot_promote_untrusted_or_incomplete_evidence(damage):
    run, jobs, artifact_data, expected = source_evidence()
    if damage in ('pr', 'dispatch'):
        run['event'] = 'pull_request' if damage == 'pr' else 'workflow_dispatch'
    elif damage == 'wrong-workflow':
        run['path'] = '.github/workflows/unreviewed.yml'
    elif damage == 'failed-run':
        run['conclusion'] = 'failure'
    elif damage == 'incomplete-run':
        run['status'] = 'in_progress'
    elif damage == 'fork':
        run['head_repository']['full_name'] = 'synthetic-fork/spt-downloader'
    elif damage == 'wrong-commit':
        run['head_sha'] = 'c' * 40
    elif damage == 'wrong-attempt':
        run['run_attempt'] = 1
    elif damage == 'wrong-artifact':
        artifact_data['id'] = 457
    elif damage == 'wrong-artifact-run':
        artifact_data['workflow_run']['id'] = 124
    elif damage == 'wrong-artifact-sha':
        artifact_data['workflow_run']['head_sha'] = 'c' * 40
    elif damage == 'expired':
        artifact_data['expired'] = True
    elif damage == 'missing-digest':
        del artifact_data['digest']
    elif damage == 'missing-package':
        jobs[:] = [job for job in jobs if not job['name'].startswith('Windows package')]
    elif damage == 'missing-provenance':
        jobs[:] = [job for job in jobs if not job['name'].startswith('Artifact provenance')]
    elif damage == 'failed-gate':
        jobs[-1]['conclusion'] = 'failure'
    elif damage == 'old-job-attempt':
        jobs[0]['run_attempt'] = 1
    else:
        jobs.append(dict(jobs[0]))
    with pytest.raises(ValueError):
        delivery_module('ci_release').validate_source(run, jobs, artifact_data, **expected)


def test_release_archive_digest_and_allowlist_are_checked_before_extraction(tmp_path):
    import hashlib
    import zipfile

    module = delivery_module('ci_release')
    archive = tmp_path / 'synthetic.zip'
    names = ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json',
             'build-info.json', 'distribution-sbom.json', 'SHA256SUMS.txt')
    with zipfile.ZipFile(archive, 'w') as output:
        for name in names:
            output.writestr(name, b'SYNTHETIC ARCHIVE FIXTURE')
    digest = 'sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest()
    target = tmp_path / 'unpacked'
    module.extract_verified_archive(archive, target, digest=digest, size=archive.stat().st_size)
    assert {path.name for path in target.iterdir()} == set(names)
    with pytest.raises(ValueError, match='digest|checksum'):
        module.extract_verified_archive(archive, tmp_path / 'wrong',
                                        digest='sha256:' + '0' * 64, size=archive.stat().st_size)
    assert not (tmp_path / 'wrong').exists()


@pytest.mark.parametrize('extra', ['../outside.txt', '/absolute.txt', 'profile/private.json',
                                 'sptdownloader.EXE', 'build-info.json'])
def test_release_archive_rejects_traversal_extra_case_collision_and_duplicates(tmp_path, extra):
    import hashlib
    import warnings
    import zipfile

    module = delivery_module('ci_release')
    archive = tmp_path / 'bad.zip'
    with warnings.catch_warnings():
        warnings.simplefilter('ignore', UserWarning)
        with zipfile.ZipFile(archive, 'w') as output:
            for name in ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json',
                         'build-info.json', 'distribution-sbom.json', 'SHA256SUMS.txt', extra):
                output.writestr(name, b'SYNTHETIC')
    with pytest.raises(ValueError, match='allowlist|duplicate|path|archive'):
        module.extract_verified_archive(archive, tmp_path / 'target',
            digest='sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest(),
            size=archive.stat().st_size)
    assert not (tmp_path / 'target').exists()


def test_provenance_verification_binds_repository_workflow_main_sha_and_hosted_runner():
    command = delivery_module('ci_release').attestation_command(
        Path('synthetic/SPTDownloader.exe'), repository='synthetic-owner/spt-downloader',
        commit='a' * 40)
    assert command[:3] == ['gh', 'attestation', 'verify']
    for flag, value in (
        ('--repo', 'synthetic-owner/spt-downloader'),
        ('--signer-workflow', 'synthetic-owner/spt-downloader/.github/workflows/windows-build.yml'),
        ('--source-ref', 'refs/heads/main'), ('--source-digest', 'a' * 40),
        ('--signer-digest', 'a' * 40), ('--format', 'json'),
    ):
        assert command[command.index(flag) + 1] == value
    assert '--deny-self-hosted-runners' in command


def test_durable_rollback_retains_provenance_for_the_original_archive_digest():
    module = delivery_module('ci_release')
    assert module.ARCHIVE in module.SUBJECTS
    from support_workflows import load_workflow
    workflow = load_workflow(Path(__file__).resolve().parents[1] / '.github/workflows/windows-build.yml')
    assert workflow['jobs']['package']['outputs']['artifact_digest'] == '${{ steps.upload.outputs.artifact-digest }}'
    steps = [step for step in workflow['jobs']['attest']['steps']
             if step.get('with', {}).get('subject-name') == module.ARCHIVE]
    assert len(steps) == 1
    assert steps[0]['with']['subject-digest'] == 'sha256:${{ needs.package.outputs.artifact_digest }}'


def test_seven_file_distribution_requires_build_identity_and_sbom_before_checksums(artifact):
    (artifact / 'build-info.json').unlink()
    (artifact / 'distribution-sbom.json').unlink()
    with pytest.raises(ValueError, match='build-info|SBOM|sbom|distribution'):
        verifier().write_checksums(artifact, '3.14.8')


@pytest.mark.parametrize('damage', ['commit', 'run_id', 'exe_digest', 'native_missing', 'coverage'])
def test_recomputed_checksums_do_not_authorize_mismatched_distribution_metadata(artifact, damage):
    path = artifact / 'distribution-sbom.json'
    data = json.loads(path.read_text(encoding='utf-8'))
    if damage == 'commit':
        data['metadata']['component']['version'] = 'c' * 40
    elif damage == 'exe_digest':
        data['metadata']['component']['hashes'][0]['content'] = 'c' * 64
    elif damage == 'native_missing':
        data['components'] = [item for item in data['components']
                              if item['bom-ref'] != 'native:tools/uv.exe']
    else:
        name = 'spt:run_id' if damage == 'run_id' else 'spt:native_audit_coverage'
        next(item for item in data['metadata']['properties'] if item['name'] == name)['value'] = 'wrong'
    path.write_text(json.dumps(data), encoding='utf-8')
    with pytest.raises(ValueError, match='SBOM'):
        verifier().write_checksums(artifact, '3.14.8')


def test_build_info_uses_exact_github_identity_and_rejects_absent_or_invalid_values(tmp_path, monkeypatch):
    module = verifier()
    for key, value in {'GITHUB_SHA': 'a' * 40, 'GITHUB_RUN_ID': '123', 'GITHUB_RUN_ATTEMPT': '2'}.items():
        monkeypatch.setenv(key, value)
    module.main(['build-info', str(tmp_path), '--python-version', '3.14.8'])
    assert json.loads((tmp_path / 'build-info.json').read_text(encoding='utf-8')) == {
        'schema': 1, 'commit': 'a' * 40, 'run_id': '123', 'run_attempt': 2}
    for key, invalid in [('GITHUB_SHA', 'main'), ('GITHUB_RUN_ID', ''), ('GITHUB_RUN_ATTEMPT', '0')]:
        with monkeypatch.context() as context:
            context.setenv(key, invalid)
            with pytest.raises(ValueError, match='build-info'):
                module.write_build_info(tmp_path, '3.14.8')


@pytest.mark.parametrize('tcl_name,tk_name,tcl_tk_version', [
    ('tcl86t.dll', 'tk86t.dll', '8.6.15'),
    ('tcl90.dll', 'tcl9tk90.dll', '9.0.2'),
    ('TCL90.DLL', 'TCL9TK90.DLL', '9.0.2'),
])
def test_native_sbom_records_observed_bytes_and_worker_delivery_scope(
        tcl_name, tk_name, tcl_tk_version):
    module = delivery_module('ci_sbom')
    identity = {'schema': 1, 'commit': 'a' * 40, 'run_id': '123', 'run_attempt': 2}
    native = [
        {'path': path, 'sha256': str(index) * 64, 'size_bytes': 100 + index}
        for index, path in enumerate(('python314.dll', tcl_name, tk_name, 'tools/uv.exe'), 1)]
    data = module.make_sbom(
        build_info=identity, executable_digest='e' * 64, native_files=native,
        runtime_packages={'playwright': '1.64.0', 'openpyxl': '3.1.5'},
        runtime_lock_digest='f' * 64,
        versions={'python': '3.14.8', 'tcl': tcl_tk_version, 'tk': tcl_tk_version,
                  'uv': '0.13.4', 'pyinstaller': '6.22.3'})
    assert data['bomFormat'] == 'CycloneDX' and data['specVersion'] == '1.6'
    assert data['metadata']['component']['version'] == identity['commit']
    assert data['metadata']['component']['hashes'] == [{'alg': 'SHA-256', 'content': 'e' * 64}]
    components = {item['bom-ref']: item for item in data['components']}
    assert components['native:tools/uv.exe']['version'] == '0.13.4'
    assert components['native:python314.dll']['version'] == '3.14.8'
    assert components['native:' + tk_name]['version'] == tcl_tk_version
    assert {'name': 'spt:version_evidence', 'value': 'validated frozen Tk self-test'} in (
        components['native:' + tk_name]['properties'])
    assert components['native:tools/uv.exe']['hashes'] == [{'alg': 'SHA-256', 'content': '4' * 64}]
    worker = components['pkg:pypi/playwright@1.64.0']
    assert {'name': 'spt:delivery', 'value': 'managed-worker-download'} in worker['properties']
    properties = {item['name']: item['value'] for item in data['metadata']['properties']}
    assert properties['spt:run_id'] == '123' and properties['spt:run_attempt'] == '2'
    assert properties['spt:runtime_lock_sha256'] == 'f' * 64
    assert 'not vulnerability-audited' in properties['spt:native_audit_coverage']
    assert 'PRIVATE' not in json.dumps(data)
    module.validate_sbom(data, build_info=identity, executable_digest='e' * 64)


@pytest.mark.parametrize('tk_name,accepted', [
    ('tcl9tk90.dll', True),
    ('TCL9TK90.DLL', True),
    ('tcl9tk90.dll.backup', False),
    ('prefix-tcl9tk90.dll', False),
])
def test_native_sbom_validation_recognizes_exact_tcl9_tk_library(artifact, tk_name, accepted):
    module = delivery_module('ci_sbom')
    data = json.loads((artifact / 'distribution-sbom.json').read_text(encoding='utf-8'))
    identity = json.loads((artifact / 'build-info.json').read_text(encoding='utf-8'))
    digest = hashlib.sha256((artifact / 'SPTDownloader.exe').read_bytes()).hexdigest()
    tk_component = next(item for item in data['components'] if item['bom-ref'] == 'native:tk86t.dll')
    tk_component.update({'bom-ref': 'native:' + tk_name, 'name': tk_name, 'version': '9.0.2'})
    next(item for item in tk_component['properties'] if item['name'] == 'spt:archive_path')['value'] = tk_name
    data['dependencies'][0]['dependsOn'] = [item['bom-ref'] for item in data['components']]
    if accepted:
        module.validate_sbom(data, build_info=identity, executable_digest=digest)
    else:
        with pytest.raises(ValueError, match='required native'):
            module.validate_sbom(data, build_info=identity, executable_digest=digest)


def test_release_promotion_workflow_is_opt_in_read_only_until_explicit_publish():
    from support_workflows import load_workflow, _expression

    path = Path(__file__).resolve().parents[1] / '.github/workflows/release-promotion.yml'
    assert path.is_file(), 'Durable verified release promotion workflow is missing'
    workflow = load_workflow(path)
    assert set(workflow['on']) == {'workflow_dispatch'}
    read_permissions = {'contents': 'read', 'actions': 'read', 'attestations': 'read'}
    assert workflow['permissions'] == read_permissions
    inputs = workflow['on']['workflow_dispatch']['inputs']
    assert inputs['publish']['type'] == 'boolean' and inputs['publish']['default'] is False
    assert {'source_run_id', 'source_run_attempt', 'source_commit', 'artifact_id', 'tag'} <= inputs.keys()
    assert workflow['jobs']['verify']['permissions'] == read_permissions
    publish = workflow['jobs']['publish']
    assert publish['needs'] == ['verify']
    assert _expression(publish['if']) == "inputs.publish&&github.ref=='refs/heads/main'"
    assert publish['permissions'] == {'contents': 'write', 'attestations': 'read'}


def test_release_dispatch_threads_the_exact_source_python_version_through_both_jobs():
    import shlex
    from support_workflows import load_workflow, _expression

    path = Path(__file__).resolve().parents[1] / '.github/workflows/release-promotion.yml'
    workflow = load_workflow(path)
    inputs = workflow['on']['workflow_dispatch']['inputs']
    assert 'source_python_version' in inputs, 'Release dispatch cannot select a historical source Python version'
    version = inputs['source_python_version']
    assert version['required'] is True and version['type'] == 'string'
    assert 'default' not in version, 'The source version must not silently default to the current build pin'
    assert _expression(workflow['env']['SOURCE_PYTHON_VERSION']) == 'inputs.source_python_version'
    for job in ('verify', 'publish'):
        commands = [shlex.split(step['run']) for step in workflow['jobs'][job]['steps']
                    if 'scripts.ci_release' in step.get('run', '')]
        assert len(commands) == 1
        argv = commands[0]
        assert argv.count('--python-version') == 1
        assert argv[argv.index('--python-version') + 1] == '$SOURCE_PYTHON_VERSION'


def release_cli_arguments(tmp_path, command='prepare'):
    return [command, '--repository', 'synthetic-owner/spt-downloader', '--run-id', '123',
            '--run-attempt', '2', '--commit', 'a' * 40, '--artifact-id', '456',
            '--output', str(tmp_path / 'candidate'), '--tag', 'v2026.10.22']


def test_release_cli_requires_an_explicit_source_python_version_before_external_work(tmp_path, monkeypatch):
    module = delivery_module('ci_release')
    monkeypatch.setattr(module, 'prepare', lambda *args, **kwargs: pytest.fail('Missing source version reached preparation'))
    with pytest.raises(SystemExit) as failure:
        module.main(release_cli_arguments(tmp_path))
    assert failure.value.code == 2


@pytest.mark.parametrize('command,rollback', [('prepare', False), ('prepare', True),
                                             ('verify', False), ('publish', False)])
def test_release_cli_preserves_a_source_version_different_from_todays_pin(
        tmp_path, monkeypatch, command, rollback):
    module = delivery_module('ci_release')
    observed = []
    target = 'restore_release' if rollback else {'verify': 'verify_candidate'}.get(command, command)
    monkeypatch.setattr(module, target, lambda *args, **kwargs: observed.append(kwargs))
    argv = release_cli_arguments(tmp_path, command) + ['--python-version', '3.13.9']
    if rollback:
        argv += ['--rollback-tag', 'v2026.01.01']
    module.main(argv)
    assert len(observed) == 1 and observed[0]['python_version'] == '3.13.9'


@pytest.mark.parametrize('version', ['03.14.8', '3.014.8', '3.14.08', '\u0663.14.8',
                                    '3.14', '3.14.8+gil', '3.14.8;unused', '', None])
def test_release_source_python_version_requires_canonical_ascii_release_syntax(version):
    module = delivery_module('ci_release')
    _, _, _, identity = source_evidence()
    with pytest.raises(ValueError, match='Python|identity|version'):
        module._identity(**dict(identity, python_version=version))


@pytest.fixture
def prepared_release(artifact, tmp_path, monkeypatch):
    """Exercise real delivery code with an explicitly synthetic GitHub adapter."""
    import zipfile

    module = delivery_module('ci_release')
    verifier().write_checksums(artifact, '3.14.8')
    archive = tmp_path / 'original.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        for name in module.DISTRIBUTION_FILES:
            output.write(artifact / name, name)
    run, jobs, remote_artifact, identity = source_evidence()
    remote_artifact.update(size_in_bytes=archive.stat().st_size,
                           digest='sha256:' + hashlib.sha256(archive.read_bytes()).hexdigest())
    commands = []

    def api(endpoint, **kwargs):
        assert kwargs == {}
        responses = {
            'repos/synthetic-owner/spt-downloader/actions/runs/123/attempts/2': run,
            'repos/synthetic-owner/spt-downloader/actions/artifacts/456': remote_artifact,
        }
        assert endpoint in responses, 'Preparation must not mutate GitHub'
        return responses[endpoint]

    def download(endpoint, path, *, accept):
        assert endpoint == 'repos/synthetic-owner/spt-downloader/actions/artifacts/456/zip'
        assert accept == 'application/vnd.github+json', 'Actions ZIP redirects reject the release-asset media type'
        Path(path).write_bytes(archive.read_bytes())

    def command(argv, *, cwd=None, **kwargs):
        assert not kwargs, 'Signature adapter cannot write through GitHub API'
        commands.append(list(argv))
        assert argv[:2] == ['gh', 'attestation']
        subject = Path(argv[3])
        digest = hashlib.sha256(subject.read_bytes()).hexdigest()
        if argv[2] == 'download':
            # gh uses a hyphen on Windows, where ':' is not a valid filename.
            Path(cwd, 'sha256-' + digest + '.jsonl').write_text(
                json.dumps({'synthetic': True, 'digest': digest}), encoding='utf-8')
            return b''
        assert argv[2] == 'verify' and '--deny-self-hosted-runners' in argv
        bundle = json.loads(Path(argv[argv.index('--bundle') + 1]).read_text(encoding='utf-8'))
        if bundle != {'synthetic': True, 'digest': digest}:
            raise ValueError('Synthetic signature adapter rejected changed subject/bundle bytes')
        return b'[{"verificationResult": {"synthetic": true}}]'

    monkeypatch.setattr(module, '_api', api)
    monkeypatch.setattr(module, '_jobs', lambda *args: jobs)
    monkeypatch.setattr(module, '_download', download)
    monkeypatch.setattr(module, '_command', command)
    assets = module.prepare(tmp_path / 'candidate', **identity)
    return module, assets, identity, commands, command


def release_metadata(module, assets, identity, *, draft=False):
    return {'id': 321, 'tag_name': 'v2026.10.22', 'target_commitish': identity['commit'],
            'draft': draft, 'html_url': 'https://example.invalid/synthetic-release',
            'assets': [
                {'id': 1000 + index, 'name': path.name, 'size': path.stat().st_size,
                 'digest': 'sha256:' + hashlib.sha256(path.read_bytes()).hexdigest()}
                for index, path in enumerate(sorted(assets.iterdir()))]}


def test_prepare_reverifies_every_retained_subject_without_publishing(prepared_release):
    module, assets, identity, commands, _ = prepared_release
    assert {path.name for path in assets.iterdir()} == set(module.ASSETS) | {module.RELEASE_MANIFEST}
    assert len([argv for argv in commands if argv[2] == 'download']) == 5
    assert len([argv for argv in commands if argv[2] == 'verify']) == 10
    assert all(argv[:2] == ['gh', 'attestation'] for argv in commands)
    receipt = json.loads((assets / module.RECEIPT).read_text(encoding='utf-8'))
    assert all(receipt['source'][key] == value for key, value in identity.items())


def test_rollback_uses_retained_assets_after_actions_artifact_expiry(prepared_release, tmp_path, monkeypatch):
    module, assets, identity, commands, _ = prepared_release
    release = release_metadata(module, assets, identity)
    endpoints = []

    def api(endpoint, **kwargs):
        endpoints.append(endpoint)
        assert '/actions/' not in endpoint, 'Rollback must survive Actions artifact/run expiry'
        if '/releases/tags/' in endpoint:
            return release
        assert '/git/ref/tags/' in endpoint
        return {'object': {'type': 'commit', 'sha': identity['commit']}}

    by_id = {entry['id']: entry for entry in release['assets']}

    def download(endpoint, path, *, accept):
        assert accept == 'application/octet-stream', 'Release assets must return bytes instead of JSON metadata'
        Path(path).write_bytes((assets / by_id[int(endpoint.rsplit('/', 1)[1])]['name']).read_bytes())

    monkeypatch.setattr(module, '_api', api)
    monkeypatch.setattr(module, '_download', download)
    before = len(commands)
    restored = module.restore_release(tmp_path / 'rollback', 'v2026.10.22', **identity)
    assert {path.name for path in restored.iterdir()} == {path.name for path in assets.iterdir()}
    assert len(commands[before:]) == 5
    assert all(argv[2] == 'verify' for argv in commands[before:])
    assert endpoints and all('/actions/' not in endpoint for endpoint in endpoints)


@pytest.mark.parametrize('damage', ['archive', 'receipt', 'bundle'])
def test_publish_rejects_tampering_even_when_outer_checksums_are_recomputed(
        prepared_release, monkeypatch, damage):
    module, assets, identity, commands, _ = prepared_release
    for key, value in {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
                       'GITHUB_REF': 'refs/heads/main', 'GITHUB_REPOSITORY': identity['repository']}.items():
        monkeypatch.setenv(key, value)
    if damage == 'archive':
        with (assets / module.ARCHIVE).open('ab') as output:
            output.write(b'SYNTHETIC CHANGED ZIP')
    elif damage == 'receipt':
        path = assets / module.RECEIPT
        data = json.loads(path.read_text(encoding='utf-8'))
        data['source']['artifact_id'] += 1
        path.write_text(json.dumps(data), encoding='utf-8')
    else:
        (assets / (module.ARCHIVE + '.sigstore.jsonl')).write_text('{}', encoding='utf-8')
    (assets / module.RELEASE_MANIFEST).write_text(''.join(
        hashlib.sha256((assets / name).read_bytes()).hexdigest() + '  ' + name + '\n'
        for name in module.ASSETS), encoding='ascii')
    monkeypatch.setattr(module, '_api', lambda *args, **kwargs: pytest.fail('Tampered candidate reached release API'))
    with pytest.raises(ValueError):
        module.publish(assets, 'v2026.10.22', **identity)
    assert all(argv[:2] == ['gh', 'attestation'] for argv in commands)


@pytest.fixture
def publishing_release(prepared_release, monkeypatch):
    """Model draft visibility and numeric-ID mutations at the documented REST boundary."""
    from urllib.parse import parse_qs, urlparse

    module, assets, identity, _, signature_command = prepared_release
    for key, value in {'GITHUB_ACTIONS': 'true', 'GITHUB_EVENT_NAME': 'workflow_dispatch',
                       'GITHUB_REF': 'refs/heads/main', 'GITHUB_REPOSITORY': identity['repository']}.items():
        monkeypatch.setenv(key, value)
    state = {'created': False, 'published': False, 'tag_created': False,
             'tag': {'type': 'commit', 'sha': identity['commit']}, 'damage': None,
             'downloaded': 0, 'reads': [], 'mutations': [], 'uploaded': {}}
    release = release_metadata(module, assets, identity)
    by_id = {entry['id']: entry for entry in release['assets']}
    by_name = {entry['name']: entry for entry in release['assets']}
    base = 'repos/' + identity['repository']

    def current_release():
        return dict(release, draft=not state['published'],
                    assets=[by_name[name] for name in state['uploaded']])

    def api(endpoint, *, missing=False):
        state['reads'].append(endpoint)
        if '/git/ref/tags/' in endpoint:
            if missing and not state['tag_created']:
                return None
            assert state['tag_created']
            return {'object': dict(state['tag'])}
        if '/releases/tags/' in endpoint:
            if missing and not state['created']:
                return None
            if not state['published']:
                raise RuntimeError('Published-release endpoint returned HTTP 404 for draft')
            return current_release()
        assert endpoint == base + '/releases/321', 'Readback must retain the created release ID'
        assert state['created']
        return current_release()

    def command(argv, **kwargs):
        if argv[:2] == ['gh', 'attestation']:
            return signature_command(argv, **kwargs)
        assert '--clobber' not in argv and 'delete' not in argv
        state['mutations'].append(list(argv))
        if argv[:2] == ['gh', 'api']:
            method = argv[argv.index('--method') + 1]
            endpoint = next(value for value in argv if value.startswith(('repos/', 'https://uploads.github.com/')))
            if endpoint == base + '/git/refs':
                assert method == 'POST' and not state['tag_created']
                assert json.loads(kwargs['input_data']) == {
                    'ref': 'refs/tags/v2026.10.22', 'sha': identity['commit']}
                state['tag_created'] = True
                return b'{}'
            if endpoint == base + '/releases':
                payload = json.loads(kwargs['input_data'])
                assert method == 'POST' and not state['created'] and state['tag_created']
                assert payload['draft'] is True and payload['target_commitish'] == identity['commit']
                assert payload['tag_name'] == release['tag_name']
                state['created'] = True
                return json.dumps(current_release()).encode()
            if endpoint.startswith('https://uploads.github.com/'):
                parsed = urlparse(endpoint)
                assert method == 'POST' and parsed.path == '/' + base + '/releases/321/assets'
                name, = parse_qs(parsed.query)['name']
                assert name in by_name and name not in state['uploaded']
                assert 'Content-Type: application/octet-stream' in argv
                path = Path(argv[argv.index('--input') + 1])
                state['uploaded'][name] = path.read_bytes()
                return json.dumps(by_name[name]).encode()
            assert endpoint == base + '/releases/321' and method == 'PATCH'
            assert json.loads(kwargs['input_data']) == {'draft': False, 'make_latest': 'true'}
            assert len(state['uploaded']) == len(by_name)
            state['published'] = True
            return json.dumps(current_release()).encode()
        if argv[:3] == ['gh', 'release', 'create']:
            # Model the old CLI create accurately so the regression reaches the
            # actual bug: REST GET-by-tag cannot retrieve this draft afterward.
            assert '--draft' in argv and '--verify-tag' in argv
            state['created'] = True
            state['uploaded'] = {name: (assets / name).read_bytes() for name in by_name}
            return b''
        raise AssertionError('Publication must mutate the created numeric release ID')

    def download(endpoint, path, *, accept):
        assert accept == 'application/octet-stream', 'Draft and published asset readback must return bytes'
        name = by_id[int(endpoint.rsplit('/', 1)[1])]['name']
        content = state['uploaded'][name]
        if state['damage'] == 'archive' and name == module.ARCHIVE:
            content += b'SYNTHETIC DRAFT DAMAGE'
        Path(path).write_bytes(content)
        state['downloaded'] += 1
        if state['downloaded'] == len(by_name):
            if state['damage'] == 'tag-moved':
                state['tag']['sha'] = 'b' * 40
            elif state['damage'] == 'tag-object':
                state['tag']['type'] = 'tag'

    monkeypatch.setattr(module, '_api', api)
    monkeypatch.setattr(module, '_command', command)
    monkeypatch.setattr(module, '_download', download)
    return module, assets, identity, release, state


@pytest.mark.parametrize('corrupt_draft', [False, True])
def test_publish_checks_draft_readback_by_created_id_before_publication_and_never_clobbers(
        publishing_release, corrupt_draft):
    module, assets, identity, release, state = publishing_release
    state['damage'] = 'archive' if corrupt_draft else None
    if corrupt_draft:
        with pytest.raises(ValueError, match='digest|size'):
            module.publish(assets, 'v2026.10.22', **identity)
        assert not state['published']
        assert 0 < state['downloaded'] <= len(release['assets'])
    else:
        assert module.publish(assets, 'v2026.10.22', **identity) == release['html_url']
        assert state['published']
        assert state['downloaded'] == 2 * len(release['assets'])
    assert any(endpoint.endswith('/releases/321') for endpoint in state['reads'])
    assert all(argv[:2] == ['gh', 'api'] for argv in state['mutations'])


@pytest.mark.parametrize('damage', ['tag-moved', 'tag-object'])
def test_a_tag_changed_after_draft_readback_never_becomes_public(publishing_release, damage):
    module, assets, identity, release, state = publishing_release
    state['damage'] = damage
    with pytest.raises(ValueError, match='tag|Tag|source commit'):
        module.publish(assets, 'v2026.10.22', **identity)
    assert state['created'] and not state['published'], 'A changed tag must leave the release in draft'
    assert state['downloaded'] == len(release['assets']), 'The race is injected after complete draft readback'
    assert not any('PATCH' in argv for argv in state['mutations'])


def test_publish_refuses_non_main_dispatch_before_any_external_command(prepared_release, monkeypatch):
    module, assets, identity, _, _ = prepared_release
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/synthetic-feature')
    monkeypatch.setattr(module, '_command', lambda *args, **kwargs: pytest.fail('Untrusted publish invoked gh'))
    with pytest.raises(ValueError, match='trusted-main'):
        module.publish(assets, 'v2026.10.22', **identity)
