"""Bounded pruning of *sealed*, successfully published desktop job workspaces.

A completed export's private capture is not the published output.  Old jobs
without a new-version seal, incomplete jobs and recovery material are retained.
Never infer deletion rights from age, folder name, or run['complete'] alone.
"""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import sys
import time

from .output_windows import DirectoryGuard
from .profile_lifecycle import _identity, _ordinary

DEFAULT_KEEP_JOBS = 10
MAX_KEEP_JOBS = 100
SEAL = '.spt-published-prune-v1.json'
_JOB = re.compile(r'[0-9a-f]{32}')
_LIMIT = 16384
_MAX_SEAL_BYTES = 128 * 1024


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


def _hash_file(path):
    initial = _plain(path)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if _identity(opened) != _identity(initial) or opened.st_size != initial.st_size:
            raise ValueError('Job file changed during verification')
        for piece in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(piece)
        after = os.fstat(stream.fileno())
    current = _plain(path)
    if ((after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
            != (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)
            or (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
            != (initial.st_dev, initial.st_ino, initial.st_size, initial.st_mtime_ns)):
        raise ValueError('Job file changed during verification')
    return initial.st_size, digest.hexdigest()


def _tree_digest(job, *, deadline):
    """Hash bounded relative inventory and actual bytes; never follow links."""
    h = hashlib.sha256()
    count = 0
    stack = [job]
    while stack:
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
                size, digest = _hash_file(path)
                h.update(b'F\0' + rel.encode('utf-8') + b'\0'
                         + str(size).encode('ascii') + b'\0' + digest.encode('ascii') + b'\0')
            else:
                raise ValueError('Job contains a redirected or shared entry')
    return count, h.hexdigest()


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


def _eligible(job, downloads, *, deadline):
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
    if run.get('complete') is not True or _hash_file(job / 'run.json')[1] != data['run_sha256']:
        return False
    if any(p.name.startswith('publication-recovery-') for p in job.iterdir()):
        return False
    count, digest = _tree_digest(job, deadline=deadline)
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
        _checked_ancestors(target.parent)
        if list(_hash_file(target)) != claim:
            return False
    return True


def prune_published_jobs(root, downloads, keep=DEFAULT_KEEP_JOBS, *, exclude=None):
    """Best-effort idle-only cleanup. Never remove unsealed/incomplete work."""
    validate_keep_jobs(keep)
    if keep == 0 or not _windows():
        return 0
    root = Path(root).absolute()
    jobs = root / 'jobs'
    if not jobs.is_dir():
        return 0
    try:
        _checked_ancestors(jobs)
        with os.scandir(jobs) as scan:
            entries = list(scan)
        if len(entries) > 4096 or any(e.name.startswith('.spt-publish-') for e in entries):
            return 0  # An unresolved recovery transaction blocks all pruning.
        known = []
        for entry in entries:
            if not _JOB.fullmatch(entry.name):
                continue
            path = jobs / entry.name
            info = _plain(path, directory=True)
            known.append((info.st_mtime_ns, entry.name, path))
        # Preserve the last N runs, including partial/error and historical jobs.
        known.sort(reverse=True)
        removed = 0
        global_deadline = time.monotonic() + 120
        for _, name, job in known[keep:]:
            if time.monotonic() >= global_deadline:
                break
            if name == exclude:
                continue
            try:
                deadline = min(time.monotonic() + 60, global_deadline)
                if not _eligible(job, Path(downloads), deadline=deadline):
                    continue
                expected = _checked_ancestors(job)
                with DirectoryGuard() as guard:
                    guard.include(expected)
                    from .profile_lifecycle import _remove_tree
                    _remove_tree(job, expected[job], guard, expected, deadline)
                removed += 1
            except (OSError, ValueError, TypeError, KeyError, RecursionError, TimeoutError, UnicodeError):
                # Preserve all uncertain candidates; never alter a job outcome.
                continue
        return removed
    except (OSError, ValueError, TypeError):
        return 0
