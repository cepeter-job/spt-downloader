"""Owned detail observations, not decoded tax records or primary identity proof.

Callbacks retain bounded driver metadata only. A completed response is read once
on the caller's thread, checked, and written immediately. Driver body() and JSON
parsing can still allocate a whole body; budgets are not hard RAM/interrupt caps.

Exception-handling policy for this module:
- Driver probes can fail through Playwright/CDP or an adapter. Preserve the
  bounded unavailable-proof fallback and surrounding Stop checks.
- Never forward exception text into captured JSON or diagnostics.
"""
from contextlib import contextmanager, ExitStack
import hashlib
import json
from pathlib import Path
import re
import stat
import time
from urllib.parse import parse_qsl, unquote, urlparse
from uuid import uuid4

from coretax_json import (JsonSafetyError, PPH21_REFERENCE_URLS, UNIFIKASI_REFERENCE_URL,
                          CORPORATE_REFERENCE_REQUESTS, ORIGIN,
                          _capture_clock_interval, _capture_component_lifetime, _capture_l8_lifetime,
                          _object_pairs, _reject_constant, _trusted_origin)
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
_BROWSER_CLOCK = '() => ({epoch_ms:Date.now(),timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})'
_COMPONENT_OWNERS = """() => {
 const visible=e=>{for(let p=e;p;p=p.parentElement){const s=getComputedStyle(p);
   if(p.hidden||s.display==='none'||s.visibility==='hidden'||s.visibility==='collapse')return false;}
   return !!e.getClientRects().length;};
 const count=s=>Array.from(document.querySelectorAll(s)).filter(visible).length;
 return {source_owner:count('rshshr-submitted-returnsheets')===1,
         detail_owner:count('rshshr-corporate-income-tax-return')===1};
}"""
_L8_HISTORY = """(d) => {
 const rootSelector='rshshr-corporate-income-tax-return';
 const dependents='rshshr-citr-l7-form,rshshr-citr-l13a-form,rshshr-citr-l13b-form';
 const state={initial_clear:d===document&&!d.querySelector(rootSelector+','+dependents),
   root_seen:false,root_changed:false,dependent_seen:false};
 let root=null,remaining=4096;
 const visit=(node,removed)=>{
   if(--remaining<0){state.initial_clear=false;return;}
   if(node.nodeType!==1)return;
   if(node.matches(dependents))state.dependent_seen=true;
   if(node.matches(rootSelector)){
     if(removed)state.root_changed=true;
     else if(root&&root!==node)state.root_changed=true;
     else {root=node;state.root_seen=true;}
   }
 };
 const inspect=(node,removed)=>{
   visit(node,removed);
   if(!state.initial_clear||!node.firstChild)return;
   const walker=d.createTreeWalker(node,NodeFilter.SHOW_ELEMENT);
   while(state.initial_clear){const next=walker.nextNode();if(!next)break;visit(next,removed);}
 };
 const process=records=>{
   if(!state.initial_clear)return;
   for(const record of records){
     if(--remaining<0){state.initial_clear=false;break;}
     for(const node of record.removedNodes){inspect(node,true);if(!state.initial_clear)break;}
     for(const node of record.addedNodes){inspect(node,false);if(!state.initial_clear)break;}
     if(!state.initial_clear)break;
   }
 };
 const observer=new MutationObserver(process);
 observer.observe(d,{childList:true,subtree:true});
 return {sample:()=>{
   process(observer.takeRecords());
   if(state.initial_clear&&root&&(!root.isConnected||root.ownerDocument!==d))state.root_changed=true;
   return {...state};
 },disconnect:()=>observer.disconnect()};
}"""


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
        meta = record.get('meta')
        tax = meta.get('Jenis Pajak') if isinstance(meta, dict) else None
        fields = record.get('source_fields', {})
        corporate = (tax == 'PPh Badan' and isinstance(fields, dict)
                     and fields.get('TaxTypeCode') == 'ICT_RCIT'
                     and fields.get('ReturnSheetTypeCode') == 'ICT_RCITR')
        self._reference_urls = (PPH21_REFERENCE_URLS if tax == 'PPh Pasal 21/26' else
                                (UNIFIKASI_REFERENCE_URL,) if tax == 'PPh Unifikasi' else
                                tuple(CORPORATE_REFERENCE_REQUESTS) if corporate else ())
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
        self._clock_start = None
        self._corporate = corporate
        self._view_called = False
        self._component_document = None
        self._component_listener = None
        self._component_transitions = 0
        self._component_target = None
        self._component_invalid = False
        self._component_observed = False
        self._component_started = False
        self._l8_history = None
        self._l8_requested = False
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

    def _sample_clock(self, page, check_cancel=None):
        """Optional browser environment evidence; driver failures reveal no text."""
        self._cancel(check_cancel)
        try:
            sample = page.evaluate(_BROWSER_CLOCK)
        except Exception:
            # Driver probes against test doubles or CDP may raise arbitrary errors.
            # The fallback is unavailable proof; no exception text is forwarded.
            sample = None
        self._cancel(check_cancel)
        if not isinstance(sample, dict) or set(sample) != {'epoch_ms', 'timezone'}:
            return None
        try:
            _capture_clock_interval({'attempt': self.attempt, 'start_ms': sample['epoch_ms'],
                                     'end_ms': sample['epoch_ms'], 'timezone': sample['timezone']}, self.attempt)
        except JsonSafetyError:
            return None
        return dict(sample)

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
            self._clock_start = self._sample_clock(self.page)
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

    def _component_detail_matches(self, value):
        if not self._detail_matches(value):
            return False
        parsed = urlparse(value)
        return (not parsed.params and parsed.query == 'view=true' and not parsed.fragment and re.fullmatch(
            r'/returnsheets/id-ID/corporate-income-tax-return/' + re.escape(self.taxpayer_id)
            + '/' + re.escape(self.record_id) + r'/ICT_RCIT/[^/%\\]+', parsed.path) is not None)

    def _component_probe(self, operation, check_cancel=None):
        self._cancel(check_cancel)
        try:
            value = operation()
        except Exception:
            # Driver failure is unavailable proof; no exception text is forwarded.
            value = None
        self._cancel(check_cancel)
        return value

    def begin_readonly_view(self):
        """Called only after the controller inspects one exact View control."""
        self._cancel()
        if self._view_called:
            raise JsonSafetyError('Inspected View authorization cannot be reused')
        self._view_called = True
        if (not self._active or not self._corporate or self.page.url != self.source_url
                or self.source_url != ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + self.taxpayer_id
                or getattr(self.context, '_spt_financial_route_policy', None) != 'service_workers_blocked'):
            return None
        self._component_listener = self._on_component_navigation
        try:
            self.page.on('framenavigated', self._component_listener)
        except Exception:
            self._component_listener = None
            self._cancel()
            return None
        def retain_document():
            self._component_document = self.page.evaluate_handle('() => document')
            return self._component_document
        self._component_probe(retain_document)
        if self._component_document is None:
            return None
        self._l8_history = self._component_probe(
            lambda: self._component_document.evaluate_handle(_L8_HISTORY))
        owners = self._component_probe(lambda: self.page.evaluate(_COMPONENT_OWNERS))
        same = self._component_probe(lambda: self._component_document.evaluate('(d) => d === document'))
        if owners != {'source_owner': True, 'detail_owner': False} or same is not True:
            return None
        self._component_started = True
        if self.page.url != self.source_url or self._component_transitions:
            self._component_invalid = True
        return None

    def _on_component_navigation(self, frame):
        if not self._active or self._result is not None:
            return
        try:
            if frame is not self.page.main_frame:
                return
            self._component_transitions += 1
            if self._component_transitions != 1 or not self._component_detail_matches(frame.url):
                self._component_invalid = True
            else:
                self._component_target = frame.url
        except Exception:
            self._component_invalid = True

    def observe_component_lifetime(self, *, check_cancel=None):
        """Value-free retained Document and structural owner evidence only."""
        self._cancel(check_cancel)
        self._verify_binding()
        if not self._component_started:
            return None
        if self._component_invalid:
            raise JsonSafetyError('Observed submitted component lifetime changed')
        if (self._component_document is None or self._bound is not self.page
                or self._component_transitions != 1 or self._component_target != self._bound_url):
            return None
        same_before = self._component_probe(
            lambda: self._component_document.evaluate('(d) => d === document'), check_cancel)
        owners = self._component_probe(lambda: self.page.evaluate(_COMPONENT_OWNERS), check_cancel)
        same_after = self._component_probe(
            lambda: self._component_document.evaluate('(d) => d === document'), check_cancel)
        self._verify_binding()
        if (same_before is False or same_after is False or self._component_invalid
                or self._component_observed and owners != {'source_owner': False, 'detail_owner': True}):
            raise JsonSafetyError('Observed submitted component lifetime changed')
        if same_before is not True or same_after is not True or owners != {'source_owner': False, 'detail_owner': True}:
            return None
        proof = _capture_component_lifetime({'attempt': self.attempt,
            'kind': 'corporate-submitted-spa-v1', 'record_id': self.record_id,
            'source_url': self.source_url, 'detail_url': self._bound_url,
            'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True},
            attempt=self.attempt, record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
        self._component_observed = True
        return proof

    def observe_l8_lifetime(self, *, check_cancel=None):
        """Stronger L8-only structural history, armed before the inspected View."""
        self._cancel(check_cancel)
        self._verify_binding()
        self._l8_requested = True
        if self.observe_component_lifetime(check_cancel=check_cancel) is None or self._l8_history is None:
            return None
        state = self._component_probe(lambda: self._l8_history.evaluate('(h) => h.sample()'), check_cancel)
        self._verify_binding()
        if (not isinstance(state, dict) or set(state) != {
                'initial_clear', 'root_seen', 'root_changed', 'dependent_seen'}
                or any(type(value) is not bool for value in state.values())):
            return None
        if state['root_changed']:
            raise JsonSafetyError('Observed corporate L8 root history changed')
        if not state['initial_clear'] or not state['root_seen'] or state['dependent_seen']:
            return None
        return _capture_l8_lifetime({'kind': 'corporate-l8-spa-v1', 'attempt': self.attempt,
            'record_id': self.record_id, 'source_url': self.source_url, 'detail_url': self._bound_url,
            'fresh_root': True, 'stable_root': True, 'no_dependent_forms': True},
            attempt=self.attempt, record_id=self.record_id,
            source_url=self.source_url, detail_url=self._bound_url)

    def _candidate(self, target, frame):
        return (target.context is self.context and frame is target.main_frame
                and frame.parent_frame is None
                and (target is self.page or target.opener() is self.page))

    def _on_request(self, request):
        if not self._active or self._result is not None:
            return
        try:
            # Replacement changes L1-D input despite ordinary capture excluding
            # this prefix. Retain only a value-free veto; never inspect its body.
            if (self._component_listener is not None and request.method == 'POST'
                    and request.url == ORIGIN + '/returnsheet/api/returnsheetsfinancialstatements'
                    and request.frame is self.page.main_frame):
                self._component_invalid = True
            reference = (request.url in self._reference_urls
                         and request.method == 'GET' and request.post_data is None)
            if (not _safe_url(request.url) or request.resource_type not in ('xhr', 'fetch')
                    or not (urlparse(request.url).path.startswith('/returnsheet/api/') or reference)
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
            # Catatan observasi menyimpan metadata request terbatas, termasuk
            # request_json, tanpa menahan objek request/response driver atau
            # byte body respons pada catatan ini.
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
        # Driver membaca seluruh body sekaligus; batas byte/waktu diperiksa lagi
        # sesudahnya, sehingga batas ini bukan jaminan RAM atau interupsi seketika.
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
        seen_before_clock = self._seen
        clock_end = self._sample_clock(self._bound, check_cancel)
        lifetime = self.observe_component_lifetime(check_cancel=check_cancel)
        l8_lifetime = self.observe_l8_lifetime(check_cancel=check_cancel) if self._l8_requested else None
        self._cancel(check_cancel)
        self._verify_binding()
        if self._requests or self._seen != seen_before_clock:
            # Evaluating environment metadata pumps browser events too. A late
            # reply may already be excluded by MIME and absent from _requests.
            # It is outside the final drain, never an empty/complete set.
            self._counts['pending'] += len(self._requests)
            self._reason('response-after-final-drain')
            self._requests.clear()
        result = {'version': 1, 'attempt': self.attempt, 'record_id': self.record_id,
                  'scope': list(self.scope), 'source_url': self.source_url, 'detail_url': self._bound_url,
                  'limits': dict(self._limits), 'counts': dict(self._counts),
                  'complete': not self._reasons, 'reasons': list(self._reasons),
                  'responses': list(self._responses), 'credentials_accessed': False,
                  'primary_identity_validated': False}
        if lifetime is not None:
            result['component_lifetime'] = lifetime
        if l8_lifetime is not None:
            result['corporate_l8_lifetime'] = l8_lifetime
        if self._clock_start is not None and clock_end is not None:
            try:
                result['clock_interval'] = _capture_clock_interval({
                    'attempt': self.attempt, 'start_ms': self._clock_start['epoch_ms'],
                    'end_ms': clock_end['epoch_ms'], 'timezone': clock_end['timezone']}, self.attempt)
            except JsonSafetyError:
                pass  # An unavailable/reversed sample cannot authorize dated selection.
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
            clock = (_capture_clock_interval(saved['clock_interval'], self.attempt)
                     if 'clock_interval' in saved else None)
            lifetime = (_capture_component_lifetime(saved['component_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'component_lifetime' in saved else None)
            l8_lifetime = (_capture_l8_lifetime(saved['corporate_l8_lifetime'], attempt=self.attempt,
                record_id=self.record_id, source_url=self.source_url, detail_url=self._bound_url)
                if 'corporate_l8_lifetime' in saved else None)
            if l8_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L8 history lacks its component lifetime')
            for descriptor in saved['responses']:
                self._cancel(check_cancel)
                relative = Path(descriptor['relative_path'])
                if (relative.is_absolute() or '..' in relative.parts or relative.parent != self._relative
                        or descriptor['attempt'] != self.attempt or 'clock_interval' in descriptor
                        or 'component_lifetime' in descriptor or 'corporate_l8_lifetime' in descriptor):
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
                context = dict(descriptor)
                if clock is not None:
                    context['clock_interval'] = dict(clock)
                if lifetime is not None:
                    context['component_lifetime'] = dict(lifetime)
                if l8_lifetime is not None:
                    context['corporate_l8_lifetime'] = dict(l8_lifetime)
                yield {'body': raw, 'payload': payload, 'context': context}
                del raw, payload
        except (OSError, ValueError, KeyError, TypeError) as error:
            raise JsonSafetyError('Private capture references cannot be safely resolved') from None

    def close(self):
        self._active = False
        self._requests.clear()
        self._observations.clear()
        if self._l8_history is not None:
            try:
                self._l8_history.evaluate('(h) => h.disconnect()')
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            try:
                self._l8_history.dispose()
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            self._l8_history = None
        if self._component_listener is not None:
            try:
                self.page.remove_listener('framenavigated', self._component_listener)
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            self._component_listener = None
        if self._component_document is not None:
            try:
                self._component_document.dispose()
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
            self._component_document = None
        for event, callback in reversed(self._listeners):
            try:
                self.context.remove_listener(event, callback)
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
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


JSON_OUTPUT_LAYOUT = 'tax-kind-v1'
_JSON_TAX_FOLDERS = {'PPh Badan': 'PPh Badan', 'PPh Pasal 21/26': 'SPT PPh 21',
                     'PPh Unifikasi': 'SPT PPh Unifikasi', 'PPN': 'PPN'}


def _json_output_layout(run):
    if 'json_output_layout' not in run:
        return None  # Existing published jobs retain the original ordinal layout.
    layout = run['json_output_layout']
    if not isinstance(layout, str) or layout != JSON_OUTPUT_LAYOUT:
        raise JsonSafetyError('Unsupported JSON output layout')
    return layout


def _published_json_path(name, record, layout):
    if layout is None:
        return name.removeprefix('returns/')
    if not isinstance(layout, str) or layout != JSON_OUTPUT_LAYOUT:
        raise JsonSafetyError('Unsupported JSON output layout')
    # Directory names are fixed presentation labels, never source path fragments.
    tax = record.get('meta', {}).get('Jenis Pajak')
    label = _JSON_TAX_FOLDERS.get(tax, 'SPT Lainnya')
    return 'json/' + label + '/' + name.removeprefix('returns/json/')


def checkpoint_bodies(folder, capture, record, scope, *, published=False,
                      output_layout=None, check_cancel=None):
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
        if check_cancel:
            check_cancel()
        if published:
            name = _published_json_path(name, record, output_layout)
        hold(guard, (root / name).parent)
        with locked_file(root / name) as stream:
            raw = stream.read(maximum + 1)
        if len(raw) > maximum:
            raise JsonSafetyError('Private checkpoint exceeds its byte budget')
        if check_cancel:
            check_cancel()
        return raw

    try:
        with DirectoryGuard() as guard:
            raw = read(guard, reference, 8 * 1024 * 1024)
            if hashlib.sha256(raw).hexdigest() != capture.get('manifest_sha256'):
                raise JsonSafetyError('Private checkpoint manifest bytes changed')
            # Hash saja belum mengikat checkpoint ke SPT terpilih; manifest,
            # metadata, dan upaya capture harus cocok sebelum body dibuka.
            saved = _json(raw)
            if _has_secret(saved):
                raise JsonSafetyError('Private checkpoint metadata no longer meets privacy policy')
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
            clock = (_capture_clock_interval(saved['clock_interval'], saved['attempt'])
                     if 'clock_interval' in saved else None)
            lifetime = (_capture_component_lifetime(saved['component_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'component_lifetime' in saved else None)
            l8_lifetime = (_capture_l8_lifetime(saved['corporate_l8_lifetime'], attempt=saved['attempt'],
                record_id=record['record_id'], source_url=record['list_url'], detail_url=record.get('detail_url'))
                if 'corporate_l8_lifetime' in saved else None)
            if l8_lifetime is not None and lifetime is None:
                raise JsonSafetyError('Private L8 history lacks its component lifetime')
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
                        or 'clock_interval' in descriptor or 'component_lifetime' in descriptor
                        or 'corporate_l8_lifetime' in descriptor
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
                context = dict(descriptor)
                if clock is not None:
                    context['clock_interval'] = dict(clock)
                if lifetime is not None:
                    context['component_lifetime'] = dict(lifetime)
                if l8_lifetime is not None:
                    context['corporate_l8_lifetime'] = dict(l8_lifetime)
                packets.append({'body': body, 'payload': payload, 'context': context})
            return packets
    except (OSError, ValueError, TypeError, KeyError, IndexError):
        raise JsonSafetyError('Private checkpoint custody cannot be safely verified') from None


def _json_output_entries(run):
    """Derive a closed file set; never enumerate private job directories."""
    from pathlib import PurePosixPath
    layout = _json_output_layout(run)
    entries, seen, sources = [], set(), set()
    for record in run['records']:
        audit = record.get('detail_source')
        if audit is None:
            continue
        if not isinstance(audit, dict):
            raise JsonSafetyError('Invalid JSON evidence audit')
        capture = audit.get('capture')
        if capture is None and audit.get('used') != 'json':
            continue
        if not isinstance(capture, dict):
            raise JsonSafetyError('Missing JSON evidence capture')
        reference = capture.get('manifest')
        if (not isinstance(reference, str) or not re.fullmatch(
                r'returns/json/[0-9]{4,}/[a-f0-9]{32}/manifest\.json', reference)):
            raise JsonSafetyError('Unsafe JSON evidence manifest path')
        responses = capture.get('responses')
        if not isinstance(responses, list) or len(responses) > MAX_RESPONSES:
            raise JsonSafetyError('Invalid JSON evidence response set')
        items = [{'source_path': reference, 'sha256': capture.get('manifest_sha256'),
                  'maximum': 8 * 1024 * 1024}]
        for descriptor in responses:
            name = descriptor.get('relative_path') if isinstance(descriptor, dict) else None
            if (not isinstance(name, str) or '\\' in name or ':' in name
                    or PurePosixPath(name).parent != PurePosixPath(reference).parent
                    or not re.fullmatch(r'response-[0-9]{4,}\.json', PurePosixPath(name).name)):
                raise JsonSafetyError('Unsafe JSON evidence response path')
            items.append({'source_path': name, 'sha256': descriptor.get('sha256'),
                          'maximum': MAX_BODY_BYTES, 'bytes': descriptor.get('bytes')})
        for item in items:
            name = _published_json_path(item['source_path'], record, layout)
            digest = item['sha256']
            if (name.casefold() in seen or item['source_path'] in sources
                    or not isinstance(digest, str)
                    or not re.fullmatch(r'[0-9a-f]{64}', digest)):
                raise JsonSafetyError('Duplicate or invalid JSON evidence declaration')
            seen.add(name.casefold())
            sources.add(item['source_path'])
            item['relative_path'] = name
        entries.append((record, capture, items))
    return entries


def json_output_names(run):
    return [item['relative_path'] for _, _, items in _json_output_entries(run) for item in items]


def verified_json_names(run):
    expected = json_output_names(run)
    if run.get('output_json', [] if not expected else None) != expected:
        raise JsonSafetyError('JSON output declaration differs from selected captures')
    return expected


def _verify_json_stream(stream, item, check_cancel=None):
    stream.seek(0)
    digest, total = hashlib.sha256(), 0
    for chunk in iter(lambda: stream.read(1048576), b''):
        if check_cancel:
            check_cancel()
        total += len(chunk)
        if total > item['maximum']:
            raise JsonSafetyError('JSON evidence exceeds its byte budget')
        digest.update(chunk)
    if (digest.hexdigest() != item['sha256']
            or 'bytes' in item and total != item['bytes']):
        raise JsonSafetyError('JSON evidence bytes changed')
    stream.seek(0)


@contextmanager
def json_custody(run, folder, *, published=True, target_layout=None, check_cancel=None):
    """Hold source-layout bytes; optionally relocate the same declared evidence."""
    if published:
        verified_json_names(run)
    entries = _json_output_entries(run)
    destinations = (_json_output_entries({**run, 'json_output_layout': target_layout})
                    if target_layout is not None else entries)
    target_items = {item['source_path']: item for _, _, items in destinations for item in items}
    if not entries:
        yield [], {}
        return
    root = Path(folder).absolute()
    if '..' in root.parts:
        raise JsonSafetyError('Unsafe JSON evidence folder')
    with DirectoryGuard() as guard, ExitStack() as readers:
        streams, items = {}, []
        for record, capture, record_items in entries:
            # Bind every byte to the unchanged manifest and literal selected scope.
            packets = checkpoint_bodies(root, capture, record,
                [run['npwp'], run['year'], run['year_basis']],
                published=published, output_layout=_json_output_layout(run), check_cancel=check_cancel)
            del packets
            for item in record_items:
                if check_cancel:
                    check_cancel()
                name = item['relative_path'] if published else item['source_path']
                parent = (root / name).parent
                guard.include({p: _ordinary_directory(p) for p in reversed([parent, *parent.parents])})
                stream = readers.enter_context(locked_file(root / name))
                _verify_json_stream(stream, item, check_cancel)
                destination = target_items[item['source_path']]
                streams[destination['relative_path']] = stream
                items.append(destination)
        yield items, streams
        for item in items:
            _verify_json_stream(streams[item['relative_path']], item, check_cancel)


def verify_existing_json(run, folder):
    """Refuse changed selected destination evidence before CLI replacement.

    A destination can contain only some selected attempts. Missing new files
    are allowed; every existing selected file must match its declared bytes.
    """
    entries = _json_output_entries(run)  # Validate the declared source layout first.
    if not entries:
        return
    legacy = {key: value for key, value in run.items() if key != 'json_output_layout'}
    # A migration must not hide changed selected evidence left at its old path.
    variants = (legacy, {**legacy, 'json_output_layout': JSON_OUTPUT_LAYOUT})
    selected = {item['relative_path']: item for variant in variants
                for _, _, items in _json_output_entries(variant) for item in items}
    root = Path(folder).absolute()
    if '..' in root.parts:
        raise JsonSafetyError('Unsafe JSON evidence destination')
    with DirectoryGuard() as guard:
        guard.include({p: _ordinary_directory(p) for p in reversed([root, *root.parents])})
        for item in selected.values():
            parent = root
            parts = Path(item['relative_path']).parts
            for index, component in enumerate(parts):
                if any(p.name.casefold() == component.casefold() and p.name != component
                       for p in parent.iterdir()):
                    raise JsonSafetyError('JSON evidence destination has a case alias')
                target = parent / component
                if not target.exists() and not target.is_symlink():
                    break
                if index == len(parts) - 1:
                    with locked_file(target) as stream:
                        _verify_json_stream(stream, item)
                else:
                    guard.include({target: _ordinary_directory(target)})
                    parent = target


def copy_held_json(items, streams, folder, check_cancel=None):
    """Copy declared evidence only; manifests retain their original references."""
    root = Path(folder).absolute()
    with DirectoryGuard() as guard:
        for item in items:
            if check_cancel:
                check_cancel()
            target = root / item['relative_path']
            for parent in reversed([target.parent, *target.parent.parents]):
                if parent == root or parent.is_relative_to(root):
                    parent.mkdir(exist_ok=True)
                    guard.include({p: _ordinary_directory(p) for p in reversed([parent, *parent.parents])})
            stream = streams[item['relative_path']]
            _verify_json_stream(stream, item, check_cancel)
            with target.open('xb') as destination:
                for chunk in iter(lambda: stream.read(1048576), b''):
                    if check_cancel:
                        check_cancel()
                    destination.write(chunk)
            with locked_file(target) as copied:
                _verify_json_stream(copied, item, check_cancel)
            stream.seek(0)
