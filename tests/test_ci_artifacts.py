"""Artifact verification rejects extra files, altered bytes and wrong build reports."""
import importlib.util
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
    return tmp_path


def test_readback_checks_each_allowed_file_and_actual_selftest_version(artifact):
    module = verifier()
    module.write_checksums(artifact, '3.14.8')
    module.verify(artifact, '3.14.8')
    assert len((artifact / 'SHA256SUMS.txt').read_text().splitlines()) == 4
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


def test_seven_file_distribution_requires_build_identity_and_sbom_before_checksums(artifact):
    with pytest.raises(ValueError, match='build-info|SBOM|sbom|distribution'):
        verifier().write_checksums(artifact, '3.14.8')


def test_native_sbom_records_observed_bytes_and_worker_delivery_scope():
    module = delivery_module('ci_sbom')
    identity = {'schema': 1, 'commit': 'a' * 40, 'run_id': '123', 'run_attempt': 2}
    native = [
        {'path': path, 'sha256': str(index) * 64, 'size_bytes': 100 + index}
        for index, path in enumerate(('python314.dll', 'tcl86t.dll', 'tk86t.dll', 'tools/uv.exe'), 1)]
    data = module.make_sbom(
        build_info=identity, executable_digest='e' * 64, native_files=native,
        runtime_packages={'playwright': '1.64.0', 'openpyxl': '3.1.5'},
        runtime_lock_digest='f' * 64,
        versions={'python': '3.14.8', 'tcl': '8.6.15', 'tk': '8.6.15',
                  'uv': '0.13.4', 'pyinstaller': '6.22.3'})
    assert data['bomFormat'] == 'CycloneDX' and data['specVersion'] == '1.6'
    assert data['metadata']['component']['version'] == identity['commit']
    assert data['metadata']['component']['hashes'] == [{'alg': 'SHA-256', 'content': 'e' * 64}]
    components = {item['bom-ref']: item for item in data['components']}
    assert components['native:tools/uv.exe']['version'] == '0.13.4'
    assert components['native:python314.dll']['version'] == '3.14.8'
    assert components['native:tools/uv.exe']['hashes'] == [{'alg': 'SHA-256', 'content': '4' * 64}]
    worker = components['pkg:pypi/playwright@1.64.0']
    assert {'name': 'spt:delivery', 'value': 'managed-worker-download'} in worker['properties']
    properties = {item['name']: item['value'] for item in data['metadata']['properties']}
    assert properties['spt:run_id'] == '123' and properties['spt:run_attempt'] == '2'
    assert properties['spt:runtime_lock_sha256'] == 'f' * 64
    assert 'not vulnerability-audited' in properties['spt:native_audit_coverage']
    assert 'PRIVATE' not in json.dumps(data)


def test_release_promotion_workflow_is_opt_in_read_only_until_explicit_publish():
    from support_workflows import load_workflow, _expression

    path = Path(__file__).resolve().parents[1] / '.github/workflows/release-promotion.yml'
    assert path.is_file(), 'Durable verified release promotion workflow is missing'
    workflow = load_workflow(path)
    assert set(workflow['on']) == {'workflow_dispatch'}
    assert workflow['permissions'] == {'contents': 'read', 'attestations': 'read'}
    inputs = workflow['on']['workflow_dispatch']['inputs']
    assert inputs['publish']['type'] == 'boolean' and inputs['publish']['default'] is False
    assert {'source_run_id', 'source_run_attempt', 'source_commit', 'artifact_id', 'tag'} <= inputs.keys()
    assert workflow['jobs']['verify']['permissions'] == {'contents': 'read', 'attestations': 'read'}
    publish = workflow['jobs']['publish']
    assert publish['needs'] == ['verify']
    assert _expression(publish['if']) == "inputs.publish&&github.ref=='refs/heads/main'"
    assert publish['permissions'] == {'contents': 'write', 'attestations': 'read'}
