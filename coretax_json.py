"""Pure, source-bound adaptation of the observed submitted-list metadata schema.

Eligibility is a page-level rendering decision, never whole-inventory acceptance.
Original response bytes remain the authority; rendered text is derived evidence.
"""
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse


ORIGIN = 'https://coretax.intranet.pajak.go.id'
PPH21_REFERENCE_URL = (ORIGIN + '/referencedata/api/currentreferencedata/id-ID/'
                       'EBUPOT_TAX_CERTIFICATE,COUNTRY_CODE,EBUPOT_STATUS')
PPH21_MODEL_REFERENCE_URL = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/RETURN_SHEET_MODEL'
PPH21_REFERENCE_URLS = (PPH21_REFERENCE_URL, PPH21_MODEL_REFERENCE_URL)
UNIFIKASI_REFERENCE_URL = (ORIGIN + '/referencedata/api/currentreferencedata/id-ID/'
    'EBUPOT_TAX_CERTIFICATE,EBUPOT_PAYMENT_METHOD,EBUPOTSP_TAX_OBJECT,EBUPOTCY_TAX_OBJECT,PERIOD')
CORPORATE_COUNTRY_REFERENCE_URL = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/COUNTRY_CODE'
CORPORATE_L3_REFERENCE_URLS = {kind: ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + kind
    for kind in ('COUNTRY_CODE', 'CURRENCY', 'FOREIGN_INCOME_TYPE_CIT', 'TAX_TYPE_BY_OTHER_PARTIES')}
CORPORATE_L3_GRID_URL = ORIGIN + '/returnsheet/api/loadcit/l3-table-b-grid'
CORPORATE_L3_FOOTER_URL = CORPORATE_L3_GRID_URL + '/footer'
CORPORATE_L11A_REFERENCE_URLS = {kind: ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + kind
    for kind in ('TYPE_OF_PROMOTION_COST', 'TANGIBLE_ASSET_INCLUDING_BUILDINGS',
                 'NON_PERFORMING_LOAN_CATEGORY', 'DEDUCTION_METHOD', 'TYPE_OF_FULFILLMENT')}
CORPORATE_REFERENCE_REQUESTS = {url: (kind,) for kind, url in
    {**CORPORATE_L3_REFERENCE_URLS, **CORPORATE_L11A_REFERENCE_URLS}.items()}
CORPORATE_REFERENCE_REQUESTS[ORIGIN + '/referencedata/api/currentreferencedata/id-ID/'
    'DEDUCTION_METHOD,TYPE_OF_FULFILLMENT'] = ('DEDUCTION_METHOD', 'TYPE_OF_FULFILLMENT')
CORPORATE_L11A_GRID_URLS = tuple(ORIGIN + f'/returnsheet/api/loadcit/l11a-table-{index}-grid'
                                  for index in (1, 2, 3, 5))
REFERENCE_ORDER_SOURCE = ORIGIN + '/returnsheets/id-ID/vendor.a03856633dae3544.js'
REFERENCE_ORDER_SHA256 = '1de6335b41d5431fd302ab7b7d00b6c593dfa6640c43ab8a88fbfbdb1b0f4b68'
SUBMITTED_ENDPOINT = '/returnsheet/api/returnsheetssubmitted'
LOOKUP_HEADERS = {
    'TaxTypeCode': 'Jenis Pajak',
    'ReturnSheetTypeCode': 'Jenis Surat Pemberitahuan Pajak',
    'TaxPeriodCode': 'Masa Pajak',
    'ReturnSheetStatusCode': 'Status SPT',
    'ChannelCode': 'Kanal',
}
TEXT_HEADERS = {
    'TaxObjectNumber': 'NOP', 'TaxObjectName': 'Nama Objek Pajak',
    'ReturnSheetModel': 'Model SPT', 'BpsNo': 'Nomor Bukti Penerimaan',
    'OfficerName': 'Nama Pegawai', 'OfficerID': 'ID Petugas',
}
DATE_HEADERS = {
    'ExpectedReturnDate': ('Tanggal Jatuh Tempo',),
    'CreationDate': ('Tanggal Dibuat',),
    'EnteredDate': ('Tanggal Penerimaan', 'Tanggal Submit SPT'),
}
REQUIRED_FIELDS = frozenset(LOOKUP_HEADERS) | frozenset(TEXT_HEADERS) | frozenset(DATE_HEADERS) | {'DateOfReceipt'}
JAKARTA = timezone(timedelta(hours=7))


class JsonSafetyError(RuntimeError):
    """Contradictory custody, identity or count evidence cannot use DOM fallback."""


def validate_detail_source(value):
    """Keep the opt-in literal identical across launcher, worker and collector."""
    if type(value) is not str or value not in ('dom', 'json-first'):
        raise ValueError('Detail source must be dom or json-first.')
    return value


class _UnsupportedMetadata(ValueError):
    pass


def _reference_locale(payload):
    """Check explicit catalog/detail locale before any unsupported fallback."""
    if not isinstance(payload, list):
        return
    for catalog in payload:
        if not isinstance(catalog, dict):
            continue
        if 'language' in catalog and catalog['language'] != 'id-ID':
            raise JsonSafetyError('Reference catalog locale contradicts bound request')
        details = catalog.get('Details')
        if isinstance(details, list):
            for entry in details:
                if isinstance(entry, dict) and 'language' in entry and entry['language'] != 'id-ID':
                    raise JsonSafetyError('Reference detail locale contradicts bound request')


def _reference_order_proof(induk, projected):
    """Duplicate ordinary codes depend on the positively hashed loaded vendor."""
    present = 'reference_order_build' in induk
    if (present and (type(induk['reference_order_build']) is not str
                     or induk['reference_order_build'] != REFERENCE_ORDER_SHA256)
            or projected['requires_vendor'] and not present):
        raise _UnsupportedMetadata('unverified_reference_order_build')
    if present:
        for entry in projected['provenance']:
            if entry.get('catalog_order_rule'):
                entry['reference_order_build'] = induk['reference_order_build']


def _capture_clock_interval(value, attempt):
    """Validate optional custody metadata, never consult this machine's clock."""
    if (not isinstance(value, dict) or set(value) != {'attempt', 'start_ms', 'end_ms', 'timezone'}
            or type(attempt) is not str or not re.fullmatch(r'[a-f0-9]{32}', attempt)
            or value.get('attempt') != attempt or value.get('timezone') != 'Asia/Jakarta'
            or type(value.get('start_ms')) is not int or type(value.get('end_ms')) is not int
            or not 0 <= value['start_ms'] <= value['end_ms'] <= 8640000000000000):
        raise JsonSafetyError('Captured browser clock interval is invalid or unbound')
    return dict(value)


def _reference_date_ms(value):
    """Reviewed ISO subset of JS Date: date-only UTC; local datetime Jakarta."""
    if value is None or value == '':
        return None
    if (type(value) is not str or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
            r'(?:\.[0-9]{3})?(?:Z|[+-](?:[01][0-9]|2[0-3]):[0-5][0-9])?)?', value)):
        raise _UnsupportedMetadata('unsupported_grid_reference_date')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.year < 1970:
            raise ValueError('Unreviewed historic local offset')
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc if len(value) == 10 else timezone(timedelta(hours=7)))
        elapsed = date.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
        return (elapsed.days * 86400 + elapsed.seconds) * 1000 + elapsed.microseconds // 1000
    except (ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_grid_reference_date') from None


def _capture_component_lifetime(value, *, attempt, record_id, source_url, detail_url):
    """Validate optional manifest-owned facts; a replay never probes a browser."""
    keys = {'attempt', 'kind', 'record_id', 'source_url', 'detail_url',
            'transition_count', 'same_document', 'source_owner', 'detail_owner'}
    if (not isinstance(value, dict) or set(value) != keys
            or type(attempt) is not str or not re.fullmatch(r'[a-f0-9]{32}', attempt)
            or value.get('attempt') != attempt or value.get('record_id') != record_id
            or value.get('kind') != 'corporate-submitted-spa-v1'
            or value.get('source_url') != source_url or value.get('detail_url') != detail_url
            or type(value.get('transition_count')) is not int or value['transition_count'] != 1
            or any(value.get(key) is not True for key in ('same_document', 'source_owner', 'detail_owner'))
            or not _trusted_origin(source_url) or not _trusted_origin(detail_url)):
        raise JsonSafetyError('Captured component lifetime is invalid or unbound')
    source, detail = urlparse(source_url), urlparse(detail_url)
    match = re.fullmatch(r'/returnsheets/id-ID/submitted-returnsheets/([^/]+)', source.path)
    if (match is None or source.params or source.query or source.fragment
            or detail.params or detail.query != 'view=true' or detail.fragment
            or not re.fullmatch(r'/returnsheets/id-ID/corporate-income-tax-return/'
                + re.escape(match.group(1)) + '/' + re.escape(record_id) + r'/ICT_RCIT/[^/%\\]+', detail.path)):
        raise JsonSafetyError('Captured component lifetime route is unverified')
    return dict(value)


def _capture_l8_lifetime(value, *, attempt, record_id, source_url, detail_url):
    """Validate the stronger optional L8 history, never inferred during replay."""
    keys = {'kind', 'attempt', 'record_id', 'source_url', 'detail_url',
            'fresh_root', 'stable_root', 'no_dependent_forms'}
    if (not isinstance(value, dict) or set(value) != keys
            or value.get('kind') != 'corporate-l8-spa-v1'
            or value.get('attempt') != attempt or value.get('record_id') != record_id
            or value.get('source_url') != source_url or value.get('detail_url') != detail_url
            or any(value.get(key) is not True for key in
                   ('fresh_root', 'stable_root', 'no_dependent_forms'))):
        raise JsonSafetyError('Captured L8 history is invalid or unbound')
    _capture_component_lifetime({'kind': 'corporate-submitted-spa-v1', 'attempt': attempt,
        'record_id': record_id, 'source_url': source_url, 'detail_url': detail_url,
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True},
        attempt=attempt, record_id=record_id, source_url=source_url, detail_url=detail_url)
    return dict(value)


def _reference_consumer_order(details, kind):
    """Pinned ordinary cache.add order, retaining original response ordinals.

    This is intentionally separate from PERIOD, model dropdowns, Code-sorted
    ignore types and ECONOMIC_CODE's additional lifecycle. Never sort raw bytes.
    """
    ordinary = {'EBUPOT_TAX_CERTIFICATE', 'COUNTRY_CODE', 'EBUPOT_STATUS',
                'EBUPOT_PAYMENT_METHOD', 'EBUPOTSP_TAX_OBJECT', 'EBUPOTCY_TAX_OBJECT',
                'CURRENCY', 'FOREIGN_INCOME_TYPE_CIT', 'TAX_TYPE_BY_OTHER_PARTIES',
                *CORPORATE_L11A_REFERENCE_URLS}
    if (kind not in ordinary or not isinstance(details, list)
            or any(not isinstance(row, dict) or type(row.get('CodeDescription')) is not str for row in details)):
        raise _UnsupportedMetadata('unsupported_reference_cache_order')

    def string_key(value):
        if type(value) is not str:
            raise _UnsupportedMetadata('unsupported_reference_cache_string')
        try:
            # Big-endian bytes compare unsigned UTF-16 code units, as JS does.
            return value.encode('utf-16-be')
        except UnicodeEncodeError:
            raise _UnsupportedMetadata('unsupported_reference_cache_string') from None

    if any(row.get('ParameterData') is not None and type(row['ParameterData']) is not str for row in details):
        raise _UnsupportedMetadata('unsupported_reference_cache_parameter')
    first = details[0].get('ParameterData') if details else None
    pairs = list(enumerate(details))
    rule = 'reviewed-cache-description-utf16'
    descriptions = [string_key(row['CodeDescription']) for row in details]
    if first is None or '"DisplayIndex":' not in first:
        keys = descriptions
    else:
        keys, types = [], set()
        for row in details:
            parameter = row.get('ParameterData')
            if type(parameter) is not str:
                raise _UnsupportedMetadata('unsupported_reference_display_index')
            try:
                parsed = json.loads(parameter, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
            except (ValueError, JsonSafetyError, RecursionError):
                raise _UnsupportedMetadata('unsupported_reference_display_index') from None
            if not isinstance(parsed, dict) or 'DisplayIndex' not in parsed:
                raise _UnsupportedMetadata('unsupported_reference_display_index')
            value = parsed['DisplayIndex']
            if type(value) is int and abs(value) <= 9007199254740991:
                key = value
            elif type(value) is str:
                key = string_key(value)
            else:
                raise _UnsupportedMetadata('unsupported_reference_display_index')
            keys.append(key)
            types.add(type(value))
        if len(types) != 1:
            raise _UnsupportedMetadata('mixed_reference_display_index_types')
        rule = ('reviewed-cache-display-index-integer' if types == {int} else
                'reviewed-cache-display-index-utf16')
    # Python's stable sort preserves the pinned Lodash original-index tie break.
    return sorted(pairs, key=lambda pair: keys[pair[0]]), rule


def _select_reference_version(candidates, clock_interval=None):
    """Pinned getActiveReferenceDataValue; require the same row at every cutoff.

    Candidates arrive in proved cache consumer order, carrying original source
    ordinals. Future rows can only expire as time moves forward, so the cursor
    advances at most once per row across all cutoffs.
    """
    clock = (_capture_clock_interval(clock_interval, clock_interval.get('attempt'))
             if isinstance(clock_interval, dict) else None)
    if clock_interval is not None and clock is None:
        raise JsonSafetyError('Captured browser clock interval is invalid or unbound')
    for ordinal, row in candidates:
        if 'ValidTo' in row and row['ValidTo'] in (None, ''):
            return ordinal, row, 'first-open-ended'
    if len(candidates) == 1:
        return *candidates[0], 'only-version'
    if not candidates or clock is None:
        raise _UnsupportedMetadata('clock_dependent_grid_reference_versions')
    dates, latest, fallback = [], None, 0
    for index, (_, row) in enumerate(candidates):
        if 'ValidTo' not in row:
            raise _UnsupportedMetadata('missing_grid_reference_validity')
        until, since = _reference_date_ms(row['ValidTo']), _reference_date_ms(row.get('ValidFrom'))
        dates.append(until)
        if since is not None and (latest is None or since > latest):
            latest, fallback = since, index
    start, end = clock['start_ms'], clock['end_ms']
    points = sorted({start, end, *(value for value in dates if value is not None and start <= value <= end)})
    cursor, chosen, rule = 0, None, None
    for point in points:
        while cursor < len(dates) and (dates[cursor] is None or dates[cursor] <= point):
            cursor += 1
        current = cursor if cursor < len(dates) else fallback
        if chosen is None:
            chosen = current
            rule = ('first-future-valid-to' if cursor < len(dates) else
                    'latest-valid-from' if latest is not None else 'first-candidate')
        elif current != chosen:
            raise _UnsupportedMetadata('unstable_grid_reference_version')
    return *candidates[chosen], rule


def _trusted_origin(value):
    if not isinstance(value, str) or value != value.strip() or '\\' in value or any(ord(c) < 32 for c in value):
        return False
    try:
        parsed = urlparse(value)
        return (parsed.scheme == 'https' and parsed.hostname == urlparse(ORIGIN).hostname
                and parsed.port in (None, 443) and parsed.username is None and parsed.password is None)
    except ValueError:
        return False


def _object_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise JsonSafetyError('Duplicate JSON field makes source evidence ambiguous')
        result[key] = value
    return result


def _reject_constant(value):
    raise JsonSafetyError('Non-finite JSON number is unsupported source evidence')


def _period_union_values(condition):
    """Recognize the shipped grid's OR-equality form without guessing operators."""
    if not isinstance(condition, dict) or condition.get('PropertyName') != 'TaxPeriodCode':
        return None
    mode = condition.get('MatchMode')
    if not isinstance(mode, str) or not mode.startswith('any-'):
        return None
    operators = mode.split('-')[1:]
    if not operators or any(operator != 'equals' for operator in operators):
        return None
    if condition.get('CaseSensitive') is not True or condition.get('AsString') is not False:
        raise JsonSafetyError('Unobserved period comparison flags')
    values = condition.get('Value')
    if (not isinstance(values, list) or len(values) != len(operators)
            or any(not isinstance(value, str) or not value or value != value.strip() for value in values)
            or len(set(values)) != len(values)):
        raise JsonSafetyError('Invalid period union filter')
    return values


def _period_contains_year(condition):
    if (not isinstance(condition, dict) or condition.get('PropertyName') != 'TaxPeriodCode'
            or condition.get('MatchMode') != 'contains'):
        return None
    value = condition.get('Value')
    if (not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}', value)
            or not 1900 <= int(value) <= 2100
            or condition.get('CaseSensitive') is not True or condition.get('AsString') is not False):
        raise JsonSafetyError('Invalid period year candidate filter')
    return value


def validate_period_filter(condition):
    """Limit owned request rewriting to the independently observed period forms."""
    if _period_contains_year(condition) is not None or _period_union_values(condition) is not None:
        return
    if (isinstance(condition, dict) and condition.get('PropertyName') == 'TaxPeriodCode'
            and condition.get('MatchMode') == 'equals'
            and isinstance(condition.get('Value'), str) and condition['Value']
            and condition['Value'] == condition['Value'].strip()
            and condition.get('CaseSensitive') is True and condition.get('AsString') is False):
        return
    raise JsonSafetyError('Unsupported owned period filter')


def validate_inventory_binding(context):
    """Validate the observed request/frame/epoch independently of metadata support."""
    taxpayer = context.get('taxpayer_id')
    if not isinstance(taxpayer, str) or not taxpayer or taxpayer != taxpayer.strip():
        raise JsonSafetyError('Missing taxpayer identity')
    source = context.get('source_url')
    if not _trusted_origin(source):
        raise JsonSafetyError('Source origin is not authorized')
    source_path = urlparse(source).path
    if source_path.rstrip('/') != '/returnsheets/id-ID/submitted-returnsheets/' + taxpayer:
        raise JsonSafetyError('Submitted source taxpayer or status scope mismatch')
    if context.get('source_status') != 'SPT Dilaporkan':
        raise JsonSafetyError('Submitted source status mismatch')
    endpoint = context.get('response_url')
    if not _trusted_origin(endpoint) or urlparse(endpoint).path != SUBMITTED_ENDPOINT:
        raise JsonSafetyError('Unexpected submitted-list response source or origin')
    frame = context.get('frame_url')
    if not _trusted_origin(frame) or urlparse(frame).path.rstrip('/') != source_path.rstrip('/'):
        raise JsonSafetyError('Response frame changed source or taxpayer')
    if context.get('method') != 'POST' or type(context.get('http_status')) is not int or not 200 <= context['http_status'] < 300:
        raise JsonSafetyError('List request method or HTTP status is unsafe')
    sequence, after = context.get('sequence'), context.get('after_sequence')
    if type(sequence) is not int or type(after) is not int or not 0 <= after < sequence:
        raise JsonSafetyError('Stale list response sequence')
    request = context.get('request')
    if not isinstance(request, dict) or request.get('TaxpayerAggregateIdentifier') != taxpayer:
        raise JsonSafetyError('Request taxpayer scope mismatch')
    if (type(request.get('First')) is not int or request['First'] < 0
            or type(request.get('Rows')) is not int or request['Rows'] <= 0):
        raise JsonSafetyError('Invalid page request First/Rows')
    if request.get('isArchieved') is not False:
        raise JsonSafetyError('Archive request contradicts submitted source scope')
    if not isinstance(request.get('Filters'), list):
        raise JsonSafetyError('Invalid request filter scope')
    # Empty responses still require a well-formed declared scope.
    for condition in request['Filters']:
        _period_union_values(condition)
        _period_contains_year(condition)
    page = context.get('page')
    if type(page) is not int or page < 1 or request['First'] != (page - 1) * request['Rows']:
        raise JsonSafetyError('Request offset contradicts source page')
    return request


def validate_inventory_rows(rows, taxpayer_id):
    """Require literal RecordId and reject identity contradictions before rendering."""
    identifiers = []
    for row in rows:
        if not isinstance(row, dict):
            raise JsonSafetyError('Invalid record identity row')
        identifier = row.get('RecordId')
        if not isinstance(identifier, str) or not identifier or identifier != identifier.strip():
            raise JsonSafetyError('Missing or invalid RecordId identity')
        if identifier in identifiers:
            raise JsonSafetyError('Repeated RecordId identity')
        # Older safe DOM records may not expose this field; a supplied foreign
        # value is always a contradiction, not a reason to fall back.
        if 'TaxpayerAggregateIdentifier' in row and row['TaxpayerAggregateIdentifier'] != taxpayer_id:
            raise JsonSafetyError('Record taxpayer identity differs from selected scope')
        identifiers.append(identifier)
    return identifiers


def _display_text(value):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise _UnsupportedMetadata('unsupported_metadata_type')
    return re.sub(r'\s+', ' ', value).strip()


def _display_date(value, context):
    if value is None:
        return ''
    if not isinstance(value, str):
        raise _UnsupportedMetadata('unsupported_date_type')
    if '0001' in value:
        return ''
    if context.get('date_format') != 'dd-MM-yyyy' or context.get('timezone') != 'Asia/Jakarta':
        raise _UnsupportedMetadata('unsupported_date_rendering')
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?', value):
        raise _UnsupportedMetadata('unsupported_date_format')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise _UnsupportedMetadata('unsupported_date_format') from exc
    if date.tzinfo is None:
        date = date.replace(tzinfo=JAKARTA)
    return date.astimezone(JAKARTA).strftime('%d-%m-%Y')


def _render_row(row, context):
    if not REQUIRED_FIELDS <= row.keys():
        raise _UnsupportedMetadata('unsupported_metadata_schema')
    catalogs = context.get('lookup_labels')
    if not isinstance(catalogs, dict):
        raise _UnsupportedMetadata('unsupported_reference_catalog')
    meta = {}
    for field, header in LOOKUP_HEADERS.items():
        code = row[field]
        labels = catalogs.get(field)
        if not isinstance(code, str) or not isinstance(labels, dict) or code not in labels or not isinstance(labels[code], str):
            raise _UnsupportedMetadata('unsupported_reference_code')
        meta[header] = _display_text(labels[code])
    for field, header in TEXT_HEADERS.items():
        meta[header] = _display_text(row[field])
    for field, headers in DATE_HEADERS.items():
        value = _display_date(row[field], context)
        for header in headers:
            meta[header] = value
    meta['Tanggal Resi Pos'] = (_display_date(row['DateOfReceipt'], context)
                               if row['ChannelCode'] in ('PAPER_AT_COUNTER', 'PAPER_VIA_MAIL') else '')
    return meta


def adapt_inventory_page(body: bytes, context: dict) -> dict:
    """Adapt one original submitted-list response using its owned request context.

    Return page eligibility and literal display/source metadata without changing
    source bytes or identifiers. Unsupported layouts require whole-page DOM
    fallback. JsonSafetyError rejects request, identity, snapshot or known caption
    contradictions; native eligibility does not certify inventory completeness."""
    request = validate_inventory_binding(context)
    if not isinstance(body, bytes):
        raise JsonSafetyError('Original list response bytes are required')
    try:
        data = json.loads(body, object_pairs_hook=_object_pairs, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise JsonSafetyError('List response is not valid source JSON') from exc
    if not isinstance(data, dict) or data.get('IsSuccessful') is not True:
        raise JsonSafetyError('List response lacks explicit success status')
    payload = data.get('Payload')
    if not isinstance(payload, dict) or type(payload.get('TotalRecords')) is not int or payload['TotalRecords'] < 0:
        raise JsonSafetyError('Invalid declared TotalRecords count')
    total = payload['TotalRecords']
    rows = payload.get('Data')
    if rows is None and total == 0:
        rows = []
    if not isinstance(rows, list):
        raise JsonSafetyError('Data rows contradict declared total count')
    first = request['First']
    if first > total or len(rows) != min(request['Rows'], total - first):
        raise JsonSafetyError('Data row count contradicts request page or declared total')
    identifiers = validate_inventory_rows(rows, context['taxpayer_id'])
    unsupported_filter = False
    for row in rows:
        if row.get('TaxpayerAggregateIdentifier') != context['taxpayer_id']:
            raise JsonSafetyError('Missing or foreign taxpayer identity in submitted record')
        if 'ReturnSheetStatusCode' in row and row['ReturnSheetStatusCode'] != 'SUBMITTED':
            raise JsonSafetyError('Record status contradicts submitted source')
        for condition in request['Filters']:
            year = _period_contains_year(condition)
            if year is not None:
                period = row.get('TaxPeriodCode')
                if not isinstance(period, str) or year not in period:
                    raise JsonSafetyError('Record period/filter contradicts request scope')
                continue
            values = _period_union_values(condition)
            if values is not None:
                if row.get('TaxPeriodCode') not in values:
                    raise JsonSafetyError('Record period/filter contradicts request scope')
                continue
            if not isinstance(condition, dict) or condition.get('MatchMode') != 'equals':
                unsupported_filter = True
                continue
            field = condition.get('PropertyName')
            if field not in row:
                unsupported_filter = True
            elif row[field] != condition.get('Value'):
                raise JsonSafetyError('Record period/filter contradicts request scope')
    if unsupported_filter:
        return {'eligible': False, 'reason': 'unsupported_request_filter', 'total': total, 'rows': []}
    rendered = []
    digest = hashlib.sha256(body).hexdigest()
    try:
        for row, identifier in zip(rows, identifiers):
            meta = _render_row(row, context)
            fields = REQUIRED_FIELDS | {'RecordId', 'AggregateIdentifier', 'TaxpayerAggregateIdentifier'}
            rendered.append({
                'record_id': identifier, 'meta': meta,
                'source_fields': {field: row[field] for field in fields if field in row},
                'source_identity': {
                    'record_id': identifier, 'aggregate_id': row.get('AggregateIdentifier'),
                    'taxpayer_id': context['taxpayer_id'], 'source_url': context['source_url'],
                    'source_status': context['source_status'], 'page': context['page'],
                    'sequence': context['sequence'], 'body_sha256': digest,
                },
            })
    except _UnsupportedMetadata as exc:
        # Skema tampilan yang belum didukung menggugurkan seluruh halaman JSON;
        # konflik identitas, filter, dan jumlah di atas tetap menjadi galat.
        return {'eligible': False, 'reason': str(exc), 'total': total, 'rows': []}
    return {'eligible': True, 'reason': 'verified_submitted_metadata', 'total': total, 'rows': rendered}


# Kept separate from inventory and capture: this API has no I/O or mode switch.
_CIT_CONTROLS = frozenset({'TaxType', 'IsDraft', 'TaxPeriodCode',
                           'ReturnSheetRecordIdentifier', 'ReturnSheetAggregateIdentifier'})
_CIT_HEADERS = ['JSON path', 'JSON type', 'Source value']
_CIT_SECRET_KEYS = frozenset({'password', 'passwd', 'pwd', 'authorization', 'cookie',
                              'setcookie', 'token', 'accesstoken', 'refreshtoken',
                              'idtoken', 'apikey', 'clientsecret', 'secret', 'sessionid'})
_CIT_SECRET_TEXT = re.compile(r'\bBearer\s+\S+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+', re.I)
_CIT_INVALID_XML = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


class _CorporateNumber(str):
    """Private parse marker; convert to plain lexical text at the DTO boundary."""


def _corporate_json(raw):
    try:
        return json.loads(raw, object_pairs_hook=_object_pairs, parse_constant=_reject_constant,
                          parse_int=_CorporateNumber, parse_float=_CorporateNumber)
    except (ValueError, UnicodeError, RecursionError):
        # Parser excerpts and chained exceptions can contain private source text.
        raise JsonSafetyError('Corporate source JSON cannot be safely decoded') from None


def _corporate_secret_key(value):
    return re.sub(r'[^a-z0-9]', '', value.casefold()) in _CIT_SECRET_KEYS


def _corporate_privacy(value, depth=0):
    if depth > 64:
        raise JsonSafetyError('Corporate source privacy nesting exceeds its budget')
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str) or _corporate_secret_key(key):
                raise JsonSafetyError('Corporate source contains prohibited secret metadata')
            _corporate_privacy(item, depth + 1)
    elif isinstance(value, list):
        for item in value:
            _corporate_privacy(item, depth + 1)
    elif isinstance(value, str):
        if _CIT_SECRET_TEXT.search(value):
            raise JsonSafetyError('Corporate source contains prohibited secret text')
        text = value.lstrip()
        if text.startswith(('{', '[', '"')):
            decoded = _corporate_json(text)
            if decoded != value:
                _corporate_privacy(decoded, depth + 1)


def _corporate_url(value):
    from urllib.parse import parse_qsl, unquote
    if not _trusted_origin(value):
        return False
    parsed = urlparse(value)
    if parsed.fragment or _CIT_SECRET_TEXT.search(unquote(value)):
        return False
    for key, item in parse_qsl(parsed.query, keep_blank_values=True):
        if _corporate_secret_key(unquote(key)):
            return False
        _corporate_privacy(item)
    return True


def _corporate_request_key(value, depth=0):
    """Do not let Python's True == 1 turn a different request into a binding."""
    if depth > 64:
        raise JsonSafetyError('Observed request nesting exceeds its budget')
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise JsonSafetyError('Observed request keys are not literal strings')
        return ('object', tuple((key, _corporate_request_key(value[key], depth + 1))
                                for key in sorted(value)))
    if isinstance(value, list):
        return ('array', tuple(_corporate_request_key(item, depth + 1) for item in value))
    if value is None or type(value) in (str, bool, int):
        return (type(value).__name__, value)
    if type(value) is float:
        import math
        if math.isfinite(value):
            return ('float', repr(value))
    raise JsonSafetyError('Observed request has an unsupported scalar type')


def _corporate_literal(value):
    return isinstance(value, str) and bool(value) and value == value.strip()


def _corporate_selected(record, scope):
    if (not isinstance(scope, (list, tuple)) or len(scope) != 3
            or not isinstance(scope[0], str) or not re.fullmatch(r'[0-9]{16}', scope[0])
            or type(scope[1]) is not int or not 1900 <= scope[1] <= 2100
            or scope[2] not in ('period', 'submission')):
        raise JsonSafetyError('Invalid corporate scope; values are not normalized')
    if not isinstance(record, dict) or not _corporate_literal(record.get('record_id')):
        raise JsonSafetyError('Missing literal selected corporate record identity')
    identifier = record['record_id']
    if '/' in identifier or '\\' in identifier:
        raise JsonSafetyError('Invalid literal selected record identity')
    if 'scope' in record and _corporate_request_key(record['scope']) != _corporate_request_key(list(scope)):
        raise JsonSafetyError('Selected record contradicts corporate scope')
    source = record.get('list_url')
    if not _corporate_url(source):
        raise JsonSafetyError('Selected corporate source is not authorized')
    match = re.fullmatch(r'/returnsheets/id-ID/[^/]*returnsheets/([^/]+)/?', urlparse(source).path)
    if not match:
        raise JsonSafetyError('Selected corporate taxpayer source is unverified')
    fields, identity = record.get('source_fields', {}), record.get('source_identity', {})
    if not isinstance(fields, dict) or not isinstance(identity, dict):
        raise JsonSafetyError('Selected native identity metadata is invalid')
    bound = {}
    for canonical, native in [('record_id', 'RecordId'), ('aggregate_id', 'AggregateIdentifier'),
                              ('taxpayer_id', 'TaxpayerAggregateIdentifier')]:
        values = [v for v in (identity.get(canonical), fields.get(native)) if v is not None]
        if any(not _corporate_literal(v) for v in values) or len(set(values)) > 1:
            raise JsonSafetyError('Selected canonical and native identities contradict')
        bound[canonical] = values[0] if values else None
    if bound['record_id'] is not None and bound['record_id'] != identifier:
        raise JsonSafetyError('Selected native record identity contradicts selection')
    if bound['taxpayer_id'] is not None and bound['taxpayer_id'] != match.group(1):
        raise JsonSafetyError('Selected native taxpayer contradicts source URL')
    if identity.get('source_url', source) != source:
        raise JsonSafetyError('Selected native source URL contradicts selection')
    bound.update(record_id=identifier, frame_taxpayer=match.group(1), native_fields=fields, source_url=source)
    return bound


def _corporate_bindings(observed_forms):
    if not isinstance(observed_forms, list):
        raise JsonSafetyError('Observed corporate forms must be explicit caller bindings')
    sections, paths, requests, grids, responses, dependencies = [], [], {}, [], [], []
    primary = None
    names = set()
    for form in observed_forms:
        if not isinstance(form, dict) or not _corporate_literal(form.get('name')) or form['name'] in names:
            raise JsonSafetyError('Observed form names are missing or ambiguous')
        names.add(form['name'])
        section = {'name': form['name'], 'fields': [], 'tables': [], 'text': ''}
        sections.append(section)
        if 'primary' in form:
            binding = form['primary']
            if (primary is not None or not isinstance(binding, dict)
                    or not _corporate_url(binding.get('endpoint'))
                    or not urlparse(binding['endpoint']).path.startswith('/returnsheet/api/')
                    or 'request_json' not in binding
                    or binding['request_json'] is not None and not isinstance(binding['request_json'], dict)):
                raise JsonSafetyError('Observed primary source binding is invalid or ambiguous')
            _corporate_privacy(binding['request_json'])
            primary = (binding['endpoint'], _corporate_request_key(binding['request_json']))
        declared = form.get('paths', [])
        if not isinstance(declared, list):
            raise JsonSafetyError('Observed source paths are invalid')
        for path in declared:
            if (not isinstance(path, list) or not path or len(path) > 64
                    or any(not _corporate_literal(token) for token in path)
                    or path[0] in _CIT_CONTROLS):
                raise JsonSafetyError('Observed source path tokens are invalid')
            key = tuple(path)
            if any(key[:len(old)] == old or old[:len(key)] == key for old, _ in paths):
                raise JsonSafetyError('Observed source paths overlap or repeat')
            paths.append((key, section))
        for kind in ('grids', 'responses', 'dependencies'):
            declared = form.get(kind, [])
            if not isinstance(declared, list):
                raise JsonSafetyError('Observed source request bindings are invalid')
            for binding in declared:
                if not isinstance(binding, dict) or not _corporate_url(binding.get('endpoint')):
                    raise JsonSafetyError('Observed source endpoint is not authorized')
                endpoint = binding['endpoint']
                if not urlparse(endpoint).path.startswith('/returnsheet/api/'):
                    raise JsonSafetyError('Observed source endpoint is not a detail API')
                state = {'kind': kind, 'section': section, 'endpoint': endpoint, 'seen': {}, 'expected': []}
                if kind != 'dependencies':
                    if not _corporate_literal(binding.get('name')):
                        raise JsonSafetyError('Observed source table name is missing')
                    state['name'] = binding['name']
                if kind == 'grids':
                    declarations = binding.get('pages')
                elif kind == 'responses':
                    values = binding.get('requests')
                    declarations = [{'request_json': req} for req in values] if isinstance(values, list) else None
                else:
                    declarations = [{'request_json': binding.get('request_json')}]
                if not isinstance(declarations, list) or not declarations:
                    raise JsonSafetyError('Observed source requests are missing')
                for declaration in declarations:
                    if not isinstance(declaration, dict):
                        raise JsonSafetyError('Observed page declaration is invalid')
                    request = declaration.get('request_json')
                    if not isinstance(request, dict) or not request:
                        raise JsonSafetyError('Observed request dictionaries must be nonempty')
                    _corporate_privacy(request)
                    if len(json.dumps(request, ensure_ascii=False).encode('utf-8')) > 65536:
                        raise JsonSafetyError('Observed request metadata exceeds its budget')
                    key = (endpoint, _corporate_request_key(request))
                    if key in requests:
                        raise JsonSafetyError('Observed request binding is ambiguous')
                    offset = declaration.get('offset', 0)
                    if type(offset) is not int or offset < 0:
                        raise JsonSafetyError('Observed source page offset is invalid')
                    requests[key] = (state, offset)
                    state['expected'].append(key)
                if kind == 'grids':
                    grids.append(state)
                elif kind == 'responses':
                    responses.append(state)
                else:
                    dependencies.append(state)
    if primary in requests:
        raise JsonSafetyError('Primary and auxiliary source bindings overlap')
    return sections, paths, requests, grids, responses, dependencies, primary


def _check_corporate_route(frame, selected):
    """Known submitted route identities remain fatal before any fallback gate."""
    match = re.fullmatch(r'/returnsheets/id-ID/corporate-income-tax-return/([^/]+)/([^/]+)/([^/]+)/([^/]+)/?',
                         urlparse(frame).path)
    if match:
        expected = (selected['frame_taxpayer'], selected['record_id'],
                    selected['native_fields'].get('TaxTypeCode'), selected['aggregate_id'])
        if any(value is not None and actual != value for actual, value in zip(match.groups(), expected)):
            raise JsonSafetyError('Corporate route identity contradicts selected source')


def _corporate_packet(item, selected, scope, attempt, sequences, *, allow_pph21_reference=False,
                      allow_unifikasi_reference=False, allow_corporate_reference=False):
    if not isinstance(item, dict) or not isinstance(item.get('body'), bytes) or not isinstance(item.get('context'), dict):
        raise JsonSafetyError('Original corporate body bytes and captured descriptor are required')
    raw, ctx = item['body'], item['context']
    _corporate_privacy(ctx)
    if (type(ctx.get('bytes')) is not int or ctx['bytes'] != len(raw)
            or len(raw) > 32 * 1024 * 1024 or ctx.get('sha256') != hashlib.sha256(raw).hexdigest()):
        raise JsonSafetyError('Captured corporate byte custody contradicts original source')
    if (ctx.get('record_id') != selected['record_id']
            or _corporate_request_key(ctx.get('scope')) != _corporate_request_key(list(scope))):
        raise JsonSafetyError('Captured corporate record or scope contradicts selection')
    current = ctx.get('attempt')
    if not isinstance(current, str) or not re.fullmatch(r'[a-f0-9]{32}', current) or attempt is not None and attempt != current:
        raise JsonSafetyError('Captured corporate attempts are missing or mixed')
    clock = _capture_clock_interval(ctx['clock_interval'], current) if 'clock_interval' in ctx else None
    sequence = ctx.get('sequence')
    if type(sequence) is not int or sequence < 1 or sequence in sequences:
        raise JsonSafetyError('Captured corporate event sequence is invalid or duplicated')
    sequences.add(sequence)
    endpoint, frame = ctx.get('url'), ctx.get('frame_url')
    if not _corporate_url(endpoint):
        raise JsonSafetyError('Captured corporate endpoint or method is unsafe')
    reference = (allow_pph21_reference is True and endpoint in PPH21_REFERENCE_URLS
                 and ctx.get('method') == 'GET' and ctx.get('request_json') is None
                 and selected['native_fields'].get('TaxTypeCode') == 'ICT_WIT'
                 and selected['native_fields'].get('ReturnSheetTypeCode') == 'ICT_WITR')
    reference = reference or (allow_unifikasi_reference is True and endpoint == UNIFIKASI_REFERENCE_URL
                 and ctx.get('method') == 'GET' and ctx.get('request_json') is None
                 and selected['native_fields'].get('TaxTypeCode') == 'ICT_WT'
                 and selected['native_fields'].get('ReturnSheetTypeCode') == 'ICT_WTR')
    reference = reference or (allow_corporate_reference is True and endpoint in CORPORATE_REFERENCE_REQUESTS
                 and ctx.get('method') == 'GET' and ctx.get('request_json') is None
                 and selected['native_fields'].get('TaxTypeCode') == 'ICT_RCIT'
                 and selected['native_fields'].get('ReturnSheetTypeCode') == 'ICT_RCITR')
    ordinary = (urlparse(endpoint).path.startswith('/returnsheet/api/')
                and not urlparse(endpoint).path.casefold().startswith('/returnsheet/api/returnsheets')
                and ctx.get('method') == 'POST')
    if not (ordinary or reference):
        raise JsonSafetyError('Captured corporate endpoint or method is unsafe')
    if endpoint in (CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL, *CORPORATE_L11A_GRID_URLS):
        request = ctx.get('request_json')
        if isinstance(request, dict) and 'ReturnSheetRecordId' in request:
            value = request['ReturnSheetRecordId']
            if type(value) is not str or value != selected['record_id']:
                raise JsonSafetyError('Known corporate request contradicts selected return')
    if not _corporate_url(frame) or not urlparse(frame).path.startswith('/returnsheets/'):
        raise JsonSafetyError('Captured corporate frame is unauthorized')
    parts = urlparse(frame).path.split('/')
    if selected['record_id'] not in parts or selected['frame_taxpayer'] not in parts:
        raise JsonSafetyError('Captured corporate frame ownership contradicts selection')
    _check_corporate_route(frame, selected)
    lifetime = None
    if 'component_lifetime' in ctx:
        if (selected['native_fields'].get('TaxTypeCode') != 'ICT_RCIT'
                or selected['native_fields'].get('ReturnSheetTypeCode') != 'ICT_RCITR'):
            raise JsonSafetyError('Captured component lifetime has an unsupported owner')
        lifetime = _capture_component_lifetime(ctx['component_lifetime'], attempt=current,
            record_id=selected['record_id'], source_url=selected['source_url'], detail_url=frame)
    l8_lifetime = None
    if 'corporate_l8_lifetime' in ctx:
        if lifetime is None:
            raise JsonSafetyError('Captured L8 history lacks its component lifetime')
        l8_lifetime = _capture_l8_lifetime(ctx['corporate_l8_lifetime'], attempt=current,
            record_id=selected['record_id'], source_url=selected['source_url'], detail_url=frame)
    status = ctx.get('status')
    if type(status) is not int or not 100 <= status <= 599 or status in (401, 403):
        raise JsonSafetyError('Captured corporate HTTP authorization is unsafe')
    envelope = _corporate_json(raw)
    _corporate_privacy(envelope)
    if reference and isinstance(envelope, dict):
        _reference_locale(envelope.get('Payload'))
    if (urlparse(endpoint).path == '/returnsheet/api/prefillreturnsheet/corporate-income'
            and isinstance(envelope, dict) and isinstance(envelope.get('Payload'), dict)):
        status_source = selected['native_fields'].get('ReturnSheetStatusCode')
        payload = envelope['Payload']
        if (status_source is not None and 'ReturnSheetStatusCode' in payload
                and (type(payload['ReturnSheetStatusCode']) is not str
                     or payload['ReturnSheetStatusCode'] != status_source)):
            raise JsonSafetyError('Corporate response status contradicts selected source')
    # Only bounded metadata is retained, never the collector packet/raw payload.
    event = {key: ctx[key] for key in ('relative_path', 'bytes', 'sha256', 'url', 'method', 'status',
                                     'frame_url', 'sequence', 'attempt', 'record_id', 'identity_validated') if key in ctx}
    event['scope'] = list(scope)
    if clock is not None:
        event['clock_interval'] = clock
    if lifetime is not None:
        event['component_lifetime'] = lifetime
    if l8_lifetime is not None:
        event['corporate_l8_lifetime'] = l8_lifetime
    if ctx.get('request_json') is not None:
        _corporate_request_key(ctx['request_json'])
        event['request_json'] = json.loads(json.dumps(ctx['request_json'], ensure_ascii=False))
    return envelope, ctx, current, event


def _corporate_pointer(tokens):
    return '/' + '/'.join(str(token).replace('~', '~0').replace('/', '~1') for token in tokens)


def _corporate_rows(value, tokens, rows, depth=0):
    if depth > 64:
        raise JsonSafetyError('Corporate source hierarchy exceeds its budget')
    if isinstance(value, dict) and value:
        for key, item in value.items():
            _corporate_rows(item, (*tokens, key), rows, depth + 1)
        return
    if isinstance(value, list) and value:
        for index, item in enumerate(value):
            _corporate_rows(item, (*tokens, index), rows, depth + 1)
        return
    if isinstance(value, _CorporateNumber):
        kind, scalar = 'number', str(value)
    elif isinstance(value, str):
        kind, scalar = 'string', value
    elif type(value) is bool:
        kind, scalar = 'boolean', value
    elif value is None:
        kind, scalar = 'null', None
    elif isinstance(value, list):
        kind, scalar = 'array', '[]'
    elif isinstance(value, dict):
        kind, scalar = 'object', '{}'
    else:
        raise JsonSafetyError('Corporate decoded source scalar is unsupported')
    pointer = _corporate_pointer(tokens)
    for text in (pointer, scalar):
        if isinstance(text, str) and (len(text) > 32767 or _CIT_INVALID_XML.search(text)):
            raise _UnsupportedMetadata('unexportable_corporate_source_text')
    rows.append([pointer, kind, scalar])


def _corporate_table(name, rows):
    return {'name': name, 'headers': list(_CIT_HEADERS), 'rows': rows, 'complete': True}


def _corporate_integer(value):
    if isinstance(value, _CorporateNumber) and re.fullmatch(r'0|[1-9][0-9]*', value):
        try:
            return int(value)
        except ValueError:
            pass
    raise JsonSafetyError('Native corporate count or year is not a nonnegative JSON integer')


def _corporate_primary(payload, record, selected, scope, paths, provenance):
    fields = selected['native_fields']
    if 'TIN' in payload and (type(payload['TIN']) is not str or payload['TIN'] != scope[0]):
        raise JsonSafetyError('Outer corporate taxpayer number contradicts selected scope')
    period = fields.get('TaxPeriodCode')
    meta = record.get('meta', {})
    label = meta.get('Masa Pajak')
    literal_period = label if isinstance(label, str) and re.fullmatch(r'[0-9]{8}', label) else None
    if literal_period is not None:
        first, last = int(literal_period[:2]), int(literal_period[2:4])
        if not 1 <= first <= last <= 12:
            raise JsonSafetyError('Selected corporate literal period month bounds are invalid')
        if period is not None and period != literal_period:
            raise JsonSafetyError('Selected corporate literal period contradicts native code')
        if scope[2] == 'period' and int(literal_period[4:]) != scope[1]:
            raise JsonSafetyError('Selected corporate literal period contradicts scope year')
    expected_year = None
    if isinstance(period, str) and re.search(r'[0-9]{4}$', period):
        expected_year = int(period[-4:])
    elif literal_period is not None:
        expected_year = int(literal_period[4:])
    elif scope[2] == 'period':
        expected_year = scope[1]
    if 'PeriodYear' in payload:
        outer_year = _corporate_integer(payload['PeriodYear'])
        if expected_year is not None and outer_year != expected_year:
            raise JsonSafetyError('Outer corporate year contradicts selected native period')
    raw = payload.get('CurrentFormData')
    if not isinstance(raw, str):
        raise _UnsupportedMetadata('unsupported_current_form_encoding')
    root = _corporate_json(raw)
    if not isinstance(root, dict):
        raise _UnsupportedMetadata('missing_corporate_current_source')
    # This comparison rejects contradictions; it cannot replace absent native
    # listing fields in the eligibility checks below.
    if literal_period is not None and 'TaxPeriodCode' in root:
        if type(root['TaxPeriodCode']) is not str or root['TaxPeriodCode'] != literal_period:
            raise JsonSafetyError('Current corporate period contradicts selected literal period')
    fields = selected['native_fields']
    expected = {'ReturnSheetRecordIdentifier': selected['record_id'],
                'ReturnSheetAggregateIdentifier': selected['aggregate_id'],
                'TaxType': fields.get('TaxTypeCode'), 'TaxPeriodCode': fields.get('TaxPeriodCode')}
    missing_binding = False
    for key, value in expected.items():
        if _corporate_literal(value) and key in root:
            if type(root[key]) is not str or root[key] != value:
                raise JsonSafetyError('Current corporate form identity contradicts selected source')
        else:
            missing_binding = True
    main = root.get('MainFormData')
    if not isinstance(main, dict):
        raise _UnsupportedMetadata('missing_corporate_main_source')
    # Validate every supplied identity before treating any missing field as
    # unsupported coverage. Missing Tin must not hide a contradictory TaxYear.
    if 'Tin' in main and (type(main['Tin']) is not str or main['Tin'] != scope[0]):
        raise JsonSafetyError('Current corporate taxpayer number contradicts selected scope')
    year = None
    if 'TaxYear' in main:
        year = _corporate_integer(main['TaxYear'])
        if not 1900 <= year <= 2100:
            raise JsonSafetyError('Current corporate tax year is outside the selected source contract')
        years = set(re.findall(r'(?<![0-9])(?:19|20|21)[0-9]{2}(?![0-9])', meta.get('Masa Pajak', '')))
        if ((expected_year is not None and year != expected_year)
                or (years and years != {str(year)})):
            raise JsonSafetyError('Current corporate year contradicts native inventory period')
        if scope[2] == 'period' and year != scope[1]:
            raise JsonSafetyError('Current corporate tax year contradicts selected period scope')
        if 'PeriodYear' in payload and _corporate_integer(payload['PeriodYear']) != year:
            raise JsonSafetyError('Outer corporate year contradicts current source form')
    if 'Tin' not in main:
        raise _UnsupportedMetadata('missing_corporate_taxpayer_number')
    if year is None:
        raise _UnsupportedMetadata('missing_native_corporate_tax_year')
    if not isinstance(period, str) or not re.search(r'[0-9]{4}$', period):
        raise _UnsupportedMetadata('unsupported_native_corporate_period')
    if scope[2] == 'submission':
        submitted = meta.get('Tanggal Submit SPT', '')
        if not isinstance(submitted, str) or not re.fullmatch(r'[0-9]{2}-[0-9]{2}-' + str(scope[1]), submitted):
            raise _UnsupportedMetadata('unverified_corporate_submission_year')
    if missing_binding:
        raise _UnsupportedMetadata('missing_native_corporate_identity_binding')
    if type(root.get('IsDraft')) is not bool or type(payload.get('IsDraft')) is not bool:
        raise _UnsupportedMetadata('unsupported_corporate_draft_observation')
    provenance['draft_flags'] = {'outer': payload['IsDraft'], 'inner': root['IsDraft']}
    controls = []
    for key, value in root.items():
        if key in _CIT_CONTROLS:
            _corporate_rows(value, (key,), controls)
    provenance['controls'] = controls
    # Every leaf/empty container outside control roots needs exactly one path.
    evidence = []
    for key, value in root.items():
        if key not in _CIT_CONTROLS:
            _corporate_rows(value, (key,), evidence)
    pointers = [_corporate_pointer(path) for path, _ in paths]
    if any(not any(row[0] == pointer or row[0].startswith(pointer + '/') for pointer in pointers)
           for row in evidence):
        raise _UnsupportedMetadata('unmapped_corporate_source_subtree')
    for path, section in paths:
        value = root
        for token in path:
            if not isinstance(value, dict) or token not in value:
                raise _UnsupportedMetadata('missing_observed_corporate_source_path')
            value = value[token]
        rows = []
        _corporate_rows(value, path, rows)
        section['tables'].append(_corporate_table(_corporate_pointer(path), rows))
    return len(root), len(evidence), root


def _corporate_grid_page(state, key, offset, payload, digest):
    if not isinstance(payload, dict) or 'TotalRecords' not in payload:
        raise _UnsupportedMetadata('unsupported_corporate_grid_payload')
    total = _corporate_integer(payload['TotalRecords'])
    if set(payload) != {'TotalRecords', 'Data', 'Index'}:
        raise _UnsupportedMetadata('unbound_corporate_grid_payload_fields')
    if 'total' in state and state['total'] != total:
        raise JsonSafetyError('Corporate grid declared counts disagree')
    state['total'] = total
    data = payload.get('Data')
    if data is None and total == 0:
        data = []
    if not isinstance(data, list) or any(not isinstance(row, dict) for row in data):
        raise _UnsupportedMetadata('unsupported_corporate_grid_rows')
    if offset + len(data) > total:
        raise JsonSafetyError('Corporate page rows exceed declared total')
    if key in state['seen']:
        if state['seen'][key]['sha256'] != digest:
            raise JsonSafetyError('Repeated corporate source page changed within one attempt')
        return
    if payload.get('Index') is not None or 'Index' not in payload:
        raise _UnsupportedMetadata('unsupported_corporate_grid_index')
    rows = []
    for index, row in enumerate(data, offset):
        _corporate_rows(row, ('Payload', 'Data', index), rows)
    state['seen'][key] = {'offset': offset, 'count': len(data), 'rows': rows, 'sha256': digest}


def _corporate_catalog_fingerprint(value):
    """Lossless typed equality across admitted transports, without raw copies."""
    digest = hashlib.sha256()

    def add(item):
        if item is None:
            digest.update(b'n')
        elif type(item) is bool:
            digest.update(b't' if item else b'f')
        elif isinstance(item, str):
            raw = item.encode('utf-8', errors='surrogatepass')
            digest.update(b'#' if type(item) is _CorporateNumber else b's')
            digest.update(str(len(raw)).encode('ascii') + b':' + raw)
        elif isinstance(item, list):
            digest.update(b'[' + str(len(item)).encode('ascii') + b':')
            for child in item:
                add(child)
            digest.update(b']')
        elif isinstance(item, dict):
            digest.update(b'{' + str(len(item)).encode('ascii') + b':')
            for key in sorted(item):
                add(key)
                add(item[key])
            digest.update(b'}')
        else:
            raise JsonSafetyError('Unsupported decoded corporate catalog type')

    add(value)
    return digest.digest()


def adapt_corporate_detail(bodies, record: dict, scope, observed_forms: list) -> dict:
    """Pure, source-bound corporate evidence; coverage never grants PDF/run COMPLETE.

    Observed UI paths and exact request/offset bindings are trusted caller input,
    not inferred API aliases. Consume the capture iterator once; unsafe evidence
    anywhere aborts even after an earlier response was safely unsupported.
    """
    selected = _corporate_selected(record, scope)
    sections, paths, request_bindings, grids, responses, dependencies, primary = _corporate_bindings(observed_forms)
    coverage = {'complete': False, 'source_root_count': 0, 'evidence_row_count': 0, 'grids': []}
    provenance = {'events': [], 'controls': [], 'draft_flags': {}}
    reasons, sequences, snapshots, clocks, lifetimes, l8_lifetimes = [], set(), {}, set(), set(), set()
    query_counts, catalog_snapshots = {}, {}
    attempt, primary_hash, total_bytes = None, None, 0
    primary_source, country_packets, reference_packets, auxiliary_packets = None, {}, {}, {}
    supported_tax = record.get('meta', {}).get('Jenis Pajak') == 'PPh Badan'
    if not supported_tax:
        reasons.append('unsupported_corporate_tax_kind')
    if not selected['aggregate_id'] or not selected['taxpayer_id']:
        reasons.append('missing_native_corporate_identity_binding')
    if not observed_forms or not paths:
        reasons.append('missing_observed_corporate_forms')
    if primary is None:
        reasons.append('missing_observed_corporate_primary_binding')
    for item in bodies:
        envelope, ctx, attempt, event = _corporate_packet(item, selected, scope, attempt, sequences,
                                                        allow_corporate_reference=supported_tax)
        clocks.add(_corporate_request_key(event.get('clock_interval')))
        if len(clocks) != 1:
            raise JsonSafetyError('Corporate capture clock evidence is missing or mixed within one attempt')
        lifetimes.add(_corporate_request_key(event.get('component_lifetime')))
        if len(lifetimes) != 1:
            raise JsonSafetyError('Corporate component lifetime is missing or mixed within one attempt')
        l8_lifetimes.add(_corporate_request_key(event.get('corporate_l8_lifetime')))
        if len(l8_lifetimes) != 1:
            raise JsonSafetyError('Corporate L8 history is missing or mixed within one attempt')
        total_bytes += ctx['bytes']
        if len(sequences) > 1024 or total_bytes > 128 * 1024 * 1024:
            raise JsonSafetyError('Corporate source response budget exceeded')
        provenance['events'].append(event)
        payload = envelope.get('Payload') if isinstance(envelope, dict) else None
        success = (200 <= ctx['status'] < 300 and isinstance(envelope, dict)
                   and envelope.get('IsSuccessful') is True)
        request = ctx.get('request_json')
        key = (ctx['url'], _corporate_request_key(request))
        binding = request_bindings.get(key)
        is_primary = primary is not None and key == primary
        is_country = ctx['url'] == CORPORATE_COUNTRY_REFERENCE_URL
        reference_kinds = CORPORATE_REFERENCE_REQUESTS.get(ctx['url'])
        is_auxiliary = ctx['url'] in (CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL, *CORPORATE_L11A_GRID_URLS)
        if is_primary or binding is not None or reference_kinds is not None or is_auxiliary:
            old_hash = snapshots.get(key)
            if old_hash is not None and old_hash != ctx['sha256']:
                raise JsonSafetyError('Declared corporate source snapshot changed within one attempt')
            snapshots[key] = ctx['sha256']
        if (ctx['url'] in (CORPORATE_L3_GRID_URL, *CORPORATE_L11A_GRID_URLS) and success
                and isinstance(payload, dict) and 'TotalRecords' in payload
                and isinstance(request, dict)
                and request.get('ReturnSheetRecordId') == selected['record_id']
                and type(request.get('First')) is int and request['First'] >= 0
                and type(request.get('Rows')) is int and request['Rows'] > 0):
            # First identifies a page; every other query field identifies the
            # dataset. Contradictions are fatal even without a semantic binding.
            query = (ctx['url'], _corporate_request_key(
                {name: value for name, value in request.items() if name != 'First'}))
            count = _corporate_integer(payload['TotalRecords'])
            if query in query_counts and query_counts[query] != count:
                raise JsonSafetyError('Corporate page count snapshot changed within one query')
            query_counts[query] = count
        if reference_kinds is not None and success and isinstance(payload, list):
            for catalog in payload:
                if not isinstance(catalog, dict):
                    continue
                kind = catalog.get('ReferenceDataType')
                if type(kind) is not str or kind not in reference_kinds:
                    continue
                fingerprint = _corporate_catalog_fingerprint(catalog)
                prior = catalog_snapshots.setdefault(kind, {})
                if any(url != ctx['url'] and values != {fingerprint} for url, values in prior.items()):
                    raise JsonSafetyError('Corporate catalog snapshot changed across admitted transports')
                prior.setdefault(ctx['url'], set()).add(fingerprint)
        try:
            if isinstance(envelope, dict) and (is_primary or binding is not None):
                envelope_rows = []
                for field, value in envelope.items():
                    if field != 'Payload':
                        _corporate_rows(value, (field,), envelope_rows)
                event['envelope_fields'] = envelope_rows
            if reference_kinds is not None:
                # Even an unused naturally observed catalog keeps all generic
                # packet/clock/snapshot/privacy checks. Its presence must not
                # change old L7/evidence-leaf coverage into an unbound response.
                if isinstance(payload, list):
                    for catalog in payload:
                        if not isinstance(catalog, dict):
                            continue
                        entries = catalog.get('Details')
                        for value in [catalog, *(entries if isinstance(entries, list) else [])]:
                            if isinstance(value, dict) and 'language' in value and value['language'] != 'id-ID':
                                raise JsonSafetyError('Corporate country locale contradicts observed source')
                if len(reference_kinds) == 1:
                    event['reference_catalog'] = reference_kinds[0]
                else:
                    event['reference_catalogs'] = list(reference_kinds)
                packet = {'payload': payload, 'event': event, 'successful': success}
                reference_packets[event['sequence']] = packet
                if is_country:
                    country_packets[event['sequence']] = packet
            elif is_primary:
                if not success:
                    reasons.append('failed_corporate_primary_response')
                if not isinstance(payload, dict):
                    raise _UnsupportedMetadata('unsupported_corporate_primary_payload')
                if primary_hash is None:
                    primary_hash = ctx['sha256']
                    roots, rows, root = _corporate_primary(payload, record, selected, scope, paths, provenance)
                    primary_source = (root, payload, event)
                    coverage['source_root_count'], coverage['evidence_row_count'] = roots, rows
                    wrapper_rows = []
                    for field, value in envelope.items():
                        if field == 'Payload':
                            for name, source in payload.items():
                                if name != 'CurrentFormData':
                                    _corporate_rows(source, ('Payload', name), wrapper_rows)
                        else:
                            _corporate_rows(value, (field,), wrapper_rows)
                    provenance['prefill_fields'] = wrapper_rows
            elif binding is not None:
                state, offset = binding
                if not isinstance(envelope, dict) or 'Payload' not in envelope:
                    raise _UnsupportedMetadata('missing_declared_corporate_payload')
                if not success:
                    raise _UnsupportedMetadata('failed_declared_corporate_source_response')
                if state['kind'] == 'grids':
                    _corporate_grid_page(state, key, offset, payload, ctx['sha256'])
                else:
                    old = state['seen'].get(key)
                    if old is not None and old['sha256'] != ctx['sha256']:
                        raise JsonSafetyError('Repeated corporate bound response changed within one attempt')
                    if old is None:
                        rows = []
                        _corporate_rows(payload, ('Payload',), rows)
                        state['seen'][key] = {'sha256': ctx['sha256'], 'rows': rows}
                        if is_auxiliary:
                            # Keep decoded original values, never reconstruct
                            # business data from the rendered leaf rows.
                            auxiliary_packets[key] = {'payload': payload, 'event': event}
            elif (urlparse(ctx['url']).path.endswith('/getinfotin') and ctx['status'] == 400
                  and isinstance(envelope, dict) and envelope.get('IsSuccessful') is False and payload is None):
                event['informational_failure'] = True
            else:
                raise _UnsupportedMetadata('unbound_corporate_source_response')
        except _UnsupportedMetadata as error:
            reasons.append(str(error))
        # Do not retain collector wrapper dictionaries across iterator advances.
        del item
    if primary_hash is None:
        reasons.append('missing_corporate_primary_response')
    # Jumlah baris saja belum membuktikan cakupan; offset harus menyambung
    # dari nol sampai total tanpa celah atau tumpang tindih.
    for state in grids:
        pages = sorted(state['seen'].values(), key=lambda page: page['offset'])
        total = state.get('total')
        received = sum(page['count'] for page in pages)
        cursor, complete = 0, total is not None and len(state['seen']) == len(state['expected'])
        rows = []
        for page in pages:
            if page['offset'] < cursor and page['count']:
                raise JsonSafetyError('Corporate grid source spans overlap')
            if page['offset'] != cursor:
                complete = False
            cursor = page['offset'] + page['count']
            rows.extend(page['rows'])
        complete = bool(complete and cursor == total and received == total)
        coverage['grids'].append({'name': state['name'], 'total': total, 'received': received, 'complete': complete})
        if not complete:
            reasons.append('incomplete_corporate_grid_source')
        else:
            state['section']['tables'].append(_corporate_table(state['name'], rows))
            coverage['evidence_row_count'] += len(rows)
    for state in responses + dependencies:
        if len(state['seen']) != len(state['expected']):
            reasons.append('missing_declared_corporate_source_response')
            continue
        rows = [row for key in state['expected'] for row in state['seen'][key]['rows']]
        if state['kind'] == 'responses':
            state['section']['tables'].append(_corporate_table(state['name'], rows))
            coverage['evidence_row_count'] += len(rows)
        else:
            provenance.setdefault('dependencies', []).append({'endpoint': state['endpoint'], 'rows': rows})
    if not reasons and primary_source is not None:
        from coretax_corporate_projection import apply_projections
        try:
            root, payload, event = primary_source
            projected = apply_projections(sections, observed_forms, root=root, payload=payload,
                record=record, event=event, country_packets=country_packets,
                reference_packets=reference_packets, auxiliary_packets=auxiliary_packets)
            if projected:
                provenance['projections'] = projected
        except _UnsupportedMetadata as error:
            reasons.append(str(error))
    if reasons:
        return {'eligible': False, 'reason': ','.join(dict.fromkeys(reasons)), 'sections': [],
                'coverage': coverage, 'provenance': provenance}
    coverage['complete'] = True
    return {'eligible': True, 'reason': 'verified_corporate_source_coverage', 'sections': sections,
            'coverage': coverage, 'provenance': provenance}
