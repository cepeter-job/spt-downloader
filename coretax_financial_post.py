"""One inspected financial-document POST, captured before transport and replayed once."""
import hashlib
import json
import re
import time
from urllib.parse import urlparse
import uuid

from coretax_browser import list_taxpayer_id
from spt_desktop import diagnostics

_NONCE = 'x-spt-financial-nonce'
_SOURCE_LIMIT = 8 * 1024 * 1024
_BODY_LIMIT = 4096
_AUTHORIZATION_LIMIT = 64 * 1024

_SOURCE_NODES = r'''({pins, document_url}) => {
    if (location.href !== document_url) throw new Error('Financial document changed');
    if (!window._spt_financial_nodes) Object.defineProperty(window, '_spt_financial_nodes',
        {value: new WeakMap(), configurable: true});
    return Object.keys(pins).map(path => {
        const url = new URL(path, location.origin).href;
        const scripts = [...document.scripts].filter(script=>script.src===url && script.isConnected);
        const loads = performance.getEntriesByType('resource')
            .filter(entry=>entry.name===url && entry.initiatorType==='script');
        // Webpack menghapus tag lazy chunk sesudah load. Timing tetap terikat dokumen.
        if (scripts.length > 1 || loads.length !== 1) throw new Error('Unsupported financial source');
        const node = scripts[0], nodes = window._spt_financial_nodes;
        if (node && !nodes.has(node)) nodes.set(node, crypto.randomUUID());
        return {path, identity: node ? nodes.get(node) : null,
            loaded_at: loads[0].startTime, duration: loads[0].duration};
    });
}'''

_SOURCE_HASH = r'''async ({path, limit, document_url}) => {
    if (location.href !== document_url) throw new Error('Financial document changed');
    const url = new URL(path, location.origin).href, controller = new AbortController();
    const timer = setTimeout(()=>controller.abort(), 15000);
    let reader = null;
    try {
        const response = await fetch(url, {method: 'GET', credentials: 'same-origin',
            redirect: 'error', cache: 'no-store', signal: controller.signal});
        const size = response.headers.get('content-length');
        if (!response.ok || response.url !== url || response.redirected || !response.body ||
            (size !== null && (!/^\d+$/.test(size) || Number(size)>limit)))
            throw new Error('Unsupported financial source');
        reader = response.body.getReader();
        let length=0; const chunks=[];
        while (true) {
            const {done,value} = await reader.read();
            if (done) break;
            length += value.byteLength;
            if (length>limit) throw new Error('Unsupported financial source');
            chunks.push(value);
        }
        const bytes = new Uint8Array(length); let offset=0;
        for (const chunk of chunks) {bytes.set(chunk,offset); offset+=chunk.length;}
        const digest = new Uint8Array(await crypto.subtle.digest('SHA-256',bytes));
        return [...digest].map(value=>value.toString(16).padStart(2,'0')).join('');
    } finally {
        controller.abort(); clearTimeout(timer);
        if (reader) reader.cancel().catch(()=>{});
    }
}'''


def _cancel(check_cancel):
    if check_cancel:
        check_cancel()


def _policy(page):
    # Hanya pembuat context berizin yang menandai service_workers='block'.
    # Tidak adanya worker saat ini tidak menjamin route tidak dapat dilewati.
    if getattr(page.context, '_spt_financial_route_policy', None) != 'service_workers_blocked':
        raise ValueError('Financial POST requires an owned service-worker-blocked context')


def verify_sources(page, pins, document_url, check_cancel=None):
    """Hash only loaded, pinned public sources, bounded independently of PDF data."""
    _policy(page)
    if (not isinstance(pins, dict) or not pins or any(
            not isinstance(path, str) or not path.startswith('/returnsheets/id-ID/')
            or not path.endswith('.js') or '?' in path or '#' in path
            or not isinstance(digest, str) or len(digest) != 64
            or any(char not in '0123456789abcdef' for char in digest)
            for path, digest in pins.items())):
        raise ValueError('Financial source pins are not supported')
    arguments = {'pins': pins, 'document_url': document_url}
    nodes = page.evaluate(_SOURCE_NODES, arguments)
    for path, expected in pins.items():
        _cancel(check_cancel)
        digest = page.evaluate(_SOURCE_HASH, {'path': path, 'limit': _SOURCE_LIMIT,
                                             'document_url': document_url})
        _cancel(check_cancel)
        if digest != expected:
            raise ValueError('Financial source build is not supported')
    if page.evaluate(_SOURCE_NODES, arguments) != nodes:
        raise ValueError('Financial source document changed')
    return nodes


def _text(value, limit):
    return (isinstance(value, str) and 0 < len(value) <= limit and value == value.strip()
            and not any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value))


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Financial body contains duplicate keys')
        result[key] = value
    return result


def _selected_corporate_detail(url, record):
    """Accept only inspected route shapes, with literal selected identities."""
    detail, listed = urlparse(url), urlparse(record['list_url'])
    if detail.fragment or detail.params:
        return False
    taxpayer = list_taxpayer_id(record['list_url'])
    if not all(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9_-]+', value)
               for value in (taxpayer, record.get('record_id'))):
        return False
    prefix = '/returnsheets/id-ID/'
    list_path = listed.path.rstrip('/')
    if list_path == prefix + 'corporatereturnsheets/' + taxpayer:
        return not detail.query and detail.path == list_path + '/' + record['record_id']
    if list_path != prefix + 'submitted-returnsheets/' + taxpayer:
        return False
    # The inspected submitted View link carries this literal read-only flag.
    # Do not parse/normalize aliases, duplicate keys, history or extra parameters.
    if detail.query not in ('', 'view=true'):
        return False
    expected = (prefix + 'corporate-income-tax-return/' + taxpayer + '/'
                + record['record_id'] + '/ICT_RCIT/')
    # The opaque context comes from the inspected active URL, never a guessed
    # document identifier. Exact document equality is checked throughout replay.
    return (detail.path.startswith(expected) and re.fullmatch(
        r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}',
        detail.path[len(expected):]) is not None)


class FinancialPost:
    """Own the temporary route and secret envelope through verified persistence."""

    def __init__(self, page, record, control, pins, sources, scan, verify_scope, check_cancel):
        self.page = page
        self.record = record
        self.control = control
        self.pins = pins
        self.sources = sources
        self.scan = scan
        self.verify_scope = verify_scope
        self.check_cancel = check_cancel
        parsed = urlparse(control['document_url'])
        self.url = f'{parsed.scheme}://{parsed.netloc}/documentmanagement/api/download'
        self.button = None
        self.envelope = {}
        self.phase = 'capture'
        self.count = 0
        self.replayed = False
        self.invalid = False
        self.guard = 'context'
        self.stopped = None
        self.nonce = uuid.uuid4().hex
        self.handler = self._route
        self.armed = False

    def check(self):
        if self.stopped is not None:
            raise self.stopped
        _cancel(self.check_cancel)
        _policy(self.page)
        self.verify_scope(self.page, self.record)
        if not _selected_corporate_detail(self.page.url, self.record):
            raise ValueError('Financial POST requires the selected corporate return detail')
        if self.invalid or self.page.url != self.control['document_url']:
            raise ValueError('Financial request or document changed')
        controls = self.page.evaluate(self.scan)['controls']
        if controls.count(self.control) != 1:
            raise ValueError('Inspected financial button changed')
        if self.button is not None and not self.button.evaluate(
                '''(button, control) => button.isConnected &&
                    button === document.querySelectorAll('.main-content button')[control.button_index] &&
                    window._spt_financial_nodes?.get(button) === control.identity''', self.control):
            raise ValueError('Inspected financial button was replaced')
        if self.page.evaluate(_SOURCE_NODES, {'pins': self.pins,
                'document_url': self.control['document_url']}) != self.sources:
            raise ValueError('Inspected financial source changed')

    def _capture(self, request, headers):
        self.guard = 'body'
        raw = request.post_data
        if not isinstance(raw, str) or len(raw.encode('utf-8')) > _BODY_LIMIT:
            raise ValueError('Unsupported financial request body')
        body = json.loads(raw, object_pairs_hook=_unique_object)
        if not isinstance(body, dict) or set(body) != {'DocumentId', 'TaxpayerAggregateIdentifier'}:
            raise ValueError('Unsupported financial request fields')
        if not all(_text(value, 512) for value in body.values()):
            raise ValueError('Unsupported financial request values')
        if body['TaxpayerAggregateIdentifier'] != list_taxpayer_id(self.record['list_url']):
            raise ValueError('Financial request does not match the selected taxpayer')
        self.guard = 'authentication'
        content_type = headers.get('content-type', '')
        if (content_type.split(';', 1)[0].strip().lower() != 'application/json'
                or not _text(content_type, 256)):
            raise ValueError('Unsupported financial request content type')
        authorization = headers.get('authorization')
        if not isinstance(authorization, str) or not authorization:
            raise ValueError('Financial request authorization is missing')
        if len(authorization) > _AUTHORIZATION_LIMIT:
            raise ValueError('Financial request authorization exceeds budget')
        if not _text(authorization, _AUTHORIZATION_LIMIT):
            raise ValueError('Unsupported financial request authorization text')
        if headers.get('request_from') != self.control['document_url']:
            raise ValueError('Unsupported financial request origin context')
        retained = {name: headers[name] for name in ('content-type', 'authorization', 'request_from')}
        if 'accept' in headers:
            if not _text(headers['accept'], 1024):
                raise ValueError('Unsupported financial request Accept header')
            retained['accept'] = headers['accept']
        self.envelope.update(body=raw, headers=retained)
        diagnostics.record('pdf.request_captured', phase='pdf',
            authorization_budget='within_8k' if len(authorization) <= 8192 else 'above_8k')

    def _route(self, route):
        request = route.request
        try:
            self.guard = 'context'
            headers = request.all_headers()
            nonce = headers.get(_NONCE)
            if request.method in ('GET', 'HEAD') and nonce is None:
                route.fallback()
                return
            self.check()
            self.guard = 'route'
            if (request.method != 'POST' or request.url != self.url
                    or request.frame != self.page.main_frame
                    or request.resource_type not in ('xhr', 'fetch')
                    or request.is_navigation_request()):
                raise ValueError('Unsupported financial request route')
            if self.phase == 'capture':
                self.guard = 'count'
                self.count += 1
                if self.count != 1 or nonce is not None:
                    raise ValueError('Multiple financial requests are not supported')
                self._capture(request, headers)
                # Request aplikasi pertama selalu dibatalkan; tidak ada byte backend.
                route.abort('blockedbyclient')
                return
            self.guard = 'replay'
            if (self.phase != 'replay' or self.replayed or nonce != self.nonce
                    or request.post_data != self.envelope.get('body')
                    or any(headers.get(name) != value
                           for name, value in self.envelope.get('headers', {}).items())):
                raise ValueError('Financial replay is not the captured request')
            self.replayed = True
            # Nonce hanya pembeda lokal. Context guard tetap memeriksa request.
            route.fallback(headers={name: value for name, value in headers.items() if name != _NONCE})
        except BaseException as error:
            first = not self.invalid
            self.invalid = True
            if first:
                # Summarize immediately: do not retain traceback locals/headers.
                diagnostics.record('pdf.request_rejected', level='WARNING', phase='pdf',
                    pdf_guard=self.guard, error=error,
                    status='PARTIAL' if isinstance(error, Exception) else 'CANCELLED')
            if not isinstance(error, Exception):
                self.stopped = error
            try:
                route.abort('blockedbyclient')
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass

    def __enter__(self):
        try:
            self.check()
            self.button = self.page.query_selector_all('.main-content button')[self.control['button_index']]
            self.check()
            self.page.route('**/*', self.handler)
            self.armed = True
            self.check()
            # Pemeriksaan terakhir dan click berbagi satu evaluasi dokumen.
            click = '''(button, control) => {
                const scan = (''' + self.scan + ''');
                const matches = scan().controls.filter(item=>
                    Object.keys(item).length === Object.keys(control).length &&
                    Object.keys(control).every(key=>item[key]===control[key]));
                if (matches.length !== 1 || !button.isConnected ||
                    window.location.href !== control.document_url ||
                    window._spt_financial_nodes?.get(button) !== control.identity)
                    throw new Error('Inspected financial button changed before click');
                button.click();
            }'''
            self.button.evaluate(click, self.control)
            deadline = time.monotonic() + 2
            while not self.count and not self.invalid and time.monotonic() < deadline:
                _cancel(self.check_cancel)
                self.page.wait_for_timeout(25)
            # Pump queued XHRs before replay; two synchronous requests authorize none.
            self.page.wait_for_timeout(150)
            self.check()
            if self.count != 1 or not self.envelope:
                raise ValueError('No unique inspected financial request was captured')
            self.phase = 'replay'
            return self
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def request(self):
        self.check()
        return {'method': 'POST', 'body': self.envelope['body'],
                'headers': {**self.envelope['headers'], _NONCE: self.nonce}}

    def identity(self):
        # Tidak ada header/token dalam nama file atau checkpoint.
        digest = hashlib.sha256(self.envelope['body'].encode('utf-8')).hexdigest()
        return self.url + '\0' + digest

    def verified(self):
        self.check()
        if not self.replayed:
            raise ValueError('Financial request did not pass the scoped replay guard')

    def __exit__(self, *_):
        if self.armed:
            try:
                self.page.unroute('**/*', self.handler)
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
        self.armed = False
        if self.button is not None:
            try:
                self.button.dispose()
            except Exception:  # nosec B110 - Owned cleanup is best effort; preserve the original outcome.
                pass
        self.button = None
        self.envelope.clear()
        self.nonce = ''
        self.stopped = None
