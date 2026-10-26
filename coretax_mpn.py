"""Pure Accounting payment qualification; private evidence never becomes SPT JSON.

Numeric source tokens stay distinct from JSON strings until projection. Nothing
in this module accesses a browser, fetches a catalog or changes source values.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

ORIGIN = 'https://coretax.intranet.pajak.go.id'
GUID = r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}'
MAX_BODY = 20 * 1024 * 1024
MAX_EVIDENCE = 256 * 1024 * 1024
MAX_RESPONSES = 20000
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
            if (len(value) > 32767 or re.search(r'(?:^|\s)(?:Bearer|Basic)\s+\S+', value, re.I)
                    or re.search(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]', value)):
                raise MpnSafetyError('MPN JSON contains unsafe text')
    if not isinstance(body, dict):
        raise MpnUnsupported('MPN response root is unsupported')
    return body


def source_number(value):
    if type(value) is not MpnNumber:
        raise MpnUnsupported('MPN requires an original JSON numeric literal')
    return Decimal(value)


def source_integer(value):
    if type(value) is not MpnNumber or not re.fullmatch(r'0|[1-9][0-9]{0,8}', value):
        raise MpnUnsupported('MPN pagination requires a bounded unsigned JSON integer')
    return int(value)


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
    if value['status'] == 'COMPLETE' and (not value['inventory_complete'] or not value['details_complete'] or value['audit']):
        raise ValueError('MPN COMPLETE requires complete inventories without unresolved audit')
    if run.get('complete') and value['status'] != 'COMPLETE':
        raise ValueError('MPN capture is required before a COMPLETE job')
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
        if (type(name) is not str or not re.fullmatch(r'mpn/[0-9a-f]{32}/[0-9]{6}-(?:list|detail)\.json', name)
                or name.casefold() in paths or type(item.get('bytes')) is not int or not 0 < item['bytes'] <= MAX_BODY
                or not isinstance(item.get('sha256'), str) or not re.fullmatch(r'[0-9a-f]{64}', item['sha256'])):
            raise ValueError('MPN private evidence declaration is invalid')
        paths.add(name.casefold())
        size += item['bytes']
    if size > MAX_EVIDENCE:
        raise ValueError('MPN private evidence byte budget exceeded')


@contextmanager
def mpn_custody(run, folder):
    """Hold verified private raw bytes through publication without copying them."""
    validate_mpn(run)
    readers = []
    with ExitStack() as stack:
        for item in run.get('mpn', {}).get('evidence', []):
            root = Path(folder).absolute()
            path = root / item['path']
            for component in (root, *[root.joinpath(*Path(item['path']).parts[:i])
                                      for i in range(1, len(Path(item['path']).parts) + 1)]):
                if component.is_symlink() or (component.exists() and getattr(component.lstat(), 'st_file_attributes', 0) & 1024):
                    raise MpnSafetyError('MPN evidence path is an alias or reparse point')
            stream = stack.enter_context(path.open('rb'))
            raw = stream.read(MAX_BODY + 1)
            if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise MpnSafetyError('MPN evidence bytes changed')
            decode_mpn(raw)
            stream.seek(0)
            readers.append((item, stream))
        yield readers
        for item, stream in readers:
            stream.seek(0)
            raw = stream.read(MAX_BODY + 1)
            if len(raw) != item['bytes'] or hashlib.sha256(raw).hexdigest() != item['sha256']:
                raise MpnSafetyError('MPN evidence changed during publication')
