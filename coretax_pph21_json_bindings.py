"""PPh21 source projections from the pinned article-2126 public component.

These functions establish presentation only, never source identity or coverage.
The caller must bind primary custody, submitted lifecycle, model and migration.
"""
from decimal import Decimal
import math
import re

from coretax_json import JsonSafetyError, _CorporateNumber, _UnsupportedMetadata, _select_reference_version
from coretax_masa_bindings import _decimal, _evidence, _number, _source_scalar, render_grid_value, _project_masa_grid

_AMOUNT_SUFFIXES = (
    'IncomeTaxWithheld', 'CarryForward', 'PaymentWithSP2D',
    'IncomeTaxUnderpaidOverpaid', 'IncomeTaxPaidOnAmended',
    'IncomeTaxUnderpaidOverpaidDueToAmendment', 'IncomeTaxBorneByGovernment',
)
AMOUNT_CONTROLS = tuple(article + suffix for article in ('A21', 'A26')
                        for suffix in _AMOUNT_SUFFIXES)


def _safe(value):
    if not math.isfinite(value):
        raise _UnsupportedMetadata('nonfinite_pph21_number')
    decimal = Decimal(str(value))
    if abs(decimal) > Decimal('9007199254740991') or Decimal(format(decimal, '.15g')) != decimal:
        raise _UnsupportedMetadata('unverified_pph21_numeric_precision')
    return value


def _numeric(form, path, evidence, *, missing_zero=False):
    value = _source_scalar(form, path, evidence)
    if evidence[-1]['type'] == 'missing' and not missing_zero:
        # Math.round(undefined) is NaN, whereas Math.round(null) is zero.
        raise _UnsupportedMetadata('missing_pph21_direct_amount')
    if value is None:
        return 0.0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_pph21_amount_type')
    decimal = _decimal(value)
    number = float(decimal)
    if Decimal(str(number)) != decimal:
        raise _UnsupportedMetadata('unverified_pph21_browser_conversion')
    return _safe(number)


def _round(value):
    # JS Math.round ties go towards positive infinity, including negative ties.
    # Avoid adding 0.5 to a large float, which can itself round before flooring.
    value = _safe(value)
    floor = math.floor(value)
    return _safe(floor + (1 if value - floor >= 0.5 else 0))


def _contribution_sum(form, article, suffix, evidence):
    paths = ([('Form1A', 'GrossIncomeAnd' + suffix, 'IncomeTax'),
              ('Form1B', 'GrossIncomeAnd' + suffix, 'IncomeTax')]
             if article == 'A21' else [])
    paths.append(('Form3', 'Article' + article[1:] + 'GrossIncomeAnd' + suffix, 'IncomeTax'))
    total = 0.0
    for path in paths:
        total = _safe(total + _numeric(form, path, evidence, missing_zero=True))
    return _round(total)


def _balance(form, article, evidence):
    withheld = _contribution_sum(form, article, 'IncomeTaxWithheld', evidence)
    carry = _round(_numeric(form, (article + 'CarryForward',), evidence))
    payment = _round(_numeric(form, (article + 'PaymentWithSP2D',), evidence))
    return _safe(_safe(withheld - carry) - payment)


def project_pph21_amount(form, control, *, model, migrated):
    """Project raw FormData through service calculation AND later child writes."""
    if (not isinstance(form, dict) or type(model) is not str or model not in ('NORMAL', 'AMENDMENT')
            or type(migrated) is not bool or type(control) is not str or control not in AMOUNT_CONTROLS):
        raise _UnsupportedMetadata('unsupported_pph21_amount_binding')
    article, suffix = control[:3], control[3:]
    evidence = []
    if suffix == 'IncomeTaxWithheld':
        value = _contribution_sum(form, article, suffix, evidence)
        rule = 'service_sum_then_child_round'
    elif suffix == 'IncomeTaxBorneByGovernment':
        stored = _numeric(form, (control,), evidence, missing_zero=True)
        value = (_contribution_sum(form, article, suffix, evidence) if stored == 0 else _round(stored))
        rule = 'zero_null_service_sum_else_stored_then_child_round'
    elif migrated and article == 'A21' and suffix in (
            'IncomeTaxUnderpaidOverpaid', 'IncomeTaxUnderpaidOverpaidDueToAmendment'):
        value = _round(_numeric(form, (control,), evidence))
        rule = 'migrated_a21_raw_balance'
    elif suffix == 'IncomeTaxUnderpaidOverpaid':
        value = _balance(form, article, evidence)
        rule = 'child_rounded_controls_balance'
    elif suffix == 'IncomeTaxUnderpaidOverpaidDueToAmendment' and model == 'AMENDMENT':
        balance = _balance(form, article, evidence)
        paid = _round(_numeric(form, (article + 'IncomeTaxPaidOnAmended',), evidence))
        value = _safe(balance - paid)
        rule = 'child_amendment_balance_after_base_model'
    else:
        value = _round(_numeric(form, (control,), evidence))
        rule = 'child_round_stored_value'
    return {'value': _number(str(value), 0, locale='id-ID'), 'rule': rule, 'provenance': evidence}


_BORNE = 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH'
_WITHHELD = 'JUMLAH PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DIPOTONG'
_TOTAL = 'JUMLAH TOTAL PENGHASILAN BRUTO DAN PAJAK PENGHASILAN YANG DITANGGUNG OLEH PEMERINTAH SERTA PAJAK PENGHASILAN YANG DIPOTONG'
_TOTAL_KEY = 'TotalGrossIncomeAndIncomeTaxBorneByGovernmentAndIncomeTaxWithheld'
_COMMON_TOTALS = (('GrossIncomeAndIncomeTaxBorneByGovernment', _BORNE),
                  ('GrossIncomeAndIncomeTaxWithheld', _WITHHELD), (_TOTAL_KEY, _TOTAL))
_FOOTERS = {
    'l1a': ('Form1A', (5, 3, 1, 1, 1, 5), _COMMON_TOTALS),
    'l1b-bpa2': ('Form1B', (5, 3, 1, 1, 5), _COMMON_TOTALS),
    'l2-bpa2': ('Form2', (5, 5, 1, 1, 4), ((None, 'TOTAL'),)),
    'l3-bp21': ('Form3', (4, 4, 1, 1, 4), (
        ('Article21GrossIncomeAndIncomeTaxBorneByGovernment',
         'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 21 DAN PAJAK PENGHASILAN PASAL 21 YANG DITANGGUNG OLEH PEMERINTAH'),
        ('Article21GrossIncomeAndIncomeTaxWithheld',
         'JUMLAH UNTUK PASAL 21 DAN PENGHASILAN BRUTO PASAL 21 SERTA PAJAK PENGHASILAN YANG DIPOTONG'))),
    'l3-bp26': ('Form3', (5, 7, 1, 1, 4), (
        ('Article26GrossIncomeAndIncomeTaxBorneByGovernment',
         'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 26 DAN PAJAK PENGHASILAN PASAL 26 YANG DITANGGUNG OLEH PEMERINTAH'),
        ('Article26GrossIncomeAndIncomeTaxWithheld',
         'JUMLAH UNTUK PASAL 26 DAN PENGHASILAN BRUTO PASAL 26 SERTA PAJAK PENGHASILAN YANG DIPOTONG'),
        (_TOTAL_KEY, _TOTAL))),
}


def project_pph21_footer(grid_name, form):
    """Keep reported totals and physical blank spacer separate from body rows."""
    if not isinstance(form, dict) or type(grid_name) is not str:
        raise _UnsupportedMetadata('unsupported_pph21_footer_source')
    if grid_name in ('l1b-bpa1', 'l2-bpa1'):
        return {'footer': [], 'footer_spans': [], 'provenance': []}
    spec = _FOOTERS.get(grid_name)
    if spec is None:
        raise _UnsupportedMetadata('unsupported_pph21_footer_grid')
    root, spans, totals = spec
    if not isinstance(form.get(root), dict):
        raise _UnsupportedMetadata('missing_pph21_appendix_source')
    rows, evidence = [[]], []
    for key, label in totals:
        fields = ('TotalGrossIncome', 'TotalIncomeTax') if key is None else ('GrossIncome', 'IncomeTax')
        displayed = []
        for field in fields:
            path = (root, field) if key is None else (root, key, field)
            value = _source_scalar(form, path, evidence)
            displayed.append(render_grid_value('0' if value is None else value, 'number', footer=True))
        gross, tax = displayed
        rows.append(['', label, gross, '', tax, ''] if grid_name == 'l1a'
                    else ['', label, gross, tax, ''])
    return {'footer': rows, 'footer_spans': [[]] + [list(spans) for _ in totals],
            'provenance': evidence}


# Each tuple binds the public component's field, renderer and static heading.
_COMMON_COLUMNS = (
    ('TIN', 'text', 'NIK/NPWP'), ('Name', 'text', 'NAMA'),
    ('WithholdingNumber', 'text', 'NOMOR BUKTI POTONG'),
    ('WithholdingDate', 'date', 'TANGGAL BUKTI PEMOTONGAN'),
    ('TaxObjectCode', 'text', 'KODE OBJEK PAJAK'),
    ('GrossIncome', 'number', 'PENGHASILAN BRUTO (Rp)'),
    ('IncomeTax', 'number', 'PAJAK PENGHASILAN (Rp)'),
    ('TaxCertificate', 'reference', 'FASILITAS PERPAJAKAN'),
    ('CountryCode', 'reference', 'Negara'),
    ('PlaceOfBusinessID', 'text', 'ID TEMPAT KEGIATAN USAHA'),
    ('RevenueCode', 'text', 'KAP-KJS'), ('Status', 'reference', 'STATUS'),
)
_LIA_COLUMNS = (_COMMON_COLUMNS[:2] + (
    ('WithholdingSlipsNumber', 'text', 'NOMOR BUKTI POTONG'),
    ('WithholdingSlipsDate', 'date', 'TANGGAL BUKTI PEMOTONGAN')) + _COMMON_COLUMNS[4:6]
    + (('TaxRate', 'number2', 'TARIF PAJAK (%)'),) + _COMMON_COLUMNS[6:])
_LII_COLUMNS = (_COMMON_COLUMNS[:7] + (('IncomePeriod', 'text', 'MASA PEEROLEHAN PENGHASILAN'),)
                + _COMMON_COLUMNS[8:10] + _COMMON_COLUMNS[11:])
_LIII_COLUMNS = (_COMMON_COLUMNS[:2] + (('TaxArticle', 'text', 'JENIS PAJAK'),)
                 + _COMMON_COLUMNS[2:5] + (('TaxObject', 'text', 'OBJEK PAJAK'),)
                 + _COMMON_COLUMNS[5:8] + _COMMON_COLUMNS[9:])
GRID_COLUMNS = {'l1a': _LIA_COLUMNS, 'l1b-bpa1': _COMMON_COLUMNS, 'l1b-bpa2': _COMMON_COLUMNS,
                'l2-bpa1': _LII_COLUMNS, 'l2-bpa2': _LII_COLUMNS,
                'l3-bp21': _LIII_COLUMNS, 'l3-bp26': _LIII_COLUMNS}

REFERENCE_TYPES = ('EBUPOT_TAX_CERTIFICATE', 'COUNTRY_CODE', 'EBUPOT_STATUS')
_REFERENCE_FIELDS = ('TaxCertificate', 'CountryCode', 'Status')


def project_pph21_references(payload, *, requested_types, locale, clock_interval=None):
    """Project a request-bound catalog, not unverified UI filter choices.

    The caller establishes response custody and request locale. Time-dependent
    version selection stays unsupported without an observed browser clock.
    """
    if (type(requested_types) not in (list, tuple) or tuple(requested_types) != REFERENCE_TYPES
            or locale != 'id-ID' or not isinstance(payload, list)):
        raise _UnsupportedMetadata('unsupported_pph21_reference_binding')
    for catalog in payload:
        if isinstance(catalog, dict) and 'language' in catalog and catalog['language'] != locale:
            raise JsonSafetyError('PPh21 reference locale contradicts bound request')
    if (len(payload) != len(REFERENCE_TYPES) or any(not isinstance(item, dict) for item in payload)
            or any(type(item.get('ReferenceDataType')) is not str for item in payload)
            or {item['ReferenceDataType'] for item in payload} != set(REFERENCE_TYPES)):
        raise _UnsupportedMetadata('unsupported_pph21_reference_catalogs')
    lookups, evidence = {}, []
    for index, catalog in enumerate(payload):
        kind = catalog['ReferenceDataType']
        details = catalog.get('Details')
        if not isinstance(details, list):
            raise _UnsupportedMetadata('unsupported_pph21_reference_details')
        evidence.append(_evidence(kind, [index, 'ReferenceDataType']))
        if 'language' in catalog:
            evidence.append(_evidence(catalog['language'], [index, 'language']))
        versions, descriptions = {}, {}
        for ordinal, item in enumerate(details):
            if (not isinstance(item, dict) or type(item.get('Code')) is not str or not item['Code']
                    or type(item.get('CodeDescription')) is not str):
                raise _UnsupportedMetadata('unsupported_pph21_reference_scalar')
            versions.setdefault(item['Code'], []).append((ordinal, item))
            for key in ('Code', 'CodeDescription', 'ValidTo', 'ValidFrom'):
                if key in item:
                    entry = _evidence(item[key], [index, 'Details', ordinal, key])
                else:
                    entry = {'path': [index, 'Details', ordinal, key], 'value': None, 'type': 'missing'}
                evidence.append(entry)
                if key == 'CodeDescription':
                    descriptions[ordinal] = entry
        labels = {}
        for code, candidates in versions.items():
            ordinal, item, rule = _select_reference_version(candidates, clock_interval)
            labels[code] = item['CodeDescription']
            selected = descriptions[ordinal]
            selected['projection_rule'] = 'reviewed-grid-active-version:' + rule
            if clock_interval is not None and rule not in ('first-open-ended', 'only-version'):
                selected['clock_interval'] = dict(clock_interval)
        lookups[_REFERENCE_FIELDS[REFERENCE_TYPES.index(kind)]] = labels
    return {'lookups': lookups, 'provenance': evidence}


def project_pph21_model_references(payload, *, locale):
    """Model dropdowns retain all versions; ambiguous codes are unsupported."""
    if locale != 'id-ID' or not isinstance(payload, list) or len(payload) != 1:
        raise _UnsupportedMetadata('unsupported_pph21_model_reference')
    catalog = payload[0]
    if isinstance(catalog, dict) and 'language' in catalog and catalog['language'] != locale:
        raise JsonSafetyError('PPh21 model reference locale contradicts bound request')
    if (not isinstance(catalog, dict) or catalog.get('ReferenceDataType') != 'RETURN_SHEET_MODEL'
            or not isinstance(catalog.get('Details'), list)):
        raise _UnsupportedMetadata('unsupported_pph21_model_reference')
    labels, evidence = {}, [_evidence('RETURN_SHEET_MODEL', [0, 'ReferenceDataType'])]
    if 'language' in catalog:
        evidence.append(_evidence(catalog['language'], [0, 'language']))
    for index, item in enumerate(catalog['Details']):
        if (not isinstance(item, dict) or type(item.get('Code')) is not str or not item['Code']
                or type(item.get('CodeDescription')) is not str or item['Code'] in labels):
            raise _UnsupportedMetadata('unsupported_pph21_model_option')
        labels[item['Code']] = item['CodeDescription']
        for key in ('Code', 'CodeDescription'):
            evidence.append(_evidence(item[key], [0, 'Details', index, key]))
    return {'lookups': {'ReturnSheetModel': labels}, 'provenance': evidence}


def project_pph21_header(payload, control, *, model_labels=None):
    """getDataFromBaseForm runs after the child FormData patch; outer wins."""
    keys = {'TaxPeriodMonth': 'PeriodMonth', 'TaxPeriodYear': 'PeriodYear',
            'Status': 'ReturnSheetModel', 'SubmitInProgressStatus': 'ReturnSheetStatusCode'}
    if not isinstance(payload, dict) or type(control) is not str or control not in keys:
        raise _UnsupportedMetadata('unsupported_pph21_header_control')
    evidence = []
    key = keys[control]
    value = _source_scalar(payload, (key,), evidence)
    if evidence[-1]['type'] == 'missing':
        raise _UnsupportedMetadata('missing_pph21_header_source')
    result = {'container_path': ['Payload'], 'provenance': evidence,
              'rule': 'final_outer_base_form_patch'}
    if control == 'Status':
        if (type(value) is not str or not isinstance(model_labels, dict)
                or type(model_labels.get(value)) is not str):
            raise _UnsupportedMetadata('unbound_pph21_model_label')
        result.update(value=model_labels[value], reference={'type': 'RETURN_SHEET_MODEL', 'code': value})
    elif control == 'SubmitInProgressStatus':
        flag = payload.get('SubmitInProgressStatus')
        if type(flag) not in (bool, type(None)) or type(value) is not str:
            raise _UnsupportedMetadata('unsupported_pph21_submission_status')
        evidence.append({'path': ['SubmitInProgressStatus'], 'value': flag,
                         'type': 'missing' if 'SubmitInProgressStatus' not in payload else
                                 'boolean' if type(flag) is bool else 'null'})
        result['value'] = 'In Progress' if flag else 'Submitted' if value == 'SUBMITTED' else '-'
    else:
        if type(value) is _CorporateNumber:
            number = _decimal(value)
            if number != number.to_integral_value():
                raise _UnsupportedMetadata('unsupported_pph21_header_number')
            value = str(int(number))
        elif value is None:
            value = ''
        elif type(value) is not str:
            raise _UnsupportedMetadata('unsupported_pph21_header_type')
        result['value'] = value
    return result


def project_pph21_grid(grid_name, pages, headers, *, record_id, timezone_name, lookups=None):
    """Project complete source pages with explicit column and callback bindings."""
    spec = GRID_COLUMNS.get(grid_name) if type(grid_name) is str else None
    if spec is None or not isinstance(headers, list) or any(type(h) is not str for h in headers):
        raise _UnsupportedMetadata('unsupported_pph21_grid_binding')

    def heading(value):
        return re.sub(r'\s+', ' ', value.replace('(dd-mm-yyyy)', '')).strip().casefold()

    expected = ['NO.'] + [label for _, _, label in spec]
    if list(map(heading, headers)) != list(map(heading, expected)):
        raise _UnsupportedMetadata('unverified_pph21_grid_headers')
    return _project_masa_grid(tuple((key, kind) for key, kind, _ in spec), pages, headers,
                              record_id=record_id, timezone_name=timezone_name, lookups=lookups,
                              date_prefix_fields=('WithholdingDate',) if grid_name.startswith('l3-') else ())
