"""Publish verified workbooks with explicit consent and private recovery copies."""
from contextlib import contextmanager, ExitStack
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile
import uuid

import coretax
from coretax_exporter import validate_export_run, validate_scope, workbook_groups
from coretax_pdf import attachment_declarations, verified_declarations, pdf_custody, copy_held_pdfs
from .paths import safe_taxpayer_name
from .output_windows import DirectoryGuard, locked_file, move_no_replace as _move_no_replace


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
    pdf_names = [item['relative_path'] for item in verified_declarations(run)]
    return [*pdf_names, *names], _group_identities(groups)


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


def _pdf_files(folder):
    # The existing workbook scan rejects every reparse point before this scan.
    return {path.relative_to(folder).as_posix() for path in folder.rglob('*')
            if path.suffix.casefold() == '.pdf' and path.is_file()}


def _approved_existing_pdfs(run, target, actual):
    selected = {item['relative_path']: item for item in verified_declarations(run)
                if item['relative_path'] in actual}
    if not selected:
        return
    path = coretax.output_path(target, 'SPT_Badan.xlsx')
    before = _fingerprint(path)
    old = {}
    with _open_workbook(path) as stream:
        workbook = coretax.load_workbook(stream, data_only=False)
        try:
            for row in workbook['Audit'].iter_rows(min_row=5, max_col=6):
                relative = row[5].value
                if relative not in selected:
                    continue
                item = selected[relative]
                if (relative in old or row[0].value != item['record_id']
                        or row[2].value != 'COMPLETE' or not row[5].hyperlink
                        or row[5].hyperlink.target != relative):
                    raise ValueError('Existing financial PDF lacks its bound Audit declaration')
                old[relative] = {'label': row[1].value, 'status': row[2].value,
                                 'bytes': row[3].value, 'hash': row[4].value,
                                 'relative_path': relative}
        finally:
            workbook.close()
    if set(old) != set(selected) or _fingerprint(path) != before:
        raise ValueError('Existing financial PDF Audit scope changed or cannot authorize replacement')
    records = []
    for record in run['records']:
        items = [old[item['relative_path']] for item in record.get('attachments', [])
                 if item.get('relative_path') in old]
        if items:
            records.append({**record, 'attachments': items})
    previous = {**run, 'records': records}
    previous['output_attachments'] = attachment_declarations(previous)
    # Old byte/hash evidence comes from the scope-checked physical workbook,
    # never a private run.json or the newly downloaded replacement's digest.
    with pdf_custody(previous, target):
        pass


def _inspect(run, downloads, target):
    names, selected_identities = _selected(run)
    parent = _parent(run, downloads)
    target = _safe_path(target)
    if target.parent != parent or not _EXPORT_FOLDER.fullmatch(target.name) or not target.is_dir():
        raise ValueError('Output destination changed or is outside the approved Downloads scope')
    directories = _directories(target)
    actual = coretax.workbook_files(target)
    actual_pdfs = _pdf_files(target)
    folded = {}
    for name in sorted(actual | actual_pdfs | set(names)):
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
    pdf_states = {}
    for name in sorted(actual_pdfs):
        path = coretax.output_path(target, name)
        _include_directories(directories, path.parent)
        pdf_states[name] = _fingerprint(path)
    _approved_existing_pdfs(run, target, actual_pdfs)
    for name, fingerprint in {**fingerprints, **pdf_states}.items():
        if _fingerprint(coretax.output_path(target, name)) != fingerprint:
            raise ValueError('Existing output bytes changed during consent inspection')
    _check_directories(directories)
    return {'target': str(target), 'scope': (run['npwp'], run['year'], run['year_basis']),
            'selected_files': names,
            'files': [name for name in names if name in actual | actual_pdfs],
            'directories': directories, 'workbooks': fingerprints, 'attachments': pdf_states}


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
    workbooks = {name for name in states if name.endswith('.xlsx')}
    pdfs = {name for name in states if name.endswith('.pdf')}
    if coretax.workbook_files(target) != workbooks or _pdf_files(target) != pdfs:
        raise ValueError('Output workbook/PDF set changed during publication')
    for name, fingerprint in states.items():
        if _fingerprint(coretax.output_path(target, name)) != fingerprint:
            raise ValueError('Output workbook changed during publication')


def _prepare_directory(folder, guard, directories):
    _check_directories(directories)
    _safe_path(folder).mkdir(parents=True, exist_ok=True)
    _include_directories(directories, folder)
    guard.include(directories)


def _release_tree(folder, guard, directories):
    names = [name for name in directories if Path(name).is_relative_to(folder)]
    for name in sorted(names, key=lambda value: len(Path(value).parts), reverse=True):
        guard.release(name)
        del directories[name]


def _remove_owned(folder, identity, guard, directories):
    """Remove contents while their directory handles still pin the owned tree."""
    if folder.exists():
        _safe_path(folder)
        if _identity(folder.lstat()) != identity:
            raise ValueError('Temporary output directory identity changed; cleanup refused')
        _include_directories(directories, folder)
        guard.include(directories)
        for child in folder.iterdir():
            info = _safe_path(child).lstat()
            if stat.S_ISDIR(info.st_mode):
                _remove_owned(child, _identity(info), guard, directories)
            elif stat.S_ISREG(info.st_mode):
                child.unlink()
            else:
                raise ValueError('Unknown temporary output file type; cleanup refused')
        # The parent remains held. rmdir cannot recurse through a raced leaf junction.
        guard.release(folder)
        directories.pop(str(folder), None)
        folder.rmdir()


@dataclass
class _Displaced:
    path: Path
    private: Path
    captured: bool = False
    uncertain: bool = False
    lock: ExitStack | None = None
    fingerprint: tuple | None = None
    archived: bool = False

    def capture(self, source):
        if self.path.exists():
            raise FileExistsError('Temporary recovery filename is already occupied')
        try:
            _move_no_replace(source, self.path)
        except BaseException:
            # Journal the on-disk result even if an interruption follows a successful move.
            self.captured = self.path.exists()
            self.uncertain = self.captured and source.exists()
            raise
        self.captured = True

    def exists(self):
        return self.captured and self.path.exists()

    def preserve(self, guard, directories):
        if not self.exists():
            return None
        if self.uncertain:
            raise ValueError('Temporary recovery file ownership cannot be established')
        if self.lock is None:
            lock = ExitStack()
            try:
                lock.enter_context(locked_file(self.path))
                current = _fingerprint(self.path)
                if self.fingerprint is not None and current != self.fingerprint:
                    raise ValueError('Displaced workbook changed while recovery was pending')
            except BaseException:
                lock.close()
                raise
            self.lock = lock
            self.fingerprint = current
        if not self.archived:
            _prepare_directory(self.private.parent, guard, directories)
            _copy_verified(self.path, self.private)
            self.archived = True
        return self.fingerprint

    def close(self):
        lock, self.lock = self.lock, None
        if lock is not None:
            lock.close()


@dataclass
class _Replacement:
    destination: Path
    staged: Path
    original: _Displaced | None
    removed: _Displaced
    new_state: tuple


class _RecoveryRequired(RuntimeError):
    def __init__(self, recovery, retained):
        self.recovery = recovery
        self.retained = retained
        detail = ('; same-volume recovery files retained at ' + ', '.join(map(str, retained))) if retained else ''
        super().__init__(f'Output rollback blocked{detail}; recovery files retained at {recovery}')


def _displaced(destination, private):
    # Keeping the actual file in the same parent also keeps that existing leaf
    # nonempty between capture and installation. This name is not a workbook.
    return _Displaced(destination.parent / f'.spt-{uuid.uuid4().hex}.recovery', private)


def _rollback(entries, guard, directories):
    errors = []
    for entry in reversed(entries):
        try:
            _check_directories(directories)
            if entry.original is not None:
                entry.original.preserve(guard, directories)
            if not entry.staged.exists() and entry.destination.exists():
                # Capture the actual current file; never replace a third party's version.
                entry.removed.capture(entry.destination)
                actual = entry.removed.preserve(guard, directories)
                if actual != entry.new_state:
                    entry.removed.close()
                    _move_no_replace(entry.removed.path, entry.destination)
                    raise ValueError('Output changed after publication; its actual version was kept')
            if entry.original is not None and entry.original.exists():
                if entry.destination.exists():
                    raise FileExistsError('An unapproved workbook occupies the recovery destination')
                entry.original.close()
                _move_no_replace(entry.original.path, entry.destination)
        except BaseException as error:
            # Even an interrupt must preserve the other journaled versions.
            # The caller converts collected failures into _RecoveryRequired.
            errors.append(error)
    return errors


def _clean_displaced(entries, guard, directories):
    retained = []
    for entry in entries:
        for item in (entry.original, entry.removed):
            if item is not None and item.exists():
                try:
                    item.preserve(guard, directories)
                    item.close()
                    item.path.unlink()
                except BaseException:
                    # This path is outside staging: cleanup cannot delete its only copy.
                    # The caller raises _RecoveryRequired for every retained path,
                    # including an interrupt that prevented recovery or cleanup.
                    retained.append(item.path)
    return retained


def _replace_selected(run, downloads, snapshot, staging, recovery, check_cancel, guard, directories):
    target = Path(snapshot['target'])
    names = snapshot['selected_files']
    states = {**snapshot['workbooks'], **snapshot['attachments']}
    backup = recovery / 'backup'
    _prepare_directory(backup, guard, directories)
    for name in names:
        _cancel(check_cancel)
        if name in states:
            _check_directories(directories)
            saved = coretax.output_path(backup, name)
            _prepare_directory(saved.parent, guard, directories)
            copied = _copy_verified(coretax.output_path(target, name), saved)
            if copied[-1] != states[name][-1]:
                raise ValueError('Output changed before its recovery copy was made')
    _revalidate(run, downloads, snapshot)
    new_states = {name: _fingerprint(coretax.output_path(staging, name)) for name in names}
    entries = []
    pdf_locks = ExitStack()
    pdf_names = {item['relative_path'] for item in verified_declarations(run)}
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
            _prepare_directory(destination.parent, guard, directories)
            entry = _Replacement(destination, coretax.output_path(staging, name),
                _displaced(destination, coretax.output_path(recovery / 'displaced', name))
                    if name in states else None,
                _displaced(destination, coretax.output_path(recovery / 'removed', name)), new_states[name])
            entries.append(entry)
            if entry.original is not None:
                entry.original.capture(destination)
                if entry.original.preserve(guard, directories) != states[name]:
                    raise ValueError('Actual displaced workbook differs from the approved consent snapshot')
            _cancel(check_cancel)
            _check_directories(directories)
            _move_no_replace(entry.staged, destination)
            if name in pdf_names:
                pdf_locks.enter_context(locked_file(destination))
                if _fingerprint(destination) != new_states[name]:
                    raise ValueError('Financial PDF bytes/identity changed at native publication')
            states[name] = new_states[name]
        _cancel(check_cancel)
        _check_directories(directories)
        _check_files(target, states)
        coretax.verify_outputs(run, target, allow_extra=True)
        _cancel(check_cancel)
    except BaseException as failure:
        # Deny-delete PDF readers must close before the native rollback moves.
        pdf_locks.close()
        errors = _rollback(entries, guard, directories)
        retained = _clean_displaced(entries, guard, directories)
        if errors or retained:
            raise _RecoveryRequired(recovery, retained) from (errors[0] if errors else failure)
        raise
    else:
        retained = _clean_displaced(entries, guard, directories)
        if retained:
            raise _RecoveryRequired(recovery, retained)
    finally:
        pdf_locks.close()
        for entry in entries:
            for item in (entry.original, entry.removed):
                if item is not None:
                    item.close()
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
    directories = dict(snapshot['directories']) if snapshot is not None else {}
    _include_directories(directories, parent)
    _include_directories(directories, source)
    with DirectoryGuard() as guard:
        guard.include(directories)
        _prepare_directory(parent, guard, directories)
        staging = Path(tempfile.mkdtemp(prefix='.spt-', dir=parent))
        staging_identity = _identity(staging.lstat())
        recovery = None
        retain_recovery = False
        retain_staging = False
        try:
            _include_directories(directories, staging)
            guard.include(directories)
            attachments = verified_declarations(run)
            pdf_names = {item['relative_path'] for item in attachments}
            for item in attachments:
                staged = coretax.output_path(staging, item['relative_path'])
                _prepare_directory(staged.parent, guard, directories)
            with pdf_custody(run, source) as (items, streams):
                copy_held_pdfs(items, streams, staging)
            for name in names:
                if name in pdf_names:
                    continue
                _cancel(check_cancel)
                original, staged = coretax.output_path(source, name), coretax.output_path(staging, name)
                _include_directories(directories, original.parent)
                _prepare_directory(staged.parent, guard, directories)
                _copy_verified(original, staged)
            with pdf_custody(run, staging):
                coretax.verify_outputs(run, staging)
                # A real staged-PDF cancellation barrier runs with native
                # deny-write/delete readers held, not an unprotected checksum.
                _cancel(check_cancel)
                _check_directories(directories)
            if snapshot is not None:
                # Private copies may be on another drive; actual file moves never are.
                recovery = Path(tempfile.mkdtemp(prefix='.spt-publish-', dir=source.parent))
                recovery_identity = _identity(recovery.lstat())
                retain_recovery = True
                _include_directories(directories, recovery)
                guard.include(directories)
                try:
                    result = _replace_selected(run, downloads, snapshot, staging, recovery,
                                               check_cancel, guard, directories)
                except _RecoveryRequired as error:
                    # Public worker errors are deliberately generic. Keep the locations
                    # discoverable in this private job, without adding JSON to Downloads.
                    try:
                        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                prefix='publication-recovery-', suffix='.json', dir=source, delete=False) as notice:
                            json.dump({'recovery_files': [str(error.recovery), *map(str, error.retained)]}, notice)
                            notice.write('\n')
                    except OSError:
                        error.add_note('The private job recovery location note could not be written')
                    raise
                retain_recovery = False
                return result
            if existing_outputs(run, downloads) is not None:
                raise FileExistsError('An export appeared during publication; overwrite consent is required')
            stamp = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
            final = parent / f'{stamp}-{job_id[:12]}'
            if final.exists():
                raise FileExistsError('Result folder already exists; overwrite consent is required')
            _cancel(check_cancel)
            staged_directories = {name: identity for name, identity in directories.items()
                                  if Path(name).is_relative_to(staging)}
            final_directories = {str(final / Path(name).relative_to(staging)): identity
                                 for name, identity in staged_directories.items()}
            pdf_states = {name: _fingerprint(coretax.output_path(staging, name)) for name in pdf_names}
            # The deny-delete readers must close before a native directory move.
            # Reacquire and compare the exact moved identities/bytes before
            # returning a result; quarantine an unsuccessful owned PDF tree.
            _release_tree(staging, guard, directories)
            try:
                _move_no_replace(staging, final)
                directories.update(final_directories)
                guard.include(directories)
                with pdf_custody(run, final):
                    for name, state in pdf_states.items():
                        if _fingerprint(coretax.output_path(final, name)) != state:
                            raise ValueError('Financial PDF changed across native directory publication')
                    coretax.verify_outputs(run, final)
                    if attachments:
                        _cancel(check_cancel)
                return final
            except BaseException as failure:
                if (attachments and final.exists()
                        and _identity(final.lstat()) == staging_identity):
                    retain_staging = True
                    try:
                        _release_tree(final, guard, directories)
                        _move_no_replace(final, staging)
                        directories.update(staged_directories)
                        guard.include(directories)
                    except BaseException as quarantine_error:
                        raise _RecoveryRequired(staging, [final]) from quarantine_error
                    # Preserve the actual failed bytes, including a concurrent
                    # version, rather than deleting an unverified moved tree.
                    raise _RecoveryRequired(staging, []) from failure
                raise
        finally:
            if not retain_staging:
                _remove_owned(staging, staging_identity, guard, directories)
            if recovery is not None and not retain_recovery:
                _remove_owned(recovery, recovery_identity, guard, directories)
