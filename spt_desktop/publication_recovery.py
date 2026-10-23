"""Private write-ahead recovery for interrupted, consent-bound replacements.

The journal makes process-death recovery discoverable. It does not turn several
filesystem moves into one atomic transaction or guarantee storage hardware.
"""
from contextlib import ExitStack
import errno
import json
import os
from pathlib import Path
import re
import shutil
import sys
import uuid

from .output_windows import DirectoryGuard, delete_verified, locked_file


_MAX_MANIFEST = 64 * 1024 * 1024
_RECOVERY_NAME = re.compile(r'\.spt-[0-9a-f]{32}\.recovery')


def _write(path, value):
    from coretax_browser import _atomic_checkpoint
    from .output import _safe_path
    _safe_path(path)
    _atomic_checkpoint(path, value)


def _read(path):
    with locked_file(path) as stream:
        raw = stream.read(_MAX_MANIFEST + 1)
    if len(raw) > _MAX_MANIFEST:
        raise ValueError('Publication recovery manifest is too large')
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('Invalid publication recovery manifest')
    return value


def _flush(path):
    # A writable handle is required for FlushFileBuffers on Windows.
    with path.open('rb+') as stream:
        stream.flush()
        os.fsync(stream.fileno())


def _directory_snapshot(source, target, recovery, directories):
    from .output import _directories
    result = {}
    for root in (source, target, recovery):
        result.update(_directories(root))
    for name, identity in directories.items():
        path = Path(name)
        if path.is_relative_to(target) or path.is_relative_to(recovery):
            result[name] = identity
    return result


class PublicationJournal:
    def __init__(self, source, downloads, snapshot, recovery, directories):
        self.source, self.recovery = Path(source), Path(recovery)
        self.path = self.recovery / 'manifest.json'
        self.notice = self.source / f'publication-recovery-{uuid.uuid4().hex}.json'
        self.value = {'schema': 1, 'state': 'pending', 'source': str(self.source),
                      'downloads': str(downloads), 'target': snapshot['target'],
                      'recovery': str(self.recovery), 'scope': snapshot['scope'],
                      'before': {**snapshot['workbooks'], **snapshot['attachments'], **snapshot.get('json', {})},
                      'directories': _directory_snapshot(self.source, Path(snapshot['target']),
                                                          self.recovery, directories),
                      'entries': []}
        for path in (self.recovery / 'backup').rglob('*'):
            if path.is_file():
                _flush(path)
        _write(self.path, self.value)
        self.retain([])

    def retain(self, paths):
        _write(self.notice, {'schema': 1, 'manifest': str(self.path),
                            'recovery_files': [str(self.recovery), *map(str, paths)]})

    def record(self, name, entry, old_state, directories):
        target = Path(self.value['target'])
        self.value['entries'].append({'name': name,
            'original': entry.original.path.relative_to(target).as_posix() if entry.original else None,
            'removed': entry.removed.path.relative_to(target).as_posix(),
            'old': old_state, 'new': entry.new_state})
        self.value['directories'] = _directory_snapshot(self.source, target, self.recovery, directories)
        _write(self.path, self.value)

    def finish(self, state):
        self.value['state'] = state
        _write(self.path, self.value)


def _state(value):
    return (isinstance(value, list) and len(value) == 5
            and all(type(item) is int and item >= 0 for item in value[:4])
            and value[1] > 0 and isinstance(value[4], str)
            and re.fullmatch(r'[0-9a-f]{64}', value[4]) is not None)


def _same_bytes(actual, expected):
    return actual[2] == expected[2] and actual[-1] == expected[-1]


def _recover_one(source, downloads, notice):
    import coretax
    from . import output

    note = _read(notice)
    if (set(note) != {'schema', 'manifest', 'recovery_files'} or note.get('schema') != 1
            or not isinstance(note.get('manifest'), str)):
        raise ValueError('Invalid private publication recovery notice')
    manifest = output._safe_path(note['manifest'])
    recovery = manifest.parent
    if (manifest.name != 'manifest.json' or recovery.parent != source.parent
            or not re.fullmatch(r'\.spt-publish-[A-Za-z0-9_-]+', recovery.name)):
        raise ValueError('Publication recovery path is outside its private job storage')
    saved = _read(manifest)
    required = {'schema', 'state', 'source', 'downloads', 'target', 'recovery',
                'scope', 'before', 'directories', 'entries'}
    if (set(saved) != required or type(saved.get('schema')) is not int or saved['schema'] != 1
            or saved.get('state') not in ('pending', 'restored', 'committed')
            or saved.get('source') != str(source) or saved.get('downloads') != str(downloads)
            or saved.get('recovery') != str(recovery) or not isinstance(saved.get('target'), str)):
        raise ValueError('Publication recovery scope or path changed')
    run = _read(source / 'run.json')
    target = output._safe_path(saved['target'])
    if (target.parent != output._parent(run, downloads)
            or not output._EXPORT_FOLDER.fullmatch(target.name)
            or saved['scope'] != [run['npwp'], run['year'], run['year_basis']]):
        raise ValueError('Publication recovery target does not match the saved scope')
    selected, _ = output._selected(run)
    before, entries, directory_rows = saved['before'], saved['entries'], saved['directories']
    if (not isinstance(before, dict) or not before or not all(_state(state) for state in before.values())
            or not isinstance(entries, list) or len(entries) > len(selected)
            or (saved['state'] == 'committed' and len(entries) != len(selected))
            or not isinstance(directory_rows, dict)):
        raise ValueError('Invalid publication recovery entries')
    for name in before:
        coretax.output_path(target, name)
    directories = {}
    for name, identity in directory_rows.items():
        path = output._safe_path(name)
        permitted = any(path == root or path in root.parents or path.is_relative_to(root)
                        for root in (source, target, recovery))
        if (not permitted or not isinstance(identity, list) or len(identity) != 2
                or any(type(item) is not int or item < 0 for item in identity) or not identity[1]):
            raise ValueError('Invalid recovery directory identity')
        directories[str(path)] = tuple(identity)
    # Never replace recorded identities with current ones; changed targets fail closed.
    for root in (source, target, recovery):
        expected = directories.get(str(root))
        if expected is None or output._identity(root.lstat()) != expected:
            raise ValueError('Publication recovery directory changed')
    seen = set()
    for ordinal, entry in enumerate(entries):
        if (not isinstance(entry, dict) or set(entry) != {'name', 'original', 'removed', 'old', 'new'}
                or entry.get('name') != selected[ordinal] or not _state(entry.get('new'))
                or entry.get('old') != before.get(entry.get('name'))):
            raise ValueError('Publication recovery selection or entry changed')
        destination = coretax.output_path(target, entry['name'])
        if entry['old'] is None and entry['original'] is not None:
            raise ValueError('Unexpected original publication recovery path')
        for key in ('original', 'removed'):
            relative = entry[key]
            if relative is None and key == 'original' and entry['old'] is None:
                continue
            path = coretax.output_path(target, relative)
            if (path.parent != destination.parent or not _RECOVERY_NAME.fullmatch(path.name)
                    or relative.casefold() in seen):
                raise ValueError('Invalid same-volume publication recovery path')
            seen.add(relative.casefold())
        if str(destination.parent) not in directories:
            raise ValueError('Publication recovery destination is not guarded')

    with DirectoryGuard() as guard, ExitStack() as readers:
        guard.include(directories)
        output._check_directories(directories)
        # Retained, unselected workbooks must also remain the approved old bytes.
        names = {entry['name'] for entry in entries}
        allowed = set(before) | names
        actual = coretax.workbook_files(target) | output._pdf_files(target) | output._json_files(target)
        if not actual.issubset(allowed):
            raise ValueError('Unapproved file appeared before publication recovery')
        for name in set(before) - names:
            path = coretax.output_path(target, name)
            readers.enter_context(locked_file(path))
            if not _same_bytes(output._fingerprint(path), before[name]):
                raise ValueError('Unselected output changed before publication recovery')
        if saved['state'] == 'committed':
            for entry in entries:
                path = coretax.output_path(target, entry['name'])
                readers.enter_context(locked_file(path))
                if tuple(entry['new']) != output._fingerprint(path):
                    raise ValueError('Committed output changed; publication recovery refused')
            return target

        # Preflight the entire journal before changing a single destination.
        for entry in entries:
            destination = coretax.output_path(target, entry['name'])
            old, new = entry['old'], entry['new']
            if destination.exists():
                current = output._fingerprint(destination)
                if not ((old is not None and _same_bytes(current, old)) or current == tuple(new)):
                    raise ValueError('Output changed or unapproved bytes block publication recovery')
            elif saved['state'] == 'restored' and old is not None:
                raise ValueError('Restored output disappeared before recovery verification')
            if old is not None:
                backup = coretax.output_path(recovery / 'backup', entry['name'])
                guard.include(output._directories(backup.parent))
                readers.enter_context(locked_file(backup))
                if not _same_bytes(output._fingerprint(backup), old):
                    raise ValueError('Private publication recovery backup changed')
            for key, expected in (('original', old), ('removed', new)):
                if entry[key] is None:
                    continue
                path = coretax.output_path(target, entry[key])
                if path.exists() and not _same_bytes(output._fingerprint(path), expected):
                    raise ValueError('Same-volume publication recovery file changed')

        for entry in reversed(entries):
            output._check_directories(directories)
            destination = coretax.output_path(target, entry['name'])
            old = entry['old']
            removed = coretax.output_path(target, entry['removed'])
            if destination.exists():
                current = output._fingerprint(destination)
                if old is not None and _same_bytes(current, old):
                    continue
                if current != tuple(entry['new']):
                    raise ValueError('Output changed during publication recovery')
                output._move_no_replace(destination, removed)
                if output._fingerprint(removed) != tuple(entry['new']):
                    output._move_no_replace(removed, destination)
                    raise ValueError('Unapproved concurrent output was preserved during recovery')
            if old is not None:
                original = coretax.output_path(target, entry['original'])
                if not original.exists():
                    backup = coretax.output_path(recovery / 'backup', entry['name'])
                    temporary = original.parent / f'.spt-restore-{uuid.uuid4().hex}.partial'
                    # A killed copy must not occupy the authoritative original path.
                    # Interrupted partial files are retained for private inspection.
                    with locked_file(backup) as stream, temporary.open('xb') as restored:
                        shutil.copyfileobj(stream, restored)
                        restored.flush()
                        os.fsync(restored.fileno())
                    if not _same_bytes(output._fingerprint(temporary), old):
                        raise ValueError('Publication recovery copy differs from its private backup')
                    output._move_no_replace(temporary, original)
                if not _same_bytes(output._fingerprint(original), old):
                    raise ValueError('Original publication recovery bytes changed')
                output._move_no_replace(original, destination)
                if not _same_bytes(output._fingerprint(destination), old):
                    raise ValueError('Restored publication output changed')

        # Only recognized displaced versions can be removed; private backups remain.
        for entry in entries:
            for key, expected in (('original', entry['old']), ('removed', entry['new'])):
                if entry[key] is None:
                    continue
                path = coretax.output_path(target, entry[key])
                if path.exists():
                    actual = output._fingerprint(path)
                    if not _same_bytes(actual, expected):
                        raise ValueError('Publication recovery cleanup encountered changed bytes')
                    # A reconstructed original can have a new inode. Bind
                    # deletion to this checked version while preserving any
                    # version that changes before native custody is acquired.
                    delete_verified(path, actual)
        for name, expected in before.items():
            if not _same_bytes(output._fingerprint(coretax.output_path(target, name)), expected):
                raise ValueError('Restored publication bytes differ from the prior output')
        saved['state'] = 'restored'
        _write(manifest, saved)
        return target


def recover_publication(source, downloads):
    """Explicitly restore a pending publication; refuse changed/unowned paths."""
    if sys.platform != 'win32':
        raise OSError(errno.ENOTSUP, 'Publication recovery requires native Windows custody')
    from . import output
    source, downloads = output._safe_path(source), output._safe_path(downloads)
    if source.is_relative_to(downloads):
        raise ValueError('Publication recovery requires a private job outside Downloads')
    with DirectoryGuard() as guard:
        guard.include(output._directories(source))
        notices = sorted(source.glob('publication-recovery-*.json'))
        if len(notices) != 1:
            raise ValueError('Publication recovery requires exactly one private journal; inspect multiple attempts separately')
        return _recover_one(source, downloads, notices[0])


def main(argv=None):
    import argparse
    from .paths import downloads_folder
    cli = argparse.ArgumentParser(description='Recover one interrupted desktop publication without browser access.')
    cli.add_argument('--job', required=True, type=Path, help='Original private job folder; do not move or edit its journal')
    args = cli.parse_args(argv)
    try:
        target = recover_publication(args.job, downloads_folder())
    except (OSError, ValueError, RuntimeError) as error:
        cli.exit(1, f'Publication recovery refused: {error}\nKeep the original job, journal and recovery files.\n')
    print(f'Publication recovery verified: {target}')
    print('This verifies local publication recovery, not COMPLETE capture of a tax scope.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
