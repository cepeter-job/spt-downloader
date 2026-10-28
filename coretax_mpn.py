"""Pure Accounting payment qualification; private evidence never becomes SPT JSON.

Numeric source tokens stay distinct from JSON strings until projection. Nothing
in this module accesses a browser, fetches a catalog or changes source values.
"""
from contextlib import contextmanager, ExitStack
from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import stat
from urllib.parse import urlsplit

ORIGIN = 'https://coretax.intranet.pajak.go.id'
GUID = r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}'
MAX_BODY = 20 * 1024 * 1024
MAX_EVIDENCE = 256 * 1024 * 1024
MAX_RESPONSES = 4096
REQUEST_LANGUAGES = ('en-US', 'id-ID')
NUMBER = re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z')
SENSITIVE_KEYS = frozenset(('authorization', 'cookie', 'setcookie', 'password',
                            'accesstoken', 'refreshtoken', 'idtoken', 'clientsecret'))
ROW_KEYS = ('record_id', 'header_id', 'period_code', 'period_label', 'transaction_date',
            'posting_date', 'transaction_number', 'accounting_type', 'accounting_detail',
            'currency', 'currency_amount', 'exchange_rate', 'amount', 'reference',
            'parent_reference', 'revenue_code', 'source')


class MpnUnsupported(ValueError):
    """Missing/unproved source shape: a required MPN capture remains PARTIAL."""


class MpnSafetyError(ValueError):
    """Identity/privacy/snapshot contradiction: never convert to DOM fallback."""


class MpnNumber(str):
    """An original JSON number lexeme, deliberately distinct from ordinary str."""


def _number(token):
    if len(token) > 1024 or not NUMBER.fullmatch(token):
        raise MpnSafetyError('MPN numeric source exceeds the supported envelope')
    try:
        value = Decimal(token)
    except InvalidOperation:
        raise MpnSafetyError('MPN numeric source is invalid') from None
    if not value.is_finite():
        raise MpnSafetyError('MPN numeric source is nonfinite')
    return MpnNumber(token)


def _object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise MpnSafetyError('MPN JSON contains duplicate object keys')
        if re.sub(r'[^a-z]', '', key.lower()) in SENSITIVE_KEYS:
            raise MpnSafetyError('MPN JSON contains forbidden authentication material')
        result[key] = value
    return result


def _forbidden_constant(_):
    raise MpnSafetyError('MPN JSON contains a nonfinite number')


def decode_mpn(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BODY:
        raise MpnSafetyError('MPN response body has an invalid byte budget')
    try:
        body = json.loads(raw.decode('utf-8-sig'), object_pairs_hook=_object,
                          parse_int=_number, parse_float=_number,
                          parse_constant=_forbidden_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError) as error:
        if isinstance(error, MpnSafetyError):
            raise
        raise MpnSafetyError('MPN response is not safe original JSON') from None
    pending = [(body, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 64 or count > 500000:
            raise MpnSafetyError('MPN JSON structure exceeds the supported budget')
        if isinstance(value, dict):
            pending.extend((item, depth + 1) for item in value.values())
        elif isinstance(value, list):
            pending.extend((item, depth + 1) for item in value)
        elif isinstance(value, str) and not isinstance(value, MpnNumber):
            if (len(value) > 32767 or _credential_text(value)
                    or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', value)):
                raise MpnSafetyError('MPN JSON contains unsafe text')
    if not isinstance(body, dict):
        raise MpnUnsupported('MPN response root is unsupported')
    return body


def _credential_text(value):
    if re.search(r'\bauthorization\s*:\s*(?:Bearer|Basic)\s+\S+', value, re.I):
        return True
    match = re.fullmatch(r'\s*(Bearer|Basic)\s+(\S+)\s*', value, re.I)
    if match is None:
        return False
    scheme, token = match.groups()
    return (len(token) >= 16 if scheme.lower() == 'basic'
            else len(token) >= 24 or re.search(r'[^A-Za-z]', token) is not None)


def source_number(value):
    if type(value) is not MpnNumber:
        raise MpnUnsupported('MPN requires an original JSON numeric literal')
    return Decimal(value)


def source_integer(value):
    if type(value) is not MpnNumber or not re.fullmatch(r'0|[1-9][0-9]{0,8}', value):
        raise MpnUnsupported('MPN pagination requires a bounded unsigned JSON integer')
    return int(value)


def validate_page_total(payload, first, size, previous=None, *, mode='fixed-v1'):
    """Reconcile literal fixed totals or the original null-Index frontier.

    A frontier is only a promise of at least one more row. It is never a final
    inventory count until an original terminal page closes it.
    """
    if mode not in ('fixed-v1', 'frontier-v1'):
        raise MpnSafetyError('MPN original page total mode is unknown')
    if (not isinstance(payload, dict) or type(first) is not int or first < 0
            or type(size) is not int or size not in (10, 25, 50) or first % size
            or previous is not None and (type(previous) is not int or previous < 0)):
        raise MpnSafetyError('MPN original page position/size is invalid')
    total = source_integer(payload.get('TotalRecords'))
    rows = payload.get('Data')
    if (not isinstance(rows, list) or first > total
            or len(rows) != min(size, total - first)):
        raise MpnSafetyError('MPN original page rows do not reconcile with its total')
    if mode == 'fixed-v1':
        if previous is not None and previous != total:
            raise MpnSafetyError('MPN fixed original page total changed')
    else:
        if 'Index' not in payload or payload['Index'] is not None:
            raise MpnSafetyError('MPN continuation lacks its original null Index')
        if first == 0:
            valid = previous is None and len(rows) == size and total == size + 1
        else:
            valid = (previous == first + 1 and bool(rows)
                     and total in (first + len(rows), first + size + 1))
        if not valid:
            raise MpnSafetyError('MPN original continuation frontier changed')
    return total


def _text(data, key, *, optional=False):
    value = data.get(key)
    if optional and value is None:
        return ''
    if type(value) is not str or (not optional and not value):
        raise MpnUnsupported('MPN required literal text is missing or unsupported')
    return value


def _identity(value):
    return type(value) is str and re.fullmatch(GUID, value) is not None


def period_year(code, catalog=None):
    if type(code) is not str or not re.fullmatch(r'[0-9]{8}', code):
        raise MpnUnsupported('MPN detail tax period is unsupported')
    first, last, year = int(code[:2]), int(code[2:4]), int(code[4:])
    if not 1 <= first <= last <= 12 or not 1900 <= year <= 2100:
        raise MpnUnsupported('MPN detail tax period is ambiguous')
    # Multi-month meanings require the observed exact period caption, not a
    # header year or the payment date. The ordinary full calendar year is exact.
    if first != last:
        months = ('Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
                  'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember')
        expected = f'{months[first - 1]} - {months[last - 1]} {year}'
        if not isinstance(catalog, dict) or catalog.get(code) != expected:
            raise MpnUnsupported('MPN period range lacks an exact captured catalog label')
    return year


def project_payment(header, detail, *, year, catalog=None):
    if not isinstance(header, dict) or not isinstance(detail, dict):
        raise MpnUnsupported('MPN header/detail source is unsupported')
    parent, identifier, owner = header.get('RecordId'), detail.get('RecordId'), detail.get('HeaderRecordId')
    if not all(_identity(value) for value in (parent, identifier, owner)):
        raise MpnUnsupported('MPN header/detail identity is unavailable')
    if owner != parent or identifier == parent:
        raise MpnSafetyError('MPN detail contradicts its owned header identity')
    if header.get('IsCancelled') is not False:
        raise MpnUnsupported('MPN header cancellation state is unproved')
    # Validate every source numeric operand before exclusion. A contradictory
    # or malformed row is never hidden by its year/positive amount.
    amount = source_number(detail.get('Amount'))
    source_number(detail.get('CurrencyAmount'))
    source_number(detail.get('HeaderExchangeRate'))
    if amount >= 0:
        return None
    code = _text(detail, 'PeriodCode')
    if period_year(code, catalog) != year:
        return None
    label = catalog.get(code, code) if isinstance(catalog, dict) else code
    if type(label) is not str or not label:
        raise MpnUnsupported('MPN period label is unsupported')
    return {
        'record_id': identifier, 'header_id': parent, 'period_code': code, 'period_label': label,
        'transaction_date': _text(detail, 'TransactionDate'),
        'posting_date': _text(detail, 'PostingDate'),
        'transaction_number': _text(detail, 'TransactionNumber'),
        'accounting_type': _text(detail, 'AccountingTypeCode'),
        'accounting_detail': _text(detail, 'AccountingTypeDetailCode'),
        'currency': _text(detail, 'CurrencyCode'),
        'currency_amount': str(detail['CurrencyAmount']),
        'exchange_rate': str(detail['HeaderExchangeRate']), 'amount': str(detail['Amount']),
        'reference': _text(detail, 'ReferenceNumber', optional=True),
        'parent_reference': _text(header, 'ReferenceNumber', optional=True),
        'revenue_code': _text(detail, 'RevenueCode'), 'source': 'json',
    }


def _dom_number(value):
    if type(value) is not str or not re.fullmatch(r'-?(?:[0-9]+|[0-9]{1,3}(?:\.[0-9]{3})+)(?:,[0-9]+)?', value):
        raise MpnUnsupported('MPN DOM numeric text is unsupported')
    return Decimal(value.replace('.', '').replace(',', '.'))


def parent_numeric_binding(row, header):
    """Exact integer-only identity for the five inspected parent number cells."""
    if not isinstance(row, list) or len(row) != 24 or not isinstance(header, dict):
        return None
    columns = ((7, 'CurrencyAmount'), (8, 'CurrencyAmountLeft'), (9, 'ExchangeRate'),
               (10, 'Amount'), (11, 'AmountLeft'))
    values, unsupported = [], False
    for column, field in columns:
        try:
            value = source_number(header.get(field))
        except (MpnUnsupported, InvalidOperation):
            unsupported = True
            continue
        if (not value.is_finite() or value.copy_abs() > 999999999999999
                or value != value.to_integral_value()):
            unsupported = True
            continue
        try:
            observed = _dom_number(row[column])
        except (MpnUnsupported, InvalidOperation):
            unsupported = True
            continue
        if observed != value:
            raise MpnSafetyError('MPN parent numeric identity differs from its original source')
        values.append(value)
    return None if unsupported else tuple(values)


def dom_numbers_match(rows, details):
    if not isinstance(rows, list) or len(rows) != len(details):
        return False
    try:
        return all(isinstance(row, list) and len(row) == 9 and all(
            _dom_number(row[column]) == source_number(detail.get(field))
            for column, field in ((5, 'CurrencyAmount'), (6, 'HeaderExchangeRate'), (7, 'Amount')))
            for row, detail in zip(rows, details))
    except (MpnUnsupported, InvalidOperation):
        return False


def source_display_date(value):
    """The bounded inspected id-ID/Jakarta date projection, not a guessed date."""
    if type(value) is not str:
        return None
    try:
        if re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
            day = datetime.strptime(value, '%Y-%m-%d')
        elif re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,3})?Z', value):
            day = datetime.fromisoformat(value.replace('Z', '+00:00')).astimezone(timezone(timedelta(hours=7)))
        else:
            return None
        return day.strftime('%d-%m-%Y') if 1970 <= day.year <= 2100 else None
    except ValueError:
        return None


def captured_catalogs(body, *, include_codes=False):
    """Only unique, explicit id-ID/null-ValidTo rows need no cache clock choice."""
    expected = {'ACCOUNTING_TYPE', 'ACCOUNTING_TYPE_DETAIL',
                'REVENUE_CHART_OF_ACCOUNTS_6_DIGITS_SEGMENT', 'PERIOD'}
    payload = body.get('Payload')
    if body.get('IsSuccessful') is not True or not isinstance(payload, list):
        raise MpnUnsupported('MPN original reference envelope is unsupported')
    result, inventories = {}, {}
    for group in payload:
        if not isinstance(group, dict) or not isinstance(group.get('Details'), list):
            raise MpnUnsupported('MPN original reference group is unsupported')
        # Explicit language contradictions remain fatal before shape fallback.
        for detail in group['Details']:
            if isinstance(detail, dict) and detail.get('AppLanguageId') not in (None, 'id-ID'):
                raise MpnSafetyError('MPN reference language contradicts its original route')
        name = group.get('ReferenceDataType')
        if (name not in expected or name in result or type(group.get('Checksum')) is not str
                or not 0 < len(group['Checksum']) <= 1024):
            raise MpnUnsupported('MPN reference identity/version is unsupported')
        labels, seen, ambiguous = {}, set(), set()
        complete_codes = True
        for detail in group['Details']:
            if not isinstance(detail, dict) or type(detail.get('Code')) is not str:
                complete_codes = False
                continue
            code = detail['Code']
            if code in seen:
                ambiguous.add(code)
            seen.add(code)
            if (detail.get('AppLanguageId') != 'id-ID' or 'ValidTo' not in detail
                    or detail['ValidTo'] is not None or type(detail.get('CodeDescription')) is not str
                    or not detail['CodeDescription']):
                continue
            labels[code] = detail['CodeDescription']
        for code in ambiguous:
            labels.pop(code, None)
        result[name] = labels
        if include_codes:
            inventories[name] = frozenset(seen) if complete_codes else None
    if set(result) != expected:
        raise MpnUnsupported('MPN reference response is not the inspected exact type set')
    return (result, inventories) if include_codes else result


def _source_digest(value):
    def typed(item):
        if type(item) is MpnNumber:
            return ['number', str(item)]
        if isinstance(item, dict):
            return ['object', [[key, typed(child)] for key, child in sorted(item.items())]]
        if isinstance(item, list):
            return ['array', [typed(child) for child in item]]
        return [type(item).__name__, item]
    return hashlib.sha256(json.dumps(typed(value), ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def _mpn_directories(path):
    path = Path(path).absolute()
    if '..' in path.parts:
        raise MpnSafetyError('MPN private path contains parent traversal')
    result = {}
    for component in reversed((path, *path.parents)):
        info = component.lstat()
        if (not stat.S_ISDIR(info.st_mode) or stat.S_ISLNK(info.st_mode)
                or getattr(info, 'st_file_attributes', 0) & 1024):
            raise MpnSafetyError('MPN private directory is an alias or reparse point')
        result[str(component)] = (info.st_dev, info.st_ino)
    return result


def taxpayer_id(run):
    candidates = set()
    for source in run.get('sources', []):
        url = source.get('url') if isinstance(source, dict) else None
        if not isinstance(url, str):
            continue
        parsed = urlsplit(url)
        match = re.fullmatch(r'/returnsheets/id-ID/submitted-returnsheets/(' + GUID + ')', parsed.path)
        if parsed.scheme == 'https' and parsed.netloc == urlsplit(ORIGIN).netloc and match and not parsed.query and not parsed.fragment:
            candidates.add(match[1])
    if len(candidates) != 1:
        raise MpnSafetyError('MPN requires one verified submitted-list taxpayer source')
    return candidates.pop()


def require_mpn(run, detail_source):
    if detail_source not in ('dom', 'json', 'json-first', 'json-hybrid'):
        raise ValueError('MPN detail source is unsupported')
    identifier = taxpayer_id(run)
    scope = [run['npwp'], run['year'], run['year_basis']]
    if 'mpn' in run:
        validate_mpn(run)
        if run['mpn']['taxpayer_id'] != identifier:
            raise MpnSafetyError('MPN taxpayer declaration changed')
        return run['mpn']
    run['complete'] = False
    run['mpn'] = {'version': 1, 'required': True, 'scope': scope,
                  'taxpayer_id': identifier, 'detail_source': detail_source,
                  'status': 'PENDING', 'inventory_complete': False, 'details_complete': False,
                  'headers': 0, 'details': 0, 'rows': [], 'audit': [], 'evidence': []}
    return run['mpn']


def mpn_filename(run):
    if 'mpn' not in run:
        return None
    validate_mpn(run)
    return f"MPN_{run['year']}.xlsx"


def validate_mpn(run):
    if 'mpn' not in run:
        return
    value = run['mpn']
    if (not isinstance(value, dict) or type(value.get('version')) is not int or value['version'] != 1
            or value.get('required') is not True
            or value.get('scope') != [run['npwp'], run['year'], run['year_basis']]
            or not _identity(value.get('taxpayer_id'))
            or value.get('status') not in ('PENDING', 'PARTIAL', 'COMPLETE')
            or any(type(value.get(k)) is not bool for k in ('inventory_complete', 'details_complete'))
            or any(type(value.get(k)) is not int or value[k] < 0 for k in ('headers', 'details'))
            or not isinstance(value.get('rows'), list) or not isinstance(value.get('audit'), list)
            or not isinstance(value.get('evidence'), list)):
        raise ValueError('MPN declaration/scope is invalid')
    if (value.get('detail_source') not in ('dom', 'json', 'json-first', 'json-hybrid')
            or len(value['rows']) > 10000 or len(value['audit']) > 200000
            or any(not isinstance(entry, dict) or set(entry) != {'message'}
                   or type(entry['message']) is not str for entry in value['audit'])):
        raise ValueError('MPN mode/row/audit declaration is invalid')
    if 'attempt' in value and (type(value['attempt']) is not str or not re.fullmatch(r'[0-9a-f]{32}', value['attempt'])):
        raise MpnSafetyError('MPN private attempt declaration is invalid')
    try:
        decode_mpn(json.dumps(value, ensure_ascii=False, allow_nan=False).encode('utf-8'))
    except (TypeError, ValueError):
        raise MpnSafetyError('MPN declaration contains unsafe text or exceeds its budget') from None
    if value['status'] == 'COMPLETE' and (not value['inventory_complete'] or not value['details_complete'] or value['audit']):
        raise ValueError('MPN COMPLETE requires complete inventories without unresolved audit')
    if 'attempt' in value and value['status'] == 'COMPLETE' and not value['evidence']:
        raise MpnSafetyError('MPN COMPLETE has no owned original inventory evidence')
    if run.get('complete') and value['status'] != 'COMPLETE':
        raise ValueError('MPN capture is required before a COMPLETE job')
    coverage = value.get('coverage')
    if coverage is not None:
        if (not isinstance(coverage, dict) or set(coverage) != {'excluded', 'unresolved', 'duplicates'}
                or any(type(number) is not int or number < 0 for number in coverage.values())
                or sum(coverage.values()) + len(value['rows']) > value['details']
                or value['status'] == 'COMPLETE' and (
                    coverage['unresolved'] or sum(coverage.values()) + len(value['rows']) != value['details'])):
            raise MpnSafetyError('MPN coverage counters do not reconcile')
    seen = set()
    for row in value['rows']:
        if (not isinstance(row, dict) or set(row) != set(ROW_KEYS)
                or any(type(row[k]) is not str or len(row[k]) > 32767 for k in ROW_KEYS)
                or not _identity(row['record_id']) or not _identity(row['header_id'])
                or row['record_id'] in seen or row['source'] not in ('json', 'dom')):
            raise ValueError('MPN canonical rows are invalid or duplicated')
        seen.add(row['record_id'])
        for key in ('amount', 'currency_amount', 'exchange_rate'):
            _number(row[key])
        if Decimal(row['amount']) >= 0 or period_year(row['period_code'], {row['period_code']: row['period_label']}) != run['year']:
            raise ValueError('MPN row is outside the negative tax-period scope')
    if len(value['evidence']) > MAX_RESPONSES:
        raise ValueError('MPN evidence count exceeds its bound')
    paths, size = set(), 0
    for item in value['evidence']:
        name = item.get('path') if isinstance(item, dict) else None
        if (type(name) is not str or not re.fullmatch(r'mpn/[0-9a-f]{32}/[0-9]{6}-(?:list|detail|catalog)\.json', name)
                or name.casefold() in paths or type(item.get('bytes')) is not int or not 0 < item['bytes'] <= MAX_BODY
                or not isinstance(item.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
            raise ValueError('MPN private evidence declaration is invalid')
        if 'attempt' in value and not name.startswith('mpn/' + value['attempt'] + '/'):
            raise MpnSafetyError('MPN selected evidence mixes private attempts')
        paths.add(name.casefold())
        size += item['bytes']
    if size > MAX_EVIDENCE:
        raise ValueError('MPN private evidence byte budget exceeded')
    if 'attempt' in value or 'provenance' in value:
        validate_provenance(value['rows'], value.get('provenance'), value['evidence'])


def validate_provenance(rows, provenance, evidence):
    if (not isinstance(provenance, list) or len(provenance) != len(rows)
            or any(not isinstance(entry, dict) or set(entry) != {'record_id', 'occurrences'}
                   for entry in provenance)
            or [entry['record_id'] for entry in provenance] != [row['record_id'] for row in rows]):
        raise MpnSafetyError('MPN qualified provenance identity/count is invalid')
    hashes = {item['sha256'] for item in evidence}
    count = 0
    for entry in provenance:
        occurrences = entry['occurrences']
        if not isinstance(occurrences, list) or not occurrences:
            raise MpnSafetyError('MPN qualified provenance has no original occurrence')
        count += len(occurrences)
        if count > MAX_RESPONSES * 50:
            raise MpnSafetyError('MPN qualified provenance exceeds its budget')
        for item in occurrences:
            if (not isinstance(item, dict) or set(item) != {
                    'header_sha256', 'header_index', 'detail_sha256', 'detail_index'}
                    or any(type(item[key]) is not str or item[key] not in hashes
                           for key in ('header_sha256', 'detail_sha256'))
                    or any(type(item[key]) is not int or not 0 <= item[key] < 50
                           for key in ('header_index', 'detail_index'))):
                raise MpnSafetyError('MPN qualified provenance has an invalid original row binding')


def _reconcile_held(run, readers):
    value = run.get('mpn', {})
    if 'attempt' not in value:
        return  # Pure/legacy render fixtures declare no browser-attempt custody.
    bindings = value.get('bindings')
    if not isinstance(bindings, list):
        raise MpnSafetyError('MPN captured page bindings are unavailable')
    by_path = {item['path']: stream for item, stream in readers}
    by_item = {item['path']: item for item, _ in readers}
    catalogs, headers, header_hashes, details, detail_hashes = {}, {}, {}, {}, {}
    header_locations, occurrences = {}, {}
    list_first, list_total, detail_offsets = 0, None, {}
    list_mode, list_query, detail_modes, detail_queries = None, None, {}, {}
    request_language = None
    seen_paths = set()
    for binding in bindings:
        if not isinstance(binding, dict) or binding.get('path') not in by_path:
            raise MpnSafetyError('MPN captured page binding is invalid')
        path = binding['path']
        if path in seen_paths:
            raise MpnSafetyError('MPN original page binding is duplicated')
        seen_paths.add(path)
        stream = by_path[path]
        stream.seek(0)
        raw = stream.read(MAX_BODY + 1)
        if hashlib.sha256(raw).hexdigest() != by_item[path]['sha256']:
            raise MpnSafetyError('MPN held source bytes changed')
        body = decode_mpn(raw)
        kind = binding.get('kind')
        if kind not in ('catalog', 'list', 'detail') or not path.endswith('-' + kind + '.json'):
            raise MpnSafetyError('MPN page kind differs from its evidence namespace')
        if kind == 'catalog':
            if catalogs:
                raise MpnSafetyError('MPN selected reference source is duplicated')
            catalogs = captured_catalogs(body)
            continue
        if kind not in ('list', 'detail') or body.get('IsSuccessful') is not True:
            raise MpnSafetyError('MPN held page envelope/kind is unsupported')
        payload, request = body.get('Payload'), binding.get('request')
        if not isinstance(payload, dict) or not isinstance(request, dict):
            raise MpnSafetyError('MPN held page/request is unsupported')
        total = source_integer(payload.get('TotalRecords'))
        rows = payload.get('Data')
        identity = 'TaxpayerAggregateIdentifier' if kind == 'list' else 'RecordId'
        if (set(request) != {identity, 'First', 'Rows', 'SortField', 'SortOrder', 'LanguageId', 'Filters'}
                or type(request['First']) is not int or request['First'] < 0
                or type(request['Rows']) is not int or request['Rows'] not in (10, 25, 50)
                or request['First'] % request['Rows'] or request['First'] > total
                or type(request['LanguageId']) is not str or request['LanguageId'] not in REQUEST_LANGUAGES
                or type(request['SortOrder']) is not int or request['SortOrder'] != -1
                or request['SortField'] != ('PostingDate' if kind == 'list' else 'TransactionDate')
                or not isinstance(rows, list) or len(rows) != min(request['Rows'], max(0, total - request['First']))):
            raise MpnSafetyError('MPN held original query/count is invalid')
        if request_language is None:
            request_language = request['LanguageId']
        elif request['LanguageId'] != request_language:
            raise MpnSafetyError('MPN held original request language changed')
        mode = binding.get('total_mode', 'fixed-v1')
        query = {key: item for key, item in request.items() if key != 'First'}
        if kind == 'list':
            filters = request['Filters']
            if (request[identity] != value['taxpayer_id'] or request['First'] != list_first
                    or list_mode is not None and list_mode != mode
                    or list_query is not None and list_query != query
                    or not isinstance(filters, list) or len(filters) != 1
                    or not isinstance(filters[0], dict) or filters[0].get('PropertyName') != 'IsCancelled'
                    or filters[0].get('Value') != '0' or filters[0].get('MatchMode') != 'equals'
                    or set(filters[0]) - {'PropertyName', 'Value', 'MatchMode', 'CaseSensitive', 'AsString'}
                    or filters[0].get('CaseSensitive', True) is not True or filters[0].get('AsString', False) is not False):
                raise MpnSafetyError('MPN held parent inventory query changed')
            validate_page_total(payload, request['First'], request['Rows'], list_total, mode=mode)
            list_first += len(rows)
            list_total = total
            list_mode, list_query = mode, query
            for header_index, header in enumerate(rows):
                if (not isinstance(header, dict) or not _identity(header.get('RecordId'))
                        or header.get('TaxpayerAggregateIdentifier') != value['taxpayer_id']
                        or header.get('TaxpayerTIN') != run['npwp'] or header.get('IsCancelled') is not False):
                    raise MpnSafetyError('MPN held parent identity/scope changed')
                identifier, fingerprint = header['RecordId'], _source_digest(header)
                if identifier in header_hashes and header_hashes[identifier] != fingerprint:
                    raise MpnSafetyError('MPN held duplicate parent changed')
                header_hashes[identifier] = fingerprint
                headers.setdefault(identifier, header)
                header_locations.setdefault(identifier, (by_item[path]['sha256'], header_index))
        else:
            parent = request[identity]
            previous_first, previous_total = detail_offsets.get(parent, (0, None))
            if (parent not in headers or request['Filters'] != [] or request['First'] != previous_first
                    or parent in detail_modes and detail_modes[parent] != mode
                    or parent in detail_queries and detail_queries[parent] != query
                    or binding.get('parent_id') != parent):
                raise MpnSafetyError('MPN held detail query/parent changed')
            validate_page_total(payload, request['First'], request['Rows'], previous_total, mode=mode)
            detail_offsets[parent] = (previous_first + len(rows), total)
            detail_modes[parent], detail_queries[parent] = mode, query
            values = details.setdefault(parent, [])
            for detail_index, detail in enumerate(rows):
                if (not isinstance(detail, dict) or not _identity(detail.get('RecordId'))
                        or detail.get('HeaderRecordId') != parent):
                    raise MpnSafetyError('MPN held detail identity changed')
                identifier, fingerprint = detail['RecordId'], _source_digest(detail)
                header_sha, header_index = header_locations[parent]
                occurrences.setdefault(identifier, []).append({
                    'header_sha256': header_sha, 'header_index': header_index,
                    'detail_sha256': by_item[path]['sha256'], 'detail_index': detail_index})
                if identifier in detail_hashes:
                    if detail_hashes[identifier] != (parent, fingerprint):
                        raise MpnSafetyError('MPN held duplicate detail changed')
                    continue
                detail_hashes[identifier] = (parent, fingerprint)
                values.append(detail)
    if seen_paths != set(by_path):
        raise MpnSafetyError('MPN original evidence lacks its owned page binding')
    complete = value['status'] == 'COMPLETE'
    if complete and (list_total is None or list_first != list_total or any(
            parent not in detail_offsets or detail_offsets[parent][0] != detail_offsets[parent][1] for parent in headers)):
        raise MpnSafetyError('MPN original inventories do not prove COMPLETE')
    if complete and (value['headers'] != len(headers) or value['details'] != sum(offset[1] for offset in detail_offsets.values())):
        raise MpnSafetyError('MPN captured counters differ from its original inventories')
    originals, expected_ids = {}, []
    for parent, header in headers.items():
        if parent not in detail_offsets or detail_offsets[parent][0] != detail_offsets[parent][1]:
            continue
        for detail in details.get(parent, []):
            try:
                projected = project_payment(header, detail, year=run['year'], catalog=catalogs.get('PERIOD'))
            except MpnUnsupported:
                if complete:
                    raise MpnSafetyError('MPN COMPLETE includes an unqualified original detail') from None
                continue
            if projected is not None:
                expected_ids.append(detail['RecordId'])
                originals[detail['RecordId']] = (detail, projected)
    actual_ids = [row['record_id'] for row in value['rows']]
    if actual_ids != (expected_ids if complete else expected_ids[:len(actual_ids)]):
        raise MpnSafetyError('MPN qualified row inventory differs from original evidence')
    if complete and value.get('coverage') != {
            'excluded': len(detail_hashes) - len(expected_ids), 'unresolved': 0,
            'duplicates': sum(offset[1] for offset in detail_offsets.values()) - len(detail_hashes)}:
        raise MpnSafetyError('MPN coverage differs from its original inventories')
    for entry in value.get('provenance', []):
        expected_occurrences = occurrences[entry['record_id']]
        actual_occurrences = entry['occurrences']
        if actual_occurrences != (expected_occurrences if complete
                                  else expected_occurrences[:len(actual_occurrences)]):
            raise MpnSafetyError('MPN qualified row provenance differs from original evidence')
    for row in value['rows']:
        detail, expected = originals[row['record_id']]
        if row['source'] == 'dom':
            dates = [source_display_date(detail.get(key)) for key in ('TransactionDate', 'PostingDate')]
            if any(date is None for date in dates):
                raise MpnSafetyError('MPN DOM date lacks its bounded original projection')
            expected.update(source='dom', transaction_date=dates[0], posting_date=dates[1],
                            accounting_type=catalogs.get('ACCOUNTING_TYPE', {}).get(detail['AccountingTypeCode'], detail['AccountingTypeCode']),
                            accounting_detail=catalogs.get('ACCOUNTING_TYPE_DETAIL', {}).get(detail['AccountingTypeDetailCode'], detail['AccountingTypeDetailCode']))
        if row != expected:
            raise MpnSafetyError('MPN canonical row differs from its original numeric/text source')


@contextmanager
def mpn_custody(run, folder, check_cancel=None):
    """Hold verified private raw bytes through publication without copying them."""
    validate_mpn(run)
    if not run.get('mpn', {}).get('evidence'):
        yield []
        return
    from spt_desktop.output_windows import DirectoryGuard, locked_file
    readers = []
    root = Path(folder).absolute()
    with DirectoryGuard() as guard, ExitStack() as stack:
        guard.include(_mpn_directories(root))
        for item in run.get('mpn', {}).get('evidence', []):
            if check_cancel:
                check_cancel()
            path = root / item['path']
            parent = root
            for component in Path(item['path']).parts:
                if any(child.name.casefold() == component.casefold() and child.name != component for child in parent.iterdir()):
                    raise MpnSafetyError('MPN private evidence contains a case alias')
                parent = parent / component
            guard.include(_mpn_directories(path.parent))
            stream = stack.enter_context(locked_file(path))
            raw = stream.read(MAX_BODY + 1)
            if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise MpnSafetyError('MPN evidence bytes changed')
            decode_mpn(raw)
            stream.seek(0)
            readers.append((item, stream))
        _reconcile_held(run, readers)
        yield readers
        for item, stream in readers:
            if check_cancel:
                check_cancel()
            stream.seek(0)
            raw = stream.read(MAX_BODY + 1)
            if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise MpnSafetyError('MPN evidence changed during publication')
