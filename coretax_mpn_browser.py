"""Owned Accounting observers, separate from all native SPT admission rules."""
from copy import deepcopy
import time
from urllib.parse import urlsplit

from coretax_mpn import (ORIGIN, MpnSafetyError, MpnUnsupported, decode_mpn,
                         source_integer, _identity)

LIST_PATH = '/accounting/api/taxpayeraccounting/list'
DETAIL_PATH = '/accounting/api/taxpayeraccounting/listdetail'


class AccountingObserver:
    """Bind original response bytes to current committed request objects.

Only one latest snapshot per grid is retained. Pending requests are bounded and
released on response/failure/close. Failures are fixed categories, never saved
exceptions, tracebacks, URLs, request bodies or authentication material.
"""
    def __init__(self, page, taxpayer_id, folder, check_cancel=None):
        if not _identity(taxpayer_id):
            raise MpnSafetyError('MPN taxpayer identity is unsupported')
        self.page, self.taxpayer_id = page, taxpayer_id
        self.folder, self.check_cancel = folder, check_cancel
        self.sequence = 0
        self.pending = {}
        self.latest = {}
        self.navigation_source = None
        self.committed = False
        self.safety_failed = False
        self.failed = False
        self.parent_id = None
        self.closed = False
        self.handlers = {'framenavigated': self.on_navigation, 'request': self.on_request,
                         'requestfailed': self.on_request_failed, 'response': self.on_response}
        for event, callback in self.handlers.items():
            page.on(event, callback)

    def _stop(self):
        if self.check_cancel:
            self.check_cancel()

    def _reject(self, *, safety=False):
        if safety:
            self.safety_failed = True
        else:
            self.failed = True
        self.pending.clear()
        self.latest.clear()

    def begin_navigation(self, url):
        self._stop()
        expected = ORIGIN + '/accounting/id-ID/balancesheet/' + self.taxpayer_id
        if url != expected or self.closed:
            raise MpnSafetyError('MPN navigation is outside its literal owned route')
        self.navigation_source = expected
        self.committed = self.safety_failed = self.failed = False
        self.pending.clear()
        self.latest.clear()
        self.parent_id = None

    def on_navigation(self, frame):
        if self.closed or self.navigation_source is None or frame is not self.page.main_frame:
            return
        if self.committed or frame.url != self.navigation_source:
            self._reject(safety=True)
            return
        self.committed = True

    def _kind(self, request):
        if getattr(request, 'frame', None) is not self.page.main_frame:
            return None
        parsed = urlsplit(request.url)
        if parsed.path not in (LIST_PATH, DETAIL_PATH):
            return None
        if request.url not in (ORIGIN + LIST_PATH, ORIGIN + DETAIL_PATH):
            raise MpnSafetyError('MPN grid endpoint contradicts its inspected route')
        return 'list' if parsed.path == LIST_PATH else 'detail'

    def _posted(self, request, kind):
        if request.method != 'POST' or request.resource_type not in ('xhr', 'fetch'):
            raise MpnUnsupported('MPN grid request method/type is unsupported')
        raw = getattr(request, 'post_data', None)
        if type(raw) is not str:
            raise MpnUnsupported('MPN original grid request is unavailable')
        data = decode_mpn(raw.encode('utf-8'))
        key = 'TaxpayerAggregateIdentifier' if kind == 'list' else 'RecordId'
        if set(data) != {key, 'First', 'Rows', 'SortField', 'SortOrder', 'LanguageId', 'Filters'}:
            raise MpnUnsupported('MPN grid request shape is unsupported')
        if data[key] != (self.taxpayer_id if kind == 'list' else self.parent_id):
            raise MpnSafetyError('MPN grid request contradicts its owned identity')
        first, size = source_integer(data['First']), source_integer(data['Rows'])
        if (size not in (10, 25, 50) or first % size or data['LanguageId'] != 'en-US'
                or data['SortField'] != ('PostingDate' if kind == 'list' else 'TransactionDate')
                or str(data['SortOrder']) != '-1' or not isinstance(data['Filters'], list)
                or (kind == 'detail' and data['Filters'] != [])):
            raise MpnUnsupported('MPN grid pagination/language/filter shape is unsupported')
        data['First'], data['Rows'] = first, size
        return data

    def on_request(self, request):
        if self.closed or not self.committed or self.safety_failed or self.failed:
            return
        try:
            kind = self._kind(request)
            if kind is None:
                return
            if self.page.url != self.navigation_source or len(self.pending) >= 128:
                raise MpnSafetyError('MPN request document/pending custody changed')
            posted = self._posted(request, kind)
            self.pending[id(request)] = (request, kind, posted)
        except MpnSafetyError:
            self._reject(safety=True)
        except Exception:
            self._reject()

    def on_request_failed(self, request):
        entry = self.pending.pop(id(request), None)
        if entry is not None and entry[0] is request:
            self._reject()

    def on_response(self, response):
        request = response.request
        entry = self.pending.pop(id(request), None)
        if entry is None or entry[0] is not request or self.closed or self.safety_failed or self.failed:
            return
        _, kind, posted = entry
        try:
            if (self.page.url != self.navigation_source or response.url != request.url
                    or self._posted(request, kind) != posted):
                raise MpnSafetyError('MPN response document/request binding changed')
            if not 200 <= response.status < 300 or 'json' not in response.headers.get('content-type', '').lower():
                raise MpnUnsupported('MPN owned grid response failed')
            raw = response.body()
            decoded = decode_mpn(raw)
            if decoded.get('IsSuccessful') is not True:
                raise MpnUnsupported('MPN owned grid response is unsuccessful')
            payload = decoded.get('Payload')
            if not isinstance(payload, dict) or not isinstance(payload.get('Data'), list):
                raise MpnUnsupported('MPN grid payload is unsupported')
            total = source_integer(payload.get('TotalRecords'))
            rows = payload['Data']
            if (len(rows) != min(posted['Rows'], max(0, total - posted['First']))
                    or posted['First'] > total or not all(isinstance(row, dict) for row in rows)):
                raise MpnUnsupported('MPN page count does not reconcile')
            for row in rows:
                if not _identity(row.get('RecordId')):
                    raise MpnUnsupported('MPN source row identity is unavailable')
                if kind == 'list':
                    if row.get('TaxpayerAggregateIdentifier') != self.taxpayer_id:
                        raise MpnSafetyError('MPN header taxpayer identity changed')
                elif row.get('HeaderRecordId') != self.parent_id:
                    raise MpnSafetyError('MPN detail header identity changed')
            self.sequence += 1
            self.latest[kind] = {'sequence': self.sequence, 'kind': kind, 'total': total,
                                 'first': posted['First'], 'page_size': posted['Rows'],
                                 'rows': rows, 'raw': raw, 'request': deepcopy(posted),
                                 'parent_id': self.parent_id if kind == 'detail' else None}
        except MpnSafetyError:
            self._reject(safety=True)
        except Exception:
            self._reject()

    def begin_detail(self, parent_id):
        self._check_state()
        if not _identity(parent_id):
            raise MpnSafetyError('MPN selected header identity is unsupported')
        # No late reply to a previous selected parent can certify this one.
        self.pending = {key: entry for key, entry in self.pending.items() if entry[1] != 'detail'}
        self.latest.pop('detail', None)
        self.parent_id = parent_id

    def _check_state(self):
        self._stop()
        if (self.closed or self.safety_failed or not self.committed
                or self.page.url != self.navigation_source):
            raise MpnSafetyError('MPN owned document/request identity changed')
        if self.failed:
            raise MpnUnsupported('MPN owned grid capture failed')

    def wait(self, after, kind, timeout=45):
        if kind not in ('list', 'detail'):
            raise ValueError('Unsupported MPN grid kind')
        deadline = time.monotonic() + timeout
        while True:
            self._check_state()
            snapshot = self.latest.get(kind)
            if snapshot is not None and snapshot['sequence'] > after:
                return snapshot
            if time.monotonic() >= deadline:
                raise MpnUnsupported('MPN fresh grid response timed out')
            self.page.wait_for_timeout(100)

    def close(self):
        if self.closed:
            return
        for event, callback in self.handlers.items():
            self.page.remove_listener(event, callback)
        self.pending.clear()
        self.latest.clear()
        self.parent_id = self.navigation_source = None
        self.closed = True
