"""Publish verified workbooks with explicit consent and private recovery copies."""
from contextlib import contextmanager
from datetime import datetime
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

import coretax
from coretax_exporter import validate_export_run, validate_scope, workbook_groups
from .paths import safe_taxpayer_name


_EXPORT_FOLDER = re.compile(r'[0-9]{8}-[0-9]{6}-[0-9]{6}-[A-Za-z0-9_-]{1,12}')


def _cancel(check_cancel):
    if check_cancel:
        check_cancel()


def _safe_path(path):
    """Inspect lexical ancestors before normalization can hide a junction."""
    path = Path(path).absolute()
    for component in (path, *path.parents):
        try:
            info = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 1024:
            raise ValueError('Downloads/output path cannot use a symbolic link or reparse point')
    return Path(os.path.abspath(path))


def _identity(info):
    return info.st_dev, info.st_ino


def _file_state(info):
    return (*_identity(info), info.st_size, info.st_mtime_ns)


@contextmanager
def _open_workbook(path):
    path = _safe_path(path)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError('Invalid workbook file type')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        if not stat.S_ISREG(opened.st_mode) or _file_state(opened) != _file_state(before):
            raise ValueError('Workbook identity changed while opening')
        _safe_path(path)
        yield stream
        if (_file_state(os.fstat(stream.fileno())) != _file_state(before)
                or _file_state(_safe_path(path).lstat()) != _file_state(before)):
            raise ValueError('Workbook changed while being inspected')


def _fingerprint(path):
    result = hashlib.sha256()
    with _open_workbook(path) as stream:
        state = _file_state(os.fstat(stream.fileno()))
        for chunk in iter(lambda: stream.read(1048576), b''):
            result.update(chunk)
    return (*state, result.hexdigest())


def _directories(path):
    path = _safe_path(path)
    result = {}
    for component in (path, *path.parents):
        if component.exists():
            info = component.lstat()
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('Invalid Downloads/output directory')
            result[str(component)] = _identity(info)
    return result


def _check_directories(expected):
    for name, identity in expected.items():
        path = _safe_path(name)
        if not path.is_dir() or _identity(path.lstat()) != identity:
            raise ValueError('Downloads/output directory changed since consent')


def _include_directories(expected, path):
    for name, identity in _directories(path).items():
        if name in expected and expected[name] != identity:
            raise ValueError('Downloads/output directory changed during publication')
        expected[name] = identity


def _case_component(parent, name):
    if parent.exists():
        if any(child.name != name and child.name.casefold() == name.casefold()
               for child in parent.iterdir()):
            raise ValueError('Downloads/output filename collision')


def _parent(run, downloads):
    npwp, year = validate_scope(run['npwp'], run['year'])
    name = safe_taxpayer_name(run.get('taxpayer_name', ''))
    downloads = _safe_path(downloads)
    parent = downloads
    for component in (f'{npwp} - {name}', str(year)):
        _case_component(parent, component)
        parent = _safe_path(parent / component)
    return parent


def _selected(run):
    validate_export_run(run)
    groups = workbook_groups(run)
    names = sorted(groups) + ['resume.xlsx']  # Publish the new index last.
    declared = run.get('output_files', names)
    if (not isinstance(declared, list) or any(not isinstance(name, str) for name in declared)
            or len(declared) != len(set(declared)) or set(declared) != set(names)):
        raise ValueError('Invalid workbook filename declaration')
    return names, _group_identities(groups)


def _group_identities(groups):
    result = {}
    for name, records in groups.items():
        meta = records[0]['meta']
        # The shared layout helper puts literal source periods in nested workbooks.
        result[name] = ((meta['Jenis Pajak'], meta.get('Masa Pajak', ''))
                        if '/' in name else (meta['Jenis Pajak'],))
    return result


def _workbook_scope(run, path, relative):
    """Read old headers and literal layout identity independently of run.json."""
    try:
        with _open_workbook(path) as stream:
            workbook = coretax.load_workbook(stream, read_only=True, data_only=False)
            try:
                summary = workbook['Ringkasan']
                basis = 'Masa/Tahun Pajak' if run['year_basis'] == 'period' else 'Tanggal Submit SPT'
                if (summary['B4'].value != run['npwp'] or summary['B4'].data_type != 's'
                        or summary['B5'].value != run['year'] or summary['B7'].value != basis
                        or summary['B8'].value not in ('COMPLETE', 'PARTIAL')
                        or 'Audit' not in workbook.sheetnames):
                    raise ValueError('Existing workbook scope/NPWP cannot authorize overwrite')
                index = workbook['Daftar SPT']
                records = [{'meta': {'Jenis Pajak': row[1], 'Masa Pajak': row[3]}}
                           for row in index.iter_rows(min_row=5, min_col=1, max_col=5, values_only=True)]
                if summary['B9'].value != len(records):
                    raise ValueError('Existing workbook scope count cannot be verified')
                groups = workbook_groups({'records': records})
                if relative != 'resume.xlsx' and set(groups) != {relative}:
                    raise ValueError('Unknown workbook filename or literal period scope')
                return _group_identities(groups)
            finally:
                workbook.close()
    except (ValueError, OSError):
        raise
    except Exception as error:
        raise ValueError('Existing workbook scope cannot be verified') from error


def _inspect(run, downloads, target):
    names, selected_identities = _selected(run)
    parent = _parent(run, downloads)
    target = _safe_path(target)
    if target.parent != parent or not _EXPORT_FOLDER.fullmatch(target.name) or not target.is_dir():
        raise ValueError('Output destination changed or is outside the approved Downloads scope')
    directories = _directories(target)
    actual = coretax.workbook_files(target)
    folded = {}
    for name in sorted(actual | set(names)):
        if name.casefold() in folded and folded[name.casefold()] != name:
            raise ValueError('Existing workbook filename collision')
        folded[name.casefold()] = name
    if 'resume.xlsx' not in actual:
        raise ValueError('Existing output scope has no known resume.xlsx')
    fingerprints, identities, indexed = {}, {}, {}
    for name in sorted(actual):
        path = coretax.output_path(target, name)
        _include_directories(directories, path.parent)
        before = _fingerprint(path)
        declared = _workbook_scope(run, path, name)
        if _fingerprint(path) != before:
            raise ValueError('Workbook changed while inspecting output scope')
        fingerprints[name] = before
        if name == 'resume.xlsx':
            indexed = declared
        else:
            identities.update(declared)
    if any(identities.get(name) != identity for name, identity in indexed.items()):
        raise ValueError('Existing resume references an unknown workbook scope')
    if any(name in identities and identities[name] != identity
           for name, identity in selected_identities.items()):
        raise ValueError('Tax type or literal period filename collision with existing output scope')
    _check_directories(directories)
    return {'target': str(target), 'scope': (run['npwp'], run['year'], run['year_basis']),
            'selected_files': names, 'files': [name for name in names if name in actual],
            'directories': directories, 'workbooks': fingerprints}


def existing_outputs(run, downloads):
    """Return a private snapshot of the latest recognizable export, without writing."""
    _selected(run)
    parent = _parent(run, downloads)
    if not parent.exists():
        return None
    candidates = []
    for child in parent.iterdir():
        if _EXPORT_FOLDER.fullmatch(child.name):
            _safe_path(child)
            if not child.is_dir():
                raise ValueError('Unknown existing output destination')
            candidates.append(child)
    if not candidates:
        return None
    if len({path.name.casefold() for path in candidates}) != len(candidates):
        raise ValueError('Existing output folder filename collision')
    return _inspect(run, downloads, max(candidates, key=lambda path: path.name))


def _revalidate(run, downloads, snapshot):
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get('target'), str):
        raise ValueError('Invalid output consent snapshot')
    try:
        current = _inspect(run, downloads, snapshot['target'])
    except FileNotFoundError as error:
        raise ValueError('Output changed since consent') from error
    if current != snapshot:
        raise ValueError('Output changed since consent; review the new snapshot')


def _copy_verified(original, target):
    before = _fingerprint(original)
    _safe_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(original, target)
    copied = _fingerprint(target)
    if before != _fingerprint(original) or before[-1] != copied[-1]:
        raise OSError('Workbook copy verification failed')
    return copied


def _check_files(target, states):
    if coretax.workbook_files(target) != set(states):
        raise ValueError('Output workbook set changed during publication')
    for name, fingerprint in states.items():
        if _fingerprint(coretax.output_path(target, name)) != fingerprint:
            raise ValueError('Output workbook changed during publication')


def _remove_owned(folder, identity):
    if folder.exists():
        _safe_path(folder)
        if _identity(folder.lstat()) != identity:
            raise ValueError('Temporary output directory identity changed; cleanup refused')
        shutil.rmtree(folder)


def _replace_selected(run, downloads, snapshot, staging, recovery, check_cancel):
    target = Path(snapshot['target'])
    names = snapshot['selected_files']
    directories = dict(snapshot['directories'])
    _include_directories(directories, staging)
    states = dict(snapshot['workbooks'])
    backup = recovery / 'backup'
    backup.mkdir()
    for name in names:
        _cancel(check_cancel)
        if name in states:
            _check_directories(directories)
            copied = _copy_verified(coretax.output_path(target, name), coretax.output_path(backup, name))
            if copied[-1] != states[name][-1]:
                raise ValueError('Output changed before its recovery copy was made')
    _revalidate(run, downloads, snapshot)
    new_states = {name: _fingerprint(coretax.output_path(staging, name)) for name in names}
    attempted = []
    try:
        for name in names:
            _cancel(check_cancel)
            _check_directories(directories)
            destination = coretax.output_path(target, name)
            if name in states:
                if _fingerprint(destination) != states[name]:
                    raise ValueError('Output workbook changed before replacement')
            elif destination.exists():
                raise ValueError('Unapproved workbook appeared before replacement')
            container = target
            for component in destination.relative_to(target).parts[:-1]:
                # Reject an empty directory alias as well as aliases containing workbooks.
                _case_component(container, component)
                container = container / component
            destination.parent.mkdir(parents=True, exist_ok=True)
            _include_directories(directories, destination.parent)
            attempted.append(name)
            coretax.output_path(staging, name).replace(destination)
            states[name] = new_states[name]
        _cancel(check_cancel)
        _check_directories(directories)
        _check_files(target, states)
        coretax.verify_outputs(run, target, allow_extra=True)
        _cancel(check_cancel)
    except BaseException:
        try:
            for name in reversed(attempted):
                if coretax.output_path(staging, name).exists():
                    continue  # The replacement did not consume its staged source.
                _check_directories(directories)
                destination = coretax.output_path(target, name)
                if _fingerprint(destination) != new_states[name]:
                    raise ValueError('Output changed after replacement; recovery must not overwrite it')
                saved = coretax.output_path(backup, name)
                if saved.exists():
                    restored = coretax.output_path(staging / 'restore', name)
                    _copy_verified(saved, restored)
                    restored.replace(destination)
                else:
                    destination.unlink()
        except BaseException as error:
            raise RuntimeError(f'Output rollback blocked; recovery files retained at {recovery}') from error
        raise
    return target


def publish_workbooks(run, source, downloads, job_id, check_cancel=None, *,
                      overwrite=False, expected_outputs=None):
    """Publish a new export, or replace only selected files with explicit consent."""
    if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', job_id):
        raise ValueError('Invalid job identifier')
    if type(overwrite) is not bool:
        raise ValueError('Overwrite consent must be an explicit boolean')
    _cancel(check_cancel)
    source, downloads = _safe_path(source), _safe_path(downloads)
    coretax.verify_outputs(run, source)
    names, _ = _selected(run)
    parent = _parent(run, downloads)
    snapshot = expected_outputs if expected_outputs is not None else existing_outputs(run, downloads)
    if snapshot is not None:
        if not overwrite:
            raise FileExistsError('Existing output requires explicit overwrite consent')
        if source.is_relative_to(downloads):
            raise ValueError('Overwrite recovery requires a private source outside Downloads')
        _revalidate(run, downloads, snapshot)
    _cancel(check_cancel)
    parent.mkdir(parents=True, exist_ok=True)
    parent_directories = _directories(parent)
    staging = Path(tempfile.mkdtemp(prefix='.spt-', dir=parent))
    staging_identity = _identity(staging.lstat())
    _include_directories(parent_directories, staging)
    recovery = None
    retain_recovery = False
    try:
        for name in names:
            _cancel(check_cancel)
            _check_directories(parent_directories)
            _copy_verified(coretax.output_path(source, name), coretax.output_path(staging, name))
        coretax.verify_outputs(run, staging)
        _cancel(check_cancel)
        _check_directories(parent_directories)
        if snapshot is not None:
            # Downloads may be on another drive; recovery copies stay beside the private job.
            recovery = Path(tempfile.mkdtemp(prefix='.spt-publish-', dir=source.parent))
            recovery_identity = _identity(recovery.lstat())
            retain_recovery = True
            result = _replace_selected(run, downloads, snapshot, staging, recovery, check_cancel)
            retain_recovery = False
            return result
        if existing_outputs(run, downloads) is not None:
            raise FileExistsError('An export appeared during publication; overwrite consent is required')
        stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
        final = parent / f'{stamp}-{job_id[:12]}'
        if final.exists():
            raise FileExistsError('Result folder already exists; overwrite consent is required')
        _cancel(check_cancel)
        staging.rename(final)
        return final
    finally:
        if recovery is not None and not retain_recovery:
            _remove_owned(recovery, recovery_identity)
        _remove_owned(staging, staging_identity)
