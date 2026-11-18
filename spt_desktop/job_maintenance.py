"""Private, bounded job inventory and separately authorized incomplete-job removal.

Automatic pruning stays in job_pruning: it may remove only sealed COMPLETE jobs.
The manual path never interprets a terminal event as verified publication.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import time
import uuid

from . import job_pruning as pruning
from .output_windows import DirectoryGuard
from .profile_lifecycle import _remove_tree

TERMINAL = '.spt-terminal-v1.json'
_FAILURES = frozenset({'ERROR', 'BLOCKED', 'CANCELLED'})


def record_terminal_status(root, job_id, status):
    """Record only safe, non-COMPLETE terminal metadata for future inventory."""
    if (not pruning._JOB.fullmatch(job_id or '') or status not in
            ('PARTIAL', 'ERROR', 'BLOCKED', 'CANCELLED')):
        return False
    job = Path(root).absolute() / 'jobs' / job_id
    temporary = None
    created = False
    try:
        with DirectoryGuard() as guard:
            guard.include(pruning._checked_ancestors(job))
            if (job / pruning.SEAL).exists() or (job / TERMINAL).exists():
                return False
            temporary = job / (TERMINAL + '.' + uuid.uuid4().hex + '.tmp')
            with temporary.open('x', encoding='utf-8') as stream:
                created = True
                json.dump({'schema': 1, 'job_id': job_id, 'status': status}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(job / TERMINAL)
        return True
    except (OSError, ValueError):
        return False
    finally:
        if created:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                # The best-effort marker cleanup cannot change terminal status.
                # A leftover file remains in private storage for later review.
                pass


def _job_directories(root):
    jobs = Path(root).absolute() / 'jobs'
    if not jobs.is_dir():
        return [], False
    pruning._checked_ancestors(jobs)
    with os.scandir(jobs) as scan:
        entries = list(scan)
    if len(entries) > 4096:
        raise ValueError('Job inventory exceeds the safety bound')
    recovery = any(entry.name.startswith('.spt-publish-') for entry in entries)
    found = []
    for entry in entries:
        if pruning._JOB.fullmatch(entry.name):
            path = jobs / entry.name
            info = pruning._plain(path, directory=True)
            found.append((info.st_mtime_ns, entry.name, path))
    found.sort(reverse=True)
    return found, recovery


def _terminal_status(job, deadline):
    path = job / TERMINAL
    try:
        data, _ = pruning._read_json_fingerprinted(path, max_bytes=2048,
                                                   deadline=deadline)
    except FileNotFoundError:
        return None
    if (not isinstance(data, dict) or set(data) != {'schema', 'job_id', 'status'}
            or data['schema'] != 1 or data['job_id'] != job.name
            or data['status'] not in ('PARTIAL', 'ERROR', 'BLOCKED', 'CANCELLED')):
        raise ValueError('Invalid terminal job marker')
    return data['status']


def _classification(job, deadline):
    """Unknown evidence is protected, not assumed to be a failed job."""
    terminal = _terminal_status(job, deadline)
    try:
        run, _ = pruning._read_json_fingerprinted(
            job / 'run.json', max_bytes=16 * 1024 * 1024, deadline=deadline)
    except FileNotFoundError:
        run = None
    if run is not None and not isinstance(run, dict):
        raise ValueError('Invalid run record')
    if run is not None and run.get('complete') is True:
        return 'COMPLETE'
    if run is not None and run.get('complete') is False:
        return 'FAILED' if terminal in _FAILURES else 'PARTIAL'
    if terminal in _FAILURES:
        return 'FAILED'
    return 'PROTECTED'


def _has_recovery(job):
    return any(child.name.startswith('publication-recovery-') for child in job.iterdir())


def _snapshot_digest(job, inventory):
    """Bind an approval to actual native objects, not just matching file bytes."""
    info = pruning._plain(job, directory=True)
    digest = hashlib.sha256()
    digest.update(json.dumps(
        [info.st_dev, info.st_ino, info.st_mtime_ns],
        separators=(',', ':')).encode('ascii'))
    for name, fingerprint in sorted(inventory.items()):
        digest.update(json.dumps(
            [name, fingerprint], separators=(',', ':'), ensure_ascii=True
        ).encode('utf-8'))
    return digest.hexdigest()


def inspect_job_storage(root, keep=pruning.DEFAULT_KEEP_JOBS, *, active_id=None):
    """Read-only dashboard and authorization snapshot. Never follows links.

    protected overlaps status counts: every unfinished/unknown job and every
    retained newest-N job is protected *from automatic pruning*.
    """
    pruning.validate_keep_jobs(keep)
    result = {'total': 0, 'complete': 0, 'partial': 0, 'failed': 0,
              'protected': 0, 'estimated_bytes': 0, 'scan_complete': True,
              'removable': ()}
    if not pruning._windows():
        return result
    with pruning._PRUNE_LOCK:
        try:
            entries, recovery = _job_directories(root)
        except (OSError, ValueError):
            result['scan_complete'] = False
            return result
        result['total'] = len(entries)
        authorized = []
        global_deadline = time.monotonic() + 120
        for index, (modified_ns, job_id, job) in enumerate(entries):
            if time.monotonic() >= global_deadline:
                result['scan_complete'] = False
                result['protected'] += len(entries) - index
                break
            try:
                deadline = min(time.monotonic() + 60, global_deadline)
                with DirectoryGuard() as guard:
                    guard.include(pruning._checked_ancestors(job))
                    status = _classification(job, deadline)
                    inventory = {}
                    count, _, bytes_used = pruning._tree_digest(
                        job, deadline=deadline, include_bytes=True,
                        inventory=inventory)
                    sealed = (job / pruning.SEAL).exists()
                    if sealed:
                        bytes_used += pruning._plain(job / pruning.SEAL).st_size
                    flagged = _has_recovery(job)
                result['estimated_bytes'] += bytes_used
                if status != 'PROTECTED':
                    result[status.lower()] += 1
                if (status != 'COMPLETE' or index < keep or flagged or recovery
                        or job_id == active_id or not sealed or keep == 0):
                    result['protected'] += 1
                if (status in ('PARTIAL', 'FAILED') and (job / TERMINAL).is_file()
                        and not flagged and not recovery and not sealed
                        and job_id != active_id):
                    authorized.append({'id': job_id, 'status': status,
                                       'bytes': bytes_used,
                                       'digest': _snapshot_digest(job, inventory),
                                       'modified_ns': modified_ns})
            except (OSError, ValueError, TypeError, KeyError, RecursionError,
                    TimeoutError, UnicodeError):
                result['scan_complete'] = False
                result['protected'] += 1
        result['removable'] = tuple(authorized) if result['scan_complete'] else ()
        return result


def delete_incomplete_jobs(root, approvals, *, active_id=None):
    """Delete only inspected, explicitly selected incomplete job snapshots.

    approvals: tuple of (32-hex job_id, 64-hex snapshot hash). This is not a
    generic arbitrary-directory cleaner. Output Downloads is never consulted.
    """
    if (not isinstance(approvals, tuple) or len(approvals) > 4096
            or any(not isinstance(pair, tuple) or len(pair) != 2
                   or type(pair[0]) is not str or not pruning._JOB.fullmatch(pair[0])
                   or type(pair[1]) is not str
                   or not re.fullmatch('[0-9a-f]{64}', pair[1])
                   for pair in approvals)
            or len(set(approvals)) != len(approvals)
            or len({item[0] for item in approvals}) != len(approvals)):
        raise ValueError('Invalid manually approved job snapshots')
    if not pruning._windows() or not approvals:
        return {'removed': 0, 'incomplete': bool(approvals)}
    removed, incomplete = 0, False
    with pruning._PRUNE_LOCK:
        try:
            entries, global_recovery = _job_directories(root)
            if global_recovery:
                return {'removed': 0, 'incomplete': True}
            known = {job_id: job for _, job_id, job in entries}
            deadline_global = time.monotonic() + 120
            for job_id, approved_digest in approvals:
                if time.monotonic() >= deadline_global:
                    incomplete = True
                    break
                if job_id == active_id or job_id not in known:
                    incomplete = True
                    continue
                job = known[job_id]
                try:
                    deadline = min(time.monotonic() + 60, deadline_global)
                    with DirectoryGuard() as guard:
                        expected = pruning._checked_ancestors(job)
                        guard.include(expected)
                        if ((job / pruning.SEAL).exists() or _has_recovery(job)
                                or _terminal_status(job, deadline) is None
                                or _classification(job, deadline) not in
                                ('PARTIAL', 'FAILED')):
                            incomplete = True
                            continue
                        # Recovery may have begun since the selection screen.
                        _, recovery = _job_directories(root)
                        if recovery:
                            incomplete = True
                            continue
                        inventory = {}
                        pruning._tree_digest(
                            job, deadline=deadline, inventory=inventory)
                        if _snapshot_digest(job, inventory) != approved_digest:
                            incomplete = True
                            continue
                        _remove_tree(job, expected[job], guard, expected, deadline,
                                     verified_inventory=inventory)
                        removed += 1
                except (OSError, ValueError, TypeError, KeyError, RecursionError,
                        TimeoutError, UnicodeError):
                    incomplete = True
        except (OSError, ValueError, TypeError):
            incomplete = True
    return {'removed': removed, 'incomplete': incomplete or removed != len(approvals)}
