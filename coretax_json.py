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


class _UnsupportedMetadata(ValueError):
    pass


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
        return {'eligible': False, 'reason': str(exc), 'total': total, 'rows': []}
    return {'eligible': True, 'reason': 'verified_submitted_metadata', 'total': total, 'rows': rendered}
