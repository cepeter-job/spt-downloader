"""Bounded pruning of *sealed*, successfully published desktop job workspaces.

A completed export's private capture is not the published output.  Old jobs
without a new-version seal, incomplete jobs and recovery material are retained.
Never infer deletion rights from age, folder name, or run['complete'] alone.
"""
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import threading
import time

from .output_windows import DirectoryGuard, locked_file
from .profile_lifecycle import _identity, _ordinary

DEFAULT_KEEP_JOBS = 10
MAX_KEEP_JOBS = 100
SEAL = '.spt-published-prune-v1.json'
_JOB = re.compile(r'[0-9a-f]{32}')
_LIMIT = 16384
_MAX_SEAL_BYTES = 128 * 1024
_PRUNE_LOCK = threading.Lock()  # Serialize automatic and manual housekeeping.


def validate_keep_jobs(value):
    """0 disables automatic pruning; positive counts retain newest N runs."""
    if type(value) is not int or not 0 <= value <= MAX_KEEP_JOBS:
        raise ValueError('Retensi job harus bilangan bulat 0 sampai 100 (0 = nonaktif).')
    return value


def _windows():
    return sys.platform == 'win32'


def _plain(path, *, directory=False):
    info = path.lstat()
    if not _ordinary(info, directory=directory):
        raise ValueError('Job pruning refuses redirected, shared or unknown entries')
    return info


def _checked_ancestors(path):
    """Reject junctions/reparse points throughout the owned workspace chain."""
    wanted = {}
    for parent in reversed((path, *path.parents)):
        info = _plain(parent, directory=True)
        wanted[parent] = _identity(info)
    return wanted


def _read_json(path, *, max_bytes=_MAX_SEAL_BYTES):
    if _plain(path).st_size > max_bytes:
        raise ValueError('Job pruning metadata exceeds its bound')
    return json.loads(path.read_text(encoding='utf-8'))


def _check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('Job verification budget exceeded')


def _hash_file(path, *, deadline=None):
    _check_deadline(deadline)
    initial = _plain(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if _identity(opened) != _identity(initial) or opened.st_size != initial.st_size:
            raise ValueError('Job file changed during verification')
        while True:
            _check_deadline(deadline)
            piece = stream.read(1024 * 1024)
            _check_deadline(deadline)
            if not piece:
                break
            digest.update(piece)
        after = os.fstat(stream.fileno())
    current = _plain(path)
    if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
            or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
            != (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)):
        raise ValueError('Job file changed during verification')
    _check_deadline(deadline)
    return initial.st_size, digest.hexdigest()


def _hash_held_output(stream, *, deadline=None):
    """Hash the exact file held under Windows deny-write/delete custody.

    The caller retains the stream (and its guarded path ancestors) until the
    private job has been removed or the deletion has been refused.  A second
    by-path open would not carry this guarantee.
    """
    info = os.fstat(stream.fileno())
    if not _ordinary(info):
        raise ValueError('Published output is not an ordinary unique file')
    digest = hashlib.sha256()
    while True:
        _check_deadline(deadline)
        piece = stream.read(1024 * 1024)
        _check_deadline(deadline)
        if not piece:
            break
        digest.update(piece)
    after = os.fstat(stream.fileno())
    if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns)):
        raise ValueError('Published output changed under custody')
    _check_deadline(deadline)
    return [info.st_size, digest.hexdigest()]


def _tree_digest(job, *, deadline, include_bytes=False):
    """Hash bounded relative inventory and actual bytes; never follow links."""
    h = hashlib.sha256()
    count = 0
    total_bytes = 0
    stack = [job]
    while stack:
        _check_deadline(deadline)
        folder = stack.pop()
        _plain(folder, directory=True)
        with os.scandir(folder) as entries:
            children = sorted(entries, key=lambda item: item.name)
        for entry in children:
            if time.monotonic() >= deadline:
                raise TimeoutError('Job inventory verification exceeded the budget')
            path = folder / entry.name
            if path == job / SEAL:
                continue
            rel = path.relative_to(job).as_posix()
            info = path.lstat()
            count += 1
            if count > _LIMIT:
                raise ValueError('Job inventory exceeds the safety bound')
            if _ordinary(info, directory=True):
                h.update(b'D\0' + rel.encode('utf-8') + b'\0')
                stack.append(path)
            elif _ordinary(info):
                size, digest = _hash_file(path, deadline=deadline)
                total_bytes += size
                h.update(b'F\0' + rel.encode('utf-8') + b'\0'
                         + str(size).encode('ascii') + b'\0' + digest.encode('ascii') + b'\0')
            else:
                raise ValueError('Job contains a redirected or shared entry')
    result = count, h.hexdigest()
    return (*result, total_bytes) if include_bytes else result


def _inside_downloads(final, downloads):
    """Physical output may live below a category/year folder, never elsewhere."""
    final, downloads = Path(final).absolute(), Path(downloads).absolute()
    if not final.is_relative_to(downloads) or final == downloads:
        raise ValueError('Published output must be within Downloads')
    _checked_ancestors(final)
    return final


def seal_completed_job(root, job_id, run, final, downloads):
    """Issue a private deletion eligibility seal only after verified COMPLETE publication."""
    if not _windows() or not _JOB.fullmatch(job_id) or run.get('complete') is not True:
        return False
    root = Path(root).absolute()
    job = root / 'jobs' / job_id
    _checked_ancestors(job)
    saved = _read_json(job / 'run.json', max_bytes=16 * 1024 * 1024)
    if not isinstance(saved, dict):
        return False
    if (saved.get('complete') is not True or any(saved.get(k) != run.get(k)
            for k in ('npwp', 'year', 'year_basis'))):
        return False
    if any(entry.name.startswith('publication-recovery-') for entry in job.iterdir()):
        return False
    # Reuse the exact, already-validated publication declarations rather than
    # guessing output names from the filesystem or copying any raw data to logs.
    from .output import _selected
    from .paths import downloads_folder
    if Path(downloads).absolute() != downloads_folder().absolute():
        return False
    final = _inside_downloads(final, downloads)
    published, _ = _selected(run)
    if not published or len(published) > _LIMIT:
        return False
    import coretax
    files = {}
    for name in published:
        target = coretax.output_path(final, name)
        if not target.is_relative_to(final):
            return False
        _checked_ancestors(target.parent)
        files[name] = _hash_file(target)
    if not (final / 'resume.xlsx').is_file():
        return False
    count, tree = _tree_digest(job, deadline=time.monotonic() + 60)
    receipt = {'schema': 1, 'job_id': job_id,
               'run_sha256': _hash_file(job / 'run.json')[1],
               'tree_entries': count, 'tree_sha256': tree,
               'output': str(final), 'files': files}
    # No secret-bearing path is logged; receipt stays in private job storage.
    temporary = job / (SEAL + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(receipt, stream, ensure_ascii=True, sort_keys=True)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(job / SEAL)
    finally:
        temporary.unlink(missing_ok=True)
    return True


def _published_target(final, name):
    if (not isinstance(name, str) or not name or len(name) > 1024
            or '\\' in name or ':' in name):
        raise ValueError('Invalid published relative name')
    posix = PurePosixPath(name)
    if posix.is_absolute() or any(part in ('..', '.', '') for part in name.split('/')):
        raise ValueError('Published name escapes the output')
    target = final.joinpath(*posix.parts)
    if not target.is_relative_to(final):
        raise ValueError('Published name escapes the output')
    return target


def _eligible(job, downloads, *, deadline, outputs, guard, preview_bytes=None):
    data = _read_json(job / SEAL)
    if (not isinstance(data, dict) or set(data) != {'schema', 'job_id', 'run_sha256', 'tree_entries', 'tree_sha256',
                     'output', 'files'}
            or data['schema'] != 1 or data['job_id'] != job.name
            or type(data['tree_entries']) is not int or not 0 <= data['tree_entries'] <= _LIMIT
            or not isinstance(data['files'], dict) or not data['files']
            or len(data['files']) > _LIMIT):
        return False
    run = _read_json(job / 'run.json', max_bytes=16 * 1024 * 1024)
    if not isinstance(run, dict):
        return False
    if run.get('complete') is not True or _hash_file(job / 'run.json', deadline=deadline)[1] != data['run_sha256']:
        return False
    if any(p.name.startswith('publication-recovery-') for p in job.iterdir()):
        return False
    tree = _tree_digest(job, deadline=deadline, include_bytes=preview_bytes is not None)
    count, digest = tree[:2]
    if (count, digest) != (data['tree_entries'], data['tree_sha256']):
        return False
    final = _inside_downloads(data['output'], downloads)
    # These exact output names were checked against the worker's validated
    # publication declarations when the private seal was created.  Keep the
    # desktop cleanup stdlib-only: importing the worker's openpyxl stack in
    # the frozen GUI would incorrectly make maintenance depend on its venv.
    from .paths import downloads_folder
    if downloads.absolute() != downloads_folder().absolute():
        return False
    for name, claim in data['files'].items():
        if (not isinstance(claim, list) or len(claim) != 2
                or type(claim[0]) is not int or not isinstance(claim[1], str)
                or not re.fullmatch(r'[0-9a-f]{64}', claim[1])):
            return False
        target = _published_target(final, name)
        # Pin the full ancestry, then retain this file's native read handle.
        # locked_file denies WRITE and DELETE sharing on Windows.  Acquiring
        # every declared file before any job mutation closes the verify/delete
        # TOCTOU window identified by the independent review.
        guard.include(_checked_ancestors(target.parent))
        stream = outputs.enter_context(locked_file(target))
        if _hash_held_output(stream, deadline=deadline) != claim:
            return False
    if preview_bytes is not None:
        # This is only an estimate; execution rechecks every byte and lock.
        preview_bytes.append(tree[2] + _plain(job / SEAL).st_size)
    return True


def _candidates(root, keep, exclude):
    """Only IDs older than the protected newest N runs; do not authorize deletion."""
    root = Path(root).absolute()
    jobs = root / 'jobs'
    if not jobs.is_dir():
        return []
    _checked_ancestors(jobs)
    with os.scandir(jobs) as scan:
        entries = list(scan)
    if len(entries) > 4096 or any(e.name.startswith('.spt-publish-') for e in entries):
        raise ValueError('Pending recovery or overlarge job inventory blocks pruning')
    known = []
    for entry in entries:
        if not _JOB.fullmatch(entry.name):
            continue
        path = jobs / entry.name
        info = _plain(path, directory=True)
        known.append((info.st_mtime_ns, entry.name, path))
    # The protected newest N includes incomplete, failed and historical jobs.
    known.sort(reverse=True)
    return [path for _, name, path in known[keep:] if name != exclude]


def preview_published_jobs(root, downloads, keep=DEFAULT_KEEP_JOBS, *, exclude=None):
    """Read-only verified subset with an explicit partial-scan flag.

    Candidate IDs are *private process-local authorizations*, not display or
    diagnostic data. Deletion must intersect them with the newest-N policy
    again and revalidate every seal, directory and output under native guards.
    """
    validate_keep_jobs(keep)
    empty = {'eligible_jobs': 0, 'estimated_bytes': 0,
             'candidate_ids': (), 'scan_complete': True}
    if keep == 0 or not _windows():
        return empty
    with _PRUNE_LOCK:
        candidates = _candidates(root, keep, exclude)
        global_deadline = time.monotonic() + 120
        eligible, bytes_total, complete = [], 0, True
        for job in candidates:
            if time.monotonic() >= global_deadline:
                complete = False
                break
            try:
                deadline = min(time.monotonic() + 60, global_deadline)
                measurements = []
                # Pin before reading the seal, run.json or source tree.
                with DirectoryGuard() as source_guard:
                    source_guard.include(_checked_ancestors(job))
                    try:
                        _plain(job / SEAL)
                    except FileNotFoundError:
                        continue  # Expected legacy/unsealed job, not a partial scan.
                    with DirectoryGuard() as output_guard, ExitStack() as handles:
                        if not _eligible(job, Path(downloads), deadline=deadline,
                                         outputs=handles, guard=output_guard,
                                         preview_bytes=measurements):
                            continue
                eligible.append(job.name)
                bytes_total += measurements[0]
            except (OSError, ValueError, TypeError, KeyError, RecursionError,
                    TimeoutError, UnicodeError):
                # Keep the safe verified subset, but never confirm a partial
                # preview; otherwise a locked/unknown job could be overlooked.
                complete = False
        return {'eligible_jobs': len(eligible), 'estimated_bytes': bytes_total,
                'candidate_ids': tuple(eligible), 'scan_complete': complete}


def prune_published_jobs(root, downloads, keep=DEFAULT_KEEP_JOBS, *,
                         exclude=None, allowed_ids=None):
    """Revalidate the newest-N policy and every file before any deletion.

    allowed_ids=None is automatic pruning. Manual pruning passes the exact IDs
    from a complete, explicitly confirmed read-only preview; never delete a
    newly eligible, previously skipped or newly discovered job.
    """
    validate_keep_jobs(keep)
    if allowed_ids is not None:
        if (not isinstance(allowed_ids, (tuple, frozenset))
                or len(allowed_ids) > 4096
                or any(type(name) is not str or not _JOB.fullmatch(name)
                       for name in allowed_ids)):
            raise ValueError('Invalid approved prune candidate set')
        approved = frozenset(allowed_ids)
        if len(approved) != len(allowed_ids):
            raise ValueError('Duplicate approved prune candidates')
        if not approved:
            return 0
    else:
        approved = None
    if keep == 0 or not _windows():
        return 0
    with _PRUNE_LOCK:
        try:
            candidates = _candidates(root, keep, exclude)
            removed = 0
            global_deadline = time.monotonic() + 120
            for job in candidates:
                if approved is not None and job.name not in approved:
                    continue
                if time.monotonic() >= global_deadline:
                    break
                try:
                    deadline = min(time.monotonic() + 60, global_deadline)
                    # The source ancestry is pinned *before* reading any seal.
                    # Keep it held through the entire irreversible deletion,
                    # alongside output handles denying write/delete sharing.
                    with DirectoryGuard() as source_guard:
                        expected = _checked_ancestors(job)
                        source_guard.include(expected)
                        with DirectoryGuard() as output_guard, ExitStack() as outputs:
                            if not _eligible(job, Path(downloads), deadline=deadline,
                                             outputs=outputs, guard=output_guard):
                                continue
                            from .profile_lifecycle import _remove_tree
                            _remove_tree(job, expected[job], source_guard,
                                         expected, deadline)
                            removed += 1
                except (OSError, ValueError, TypeError, KeyError, RecursionError,
                        TimeoutError, UnicodeError):
                    # Uncertain or interrupted candidates are retained for
                    # their next explicit inspection, not marked as deleted.
                    continue
            return removed
        except (OSError, ValueError, TypeError):
            return 0
