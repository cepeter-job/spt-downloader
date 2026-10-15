"""Owned detail observations, not decoded tax records or primary identity proof.

Callbacks retain bounded driver metadata only. A completed response is read once
on the caller's thread, checked, and written immediately. Driver body() and JSON
parsing can still allocate a whole body; budgets are not hard RAM/interrupt caps.
"""
import hashlib
import json
from pathlib import Path
import re
import stat
import time
from urllib.parse import parse_qsl, unquote, urlparse
from uuid import uuid4

from coretax_json import JsonSafetyError, _object_pairs, _reject_constant, _trusted_origin
from spt_desktop.output_windows import DirectoryGuard, locked_file

MAX_RESPONSES = 1024
MAX_BODY_BYTES = 32 * 1024 * 1024
MAX_TOTAL_BYTES = 128 * 1024 * 1024
DRAIN_SECONDS = 20
MAX_REQUEST_METADATA_BYTES = 65536
_SECRET_KEYS = frozenset({'password', 'passwd', 'pwd', 'authorization', 'cookie',
                          'setcookie', 'token', 'accesstoken', 'refreshtoken',
                          'idtoken', 'apikey', 'clientsecret', 'secret', 'sessionid'})
_SECRET_TEXT = re.compile(r'\bBearer\s+\S+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', re.I)


def _secret_key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold()) in _SECRET_KEYS


def _json(raw):
    return json.loads(raw, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)


def _has_secret(value, depth=0):
    if depth > 64:
        raise ValueError('JSON nesting exceeds capture privacy inspection')
    if isinstance(value, dict):
        return any(_secret_key(key) or _has_secret(item, depth + 1) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_secret(item, depth + 1) for item in value)
    if isinstance(value, str):
        if _SECRET_TEXT.search(value):
            return True
        # Embedded and doubly encoded form JSON has the same privacy boundary.
        text = value.lstrip()
        if text.startswith(('{', '[', '"')):
            try:
                decoded = _json(text)
            except (ValueError, JsonSafetyError, RecursionError):
                raise ValueError('Embedded JSON cannot be safely privacy inspected') from None
            return decoded != value and _has_secret(decoded, depth + 1)
    return False


def _safe_url(value):
    if not _trusted_origin(value):
        return False
    parsed = urlparse(value)
    if parsed.fragment or _SECRET_TEXT.search(unquote(value)):
        return False
    try:
        return not any(_secret_key(unquote(key)) or _has_secret(item)
                       for key, item in parse_qsl(parsed.query, keep_blank_values=True))
    except (ValueError, JsonSafetyError, RecursionError):
        return False


def _ordinary_directory(path):
    info = path.lstat()
    if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
            or getattr(info, 'st_file_attributes', 0) & 0x400):
        raise ValueError('Private capture ancestor is not an ordinary directory')
    return info.st_dev, info.st_ino


class DetailJsonCapture:
    """Enter before inspected View; bind only its verified page, then drain."""

    def __init__(self, context, page, record, scope, folder, *, ordinal=1, check_cancel=None):
        if (not isinstance(scope, (list, tuple)) or len(scope) != 3
                or not isinstance(scope[0], str) or not re.fullmatch(r'[0-9]{16}', scope[0])
                or type(scope[1]) is not int or not 1900 <= scope[1] <= 2100
                or scope[2] not in ('period', 'submission')):
            raise JsonSafetyError('Invalid private capture scope; values are not normalized')
        if type(ordinal) is not int or ordinal < 1:
            raise JsonSafetyError('Private capture ordinal must be a positive integer')
        if (not isinstance(record, dict) or not isinstance(record.get('record_id'), str)
                or not record['record_id'] or record['record_id'] != record['record_id'].strip()
                or '/' in record['record_id'] or '\\' in record['record_id']):
            raise JsonSafetyError('Missing literal selected record identity')
        source = record.get('list_url')
        if not _safe_url(source):
            raise JsonSafetyError('Private capture source is not authorized')
        match = re.fullmatch(r'/returnsheets/id-ID/[^/]*returnsheets/([^/]+)/?', urlparse(source).path)
        if not match or page.context is not context:
            raise JsonSafetyError('Private capture taxpayer or browser context is unverified')
        root = Path(folder)
        if '..' in root.parts:
            raise JsonSafetyError('Private capture path contains parent traversal')
        self.context = context
        self.page = page
        self.folder = root.absolute()
        self.scope = list(scope)
        self.record_id = record['record_id']
        self.source_url = source
        self.taxpayer_id = match.group(1)
        self.ordinal = ordinal
        self.check_cancel = check_cancel
        self.attempt = uuid4().hex
        self._relative = Path('returns', 'json', f'{ordinal:04d}', self.attempt)
        self._guard = DirectoryGuard()
        self._listeners = []
        self._requests = {}
        self._observations = []
        self._active = False
        self._bound = None
        self._bound_url = None
        self._seen = 0
        self._read_bytes = 0
        self._responses = []
        self._reasons = []
        self._result = None
        self._manifest_hash = None
        self._counts = {'accepted': 0, 'pending': 0, 'excluded': 0, 'failed': 0}
        self._limits = {'responses': MAX_RESPONSES, 'body_bytes': MAX_BODY_BYTES,
                        'attempt_bytes': MAX_TOTAL_BYTES, 'drain_seconds': DRAIN_SECONDS}

    def _cancel(self, callback=None):
        if self.check_cancel:
            self.check_cancel()
        if callback is not None and callback is not self.check_cancel:
            callback()

    def _reason(self, reason):
        if reason not in self._reasons:
            self._reasons.append(reason)

    def _hold(self, path):
        expected = {parent: _ordinary_directory(parent) for parent in reversed([path, *path.parents])}
        self._guard.include(expected)

    def __enter__(self):
        self._cancel()
        if self._active or self._listeners or self._result is not None:
            raise JsonSafetyError('Private capture attempt cannot be restarted')
        try:
            self._hold(self.folder)
            current = self.folder
            for name in self._relative.parts:
                self._cancel()
                current = current / name
                current.mkdir(exist_ok=name != self.attempt)
                self._hold(current)
            self._active = True
            for event, callback in (('request', self._on_request), ('response', self._on_response),
                                    ('requestfinished', self._on_finished), ('requestfailed', self._on_failed)):
                self.context.on(event, callback)
                self._listeners.append((event, callback))
            return self
        except (OSError, ValueError):
            self.close()
            raise JsonSafetyError('Private capture folder cannot be safely acquired') from None
        except BaseException:
            self.close()
            raise

    def _detail_matches(self, value):
        if not _safe_url(value) or not urlparse(value).path.startswith('/returnsheets/'):
            return False
        parts = urlparse(value).path.split('/')
        return self.taxpayer_id in parts and self.record_id in parts

    def _candidate(self, target, frame):
        return (target.context is self.context and frame is target.main_frame
                and frame.parent_frame is None
                and (target is self.page or target.opener() is self.page))

    def _on_request(self, request):
        if not self._active or self._result is not None:
            return
        try:
            if (not _safe_url(request.url) or request.resource_type not in ('xhr', 'fetch')
                    or not urlparse(request.url).path.startswith('/returnsheet/api/')
                    or urlparse(request.url).path.casefold().startswith('/returnsheet/api/returnsheets')):
                return
            frame = request.frame
            target = frame.page
            if (not self._candidate(target, frame) or not self._detail_matches(frame.url)
                    or self._bound is not None and target is not self._bound):
                return
            if self._seen >= self._limits['responses']:
                self._reason('response-limit')
                return
            self._seen += 1
            post = request.post_data
            request_json = None
            if post is not None:
                if not isinstance(post, str) or len(post.encode('utf-8')) > MAX_REQUEST_METADATA_BYTES:
                    self._reason('request-context-limit')
                    return
                request_json = _json(post)
                if _has_secret(request_json):
                    self._reason('secret-request')
                    return
            # Keep bounded metadata after MIME exclusion/drain, but never keep
            # the driver request/response or its body through this ledger.
            observation = {'target': target, 'frame_url': frame.url, 'url': request.url,
                           'method': request.method, 'request_json': request_json,
                           'sequence': self._seen, 'status': None}
            self._observations.append(observation)
            self._requests[request] = {**observation, 'frame': frame,
                                       'observation': observation,
                                       'state': 'pending', 'response': None}
        except Exception:
            # Driver/JSON exception text may contain credentials; never persist it.
            self._reason('request-context-unavailable')

    def _on_response(self, response):
        entry = self._requests.get(response.request)
        if entry is None:
            return
        try:
            if response.url != entry['url'] or not _safe_url(response.url):
                entry['state'] = 'failed'
                self._reason('response-source-mismatch')
                return
            # Authorization failure is decisive even when the server sends HTML.
            # Keep only the status: no rejected body is read or persisted.
            entry['status'] = response.status
            entry['observation']['status'] = entry['status']
            if entry['status'] in (401, 403):
                entry['state'] = 'failed'
                self._reason('authorization-rejected')
                return
            content_type = response.header_value('content-type') or ''
            mime = content_type.split(';', 1)[0].strip().casefold()
            if mime != 'application/json' and not mime.endswith('+json'):
                self._requests.pop(response.request)
                self._counts['excluded'] += 1
                return
            entry.update(response=response, content_type=mime,
                         content_length=response.header_value('content-length'), status=response.status)
        except Exception:
            entry['state'] = 'failed'
            self._reason('response-metadata-unavailable')

    def _on_finished(self, request):
        entry = self._requests.get(request)
        if entry is not None and entry['state'] != 'failed':
            entry['state'] = 'finished'

    def _on_failed(self, request):
        entry = self._requests.get(request)
        if entry is not None:
            entry['state'] = 'failed'
            self._reason('request-failed')

    def bind_detail_page(self, detail):
        self._cancel()
        if (not self._active or detail.context is not self.context or detail.is_closed()
                or not self._detail_matches(detail.url)
                or detail is not self.page and detail.opener() is not self.page):
            raise JsonSafetyError('Detail page does not belong to this selected capture attempt')
        if self._bound is not None and self._bound is not detail:
            raise JsonSafetyError('Detail page changed inside a capture attempt')
        self._bound = detail
        self._bound_url = detail.url
        self._observations = [item for item in self._observations if item['target'] is detail]
        for request, entry in list(self._requests.items()):
            if entry['target'] is not detail:
                self._requests.pop(request)
                self._counts['excluded'] += 1

    def _verify_binding(self):
        if (not self._active or self._bound is None or self._bound.is_closed()
                or self._bound.context is not self.context or self._bound.url != self._bound_url
                or not self._detail_matches(self._bound.url)):
            raise JsonSafetyError('Verified detail page binding changed or is missing')

    def _write(self, name, raw, check_cancel=None):
        self._cancel(check_cancel)
        directory = self.folder / self._relative
        self._hold(directory)
        path = directory / name
        with path.open('xb') as stream:
            for offset in range(0, len(raw), 65536):
                self._cancel(check_cancel)
                stream.write(raw[offset:offset + 65536])
            self._cancel(check_cancel)
        self._hold(directory)
        return path.relative_to(self.folder).as_posix()

    def _process(self, entry, deadline, check_cancel):
        self._cancel(check_cancel)
        self._verify_binding()
        response = entry['response']
        if response is None:
            self._reason('response-metadata-unavailable')
            return
        declared = entry.get('content_length')
        if declared is not None and (not re.fullmatch(r'[0-9]+', declared)
                                     or int(declared) > self._limits['body_bytes']):
            self._reason('body-size-limit')
            return
        if declared is not None and int(declared) + self._read_bytes > self._limits['attempt_bytes']:
            self._reason('attempt-byte-limit')
            return
        try:
            raw = response.body()
        except Exception:
            self._reason('body-read-failed')
            return
        self._cancel(check_cancel)
        self._verify_binding()
        if time.monotonic() >= deadline:
            self._reason('drain-deadline')
            return
        if not isinstance(raw, bytes) or len(raw) > self._limits['body_bytes']:
            self._reason('body-size-limit')
            return
        self._read_bytes += len(raw)
        if self._read_bytes > self._limits['attempt_bytes']:
            self._reason('attempt-byte-limit')
            return
        try:
            payload = _json(raw)
            secret = _has_secret(payload)
        except (ValueError, JsonSafetyError, RecursionError, UnicodeError):
            self._reason('invalid-json')
            return
        if secret:
            self._reason('secret-body')
            return
        del payload
        self._cancel(check_cancel)
        self._verify_binding()
        relative = self._write(f'response-{len(self._responses) + 1:04d}.json', raw, check_cancel)
        self._responses.append({'relative_path': relative, 'bytes': len(raw),
                                'sha256': hashlib.sha256(raw).hexdigest(),
                                'url': entry['url'], 'method': entry['method'], 'status': entry['status'],
                                'frame_url': entry['frame_url'], 'sequence': entry['sequence'],
                                'attempt': self.attempt, 'record_id': self.record_id,
                                'scope': list(self.scope), 'request_json': entry['request_json'],
                                'identity_validated': False})
        self._counts['accepted'] += 1

    def drain(self, check_cancel=None):
        self._cancel(check_cancel)
        self._verify_binding()
        if self._result is not None:
            return json.loads(json.dumps(self._result))
        deadline = time.monotonic() + self._limits['drain_seconds']
        while self._requests:
            self._cancel(check_cancel)
            self._verify_binding()
            if time.monotonic() >= deadline:
                self._counts['pending'] = len(self._requests)
                self._reason('response-pending')
                break
            ready = next(((request, entry) for request, entry in self._requests.items()
                          if entry['state'] in ('finished', 'failed')), None)
            if ready is None:
                self._bound.wait_for_timeout(100)
                continue
            request, entry = ready
            try:
                if entry['state'] == 'failed':
                    self._counts['failed'] += 1
                else:
                    self._process(entry, deadline, check_cancel)
            finally:
                self._requests.pop(request, None)
            del request, entry, ready
        self._requests.clear()
        self._cancel(check_cancel)
        self._verify_binding()
        result = {'version': 1, 'attempt': self.attempt, 'record_id': self.record_id,
                  'scope': list(self.scope), 'source_url': self.source_url, 'detail_url': self._bound_url,
                  'limits': dict(self._limits), 'counts': dict(self._counts),
                  'complete': not self._reasons, 'reasons': list(self._reasons),
                  'responses': list(self._responses), 'credentials_accessed': False,
                  'primary_identity_validated': False}
        raw = json.dumps(result, ensure_ascii=False, sort_keys=True).encode('utf-8')
        manifest = self._write('manifest.json', raw, check_cancel)
        self._cancel(check_cancel)
        self._manifest_hash = hashlib.sha256(raw).hexdigest()
        self._result = {**result, 'manifest': manifest, 'manifest_sha256': self._manifest_hash}
        return json.loads(json.dumps(self._result))

    def request_observations(self):
        """Expose this attempt's bounded metadata, including excluded replies."""
        self._cancel()
        self._verify_binding()
        keys = ('url', 'method', 'frame_url', 'sequence', 'request_json', 'status')
        return json.loads(json.dumps([{key: item.get(key) for key in keys}
                                      for item in self._observations
                                      if item['target'] is self._bound]))

    def iter_bodies(self, check_cancel=None):
        self._cancel(check_cancel)
        if self._result is None:
            raise JsonSafetyError('Capture must be drained before resolving body references')
        try:
            self._hold(self.folder / self._relative)
            with locked_file(self.folder / self._result['manifest']) as stream:
                manifest = stream.read()
            if hashlib.sha256(manifest).hexdigest() != self._manifest_hash:
                raise JsonSafetyError('Private capture manifest changed')
            saved = _json(manifest)
            if saved['attempt'] != self.attempt or saved['scope'] != self.scope or saved['record_id'] != self.record_id:
                raise JsonSafetyError('Private capture scope or attempt changed')
            for descriptor in saved['responses']:
                self._cancel(check_cancel)
                relative = Path(descriptor['relative_path'])
                if (relative.is_absolute() or '..' in relative.parts or relative.parent != self._relative
                        or descriptor['attempt'] != self.attempt):
                    raise JsonSafetyError('Unsafe private response reference')
                self._hold(self.folder / self._relative)
                with locked_file(self.folder / relative) as stream:
                    raw = stream.read(self._limits['body_bytes'] + 1)
                if (len(raw) != descriptor['bytes'] or len(raw) > self._limits['body_bytes']
                        or hashlib.sha256(raw).hexdigest() != descriptor['sha256']):
                    raise JsonSafetyError('Private response bytes changed')
                self._cancel(check_cancel)
                payload = _json(raw)
                if _has_secret(payload):
                    raise JsonSafetyError('Private response no longer meets privacy policy')
                self._cancel(check_cancel)
                yield {'body': raw, 'payload': payload, 'context': descriptor}
                del raw, payload
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise JsonSafetyError('Private capture references cannot be safely resolved') from None

    def close(self):
        self._active = False
        self._requests.clear()
        self._observations.clear()
        for event, callback in reversed(self._listeners):
            try:
                self.context.remove_listener(event, callback)
            except Exception:
                pass  # Context may already be disposed; never close user pages.
        self._listeners.clear()
        self._guard.close()

    def __exit__(self, exception_type, exception, traceback):
        try:
            self.close()
        except Exception:
            if exception_type is None:
                raise JsonSafetyError('Private capture cleanup failed') from None
        return False


def checkpoint_bodies(folder, capture, record, scope):
    """Reacquire original private bytes; reject lexical escapes before any read."""
    from pathlib import PurePosixPath
    if not isinstance(capture, dict):
        raise JsonSafetyError('Missing private capture checkpoint')
    reference = capture.get('manifest')
    if (not isinstance(reference, str) or '\\' in reference or ':' in reference
            or not re.fullmatch(r'returns/json/[0-9]{4,}/[a-f0-9]{32}/manifest\.json', reference)):
        raise JsonSafetyError('Unsafe private capture manifest reference')
    relative = PurePosixPath(reference)
    root = Path(folder).absolute()
    if '..' in root.parts:
        raise JsonSafetyError('Unsafe private capture folder')

    def hold(guard, directory):
        guard.include({parent: _ordinary_directory(parent)
                       for parent in reversed([directory, *directory.parents])})

    def read(guard, name, maximum):
        hold(guard, (root / name).parent)
        with locked_file(root / name) as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise JsonSafetyError('Private checkpoint exceeds its byte budget')
        return raw

    try:
        with DirectoryGuard() as guard:
            raw = read(guard, reference, 8 * 1024 * 1024)
            if hashlib.sha256(raw).hexdigest() != capture.get('manifest_sha256'):
                raise JsonSafetyError('Private checkpoint manifest bytes changed')
            saved = _json(raw)
            expected = {**saved, 'manifest': reference, 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
            if json.dumps(capture, sort_keys=True) != json.dumps(expected, sort_keys=True):
                raise JsonSafetyError('Private checkpoint manifest metadata changed')
            if (type(saved.get('version')) is not int or saved['version'] != 1
                    or saved.get('scope') != list(scope) or type(saved['scope'][1]) is not int
                    or saved.get('record_id') != record['record_id']
                    or saved.get('source_url') != record['list_url']
                    or saved.get('attempt') != relative.parent.name
                    or saved.get('detail_url') != record.get('detail_url')):
                raise JsonSafetyError('Private checkpoint identity or attempt changed')
            descriptors = saved.get('responses')
            if not isinstance(descriptors, list) or len(descriptors) > MAX_RESPONSES:
                raise JsonSafetyError('Private checkpoint response budget changed')
            packets, total, seen = [], 0, set()
            for descriptor in descriptors:
                name = descriptor.get('relative_path')
                if (not isinstance(name, str) or '\\' in name or ':' in name
                        or PurePosixPath(name).parent != relative.parent
                        or not re.fullmatch(r'response-[0-9]{4,}\.json', PurePosixPath(name).name)
                        or name in seen or descriptor.get('attempt') != saved['attempt']
                        or descriptor.get('record_id') != record['record_id']
                        or descriptor.get('scope') != list(scope) or type(descriptor['scope'][1]) is not int
                        or type(descriptor.get('bytes')) is not int or descriptor['bytes'] < 0
                        or descriptor['bytes'] > MAX_BODY_BYTES):
                    raise JsonSafetyError('Unsafe private checkpoint response reference')
                seen.add(name)
                total += descriptor['bytes']
                if total > MAX_TOTAL_BYTES:
                    raise JsonSafetyError('Private checkpoint attempt budget changed')
                body = read(guard, name, MAX_BODY_BYTES)
                if len(body) != descriptor['bytes'] or hashlib.sha256(body).hexdigest() != descriptor.get('sha256'):
                    raise JsonSafetyError('Private checkpoint response bytes changed')
                payload = _json(body)
                if _has_secret(payload):
                    raise JsonSafetyError('Private checkpoint no longer meets privacy policy')
                packets.append({'body': body, 'payload': payload, 'context': descriptor})
            return packets
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        raise JsonSafetyError('Private checkpoint custody cannot be safely verified') from None
