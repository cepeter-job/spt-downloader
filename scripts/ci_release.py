"""Verify exact trusted-main artifacts; publication is a separate explicit command."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
from urllib.parse import quote
import zipfile


WORKFLOW = '.github/workflows/windows-build.yml'
PAYLOAD = ('SPTDownloader.exe', 'LICENSE.txt', 'README.txt', 'build-selftest.json',
           'build-info.json', 'distribution-sbom.json')
DISTRIBUTION_FILES = frozenset((*PAYLOAD, 'SHA256SUMS.txt'))
ARCHIVE = 'SPTDownloader-Windows-x64.zip'
SUBJECTS = ('SPTDownloader.exe', 'SHA256SUMS.txt', 'build-info.json', 'distribution-sbom.json', ARCHIVE)
RECEIPT = 'release-receipt.json'
VERIFICATION = 'provenance-verification.json'
RELEASE_MANIFEST = 'release-SHA256SUMS.txt'
ASSETS = (ARCHIVE, RECEIPT, VERIFICATION, *(name + '.sigstore.jsonl' for name in SUBJECTS))
MAX_ARCHIVE = 512 * 1024 * 1024


def _sha(value, length=40):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{' + str(length) + '}', value):
        raise ValueError('A complete lowercase commit or checksum digest is required.')
    return value


def _positive(value):
    if type(value) is not int or value < 1:
        raise ValueError('Run, attempt and artifact identities must be positive integers.')
    return value


def _identity(repository, run_id, run_attempt, commit, artifact_id, python_version):
    if (not isinstance(repository, str)
            or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository)
            or not isinstance(python_version, str)
            or not re.fullmatch(r'[1-9][0-9]*\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)', python_version)):
        raise ValueError('Repository or Python identity is invalid.')
    return dict(repository=repository, run_id=_positive(run_id), run_attempt=_positive(run_attempt),
                commit=_sha(commit), artifact_id=_positive(artifact_id), python_version=python_version)


def _artifact_name(commit, python_version, run_attempt):
    return f'SPTDownloader-Windows-x64-{commit}-python{python_version}-attempt{run_attempt}'


def validate_source(run, jobs, artifact, *, repository, run_id, run_attempt,
                    commit, artifact_id, python_version):
    identity = _identity(repository, run_id, run_attempt, commit, artifact_id, python_version)
    expected = {'id': run_id, 'run_attempt': run_attempt, 'head_sha': commit,
                'head_branch': 'main', 'event': 'push', 'status': 'completed',
                'conclusion': 'success', 'path': WORKFLOW}
    if (not isinstance(run, dict) or any(run.get(key) != value for key, value in expected.items())
            or run.get('repository', {}).get('full_name') != repository
            or run.get('head_repository', {}).get('full_name') != repository):
        raise ValueError('Source must be the exact completed successful trusted-main push build.')
    names = {
        'Route changes and validate workflows', f'Portable tests (Python {python_version})',
        f'Windows integration (Python {python_version}, shard-0)',
        f'Windows integration (Python {python_version}, shard-1)',
        'Locked dependency audit', f'Windows package (Python {python_version})',
        f'Artifact provenance (Python {python_version})', 'Windows tests and dependency audit',
    }
    if not isinstance(jobs, list) or any(not isinstance(job, dict) for job in jobs):
        raise ValueError('Source job evidence is malformed.')
    for name in names:
        matches = [job for job in jobs if job.get('name') == name]
        required = {'run_id': run_id, 'run_attempt': run_attempt, 'head_sha': commit,
                    'status': 'completed', 'conclusion': 'success'}
        if len(matches) != 1 or any(matches[0].get(key) != value for key, value in required.items()):
            raise ValueError('Source has missing, duplicated, failed or mixed-attempt required jobs: ' + name)
    if (not isinstance(artifact, dict) or artifact.get('id') != artifact_id
            or artifact.get('expired') is not False
            or artifact.get('name') != _artifact_name(commit, python_version, run_attempt)
            or artifact.get('workflow_run', {}).get('id') != run_id
            or artifact['workflow_run'].get('head_sha') != commit
            or artifact['workflow_run'].get('head_branch') != 'main'
            or type(artifact.get('size_in_bytes')) is not int
            or not 0 < artifact['size_in_bytes'] <= MAX_ARCHIVE
            or not re.fullmatch(r'sha256:[0-9a-f]{64}', str(artifact.get('digest', '')))):
        raise ValueError('Artifact ID, digest, size, expiry or source identity does not match.')
    return dict(identity, artifact_digest=artifact['digest'], artifact_size=artifact['size_in_bytes'],
                artifact_name=artifact['name'])


def _hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _verify_bytes(path, digest, size):
    path = Path(path)
    if (not re.fullmatch(r'sha256:[0-9a-f]{64}', str(digest))
            or type(size) is not int or not 0 < size <= MAX_ARCHIVE
            or path.is_symlink() or not path.is_file() or path.stat().st_size != size
            or 'sha256:' + _hash(path) != digest):
        raise ValueError('Downloaded archive or release asset digest/size does not match its source.')


def extract_verified_archive(archive, target, *, digest, size):
    """Check the complete archive before creating an extraction destination."""
    _verify_bytes(archive, digest, size)
    target = Path(target)
    if target.exists() or target.is_symlink():
        raise ValueError('Archive extraction destination must not already exist.')
    with zipfile.ZipFile(archive) as source:
        entries = source.infolist()
        names = [item.filename for item in entries]
        if len(names) != len(set(names)) or set(names) != DISTRIBUTION_FILES:
            raise ValueError('Archive differs from the exact distribution allowlist or has duplicate paths.')
        for item in entries:
            kind = stat.S_IFMT(item.external_attr >> 16)
            limit = MAX_ARCHIVE if item.filename == 'SPTDownloader.exe' else 8 * 1024 * 1024
            if (item.is_dir() or kind not in (0, stat.S_IFREG) or item.flag_bits & 1
                    or not 0 < item.file_size <= limit):
                raise ValueError('Archive contains a linked, encrypted or oversized path.')
        if sum(item.file_size for item in entries) > MAX_ARCHIVE:
            raise ValueError('Archive expanded size exceeds the bounded distribution limit.')
        target.mkdir(parents=True)
        try:
            for item in entries:
                with source.open(item) as incoming, (target / item.filename).open('xb') as output:
                    shutil.copyfileobj(incoming, output)
        except BaseException:
            shutil.rmtree(target)
            raise


def attestation_command(path, *, repository, commit):
    _sha(commit)
    return ['gh', 'attestation', 'verify', str(path), '--repo', repository,
            '--signer-workflow', repository + '/' + WORKFLOW, '--source-ref', 'refs/heads/main',
            '--source-digest', commit, '--signer-digest', commit,
            '--deny-self-hosted-runners', '--format', 'json']


def _command(argv, *, cwd=None, output=None, input_data=None):
    environment = dict(os.environ, GH_PROMPT_DISABLED='1', GH_HOST='github.com')
    environment.pop('GH_DEBUG', None)
    result = subprocess.run(argv, cwd=cwd, input=input_data, stdout=output or subprocess.PIPE,
                            stderr=subprocess.PIPE, check=True, timeout=180, env=environment)
    return result.stdout


def _api(endpoint, *, missing=False):
    try:
        raw = _command(['gh', 'api', '--method', 'GET', endpoint])
    except subprocess.CalledProcessError as error:
        if missing and re.search(rb'\bHTTP 404\b', error.stderr or b''):
            return None
        raise RuntimeError('GitHub metadata request failed; no fallback to weaker evidence.') from error
    return json.loads(raw)


def _write_api(method, endpoint, payload):
    raw = _command(['gh', 'api', '--method', method, endpoint, '--input', '-'],
                   input_data=json.dumps(payload).encode('utf-8'))
    return json.loads(raw)


def _download(endpoint, path):
    with Path(path).open('xb') as output:
        _command(['gh', 'api', '--method', 'GET', '-H', 'Accept: application/octet-stream', endpoint],
                 output=output)


def _jobs(repository, run_id, run_attempt):
    result = []
    for page in range(1, 11):
        data = _api(f'repos/{repository}/actions/runs/{run_id}/attempts/{run_attempt}/jobs?per_page=100&page={page}')
        if (not isinstance(data.get('jobs'), list) or type(data.get('total_count')) is not int
                or data['total_count'] < 1):
            raise ValueError('Source job response is incomplete.')
        result.extend(data['jobs'])
        if len(result) == data['total_count']:
            return result
        if not data['jobs'] or len(result) > data['total_count']:
            break
    raise ValueError('Could not read a complete bounded source job inventory.')


def _json(path):
    if Path(path).stat().st_size > 8 * 1024 * 1024:
        raise ValueError('Release metadata exceeds its size bound.')
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def _manifest(folder):
    return ''.join(_hash(folder / name) + '  ' + name + '\n' for name in ASSETS)


def verify_payload(folder, source):
    """Use the stable delivery schema so older releases do not depend on today's GUI controls."""
    if ({path.name for path in folder.iterdir()} != DISTRIBUTION_FILES
            or any(path.is_symlink() or not path.is_file() for path in folder.iterdir())):
        raise ValueError('Release payload differs from its exact distribution allowlist.')
    expected_manifest = ''.join(_hash(folder / name) + '  ' + name + '\n' for name in PAYLOAD)
    if (folder / 'SHA256SUMS.txt').read_text(encoding='ascii') != expected_manifest:
        raise ValueError('Release distribution checksum manifest does not match all payload bytes.')
    identity = _json(folder / 'build-info.json')
    if identity != {'schema': 1, 'commit': source['commit'], 'run_id': str(source['run_id']),
                    'run_attempt': source['run_attempt']}:
        raise ValueError('Release build identity does not match its selected source.')
    report = _json(folder / 'build-selftest.json')
    expected = {'ok': True, 'frozen': True, 'uv_bundled': True, 'bits': 64,
                'credentials_accessed': False, 'live_scrape': False, 'free_threaded': False,
                'python_implementation': 'CPython', 'python': source['python_version']}
    if any(type(report.get(key)) is not type(value) or report[key] != value for key, value in expected.items()):
        raise ValueError('Release frozen self-test has unsuccessful or unsafe core evidence.')
    from scripts.ci_sbom import validate_sbom
    validate_sbom(_json(folder / 'distribution-sbom.json'), build_info=identity,
                  executable_digest=_hash(folder / 'SPTDownloader.exe'))


def _verify_provenance(folder, assets, source):
    results = {}
    for name in SUBJECTS:
        bundle = assets / (name + '.sigstore.jsonl')
        subject = assets / name if name == ARCHIVE else folder / name
        result = json.loads(_command(attestation_command(subject,
            repository=source['repository'], commit=source['commit']) + ['--bundle', str(bundle)]))
        if (not isinstance(result, list) or not result
                or any(not isinstance(item, dict) or not item.get('verificationResult') for item in result)):
            raise ValueError('Provenance verification returned no verified attestations.')
        results[name] = result
    return results


def prepare(output, **identity):
    identity = _identity(**identity)
    repository, run_id, attempt = (identity[key] for key in ('repository', 'run_id', 'run_attempt'))
    run = _api(f'repos/{repository}/actions/runs/{run_id}/attempts/{attempt}')
    artifact = _api(f'repos/{repository}/actions/artifacts/{identity["artifact_id"]}')
    source = validate_source(run, _jobs(repository, run_id, attempt), artifact, **identity)
    assets = Path(output) / 'assets'
    assets.mkdir(parents=True, exist_ok=False)
    _download(f'repos/{repository}/actions/artifacts/{identity["artifact_id"]}/zip', assets / ARCHIVE)
    with tempfile.TemporaryDirectory(prefix='spt-release-') as temporary:
        folder = Path(temporary) / 'payload'
        extract_verified_archive(assets / ARCHIVE, folder,
                                 digest=source['artifact_digest'], size=source['artifact_size'])
        verify_payload(folder, source)
        for name in SUBJECTS:
            subject = assets / name if name == ARCHIVE else folder / name
            with tempfile.TemporaryDirectory(prefix='spt-attestation-') as downloads:
                _command(['gh', 'attestation', 'download', str(subject.resolve()), '--repo', repository], cwd=downloads)
                files = list(Path(downloads).iterdir())
                if (len(files) != 1 or files[0].is_symlink() or not files[0].is_file()
                        or files[0].name not in {'sha256:' + _hash(subject) + '.jsonl',
                                                 'sha256-' + _hash(subject) + '.jsonl'}):
                    raise ValueError('Downloaded attestation bundle does not match the subject digest.')
                shutil.copyfile(files[0], assets / (name + '.sigstore.jsonl'))
        results = _verify_provenance(folder, assets, source)
    _write_json(assets / RECEIPT, {'schema': 1, 'source': source})
    _write_json(assets / VERIFICATION, results)
    (assets / RELEASE_MANIFEST).write_text(_manifest(assets), encoding='ascii')
    verify_candidate(assets, **identity)
    return assets


def verify_candidate(assets, **identity):
    identity = _identity(**identity)
    assets = Path(assets)
    if ({path.name for path in assets.iterdir()} != set(ASSETS) | {RELEASE_MANIFEST}
            or any(path.is_symlink() or not path.is_file() for path in assets.iterdir())):
        raise ValueError('Release candidate differs from its exact retained asset allowlist.')
    if (assets / RELEASE_MANIFEST).read_text(encoding='ascii') != _manifest(assets):
        raise ValueError('Release candidate checksum manifest does not match retained assets.')
    receipt = _json(assets / RECEIPT)
    source = receipt.get('source', {})
    if (receipt.get('schema') != 1 or type(receipt.get('schema')) is not int
            or set(source) != set(identity) | {'artifact_name', 'artifact_digest', 'artifact_size'}
            or any(source.get(key) != value for key, value in identity.items())
            or source.get('artifact_name') != _artifact_name(identity['commit'], identity['python_version'], identity['run_attempt'])):
        raise ValueError('Release receipt does not bind the selected repository/run/attempt/commit/artifact.')
    with tempfile.TemporaryDirectory(prefix='spt-release-verify-') as temporary:
        folder = Path(temporary) / 'payload'
        extract_verified_archive(assets / ARCHIVE, folder,
                                 digest=source['artifact_digest'], size=source['artifact_size'])
        verify_payload(folder, source)
        # Retained verification JSON is explanatory evidence, never a substitute
        # for verifying the actual signatures again against the expected identity.
        _verify_provenance(folder, assets, source)
    return source


def _tag(value):
    if (not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,79}', value)
            or '..' in value or value.endswith(('.', '.lock'))):
        raise ValueError('Release tag must be a bounded literal tag without path or shell syntax.')
    return value


def _release_identity(release, *, tag, commit, draft, release_id=None):
    if (not isinstance(release, dict) or release.get('tag_name') != tag
            or release.get('target_commitish') != commit or release.get('draft') is not draft
            or type(release.get('id')) is not int or release['id'] < 1
            or (release_id is not None and release['id'] != release_id)):
        raise ValueError('Release identity or publication state does not match.')
    return release['id']


def _release_assets(repository, release, destination, *, tag, commit, draft, release_id=None):
    _release_identity(release, tag=tag, commit=commit, draft=draft, release_id=release_id)
    entries = release.get('assets', [])
    if (len(entries) != len(ASSETS) + 1
            or {entry.get('name') for entry in entries} != set(ASSETS) | {RELEASE_MANIFEST}):
        raise ValueError('Release assets are missing, duplicated or outside the exact allowlist.')
    destination.mkdir(parents=True, exist_ok=False)
    for entry in entries:
        _positive(entry.get('id'))
        path = destination / entry['name']
        _download(f'repos/{repository}/releases/assets/{entry["id"]}', path)
        _verify_bytes(path, entry.get('digest'), entry.get('size'))


def _verify_tag(repository, tag, commit):
    ref = _api(f'repos/{repository}/git/ref/tags/{quote(tag, safe="")}')
    obj = ref.get('object', {}) if isinstance(ref, dict) else {}
    if not isinstance(obj, dict) or obj.get('type') != 'commit' or obj.get('sha') != commit:
        raise ValueError('Release tag no longer points directly to the verified source commit.')


def restore_release(output, tag, **identity):
    """Read retained release assets even after the Actions archive has expired."""
    identity = _identity(**identity)
    tag = _tag(tag)
    repository = identity['repository']
    release = _api(f'repos/{repository}/releases/tags/{quote(tag, safe="")}')
    _verify_tag(repository, tag, identity['commit'])
    assets = Path(output) / 'assets'
    _release_assets(repository, release, assets, tag=tag, commit=identity['commit'], draft=False)
    verify_candidate(assets, **identity)
    return assets


def publish(assets, tag, **identity):
    identity = _identity(**identity)
    repository = identity['repository']
    if (os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch'
            or os.environ.get('GITHUB_REF') != 'refs/heads/main'
            or os.environ.get('GITHUB_REPOSITORY') != repository):
        raise ValueError('Publishing requires the explicit trusted-main dispatch job.')
    tag = _tag(tag)
    source = verify_candidate(assets, **identity)
    assets = Path(assets).resolve()
    if (_api(f'repos/{repository}/releases/tags/{quote(tag, safe="")}', missing=True) is not None
            or _api(f'repos/{repository}/git/ref/tags/{quote(tag, safe="")}', missing=True) is not None):
        raise ValueError('Refusing to overwrite an existing release or tag.')
    # The atomic create-only ref request closes the tag-name race. No force
    # update, clobber, deletion, or retry of a partially created release is used.
    _write_api('POST', f'repos/{repository}/git/refs',
               {'ref': 'refs/tags/' + tag, 'sha': source['commit']})
    notes = (
        f'Exact verified Windows distribution from `{source["commit"]}`.\n\n'
        f'Source run {source["run_id"]}, attempt {source["run_attempt"]}, '
        f'artifact {source["artifact_id"]}, Python {source["python_version"]}.\n\n'
        'Original artifact ZIP, build identity, SBOM, checksum manifests and signed provenance '
        'are retained for verification and rollback. This is synthetic CI evidence; '
        'it does not claim a Windows publisher signature or real-account acceptance.\n')
    created = _write_api('POST', f'repos/{repository}/releases', {
        'tag_name': tag, 'target_commitish': source['commit'], 'name': 'SPT Downloader ' + tag,
        'body': notes, 'draft': True, 'prerelease': False, 'make_latest': 'false',
    })
    release_id = _release_identity(created, tag=tag, commit=source['commit'], draft=True)
    if created.get('assets') != []:
        raise ValueError('A new release draft must not contain unexpected existing assets.')
    endpoint = f'repos/{repository}/releases/{release_id}'
    # GET /releases/tags/{tag} only retrieves published releases. Keep the
    # numeric ID returned by creation for every upload, readback and mutation.
    for name in (*ASSETS, RELEASE_MANIFEST):
        path = assets / name
        upload_url = f'https://uploads.github.com/{endpoint}/assets?name={quote(name, safe="")}'
        uploaded = json.loads(_command([
            'gh', 'api', '--method', 'POST', upload_url,
            '-H', 'Content-Type: application/octet-stream',
            '-H', 'Accept: application/vnd.github+json', '--input', str(path),
        ]))
        if not isinstance(uploaded, dict) or uploaded.get('name') != name:
            raise ValueError('Uploaded release asset identity does not match the candidate.')
        _positive(uploaded.get('id'))
        _verify_bytes(path, uploaded.get('digest'), uploaded.get('size'))
    with tempfile.TemporaryDirectory(prefix='spt-publish-') as temporary:
        release = _api(endpoint)
        readback = Path(temporary) / 'readback'
        _release_assets(repository, release, readback, tag=tag, commit=source['commit'],
                        draft=True, release_id=release_id)
        for name in (*ASSETS, RELEASE_MANIFEST):
            if _hash(readback / name) != _hash(assets / name):
                raise ValueError('Draft release readback differs from the verified candidate.')
        verify_candidate(readback, **identity)
        # A tag can be moved while assets upload or signatures are verified.
        # Check its direct commit immediately before making this draft public.
        _verify_tag(repository, tag, source['commit'])
        published = _write_api('PATCH', endpoint, {'draft': False, 'make_latest': 'true'})
        _release_identity(published, tag=tag, commit=source['commit'],
                          draft=False, release_id=release_id)
        final = _api(endpoint)
        final_readback = Path(temporary) / 'published'
        _release_assets(repository, final, final_readback, tag=tag, commit=source['commit'],
                        draft=False, release_id=release_id)
        for name in (*ASSETS, RELEASE_MANIFEST):
            if _hash(final_readback / name) != _hash(assets / name):
                raise ValueError('Published release bytes changed after draft verification.')
        _verify_tag(repository, tag, source['commit'])
    return final['html_url']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'verify', 'publish'))
    parser.add_argument('--repository', required=True)
    parser.add_argument('--run-id', required=True, type=int)
    parser.add_argument('--run-attempt', required=True, type=int)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--artifact-id', required=True, type=int)
    parser.add_argument('--python-version', required=True,
                        help='Exact source build Python version, including for retained releases.')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--rollback-tag', default='')
    args = parser.parse_args(argv)
    _tag(args.tag)
    identity = {key: getattr(args, key) for key in
                ('repository', 'run_id', 'run_attempt', 'commit', 'artifact_id', 'python_version')}
    if args.command == 'prepare':
        if args.rollback_tag:
            restore_release(args.output, args.rollback_tag, **identity)
        else:
            prepare(args.output, **identity)
        print('Verified release candidate. No release or tag was published.')
    elif args.command == 'verify':
        verify_candidate(args.output / 'assets', **identity)
        print('Reverified retained release bytes, source identity and signed provenance.')
    else:
        print(publish(args.output / 'assets', args.tag, **identity))


if __name__ == '__main__':
    main()
