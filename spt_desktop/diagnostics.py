"""Explicit, best-effort diagnostics. No raw messages, payloads or console sink."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import hashlib
import json
import os
from pathlib import Path
import queue
import sys
import threading
import time
import uuid

from .diagnostic_store import SegmentStore

SCHEMA = 1
LEVELS = {'DEBUG': 10, 'INFO': 20, 'WARNING': 30, 'ERROR': 40, 'OFF': 100}
EVENTS = frozenset({
    'session.started', 'session.closed', 'operation.started', 'operation.finished', 'detail.source',
    'operation.failed', 'operation.cancelled', 'phase.started', 'phase.completed',
    'phase.failed', 'phase.cancelled', 'progress', 'runtime.reused', 'runtime.install',
    'runtime.command', 'worker.spawned', 'worker.authorized', 'worker.protocol_rejected',
    'worker.stderr_discarded', 'worker.finished', 'worker.forced_stop', 'worker.stop',
    'consent.requested', 'consent.replied', 'capture.partial', 'pdf.partial',
    'publish.rollback', 'gui.callback_failed', 'gui.poll_failed', 'gui.failed',
    'settings.failed', 'checkpoint.reused', 'auth.state', 'auth.result', 'auth.request_blocked',
    'catalog.checkpoint', 'catalog.read', 'catalog.validation',
})
ENUMS = {
    'catalog_stage': frozenset({'planning', 'recheck', 'after_inventory'}),
    'catalog_reason': frozenset({'available', 'catalog_missing', 'catalog_type',
        'catalog_language', 'catalog_checksum', 'catalog_details', 'catalog_expiry_invalid',
        'catalog_expired_or_unbound', 'catalog_serialization', 'catalog_row', 'catalog_code',
        'catalog_label', 'catalog_duplicate', 'scope_unsupported', 'origin_blocked',
        'enumeration_unavailable', 'enumeration_error', 'database_missing', 'store_missing',
        'record_missing', 'record_identity', 'open_blocked', 'open_error', 'upgrade_refused',
        'version_changed', 'read_error', 'projection_error', 'read_timeout', 'evaluation_error'}),
    'source_requested': frozenset({'dom', 'json-first'}),
    'source_used': frozenset({'dom', 'json', 'none'}),
    'source_reason': frozenset({'dom_requested', 'native_verified', 'capture_incomplete',
        'adapter_ineligible', 'coverage_incomplete', 'forms_unavailable', 'unsupported_tax', 'checkpoint_reuse'}),
    'tax_kind': frozenset({'ppn', 'pph21', 'unifikasi', 'corporate', 'other'}),
    'phase': frozenset({'startup', 'runtime', 'authentication', 'inventory', 'details',
                       'detail', 'pdf', 'export', 'verify', 'publish', 'rollback', 'cli',
                       'return_detail', 'list_restore', 'open_detail', 'json_observe', 'json_project'}),
    'stage': frozenset({'setup', 'authentication', 'inventory', 'details', 'export',
                       'publish', 'finished', 'login_check', 'selection', 'overwrite'}),
    'operation': frozenset({'export', 'login_check', 'offline', 'resume'}),
    'status': frozenset({'COMPLETE', 'PARTIAL', 'CANCELLED', 'BLOCKED', 'ERROR',
                        'LOGIN_OK', 'LOGIN_UNVERIFIED', 'LOGIN_MANUAL', 'LOGIN_BLOCKED', 'LOGIN_ERROR'}),
    'kind': frozenset({'selection', 'overwrite', 'start', 'stop'}),
    'browser': frozenset({'msedge', 'chrome'}),
    'expected_origin': frozenset({'coretax', 'satu', 'other'}),
    'observed_origin': frozenset({'coretax', 'satu', 'other'}),
    'target_origin': frozenset({'coretax', 'satu', 'other'}),
    'method': frozenset({'GET', 'HEAD', 'POST', 'OTHER'}),
    'resource_type': frozenset({'document', 'xhr', 'fetch', 'other'}),
    'reason': frozenset({'waiting_redirect', 'waiting_form', 'login_form_ready',
        'existing_session', 'existing_home', 'origin_blocked', 'origin_mismatch',
        'challenge', 'unsafe_form', 'form_changed', 'readiness_timeout',
        'credential_missing', 'account_mismatch', 'verified', 'verification_timeout',
        'check_error', 'cancelled', 'cross_origin_write', 'origin_not_allowed'}),
}
COUNTERS = frozenset({'count', 'processed', 'total', 'verified', 'scanned', 'percent', 'blocked_requests', 'ordinal', 'body_rows', 'pages', 'grids', 'forms'})
ERROR_TYPES = frozenset({'ValueError', 'TypeError', 'RuntimeError', 'OSError', 'PermissionError',
    'FileNotFoundError', 'FileExistsError', 'TimeoutError', 'TimeoutExpired', 'CalledProcessError',
    'KeyError', 'IndexError', 'AssertionError', 'UnicodeError', 'UnicodeDecodeError',
    'JSONDecodeError', 'TclError', 'AuthBlocked', 'SetupCancelled', 'CaptureCancelled',
    'KeyboardInterrupt', 'SystemExit', 'JsonSafetyError', '_RecoveryRequired'})
MODULES = frozenset({'coretax', 'coretax_browser', 'coretax_attachments', 'coretax_pdf',
    'coretax_exporter', 'coretax_json', 'coretax_json_capture', 'coretax_corporate',
    'spt_gui', *('spt_desktop.' + name for name in (
        'app', 'controller', 'worker', 'auth', 'runtime', 'events', 'interaction',
        'output', 'output_windows', 'paths', 'credentials', 'ui_state', 'ui_views'))})
FUNCTIONS = frozenset({'main', '_main', 'run_job', 'run_login_check', 'prepare', '_run',
    'start', '_start_worker', 'poll', '_poll', '_finish', '_drain', '_enqueue',
    'read_events', 'drain_errors', 'respond', 'read_request', 'check', 'save', 'remove',
    'ensure_runtime', '_probe_python', '_resources', '_uv', 'worker_source',
    'authenticate_owned', 'try_saved_login', 'check_saved_credentials', '_bind_login_fields',
    'collect_inventory', 'collect_details', 'capture_detail', 'capture_panel', 'capture_table',
    'download_financial_attachments', '_read_pdf', '_verify_page', '_financial_url',
    'save_output', 'verify_outputs', '_publish_output', '_check_output_scope',
    'validate_export_run', 'export_workbook', 'export_split_workbooks',
    'publish_workbooks', '_replace_selected', '_rollback', '_fingerprint', '_inspect',
    'pdf_custody', '_verify_stream', 'locked_file', 'include', 'self_test'})
_active = None
_job = ContextVar('diagnostic_job_ref', default=None)
_detail = ContextVar('diagnostic_detail_fields', default=None)


def job_reference(value):
    if type(value) is str and 0 < len(value) <= 64:
        return hashlib.sha256(b'spt-diagnostic-job:' + value.encode('utf-8')).hexdigest()
    return None


def _error_summary(error):
    name = type(error).__name__
    result = {'type': name if name in ERROR_TYPES else 'Error', 'frames': []}
    # Never inspect source text, locals, args, message or exception chains.
    tb = error.__traceback__
    for _ in range(64):
        if tb is None:
            break
        frame = tb.tb_frame
        module = frame.f_globals.get('__name__')
        if type(module) is str and module in MODULES:
            name = frame.f_code.co_name
            result['frames'].append({'file': module.replace('.', '/') + '.py',
                'function': name if name in FUNCTIONS else '<other>', 'line': tb.tb_lineno})
            if len(result['frames']) > 8:
                result['frames'].pop(0)
        tb = tb.tb_next
    for name in ('errno', 'winerror'):
        value = getattr(error, name, None)
        if type(value) is int and 0 <= value <= 65535:
            result[name] = value
    return result


def _safe_fields(fields):
    result = {}
    for name, allowed in ENUMS.items():
        value = fields.get(name)
        if type(value) is str and value in allowed:
            result[name] = value
    for name in COUNTERS:
        value = fields.get(name)
        if type(value) is int and 0 <= value <= 10_000_000:
            result[name] = value
    for name in ('exit_code',):
        value = fields.get(name)
        if type(value) is int and -(2 ** 31) <= value < 2 ** 32:
            result[name] = value
    value = fields.get('duration_ms')
    if type(value) in (int, float) and 0 <= value <= 604_800_000:
        result['duration_ms'] = round(value, 2)
    for name in ('headless', 'accepted', 'submitted', 'cached'):
        if type(fields.get(name)) is bool:
            result[name] = fields[name]
    return result


class DiagnosticLog:
    """One bounded queue and one file-owning daemon thread per process session."""

    def __init__(self, root, role, *, job_id=None, level='INFO', max_bytes=1048576,
                 backup_count=3, max_files=32, retention_days=7, queue_size=256):
        self.session_id = uuid.uuid4().hex
        self.role = role
        self.level = level if type(level) is str and level in LEVELS else 'INFO'
        self.job_ref = job_reference(job_id)
        self.dropped = 0
        self._closed = False
        self._failed = False
        self._started = time.monotonic()
        self._sequence = 0
        self._lock = threading.RLock()
        self._stop = threading.Event()
        self._thread = None
        self._queue = queue.Queue(maxsize=queue_size if type(queue_size) is int and 1 <= queue_size <= 8192 else 256)
        root = Path(root)
        valid = (root.is_absolute() and '..' not in root.parts and type(role) is str
                 and role in ('gui', 'worker', 'cli') and self.level != 'OFF'
                 and type(max_bytes) is int and 512 <= max_bytes <= 1048576
                 and type(backup_count) is int and 1 <= backup_count <= 8
                 and type(max_files) is int and 1 <= max_files <= 128
                 and type(retention_days) is int and 0 <= retention_days <= 30)
        if not valid:
            self._closed = True
            return
        self._store_args = (root, role, self.session_id)
        self._store_options = dict(max_bytes=max_bytes, backup_count=backup_count,
                                   max_files=max_files, retention_days=retention_days)
        self._thread = threading.Thread(target=self._consume, name='spt-diagnostics', daemon=True)
        self._thread.start()
        self.record('session.started')

    @property
    def pending(self):
        return self._queue.qsize()

    def record(self, event, *, level='INFO', error=None, job_id=None, **fields):
        try:
            if (type(event) is not str or event not in EVENTS or type(level) is not str
                    or level not in LEVELS or LEVELS[level] < LEVELS[self.level]):
                return False
            with self._lock:
                if self._closed or self._failed:
                    return False
                self._sequence += 1
                row = {'schema': SCHEMA, 'timestamp': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
                       'level': level, 'event': event, 'role': self.role,
                       'session_id': self.session_id, 'sequence': self._sequence,
                       'elapsed_ms': max(0, round((time.monotonic() - self._started) * 1000, 2)),
                       'python': '.'.join(map(str, sys.version_info[:3])),
                       'frozen': bool(getattr(sys, 'frozen', False)), **_safe_fields(fields)}
                reference = job_reference(job_id) or _job.get() or self.job_ref
                if reference:
                    row['job_ref'] = reference
                if isinstance(error, BaseException):
                    row['error'] = _error_summary(error)
                self._queue.put_nowait(row)
                return True
        except queue.Full:
            with self._lock:
                self.dropped += 1
            return False
        except Exception:
            # Diagnostic input must never replace a business exception.
            return False

    def _consume(self):
        store = None
        try:
            store = SegmentStore(*self._store_args, **self._store_options)
            while not self._stop.is_set() or not self._queue.empty():
                try:
                    item = self._queue.get(timeout=0.05)
                except queue.Empty:
                    continue
                try:
                    if isinstance(item, threading.Event):
                        item.set()
                        continue
                    with self._lock:
                        if self.dropped:
                            item['dropped'] = self.dropped
                    line = json.dumps(item, ensure_ascii=True, separators=(',', ':'), allow_nan=False) + '\n'
                    if len(line.encode('utf-8')) > 4096:
                        with self._lock:
                            self.dropped += 1
                        continue
                    store.write(line)
                finally:
                    self._queue.task_done()
        except Exception:
            self._failed = True
        finally:
            try:
                if store is not None:
                    store.close()
            except Exception:
                self._failed = True
            while True:
                try:
                    item = self._queue.get_nowait()
                except queue.Empty:
                    break
                if isinstance(item, threading.Event):
                    item.set()
                self._queue.task_done()

    def flush(self, timeout=2):
        try:
            if self._failed or self._thread is None or not self._thread.is_alive():
                return False
            timeout = min(2, max(0, float(timeout)))
            deadline = time.monotonic() + timeout
            barrier = threading.Event()
            self._queue.put(barrier, timeout=timeout)
            return barrier.wait(max(0, deadline - time.monotonic())) and not self._failed
        except Exception:
            return False

    def close(self, timeout=2):
        try:
            with self._lock:
                if not self._closed:
                    self.record('session.closed')
                    self._closed = True
                    self._stop.set()
            if self._thread is not None and self._thread is not threading.current_thread():
                self._thread.join(timeout=min(2, max(0, float(timeout))))
        except Exception:
            pass  # Shutdown must not replace the original outcome.

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


def configured_level():
    value = os.environ.get('SPT_LOG_LEVEL', 'INFO')
    return value if value in LEVELS else 'INFO'


def default_root(workspace=None):
    try:
        override = os.environ.get('SPT_LOG_ROOT')
        if override is not None:
            return Path(override)
        if workspace is not None:
            return Path(workspace)
        if sys.platform == 'win32':
            from .paths import workspace_root
            return workspace_root()
        return Path.home() / '.local' / 'state' / 'spt-downloader'
    except Exception:
        # Resolving diagnostics is optional too. Relative roots are disabled,
        # never interpreted as permission to write into the working directory.
        return Path('.')


@contextmanager
def session(root, role, *, job_id=None, level=None):
    global _active
    previous = _active
    log = None
    try:
        try:
            log = DiagnosticLog(root, role, job_id=job_id, level=level or configured_level())
        except Exception:
            # An unavailable logger must not prevent the caller from running.
            pass
        _active = log
        yield log
    finally:
        _active = previous
        if log is not None:
            try:
                log.close()
            except Exception:
                # Preserve the product outcome even when diagnostic shutdown fails.
                pass


@contextmanager
def job_context(job_id):
    token = _job.set(job_reference(job_id))
    try:
        yield
    finally:
        _job.reset(token)


def record(event, **fields):
    try:
        if _active is not None:
            return _active.record(event, **{**(_detail.get() or {}), **fields})
    except Exception:
        # Optional instrumentation cannot replace an operation's error or Stop.
        pass
    return False


@contextmanager
def detail_context(**fields):
    # Only anonymous benchmark categories enter the inherited context.
    safe = _safe_fields(fields)
    token = _detail.set({k: safe[k] for k in ('ordinal', 'tax_kind', 'source_requested') if k in safe})
    try:
        yield
    finally:
        _detail.reset(token)


@contextmanager
def measure(phase, **fields):
    if _active is None:
        yield fields
        return
    start = time.monotonic()
    record('phase.started', phase=phase, **fields)
    try:
        yield fields
    except BaseException as error:
        cancelled = isinstance(error, KeyboardInterrupt) or type(error).__name__ == 'SetupCancelled'
        record('phase.cancelled' if cancelled else 'phase.failed', phase=phase,
               level='INFO' if cancelled else 'ERROR', error=error,
               **{**fields, 'status': 'CANCELLED' if cancelled else 'ERROR',
                  'duration_ms': (time.monotonic() - start) * 1000})
        raise
    record('phase.completed', phase=phase,
           **{**fields, 'duration_ms': (time.monotonic() - start) * 1000})


def traced(phase):
    def decorate(function):
        @wraps(function)
        def call(*args, **kwargs):
            with measure(phase):
                return function(*args, **kwargs)
        return call
    return decorate


def log_folder(workspace):
    root = default_root(workspace)
    if not root.is_absolute() or '..' in root.parts:
        raise ValueError('Diagnostic location unavailable')
    folder = root / 'logs'
    import stat
    for parent in (folder, *folder.parents):
        info = parent.lstat()
        if not stat.S_ISDIR(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Diagnostic location is redirected')
    return folder


def self_test(root):
    """Actually emit/read synthetic logs; used by source and frozen GUI gates."""
    with session(root, 'gui', level='INFO') as log:
        record('operation.started')
        record('catalog.checkpoint', catalog_stage='planning')
        record('catalog.read', catalog_reason='available', count=2,
               payload='SYNTHETIC PRIVATE VALUE MUST NOT BE LOGGED')
        record('catalog.validation', catalog_reason='available', count=2)
        with detail_context(ordinal=1, tax_kind='ppn', source_requested='json-first'):
            with measure('return_detail') as benchmark:
                record('detail.source', source_used='json', source_reason='native_verified',
                       token='SYNTHETIC PRIVATE VALUE MUST NOT BE LOGGED')
                benchmark.update(source_used='json', status='COMPLETE', body_rows=2, cached=False)
        record('auth.state', reason='waiting_redirect', expected_origin='satu', observed_origin='coretax')
        record('auth.request_blocked',reason='cross_origin_write',target_origin='coretax',method='POST',resource_type='fetch')
        record('auth.result', status='LOGIN_BLOCKED', reason='origin_mismatch',
               expected_origin='coretax', observed_origin='satu', submitted=False,
               password='SYNTHETIC PRIVATE VALUE MUST NOT BE LOGGED')
        try:
            raise ValueError('SYNTHETIC PRIVATE VALUE MUST NOT BE LOGGED')
        except ValueError as error:
            record('operation.failed', error=error)
        if log is None or not log.flush():
            raise RuntimeError('Synthetic diagnostics self-test failed')
    text = ''.join(path.read_text(encoding='utf-8') for path in (Path(root) / 'logs').glob('diag-*.jsonl'))
    rows = [json.loads(line) for line in text.splitlines()]
    if ('SYNTHETIC PRIVATE' in text or not any(row['event'] == 'operation.failed' for row in rows)
            or not any(row['event'] == 'session.closed' for row in rows)):
        raise RuntimeError('Synthetic diagnostics self-test failed')
    if not (any(row.get('event') == 'catalog.checkpoint' and row.get('catalog_stage') == 'planning' for row in rows)
            and any(row.get('event') == 'catalog.read' and row.get('catalog_reason') == 'available'
                    and row.get('count') == 2 and 'payload' not in row for row in rows)
            and any(row.get('event') == 'catalog.validation' and row.get('catalog_reason') == 'available' for row in rows)):
        raise RuntimeError('Synthetic catalog diagnostics self-test failed')
    states = [row for row in rows if row['event'] == 'auth.state']
    results = [row for row in rows if row['event'] == 'auth.result']
    if (not any(row.get('reason') == 'waiting_redirect' and row.get('expected_origin') == 'satu'
                and row.get('observed_origin') == 'coretax' for row in states)
            or not any(row.get('status') == 'LOGIN_BLOCKED' and row.get('reason') == 'origin_mismatch'
                       and row.get('submitted') is False for row in results)):
        raise RuntimeError('Synthetic authentication diagnostics self-test failed')
    if not any(row.get('event')=='auth.request_blocked' and row.get('target_origin')=='coretax'
               and row.get('method')=='POST' and row.get('resource_type')=='fetch' for row in rows):
        raise RuntimeError('Synthetic request diagnostics self-test failed')
    benchmark = [row for row in rows if row.get('phase') == 'return_detail' and row['event'] == 'phase.completed']
    if not (len(benchmark) == 1 and benchmark[0].get('ordinal') == 1
            and benchmark[0].get('source_requested') == 'json-first'
            and benchmark[0].get('source_used') == 'json' and benchmark[0].get('body_rows') == 2):
        raise RuntimeError('Synthetic benchmark diagnostics self-test failed')
    return {'schema': SCHEMA, 'safe_logging': True}
