"""Explicit native Masa presentation bindings from reviewed public UI code.

These project source values; they do not establish identity or native eligibility.
"""
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_FLOOR, ROUND_HALF_UP, localcontext
import re

from coretax_json import (ORIGIN, JsonSafetyError, _CorporateNumber, _UnsupportedMetadata,
                          _corporate_request_key, _capture_clock_interval)

MAIN_SOURCE = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
TAX_SOURCES = {
    'PPN': ORIGIN + '/returnsheets/id-ID/640.36c042afd2381189.js',
    'PPh Unifikasi': ORIGIN + '/returnsheets/id-ID/693.4de61c6eb2000c7e.js',
}
BUILD_DIGESTS = {
    MAIN_SOURCE: '696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd',
    TAX_SOURCES['PPN']: '4a7e33826b6d0395afb23372fb6b4a9d4be6abaab0ec25fa743c897d0e654aef',
    TAX_SOURCES['PPh Unifikasi']: '2694fdda5c23b7d5f0eefe0cf0a0c55caa0fe29acc590363f34684ed90188fe0',
}
# Component names come from the reviewed public build, not field-name guessing.
FORMS = {
    'PPN': {
        'INDUK': (None, ()),
        'A-1': ('rshshr-nvat-la1-form', (('rshshr-nvat-la1-grid', 'la1'),)),
        'A-2': ('rshshr-nvat-la2-form', (('rshshr-nvat-la2-grid', 'la2'),)),
        'B-1': ('rshshr-nvat-lb1-form', (('rshshr-nvat-lb1-grid', 'lb1'),)),
        'B-2': ('rshshr-nvat-lb2-form', (('rshshr-nvat-lb2-grid', 'lb2'),)),
        'B-3': ('rshshr-nvat-lb3-form', (('rshshr-nvat-lb3-grid', 'lb3'),)),
        'C': ('rshshr-nvat-lc-form', (('rshshr-nvat-lc-grid', 'lc'),)),
    },
    'PPh Unifikasi': {
        'INDUK': ('rshshr-spt-unifikasi', ()),
        'DAFTAR-I': ('rshshr-list-i', (('rshshr-list-i-grid-a', 'list-i-bpu'),
                                    ('rshshr-list-i-grid-b', 'list-i-bpnr'))),
        'DAFTAR-II': ('rshshr-list-ii', (('rshshr-list-ii-grid-a', 'list-ii-sp'),
                                      ('rshshr-list-ii-grid-b', 'list-ii-cy'))),
        'LAMPIRAN-I': ('rshshr-attachment-i', (('rshshr-attachment-i-grid', 'attachment-i'),)),
    },
}

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
        # Decimal accepts underscores which the UI's number pipe rejects.
        if footer and type(value) is str and not _FOOTER_DECIMAL_STRING.fullmatch(value.strip()):
            raise _UnsupportedMetadata('unsupported_masa_footer_numeric_string')
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
    'SumDeliveryOfTaxableGoodsSellingPrice': (('DeliveryOfTaxableGoodsSubjectToVAT', 'SellingPrice'), False),
    'SumDeliveryOfTaxableGoodsVAT': (('DeliveryOfTaxableGoodsSubjectToVAT', 'VAT'), False),
    'SumDeliveryOfTaxableGoodsSTLG': (('DeliveryOfTaxableGoodsSubjectToVAT', 'SalesTaxLuxuryGoods'), False),
    'TotalDeliveryGoodsAndServices': (('TotalDeliveryOfGoodsAndServices', 'SellingPrice'), True),
    'AmountCalculatedInputTaxSellingPrice': (('AmountOfInputTaxCalculated', 'SellingPrice'), False),
    'AmountCalculatedInputTaxVAT': (('AmountOfInputTaxCalculated', 'VAT'), False),
    'TotalAcquisition': (('TotalAcquisition', 'SellingPrice'), False),
    'SelfCollectedOutputTax': (('OutputTaxMustBeSelfCollected', 'VAT'), False),
    'CalculatedInputTax': (('InputTaxCanBeCalculated', 'VAT'), False),
    'STLGUnderOverOnPreviousVATReturn': (('STLGUnderOrOverPaidOnPrevious', 'SalesTaxLuxuryGoods'), False),
    'VATIsUnderOrOverpaidAmandment': (('VATUnderOrOverPaidDueToAmendment', 'VAT'), False),
    'CarryForwardOfInputTax': (('CarryForwardOfInputTax', 'VAT'), False),
    'VATNeedRepayVAT': (('VATNeedToRepay', 'VAT'), False),
    'DomesticDeliveriesUsingOtherValueTaxBaseSTLG': (
        ('DomesticDeliveriesUsingOtherValue', 'SalesTaxLuxuryGoods'), True),
    'ImportOfTaxableGoodsFromOusideCustomsAreaImportValue': (
        ('ImportOfTaxableGoods', 'SellingPrice'), True),
    'DomesticDeliveriesUsingOtherValueTaxBaseSellingPrice': (('DomesticDeliveriesUsingOtherValue', 'SellingPrice'), True),
    'DomesticDeliveriesUsingOtherValueTaxBaseOtherTaxBase': (('DomesticDeliveriesUsingOtherValue', 'OtherTaxBase'), True),
    'DomesticDeliveriesUsingOtherValueTaxBaseVAT': (('DomesticDeliveriesUsingOtherValue', 'VAT'), True),
    'DomesticDeliveriesUsingTouristSellingPrice': (('DomesticDeliveriesToTourist', 'SellingPrice'), True),
    'DomesticDeliveriesUsingTouristOtherTaxBase': (('DomesticDeliveriesToTourist', 'OtherTaxBase'), True),
    'DomesticDeliveriesUsingTouristVAT': (('DomesticDeliveriesToTourist', 'VAT'), True),
    'DomesticDeliveriesUsingTouristSTLG': (('DomesticDeliveriesToTourist', 'SalesTaxLuxuryGoods'), True),
    'DomesticDeliveriesOtherThanWithOtherValueTaxBaseSellingPrice': (('DomesticDeliveriesOtherThanOtherValue', 'SellingPrice'), True),
    'DomesticDeliveriesOtherThanWithOtherValueTaxBaseVAT': (('DomesticDeliveriesOtherThanOtherValue', 'VAT'), True),
    'DomesticDeliveriesOtherThanWithOtherValueTaxBaseSTLG': (('DomesticDeliveriesOtherThanOtherValue', 'SalesTaxLuxuryGoods'), True),
    # Attachment IA6/IA9/IB overrides are draft-only; submitted values stay here.
    'DomesticDeliveriesMustBeSelfCollectedSellingPrice': (('DomesticDeliveriesSelfCollected', 'SellingPrice'), True),
    'DomesticDeliveriesMustBeSelfCollectedOtherTaxBase': (('DomesticDeliveriesSelfCollected', 'OtherTaxBase'), True),
    'DomesticDeliveriesMustBeSelfCollectedVAT': (('DomesticDeliveriesSelfCollected', 'VAT'), True),
    'DomesticDeliveriesMustBeSelfCollectedSTLG': (('DomesticDeliveriesSelfCollected', 'SalesTaxLuxuryGoods'), True),
    'DomesticDeliveriesCollectedByVATCollectorSellingPrice': (('DomesticDeliveriesCollectedByVATCollector', 'SellingPrice'), True),
    'DomesticDeliveriesCollectedByVATCollectorOtherTaxBase': (('DomesticDeliveriesCollectedByVATCollector', 'OtherTaxBase'), True),
    'DomesticDeliveriesCollectedByVATCollectorVAT': (('DomesticDeliveriesCollectedByVATCollector', 'VAT'), True),
    'DomesticDeliveriesCollectedByVATCollectorSTLG': (('DomesticDeliveriesCollectedByVATCollector', 'SalesTaxLuxuryGoods'), True),
    'DomesticDeliveriesUncollectedVATFacilitiesSellingPrice': (('DomesticDeliveriesUncollectedVAT', 'SellingPrice'), True),
    'DomesticDeliveriesUncollectedVATFacilitiesOtherTaxBase': (('DomesticDeliveriesUncollectedVAT', 'OtherTaxBase'), True),
    'DomesticDeliveriesUncollectedVATFacilitiesVAT': (('DomesticDeliveriesUncollectedVAT', 'VAT'), True),
    'DomesticDeliveriesUncollectedVATFacilitiesSTLG': (('DomesticDeliveriesUncollectedVAT', 'SalesTaxLuxuryGoods'), True),
    'DomesticDeliveriesExemptedVATFacilitiesSellingPrice': (('DomesticDeliveriesExemptedVAT', 'SellingPrice'), True),
    'DomesticDeliveriesExemptedVATFacilitiesOtherTaxBase': (('DomesticDeliveriesExemptedVAT', 'OtherTaxBase'), True),
    'DomesticDeliveriesExemptedVATFacilitiesVAT': (('DomesticDeliveriesExemptedVAT', 'VAT'), True),
    'DomesticDeliveriesExemptedVATFacilitiesSTLG': (('DomesticDeliveriesExemptedVAT', 'SalesTaxLuxuryGoods'), True),
    'DomesticDeliveriesVATFacilitiesSellingPrice': (('DomesticDeliveriesVAT', 'SellingPrice'), True),
    'DomesticDeliveriesVATFacilitiesOtherTaxBase': (('DomesticDeliveriesVAT', 'OtherTaxBase'), True),
    'DomesticDeliveriesVATFacilitiesVAT': (('DomesticDeliveriesVAT', 'VAT'), True),
    'DomesticDeliveriesVATFacilitiesSTLG': (('DomesticDeliveriesVAT', 'SalesTaxLuxuryGoods'), True),
    'DeliveryOfGoodsNoVATPayable': (('DeliveriesOfGoodsNoVAT', 'SellingPrice'), True),
    'ImportOfTaxableGoodsFromOusideCustomsAreaVAT': (('ImportOfTaxableGoods', 'VAT'), True),
    'ImportOfTaxableGoodsFromOusideCustomsAreaSTLG': (('ImportOfTaxableGoods', 'SalesTaxLuxuryGoods'), True),
    'DomesticTaxableCreditedUsingOtherValueTaxBaseSellingPrice': (('DomesticTaxableGoodsUsingOtherValueTaxBase', 'SellingPrice'), True),
    'DomesticTaxableCreditedUsingOtherValueTaxBaseOtherTaxBase': (('DomesticTaxableGoodsUsingOtherValueTaxBase', 'OtherTaxBase'), True),
    'DomesticTaxableCreditedUsingOtherValueTaxBaseVAT': (('DomesticTaxableGoodsUsingOtherValueTaxBase', 'VAT'), True),
    'DomesticTaxableCreditedUsingOtherValueTaxBaseSTLG': (('DomesticTaxableGoodsUsingOtherValueTaxBase', 'SalesTaxLuxuryGoods'), True),
    'DomesticTaxableWhichTaxInputcanBeCreditedWithSellingPrice': (('DomesticTaxableGoodsWithInvoiceCode01', 'SellingPrice'), True),
    'DomesticTaxableWhichTaxInputcanBeCreditedWithVAT': (('DomesticTaxableGoodsWithInvoiceCode01', 'VAT'), True),
    'DomesticTaxableWhichTaxInputcanBeCreditedWithSTLG': (('DomesticTaxableGoodsWithInvoiceCode01', 'SalesTaxLuxuryGoods'), True),
    'DomesticTaxableFromWhichTaxInputcanBeCreditedWithSellingPrice': (('DomesticTaxableGoodsWithInvoiceCode02', 'SellingPrice'), True),
    'DomesticTaxableFromWhichTaxInputcanBeCreditedWithOtherTaxBase': (('DomesticTaxableGoodsWithInvoiceCode02', 'OtherTaxBase'), True),
    'DomesticTaxableFromWhichTaxInputcanBeCreditedWithVAT': (('DomesticTaxableGoodsWithInvoiceCode02', 'VAT'), True),
    'DomesticTaxableFromWhichTaxInputcanBeCreditedWithSTLG': (('DomesticTaxableGoodsWithInvoiceCode02', 'SalesTaxLuxuryGoods'), True),
    'ResultRecalculationCreditedTaxInput': (('ResultsOfTheRecalculation', 'VAT'), False),
    'ImportOrAcquisitionsWithFacilitiesSellingPrice': (('ImportsOfUncreditedInput', 'SellingPrice'), True),
    'ImportOrAcquisitionsWithFacilitiesOtherTaxBase': (('ImportsOfUncreditedInput', 'OtherTaxBase'), True),
    'ImportOrAcquisitionsWithFacilitiesVAT': (('ImportsOfUncreditedInput', 'VAT'), True),
    'ImportOrAcquisitionsWithFacilitiesSTLG': (('ImportsOfUncreditedInput', 'SalesTaxLuxuryGoods'), True),
    'ImportOrAcquisitionsThatNotVATPayable': (('ImportsOfOtherTaxableGoods', 'SellingPrice'), True),
    'DepositedVATSAmePeriod': (('VATIsDepositedInAdvance', 'VAT'), False),
    'OverPaidVATCollectedByVATCollector': (('VATCollectedByVATCollector', 'VAT'), True),
    'VATIsUnderOrOverpaidOnPrevious': (('VATUnderOrOverPaidOnPrevious', 'VAT'), False),
    'VATPayableSellingPrice': (('VATPayable', 'SellingPrice'), True),
    'VATPayableVAT': (('VATPayable', 'VAT'), False),
    'STLGCollectedByVATCollectorOverpaid': (('STLGCollectedByVATCollector', 'SalesTaxLuxuryGoods'), True),
    'TotalVATandSTLGCollectedSellingPrice': (('TotalVATAndSTLGCollected', 'SellingPrice'), False),
    'TotalVATandSTLGCollectedOtherTaxBase': (('TotalVATAndSTLGCollected', 'OtherTaxBase'), False),
    'TotalVATandSTLGCollectedVAT': (('TotalVATAndSTLGCollected', 'VAT'), False),
    'TotalVATandSTLGCollectedSTLG': (('TotalVATAndSTLGCollected', 'SalesTaxLuxuryGoods'), False),
    # OtherParties totals are deliberately absent: the LC callback replaces them.
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


def _source_scalar(form, path, evidence):
    value = form
    for index, key in enumerate(path):
        if value is None:
            evidence.append({**_evidence(None, list(path[:index])), 'requested_path': list(path)})
            return None
        if not isinstance(value, dict):
            raise _UnsupportedMetadata('unsupported_ppn_amount_path_shape')
        if key not in value:
            # This is missing-path evidence, not a fabricated JSON null.
            evidence.append({'path': list(path), 'type': 'missing', 'value': None})
            return None
        value = value[key]
    evidence.append(_evidence(value, list(path)))
    return value


def _ppn_source_number(form, path, evidence):
    value = _source_scalar(form, path, evidence)
    if value is not None and type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_ppn_amount_source_type')
    if value is not None:
        _decimal(value)
    return value


_PPN_INTEGER_BOUND = Decimal('999999999999999')


def _checked_ppn_number(number, *, integral=False):
    # Binary-exact fractions retain the pre-existing final-floor subset. Every
    # intermediate operation must also be exact; ordinary decimal coercion or
    # underflow cannot authorize a different browser Math.floor result.
    if (abs(number) > _PPN_INTEGER_BOUND or len(number.as_tuple().digits) > 15
            or integral and number != number.to_integral_value()
            or Decimal.from_float(float(number)) != number):
        raise _UnsupportedMetadata('unverified_ppn_exact_arithmetic')
    return number


def _observed_ppn_number(form, path, evidence, *, nullish=False, integral=True):
    value = _ppn_source_number(form, path, evidence)
    if evidence[-1]['type'] == 'missing' or value is None and not nullish:
        raise _UnsupportedMetadata('missing_ppn_choice_or_balance_dependency')
    return _checked_ppn_number(Decimal(0) if value is None else _decimal(value), integral=integral)


def _ppn_facility_clears(form, evidence):
    period = _source_scalar(form, ('TaxPeriod',), evidence)
    if (type(period) is not str or not re.fullmatch(r'(0[1-9]|1[0-2]){2}[1-9][0-9]{3}', period)
            or period[:2] != period[2:4]):
        raise _UnsupportedMetadata('unverified_ppn_facility_period')
    end = _observed_ppn_number(form, ('BookkeepingPeriodEnd',), evidence)
    if not 1 <= end <= 12 or 'FacilityRegisters' not in form:
        raise _UnsupportedMetadata('unverified_ppn_facility_source')
    facilities = form['FacilityRegisters']
    if facilities is None:
        evidence.append(_evidence(None, ['FacilityRegisters']))
        facilities = []
    elif isinstance(facilities, list) and len(facilities) <= 10000 and all(type(v) is str for v in facilities):
        evidence.extend(_evidence(v, ['FacilityRegisters', i]) for i, v in enumerate(facilities))
        if not facilities:
            evidence.append({'path': ['FacilityRegisters'], 'type': 'array', 'value': '[]'})
    else:
        raise _UnsupportedMetadata('unverified_ppn_facility_source')
    if any(code in facilities for code in ('AS.09-01', 'AS.09-02')):
        return False
    same_month = int(period[2:4]) == end
    delivery = False
    if not same_month:
        for root in ('ExportTangibleTaxableGoods', 'DomesticDeliveriesCollectedByVATCollector',
                     'DomesticDeliveriesUncollectedVAT'):
            if _observed_ppn_number(form, (root, 'SellingPrice'), evidence) > 0:
                delivery = True
                break
    if not same_month and not delivery:
        return False
    turnover = _observed_ppn_number(form, ('TotalDeliveryOfGoodsAndServices', 'SellingPrice'), evidence)
    return not 1 <= turnover <= 4200000000


def _ppn_calendar_blocker(form, evidence, *, clock_interval, period_year):
    initial = _observed_ppn_number(form, ('ExportTangibleTaxableGoods', 'SellingPrice'), evidence)
    final = _observed_ppn_number(form, ('A1FormListOfExportTaxableGoodsOrServices', 'Total'), evidence)
    if initial != 0 and final != 0:
        return 'export_blocks_calendar_override'
    quartet = ('SellingPrice', 'OtherTaxBase', 'VAT', 'SalesTaxLuxuryGoods')
    invoice = [_observed_ppn_number(form, ('DomesticTaxableGoodsWithInvoiceCode02', key), evidence,
                                   nullish=True) for key in quartet]
    uncollected = [_observed_ppn_number(form, ('DomesticDeliveriesUncollectedVAT', key), evidence,
                                       nullish=True) for key in quartet]
    if any(value != 0 for value in invoice) and any(value == 0 for value in uncollected):
        return 'invoice_blocks_calendar_override'
    if clock_interval is None or type(period_year) is not _CorporateNumber:
        raise _UnsupportedMetadata('unbound_ppn_carry_forward_calendar')
    year = _checked_ppn_number(_decimal(period_year), integral=True)
    end = _observed_ppn_number(form, ('BookkeepingPeriodEnd',), evidence)
    if not 1970 <= year <= 2100 or not 1 <= end <= 12:
        raise _UnsupportedMetadata('unverified_ppn_calendar_source')
    try:
        dates = [datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=clock_interval[key])
                 for key in ('start_ms', 'end_ms')]
        dates = [date.astimezone(_JAKARTA) for date in dates]
    except (ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_ppn_calendar_interval') from None
    if any(not 1970 <= date.year <= 2100 or date.year > year
           or date.year == year and date.month > end for date in dates):
        raise _UnsupportedMetadata('unbound_ppn_carry_forward_calendar')
    evidence.append({**_evidence(period_year, ['PeriodYear']), 'source': 'outer',
                     'clock_interval': dict(clock_interval), 'rule': 'calendar-inactive-throughout-attempt'})
    return 'owned_interval_blocks_calendar_override'


def project_ppn_asked_to(form, *, model, clock_interval=None, period_year=None):
    """Resolve reviewed submitted-choice paths without a DOM checked-state read.

    Potential calendar-dependent carry-forward overrides remain unsupported
    unless a response-bound short circuit proves they cannot execute.
    """
    if clock_interval is not None:
        clock_interval = _capture_clock_interval(clock_interval,
            clock_interval.get('attempt') if isinstance(clock_interval, dict) else None)
    if not isinstance(form, dict) or model not in ('NORMAL', 'AMENDMENT'):
        raise _UnsupportedMetadata('unverified_ppn_asked_to_model')
    if 'AskedTo' not in form:
        raise _UnsupportedMetadata('missing_ppn_asked_to_source')
    evidence = []
    choice = _source_scalar(form, ('AskedTo',), evidence)
    choices = ('CARRY_FORWARD', 'FAST_REFUND', 'FORWARD_REFUND')
    if choice is not None and (type(choice) is not str or choice not in choices):
        raise _UnsupportedMetadata('unsupported_ppn_asked_to_source')
    if model == 'NORMAL':
        balance, integral, contributing = _ppn_vat_balance(form)
        evidence.extend(contributing)
        if not integral or balance < 0 or choice == 'FORWARD_REFUND':
            raise _UnsupportedMetadata('unverified_ppn_normal_choice_lifecycle')
        return {'value': None, 'rule': 'not_overpaid_clear', 'provenance': evidence}
    balance = _observed_ppn_number(form, ('VATUnderOrOverPaidDueToAmendment', 'VAT'), evidence)
    if balance >= 0:
        if choice == 'FORWARD_REFUND':
            raise _UnsupportedMetadata('unverified_ppn_forward_refund_clear_event')
        return {'value': None, 'rule': 'not_overpaid_clear', 'provenance': evidence}
    clears = _ppn_facility_clears(form, evidence)
    rule = _ppn_calendar_blocker(form, evidence, clock_interval=clock_interval, period_year=period_year)
    if clears:
        if choice == 'FORWARD_REFUND':
            raise _UnsupportedMetadata('unverified_ppn_forward_refund_clear_event')
        return {'value': None, 'rule': 'facility_clear_without_calendar_override', 'provenance': evidence}
    return {'value': choice, 'rule': rule, 'provenance': evidence}


def project_ppn_header(payload, control):
    """Use source literals with the approved workbook's period/status presentation."""
    if not isinstance(payload, dict):
        raise _UnsupportedMetadata('unsupported_ppn_header_source')
    if control == 'Period':
        value = payload.get('PeriodCode')
        if (type(value) is not str or not re.fullmatch(r'(0[1-9]|1[0-2]){2}[1-9][0-9]{3}', value)
                or value[:2] != value[2:4]):
            raise _UnsupportedMetadata('unsupported_ppn_header_period')
        return {'value': value[2:], 'rule': 'period_code_slice_2',
                'provenance': [_evidence(value, ['PeriodCode'])]}
    if control == 'Model':
        value = payload.get('ReturnSheetModel')
        labels = {'NORMAL': 'Normal', 'AMENDMENT': 'Pembetulan'}
        if type(value) is not str or value not in labels:
            raise _UnsupportedMetadata('unsupported_ppn_header_model')
        return {'value': labels[value], 'rule': 'approved_status_presentation',
                'provenance': [_evidence(value, ['ReturnSheetModel'])]}
    raise _UnsupportedMetadata('unsupported_ppn_header_control')


_PPN_COLLECTION_COLUMNS = {
    'SellingPrice': ('SellingPrice', 'TaxBase'),
    'OtherTaxBase': ('OtherTaxBase', 'OtherTaxBase'),
    'VAT': ('VAT', 'VAT'),
    'STLG': ('SalesTaxLuxuryGoods', 'STLG'),
}
_PPN_COLLECTION_BINDINGS = {
    prefix + suffix: (root, leaf, zero, conditional, footer_key)
    for prefix, root, zero, conditional in (
        ('VATandSTLGUnderOverpaidOnAmmendedVAT', 'VATAndSTLGUnderOrOverPaidOnAmmended', False, False),
        ('VATandSTLGUnderOverpaidDueAmmendment', 'VATAndSTLGUnderOfOverPaidDueToAmmendment', True, True),
        ('VATandSTLGCollectedByOtherPartiesUnderOverpaidOnAmmendedVAT', 'VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended', True, True),
        ('VATandSTLGCollectedByOtherPartiesUnderOverpaidDueAmmendment', None, True, True),
    )
    for suffix, (leaf, footer_key) in _PPN_COLLECTION_COLUMNS.items()
}


def _project_ppn_collection(form, control, model, lc_footer):
    root, leaf, zero, conditional, footer_key = _PPN_COLLECTION_BINDINGS[control]
    evidence = []
    if conditional:
        nested = _source_scalar(form, ('A1FormListOfExportTaxableGoodsOrServices', 'ReturnSheetModel'), evidence)
        if model != 'AMENDMENT' or nested != 'AMENDMENT':
            raise _UnsupportedMetadata('unverified_ppn_nested_amendment_branch')
    if root is not None:
        value = _ppn_source_number(form, (root, leaf), evidence)
        rendered = ('0' if zero else '') if value is None else _number(value, 0, locale='id-ID')
        return {'value': rendered, 'rule': 'nested_amendment_stored' if conditional else 'direct_final_path',
                'provenance': evidence}
    if not isinstance(lc_footer, dict):
        raise _UnsupportedMetadata('missing_ppn_amendment_lc_footer')
    prior = _ppn_source_number(form, ('VATAndSTLGCollectedByOtherPartiesUnderOrOverPaidOnAmmended', leaf), evidence)
    previous = _decimal(prior) if prior is not None else Decimal(0)
    footer_evidence = []
    raw = _source_scalar(lc_footer, (footer_key,), footer_evidence)
    if raw is not None and not (isinstance(raw, _CorporateNumber) or
            type(raw) is str and _FOOTER_DECIMAL_STRING.fullmatch(raw)):
        raise _UnsupportedMetadata('unsupported_ppn_amendment_footer_number')
    current = _decimal(raw) if raw is not None else Decimal(0)
    evidence.extend({**entry, 'source': 'lc_footer'} for entry in footer_evidence)
    if current == previous:
        # The subscription merges total/prior changes BEFORE distinctUntilChanged.
        # An equal footer can be suppressed. Only an invariant initial difference
        # proves zero without inventing an unobserved intermediate callback.
        initial = _ppn_source_number(form, ('TotalVATAndSTLGCollectedByOtherParties', leaf), evidence)
        initial = _decimal(initial) if initial is not None else Decimal(0)
        if initial != current:
            raise _UnsupportedMetadata('unverified_ppn_equal_footer_callback')
    total = (current - previous).to_integral_value(rounding=ROUND_FLOOR)
    return {'value': _number(str(total), 0, locale='id-ID'),
            'rule': 'floor_lc_footer_minus_previous', 'provenance': evidence}


_PPN_OUTPUT_COMPONENTS = ('DomesticDeliveriesUsingOtherValue', 'DomesticDeliveriesToTourist',
    'DomesticDeliveriesOtherThanOtherValue', 'DomesticDeliveriesSelfCollected')
_PPN_INPUT_COMPONENTS = ('ImportOfTaxableGoods', 'DomesticTaxableGoodsUsingOtherValueTaxBase',
    'DomesticTaxableGoodsWithInvoiceCode01', 'DomesticTaxableGoodsWithInvoiceCode02',
    'CarryForwardOfInputTax', 'ResultsOfTheRecalculation')


def _ppn_vat_balance(form):
    evidence = []
    basis = _source_scalar(form, ('BasedOnType',), evidence)
    goods = _ppn_source_number(form, ('InputTaxPercentageGoods',), evidence)
    services = _ppn_source_number(form, ('InputTaxPercentageServices',), evidence)
    if basis is not None or (goods is not None and services is not None and
                             float(_decimal(goods)) == 90 and float(_decimal(services)) == 0):
        raise _UnsupportedMetadata('unverified_ppn_final_balance_lifecycle')
    # The final onChangeBasedOnType resets these percentages to 90/0.
    # A definite change invokes the normal-VAT balance calculation even on a
    # disabled submitted form; its earlier stored balance is then overwritten.
    values = []
    for path in (('OutputTaxMustBeSelfCollected', 'VAT'), ('VATIsDepositedInAdvance', 'VAT'),
                 ('InputTaxCanBeCalculated', 'VAT'), ('VATCollectedByVATCollector', 'VAT')):
        values.append(_observed_ppn_number(form, path, evidence,
            nullish=path[0] in ('VATIsDepositedInAdvance', 'VATCollectedByVATCollector'), integral=False))
    for components, reported in ((_PPN_OUTPUT_COMPONENTS, values[0]), (_PPN_INPUT_COMPONENTS, values[2])):
        total = Decimal(0)
        for root in components:
            total = _checked_ppn_number(total + _observed_ppn_number(form, (root, 'VAT'), evidence, nullish=True),
                                       integral=True)
        if total != reported:
            raise _UnsupportedMetadata('unreconciled_ppn_reactive_balance_operand')
    with localcontext() as context:
        context.prec = 40
        total = values[0]
        for value in values[1:]:
            total = _checked_ppn_number(total - value)
    return (total.to_integral_value(rounding=ROUND_FLOOR),
            all(value == value.to_integral_value() for value in values), evidence)


def _project_ppn_vat_balance(form):
    total, _, evidence = _ppn_vat_balance(form)
    return {'value': _number(str(total), 0, locale='id-ID'),
            'rule': 'late_percentage_change_normal_vat_balance', 'provenance': evidence}


def project_ppn_amount(form, control, *, model, lc_footer=None):
    """Apply reviewed final-value precedence, retaining only real dependencies."""
    if not isinstance(form, dict) or model not in ('NORMAL', 'AMENDMENT'):
        raise _UnsupportedMetadata('unsupported_ppn_amount_model_or_source')
    if model == 'NORMAL' and control in _NORMAL_NULL_CONTROLS:
        return {'value': '', 'rule': 'normal_model_null', 'provenance': []}
    evidence = []
    if control in ('STLGSelfCollected', 'STLGUnderOverpaid', 'STLGUnderOverpaidDueAmmendment'):
        total = Decimal(0)
        for path in _STLG_SUM_PATHS:
            value = _ppn_source_number(form, path, evidence)
            total += _decimal(value) if value is not None else Decimal(0)
        total = total.to_integral_value(rounding=ROUND_FLOOR)
        rule = 'floor_sum_submitted_stlg'
        if control != 'STLGSelfCollected':
            value = _ppn_source_number(form, ('STLGCollectedByVATCollector', 'SalesTaxLuxuryGoods'), evidence)
            total = (total - (_decimal(value) if value is not None else Decimal(0))).to_integral_value(rounding=ROUND_FLOOR)
            rule = 'floor_difference_submitted_stlg'
        if control == 'STLGUnderOverpaidDueAmmendment':
            value = _ppn_source_number(form, ('STLGUnderOrOverPaidOnPrevious', 'SalesTaxLuxuryGoods'), evidence)
            total = (total - (_decimal(value) if value is not None else Decimal(0))).to_integral_value(rounding=ROUND_FLOOR)
            rule = 'floor_difference_submitted_stlg_amendment'
        return {'value': _number(str(total), 0, locale='id-ID'), 'rule': rule, 'provenance': evidence}
    if control == 'VATIsUnderOrOverPaid':
        return _project_ppn_vat_balance(form)
    if control in _PPN_COLLECTION_BINDINGS:
        return _project_ppn_collection(form, control, model, lc_footer)
    binding = _PPN_AMOUNTS.get(control)
    if binding is None:
        raise _UnsupportedMetadata('unverified_ppn_amount_control')
    path, nullish_zero = binding
    value = _ppn_source_number(form, path, evidence)
    if control == 'VATIsUnderOrOverpaidAmandment' and value is None:
        # A submitted callback restores its prior value; it does not calculate
        # the amount from III.E/III.F. Null requires separate lifecycle proof.
        raise _UnsupportedMetadata('unverified_ppn_null_amendment_due_lifecycle')
    rendered = ('0' if nullish_zero else '') if value is None else _number(value, 0, locale='id-ID')
    return {'value': rendered, 'rule': 'nullish_zero' if nullish_zero else 'direct_final_path',
            'provenance': evidence}


# Columns bind footer source fields independently of grid row fields. In B2,
# TotalOtherTaxBase intentionally has no nullish-zero operator in the UI.
_PPN_FOOTERS = {
    'A-1': ('A1FormListOfExportTaxableGoodsOrServices', 4, (('Total', True),)),
    'A-2': ('A2FormListOfOutputTaxesOnDomesticDeliveries', 5,
            (('TotalTaxBase', True), ('TotalOtherTaxBase', True), ('TotalVAT', True), ('TotalSTLG', True))),
    'B-1': ('B1FormListTaxesCreditedOnTheImportTaxableGoods', 5,
            (('TotalTaxBase', True), ('TotalVAT', True), ('TotalSTLG', True))),
    'B-2': ('B2FormListTaxesThatCanBeCreditedForDomesticTaxableGoods', 5,
            (('TotalSellingPrice', True), ('TotalOtherTaxBase', False), ('TotalVAT', True), ('TotalSTLG', True))),
    'B-3': ('B3FormListOfInputTaxesUncredit', 5,
            (('TotalSellingPrice', True), ('TotalOtherTaxBase', True), ('TotalVAT', True), ('TotalSTLG', True))),
}
_LC_INDUK_CONTROLS = (
    ('TaxBase', 'TotalVATandSTLGCollectedByOtherPartiesSellingPrice'),
    ('OtherTaxBase', 'TotalVATandSTLGCollectedByOtherPartiesOtherTaxBase'),
    ('VAT', 'TotalVATandSTLGCollectedByOtherPartiesVAT'),
    ('STLG', 'TotalVATandSTLGCollectedByOtherPartiesSTLG'),
)
_FOOTER_DECIMAL_STRING = re.compile(r'[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?')


def project_ppn_footer(form_name, form, *, lc_footer=None):
    """Project totals only; caller must bind packets, endpoint and completion.

    C's successful footer response supersedes both stored Induk and C totals.
    Never derive a footer by summing the visible page or reuse a stale prefill.
    """
    if not isinstance(form, dict):
        raise _UnsupportedMetadata('unsupported_ppn_footer_form')
    if form_name == 'C':
        if not isinstance(lc_footer, dict):
            raise _UnsupportedMetadata('unbound_ppn_lc_footer')
        source, source_kind, root, span = lc_footer, 'lc_footer', None, 9
        fields = tuple((field, True) for field, _ in _LC_INDUK_CONTROLS)
    else:
        binding = _PPN_FOOTERS.get(form_name)
        if binding is None:
            raise _UnsupportedMetadata('unsupported_ppn_footer_binding')
        root, span, fields = binding
        source, source_kind = form, 'prefill_form'
    cells, evidence = [], []
    for field, nullish_zero in fields:
        path = (root, field) if root is not None else (field,)
        value = _source_scalar(source, path, evidence)
        evidence[-1]['source'] = source_kind
        if value is None and nullish_zero:
            value = '0'
        cells.append(render_grid_value(value, 'number', footer=True))
    induk_values = {}
    if form_name == 'C':
        induk_values = {control: value for (_, control), value in zip(_LC_INDUK_CONTROLS, cells)}
    return {'footer': [['TOTAL', *cells, '']],
            'footer_spans': [[span, *([1] * len(cells)), 1]],
            'induk_values': induk_values, 'provenance': evidence}


_UNIFIKASI_FOOTERS = {
    'list-i-bpnr': ((10, 1, 5), (
        ('TotalIncomeTaxWithDirectPaymentBPUBPNR', 'JUMLAH PAJAK PENGHASILAN DITANGGUNG PEMERINTAH DENGAN MENGGUNAKAN METODE PEMBAYARAN LANGSUNG'),
        ('TotalIncomeTaxBPUBPNR', 'JUMLAH PAJAK PENGHASILAN DITANGGUNG PEMERINTAH'),
        ('TotalIncomeTaxPaidWithDirectPaymentBPUBPNR', 'JUMLAH PAJAK PENGHASILAN DIBAYAR DENGAN MENGGUNAKAN METODE PEMBAYARAN LANGSUNG'),
        ('TotalIncomeTaxToBePaidBPUBPNR', 'JUMLAH PAJAK PENGHASILAN YANG HARUS DIBAYAR'),
    )),
    'list-ii-sp': ((6, 1, 4), (
        ('TotalIncomeTaxSP', 'JUMLAH PPh YANG DITANGGUNG PEMERINTAH'),
        ('TotalIncomeTaxToBePaidSP', 'JUMLAH PPh YANG HARUS DIBAYAR'),
    )),
    'list-ii-cy': ((6, 1, 4), (('TotalIncomeTaxToBePaidCY', 'JUMLAH PPh YANG HARUS DIBAYAR'),)),
    'attachment-i': ((12, 1, 4), (('TotalIncomeTaxAttachment', 'TOTAL INCOME PAX TO BE PAID'),)),
}


def project_unifikasi_footer(grid_name, form):
    """Bind totals to their visible grid, not to similarly named body columns."""
    if not isinstance(form, dict):
        raise _UnsupportedMetadata('unsupported_unifikasi_footer_source')
    if grid_name == 'list-i-bpu':
        # This grid explicitly sets showFooter=false, despite column footer keys.
        return {'footer': [], 'footer_spans': [], 'provenance': []}
    binding = _UNIFIKASI_FOOTERS.get(grid_name)
    if binding is None:
        raise _UnsupportedMetadata('unsupported_unifikasi_footer_grid')
    spans, fields = binding
    rows, evidence = [], []
    for field, label in fields:
        value = _source_scalar(form, (field,), evidence)
        evidence[-1]['source'] = 'prefill_form'
        displayed = render_grid_value('0' if value is None else value, 'number', footer=True)
        rows.append([label, displayed, ''])
    return {'footer': rows, 'footer_spans': [list(spans) for _ in rows], 'provenance': evidence}


_UNIFIKASI_TEXT = {
    'TaxIdentificationNumber': ('TaxIdentificationNumber',),
    'FullName': ('Name',),
    'Address': ('Address',),
    'PhoneNumber': ('PhoneNumber',),
    'StatementTIN': ('Signer', 'StatementTIN'),
    'StatementFullName': ('Signer', 'StatementFullName'),
}


def project_unifikasi_text(form, control):
    """Missing signer values require claims in the UI, so cannot be projected."""
    path = _UNIFIKASI_TEXT.get(control)
    if path is None or not isinstance(form, dict):
        raise _UnsupportedMetadata('unsupported_unifikasi_text_binding')
    evidence = []
    value = _source_scalar(form, path, evidence)
    if value is None and path[0] == 'Signer':
        raise _UnsupportedMetadata('unverified_unifikasi_signer_claim_fallback')
    if value is not None and type(value) is not str:
        raise _UnsupportedMetadata('unsupported_unifikasi_text_type')
    return {'value': '' if value is None else value, 'provenance': evidence}


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
    'C': (('SellerTin', 'text'), ('SellerName', 'text'), ('BuyerTin', 'text'),
          ('BuyerName', 'text'), ('TypeOfVat', 'reference'), ('BillingNumber', 'text'),
          ('BillingDate', 'date'), ('CodeAndSerialNumber', 'text'), ('TaxBase', 'number'),
          ('OtherTaxBase', 'number'), ('VAT', 'number'), ('STLG', 'number'), ('Information', 'text')),
}
_UNIFIKASI_WITHHOLDING_COLUMNS = (
    ('TaxIdentificationNumber', 'text'), ('TaxpayerName', 'text'), ('WithholdingSlipsNumber', 'text'),
    ('WithholdingSlipsDate', 'date'), ('TaxArticle', 'text'), ('TaxObjectCode', 'text'),
    ('TaxObject', 'text'), ('TaxBase', 'number'), ('TaxRate', 'number2'), ('IncomeTax', 'number'),
    ('TaxCertificate', 'reference'), ('PaymentMethod', 'reference'), ('BranchId', 'text'),
    ('Status', 'text'), ('RevenueCode', 'text'),
)
_UNIFIKASI_SELF_PAYMENT_COLUMNS = (
    ('TaxArticle', 'text'), ('TaxObjectCode', 'text'), ('TaxObject', 'reference'),
    ('TaxBase', 'number'), ('TaxRate', 'number2'), ('IncomeTax', 'number'),
    ('TaxCertificate', 'reference'), ('BranchId', 'text'), ('Status', 'text'), ('RevenueCode', 'text'),
)
_UNIFIKASI_GRID_COLUMNS = {
    'list-i-bpu': _UNIFIKASI_WITHHOLDING_COLUMNS,
    'list-i-bpnr': _UNIFIKASI_WITHHOLDING_COLUMNS,
    'list-ii-sp': _UNIFIKASI_SELF_PAYMENT_COLUMNS,
    'list-ii-cy': _UNIFIKASI_SELF_PAYMENT_COLUMNS,
    'attachment-i': (
        ('RecipientIdentificationNumber', 'text'), ('RecipientName', 'text'), ('RecipientAccountId', 'text'),
        ('GiverIdentificationNumber', 'text'), ('GiverName', 'text'), ('GiverAccountId', 'text'),
        ('TaxObjectCode', 'text'), ('BillingDocumentNumber', 'text'), ('BillingDocumentDate', 'date'),
        ('TaxBase', 'number'), ('TaxRate', 'number2'), ('IncomeTax', 'number'),
        ('TaxCertificate', 'reference'), ('BranchId', 'text'), ('Status', 'text'), ('RevenueCode', 'text')),
}


def project_ppn_grid(form_name, pages, headers, *, record_id, timezone_name, lookups=None):
    return _project_masa_grid(_PPN_GRID_COLUMNS.get(form_name), pages, headers,
                              record_id=record_id, timezone_name=timezone_name,
                              lookups=lookups, ppn_form=form_name)


def project_unifikasi_grid(grid_name, pages, headers, *, record_id, timezone_name, lookups):
    return _project_masa_grid(_UNIFIKASI_GRID_COLUMNS.get(grid_name), pages, headers,
                              record_id=record_id, timezone_name=timezone_name,
                              lookups=lookups, global_ordinal=True)


def _project_masa_grid(columns, pages, headers, *, record_id, timezone_name,
                       lookups, ppn_form=None, global_ordinal=False, date_prefix_fields=()):
    """Share page custody for the observed grids, not their semantic bindings.

    Endpoint/build/header/reference binding remains the observer/adapter's job;
    these checks additionally prevent mixing selected records and page scopes.
    """
    lookups = {} if lookups is None else lookups
    if not isinstance(lookups, dict):
        raise _UnsupportedMetadata('unverified_masa_reference_bindings')
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
    query_scope = None
    for page in pages:
        request, payload = page['request'], page.get('payload')
        if 'ReturnSheetRecordId' not in request:
            raise _UnsupportedMetadata('missing_ppn_grid_record_binding')
        if request.get('Filters', []) != []:
            raise _UnsupportedMetadata('filtered_masa_grid_is_not_full_coverage')
        current_scope = _corporate_request_key({key: value for key, value in request.items()
                                               if key not in ('First', 'Rows')})
        if query_scope is not None and query_scope != current_scope:
            raise JsonSafetyError('Masa grid query scope or sorting changed between pages')
        query_scope = current_scope
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
            # PPN components use page-local Data.indexOf; generic Unifikasi
            # RowNumber includes the request offset and a trailing dot.
            rendered = [f'{first + index + 1}.' if global_ordinal else str(index + 1)]
            for key, kind in columns:
                if key not in source:
                    raise _UnsupportedMetadata('missing_ppn_grid_source_column')
                value = source[key]
                provenance.append({**_evidence(value, ['Data', index, key]), 'sequence': sequence})
                if (ppn_form == 'A-2' and key == 'TIN' and value == '0000000000000000'
                        and source.get('DocumentNumberByBuyerInfor') is not None):
                    value = source['DocumentNumberByBuyerInfor']
                    provenance.append({**_evidence(value, ['Data', index, 'DocumentNumberByBuyerInfor']),
                                       'sequence': sequence})
                if kind == 'reference':
                    if value is None or value == '':
                        rendered.append('')
                        continue
                    mapping = lookups.get(key)
                    if (type(value) is not str or not isinstance(mapping, dict)
                            or type(mapping.get(value)) is not str):
                        raise _UnsupportedMetadata('unbound_masa_reference_description')
                    provenance[-1]['lookup'] = key
                    rendered.append(mapping[value])
                else:
                    if key in date_prefix_fields:
                        if kind != 'date' or type(value) is not str:
                            raise _UnsupportedMetadata('unsupported_masa_date_prefix')
                        # Preserve the unmodified value in provenance above.
                        value = value[:10]
                    rendered.append(render_grid_value(value, 'number' if kind == 'number2' else kind,
                                                      fraction=2 if kind == 'number2' else 0,
                                                      timezone_name=timezone_name))
            rows.append(rendered)
    if len(rows) != total:
        raise _UnsupportedMetadata('incomplete_ppn_grid_pages')
    return {'table': {'headers': list(headers), 'rows': rows, 'body_row_count': len(rows),
                      'source_total': total, 'complete': True}, 'provenance': provenance}
