"""Resolve immutable GitHub Actions artifacts from the actual successful producer attempt.

GitHub's per-attempt job API also repeats successful *unchanged* jobs on partial
reruns with a new run_attempt. An unchanged job retains its original started_at,
so only a job started at/after that attempt's created_at is a real producer.
Never use a failed rerun's older artifact or fall back to another run/commit.
"""
import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
from urllib.request import Request, urlopen


_SHA = re.compile(r'[a-f0-9]{40}\Z')
_REPO = re.compile(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z')
_DIGEST = re.compile(r'sha256:[a-f0-9]{64}\Z')
_SLOT_MODES = {
    'serial': ('serial',),
    'two-shards': ('shard-0', 'shard-1'),
    'four-shards': ('shard-0', 'shard-1', 'shard-2', 'shard-3'),
}


def slots(mode):
    try:
        return ('portable', *_SLOT_MODES[mode])
    except KeyError as error:
        raise ValueError('Unknown Windows mode') from error


def _positive(value):
    return type(value) is int and value > 0


def _time(value):
    if not isinstance(value, str) or not value.endswith('Z'):
        raise ValueError('Missing UTC job or attempt timestamp')
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise ValueError('Invalid UTC job or attempt timestamp') from error


def _items(fetch, path, key):
    found = []
    for page in range(1, 11):
        response = fetch(f'{path}&per_page=100&page={page}')
        total, batch = response.get('total_count'), response.get(key)
        if type(total) is not int or total < 0 or not isinstance(batch, list):
            raise ValueError('Malformed Actions index')
        if total > 1000 or len(batch) > 100 or total < len(found) + len(batch):
            raise ValueError('Unbounded or inconsistent Actions index')
        found.extend(batch)
        if len(found) == total:
            return found
        if len(batch) != 100:
            raise ValueError('Incomplete Actions index')
    raise ValueError('Actions index exceeded reviewed pagination bound')


def _names(slot, python, sha, attempt):
    stem = f'python{python}-{sha}-attempt{attempt}'
    if slot == 'portable':
        return {'inventory': f'test-inventory-portable-{stem}'}
    return {
        'inventory': f'test-inventory-windows-{slot}-{stem}',
        'coverage': f'windows-coverage-{slot}-{stem}',
    }


def select(fetch, *, repo, run_id, sha, head_sha, current_attempt, python, mode):
    """Read-only selection from the current run's original per-attempt jobs."""
    if (not _REPO.fullmatch(repo) or not _SHA.fullmatch(sha)
            or not _SHA.fullmatch(head_sha) or not _positive(run_id)
            or not _positive(current_attempt)
            or not re.fullmatch(r'3\.14\.[0-9]+', python)):
        raise ValueError('Invalid immutable Actions identity')
    expected = slots(mode)
    artifacts = _items(fetch, f'repos/{repo}/actions/runs/{run_id}/artifacts?', 'artifacts')
    by_name = {}
    for item in artifacts:
        name = item.get('name')
        if not isinstance(name, str):
            raise ValueError('Unnamed Actions artifact')
        if name in by_name:
            raise ValueError('Ambiguous duplicate artifact name')
        by_name[name] = item

    chosen = {}
    for attempt in range(current_attempt, 0, -1):
        metadata = fetch(f'repos/{repo}/actions/runs/{run_id}/attempts/{attempt}')
        if (metadata.get('id') != run_id or metadata.get('run_attempt') != attempt
                or metadata.get('head_sha') != head_sha):
            raise ValueError('Attempt belongs to a different run or source')
        began = _time(metadata.get('created_at'))
        jobs = _items(fetch, f'repos/{repo}/actions/runs/{run_id}/attempts/{attempt}/jobs?', 'jobs')
        for slot in expected:
            if slot in chosen:
                continue
            name = (f'Portable tests (Python {python})' if slot == 'portable'
                    else f'Windows integration (Python {python}, {slot})')
            matches = [job for job in jobs if job.get('name') == name]
            if len(matches) != 1:
                raise ValueError('Missing or duplicate producer job: ' + slot)
            job = matches[0]
            if (job.get('head_sha') != head_sha
                    or job.get('run_attempt') != attempt or not _positive(job.get('id'))
                    or job.get('status') != 'completed' or job.get('conclusion') != 'success'):
                raise ValueError('Producer not successful on latest attempt: ' + slot)
            if _time(job.get('started_at')) < began:
                # This is a UI/API replay of a job from an earlier attempt.
                continue
            named = _names(slot, python, sha, attempt)
            checked = {}
            for kind, artifact_name in named.items():
                item = by_name.get(artifact_name)
                if (not item or not _positive(item.get('id'))
                        or not _positive(item.get('size_in_bytes'))
                        or item.get('expired') is not False
                        or not isinstance(item.get('digest'), str)
                        or not _DIGEST.fullmatch(item['digest'])
                        or not isinstance(item.get('workflow_run'), dict)
                        or item['workflow_run'].get('id') != run_id
                        or item['workflow_run'].get('head_sha') != head_sha):
                    raise ValueError('Missing or invalid exact producer artifact: ' + artifact_name)
                checked[kind] = {
                    'name': artifact_name, 'id': item['id'],
                    'size': item['size_in_bytes'], 'digest': item['digest'],
                }
            chosen[slot] = {'attempt': attempt, 'job_id': job['id'],
                            'artifacts': checked}
        if len(chosen) == len(expected):
            break
    if set(chosen) != set(expected):
        raise ValueError('No valid successful producer for every required slot')
    return {
        'schema': 1, 'repository': repo, 'run_id': run_id, 'commit': sha,
        'head_sha': head_sha, 'current_attempt': current_attempt,
        'python': python, 'mode': mode, 'producers': chosen,
    }


def validated_attempts(data, *, commit, run_id, run_attempt, python, mode):
    """Fail closed on a missing/altered producer coordinate manifest."""
    if (not isinstance(data, dict)
            or set(data) != {'schema', 'repository', 'run_id', 'commit', 'head_sha',
                             'current_attempt', 'python', 'mode', 'producers'}
            or type(data['schema']) is not int or data['schema'] != 1
            or not isinstance(data['repository'], str)
            or not _REPO.fullmatch(data['repository'])
            or data['commit'] != commit or not _SHA.fullmatch(commit)
            or not _SHA.fullmatch(data['head_sha'])
            or str(data['run_id']) != run_id or not _positive(data['run_id'])
            or str(data['current_attempt']) != run_attempt
            or not _positive(data['current_attempt'])
            or data['python'] != python or data['mode'] != mode):
        raise ValueError('Producer manifest identity mismatch')
    if not isinstance(data['producers'], dict) or set(data['producers']) != set(slots(mode)):
        raise ValueError('Producer manifest does not cover the execution plan')
    result = {}
    seen = set()
    for slot in slots(mode):
        producer = data['producers'][slot]
        if not isinstance(producer, dict) or set(producer) != {'attempt', 'job_id', 'artifacts'}:
            raise ValueError('Malformed producer manifest')
        attempt = producer['attempt']
        if (not _positive(attempt) or attempt > data['current_attempt']
                or not _positive(producer['job_id'])):
            raise ValueError('Invalid selected producer attempt')
        artifacts = producer['artifacts']
        if not isinstance(artifacts, dict) or set(artifacts) != set(_names(slot, python, commit, attempt)):
            raise ValueError('Producer artifact set mismatch')
        for kind, name in _names(slot, python, commit, attempt).items():
            obj = artifacts[kind]
            if (not isinstance(obj, dict) or set(obj) != {'name', 'id', 'size', 'digest'}
                    or obj['name'] != name or not _positive(obj['id'])
                    or not _positive(obj['size']) or not isinstance(obj['digest'], str)
                    or not _DIGEST.fullmatch(obj['digest']) or obj['id'] in seen):
                raise ValueError('Invalid artifact provenance in producer manifest')
            seen.add(obj['id'])
        result[slot] = str(attempt)
    return result


def _api(repo, token):
    from urllib.parse import quote
    def fetch(path):
        url = 'https://api.github.com/' + path
        req = Request(url, headers={
            'Authorization': 'Bearer ' + token,
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
            'User-Agent': 'spt-downloader-ci-attempt-resolver',
        })
        with urlopen(req, timeout=20) as stream:
            raw = stream.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('Actions API response too large')
        obj = json.loads(raw)
        if not isinstance(obj, dict):
            raise ValueError('Actions API response is not an object')
        return obj
    return fetch


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--run-id', type=int, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--head-sha', required=True)
    parser.add_argument('--current-attempt', type=int, required=True)
    parser.add_argument('--python-version', required=True)
    parser.add_argument('--mode', choices=tuple(_SLOT_MODES), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--github-output', type=Path, required=True)
    args = parser.parse_args(argv)
    token = os.environ.get('GH_TOKEN', '')
    if not token:
        raise ValueError('GitHub token required for this run-scoped read')
    manifest = select(_api(args.repository, token), repo=args.repository,
                      run_id=args.run_id, sha=args.commit, head_sha=args.head_sha,
                      current_attempt=args.current_attempt, python=args.python_version,
                      mode=args.mode)
    validated_attempts(manifest, commit=args.commit, run_id=str(args.run_id),
                       run_attempt=str(args.current_attempt), python=args.python_version,
                       mode=args.mode)
    if args.output.is_symlink() or args.github_output.is_symlink():
        raise ValueError('Refusing linked Actions output path')
    args.output.write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    with args.github_output.open('a', encoding='utf-8') as stream:
        for slot in slots(args.mode):
            for kind, item in manifest['producers'][slot]['artifacts'].items():
                stream.write(f"{slot.replace('-', '_')}_{kind}={item['name']}\n")
    print('Resolved exact producer attempts: ' +
          ', '.join(f"{s}={manifest['producers'][s]['attempt']}" for s in slots(args.mode)))


if __name__ == '__main__':
    main()
