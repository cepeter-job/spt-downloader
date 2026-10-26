"""Inspected Accounting UI navigation only; never manufacture/replay a POST."""
import hashlib
import re
import time

from coretax_mpn import (ORIGIN, MpnUnsupported, MpnSafetyError, decode_mpn,
                         dom_numbers_match, taxpayer_id, captured_catalogs,
                         source_display_date as _date)
from coretax_mpn_browser import AccountingObserver, _digest

SOURCE_PINS = {
    '/accounting/id-ID/main.fedea3c4d025195e.js': '7a76f131ac13b124087c4c968154d0f73c26a92069dc8d6dd59791f908d4bdf1',
    '/accounting/id-ID/vendor.5900c4ddec796b87.js': 'b876e4421e8d8caa81b98928f23e672e5da7069fa7ab30ab14318b5f3726af5c',
}
REFERENCE_PATH = ('/referencedata/api/currentreferencedata/id-ID/'
                  'ACCOUNTING_TYPE,ACCOUNTING_TYPE_DETAIL,REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT,PERIOD')
LIST_HEADERS = ('Aksi', 'Tanggal Transaksi', 'Tanggal Posting', 'Jenis Pencatatan',
                'Detail Jenis Pencatatan', 'Mata Uang', 'Jenis Transaksi', 'Nilai Mata Uang',
                'Nilai Sisa dalam Mata Uang', 'Nilai Tukar', 'Jumlah', 'Nilai Sisa',
                'Referensi', 'KAP', 'Deskripsi KAP', 'KJS', 'Masa Pajak', 'Nomor Transaksi',
                'Tanggal Jatuh Tempo Pembayaran', 'Tanggal Utang Pajak Dapat Ditagih',
                'Tanggal Daluwarsa', 'Dibatalkan', 'NOP', 'Dapat Digunakan')
DETAIL_HEADERS = ('Tanggal Transaksi', 'Tanggal Posting', 'Nomor Transaksi',
                  'Jenis Pencatatan', 'Detail Jenis Pencatatan', 'Nilai Mata Uang',
                  'Nilai Tukar Transaksi Induk', 'Jumlah', 'Referensi')
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


class AccountingUI:
    def __init__(self, page, run, folder, *, check_cancel=None):
        self.page, self.run, self.folder = page, run, folder
        self.check_cancel = check_cancel
        self.taxpayer = taxpayer_id(run)
        self.url = ORIGIN + '/accounting/id-ID/balancesheet/' + self.taxpayer
        self.observer = AccountingObserver(page, self.taxpayer, folder, check_cancel)
        self.pins, self.catalogs, self.catalog = {}, {}, {}
        self.source_failed = False
        self.source_safety = False
        self.source_pending = {}
        self.source_sequence = 0
        self.catalog_frozen = False
        self.closed = False
        self.reference_raw = None
        self.list_snapshot = None
        self.list_owner = None

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
        self.observer.close()

    def _stop(self):
        if self.check_cancel:
            self.check_cancel()
        if self.source_safety:
            raise MpnSafetyError('MPN loaded source/catalog identity changed')
        if self.source_failed:
            raise MpnUnsupported('MPN loaded source is unsupported')

    def _source_request(self, request):
        if (self.closed or not self.observer.committed
                or request.frame is not self.page.main_frame):
            return
        url = request.url
        pin = SOURCE_PINS.get(url.removeprefix(ORIGIN)) if url.startswith(ORIGIN + '/') else None
        catalog = url == ORIGIN + REFERENCE_PATH
        if pin is None and request.resource_type == 'script' and re.match(
                re.escape(ORIGIN) + r'/accounting/id-ID/(?:main|vendor)\.', url):
            self.source_safety = bool(self.pins)
            self.source_failed = True
            return
        if pin is None and not catalog:
            return
        if len(self.source_pending) >= 16:
            self.source_failed = True
            return
        self.source_sequence += 1
        self.source_pending[id(request)] = (request, pin, catalog)

    def _source_request_failed(self, request):
        entry = self.source_pending.pop(id(request), None)
        if entry is not None and entry[0] is request:
            self.source_sequence += 1
            self.source_failed = True

    def _source_finished(self, request):
        entry = self.source_pending.pop(id(request), None)
        if entry is None or entry[0] is not request or self.closed:
            return
        self.source_sequence += 1
        _, pin, catalog = entry
        url = request.url
        try:
            if (not self.observer.committed or request.frame is not self.page.main_frame
                    or request.method != 'GET' or self.page.url != self.url
                    or pin is not None and request.resource_type != 'script'):
                raise MpnSafetyError('MPN source request ownership changed')
            response = request.response()
            if response is None or response.url != url or response.status != 200 or response.from_service_worker:
                raise MpnUnsupported('MPN original loaded source response unavailable')
            raw = response.body()
            if len(raw) > 8 * 1024 * 1024:
                raise MpnUnsupported('MPN loaded source byte budget exceeded')
            digest = hashlib.sha256(raw).hexdigest()
            if pin is not None:
                if digest != pin:
                    raise MpnUnsupported('MPN loaded script differs from reviewed source')
                self.pins[url.removeprefix(ORIGIN)] = digest
            elif self.reference_raw is not None:
                if self.reference_raw != raw:
                    raise MpnSafetyError('MPN reference snapshot changed')
            else:
                if self.catalog_frozen:
                    raise MpnUnsupported('MPN first reference reply arrived after catalog binding')
                self.reference_raw = raw
                self._catalog(raw)
        except MpnSafetyError:
            self.source_safety = True
        except Exception:
            self.source_failed = True

    def _catalog(self, raw):
        self.catalogs = captured_catalogs(decode_mpn(raw))
        self.catalog = self.catalogs.get('PERIOD', {})

    def _one(self, selector):
        self._stop()
        locator = self.page.locator(selector)
        if locator.count() != 1:
            raise MpnUnsupported('MPN unique inspected UI owner/control is unavailable')
        return locator

    def _dropdown(self, selector, caption):
        trigger = self._one(selector + ' .p-dropdown-trigger')
        trigger.click(timeout=1000)
        self._stop()
        option = self.page.locator('.p-dropdown-panel:visible').get_by_role('option', name=caption, exact=True)
        if option.count() != 1:
            raise MpnUnsupported('MPN inspected dropdown option is unavailable')
        option.click(timeout=1000)

    def open(self):
        self._stop()
        if getattr(self.page.context, '_spt_financial_route_policy', None) != 'service_workers_blocked':
            raise MpnUnsupported('MPN requires the reviewed owned browser context')
        self.observer.begin_navigation(self.url)
        self.page.goto(self.url, wait_until='domcontentloaded', timeout=60000)
        self._one('acc-balance-sheet-light').wait_for(state='visible', timeout=45000)
        environment = self.page.evaluate('''() => ({language:navigator.language,
            timezone:Intl.DateTimeFormat().resolvedOptions().timeZone,
            scripts:[...document.scripts].filter(e=>e.isConnected).map(e=>e.src)})''')
        if environment.get('language') != 'id-ID' or environment.get('timezone') != 'Asia/Jakarta':
            raise MpnUnsupported('MPN display environment is unsupported')
        if (set(self.pins) != set(SOURCE_PINS)
                or set(url for url in environment.get('scripts', []) if re.match(
                    re.escape(ORIGIN) + r'/accounting/id-ID/(?:main|vendor)\.', url))
                    != {ORIGIN + path for path in SOURCE_PINS}):
            raise MpnUnsupported('MPN reviewed loaded script providers are unavailable')
        self._dropdown('acc-balance-sheet-light form ui-dropdown#ShowZeroValue', 'Yes')
        self._dropdown('acc-balance-sheet-light form ui-dropdown#ShowCancelledTransaction', 'No')
        self.list_owner = self._one('acc-balance-sheet-light-grid ui-grid p-table')
        clear = self.list_owner.locator('#filterPeriodCode .p-dropdown-clear-icon')
        if clear.count() == 1 and clear.is_visible():
            clear.click(timeout=1000)
        search = self._one('acc-balance-sheet-light form button#submit')
        if search.inner_text(timeout=1000).strip() != 'Cari':
            raise MpnUnsupported('MPN inspected search control changed')
        # The first submit may still add its initial default date interval.
        for _ in range(2):
            self._stop()
            marker = self.observer.sequence
            search.click(timeout=1000)
            snapshot = self.observer.wait(marker, 'list')
            if self._unfiltered(snapshot):
                self.list_snapshot = snapshot
                break
        if self.list_snapshot is None:
            raise MpnUnsupported('MPN unfiltered non-cancelled inventory is unproved')
        self._page_size()
        self._stop()
        self.catalog_frozen = True

    @staticmethod
    def _unfiltered(snapshot):
        filters = snapshot['request']['Filters']
        return (len(filters) == 1 and isinstance(filters[0], dict)
                and set(filters[0]).issubset({'PropertyName', 'Value', 'MatchMode', 'CaseSensitive', 'AsString'})
                and filters[0].get('PropertyName') == 'IsCancelled' and filters[0].get('Value') == '0'
                and filters[0].get('MatchMode') == 'equals'
                and filters[0].get('CaseSensitive', True) is True
                and filters[0].get('AsString', False) is False)

    def _page_size(self):
        trigger = self.list_owner.locator('.p-paginator .p-dropdown-trigger')
        if trigger.count() == 0:
            return
        if trigger.count() != 1:
            raise MpnUnsupported('MPN paginator page-size ownership is ambiguous')
        self._stop()
        trigger.click(timeout=1000)
        options = self.page.locator('.p-dropdown-panel:visible [role="option"]')
        texts = options.all_text_contents()
        sizes = [(int(text.strip()), index) for index, text in enumerate(texts)
                 if re.fullmatch(r'[0-9]{1,3}', text.strip()) and int(text.strip()) in (10, 25, 50)]
        if not sizes:
            raise MpnUnsupported('MPN inspected page sizes are unavailable')
        maximum, index = max(sizes)
        current = self.list_owner.locator('.p-paginator .p-dropdown-label')
        if current.count() == 1 and current.inner_text(timeout=1000).strip() == str(maximum):
            self.page.keyboard.press('Escape')
            return
        marker = self.observer.sequence
        self._stop()
        options.nth(index).click(timeout=1000)
        snapshot = self.observer.wait(marker, 'list')
        if not self._unfiltered(snapshot) or snapshot['first'] != 0 or snapshot['page_size'] != maximum:
            raise MpnSafetyError('MPN page-size action changed the inventory scope')
        self.list_snapshot = snapshot

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
        expected_first, total = 0, snapshot['total']
        for page_index in range(max_pages):
            self._stop()
            self.observer._check_state()
            if (snapshot['first'] != expected_first or snapshot['total'] != total
                    or {key: value for key, value in snapshot['request'].items() if key != 'First'} != binding
                    or kind == 'list' and not self._unfiltered(snapshot)):
                raise MpnSafetyError('MPN paginator query/total/offset changed')
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
            self._stop()
            next_button.click(timeout=1000)
            snapshot = self.observer.wait(marker, kind)
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
        return (self._literal(header.get('CurrencyCode')), self._literal(header.get('RevenueCode')),
                self._literal(header.get('PaymentCode')), self.catalog.get(code, code),
                self._literal(header.get('TransactionNumber')))

    def _bind_header(self, header):
        self._stop()
        snapshot = self.list_snapshot
        if self.observer.latest.get('list', {}).get('sequence') != snapshot['sequence']:
            raise MpnSafetyError('MPN parent list changed before the detail action')
        candidates = [index for index, row in enumerate(snapshot['rows']) if row.get('RecordId') == header['RecordId']]
        if not candidates or any(_digest(snapshot['rows'][index]) != _digest(header) for index in candidates):
            raise MpnUnsupported('MPN selected parent position is ambiguous')
        index = candidates[0]
        _, rendered = self._table(self.list_owner, LIST_HEADERS, len(snapshot['rows']))
        expected = self._header_projection(header)
        if (any(value is None for value in expected) or not expected[-1]
                or {row['RecordId'] for row in snapshot['rows'] if self._header_projection(row) == expected}
                    != {header['RecordId']}):
            raise MpnUnsupported('MPN parent visible identity is not independently unique')
        actual = tuple(rendered[index][column] for column in (5, 13, 15, 16, 17))
        if actual != expected:
            raise MpnSafetyError('MPN selected parent rendered/source identity differs')
        row = self.list_owner.locator('tbody tr').nth(index)
        button = row.locator('td').nth(0).locator('button[title="Detail Transaksi"]:has(.pi-list)')
        if button.count() != 1 or not button.is_visible() or not button.is_enabled():
            raise MpnUnsupported('MPN inspected read-only Detail Transaksi action is unavailable')
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
        self.observer.begin_detail(header['RecordId'])
        marker = self.observer.sequence
        self._stop()
        button.click(timeout=1000)
        initial = self.observer.wait(marker, 'detail')
        dialog = self._one('p-dialog#isShowDetail [role="dialog"]:visible')
        title = dialog.locator('.p-dialog-title')
        if title.count() != 1 or title.inner_text(timeout=1000).strip() != 'Detail Transaksi':
            raise MpnUnsupported('MPN inspected detail dialog changed')
        owners = dialog.locator('ui-grid p-table')
        if owners.count() != 1:
            raise MpnUnsupported('MPN unique detail paginator owner is unavailable')
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
            close.click(timeout=1000)
            dialog.wait_for(state='hidden', timeout=1000)

    def finish(self):
        self._stop()
        self.observer._check_state()
        sequence = self.observer.sequence
        source_sequence = self.source_sequence
        # An already pending reply cannot become COMPLETE by arriving in drain.
        if self.observer.pending or self.source_pending:
            raise MpnUnsupported('MPN has pending owned replies at final sampling')
        deadline = time.monotonic() + .5
        while time.monotonic() < deadline:
            self._stop()
            self.page.wait_for_timeout(100)
            self.observer._check_state()
            if (self.observer.pending or self.observer.sequence != sequence
                    or self.source_pending or self.source_sequence != source_sequence):
                raise MpnUnsupported('MPN received a late owned reply during final drain')
        providers = self.page.evaluate('''() => [...document.scripts].filter(e=>e.isConnected).map(e=>e.src)''')
        actual = {url for url in providers if re.match(
            re.escape(ORIGIN) + r'/accounting/id-ID/(?:main|vendor)\.', url)}
        if actual != {ORIGIN + path for path in SOURCE_PINS}:
            raise MpnSafetyError('MPN script providers changed during capture')
