"""Inspected Accounting UI navigation only; never manufacture/replay a POST."""
import hashlib
import re
import time
from urllib.parse import urlsplit
from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeoutError

from coretax_mpn import (ORIGIN, MpnUnsupported, MpnSafetyError, decode_mpn,
                         dom_numbers_match, parent_numeric_binding, taxpayer_id, captured_catalogs,
                         source_display_date as _date, validate_page_total)
from coretax_mpn_browser import AccountingObserver, _digest
from spt_desktop import diagnostics

SOURCE_PINS = {
    '/accounting/id-ID/main.fedea3c4d025195e.js': '7a76f131ac13b124087c4c968154d0f73c26a92069dc8d6dd59791f908d4bdf1',
    '/accounting/id-ID/vendor.5900c4ddec796b87.js': 'b876e4421e8d8caa81b98928f23e672e5da7069fa7ab30ab14318b5f3726af5c',
}
REFERENCE_PATH = ('/referencedata/api/currentreferencedata/id-ID/'
                  'ACCOUNTING_TYPE,ACCOUNTING_TYPE_DETAIL,REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT,PERIOD')


def _reference_route_kind(url):
    # Classification only. Neither query variants nor neighboring paths are
    # permitted sources; they must NEVER be admitted to source_pending.
    if type(url) is not str or url == ORIGIN + REFERENCE_PATH:
        return 'not_observed'
    parts, expected = urlsplit(url), urlsplit(ORIGIN)
    if (parts.scheme != expected.scheme or parts.netloc != expected.netloc
            or not parts.path.startswith('/referencedata/api/currentreferencedata/id-ID/')):
        return 'not_observed'
    return 'query_variant' if parts.path == REFERENCE_PATH else 'path_variant'


def _other_reference_get(url):
    return _reference_route_kind(url) != 'not_observed'

LIST_HEADERS = ('Aksi', 'Tanggal Transaksi', 'Tanggal Posting', 'Jenis Pencatatan',
                'Detail Jenis Pencatatan', 'Mata Uang', 'Jenis Transaksi', 'Nilai Mata Uang',
                'Nilai Sisa dalam Mata Uang', 'Nilai Tukar', 'Jumlah', 'Nilai Sisa',
                'Referensi', 'KAP', 'Deskripsi KAP', 'KJS', 'Masa Pajak', 'Nomor Transaksi',
                'Tanggal Jatuh Tempo Pembayaran', 'Tanggal Utang Pajak Dapat Ditagih',
                'Tanggal Daluwarsa', 'Dibatalkan', 'NOP', 'Dapat Digunakan')
DETAIL_HEADERS = ('Tanggal Transaksi', 'Tanggal Posting', 'Nomor Transaksi',
                  'Jenis Pencatatan', 'Detail Jenis Pencatatan', 'Nilai Mata Uang',
                  'Nilai Tukar Transaksi Induk', 'Jumlah', 'Referensi')
REFERENCE_TAX_TYPES = frozenset((
    'LBT_LBT', 'ICT_OGT', 'ICT_WT', 'SDT_SDT', 'ICT_PIT', 'ICT_RCIT', 'ICT_DCIT',
    'ICT_NADFIT', 'ICT_ITA25ICDM', 'ICT_ITA25ICDQ', 'ICT_ITA25ICDA', 'VAT_VAT',
    'VAT_DVAT', 'VAT_VATTNTEVATC', 'LBT_LBTR', 'ICT_OGTR', 'SDT_SDTR', 'ICT_WTR',
    'ICT_PITR', 'ICT_RCITR', 'ICT_DCITR', 'VAT_VATR', 'VAT_DVATR',
    'VAT_VATTRNTEVATC', 'ICT_WIT', 'AUDIT'))
TABLE_JS = r'''table => {
 const text=e=>{
   const copy=e.cloneNode(true);
   for(const duplicate of copy.querySelectorAll('.p-column-title')) duplicate.remove();
   return (copy.textContent||'').replace(/\s+/g,' ').trim();
 };
 const headers=[...(table.tHead?.rows||[])].filter(row=>
   !row.querySelector('input,select,p-columnfilter')).map(row=>[...row.cells].map(text));
 const body=[...table.tBodies].flatMap(body=>[...body.rows]).filter(row=>
   !row.classList.contains('p-datatable-emptymessage') &&
   !(row.cells.length===1 && row.cells[0].colSpan>1));
 if(body.some(row=>[...row.cells].some(cell=>cell.colSpan!==1||cell.rowSpan!==1))) return null;
 return {headers,rows:body.map(row=>[...row.cells].map(text))};
}'''


def prepare_accounting_session(page, run, *, check_cancel=None):
    """Finish the observed normal session transition before capture exists.

    No source/grid bytes, credentials, callback query or browser storage are read.
    The caller constructs its observer only after this listener has been removed.
    """
    if getattr(page.context, '_spt_financial_route_policy', None) != 'service_workers_blocked':
        raise MpnUnsupported('MPN requires the reviewed owned browser context')
    selected = ORIGIN + '/accounting/id-ID/balancesheet/' + taxpayer_id(run)
    refused = False
    # Record only whether the original reference GET happened during the
    # navigation that precedes AccountingUI's source-binding listeners.
    # No response bytes/cache are read; seeing this request is NOT admission.
    preparation_catalog_seen = False
    preparation_reference_variant = False
    preparation_variant_kind = 'not_observed'
    deadline = time.monotonic() + 60

    def reference_request(request):
        nonlocal preparation_catalog_seen, preparation_reference_variant, preparation_variant_kind
        # Inspect the frame only for a recognized reference GET; never log
        # or read any URL, query, body, response or taxpayer identifier.
        if request.method != 'GET' or request.resource_type not in ('xhr', 'fetch'):
            return
        url = request.url
        exact = url == ORIGIN + REFERENCE_PATH
        variant_kind = _reference_route_kind(url)
        if (exact or variant_kind != 'not_observed') and request.frame is page.main_frame:
            preparation_catalog_seen |= exact
            preparation_reference_variant |= variant_kind != 'not_observed'
            if variant_kind == 'path_variant' or preparation_variant_kind == 'not_observed':
                preparation_variant_kind = variant_kind

    def allowed(url):
        if '#' in url:
            return False
        if url in (selected, ORIGIN + '/', ORIGIN + '/accounting/id-ID/'):
            return True
        parts = urlsplit(url)
        return (parts.scheme == 'https' and parts.netloc == urlsplit(ORIGIN).netloc
                and parts.path == '/accounting/id-ID/auth-callback' and not parts.fragment)

    def navigation(frame):
        nonlocal refused
        if frame is page.main_frame and not allowed(frame.url):
            refused = True

    def check():
        if check_cancel:
            check_cancel()
        if refused or not allowed(page.url):
            raise MpnSafetyError('MPN session preparation left its inspected routes')
        if time.monotonic() >= deadline:
            raise MpnUnsupported('MPN session preparation deadline exceeded')

    if check_cancel:
        check_cancel()
    page.on('framenavigated', navigation)
    page.on('request', reference_request)
    try:
        page.goto(selected, wait_until='domcontentloaded', timeout=60000)
        while True:
            check()
            owner = page.locator('acc-balance-sheet-light')
            count = owner.count()
            check()
            if count > 1:
                raise MpnUnsupported('MPN session owner is ambiguous')
            visible = count == 1 and owner.is_visible()
            check()
            if visible and page.url == selected:
                return
            page.wait_for_timeout(min(100, max(1, int((deadline - time.monotonic()) * 1000))))
    finally:
        page.remove_listener('request', reference_request)
        page.remove_listener('framenavigated', navigation)
        diagnostics.record('mpn.catalog_preparation', level='INFO',
                           mpn_catalog_preparation=('request_seen' if preparation_catalog_seen
                                                    else 'not_observed'),
                           mpn_catalog_route_shape=('alternate_reference_get'
                                                    if preparation_reference_variant else 'not_observed'),
                           mpn_catalog_variant_kind=preparation_variant_kind)


class AccountingUI:
    def __init__(self, page, run, folder, *, check_cancel=None):
        self.page, self.run, self.folder = page, run, folder
        self.check_cancel = check_cancel
        self.taxpayer = taxpayer_id(run)
        self.url = ORIGIN + '/accounting/id-ID/balancesheet/' + self.taxpayer
        self.observer = AccountingObserver(page, self.taxpayer, folder, check_cancel)
        self.pins, self.catalogs, self.catalog = {}, {}, {}
        self.catalog_codes = {}
        self.source_failed = False
        self.source_safety = False
        self.source_rejection_recorded = False
        self.source_pending = {}
        self.source_ready = {}
        self.source_sequence = 0
        self.catalog_frozen = False
        self.closed = False
        self.reference_raw = None
        self.reference_request_seen = False
        self.reference_route_variant_seen = False
        self.reference_route_variant_kind = 'not_observed'
        self.list_snapshot = None
        self.list_owner = None
        self.preparation_deadline = None

    def __enter__(self):
        self.page.on('request', self._source_request)
        self.page.on('requestfailed', self._source_request_failed)
        self.page.on('requestfinished', self._source_finished)
        return self

    def __exit__(self, *args):
        self.closed = True
        self.page.remove_listener('request', self._source_request)
        self.page.remove_listener('requestfailed', self._source_request_failed)
        self.page.remove_listener('requestfinished', self._source_finished)
        self.source_pending.clear()
        self.source_ready.clear()
        self.observer.close()

    def _stop(self):
        if self.check_cancel:
            self.check_cancel()
        self._failures()
        if getattr(self, 'preparation_deadline', None) is not None and time.monotonic() >= self.preparation_deadline:
            raise MpnUnsupported('MPN UI preparation deadline exceeded')
        if not getattr(self.observer, '_binding_document', False):
            for request in list(getattr(self, 'source_ready', {}).values()):
                self._source_finished(request)
        if self.check_cancel:
            self.check_cancel()
        self._failures()
        if getattr(self, 'preparation_deadline', None) is not None and time.monotonic() >= self.preparation_deadline:
            raise MpnUnsupported('MPN UI preparation deadline exceeded')

    def _failures(self):
        if getattr(self.observer, 'safety_failed', False):
            raise MpnSafetyError('MPN owned document/request identity changed')
        if self.source_safety:
            raise MpnSafetyError('MPN loaded source/catalog identity changed')
        if getattr(self.observer, 'failed', False):
            raise MpnUnsupported('MPN owned grid capture failed')
        if self.source_failed:
            raise MpnUnsupported('MPN loaded source is unsupported')

    def _owned(self):
        self._stop()
        self._state()
        # The Document RPC can dispatch source refusals. No unchecked RPC follows.
        self._stop()

    def _observer_call(self, method, *args, **kwargs):
        try:
            result = method(*args, **kwargs)
        except (MpnUnsupported, PlaywrightError):
            # Reconcile fatal source/Stop state on exceptional RPC exits too.
            self._stop()
            raise
        self._stop()
        return result

    def _state(self, **kwargs):
        return self._observer_call(self.observer._check_state, **kwargs)

    def _wait(self, *args, **kwargs):
        return self._observer_call(self.observer.wait, *args, **kwargs)

    def _reject_source(self, stage, error=None, *, safety=False, ownership_reason=None):
        # Keep fatal refusals sticky and summarize the originating callback now.
        # Retain neither exceptions/tracebacks nor request/response material.
        if safety:
            self.source_safety = True
        else:
            self.source_failed = True
        if not self.source_rejection_recorded:
            self.source_rejection_recorded = True
            diagnostics.record('mpn.source_rejected', level='WARNING', phase='mpn',
                               mpn_source_stage=stage, error=error, status='PARTIAL',
                               mpn_ownership_reason=ownership_reason if stage == 'ownership' else None)

    def _source_request(self, request):
        if (self.closed or not self.observer.committed
                or self.observer.safety_failed or self.observer.failed
                or request.frame is not self.page.main_frame or request.method != 'GET'):
            return
        url = request.url
        pin = SOURCE_PINS.get(url.removeprefix(ORIGIN)) if url.startswith(ORIGIN + '/') else None
        kind = request.resource_type
        catalog = url == ORIGIN + REFERENCE_PATH and kind in ('xhr', 'fetch')
        if kind in ('xhr', 'fetch'):
            variant_kind = _reference_route_kind(url)
            if variant_kind != 'not_observed':
                # Fixed category only; NEVER enter source_pending.
                self.reference_route_variant_seen = True
                if variant_kind == 'path_variant' or self.reference_route_variant_kind == 'not_observed':
                    self.reference_route_variant_kind = variant_kind
        # A fetch/preload of script bytes does not prove an executable provider.
        # Nonqualifying traffic must not enter the later ownership checks.
        if pin is not None and kind != 'script':
            return
        if pin is None and request.resource_type == 'script' and re.match(
                re.escape(ORIGIN) + r'/accounting/id-ID/(?:main|vendor)\.', url):
            self._reject_source('provider', safety=bool(self.pins))
            return
        if pin is None and not catalog:
            return
        if len(self.source_pending) >= 16:
            self._reject_source('pending_budget')
            return
        self.source_sequence += 1
        if catalog:
            self.reference_request_seen = True
        self.source_pending[id(request)] = (request, pin, catalog, url, kind, self.observer._navigation_attempt)

    def _source_request_failed(self, request):
        entry = self.source_pending.pop(id(request), None)
        self.source_ready.pop(id(request), None)
        if entry is not None and entry[0] is request:
            self.source_sequence += 1
            self._reject_source('request_failed')

    def _source_finished(self, request):
        if (not self.closed and self.observer._binding_document
                and not self.observer.safety_failed and not self.observer.failed
                and id(request) in self.source_pending):
            self.source_ready[id(request)] = request
            return
        entry = self.source_pending.pop(id(request), None)
        self.source_ready.pop(id(request), None)
        if entry is None or entry[0] is not request or self.closed:
            return
        self.source_sequence += 1
        _, pin, catalog, expected_url, expected_kind, attempt = entry
        url = request.url
        stage = 'ownership'
        ownership_reason = None
        try:
            if (not self.observer.committed or self.observer.safety_failed
                    or attempt is not self.observer._navigation_attempt):
                ownership_reason = 'navigation'
            elif request.frame is not self.page.main_frame:
                ownership_reason = 'frame'
            elif request.method != 'GET':
                ownership_reason = 'method'
            elif self.page.url != self.url:
                ownership_reason = 'page_route'
            elif url != expected_url:
                ownership_reason = 'request_url'
            elif request.resource_type != expected_kind:
                ownership_reason = 'resource_kind'
            if ownership_reason is not None:
                raise MpnSafetyError('MPN source request ownership changed')

            def current():
                nonlocal stage, ownership_reason
                if (attempt is not self.observer._navigation_attempt or self.observer.safety_failed
                        or self.page.url != self.url):
                    stage, ownership_reason = 'ownership', 'navigation'
                    raise MpnSafetyError('MPN source document ownership changed')
                # A failed grid is terminal, but does not manufacture an identity contradiction.
                return not self.observer.failed

            if not current():
                return
            same = self.observer._same_document()
            if not current():
                return
            if not same:
                ownership_reason = 'navigation'
                raise MpnSafetyError('MPN source document ownership is unproved')
            stage = 'response'
            response = request.response()
            if not current():
                return
            if response is None or response.url != url or response.status != 200 or response.from_service_worker:
                raise MpnUnsupported('MPN original loaded source response unavailable')
            stage = 'body'
            raw = response.body()
            if not current():
                return
            stage = 'body_budget'
            if len(raw) > 8 * 1024 * 1024:
                raise MpnUnsupported('MPN loaded source byte budget exceeded')
            digest = hashlib.sha256(raw).hexdigest()
            if pin is not None:
                stage = 'script_digest'
                if digest != pin:
                    raise MpnUnsupported('MPN loaded script differs from reviewed source')
                self.pins[url.removeprefix(ORIGIN)] = digest
            elif self.reference_raw is not None:
                stage = 'catalog_snapshot'
                if self.reference_raw != raw:
                    raise MpnSafetyError('MPN reference snapshot changed')
            else:
                stage = 'catalog_late'
                if self.catalog_frozen:
                    raise MpnUnsupported('MPN first reference reply arrived after catalog binding')
                self.reference_raw = raw
                stage = 'catalog_decode'
                self._catalog(raw)
        except MpnSafetyError as error:
            self._reject_source(stage, error, safety=True, ownership_reason=ownership_reason)
        except Exception as error:
            self._reject_source(stage, error, ownership_reason=ownership_reason)

    def _catalog(self, raw):
        self.catalogs, self.catalog_codes = captured_catalogs(decode_mpn(raw), include_codes=True)
        self.catalog = self.catalogs.get('PERIOD', {})

    def _one(self, selector):
        self._stop()
        self._state()
        locator = self.page.locator(selector)
        if locator.count() != 1:
            raise MpnUnsupported('MPN unique inspected UI owner/control is unavailable')
        return locator

    def _ready_one(self, selector, *, deadline=None):
        deadline = deadline if deadline is not None else self.preparation_deadline or time.monotonic() + 5
        while True:
            self._stop()
            self._state(allow_document_pending=True)
            if not self.observer._binding_document:
                locator = self.page.locator(selector) if isinstance(selector, str) else selector
                count = locator.count()
                self._stop()
                self._state()
                if count > 1:
                    raise MpnUnsupported('MPN inspected readiness owner is ambiguous')
                visible = count == 1 and locator.is_visible()
                self._stop()
                self._state()
                if time.monotonic() >= deadline:
                    raise MpnUnsupported('MPN inspected control readiness deadline exceeded')
                if visible:
                    return locator
            if time.monotonic() >= deadline:
                raise MpnUnsupported('MPN inspected control readiness deadline exceeded')
            self.page.wait_for_timeout(min(100, max(1, int((deadline - time.monotonic()) * 1000))))

    def _click_ready(self, locator, *, actual_timeout_ms=1000):
        deadline = self.preparation_deadline or time.monotonic() + 5
        while True:
            self._owned()
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0:
                raise MpnUnsupported('MPN inspected action readiness deadline exceeded')
            try:
                locator.click(trial=True, timeout=min(1000, remaining))
            except PlaywrightTimeoutError:
                continue  # Only actionability is retried; the actual click occurs once.
            self._owned()
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0:
                raise MpnUnsupported('MPN inspected action readiness deadline exceeded')
            # One actual click only: never retry if the browser may have dispatched it.
            locator.click(timeout=min(actual_timeout_ms, remaining))
            self._owned()
            return

    def _dropdown(self, selector, caption):
        # Only the two reviewed fixed captions are used by this preparation path.
        if caption not in ('Yes', 'No'):
            raise MpnUnsupported('MPN inspected dropdown caption is unsupported')
        trigger = self._ready_one(selector + ' .p-dropdown-trigger')
        self._click_ready(trigger)
        option = self._ready_one(self.page.locator('.p-dropdown-panel:visible').get_by_role(
            'option', name=caption, exact=True))
        self._click_ready(option)
        # PrimeNG may keep the selected panel visible during its close animation.
        # Do not open the next inspected dropdown while its options still exist.
        deadline = self.preparation_deadline or time.monotonic() + 5
        while True:
            self._owned()
            count = self._observer_call(self.page.locator('.p-dropdown-panel:visible').count)
            if count > 1:
                raise MpnUnsupported('MPN inspected dropdown close owner is ambiguous')
            remaining = int((deadline - time.monotonic()) * 1000)
            if remaining <= 0:
                raise MpnUnsupported('MPN inspected dropdown close readiness deadline exceeded')
            if count == 0:
                return
            self._observer_call(self.page.wait_for_timeout, min(100, remaining))

    def open(self):
        self.diagnostic_stage = 'navigation'
        self._stop()
        if getattr(self.page.context, '_spt_financial_route_policy', None) != 'service_workers_blocked':
            raise MpnUnsupported('MPN requires the reviewed owned browser context')
        self.observer.begin_navigation(self.url)
        self.page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
        self.preparation_deadline = time.monotonic() + 45
        # Angular may mount its route owner after DOMContentLoaded. Short
        # value-free probes keep Stop and the original deadline authoritative.
        self.diagnostic_stage = 'owner'
        self._ready_one('acc-balance-sheet-light')
        self.diagnostic_stage = 'environment'
        environment = self.page.evaluate('''() => ({language:navigator.language,
            timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
            scripts:[...document.scripts].filter(e=>e.isConnected).map(e=>e.src)})''')
        self._stop()
        self._state()
        if environment.get('language') != 'id-ID' or environment.get('timezone') != 'Asia/Jakarta':
            raise MpnUnsupported('MPN display environment is unsupported')
        self.diagnostic_stage = 'source'
        if (set(self.pins) != set(SOURCE_PINS)
                or set(url for url in environment.get('scripts', []) if re.match(
                    re.escape(ORIGIN) + r'/accounting/id-ID/(?:main|vendor)\.', url))
                    != {ORIGIN + path for path in SOURCE_PINS}):
            raise MpnUnsupported('MPN reviewed loaded script providers are unavailable')
        self.diagnostic_stage = 'dropdowns'
        self._dropdown('acc-balance-sheet-light form ui-dropdown#ShowZeroValue', 'Yes')
        self._dropdown('acc-balance-sheet-light form ui-dropdown#ShowCancelledTransaction', 'No')
        self.diagnostic_stage = 'search'
        search = self._ready_one('acc-balance-sheet-light form button#submit')
        if search.inner_text(timeout=1000).strip() != 'Cari':
            raise MpnUnsupported('MPN inspected search control changed')
        # The first submit may still add its initial default date interval.
        for _ in range(2):
            self._stop()
            marker = self.observer.sequence
            # A successful actionability probe may precede >1s browser scheduling.
            # Bound the sole real Search click by the original 45s preparation deadline.
            self._click_ready(search, actual_timeout_ms=5000)
            snapshot = self._wait(marker, 'list', timeout=max(.001, self.preparation_deadline - time.monotonic()))
            self._stop()
            self.list_owner = self._ready_one('acc-balance-sheet-light-grid ui-grid p-table')
            if self._unfiltered(snapshot):
                self.list_snapshot = snapshot
                break
            self.diagnostic_stage = 'period_clear'
            refusal = self._unfiltered_reason(snapshot)
            # The reviewed list owner is p-table inside its single ui-grid.
            # A PrimeNG header filter can be a sibling of p-table; searching
            # only the table silently misses an eligible owned clear control.
            grid = self.list_owner.locator('xpath=ancestor::ui-grid[1]')
            if grid.count() != 1 or grid.locator('p-table').count() != 1:
                raise MpnUnsupported('MPN period clear grid owner is unproved')
            # A unique clear icon inside two identical widget IDs does not
            # prove which period filter owns that action. Do not click either.
            widget_count = grid.locator('#filterPeriodCode').count()
            widget_state = ('ambiguous' if widget_count > 1
                            else 'present' if widget_count == 1 else 'absent')
            clear = grid.locator('#filterPeriodCode .p-dropdown-clear-icon')
            count = clear.count()
            self._stop()
            # Never record filter values, names, dates or UI captions. These
            # fixed categories only identify why original source was refused.
            clear_state = ('ambiguous' if count > 1 else 'absent' if count == 0
                           else 'present' if clear.is_visible() else 'hidden')
            diagnostics.record('mpn.unfiltered_refused', level='WARNING',
                               mpn_filter_reason=refusal, mpn_clear_state=clear_state,
                               mpn_period_widget_state=widget_state)
            if widget_count > 1 or count > 1:
                raise MpnUnsupported('MPN period clear owner/control is ambiguous')
            if clear_state == 'present':
                self._click_ready(clear)
        if self.list_snapshot is None:
            raise MpnUnsupported('MPN unfiltered non-cancelled inventory is unproved')
        # Retain the already verified initial page size. Its optional picker is
        # unnecessary for complete owned pagination and can still be animating.
        self._stop()
        self.preparation_deadline = None
        self.diagnostic_stage = 'ready'

    def _freeze_catalog(self):
        if self.catalog_frozen:
            return
        deadline = time.monotonic() + 5
        while self.source_pending:
            self._owned()
            if time.monotonic() >= deadline:
                raise MpnUnsupported('MPN original reference readiness deadline exceeded')
            self.page.wait_for_timeout(min(100, max(1, int((deadline-time.monotonic())*1000))))
        self._owned()
        if time.monotonic() >= deadline:
            raise MpnUnsupported('MPN original reference readiness deadline exceeded')
        # Readiness is not an authorization to invent a reference fetch.
        # Differentiate observed-but-unbound from a missing original GET.
        status = ('accepted' if self.reference_raw is not None else
                  'observed_unbound' if getattr(self, 'reference_request_seen', False)
                  else 'not_observed')
        diagnostics.record('mpn.catalog_readiness', level='INFO',
                           mpn_catalog_state=status,
                           mpn_catalog_route_shape=('alternate_reference_get'
                                                    if getattr(self, 'reference_route_variant_seen', False)
                                                    else 'not_observed'),
                           mpn_catalog_variant_kind=getattr(self, 'reference_route_variant_kind', 'not_observed'))
        self.catalog_frozen = True

    @staticmethod
    def _unfiltered_reason(snapshot):
        # Categorize only the original owned request's structure, not its
        # contents. A diagnostic category must never authorize inventory.
        request = snapshot.get('request') if isinstance(snapshot, dict) else None
        filters = request.get('Filters') if isinstance(request, dict) else None
        if not isinstance(filters, list) or any(not isinstance(f, dict) for f in filters):
            return 'request_shape'
        if len(filters) != 1:
            if any(f.get('PropertyName') in ('TransactionDate', 'PeriodCode')
                   for f in filters):
                return 'date_filter_present'
            return 'additional_filter' if filters else 'cancelled_filter_missing'
        rule = filters[0]
        if rule.get('PropertyName') != 'IsCancelled':
            return 'cancelled_filter_missing'
        if (set(rule).issubset({'PropertyName', 'Value', 'MatchMode',
                                'CaseSensitive', 'AsString'})
                and rule.get('Value') == '0'
                and rule.get('MatchMode') == 'equals'
                and rule.get('CaseSensitive', True) is True
                and rule.get('AsString', False) is False):
            return None
        return 'cancelled_filter_modified'

    @staticmethod
    def _unfiltered(snapshot):
        return AccountingUI._unfiltered_reason(snapshot) is None

    def _table(self, owner, headers, count):
        deadline = time.monotonic() + 5
        while True:
            self._stop()
            tables = owner.locator('table')
            if tables.count() != 1 or not tables.is_visible():
                raise MpnUnsupported('MPN visible table ownership is unsupported')
            result = tables.evaluate(TABLE_JS, timeout=1000)
            if (not isinstance(result, dict) or result.get('headers') != [list(headers)]
                    or any(len(row) != len(headers) for row in result.get('rows', []))):
                raise MpnUnsupported('MPN observed table columns changed')
            if len(result.get('rows', [])) == count:
                return tables, result['rows']
            if time.monotonic() >= deadline:
                raise MpnUnsupported('MPN rendered row count did not reconcile')
            self.page.wait_for_timeout(100)

    def _pages(self, kind, owner, initial, max_pages):
        snapshot = initial
        binding = {key: value for key, value in snapshot['request'].items() if key != 'First'}
        payload = decode_mpn(initial['raw'])['Payload']
        mode = ('frontier-v1' if payload.get('Index', False) is None
                and initial['total'] == initial['page_size'] + 1
                and len(initial['rows']) == initial['page_size'] else 'fixed-v1')
        expected_first, total = 0, None
        for page_index in range(max_pages):
            self._stop()
            self._state()
            if (snapshot['first'] != expected_first
                    or {key: value for key, value in snapshot['request'].items() if key != 'First'} != binding
                    or kind == 'list' and not self._unfiltered(snapshot)):
                raise MpnSafetyError('MPN paginator query/total/offset changed')
            total = validate_page_total(decode_mpn(snapshot['raw'])['Payload'], expected_first,
                                        snapshot['page_size'], total, mode=mode)
            if snapshot['total'] != total:
                raise MpnSafetyError('MPN paginator total differs from its original response')
            snapshot['total_mode'] = mode
            if kind == 'list':
                self.list_snapshot = snapshot
            yield snapshot
            self._stop()
            if self.observer.latest.get(kind, {}).get('sequence') != snapshot['sequence']:
                raise MpnSafetyError('MPN grid refreshed outside its owned paginator action')
            expected_first += len(snapshot['rows'])
            next_button = owner.locator('.p-paginator-next:not([disabled]):not(.p-disabled)')
            if expected_first == total:
                if next_button.count():
                    raise MpnSafetyError('MPN paginator exceeds its captured total')
                return
            if next_button.count() != 1 or not next_button.is_visible():
                raise MpnUnsupported('MPN next page control is unavailable')
            if page_index + 1 == max_pages:
                raise MpnUnsupported('MPN owned paginator page cap reached')
            marker = self.observer.sequence
            self._owned()
            next_button.click(timeout=1000)
            snapshot = self._wait(marker, kind)
        raise MpnUnsupported('MPN owned paginator page cap reached')

    def list_pages(self, max_pages):
        for snapshot in self._pages('list', self.list_owner, self.list_snapshot, max_pages):
            self._table(self.list_owner, LIST_HEADERS, len(snapshot['rows']))
            yield snapshot

    @staticmethod
    def _literal(value):
        return '' if value is None else value if type(value) is str else None

    def _header_projection(self, header):
        code = header.get('PeriodCode')
        classifications = []
        for catalog, field in (('ACCOUNTING_TYPE', 'AccountingTypeCode'),
                               ('ACCOUNTING_TYPE_DETAIL', 'AccountingTypeDetailCode')):
            literal = header.get(field)
            label = self.catalogs.get(catalog, {}).get(literal, literal)
            inventory = getattr(self, 'catalog_codes', {}).get(catalog)
            # The ordinary pinned reference template leaves an absent detail
            # description blank; ineligible present rows prove no such absence.
            if (catalog == 'ACCOUNTING_TYPE_DETAIL' and type(literal) is str and literal
                    and inventory is not None and literal not in inventory):
                label = ''
            classifications.append(self._literal(label))
        return tuple(classifications) + (self._literal(header.get('CurrencyCode')), self._literal(header.get('RevenueCode')),
                self._literal(header.get('PaymentCode')), self.catalog.get(code, code),
                self._literal(header.get('TransactionNumber')))

    def _reference_caption(self, header):
        # Bounded defined-string branch of the loaded helper's dataColumnRender.
        # Reference is a link input, not the displayed ReferenceNumber caption.
        reference_type = header.get('ReferenceType')
        if (type(reference_type) is not str
                or not header.get('AccountingTypeCode') or not header.get('AccountingTypeDetailCode')):
            return None
        number = self._literal(header.get('ReferenceNumber'))
        caption = ('Tax Return Reference' if reference_type.replace(' Replacement', '', 1)
                   in REFERENCE_TAX_TYPES else number)
        if (header.get('AccountingTypeCode') == 'TaxNotice' and reference_type not in REFERENCE_TAX_TYPES
                or header.get('AccountingTypeCode') == 'Adjustment' and header.get('AccountingTypeDetailCode') == 'AIP'):
            caption = number
        return caption if caption else None

    def _bind_header(self, header):
        self._stop()
        self._freeze_catalog()
        snapshot = self.list_snapshot
        if self.observer.latest.get('list', {}).get('sequence') != snapshot['sequence']:
            raise MpnSafetyError('MPN parent list changed before the detail action')
        candidates = [index for index, row in enumerate(snapshot['rows']) if row.get('RecordId') == header['RecordId']]
        if not candidates or any(_digest(snapshot['rows'][index]) != _digest(header) for index in candidates):
            raise MpnUnsupported('MPN selected parent position is ambiguous')
        index = candidates[0]
        _, rendered = self._table(self.list_owner, LIST_HEADERS, len(snapshot['rows']))
        self._owned()
        if self.observer.latest.get('list', {}).get('sequence') != snapshot['sequence']:
            raise MpnSafetyError('MPN parent list changed while binding the rendered row')
        expected = self._header_projection(header)
        if any(value is None for value in expected) or not expected[-1]:
            raise MpnUnsupported('MPN parent visible identity is not independently unique')
        matching = [row for row in snapshot['rows'] if self._header_projection(row) == expected]
        if {row['RecordId'] for row in matching} != {header['RecordId']}:
            for peer in matching:
                if (any(peer.get(field) != header.get(field)
                        for field in ('TaxpayerAggregateIdentifier', 'TaxpayerTIN'))
                        or peer.get('IsCancelled') is not False):
                    raise MpnSafetyError('MPN participating parent source identity contradicts its owner')
            captions = [(row['RecordId'], self._reference_caption(row)) for row in matching]
            caption = self._reference_caption(header)
            if any(value is None for _, value in captions) or caption is None:
                raise MpnUnsupported('MPN repeated parent captions lack a unique original reference binding')
            if rendered[index][12] != caption:
                raise MpnSafetyError('MPN selected parent reference caption differs from its original source')
            if {identifier for identifier, value in captions if value == caption} != {header['RecordId']}:
                numeric, unsupported = [], False
                for position, peer in enumerate(snapshot['rows']):
                    if self._header_projection(peer) != expected or self._reference_caption(peer) != caption:
                        continue
                    observed = rendered[position]
                    if (tuple(observed[column] for column in (3, 4, 5, 13, 15, 16, 17)) != expected
                            or observed[12] != caption):
                        raise MpnSafetyError('MPN repeated parent visible identity differs from its source')
                    values = parent_numeric_binding(observed, peer)
                    if values is None:
                        unsupported = True
                    else:
                        numeric.append((peer['RecordId'], values))
                if unsupported:
                    raise MpnUnsupported('MPN repeated parent numeric identity is unproved')
                selected = next(values for identifier, values in numeric if identifier == header['RecordId'])
                if {identifier for identifier, values in numeric if values == selected} != {header['RecordId']}:
                    raise MpnUnsupported('MPN repeated parent numeric identity is not independently unique')
        actual = tuple(rendered[index][column] for column in (3, 4, 5, 13, 15, 16, 17))
        if actual != expected:
            # Only fixed column categories and a bounded mismatch count; no
            # actual/expected values or new authorization to click detail.
            fields = ('accounting_type', 'accounting_detail', 'currency',
                      'revenue_code', 'payment_code', 'tax_period', 'transaction_number')
            differing = [position for position in range(len(fields))
                         if actual[position] != expected[position]]
            field = fields[differing[0]]
            provenance = None
            if field == 'accounting_type':
                code = header.get('AccountingTypeCode')
                labels = getattr(self, 'catalogs', {}).get('ACCOUNTING_TYPE', {})
                inventory = getattr(self, 'catalog_codes', {}).get('ACCOUNTING_TYPE')
                provenance = ('source_code_missing' if type(code) is not str or not code
                              else 'catalog_missing' if inventory is None
                              else 'code_not_in_catalog' if code not in inventory
                              else 'catalog_label' if code in labels
                              else 'raw_code_fallback')
            diagnostics.record('mpn.parent_binding_mismatch', level='WARNING',
                               mpn_parent_field=field,
                               mpn_parent_secondary_field=(fields[differing[1]]
                                                           if len(differing) > 1 else 'none'),
                               mpn_parent_tertiary_field=(fields[differing[2]]
                                                          if len(differing) > 2 else 'none'),
                               mpn_parent_mismatch_count=len(differing),
                               mpn_accounting_type_projection=provenance)
            if (actual[0] != expected[0] and actual[1:] == expected[1:]
                    and getattr(self, 'catalog_codes', {}).get('ACCOUNTING_TYPE') is None):
                # Without an accepted original code inventory, a displayed
                # localized label cannot prove a source contradiction. Refuse
                # the action as unsupported; never guess a mapping or click.
                raise MpnUnsupported('MPN accounting type original reference is unproved')
            raise MpnSafetyError('MPN selected parent rendered/source identity differs')
        row = self.list_owner.locator('tbody tr').nth(index)
        button = row.locator('td').nth(0).locator(
            'button[title="Detail Transaksi"]:has(.pi-list), '
            'button#ViewButton[type="button"]:has(.pi-list)')
        if button.count() != 1 or not button.is_visible() or not button.is_enabled():
            raise MpnUnsupported('MPN inspected read-only Detail Transaksi action is unavailable')
        if (button.get_attribute('id') not in (None, '', 'ViewButton')
                or button.get_attribute('title') not in (None, '', 'Detail Transaksi')
                or button.get_attribute('aria-label') not in (None, '', 'Detail Transaksi')):
            raise MpnUnsupported('MPN inspected detail action captions contradict its source name')
        return button

    def _detail_dom(self, owner, snapshot):
        try:
            _, rows = self._table(owner, DETAIL_HEADERS, len(snapshot['rows']))
        except MpnUnsupported:
            return None
        if not dom_numbers_match(rows, snapshot['rows']):
            return None
        for row, detail in zip(rows, snapshot['rows']):
            expected = (_date(detail.get('TransactionDate')), _date(detail.get('PostingDate')),
                        detail.get('TransactionNumber'),
                        self.catalogs.get('ACCOUNTING_TYPE', {}).get(detail.get('AccountingTypeCode'), detail.get('AccountingTypeCode')),
                        self.catalogs.get('ACCOUNTING_TYPE_DETAIL', {}).get(detail.get('AccountingTypeDetailCode'), detail.get('AccountingTypeDetailCode')),
                        self._literal(detail.get('ReferenceNumber')))
            if any(value is None for value in expected) or tuple(row[i] for i in (0, 1, 2, 3, 4, 8)) != expected:
                return None
        return rows

    def detail_pages(self, header, max_pages):
        button = self._bind_header(header)
        host = self._one('p-dialog#isShowDetail')
        if self.page.locator('[role="dialog"]:visible').count():
            raise MpnUnsupported('MPN detail action has a pre-existing visible dialog')
        self._observer_call(self.observer.begin_detail, header['RecordId'])
        marker = self.observer.sequence
        self._owned()
        self._observer_call(button.click, timeout=5000, no_wait_after=True)
        initial = self._wait(marker, 'detail')
        deadline = time.monotonic() + 5
        dialog = self._ready_one('p-dialog#isShowDetail [role="dialog"]:visible, '
            'body > .p-dialog-mask.p-component-overlay > .p-dialog.p-component[role="dialog"]:visible', deadline=deadline)
        title = self._ready_one(dialog.locator('.p-dialog-title'), deadline=deadline)
        if title.count() != 1 or title.inner_text(timeout=1000).strip() != 'Detail Transaksi':
            raise MpnUnsupported('MPN inspected detail dialog changed')
        if self.page.locator('[role="dialog"]:visible').count() != 1:
            raise MpnUnsupported('MPN detail dialog ownership is ambiguous')
        if dialog.locator('xpath=ancestor::p-dialog[@id="isShowDetail"]').count() == 0:
            title_id = title.get_attribute('id')
            if (host.get_attribute('header') != 'Detail Transaksi' or not title_id
                    or dialog.get_attribute('aria-labelledby') != title_id):
                raise MpnUnsupported('MPN body-mounted detail dialog lacks its inspected title binding')
        owners = self._ready_one(dialog.locator('ui-grid p-table'), deadline=deadline)
        try:
            for snapshot in self._pages('detail', owners, initial, max_pages):
                self._stop()
                dom = self._detail_dom(owners, snapshot) if self.run['mpn']['detail_source'] == 'dom' else None
                yield snapshot, dom
        finally:
            self._stop()
            close = dialog.locator('button.p-dialog-header-close')
            if close.count() != 1 or not close.is_visible():
                raise MpnUnsupported('MPN inspected dialog close control is unavailable')
            self._owned()
            self._observer_call(close.click, timeout=5000, no_wait_after=True)
            self._observer_call(dialog.wait_for, state='hidden', timeout=5000)

    def finish(self):
        pending = bool(self.observer.pending or self.source_pending)
        self.catalog_frozen = True
        self._stop()
        self._state()
        sequence = self.observer.sequence
        source_sequence = self.source_sequence
        # An already pending reply cannot become COMPLETE by arriving in drain.
        if pending or self.observer.pending or self.source_pending:
            raise MpnUnsupported('MPN has pending owned replies at final sampling')
        deadline = time.monotonic() + .5
        while time.monotonic() < deadline:
            self._stop()
            self.page.wait_for_timeout(100)
            self._state()
            if (self.observer.pending or self.observer.sequence != sequence
                    or self.source_pending or self.source_sequence != source_sequence):
                raise MpnUnsupported('MPN received a late owned reply during final drain')
        providers = self.page.evaluate('''() => [...document.scripts].filter(e=>e.isConnected).map(e=>e.src)''')
        self._owned()
        if (pending or self.observer.pending or self.source_pending
                or self.observer.sequence != sequence or self.source_sequence != source_sequence):
            raise MpnUnsupported('MPN received late owned traffic during final provider validation')
        actual = {url for url in providers if re.match(
            re.escape(ORIGIN) + r'/accounting/id-ID/(?:main|vendor)\.', url)}
        if actual != {ORIGIN + path for path in SOURCE_PINS}:
            raise MpnSafetyError('MPN script providers changed during capture')
