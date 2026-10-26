"""Owned Accounting observers, separate from all native SPT admission rules."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from urllib.parse import urlsplit
from playwright.sync_api import Error as PlaywrightError

from coretax_mpn import (ORIGIN, MpnSafetyError, MpnUnsupported, decode_mpn,
                         source_integer, _identity, MpnNumber, require_mpn,
                         project_payment, validate_mpn, MAX_BODY, MAX_EVIDENCE, MAX_RESPONSES,
                         _mpn_directories, _source_digest)

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
                or type(data['SortOrder']) is not MpnNumber or str(data['SortOrder']) != '-1'
                or not isinstance(data['Filters'], list)
                or (kind == 'detail' and data['Filters'] != [])):
            raise MpnUnsupported('MPN grid pagination/language/filter shape is unsupported')
        data['First'], data['Rows'] = first, size
        data['SortOrder'] = -1
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


def AccountingUI(*args, **kwargs):
    # Lazy to keep source qualification/observer imports independent of UI code.
    from coretax_mpn_ui import AccountingUI as owned_ui
    return owned_ui(*args, **kwargs)


def _digest(value):
    return _source_digest(value)


def _accept_snapshot(snapshot, kind, first, total=None):
    if not isinstance(snapshot, dict) or snapshot.get('kind') != kind:
        raise MpnUnsupported('MPN owned page snapshot is unavailable')
    decoded = decode_mpn(snapshot.get('raw'))
    payload = decoded.get('Payload')
    if decoded.get('IsSuccessful') is not True or not isinstance(payload, dict):
        raise MpnUnsupported('MPN original page envelope is unsuccessful')
    actual_total = source_integer(payload.get('TotalRecords'))
    size = snapshot.get('page_size')
    rows = payload.get('Data')
    if (type(size) is not int or size not in (10, 25, 50) or snapshot.get('first') != first
            or actual_total != snapshot.get('total') or total is not None and total != actual_total
            or not isinstance(rows, list) or len(rows) != min(size, max(0, actual_total - first))
            or not all(isinstance(row, dict) for row in rows)
            or _digest(rows) != _digest(snapshot.get('rows'))):
        raise MpnSafetyError('MPN page snapshot/count changed during capture')
    return rows, actual_total


def collect_mpn(page, run, folder, *, detail_source='dom', max_pages=1000,
                on_progress=None, check_cancel=None):
    if check_cancel:
        check_cancel()
    from spt_desktop.output_windows import DirectoryGuard
    root = Path(folder).absolute()
    with DirectoryGuard() as guard:
        guard.include(_mpn_directories(root))
        return _collect_mpn_owned(page, run, root, detail_source=detail_source,
            max_pages=max_pages, on_progress=on_progress, check_cancel=check_cancel, guard=guard)


def _collect_mpn_owned(page, run, folder, *, detail_source, max_pages,
                       on_progress, check_cancel, guard):
    """Capture all owned non-cancelled parents, then qualify complete details.

The preceding SPT component's completion is separate from the required MPN gate.
No partial DOM page is combined with another source. Raw pages stay private.
"""
    def stop():
        if check_cancel:
            check_cancel()
    stop()
    if type(max_pages) is not int or not 1 <= max_pages <= 100000:
        raise ValueError('MPN page cap must be a positive bounded integer')
    spt_complete = run.get('complete') is True
    run['complete'] = False
    value = require_mpn(run, detail_source)
    value.update(status='PENDING', inventory_complete=False, details_complete=False,
                 headers=0, details=0, rows=[], audit=[], evidence=[], provenance=[],
                 coverage={'excluded': 0, 'unresolved': 0, 'duplicates': 0},
                 attempt=uuid.uuid4().hex, source_pins={}, bindings=[])
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    private = folder / 'mpn' / value['attempt']
    # Exclusive attempt; never replace/delete a preceding private capture.
    if any(child.name.casefold() == 'mpn' and child.name != 'mpn' for child in folder.iterdir()):
        raise MpnSafetyError('MPN private capture root has a case alias')
    private.parent.mkdir(exist_ok=True)
    guard.include(_mpn_directories(private.parent))
    private.mkdir(exist_ok=False)
    guard.include(_mpn_directories(private))
    budget = 0
    canonical_bytes = 0
    last_checkpoint = time.monotonic()

    def checkpoint():
        from coretax_browser import _atomic_checkpoint
        stop()
        validate_mpn(run)
        _atomic_checkpoint(private / 'manifest.json', {
            'format': 'spt-downloader-mpn-private', 'version': 1, 'mpn': value})
        _atomic_checkpoint(folder / 'run.json', run)

    def evidence(snapshot, kind):
        nonlocal budget
        stop()
        raw = snapshot['raw']
        decode_mpn(raw)
        if len(value['evidence']) >= MAX_RESPONSES or budget + len(raw) > MAX_EVIDENCE:
            raise MpnUnsupported('MPN capture evidence budget reached')
        ordinal = len(value['evidence']) + 1
        name = f'{ordinal:06d}-{kind}.json'
        with (private / name).open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        item = {'path': f"mpn/{value['attempt']}/{name}", 'bytes': len(raw),
                'sha256': hashlib.sha256(raw).hexdigest()}
        value['evidence'].append(item)
        binding = {'path': item['path'], 'kind': kind}
        if kind != 'catalog':
            binding.update(request=deepcopy(snapshot['request']), parent_id=snapshot.get('parent_id'))
        value['bindings'].append(binding)
        budget += len(raw)
        return item

    seen_headers, seen_details, provenance = {}, {}, {}
    try:
        with AccountingUI(page, run, folder, check_cancel=check_cancel) as ui:
            ui.open()
            value['source_pins'] = deepcopy(ui.pins)
            if getattr(ui, 'reference_raw', None) is not None:
                evidence({'raw': ui.reference_raw}, 'catalog')
            first, total, pages = 0, None, 0
            for snapshot in ui.list_pages(max_pages):
                stop()
                pages += 1
                if pages > max_pages:
                    raise MpnUnsupported('MPN parent page cap reached')
                headers, total = _accept_snapshot(snapshot, 'list', first, total)
                list_item = evidence(snapshot, 'list')
                for header_index, header in enumerate(headers):
                    stop()
                    identifier = header.get('RecordId')
                    if (not _identity(identifier) or header.get('TaxpayerAggregateIdentifier') != value['taxpayer_id']
                            or header.get('TaxpayerTIN') != run['npwp']):
                        raise MpnSafetyError('MPN parent taxpayer/scope identity changed')
                    if header.get('IsCancelled') is not False:
                        raise MpnSafetyError('MPN parent violates the non-cancelled inventory')
                    digest = _digest(header)
                    if identifier in seen_headers:
                        if seen_headers[identifier] != digest:
                            raise MpnSafetyError('MPN repeated parent content changed')
                        continue
                    seen_headers[identifier] = digest
                    value['headers'] += 1
                    detail_rows, detail_events, dom_pages = [], [], []
                    detail_first, detail_total, detail_page_count = 0, None, 0
                    for detail_snapshot, dom in ui.detail_pages(header, max_pages):
                        stop()
                        detail_page_count += 1
                        if detail_page_count > max_pages:
                            raise MpnUnsupported('MPN detail page cap reached')
                        if detail_snapshot.get('parent_id') != identifier:
                            raise MpnSafetyError('MPN detail snapshot parent changed')
                        rows, detail_total = _accept_snapshot(detail_snapshot, 'detail', detail_first, detail_total)
                        item = evidence(detail_snapshot, 'detail')
                        detail_rows.extend(rows)
                        detail_events.extend((item, index) for index in range(len(rows)))
                        dom_pages.append(dom)
                        detail_first += len(rows)
                    if detail_total is None or detail_first != detail_total:
                        raise MpnUnsupported('MPN complete detail inventory is unavailable')
                    value['details'] += detail_first
                    # UI returns only a complete, fully source-bound DOM projection;
                    # any unqualified page replaces this entire parent's DOM attempt.
                    use_dom = detail_source == 'dom' and all(isinstance(rows, list) for rows in dom_pages)
                    flat_dom = [row for rows in dom_pages for row in rows] if use_dom else None
                    from coretax_mpn import dom_numbers_match
                    use_dom = bool(use_dom and dom_numbers_match(flat_dom, detail_rows))
                    if use_dom:
                        identities = {}
                        for rendered, detail in zip(flat_dom, detail_rows):
                            identities.setdefault(tuple(rendered), set()).add(detail.get('RecordId'))
                        use_dom = all(len(ids) == 1 for ids in identities.values())
                    for index, (detail, (item, source_index)) in enumerate(zip(detail_rows, detail_events)):
                        stop()
                        detail_id = detail.get('RecordId')
                        if not _identity(detail_id) or detail.get('HeaderRecordId') != identifier:
                            raise MpnSafetyError('MPN detail identity contradicts its inspected parent')
                        fingerprint = _digest(detail)
                        occurrence = {'header_sha256': list_item['sha256'], 'header_index': header_index,
                                      'detail_sha256': item['sha256'], 'detail_index': source_index}
                        if detail_id in seen_details:
                            if seen_details[detail_id] != (identifier, fingerprint):
                                raise MpnSafetyError('MPN repeated detail identity/content changed')
                            if detail_id in provenance:
                                provenance[detail_id]['occurrences'].append(occurrence)
                            value['coverage']['duplicates'] += 1
                            continue
                        seen_details[detail_id] = (identifier, fingerprint)
                        try:
                            row = project_payment(header, detail, year=run['year'], catalog=ui.catalog)
                        except MpnUnsupported:
                            value['coverage']['unresolved'] += 1
                            value['audit'].append({'message': 'Detail MPN tidak dapat dipastikan dalam lingkup masa/tahun; lihat checkpoint privat.'})
                            continue
                        if row is not None:
                            row_bytes = len(json.dumps(row, ensure_ascii=False).encode('utf-8'))
                            if len(value['rows']) >= 10000 or canonical_bytes + row_bytes > MAX_BODY // 2:
                                raise MpnUnsupported('MPN canonical row budget reached')
                            canonical_bytes += row_bytes
                            if use_dom:
                                # Numeric lexemes/identifiers always come from original
                                # JSON. Only verified display date/classification text
                                # uses the DOM projection; raw JSON stays in evidence.
                                row.update(source='dom', transaction_date=flat_dom[index][0],
                                           posting_date=flat_dom[index][1],
                                           accounting_type=flat_dom[index][3], accounting_detail=flat_dom[index][4])
                            value['rows'].append(row)
                            entry = {'record_id': detail_id, 'occurrences': [occurrence]}
                            value['provenance'].append(entry)
                            provenance[detail_id] = entry
                        else:
                            value['coverage']['excluded'] += 1
                    if value['headers'] % 25 == 0 or time.monotonic() - last_checkpoint >= 5:
                        checkpoint()
                        last_checkpoint = time.monotonic()
                    if on_progress:
                        on_progress(value['headers'], total, len(value['rows']))
                first += len(headers)
            if total is None or first != total:
                raise MpnUnsupported('MPN complete parent inventory is unavailable')
            value['inventory_complete'] = True
            value['details_complete'] = True
            ui.finish()
            value['status'] = 'PARTIAL' if value['audit'] else 'COMPLETE'
    except MpnSafetyError:
        value['status'] = 'PARTIAL'
        value['audit'].append({'message': 'Identitas atau snapshot MPN berubah; pengambilan ditolak.'})
        checkpoint()
        raise
    except (MpnUnsupported, PlaywrightError):
        value['status'] = 'PARTIAL'
        value['audit'].append({'message': 'Pengambilan MPN belum lengkap; lihat checkpoint privat dan coba kembali.'})
    except KeyboardInterrupt:
        value['status'] = 'PARTIAL'
        raise
    stop()
    run['complete'] = spt_complete and value['status'] == 'COMPLETE'
    checkpoint()
    return run
