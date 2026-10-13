"""Bound PDF declarations and native-held byte custody, without browser access."""
from contextlib import contextmanager, ExitStack
import hashlib
import os
from pathlib import Path
import stat

from coretax_exporter import validate_export_run
from spt_desktop.output_windows import DirectoryGuard, locked_file

MAX_PDF_BYTES = 20 * 1024 * 1024


def attachment_declarations(run):
    validate_export_run(run)
    return [{**item, 'record_id': record['record_id'], 'scope': list(record['scope'])}
            for record in run['records'] for item in record.get('attachments', [])
            if item['status'] == 'COMPLETE']


def verified_declarations(run):
    expected = attachment_declarations(run)
    declared = run.get('output_attachments', [] if not expected else None)
    if not isinstance(declared, list) or declared != expected:
        raise ValueError('Financial PDF declaration differs from selected record/scope metadata')
    for item in declared:
        scope = item.get('scope')
        if (type(item.get('bytes')) is not int or not isinstance(scope, list)
                or len(scope) != 3 or type(scope[1]) is not int):
            raise ValueError('Invalid financial PDF declaration types')
    return expected


def _directories(path):
    result = {}
    for parent in (path, *path.parents):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, 'st_file_attributes', 0) & 1024):
            raise ValueError('Financial PDF directory uses an invalid type or reparse point')
        result[str(parent)] = (info.st_dev, info.st_ino)
    return result


def _verify_stream(stream, item):
    size = os.fstat(stream.fileno()).st_size
    if size != item['bytes'] or not 0 < size <= MAX_PDF_BYTES:
        raise ValueError('Financial PDF byte count differs from its declaration')
    stream.seek(0)
    if stream.read(5) != b'%PDF-':
        raise ValueError('Financial attachment is not a PDF byte stream')
    stream.seek(0)
    digest, total, tail = hashlib.sha256(), 0, b''
    for chunk in iter(lambda: stream.read(1048576), b''):
        total += len(chunk)
        if total > size:
            raise ValueError('Financial PDF changed or exceeded its byte bound')
        digest.update(chunk)
        tail = (tail + chunk).rstrip()[-16:]
    if total != size or not tail.endswith(b'%%EOF') or digest.hexdigest() != item['hash']:
        raise ValueError('Financial PDF is incomplete or its bytes/hash changed')
    stream.seek(0)


@contextmanager
def pdf_custody(run, folder):
    """Keep the exact checked readers and lexical ancestors held until exit.

    Consumers must close this context before renaming held source objects.
    Hash-derived filenames bind naming/scope; they do not prove authenticity.
    """
    items = verified_declarations(run)
    folder = Path(folder).absolute()
    if not items:
        yield items, {}
        return
    directories = _directories(folder)
    for item in items:
        directories.update(_directories((folder / item['relative_path']).parent))
    with DirectoryGuard() as guard, ExitStack() as readers:
        guard.include(directories)
        streams = {}
        for item in items:
            stream = readers.enter_context(locked_file(folder / item['relative_path']))
            _verify_stream(stream, item)
            streams[item['relative_path']] = stream
        yield items, streams
        for item in items:
            _verify_stream(streams[item['relative_path']], item)


def copy_held_pdfs(items, streams, folder):
    """Copy only declared bytes from the still-held readers into owned staging."""
    folder = Path(folder).absolute()
    with DirectoryGuard() as guard:
        guard.include(_directories(folder))
        for item in items:
            target = folder / item['relative_path']
            for parent in reversed(target.parent.parents):
                if parent != folder and not parent.is_relative_to(folder):
                    continue
                parent.mkdir(exist_ok=True)
                guard.include(_directories(parent))
            target.parent.mkdir(exist_ok=True)
            guard.include(_directories(target.parent))
            source = streams[item['relative_path']]
            _verify_stream(source, item)
            with target.open('xb') as destination:
                for chunk in iter(lambda: source.read(1048576), b''):
                    destination.write(chunk)
            with locked_file(target) as copied:
                _verify_stream(copied, item)
            source.seek(0)
