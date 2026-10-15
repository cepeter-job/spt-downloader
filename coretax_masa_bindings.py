"""Explicit native Masa presentation bindings from reviewed public UI code.

These project source values; they do not establish identity or native eligibility.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP, localcontext
import re

from coretax_json import JsonSafetyError, _CorporateNumber, _UnsupportedMetadata

_MAX_EXACT_INTEGER = Decimal('9007199254740991')
_JAKARTA = timezone(timedelta(hours=7))
_ISO_DATE = re.compile(r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})?)?')


def _decimal(value):
    if type(value) not in (str, _CorporateNumber) or len(value) > 128:
        raise _UnsupportedMetadata('unsupported_masa_number_type')
    try:
        number = Decimal(value)
    except InvalidOperation:
        raise _UnsupportedMetadata('unsupported_masa_number') from None
    if not number.is_finite() or abs(number) > _MAX_EXACT_INTEGER:
        raise _UnsupportedMetadata('unverified_masa_browser_number_precision')
    return number


def _number(value, fraction, *, locale, trim=False):
    if type(fraction) is not int or not 0 <= fraction <= 6:
        raise _UnsupportedMetadata('unsupported_masa_numeric_precision')
    if locale not in ('en-US', 'id-ID'):
        raise _UnsupportedMetadata('unverified_masa_numeric_locale')
    number = _decimal(value)
    with localcontext() as context:
        context.prec = 40
        rounded = number.quantize(Decimal(1).scaleb(-fraction), rounding=ROUND_HALF_UP)
    if rounded == 0:
        rounded = abs(rounded)
    text = format(rounded, f',.{fraction}f')
    if trim and '.' in text:
        text = text.rstrip('0').rstrip('.')
    return text.translate(str.maketrans(',.', '.,')) if locale == 'id-ID' else text


def render_grid_value(value, kind, *, fraction=0, footer=False, timezone_name=None):
    """Match reviewed ui-grid behavior without conflating JSON strings/numbers."""
    if kind == 'text':
        if value is None:
            return ''
        if type(value) in (str, _CorporateNumber):
            return str(value)
        raise _UnsupportedMetadata('unsupported_masa_text_type')
    if kind == 'number':
        # Body uses numberformat_ignoreprec (null->0), footer numberformat does
        # not. Actual string values bypass the body pipe, including leading zeroes.
        if value is None:
            return '' if footer else _number('0', fraction, locale='id-ID')
        if type(value) is str and not footer:
            return value
        if footer and value == '':
            return ''
        return _number(value, fraction, locale='id-ID')
    if kind == 'date':
        if value is None:
            return ''
        if type(value) is not str:
            raise _UnsupportedMetadata('unsupported_masa_date_type')
        if '0001' in value:
            return ''
        if not _ISO_DATE.fullmatch(value):
            raise _UnsupportedMetadata('unverified_masa_date_shape')
        try:
            date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            raise _UnsupportedMetadata('invalid_masa_date') from None
        if date.tzinfo is not None:
            # No system-local timezone or Windows tzdata dependency. Only the
            # explicitly verified browser timezone is currently supported.
            if timezone_name != 'Asia/Jakarta':
                raise _UnsupportedMetadata('unverified_masa_date_timezone')
            date = date.astimezone(_JAKARTA)
        return date.strftime('%d-%m-%Y')
    raise _UnsupportedMetadata('unsupported_masa_column_kind')


_TREE_FIELDS = ('No', 'Name', 'TotalSelfPayment', 'TotalWithholding',
                'TotalIncomeTaxByGovernment', 'TotalIncomeTaxPaid',
                'TotalIncomeTaxPaidPreviousReturn', 'TotalIncomeTaxAmendment')
_TREE_TOTALS = ('TotalSelfPayment', 'TotalWithholding', 'TotalIncomeTaxByGoverment',
                'TotalIncomeTaxPaid', 'TotalIncomeTaxPaidPreviousReturn')


def _tree_number(value, locale):
    # ui-tree-table uses Angular DecimalPipe with its default 0..3 fractional
    # digits, not ui-grid's fixed precision and null-to-zero body formatter.
    return '' if value is None or value == '' else _number(value, 3, locale=locale, trim=True)


def _evidence(value, path):
    if type(value) is _CorporateNumber:
        return {'path': path, 'type': 'number', 'value': str(value)}
    if value is None or type(value) is str:
        return {'path': path, 'type': 'null' if value is None else 'string', 'value': value}
    raise _UnsupportedMetadata('unsupported_masa_projected_scalar')


def project_unifikasi_tree(form, headers, *, locale):
    """Project the reviewed Induk tree; the caller must bind build and locale."""
    if locale not in ('en-US', 'id-ID'):
        raise _UnsupportedMetadata('unverified_masa_tree_locale')
    if (not isinstance(form, dict) or not isinstance(form.get('IncomeTaxes'), list)
            or not isinstance(headers, list) or len(headers) != 8
            or any(type(header) is not str or not header for header in headers)):
        raise _UnsupportedMetadata('unsupported_unifikasi_tree_binding')
    rows, provenance = [], []

    def walk(nodes, path, depth):
        if depth > 32:
            raise _UnsupportedMetadata('unifikasi_tree_depth_exceeded')
        for index, node in enumerate(nodes):
            if not isinstance(node, dict) or not isinstance(node.get('data'), dict):
                raise _UnsupportedMetadata('unsupported_unifikasi_tree_node')
            data = node['data']
            values = []
            for column, key in enumerate(_TREE_FIELDS):
                value = data.get(key)
                if key in data:
                    provenance.append(_evidence(value, path + [index, 'data', key]))
                if column < 2:
                    rendered = render_grid_value(value, 'text')
                    if key == 'Name' and depth == 0:
                        rendered = rendered.replace('Article', 'Pasal', 1).replace('Section', 'Ayat', 1)
                else:
                    rendered = _tree_number(value, locale)
                values.append(rendered)
            rows.append(values)
            if len(rows) > 10000:
                raise _UnsupportedMetadata('unifikasi_tree_row_budget_exceeded')
            children = node.get('children')
            if children is not None:
                if not isinstance(children, list):
                    raise _UnsupportedMetadata('unsupported_unifikasi_tree_children')
                if children and node.get('expanded') is not True:
                    raise _UnsupportedMetadata('unverified_unifikasi_collapsed_tree')
                walk(children, path + [index, 'children'], depth + 1)

    walk(form['IncomeTaxes'], ['IncomeTaxes'], 0)
    footer = ['TOTAL OF INCOME TAX']
    for key in _TREE_TOTALS:
        value = form.get(key)
        if key in form:
            provenance.append(_evidence(value, [key]))
        footer.append(_tree_number(value, locale))
    # Native footer's last cell has no value binding; do not infer one from the
    # similarly named amendment total elsewhere in FormData.
    footer.append('')
    return {'table': {'headers': list(headers), 'rows': rows, 'body_row_count': len(rows),
                      'source_total': len(rows), 'footer': [footer],
                      'footer_spans': [[2, 1, 1, 1, 1, 1, 1]], 'complete': True},
            'provenance': provenance}


# Explicit control->source bindings, not name-derived aliases. Boolean marks the
# reviewed nullish-zero operator; unlisted controls are not supported yet.
_PPN_AMOUNTS = {
    'ExportOfTangibleGoods': (('A1FormListOfExportTaxableGoodsOrServices', 'Total'), False),
    'CarryForwardOfInputTax': (('CarryForwardOfInputTax', 'VAT'), False),
    'VATNeedRepayVAT': (('VATNeedToRepay', 'VAT'), False),
    'DomesticDeliveriesUsingOtherValueTaxBaseSTLG': (
        ('DomesticDeliveriesUsingOtherValue', 'SalesTaxLuxuryGoods'), True),
    'ImportOfTaxableGoodsFromOusideCustomsAreaImportValue': (
        ('ImportOfTaxableGoods', 'SellingPrice'), True),
}
_NORMAL_NULL_CONTROLS = frozenset({
    'STLGUnderOverOnPreviousVATReturn', 'STLGUnderOverpaidDueAmmendment',
    'VATIsUnderOrOverpaidAmandment',
})
_STLG_SUM_PATHS = (
    ('DomesticDeliveriesUsingOtherValue', 'SalesTaxLuxuryGoods'),
    ('DomesticDeliveriesToTourist', 'SalesTaxLuxuryGoods'),
    ('DomesticDeliveriesOtherThanOtherValue', 'SalesTaxLuxuryGoods'),
    ('DomesticDeliveriesSelfCollected', 'SalesTaxLuxuryGoods'),
)


def _ppn_source_number(form, path, evidence):
    value = form
    for key in path:
        if value is None:
            break
        if not isinstance(value, dict):
            raise _UnsupportedMetadata('unsupported_ppn_amount_path_shape')
        if key not in value:
            # This is missing-path evidence, not a fabricated JSON null.
            evidence.append({'path': list(path), 'type': 'missing', 'value': None})
            return None
        value = value[key]
    if value is not None and type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_ppn_amount_source_type')
    evidence.append(_evidence(value, list(path)))
    if value is not None:
        _decimal(value)
    return value


def project_ppn_amount(form, control, *, model):
    """Apply reviewed final-value precedence, retaining only real dependencies."""
    if not isinstance(form, dict) or model != 'NORMAL':
        raise _UnsupportedMetadata('unsupported_ppn_amount_model_or_source')
    if control in _NORMAL_NULL_CONTROLS:
        return {'value': '', 'rule': 'normal_model_null', 'provenance': []}
    evidence = []
    if control in ('STLGSelfCollected', 'STLGUnderOverpaid'):
        total = Decimal(0)
        for path in _STLG_SUM_PATHS:
            value = _ppn_source_number(form, path, evidence)
            total += _decimal(value) if value is not None else Decimal(0)
        total = total.to_integral_value(rounding=ROUND_FLOOR)
        rule = 'floor_sum_submitted_stlg'
        if control == 'STLGUnderOverpaid':
            value = _ppn_source_number(form, ('STLGCollectedByVATCollector', 'SalesTaxLuxuryGoods'), evidence)
            total = (total - (_decimal(value) if value is not None else Decimal(0))).to_integral_value(rounding=ROUND_FLOOR)
            rule = 'floor_difference_submitted_stlg'
        return {'value': _number(str(total), 0, locale='id-ID'), 'rule': rule, 'provenance': evidence}
    binding = _PPN_AMOUNTS.get(control)
    if binding is None:
        raise _UnsupportedMetadata('unverified_ppn_amount_control')
    path, nullish_zero = binding
    value = _ppn_source_number(form, path, evidence)
    rendered = ('0' if nullish_zero else '') if value is None else _number(value, 0, locale='id-ID')
    return {'value': rendered, 'rule': 'nullish_zero' if nullish_zero else 'direct_final_path',
            'provenance': evidence}


_PPN_DOMESTIC_COLUMNS = (
    ('Name', 'text'), ('TIN', 'text'), ('DocumentNumber', 'text'), ('DocumentDate', 'date'),
    ('TaxBase', 'number'), ('OtherTaxBase', 'number'), ('VAT', 'number'),
    ('STLG', 'number'), ('TaxInvoiceCode', 'text'),
)
_PPN_GRID_COLUMNS = {
    'A-1': (('Name', 'text'), ('DocumentNumber', 'text'), ('DocumentDate', 'date'),
            ('TaxBase', 'number'), ('Information', 'text')),
    'A-2': _PPN_DOMESTIC_COLUMNS,
    'B-1': (('Name', 'text'), ('TIN', 'text'), ('DocumentNumber', 'text'),
            ('DocumentDate', 'date'), ('TaxBase', 'number'), ('VAT', 'number'),
            ('STLG', 'number'), ('Information', 'text')),
    'B-2': _PPN_DOMESTIC_COLUMNS,
    'B-3': _PPN_DOMESTIC_COLUMNS,
}


def project_ppn_grid(form_name, pages, headers, *, record_id, timezone_name):
    """Project validated PPN page bodies without deduplication or missing cells.

    Endpoint/build/header-label binding is the observer/adapter's responsibility;
    this function additionally enforces selected-record identity and page coverage.
    """
    columns = _PPN_GRID_COLUMNS.get(form_name)
    if (columns is None or not isinstance(headers, list) or len(headers) != len(columns) + 1
            or any(type(h) is not str or not h for h in headers)
            or not isinstance(pages, list) or not pages):
        raise _UnsupportedMetadata('unverified_ppn_grid_binding')
    if type(record_id) is not str or not record_id or record_id != record_id.strip():
        raise JsonSafetyError('PPN grid selected identity is invalid')
    # Check every available request identity before incomplete page metadata can
    # result in fallback. Full byte/frame/attempt custody lives in the adapter.
    for page in pages:
        if not isinstance(page, dict) or not isinstance(page.get('request'), dict):
            raise _UnsupportedMetadata('missing_ppn_grid_request')
        request = page['request']
        if 'ReturnSheetRecordId' in request and (
                type(request['ReturnSheetRecordId']) is not str or request['ReturnSheetRecordId'] != record_id):
            raise JsonSafetyError('PPN grid request belongs to a different selected return')
    rows, provenance, sequences = [], [], set()
    total = None
    for page in pages:
        request, payload = page['request'], page.get('payload')
        if 'ReturnSheetRecordId' not in request:
            raise _UnsupportedMetadata('missing_ppn_grid_record_binding')
        first, size = request.get('First'), request.get('Rows')
        if type(first) is not int or first < 0 or type(size) is not int or not 0 < size <= 1000:
            raise JsonSafetyError('PPN grid request page bounds are invalid')
        if first != len(rows):
            raise JsonSafetyError('PPN grid pages overlap or contain a gap')
        if not isinstance(payload, dict) or not isinstance(payload.get('Data'), list):
            raise _UnsupportedMetadata('unsupported_ppn_grid_payload')
        declared = payload.get('TotalRecords')
        if type(declared) is not _CorporateNumber or not re.fullmatch(r'[0-9]+', declared):
            raise _UnsupportedMetadata('missing_ppn_grid_total')
        declared = int(declared)
        if declared > 100000:
            raise _UnsupportedMetadata('ppn_grid_row_budget_exceeded')
        if total is not None and declared != total:
            raise JsonSafetyError('PPN grid total changed between pages')
        total = declared
        data = payload['Data']
        if len(data) > size or first + len(data) > total:
            raise JsonSafetyError('PPN grid page body contradicts declared bounds')
        sequence = page.get('sequence')
        if type(sequence) is not int or sequence <= 0 or sequence in sequences:
            raise JsonSafetyError('PPN grid source sequence is invalid or duplicated')
        sequences.add(sequence)
        for index, source in enumerate(data):
            if not isinstance(source, dict):
                raise _UnsupportedMetadata('unsupported_ppn_grid_row')
            # The native component uses Data.indexOf(row)+1 on each page.
            rendered = [str(index + 1)]
            for key, kind in columns:
                if key not in source:
                    raise _UnsupportedMetadata('missing_ppn_grid_source_column')
                value = source[key]
                provenance.append({**_evidence(value, ['Data', index, key]), 'sequence': sequence})
                if (form_name == 'A-2' and key == 'TIN' and value == '0000000000000000'
                        and source.get('DocumentNumberByBuyerInfor') is not None):
                    value = source['DocumentNumberByBuyerInfor']
                    provenance.append({**_evidence(value, ['Data', index, 'DocumentNumberByBuyerInfor']),
                                       'sequence': sequence})
                rendered.append(render_grid_value(value, kind, timezone_name=timezone_name))
            rows.append(rendered)
    if len(rows) != total:
        raise _UnsupportedMetadata('incomplete_ppn_grid_pages')
    return {'table': {'headers': list(headers), 'rows': rows, 'body_row_count': len(rows),
                      'source_total': total, 'complete': True}, 'provenance': provenance}
