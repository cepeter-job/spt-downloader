"""Job-bound consent; private return identifiers never travel on stdout/stdin."""
from copy import deepcopy
import json
import os
from pathlib import Path
import re
import stat
import threading
import time
import uuid

MAX_MESSAGE_BYTES = 16 * 1024 * 1024


def select_records(run, selected_ids):
    records = run.get('records')
    if not isinstance(records, list):
        raise ValueError('Invalid inventory records')
    identifiers = []
    for record in records:
        identifier = record.get('record_id') if isinstance(record, dict) else None
        if not isinstance(identifier, str) or not identifier or len(identifier) > 512:
            raise ValueError('Invalid inventory identifier')
        identifiers.append(identifier)
    if len(identifiers) != len(set(identifiers)):
        raise ValueError('Duplicate inventory identifiers')
    if (not isinstance(selected_ids, list) or not selected_ids
            or any(not isinstance(item, str) for item in selected_ids)
            or len(selected_ids) != len(set(selected_ids))
            or not set(selected_ids).issubset(identifiers)):
        raise ValueError('Select distinct identifiers from the observed inventory')
    selected = deepcopy(run)
    chosen = set(selected_ids)
    selected['records'] = [record for record in selected['records'] if record['record_id'] in chosen]
    selected['selection'] = {'inventory_count': len(records),
                             'selected_ids': [record['record_id'] for record in selected['records']]}
    selected['scope_description'] = f"Pilihan pengguna: {len(chosen)} dari {len(records)} SPT teramati."
    # Details must establish completeness again for this explicitly declared subset.
    selected['complete'] = False
    selected.pop('output_files', None)
    return selected


def _message_path(folder, job_id, request_id, reply):
    if not isinstance(job_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', job_id):
        raise ValueError('Invalid job identifier')
    if not isinstance(request_id, str) or not re.fullmatch(r'[0-9a-f]{32}', request_id):
        raise ValueError('Invalid request identifier')
    folder = Path(folder).absolute()
    for part in (folder, *folder.parents):
        if part.is_symlink() or (part.exists() and getattr(part.lstat(), 'st_file_attributes', 0) & 1024):
            raise ValueError('Private job message path cannot use a reparse point')
    suffix = 'reply' if reply else 'request'
    path = folder / f'.interaction-{request_id}.{suffix}.json'
    if path.is_symlink() or (path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 1024):
        raise ValueError('Private job message cannot use a reparse point')
    return path


def _write_message(folder, job_id, request_id, payload, reply=False):
    if not isinstance(payload, dict):
        raise ValueError('Invalid interaction payload')
    path = _message_path(folder, job_id, request_id, reply)
    data = json.dumps({'job_id': job_id, 'request_id': request_id, 'payload': payload}, ensure_ascii=False)
    if len(data.encode('utf-8')) > MAX_MESSAGE_BYTES:
        raise ValueError('Interaction payload is too large')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation prevents replay/second answers; the signal is sent only after close.
    with path.open('x', encoding='utf-8') as stream:
        stream.write(data)


def write_reply(folder, job_id, request_id, payload):
    _write_message(folder, job_id, request_id, payload, reply=True)


def read_message(folder, job_id, request_id, *, reply=False):
    path = _message_path(folder, job_id, request_id, reply)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_MESSAGE_BYTES:
        raise ValueError('Invalid private job message size/type')
    with path.open('rb') as stream:
        opened = os.fstat(stream.fileno())
        # Windows Path.open has no no-follow flag: verify the handle before reading any bytes.
        if (not os.path.samestat(before, opened) or not stat.S_ISREG(opened.st_mode)
                or opened.st_size > MAX_MESSAGE_BYTES):
            raise ValueError('Private job message identity changed while opening')
        _message_path(folder, job_id, request_id, reply)
        data = stream.read(MAX_MESSAGE_BYTES + 1)
    if len(data) > MAX_MESSAGE_BYTES:
        raise ValueError('Interaction payload is too large')
    try:
        packet = json.loads(data)
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid private job message') from error
    if (not isinstance(packet, dict) or set(packet) != {'job_id', 'request_id', 'payload'}
            or packet['job_id'] != job_id or packet['request_id'] != request_id
            or not isinstance(packet['payload'], dict)):
        raise ValueError('Interaction message is not bound to the requested job')
    return packet['payload']


class Requests:
    def __init__(self, folder, job_id, emit, check_cancel):
        self.folder, self.job_id = Path(folder), job_id
        self.emit, self.check_cancel = emit, check_cancel
        self._ready = threading.Event()
        self._lock = threading.Lock()
        self._pending = None

    def respond(self, kind, request_id):
        with self._lock:
            if self._pending != (kind, request_id) or self._ready.is_set():
                return False
            self._ready.set()
            return True

    def request(self, kind, payload, percent, *, timeout=600):
        if kind not in ('selection', 'overwrite') or type(percent) is not int or not 0 <= percent < 100:
            raise ValueError('Invalid interaction request')
        self.check_cancel()
        request_id = uuid.uuid4().hex
        _write_message(self.folder, self.job_id, request_id, payload)
        with self._lock:
            if self._pending is not None:
                raise RuntimeError('Another interaction is pending')
            self._ready.clear()
            self._pending = (kind, request_id)
        try:
            self.emit({'job_id': self.job_id, 'type': kind + '_required', 'request_id': request_id,
                       'stage': kind, 'percent': percent,
                       'message': 'Pilih SPT yang akan disedot.' if kind == 'selection' else
                                  'Hasil sebelumnya ditemukan; konfirmasi penggantian berkas.'})
            deadline = time.monotonic() + timeout
            while not self._ready.wait(min(0.1, max(0, deadline - time.monotonic()))):
                self.check_cancel()
                if time.monotonic() >= deadline:
                    raise TimeoutError('User confirmation deadline expired; no automatic consent')
            self.check_cancel()
            return read_message(self.folder, self.job_id, request_id, reply=True)
        finally:
            with self._lock:
                self._pending = None
