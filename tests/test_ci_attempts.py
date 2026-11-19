"""Synthetic, offline replay of GitHub Actions per-producer partial rerun records."""
from copy import deepcopy

import pytest

from scripts import ci_attempts, ci_tests
from test_ci_sharding import production_evidence, VERSION, COMMIT, RUN_ID


REPO = 'example/synthetic'
HEAD = 'b' * 40
STARTS = ['2026-11-18T11:00:00Z', '2026-11-18T12:00:00Z',
          '2026-11-18T13:00:00Z']


def fake_run(mode='four-shards', attempts=1, rerun=()):
    """Rerun entries: tuples of (attempt, slot) actually launched that attempt."""
    rerun = set(rerun)
    slots = ci_attempts.slots(mode)
    jobs = {}
    artifacts = []
    last_run = {slot: 1 for slot in slots}
    for attempt in range(1, attempts + 1):
        rows = []
        for index, slot in enumerate(slots):
            executed = attempt == 1 or (attempt, slot) in rerun
            if executed:
                last_run[slot] = attempt
                names = ci_attempts._names(slot, VERSION, COMMIT, attempt)
                for kind, name in names.items():
                    artifacts.append({
                        'name': name, 'id': attempt * 100 + index * 2 + (kind == 'coverage') + 1,
                        'size_in_bytes': 100, 'digest': 'sha256:' + 'c' * 64,
                        'expired': False,
                        'workflow_run': {'id': int(RUN_ID), 'head_sha': HEAD},
                    })
            name = (f'Portable tests (Python {VERSION})' if slot == 'portable'
                    else f'Windows integration (Python {VERSION}, {slot})')
            rows.append({
                'id': attempt * 100 + index + 1, 'name': name,
                'head_sha': HEAD, 'run_attempt': attempt,
                'status': 'completed', 'conclusion': 'success',
                'started_at': STARTS[last_run[slot] - 1].replace('11:00:', '11:01:') if
                              last_run[slot] == 1 else STARTS[last_run[slot] - 1].replace('00:00Z', '01:00Z'),
            })
        jobs[attempt] = rows

    def fetch(path):
        if '/artifacts?' in path:
            return {'total_count': len(artifacts), 'artifacts': artifacts}
        if '/jobs?' in path:
            number = int(path.split('/attempts/')[1].split('/')[0])
            return {'total_count': len(jobs[number]), 'jobs': jobs[number]}
        if '/attempts/' in path:
            number = int(path.rsplit('/', 1)[1])
            return {'id': int(RUN_ID), 'run_attempt': number, 'head_sha': HEAD,
                    'created_at': STARTS[number - 1]}
        raise AssertionError(path)

    return fetch, jobs, artifacts


def resolve(fetch, *, mode='four-shards', attempts=1):
    return ci_attempts.select(
        fetch, repo=REPO, run_id=int(RUN_ID), sha=COMMIT, head_sha=HEAD,
        current_attempt=attempts, python=VERSION, mode=mode)


@pytest.mark.parametrize('mode', ['serial', 'two-shards', 'four-shards'])
def test_original_full_run_uses_only_attempt_one(mode):
    fetch, _, _ = fake_run(mode)
    result = resolve(fetch, mode=mode)
    assert set(result['producers']) == set(ci_attempts.slots(mode))
    assert set(ci_attempts.validated_attempts(
        result, commit=COMMIT, run_id=RUN_ID, run_attempt='1',
        python=VERSION, mode=mode).values()) == {'1'}


def test_one_shard_partial_rerun_selects_original_successes_and_new_success():
    fetch, _, _ = fake_run(attempts=2, rerun={(2, 'shard-1')})
    result = resolve(fetch, attempts=2)
    selected = ci_attempts.validated_attempts(
        result, commit=COMMIT, run_id=RUN_ID, run_attempt='2',
        python=VERSION, mode='four-shards')
    assert selected == {'portable': '1', 'shard-0': '1', 'shard-1': '2',
                        'shard-2': '1', 'shard-3': '1'}
    assert result['producers']['shard-1']['artifacts']['coverage']['name'].endswith('-attempt2')
    assert result['producers']['portable']['artifacts']['inventory']['name'].endswith('-attempt1')


def test_package_retry_on_third_attempt_keeps_each_original_producer():
    fetch, _, _ = fake_run(attempts=3, rerun={(2, 'shard-1')})
    result = resolve(fetch, attempts=3)
    assert {k: v['attempt'] for k, v in result['producers'].items()} == {
        'portable': 1, 'shard-0': 1, 'shard-1': 2, 'shard-2': 1, 'shard-3': 1}


@pytest.mark.parametrize('mutation', [
    'failed-rerun', 'missing-rerun-artifact', 'expired', 'wrong-head',
    'missing-digest', 'missing-shard', 'duplicate-artifact', 'zero-size',
])
def test_invalid_producer_or_artifact_fails_closed(mutation):
    fetch, jobs, artifacts = fake_run(attempts=2, rerun={(2, 'shard-1')})
    if mutation == 'failed-rerun':
        jobs[2][2]['conclusion'] = 'failure'
    elif mutation == 'missing-rerun-artifact':
        artifacts[:] = [a for a in artifacts if 'windows-coverage-shard-1' not in a['name']
                        or not a['name'].endswith('-attempt2')]
    elif mutation == 'expired':
        artifacts[0]['expired'] = True
    elif mutation == 'wrong-head':
        artifacts[0]['workflow_run']['head_sha'] = 'f' * 40
    elif mutation == 'missing-digest':
        artifacts[0]['digest'] = ''
    elif mutation == 'missing-shard':
        jobs[1].pop()
    elif mutation == 'duplicate-artifact':
        artifacts.append(deepcopy(artifacts[0]))
    elif mutation == 'zero-size':
        artifacts[0]['size_in_bytes'] = 0
    with pytest.raises(ValueError):
        resolve(fetch, attempts=2)


@pytest.mark.parametrize('mutation', ['current-attempt', 'run-id', 'commit', 'slot',
                                       'artifact-id', 'digest', 'older-attempt', 'extra-key'])
def test_provenance_manifest_rejects_any_tampering(mutation):
    fetch, _, _ = fake_run(attempts=2, rerun={(2, 'shard-1')})
    result = resolve(fetch, attempts=2)
    if mutation == 'current-attempt':
        result['current_attempt'] = 3
    elif mutation == 'run-id':
        result['run_id'] += 1
    elif mutation == 'commit':
        result['commit'] = 'f' * 40
    elif mutation == 'slot':
        result['producers'].pop('shard-2')
    elif mutation == 'artifact-id':
        result['producers']['shard-0']['artifacts']['coverage']['id'] = 0
    elif mutation == 'digest':
        result['producers']['portable']['artifacts']['inventory']['digest'] = ''
    elif mutation == 'older-attempt':
        result['producers']['shard-1']['attempt'] = 1
    else:
        result['unreviewed'] = True
    with pytest.raises(ValueError):
        ci_attempts.validated_attempts(
            result, commit=COMMIT, run_id=RUN_ID, run_attempt='2',
            python=VERSION, mode='four-shards')


def test_mixed_producer_attempts_still_verify_original_test_outcomes_and_partition():
    portable, _, shards = production_evidence()
    # The chosen producer artifact is immutable; its internal attempt must match
    # its own producer, not the downstream package retry attempt.
    portable['run_attempt'] = '1'
    shards[0]['run_attempt'] = '1'
    shards[1]['run_attempt'] = '2'
    assert ci_tests.check_inventories(portable, shards, VERSION, COMMIT,
        run_id=RUN_ID, run_attempt='2',
        attempt_map={'portable': '1', 'shard-0': '1', 'shard-1': '2'}) == 15
    shards[1]['run_attempt'] = '1'
    with pytest.raises(ValueError, match='runner|run'):
        ci_tests.check_inventories(portable, shards, VERSION, COMMIT,
            run_id=RUN_ID, run_attempt='2',
            attempt_map={'portable': '1', 'shard-0': '1', 'shard-1': '2'})
