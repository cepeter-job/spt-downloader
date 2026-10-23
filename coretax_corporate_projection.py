"""Source-bound corporate presentation with separately proved form branches."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re

from coretax_json import (ORIGIN, CORPORATE_COUNTRY_REFERENCE_URL, JsonSafetyError,
                          CORPORATE_L3_REFERENCE_URLS, CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL,
                          CORPORATE_L11A_REFERENCE_URLS, CORPORATE_L11A_GRID_URLS,
                          CORPORATE_REFERENCE_REQUESTS,
                          _CorporateNumber, _UnsupportedMetadata, _corporate_json,
                          _corporate_request_key, _corporate_integer,
                          _select_reference_version, _reference_consumer_order, _reference_locale)
from coretax_masa_bindings import _decimal, _number, _evidence

CIT_SOURCE = ORIGIN + '/returnsheets/id-ID/525.ec1edffbb4a91d20.js'
MAIN_SOURCE = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
BUILD_DIGESTS = {
    CIT_SOURCE: 'fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d',
    MAIN_SOURCE: '696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd',
}
VENDOR_SOURCE = ORIGIN + '/returnsheets/id-ID/vendor.a03856633dae3544.js'
L11C_BUILD_DIGESTS = {**BUILD_DIGESTS,
    VENDOR_SOURCE: '1de6335b41d5431fd302ab7b7d00b6c593dfa6640c43ab8a88fbfbdb1b0f4b68'}
L1D_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L3_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L11A_BUILD_DIGESTS = dict(L11C_BUILD_DIGESTS)
L11C_ROOT, L11C_BODY = 'L11CFormData', 'ForeignPrivateDebtReports'
L11C_AMOUNTS = ('DebtPrincipalBeginningOfYear', 'AdditionOfDebtPrincipal',
    'SubstractionOfDebtPrincipal', 'DebtPrincipalEndOfYear', 'AmountOfInterest',
    'BorrowingCostOtherThanInterest')
L11C_TOTALS = ('TotalDebtPrincipalBeginningOfYear', 'TotalAdditionOfDebtPrincipal',
    'TotalSubstractionOfDebtPrincipal', 'TotalDebtPrincipalEndOfYear', 'TotalInterest',
    'TotalBorrowingCostOtherThanInterest')
L11C_COLUMNS = ('NameOfCreditor', 'AddressOfCreditor', 'CountryOfCreditor', 'Currency',
    'EndOfYearRate', *L11C_AMOUNTS[:4], 'LoanStartDate', 'LoanDueDate', 'InterestRate',
    *L11C_AMOUNTS[4:], 'LoanAllocation')
L11C_HEADERS = ['NO.', 'PEMBERI PINJAMAN / NAMA', 'PEMBERI PINJAMAN / ALAMAT',
    'PEMBERI PINJAMAN / NEGARA/YURISDIKSI', 'MATA UANG / KODE', 'MATA UANG / KURS AKHIR TAHUN',
    'POKOK UTANG (Rp) / AWAL TAHUN', 'POKOK UTANG (Rp) / MUTASI / PENAMBAHAN',
    'POKOK UTANG (Rp) / MUTASI / PENGURANGAN', 'POKOK UTANG (Rp) / AKHIR TAHUN',
    'JANGKA WAKTU PINJAMAN / Tanggal Mulai', 'JANGKA WAKTU PINJAMAN / Tanggal Jatuh Tempo',
    'BUNGA / TINGKAT (%)', 'BUNGA / JUMLAH (Rp)',
    'BIAYA TERKAIT PEROLEHAN PINJAMAN SELAIN BUNGA (Rp)', 'PERUNTUKAN PINJAMAN']
L11C_SPANS = [[1, 5, *([1] * 10)]]
L7_ROOT = 'CalculationOfFiscalLossCompensation'
L7_BODY = 'FiscalNetProfitAndLossCompensation'
L7_SUFFIXES = ('YearMinus4', 'YearMinus3', 'YearMinus2', 'YearMinus1', 'YearCurrent', 'YearNext')
_MAX_INTEGER = 999999999999999


def _integer(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l7_numeric_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l7_numeric_precision')
    return int(number)


def _year(value):
    if (type(value) not in (str, _CorporateNumber) or len(value) > 32
            or not re.fullmatch(r'[0-9]+', value) or not 1900 <= int(value) <= 2100):
        raise _UnsupportedMetadata('unsupported_corporate_l7_year')
    return int(value)


def l7_headers(year):
    return ['NO.', 'LABA (RUGI) NETTO FISKAL / TAHUN/BAGIAN TAHUN PAJAK',
            'LABA (RUGI) NETTO FISKAL / NILAI (Rp)',
            *[f'KOMPENSASI KERUGIAN FISKAL / Y-{offset} / NILAI (Rp)' for offset in (4, 3, 2, 1)],
            f'KOMPENSASI KERUGIAN FISKAL / {year} / TAHUN PAJAK INI - NILAI (Rp)',
            'KOMPENSASI KERUGIAN FISKAL / Y+1 / TAHUN PAJAK BERJALAN - NILAI (Rp)']


def project_l7(form, *, main_form, period_year, headers, footer_spans, tax_type, locale):
    """Caller proves submitted initialization, current source, loaded pins and route.

    The pinned parent/Induk/L7 feedback supplies a stable nonnegative main input.
    Preserve reported totals only after proving equality with the six ordered
    JS reductions. Exact integral operands and partial sums avoid float guesses.
    """
    year = _year(period_year)
    if (type(period_year) is not _CorporateNumber or str(year) != period_year
            or tax_type not in ('ICT_RCIT', 'ICT_ROGCIT') or locale != 'id-ID'
            or headers != l7_headers(year) or footer_spans != [[3, 1, 1, 1, 1, 1, 1]]):
        raise _UnsupportedMetadata('unverified_corporate_l7_structure')
    total_keys = ['TotalFiscalLossCompensation' + suffix for suffix in L7_SUFFIXES]
    row_keys = ['TaxYear', 'FiscalNetProfitIncome'] + ['FiscalLossCompensation' + suffix for suffix in L7_SUFFIXES]
    if (not isinstance(form, dict) or set(form) != {L7_BODY, *total_keys}
            or not isinstance(form[L7_BODY], list) or not form[L7_BODY]
            or any(not isinstance(row, dict) or set(row) != set(row_keys) for row in form[L7_BODY])
            or not isinstance(main_form, dict) or 'NetIncomeBeforeTax' not in main_form):
        raise _UnsupportedMetadata('unsupported_corporate_l7_source_shape')
    main_value = main_form['NetIncomeBeforeTax']
    main_number = _integer(main_value)
    if main_number < 0:
        raise _UnsupportedMetadata('unverified_corporate_l7_main_lifecycle')
    years = [_year(row['TaxYear']) for row in form[L7_BODY]]
    if year not in years:
        # Pinned child dereferences find(currentYear) when main first changes.
        raise _UnsupportedMetadata('unverified_corporate_l7_current_year_row')
    first_current = years.index(year)
    totals, rows, provenance = [0] * 6, [], []
    for index, source in enumerate(form[L7_BODY]):
        values = [_integer(source[key]) for key in row_keys[1:]]
        for column, value in enumerate(values[1:]):
            totals[column] += value
            if abs(totals[column]) > _MAX_INTEGER:
                raise _UnsupportedMetadata('unsafe_corporate_l7_ordered_total')
        profit = main_value if index == first_current and values[0] == 0 else source['FiscalNetProfitIncome']
        rendered = [str(index + 1), str(source['TaxYear']),
                    _number(profit, 0, locale=locale),
                    *[_number(source[key], 0, locale=locale) for key in row_keys[2:]]]
        rows.append(rendered)
        for column, key in enumerate(row_keys, 1):
            entry = _evidence(source[key], [L7_ROOT, L7_BODY, index, key])
            entry.update(destination={'table': 'L7', 'row': index, 'column': column},
                         rule='literal-year' if key == 'TaxYear' else 'angular-number-1.0-0-id')
            if index == first_current and key == 'FiscalNetProfitIncome' and values[0] == 0:
                entry['rule'] = 'submitted-first-current-year-zero-to-main'
            provenance.append(entry)
    footer = ['JUMLAH']
    for column, key in enumerate(total_keys):
        if _integer(form[key]) != totals[column]:
            raise _UnsupportedMetadata('unreconciled_corporate_l7_reported_total')
        footer.append(_number(form[key], 0, locale=locale))
        entry = _evidence(form[key], [L7_ROOT, key])
        entry.update(destination={'table': 'L7', 'footer': 0, 'column': column + 3},
                     rule='reconciled-reported-total/angular-number-1.0-0-id')
        provenance.append(entry)
    main_entry = _evidence(main_value, ['MainFormData', 'NetIncomeBeforeTax'])
    main_entry.update(rule='submitted-nonnegative-main-invariant',
                      destination={'table': 'L7', 'row': first_current, 'column': 2})
    provenance.append(main_entry)
    count = len(rows)
    return {'table': {'name': 'L7', 'headers': list(headers), 'rows': rows + [footer],
                     'footer': [footer], 'footer_spans': [[3, 1, 1, 1, 1, 1, 1]],
                     'body_row_count': count, 'source_total': count, 'complete': True},
            'provenance': provenance}


L8_ROOT = 'CalculationFacilitiesIncomeTaxRateReduction'
L8_HEADERS = ['NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)']
_L8_GROUP = ('PERHITUNGAN FASILITAS PENGURANGAN TARIF PPh BAGI WAJIB PAJAK BADAN DALAM NEGERI '
             'BERDASARKAN PASAL 31E AYAT (1) UNDANG-UNDANG PPh')
_L8_KEYS = (
    'GrossTurnOver',
    'TaxableIncomeShareOfGrossCirculationGrantedFacility',
    'TaxableIncomeShareOfGrossCirculationNotGrantedFacility',
    'IncomeTaxPayableFromTaxableIncomeShareOfGrossCirculationGrantedFacility',
    'IncomeTaxPayableFromTaxableIncomeShareOfGrossCirculationNotGrantedFacility',
    'TotalIncomeTax',
)
_L8_CAPTIONS = (
    'Jumlah Peredaran Bruto',
    'Penghasilan Kena Pajak',
    'Penghasilan Kena Pajak dari bagian peredaran bruto yang memperoleh fasilitas',
    'Penghasilan Kena Pajak dari bagian peredaran bruto yang tidak memperoleh fasilitas',
    'Pajak Terutang',
    'PPh Terutang atas Penghasilan Kena Pajak dari bagian peredararan bruto yang memperoleh fasilitas',
    'PPh Terutang atas Penghasilan Kena Pajak dari bagian peredararan bruto yang tidak memperoleh fasilitas',
)
_L8_SPANS = ((1, 2), (1, 1, 1), (1, 2), (1, 1, 1), (1, 1, 1), (1, 2), (1, 1, 1), (1, 1, 1))


def _l8_integer(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l8_numeric_type')
    number = _decimal(value)
    if number.is_signed() or number > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l8_numeric_precision')
    return int(number)


def project_l8(form, *, main_form, period_year, headers, footer_spans, tax_type, locale):
    """Pure projection, never native admission or proof of stable main inputs.

    Caller proves loaded sources, current data, final original main operands and
    effective grid rate 1 throughout the relevant Rupiah lifecycle. The parent's
    optional captured exchange control cannot prove the grid rate. Preserve
    reported values only when initialization and recalculation agree; the
    reviewed integer bound makes the supported 11% multiplication exact.
    """
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or headers != L8_HEADERS
            or footer_spans != [[1, 1, 1]]
            or any(type(span) is not int for span in footer_spans[0])):
        raise _UnsupportedMetadata('unverified_corporate_l8_structure')
    required = set(_L8_KEYS)
    if (not isinstance(form, dict) or set(form) not in (required, required | {'ExchangeRateValue'})
            or not isinstance(main_form, dict)
            or not {'TaxYear', 'TaxableIncome', 'TotalGrossIncomeResearch'} <= set(main_form)
            or ('ExchangeRateValue' in form and form['ExchangeRateValue'] is not None
                and type(form['ExchangeRateValue']) is not _CorporateNumber)):
        raise _UnsupportedMetadata('unsupported_corporate_l8_source_shape')
    if (type(period_year) is not _CorporateNumber or not re.fullmatch(r'[0-9]{4}', period_year)
            or not 2020 <= int(period_year) <= 2100
            or type(main_form['TaxYear']) is not _CorporateNumber or main_form['TaxYear'] != period_year):
        raise _UnsupportedMetadata('unverified_corporate_l8_rate_year')
    values = [_l8_integer(form[key]) for key in _L8_KEYS]
    taxable = _l8_integer(main_form['TaxableIncome'])
    research = _l8_integer(main_form['TotalGrossIncomeResearch'])
    if values[0] > 4800000000 or research != 0:
        raise _UnsupportedMetadata('unverified_corporate_l8_branch')
    masked = taxable - taxable % 1000
    tax = (masked // 100) * 11
    if values[1:5] != [masked, 0, tax, 0]:
        raise _UnsupportedMetadata('unreconciled_corporate_l8_reported_values')
    if values[5] != values[3] + values[4] or values[5] != tax:
        raise _UnsupportedMetadata('unreconciled_corporate_l8_reported_total')

    rendered = [_number(form[key], 0, locale=locale) for key in _L8_KEYS]
    body = [
        ['1.', _L8_CAPTIONS[0]], ['', _L8_CAPTIONS[0], rendered[0]],
        ['2.', _L8_CAPTIONS[1]], ['', _L8_CAPTIONS[2], rendered[1]], ['', _L8_CAPTIONS[3], rendered[2]],
        ['3.', _L8_CAPTIONS[4]], ['', _L8_CAPTIONS[5], rendered[3]], ['', _L8_CAPTIONS[6], rendered[4]],
    ]
    footer = ['', 'Jumlah PPh Terutang', rendered[5]]
    destinations = [{'table': 'L8', 'row': row, 'column': 2} for row in (1, 3, 4, 6, 7)]
    destinations.append({'table': 'L8', 'footer': 0, 'column': 2})
    provenance = []
    for index, key in enumerate(_L8_KEYS):
        entry = _evidence(form[key], [L8_ROOT, key])
        entry.update(source='current', destination=deepcopy(destinations[index]),
                     rule='reconciled-captured/input-number-integer-id')
        if index in (3, 4):
            entry['also_supports'] = [deepcopy(destinations[-1])]
        provenance.append(entry)
    for key in ('TaxableIncome', 'TotalGrossIncomeResearch'):
        entry = _evidence(main_form[key], ['MainFormData', key])
        entry.update(source='current', destinations=deepcopy(destinations[1:]),
                     rule='reconciled-original-main-input')
        provenance.append(entry)
    for value, path, source, control in (
            (main_form['TaxYear'], ['MainFormData', 'TaxYear'], 'current', 'rate-year'),
            (period_year, ['PeriodYear'], 'primary', 'header-year')):
        entry = _evidence(value, path)
        entry.update(source=source, destination={'table': 'L8', 'control': control},
                     rule='matched-original-rate-and-header-years')
        provenance.append(entry)
    if 'ExchangeRateValue' in form:
        entry = _evidence(form['ExchangeRateValue'], [L8_ROOT, 'ExchangeRateValue'])
        entry.update(source='current', destination={'table': 'L8', 'control': 'unused-rupiah-exchange-rate'},
                     rule='retained-unused-rupiah-source-control')
        provenance.append(entry)
    return {'table': {'name': 'L8', 'group': _L8_GROUP, 'headers': list(headers),
                     'rows': body + [footer], 'footer': [footer], 'footer_spans': [[1, 1, 1]],
                     'body_spans': [list(spans) for spans in _L8_SPANS],
                     'body_rowspans': [[1] * len(row) for row in body],
                     'source_structure': {'form': 'L8', 'component': 'rsh-citr-l8-form-grid1',
                                          'groups': [_L8_GROUP]},
                     'pages': 1, 'body_row_count': 8, 'source_total': 8, 'complete': True},
            'provenance': provenance}


def _l11c_integer(value):
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11c_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l11c_number_precision')
    return int(number)


def _l11c_date(value):
    if value is None or value == '':
        return ''
    if type(value) is not str or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
            r'(?:\.[0-9]{1,3})?Z)?', value):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_date')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if date.year == 1:
            return ''  # Validated normalized ISO year0001 is the source sentinel.
        if not 1970 <= date.year <= 2100:
            raise ValueError('Unreviewed date range')
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
        return date.astimezone(timezone(timedelta(hours=7))).strftime('%d-%m-%Y')
    except (ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_date') from None


def project_countries(payload, *, clock_interval=None):
    """Exact naturally observed COUNTRY_CODE consumer; never read browser cache."""
    return _project_corporate_catalog(payload, kind='COUNTRY_CODE', clock_interval=clock_interval)


def _project_corporate_catalog(payload, *, kind, clock_interval=None, requested_types=None):
    """Reviewed singleton or exact ordered pair; preserve original array paths."""
    _reference_locale(payload)
    requested = (kind,) if requested_types is None else tuple(requested_types)
    if (kind not in {*CORPORATE_L3_REFERENCE_URLS, *CORPORATE_L11A_REFERENCE_URLS}
            or requested not in ((kind,), ('DEDUCTION_METHOD', 'TYPE_OF_FULFILLMENT'))
            or kind not in requested or not isinstance(payload, list) or len(payload) != len(requested)
            or any(not isinstance(item, dict) or type(item.get('ReferenceDataType')) is not str
                   for item in payload)
            or {item['ReferenceDataType'] for item in payload} != set(requested)):
        raise _UnsupportedMetadata('unsupported_corporate_country_catalog')
    catalog_index = next(index for index, item in enumerate(payload) if item['ReferenceDataType'] == kind)
    catalog, groups, evidence = payload[catalog_index], {}, []
    if not isinstance(catalog.get('Details'), list):
        raise _UnsupportedMetadata('unsupported_corporate_country_catalog')
    if 'language' in catalog and catalog['language'] != 'id-ID':
        raise JsonSafetyError('Corporate country locale contradicts observed source')
    evidence.append(_evidence(kind, [catalog_index, 'ReferenceDataType']))
    descriptions = {}
    ordered, order_rule = _reference_consumer_order(catalog['Details'], kind)
    for index, row in enumerate(catalog['Details']):
        if (not isinstance(row, dict) or type(row.get('Code')) is not str or not row['Code']
                or type(row.get('CodeDescription')) is not str or not row['CodeDescription'].strip()):
            raise _UnsupportedMetadata('unsupported_corporate_country_description')
        if 'language' in row and row['language'] != 'id-ID':
            raise JsonSafetyError('Corporate country locale contradicts observed source')
        for key in ('ValidFrom', 'ValidTo'):
            if key in row and row[key] is not None and type(row[key]) is not str:
                raise _UnsupportedMetadata('unsupported_corporate_country_validity')
        for key in ('Code', 'CodeDescription', 'ValidFrom', 'ValidTo', 'ParameterData'):
            entry = (_evidence(row[key], [catalog_index, 'Details', index, key]) if key in row else
                     {'path': [catalog_index, 'Details', index, key], 'type': 'missing', 'value': None})
            evidence.append(entry)
            if key == 'CodeDescription':
                descriptions[index] = entry
    for index, row in ordered:
        groups.setdefault(row['Code'], []).append((index, row))
    lookups, selected = {}, {}
    for code, candidates in groups.items():
        index, row, rule = _select_reference_version(candidates, clock_interval)
        lookups[code] = row['CodeDescription']
        entry = descriptions[index]
        entry['rule'] = ('reviewed-country-active-version:' if kind == 'COUNTRY_CODE'
                         else 'reviewed-corporate-catalog-active-version:') + rule
        entry['catalog_order_rule'] = order_rule
        if clock_interval is not None and rule not in ('first-open-ended', 'only-version'):
            entry['clock_interval'] = dict(clock_interval)
        selected[code] = deepcopy(entry)
    return {'lookups': lookups, 'provenance': evidence, 'selected': selected,
            'requires_vendor': any(len(items) > 1 for items in groups.values())}


def project_l11c(form, *, headers, footer_spans, tax_type, locale, timezone_name, country_labels):
    """Caller proves loaded provider/consumer pins and submitted current lifecycle."""
    if (headers != L11C_HEADERS or footer_spans != L11C_SPANS or tax_type != 'ICT_RCIT'
            or locale != 'id-ID' or timezone_name != 'Asia/Jakarta' or not isinstance(country_labels, dict)):
        raise _UnsupportedMetadata('unverified_corporate_l11c_structure')
    if not isinstance(form, dict) or set(form) != {L11C_BODY, *L11C_TOTALS}:
        raise _UnsupportedMetadata('unsupported_corporate_l11c_source_shape')
    body = [] if form[L11C_BODY] is None else form[L11C_BODY]
    if (not isinstance(body, list) or len(body) > 10000
            or any(not isinstance(row, dict) or set(row) != set(L11C_COLUMNS) for row in body)):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_source_shape')
    rows, evidence, sums = [], [], [0] * len(L11C_AMOUNTS)
    for index, source in enumerate(body):
        rendered = [str(index + 1)]
        for column, key in enumerate(L11C_COLUMNS, 1):
            value = source[key]
            entry = _evidence(value, [L11C_ROOT, L11C_BODY, index, key])
            entry['destination'] = {'table': 'L11-C', 'row': index, 'column': column}
            if key in L11C_AMOUNTS:
                number = 0 if value is None else _l11c_integer(value)
                position = L11C_AMOUNTS.index(key)
                sums[position] += number
                if abs(sums[position]) > _MAX_INTEGER:
                    raise _UnsupportedMetadata('unsafe_corporate_l11c_ordered_total')
                digits = 2 if key == 'DebtPrincipalEndOfYear' else 0
                text = _number(str(number), digits, locale=locale)
                entry['rule'] = 'nullish-zero/angular-number-id' if value is None else 'angular-number-id'
            elif key == 'InterestRate':
                text = '' if value is None else _number(str(_l11c_integer(value)), 2, locale=locale)
                entry['rule'] = 'angular-number-1.2-2-id'
            elif key in ('LoanStartDate', 'LoanDueDate'):
                text = _l11c_date(value)
                entry['rule'] = 'validated-date/normalized-sentinel/jakarta-dd-MM-yyyy'
            elif key == 'CountryOfCreditor':
                if value is None or value == '':
                    text = ''
                elif type(value) is str and value in country_labels and type(country_labels[value]) is str:
                    text = country_labels[value]
                else:
                    raise _UnsupportedMetadata('unbound_corporate_country_description')
                entry['rule'] = 'country-code-to-description'
            elif value is None or type(value) is str:
                text = '' if value is None else value
                entry['rule'] = 'literal-string'
            else:
                raise _UnsupportedMetadata('unsupported_corporate_l11c_text_type')
            rendered.append(text)
            evidence.append(entry)
        rows.append(rendered)
    amounts = []
    for index, key in enumerate(L11C_TOTALS):
        if _l11c_integer(form[key]) != sums[index]:
            raise _UnsupportedMetadata('unreconciled_corporate_l11c_reported_total')
        amounts.append(_number(form[key], 2 if index == 3 else 0, locale=locale))
        entry = _evidence(form[key], [L11C_ROOT, key])
        entry.update(destination={'table': 'L11-C', 'footer': 0, 'column': (6, 7, 8, 9, 13, 14)[index]},
                     rule='reconciled-reported-total/angular-number-id')
        evidence.append(entry)
    footer = ['', 'JUMLAH', *amounts[:4], '', '', '', *amounts[4:], '']
    return {'table': {'name': 'L11-C', 'headers': list(headers), 'rows': rows + [footer],
        'footer': [footer], 'footer_spans': deepcopy(L11C_SPANS), 'body_row_count': len(body),
        'source_total': len(body), 'complete': True}, 'provenance': evidence}


def _apply_l11c(binding, section, observed_forms, *, root, payload, record, event, country_packets):
    proof = binding['projection']
    if (not isinstance(proof, dict) or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
            or proof['kind'] != 'corporate-l11c-v1' or proof['builds'] != L11C_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[L11C_ROOT]]
            or binding.get('grids', []) or binding.get('responses', []) or binding.get('dependencies', [])):
        raise _UnsupportedMetadata('unsupported_corporate_l11c_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier')))
    literal = record.get('meta', {}).get('Model SPT')
    model = 'NORMAL' if literal == 'Normal' else 'AMENDMENT' if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None
    if (proof['route'] not in (route, route + '?view=true') or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l11c_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l11c_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11c_previous_encoding')
        try:
            previous = _corporate_json(previous)
        except JsonSafetyError:
            raise _UnsupportedMetadata('unsupported_corporate_l11c_previous_encoding') from None
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l11c_previous_shape')
    if not isinstance(proof['tables'], list) or len(proof['tables']) != 1:
        raise _UnsupportedMetadata('unverified_corporate_l11c_table_catalog')
    table = proof['tables'][0]
    if (not isinstance(table, dict) or set(table) != {'component', 'headers', 'footer_spans'}
            or table['component'] != 'rshshr-citr-l11c-form-grid1'):
        raise _UnsupportedMetadata('unverified_corporate_l11c_grid_owner')
    references = proof['references']
    if not isinstance(references, list) or len(references) > 1:
        raise _UnsupportedMetadata('unsupported_corporate_country_binding')
    catalogs, catalog_source = {'lookups': {}, 'provenance': [], 'selected': {}}, None
    if references:
        ref = references[0]
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or ref['endpoint'] != CORPORATE_COUNTRY_REFERENCE_URL or ref['method'] != 'GET'
                or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_country_binding')
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate country sequence is invalid or repeated')
        if set(sequences) != set(country_packets) or any(not country_packets[n]['successful'] for n in sequences):
            raise _UnsupportedMetadata('missing_or_failed_corporate_country_packet')
        catalog_source = country_packets[sequences[0]]
        catalogs = project_countries(catalog_source['payload'], clock_interval=catalog_source['event'].get('clock_interval'))
    result = project_l11c(root.get(L11C_ROOT), headers=table['headers'], footer_spans=table['footer_spans'],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'],
        country_labels=catalogs['lookups'])
    section['tables'] = [result['table']]
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    if catalog_source is not None:
        for entry in catalogs['provenance']:
            result['provenance'].append({**entry, 'response_sequence': catalog_source['event']['sequence'],
                'container': ['Payload'], 'destination': {'table': 'L11-C', 'reference': 'COUNTRY_CODE'}})
        for index, row in enumerate(root[L11C_ROOT][L11C_BODY] or []):
            if row['CountryOfCreditor'] in catalogs['selected']:
                result['provenance'].append({**deepcopy(catalogs['selected'][row['CountryOfCreditor']]),
                    'response_sequence': catalog_source['event']['sequence'], 'container': ['Payload'],
                    'destination': {'table': 'L11-C', 'row': index, 'column': 3}})
    return {'form': 'L11-C', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def _apply_l1d(binding, section, observed_forms, *, root, payload, record, event):
    proof = binding['projection']
    if (not isinstance(proof, dict)
            or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables'}
            or proof['kind'] != 'corporate-l1d-v1' or proof['builds'] != L1D_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [['L1dFormData']]
            or binding.get('grids', []) or binding.get('responses', []) or binding.get('dependencies', [])):
        raise _UnsupportedMetadata('unsupported_corporate_l1d_semantic_binding')
    # Packet decoding has already validated every present lifetime fact against
    # this attempt/record/source/frame. Absence never authorizes this branch.
    if event.get('component_lifetime') is None:
        raise _UnsupportedMetadata('missing_corporate_l1d_component_lifetime')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or payload.get('BusinessClassification') != 'BC04'
            or type(payload.get('IsMigrated')) is not bool
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]):
        raise _UnsupportedMetadata('unverified_corporate_l1d_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l1d_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l1d_previous_encoding')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l1d_previous_shape')
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 3:
        raise _UnsupportedMetadata('unverified_corporate_l1d_table_catalog')
    for index, table in enumerate(tables):
        structure = {'form': 'L1-D', 'component': f'rsh-citr-l1d-grid{index + 1}',
                     'groups': ['A. LAPORAN LABA RUGI' if index == 0 else 'B. LAPORAN POSISI KEUANGAN']}
        if (not isinstance(table, dict)
                or set(table) != {'component', 'headers', 'footer_spans', 'source_structure'}
                or table['component'] != structure['component'] or table['source_structure'] != structure):
            raise _UnsupportedMetadata('unverified_corporate_l1d_grid_owner')
    result = project_l1d(root.get('L1dFormData'), migrated=payload['IsMigrated'],
        headers=[t['headers'] for t in tables], footer_spans=[t['footer_spans'] for t in tables],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'])
    section['tables'] = result['tables']
    for entry in result['provenance']:
        entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
    return {'form': 'L1-D', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def apply_projections(sections, observed_forms, *, root, payload, record, event, country_packets=None,
                      reference_packets=None, auxiliary_packets=None):
    """Replace only explicitly declared semantic sections after packet safety."""
    projected = []
    for binding, section in zip(observed_forms, sections):
        if 'projection' not in binding:
            continue  # Preserve old evidence-leaf captures and caller contracts.
        if binding['name'] == 'L11-A':
            projected.append(_apply_l11a(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, reference_packets=reference_packets or {},
                auxiliary_packets=auxiliary_packets or {}))
            continue
        if binding['name'] == 'L3':
            projected.append(_apply_l3(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, reference_packets=reference_packets or {},
                auxiliary_packets=auxiliary_packets or {}))
            continue
        if binding['name'] == 'L1-D':
            projected.append(_apply_l1d(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event))
            continue
        if binding['name'] == 'L11-C':
            projected.append(_apply_l11c(binding, section, observed_forms, root=root, payload=payload,
                record=record, event=event, country_packets=country_packets or {}))
            continue
        proof = binding['projection']
        if (binding['name'] != 'L7' or not isinstance(proof, dict)
                or set(proof) != {'kind', 'builds', 'route', 'locale', 'tables'}
                or proof['kind'] != 'corporate-l7-v1' or proof['builds'] != BUILD_DIGESTS
                or proof['route'] != event['frame_url'] or proof['locale'] != 'id-ID'
                or not isinstance(proof['tables'], list) or len(proof['tables']) != 1
                or binding.get('paths') != [[L7_ROOT]] or binding.get('grids', [])
                or binding.get('responses', []) or binding.get('dependencies', [])):
            raise _UnsupportedMetadata('unsupported_corporate_semantic_binding')
        fields = record.get('source_fields', {})
        route = (ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
            str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                    fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))))
        literal_model = record.get('meta', {}).get('Model SPT')
        model = ('NORMAL' if literal_model == 'Normal' else 'AMENDMENT'
                 if isinstance(literal_model, str) and re.fullmatch(r'Amendment [0-9]{3}', literal_model) else None)
        if (proof['route'] not in (route, route + '?view=true') or record.get('source_status') != 'SPT Dilaporkan'
                or payload.get('ReturnSheetStatusCode') != 'SUBMITTED'
                or model is None or payload.get('ReturnSheetModel') != model
                or fields.get('ReturnSheetModel') != literal_model
                or 'Induk' not in [form['name'] for form in observed_forms[:observed_forms.index(binding)]]):
            raise _UnsupportedMetadata('unverified_corporate_l7_submitted_lifecycle')
        if 'PreviousFormData' not in payload:
            raise _UnsupportedMetadata('missing_corporate_l7_previous_encoding')
        previous = payload['PreviousFormData']
        if previous is not None:
            if type(previous) is not str:
                raise _UnsupportedMetadata('unsupported_corporate_l7_previous_encoding')
            try:
                previous = _corporate_json(previous)
            except JsonSafetyError:
                raise _UnsupportedMetadata('unsupported_corporate_l7_previous_encoding') from None
            if previous is not None and not isinstance(previous, dict):
                raise _UnsupportedMetadata('unsupported_corporate_l7_previous_shape')
        table = proof['tables'][0]
        if (not isinstance(table, dict) or set(table) != {'component', 'headers', 'footer_spans'}
                or table['component'] != 'rsh-citr-l7-grid1'):
            raise _UnsupportedMetadata('unverified_corporate_l7_grid_owner')
        result = project_l7(root.get(L7_ROOT), main_form=root.get('MainFormData'),
            period_year=payload.get('PeriodYear'), headers=table['headers'], footer_spans=table['footer_spans'],
            tax_type=fields.get('TaxTypeCode'), locale=proof['locale'])
        section['tables'] = [result['table']]
        for entry in result['provenance']:
            entry.update(response_sequence=event['sequence'], container=['Payload', 'CurrentFormData'])
        projected.append({'form': 'L7', 'kind': proof['kind'], 'builds': dict(proof['builds']),
                          'route': proof['route'], 'values': result['provenance']})
    return projected


# Static captions/control ownership from the pinned L1-D source; no source defaults.
_L1D_BALANCE_ROWS = [[('group', 'body', None, 'Aset Lancar', None),
  ('amount', 'body', '1101', 'Kas dan Setara Kas', 'AC1101'),
  ('amount', 'body', '1122', 'Piutang Usaha - Pihak Ketiga', 'AC1122'),
  ('amount', 'body', '1123', 'Piutang Usaha - Pihak yang Mempunyai Hubungan Istimewa', 'AC1123'),
  ('amount', 'body', '1124', 'Piutang Lainnya - Pihak Ketiga', 'AC1124'),
  ('amount', 'body', '1125', 'Piutang Lainnya - Pihak yang Mempunyai Hubungan Istimewa', 'AC1125'),
  ('amount', 'body', '1131', 'Cadangan Kerugian Penurunan Nilai - Aset Lancar', 'AC1131'),
  ('amount', 'body', '1181', 'Aset Kontrak', 'AC1181'),
  ('amount', 'body', '1200', 'Investasi', 'AC1200'),
  ('amount', 'body', '1401', 'Persediaan', 'AC1401'),
  ('amount', 'body', '1421', 'Beban Dibayar di Muka', 'AC1421'),
  ('amount', 'body', '1422', 'Uang Muka', 'AC1422'),
  ('amount', 'body', '1423', 'Pajak Dibayar di Muka', 'AC1423'),
  ('amount', 'body', '1499', 'Aset lancar lainnya', 'AC1499'),
  ('group', 'body', None, 'Aset Tidak Lancar', None),
  ('amount', 'body', '1501', 'Piutang Jangka Panjang', 'AC1501'),
  ('amount', 'body', '1521', 'Aset tetap dan inventaris', 'AC1521'),
  ('amount', 'body', '1522', 'Dikurangi: Akumulasi penyusutan aset tetap dan inventaris', 'AC1522'),
  ('amount',
   'body',
   '1551',
   'Investasi pada Perusahaan Asosiasi, Ventura Bersama dan Anak Perusahaan',
   'AC1551'),
  ('amount', 'body', '1599', 'Investasi Jangka Panjang Lainnya', 'AC1599'),
  ('amount', 'body', '1600', 'Aset Tak Berwujud', 'AC1600'),
  ('amount', 'body', '1601', 'Dikurangi : Akumulasi Amortisasi-Aset Tak Berwujud', 'AC1601'),
  ('amount', 'body', '1611', 'Aktiva Pajak Tangguhan', 'AC1611'),
  ('amount', 'body', '1651', 'Klaim atas pengembalian pajak', 'AC1651'),
  ('amount', 'body', '1658', 'Cadangan Kerugian Penurunan Nilai - Aset Tidak Lancar', 'AC1658'),
  ('amount', 'body', '1698', 'Aset Tidak Lancar Lainnya', 'AC1698'),
  ('footer_total', 'footer', '1700', 'Jumlah Aset', 'AC1700')],
 [('group', 'body', None, 'Liabilitas Jangka Pendek', None),
  ('amount', 'body', '2102', 'Utang Usaha - Pihak Ketiga', 'AC2102'),
  ('amount', 'body', '2103', 'Utang Usaha - Pihak yang Mempunyai Hubungan Istimewa', 'AC2103'),
  ('amount', 'body', '2111', 'Utang Bunga', 'AC2111'),
  ('amount', 'body', '2186', 'Liabilitas Kontrak', 'AC2186'),
  ('amount', 'body', '2187', 'Liabilitas Sewa Jangka Pendek', 'AC2187'),
  ('amount', 'body', '2191', 'Utang Pajak', 'AC2191'),
  ('amount', 'body', '2192', 'Utang Dividen', 'AC2192'),
  ('amount', 'body', '2195', 'Beban yang Masih Harus Dibayar', 'AC2195'),
  ('amount', 'body', '2201', 'Utang Bank Jangka Pendek', 'AC2201'),
  ('amount', 'body', '2202', 'Utang Jangka Panjang yang Jatuh Tempo dalam Satu Tahun', 'AC2202'),
  ('amount', 'body', '2203', 'Pendapatan Diterima di Muka', 'AC2203'),
  ('amount', 'body', '2228', 'Liabilitas Jangka Pendek Lainnya', 'AC2228'),
  ('group', 'body', None, 'Liabilitas Jangka Panjang', None),
  ('amount', 'body', '2301', 'Utang Bank Jangka Panjang', 'AC2301'),
  ('amount', 'body', '2303', 'Utang Jangka Panjang-Pihak Ketiga', 'AC2303'),
  ('amount',
   'body',
   '2304',
   'Utang Jangka Panjang - Pihak yang Mempunyai Hubungan Istimewa',
   'AC2304'),
  ('amount', 'body', '2312', 'Liabilitas Sewa Jangka Panjang', 'AC2312'),
  ('amount', 'body', '2321', 'Liabilitas Pajak Tangguhan', 'AC2321'),
  ('amount', 'body', '2322', 'Liabilitas Imbalan Kerja', 'AC2322'),
  ('amount', 'body', '2998', 'Liabilitas Jangka Panjang Lainnya', 'AC2998'),
  ('body_total', 'body', '2999', 'Jumlah Liabilitas', 'AC2999'),
  ('group', 'body', None, 'Ekuitas', None),
  ('amount', 'body', '3102', 'Modal Saham', 'AC3102'),
  ('amount', 'body', '3120', 'Tambahan Modal Disetor', 'AC3120'),
  ('amount', 'body', '3200', 'Laba Ditahan', 'AC3200'),
  ('amount', 'body', '3297', 'Pendapatan Komprehensif Lainnya', 'AC3297'),
  ('amount', 'body', '3298', 'Ekuitas Lainnya', 'AC3298'),
  ('body_total', 'body', '3299', 'Jumlah Ekuitas', 'AC3299'),
  ('footer_total', 'footer', '3300', 'Jumlah Liabilitas dan Ekuitas', 'AC3300')]]

_L1D_FIELDS = ('Amount', 'NonTaxableObject', 'SubjectToFinalTax', 'NonFinal',
               'PositiveFiscalCorrection', 'NegativeFiscalCorrection', 'FinalAmount')
_L1D_ORDER = ['Pendapatan:', '4021', '4013', '5020', '4300', '4199', 'Beban Usaha',
    *[str(code) for code in range(5311, 5323)], '5399', '5400', '4500',
    'Pendapatan Non Usaha', '4501', '4503', '4511', '4599', '4600',
    'Beban Non Usaha', '5405', '5409', '5421', '5499', '5500', '4700']
_L1D_HEADERS = [['KODE AKUN', 'NAMA AKUN', 'NILAI KOMERSIAL', 'TIDAK TERMASUK OBJEK PAJAK',
    'DIKENAKAN PPh BERSIFAT FINAL', 'OBJEK PAJAK TIDAK FINAL', 'PENYESUAIAN FISKAL POSITIF',
    'PENYESUAIAN FISKAL NEGATIF', 'KODE PENYESUAIAN FISKAL', 'NILAI FISKAL'],
    ['KODE AKUN', 'NAMA AKUN', 'NILAI'], ['KODE AKUN', 'NAMA AKUN', 'NILAI']]
_L1D_ASSET_CALC = ['1101', '1122', '1123', '1124', '1125', '-1131', '1181', '1200', '1401',
    '1421', '1423', '1422', '1499', '1501', '1521', '-1522', '1551', '1599',
    '1600', '-1601', '1611', '1651', '-1658', '1698']
_L1D_DEBT_CALC = ['2102', '2103', '2111', '2186', '2187', '2191', '2192', '2195',
    '2201', '2202', '2203', '2228', '2301', '2303', '2304', '2312', '2322', '2321', '2998']
_L1D_EQUITY_CALC = ['3102', '3120', '3200', '3297', '3298']
_L1D_UNCHANGED = {'4021', '4199', '4501', '4503', '4511', '4599'}
_L1D_SUBTOTALS = {'4300', '5400', '4500', '4600', '5500', '4700'}
_L1D_MASKS = {'NonTaxableObject', 'SubjectToFinalTax',
              'PositiveFiscalCorrection', 'NegativeFiscalCorrection'}


def _l1d_integer(value, *, nullish=False):
    if value is None and nullish:
        return 0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l1d_numeric_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l1d_numeric_precision')
    return int(number)


def _l1d_sum(values):
    result = 0
    for value in values:
        result += value
        if abs(result) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsafe_corporate_l1d_ordered_sum')
    return result


def project_l1d(form, *, migrated, headers, footer_spans, tax_type, locale, timezone_name):
    """Pure source transformation; caller must separately prove fresh lifetime.

    This helper cannot authorize a native record. It copies reported totals
    only after exact consumer reconciliation, preserving original source paths.
    """
    if (type(migrated) is not bool or tax_type != 'ICT_RCIT' or locale != 'id-ID'
            or timezone_name != 'Asia/Jakarta' or headers != _L1D_HEADERS
            or footer_spans != [[[1] * 10], [[1, 1, 1]], [[1, 1, 1]]]):
        raise _UnsupportedMetadata('unverified_corporate_l1d_structure')
    roots = {'L1dTreeData', 'L1dTreeTotalRow', 'L1dAssets', 'L1dLiabilitiesAndEquity'}
    if (not isinstance(form, dict) or set(form) != roots
            or not isinstance(form['L1dTreeData'], list) or not form['L1dTreeData']):
        raise _UnsupportedMetadata('unsupported_corporate_l1d_source_shape')
    codes = {value for value in _L1D_ORDER if value.isdecimal()}
    nodes, provenance = {}, []
    data_fields = {*_L1D_FIELDS, 'AccountCode', 'Description', 'CorrectionCode'}
    metadata_fields = {'BlockFields', 'RowOptions', 'StyleOptions'}

    def evidence(value, path, destination, rule='literal-source'):
        item = _evidence(value, ['L1dFormData', *path])
        provenance.append({**item, 'destination': destination, 'rule': rule})

    def walk(rows, path, depth=0):
        if depth > 32 or not isinstance(rows, list):
            raise _UnsupportedMetadata('unsupported_corporate_l1d_tree')
        for index, node in enumerate(rows):
            if (not isinstance(node, dict) or set(node) - {'Data', 'Expanded', 'Children'}
                    or not isinstance(node.get('Data'), dict)):
                raise _UnsupportedMetadata('unsupported_corporate_l1d_tree_node')
            data = node['Data']
            if (not data_fields <= set(data) or set(data) - data_fields - metadata_fields
                    or type(data.get('AccountCode')) is not str or data['AccountCode'] not in codes
                    or data['AccountCode'] in nodes or type(data.get('Description')) is not str):
                raise _UnsupportedMetadata('ambiguous_corporate_l1d_account')
            code = data['AccountCode']
            if code in _L1D_UNCHANGED:
                style = data.get('StyleOptions')
                if style is not None and (not isinstance(style, dict)
                        or set(style) - {'Style', 'DescriptionStyle'}
                        or any(value not in ('', None) for value in style.values())):
                    raise _UnsupportedMetadata('unverified_corporate_l1d_effective_style')
            for field in _L1D_FIELDS:
                _l1d_integer(data[field], nullish=True)
            masks = data.get('BlockFields')
            if (masks is not None and not isinstance(masks, dict)
                    or code in _L1D_UNCHANGED and isinstance(masks, dict)
                    and any(masks.get(key) is not None and type(masks[key]) is not bool
                            for key in _L1D_MASKS)):
                raise _UnsupportedMetadata('unsupported_corporate_l1d_mask')
            correction = data['CorrectionCode']
            if not (correction is None or type(correction) is str or
                    isinstance(correction, list) and len(correction) <= 10000
                    and all(type(value) is str for value in correction)):
                raise _UnsupportedMetadata('unsupported_corporate_l1d_correction_code')
            nodes[code] = (data, [*path, index, 'Data'])
            if len(nodes) > 10000:
                raise _UnsupportedMetadata('corporate_l1d_tree_budget')
            children = node.get('Children')
            if children is not None:
                walk(children, [*path, index, 'Children'], depth + 1)

    walk(form['L1dTreeData'], ['L1dTreeData'])
    if set(nodes) != codes:
        raise _UnsupportedMetadata('missing_corporate_l1d_account')
    body = []
    for code in _L1D_ORDER:
        if code not in codes:
            body.append(['', code, *([''] * 8)])
            continue
        data, path = nodes[code]
        row, destination = [code, data['Description']], {'table': 'L1-D/tree', 'row': len(body)}
        evidence(code, [*path, 'AccountCode'], {**destination, 'column': 0})
        evidence(data['Description'], [*path, 'Description'], {**destination, 'column': 1})
        masks = data.get('BlockFields') or {}
        if code in _L1D_UNCHANGED:
            for field in sorted(_L1D_MASKS):
                value = masks.get(field)
                provenance.append({'path': ['L1dFormData', *path, 'BlockFields', field],
                    'type': 'missing' if field not in masks else
                            'null' if value is None else 'boolean',
                    'value': value, 'destination': dict(destination), 'rule': 'captured-mask-truthiness'})
        for column, field in enumerate(_L1D_FIELDS[:6], 2):
            masked = field in _L1D_MASKS and (
                field in ('NonTaxableObject', 'SubjectToFinalTax') and code not in _L1D_UNCHANGED
                or code in _L1D_SUBTOTALS
                or code in _L1D_UNCHANGED and masks.get(field) is True)
            row.append('' if masked or data[field] is None else _number(data[field], 0, locale=locale))
            evidence(data[field], [*path, field], {**destination, 'column': column},
                     'source-mask' if masked else 'angular-number-1.0-0-id')
        correction = data['CorrectionCode']
        row.append('; '.join(correction) if isinstance(correction, list) else correction or '')
        if isinstance(correction, list):
            for index, value in enumerate(correction):
                evidence(value, [*path, 'CorrectionCode', index], {**destination, 'column': 8})
        else:
            evidence(correction, [*path, 'CorrectionCode'], {**destination, 'column': 8})
        row.append('' if data['FinalAmount'] is None else _number(data['FinalAmount'], 0, locale=locale))
        evidence(data['FinalAmount'], [*path, 'FinalAmount'], {**destination, 'column': 9})
        body.append(row)
    reported = form['L1dTreeTotalRow']
    if (not isinstance(reported, dict) or not set(_L1D_FIELDS) <= set(reported)
            or set(reported) - data_fields - metadata_fields):
        raise _UnsupportedMetadata('unsupported_corporate_l1d_tree_totals')
    footer = ['4800', 'Laba (Rugi) Sebelum Pajak']
    for field in _L1D_FIELDS:
        value = _l1d_integer(reported[field])
        if not migrated and value != _l1d_sum(
                [_l1d_integer(nodes[code][0][field], nullish=True) for code in ('4500', '4700')]):
            raise _UnsupportedMetadata('unreconciled_corporate_l1d_tree_total')
        footer.append(_number(reported[field], 0, locale=locale))
        evidence(reported[field], ['L1dTreeTotalRow', field], {'table': 'L1-D/tree', 'footer': 0},
                 'migrated-reported-total' if migrated else 'reconciled-reported-total')
    footer.insert(8, '')

    def table(index, rows, foot):
        return {'name': ['L1-D/tree', 'L1-D/assets', 'L1-D/liabilities-equity'][index],
            'headers': list(headers[index]), 'rows': rows + [foot], 'footer': [foot],
            'footer_spans': deepcopy(footer_spans[index]), 'body_row_count': len(rows),
            'source_total': len(rows), 'complete': True, 'source_structure': {'form': 'L1-D',
                'component': f'rsh-citr-l1d-grid{index + 1}',
                'groups': ['A. LAPORAN LABA RUGI' if index == 0 else 'B. LAPORAN POSISI KEUANGAN']}}

    tables = [table(0, body, footer)]
    for index, root in enumerate(('L1dAssets', 'L1dLiabilitiesAndEquity'), 1):
        data = form[root]
        descriptors = _L1D_BALANCE_ROWS[index - 1]
        expected = {entry[4] for entry in descriptors if entry[4] is not None}
        if not isinstance(data, dict) or set(data) != expected:
            raise _UnsupportedMetadata('unsupported_corporate_l1d_balance_source')
        values = {key: _l1d_integer(value, nullish=True) for key, value in data.items()}
        calculations = [('AC1700', _L1D_ASSET_CALC)] if index == 1 else [
            ('AC2999', _L1D_DEBT_CALC), ('AC3299', _L1D_EQUITY_CALC),
            ('AC3300', ['2999', '3299'])]
        for total, operands in calculations:
            computed = _l1d_sum([(-1 if code.startswith('-') else 1) * values['AC' + code.lstrip('-')]
                                 for code in operands])
            if _l1d_integer(data[total]) != computed:
                raise _UnsupportedMetadata('unreconciled_corporate_l1d_balance_total')
        rows, foot = [], None
        for _, location, code, caption, key in descriptors:
            row = [code or '', caption, '' if key is None or data[key] is None
                   else _number(data[key], 0, locale=locale)]
            if key is not None:
                evidence(data[key], [root, key], {'table': f'L1-D/grid{index + 1}',
                    'footer': 0} if location == 'footer' else {'table': f'L1-D/grid{index + 1}',
                    'row': len(rows), 'column': 2}, 'reconciled-reported-total' if key in
                    {total for total, _ in calculations} else 'angular-number-1.0-0-id')
            if location == 'footer':
                foot = row
            else:
                rows.append(row)
        tables.append(table(index, rows, foot))
    return {'tables': tables, 'provenance': provenance}


_L3_ROOT = 'ListIncomeTaxWithheldByOtherParties'
_L3_OWNERS = ('rsh-citr-l3-grid1', 'rshshr-citr-l3-grid2')
_L3_GROUPS = ('A. PENGHASILAN DARI LUAR NEGERI', 'B. PPh YANG DIPOTONG/DIPUNGUT PIHAK LAIN')
_L3_HEADERS = [['NO.', 'PEMOTONG PAJAK / NAMA', 'PEMOTONG PAJAK / NEGARA',
    'TANGGAL TRANSAKSI/PEMBAYARAN PPh', 'JENIS PENGHASILAN', 'PENGHASILAN NETO (RUPIAH)',
    'PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI / NILAI (Rp)',
    'PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI / MATA UANG',
    'PPh YANG DIBAYAR/DIPOTONG/TERUTANG DI LUAR NEGERI / NILAI DALAM MATA UANG ASING',
    'JUMLAH KREDIT PAJAK YANG DAPAT DIPERHITUNGKAN (Rp)'],
    ['NO.', 'NAMA PEMOTONG/PEMUNGUT', 'NPWPW PEMOTONG/PEMUNGUT', 'Jenis Pajak',
     'DASAR PENGENAAN PAJAK (Rupiah)', 'PPH YANG DIPOTONG/DIPUNGUT (Rupiah)',
     'BUKTI POTONG/SSP/SSPCP - NOMOR', 'BUKTI POTONG/SSP/SSPCP - TANGGAL']]
_L3_SCALARS = ('OverseasTotalNetIncome', 'OverseasTotalTaxPayable', 'OverseasTotalTaxCredit',
    'OverseasRefundPreviousYear', 'OverseasTotalCalculatedCurrentYear', 'OtherPartiesTotalTaxBase',
    'OtherPartiesIncomeTaxWithheld', 'OtherPartiesIncomeTaxWithheldUsd',
    'OtherPartiesOverseasIncomeTax', 'OtherPartiesTotalCredit', 'OtherPartiesTotalCreditUsd')
_L3_A_FIELDS = ('Name', 'CountryCode', 'DateOfTransaction', 'IncomeCode', 'NetIncome',
    'PayableRupiah', 'PayableCurrency', 'AmountForeignCurrency', 'CreditCalculated')
_L3_B_FIELDS = ('Name', 'TIN', 'TaxType', 'TaxBase', 'IncomeTax',
    'WithholdingSlipsNumber', 'WithholdingSlipsDate')
_L3_LABELS = ('COUNTRY_CODE', 'CURRENCY', 'FOREIGN_INCOME_TYPE_CIT', 'TAX_TYPE_BY_OTHER_PARTIES')
_L3_CAPTIONS = (
    'PENGEMBALIAN/PENGURANGAN PAJAK PENGHASILAN LUAR NEGERI (PASAL 24) YANG TELAH DIKREDITKAN UNTUK TAHUN SEBELUMNYA',
    'JUMLAH PAJAK PENGHASILAN YANG DIBAYAR DI LUAR NEGERI YANG DAPAT DIPERHITUNGKAN DALAM TAHUN BERJALAN')


def _l3_integer(value, *, nullish=False):
    if value is None and nullish:
        return 0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l3_number_precision')
    return int(number)


def _l3_sum(values):
    result = 0
    for value in values:
        result += value
        if abs(result) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsafe_corporate_l3_ordered_sum')
    return result


def _l3_date(value, *, offline=False):
    if value is None or offline and value == '':
        return ''
    if type(value) is not str or not re.fullmatch(
            r'[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]'
            r'(?:\.[0-9]{1,3})?Z)?', value):
        raise _UnsupportedMetadata('unsupported_corporate_l3_date')
    try:
        date = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if not 1970 <= date.year <= 2100:
            raise ValueError('Unreviewed date range')
        date = date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date
        return date.astimezone(timezone(timedelta(hours=7))).strftime('%d-%m-%Y')
    except (ValueError, OverflowError):
        raise _UnsupportedMetadata('unsupported_corporate_l3_date') from None


def project_l3(form, *, pages, footer_payload, headers, footer_spans, tax_type, locale,
               timezone_name, labels):
    """Pure consumer projection; callers must separately prove every packet/owner.

    Normalized page bounds are metadata, never original business identifiers.
    This helper grants no native eligibility or reference/footer transport access.
    """
    spans = [[[1, 4, 1, 1, 2, 1]], [[4, 1, 1, 2]] * 3]
    if (tax_type != 'ICT_RCIT' or locale != 'id-ID' or timezone_name != 'Asia/Jakarta'
            or headers != _L3_HEADERS or footer_spans != spans
            or not isinstance(form, dict) or set(form) != {'IncomeOverseas', *_L3_SCALARS}
            or not isinstance(labels, dict) or set(labels) != set(_L3_LABELS)
            or any(not isinstance(labels[k], dict) for k in _L3_LABELS)):
        raise _UnsupportedMetadata('unverified_corporate_l3_source_structure')
    overseas = [] if form['IncomeOverseas'] is None else form['IncomeOverseas']
    if not isinstance(overseas, list) or len(overseas) > 100000:
        raise _UnsupportedMetadata('unsupported_corporate_l3_overseas_body')
    if (not isinstance(footer_payload, dict) or set(footer_payload) != {'TaxBase', 'IncomeTax', 'IncomeTaxUsd'}
            or not isinstance(pages, list) or not 1 <= len(pages) <= 1000):
        raise _UnsupportedMetadata('missing_corporate_l3_footer_or_pages')
    provenance, arows, brows = [], [], []

    def evidence(value, path, destination, *, source='current', page_index=None, rule='literal-source'):
        item = {**_evidence(value, path), 'source': source, 'destination': destination, 'rule': rule}
        if page_index is not None:
            item['page_index'] = page_index
        provenance.append(item)

    def text(value):
        if value is None:
            return ''
        if type(value) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l3_text')
        return value

    def label(value, kind, *, offline=False):
        if offline and (value is None or type(value) is str and value == ''):
            return ''
        if (type(value) is not str or not value or type(labels[kind].get(value)) is not str
                or not labels[kind][value].strip()):
            raise _UnsupportedMetadata('missing_corporate_l3_reference_label')
        return labels[kind][value]

    def number(value, fraction=0):
        _l3_integer(value)
        return _number(value, fraction, locale=locale)

    for field in _L3_SCALARS:
        _l3_integer(form[field], nullish=True)
        evidence(form[field], [_L3_ROOT, field], {'control': field})
    sums = []
    for field, reported in zip(('NetIncome', 'PayableRupiah', 'CreditCalculated'), _L3_SCALARS[:3]):
        if any(not isinstance(row, dict) or set(row) != set(_L3_A_FIELDS) for row in overseas):
            raise _UnsupportedMetadata('unsupported_corporate_l3_overseas_row')
        total = _l3_sum(_l3_integer(row[field]) for row in overseas)
        if _l3_integer(form[reported]) != total:
            raise _UnsupportedMetadata('unreconciled_corporate_l3_overseas_total')
        sums.append(total)
    foreign_credit = _l3_sum([sums[2], -_l3_integer(form['OverseasRefundPreviousYear'], nullish=True)])
    for index, row in enumerate(overseas):
        arows.append([str(index + 1), text(row['Name']), label(row['CountryCode'], 'COUNTRY_CODE', offline=True),
            _l3_date(row['DateOfTransaction'], offline=True), label(row['IncomeCode'], 'FOREIGN_INCOME_TYPE_CIT', offline=True),
            number(row['NetIncome']), number(row['PayableRupiah']), label(row['PayableCurrency'], 'CURRENCY', offline=True),
            number(row['AmountForeignCurrency'], 2), number(row['CreditCalculated'])])
        for column, field in enumerate(_L3_A_FIELDS, 1):
            evidence(row[field], [_L3_ROOT, 'IncomeOverseas', index, field],
                     {'table': 'L3/overseas', 'row': index, 'column': column},
                     rule='bound-reference-label' if field in ('CountryCode', 'IncomeCode', 'PayableCurrency')
                     else 'date-id-jakarta' if field == 'DateOfTransaction'
                     else 'number-id-fraction-2' if field == 'AmountForeignCurrency'
                     else 'number-id-fraction-0' if field in ('NetIncome', 'PayableRupiah', 'CreditCalculated')
                     else 'literal-source')
    for field, column in zip(_L3_SCALARS[:3], (5, 6, 9)):
        evidence(form[field], [_L3_ROOT, field], {'table': 'L3/overseas', 'footer': 0, 'column': column},
                 rule='reconciled-model-ordered-sum')
    total = None
    for page_index, page in enumerate(pages):
        if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'total', 'data'}
                or any(type(page[k]) is not int for k in ('offset', 'rows', 'total'))
                or page['rows'] not in (10, 25, 50, 100, 250, 500)
                or not 0 <= page['total'] <= 100000 or page['offset'] != len(brows)
                or page['offset'] > page['total'] or not isinstance(page['data'], list)
                or len(page['data']) != min(page['rows'], page['total'] - page['offset'])
                or total is not None and total != page['total']
                or page_index and page['offset'] == page['total']):
            raise _UnsupportedMetadata('incomplete_corporate_l3_pages')
        total = page['total']
        for local_index, row in enumerate(page['data']):
            if not isinstance(row, dict) or set(row) != {'RecordId', *_L3_B_FIELDS}:
                raise _UnsupportedMetadata('unsupported_corporate_l3_domestic_row')
            text(row['RecordId'])
            brows.append([str(local_index + 1), text(row['Name']), text(row['TIN']),
                label(row['TaxType'], 'TAX_TYPE_BY_OTHER_PARTIES'), number(row['TaxBase']), number(row['IncomeTax']),
                text(row['WithholdingSlipsNumber']), _l3_date(row['WithholdingSlipsDate'])])
            evidence(row['RecordId'], ['Data', local_index, 'RecordId'],
                {'table': 'L3/domestic', 'row': len(brows) - 1}, source='grid', page_index=page_index,
                rule='non-displayed-row-key')
            for column, field in enumerate(_L3_B_FIELDS, 1):
                evidence(row[field], ['Data', local_index, field],
                    {'table': 'L3/domestic', 'row': len(brows) - 1, 'column': column}, source='grid', page_index=page_index,
                    rule='bound-reference-label' if field == 'TaxType' else 'date-id-jakarta'
                    if field == 'WithholdingSlipsDate' else 'number-id-fraction-0'
                    if field in ('TaxBase', 'IncomeTax') else 'literal-source')
    if len(brows) != total:
        raise _UnsupportedMetadata('incomplete_corporate_l3_pages')
    amounts = {key: _l3_integer(value, nullish=True) for key, value in footer_payload.items()}
    credit = _l3_sum([foreign_credit, amounts['IncomeTax']])
    _l3_sum([foreign_credit, amounts['IncomeTaxUsd']])  # The same callback writes the hidden USD total.
    for field, value in footer_payload.items():
        destination = ({'table': 'L3/domestic', 'footer': 0, 'column': 4 if field == 'TaxBase' else 5}
                       if field != 'IncomeTaxUsd' else {'hidden_control': 'OtherPartiesIncomeTaxWithheldUsd'})
        evidence(value, [field], destination, source='footer', rule='captured-footer-nullish-zero')
    for footer_index in (1, 2):
        destination = {'table': 'L3/domestic', 'footer': footer_index, 'column': 5}
        for index, row in enumerate(overseas):
            evidence(row['CreditCalculated'], [_L3_ROOT, 'IncomeOverseas', index, 'CreditCalculated'],
                     destination, rule='credit-sum-minus-refund')
        evidence(form['OverseasRefundPreviousYear'], [_L3_ROOT, 'OverseasRefundPreviousYear'],
                 destination, rule='credit-sum-minus-refund')
        if footer_index == 2:
            evidence(footer_payload['IncomeTax'], ['IncomeTax'], destination, source='footer',
                     rule='overseas-model-plus-footer-income-tax')
    def render(value):
        return _number(str(value), 0, locale=locale)

    afooter = [['', 'JUMLAH', number(form[_L3_SCALARS[0]]), number(form[_L3_SCALARS[1]]),
                '', number(form[_L3_SCALARS[2]])]]
    bfooter = [['JUMLAH', render(amounts['TaxBase']), render(amounts['IncomeTax']), ''],
        ['KREDIT PAJAK LUAR NEGERI', '', render(foreign_credit), ''], ['JUMLAH KREDIT PAJAK', '', render(credit), '']]
    tables = []
    for index, (body, footer) in enumerate(((arows, afooter), (brows, bfooter))):
        tables.append({'name': ('L3/overseas', 'L3/domestic')[index], 'headers': list(headers[index]),
            'rows': body + footer, 'footer': footer, 'footer_spans': deepcopy(spans[index]),
            'body_row_count': len(body), 'source_total': len(body), 'complete': True})
    fields = [{'field': field, 'label': caption, 'value': '' if form[field] is None else number(form[field]),
               'group': 'A. PENGHASILAN DARI LUAR NEGERI'}
              for field, caption in zip(_L3_SCALARS[3:5], _L3_CAPTIONS)]
    return {'tables': tables, 'fields': fields, 'provenance': provenance}


def _apply_l3(binding, section, observed_forms, *, root, payload, record, event,
              reference_packets, auxiliary_packets):
    proof = binding['projection']
    if (not isinstance(proof, dict)
            or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
            or proof['kind'] != 'corporate-l3-v1' or proof['builds'] != L3_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[_L3_ROOT]]
            or binding.get('grids', []) or event.get('component_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l3_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    main = root.get('MainFormData')
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or not isinstance(main, dict)
            or any(type(value) is not _CorporateNumber or _decimal(value) != 1
                   for value in (payload.get('IsIncomeTaxOverseas'), main.get('IsIncomeTaxOverseas')))):
        raise _UnsupportedMetadata('unverified_corporate_l3_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l3_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l3_previous_encoding')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l3_previous_shape')
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 2:
        raise _UnsupportedMetadata('unverified_corporate_l3_table_catalog')
    for index, table in enumerate(tables):
        structure = {'form': 'L3', 'component': _L3_OWNERS[index], 'groups': [_L3_GROUPS[index]]}
        if (not isinstance(table, dict)
                or set(table) != {'component', 'source_structure', 'headers', 'footer_spans'}
                or table['component'] != structure['component'] or table['source_structure'] != structure):
            raise _UnsupportedMetadata('unverified_corporate_l3_grid_owner')
    responses, dependencies = binding.get('responses'), binding.get('dependencies')
    footer_request = {'ReturnSheetRecordId': record['record_id']}
    if (not isinstance(responses, list) or len(responses) != 1
            or not isinstance(responses[0], dict) or set(responses[0]) != {'name', 'endpoint', 'requests'}
            or responses[0]['name'] != 'L3/domestic' or responses[0]['endpoint'] != CORPORATE_L3_GRID_URL
            or dependencies != [{'endpoint': CORPORATE_L3_FOOTER_URL, 'request_json': footer_request}]):
        raise _UnsupportedMetadata('unverified_corporate_l3_auxiliary_binding')
    requests = responses[0]['requests']
    if not isinstance(requests, list) or not 1 <= len(requests) <= 1000:
        raise _UnsupportedMetadata('missing_corporate_l3_page_requests')
    for request in requests:
        if (not isinstance(request, dict) or set(request) != {'ReturnSheetRecordId', 'Language',
                'First', 'Rows', 'SortField', 'SortOrder', 'Filters', 'LanguageId'}
                or request['ReturnSheetRecordId'] != record['record_id']
                or request['Language'] != 'id-ID' or request['LanguageId'] != 'id-ID'
                or type(request['First']) is not int or request['First'] < 0
                or type(request['Rows']) is not int or request['Rows'] != 10
                or request['SortField'] != 'WithholdingSlipsDate'
                or type(request['SortOrder']) is not int or request['SortOrder'] != 1
                or request['Filters'] != []):
            raise _UnsupportedMetadata('unsupported_corporate_l3_page_request')
    requests = sorted(requests, key=lambda value: value['First'])
    page_sources, pages, expected = [], [], set()
    for request in requests:
        key = (CORPORATE_L3_GRID_URL, _corporate_request_key(request))
        expected.add(key)
        packet = auxiliary_packets.get(key)
        source = packet['payload'] if packet is not None else None
        if not isinstance(source, dict) or set(source) != {'Data', 'TotalRecords'}:
            raise _UnsupportedMetadata('unsupported_corporate_l3_page_payload')
        pages.append({'offset': request['First'], 'rows': request['Rows'],
                      'total': _corporate_integer(source['TotalRecords']), 'data': source['Data']})
        page_sources.append(packet['event'])
    footer_key = (CORPORATE_L3_FOOTER_URL, _corporate_request_key(footer_request))
    expected.add(footer_key)
    if expected != {key for key in auxiliary_packets
                    if key[0] in (CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL)}:
        raise _UnsupportedMetadata('incomplete_corporate_l3_auxiliary_packets')
    footer = auxiliary_packets[footer_key]
    references = proof['references']
    if not isinstance(references, list) or len(references) != 4:
        raise _UnsupportedMetadata('missing_corporate_l3_reference_bindings')
    catalogs, sources, labels, seen_kinds = {}, {}, {}, set()
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or ref['method'] != 'GET' or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_l3_reference_binding')
        kind = next((kind for kind, url in CORPORATE_L3_REFERENCE_URLS.items() if url == ref['endpoint']), None)
        if kind is None or kind in seen_kinds:
            raise _UnsupportedMetadata('unsupported_corporate_l3_reference_binding')
        seen_kinds.add(kind)
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate L3 reference sequence is invalid or repeated')
        actual = {n for n, packet in reference_packets.items() if packet['event']['url'] == ref['endpoint']}
        if set(sequences) != actual or any(not reference_packets[n]['successful'] for n in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l3_catalog')
        source = reference_packets[sequences[0]]
        catalogs[kind] = _project_corporate_catalog(source['payload'], kind=kind,
            clock_interval=source['event'].get('clock_interval'))
        sources[kind], labels[kind] = source['event'], catalogs[kind]['lookups']
    result = project_l3(root.get(_L3_ROOT), pages=pages, footer_payload=footer['payload'],
        headers=[t['headers'] for t in tables], footer_spans=[t['footer_spans'] for t in tables],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'], labels=labels)
    for index, table in enumerate(result['tables']):
        table['source_structure'] = deepcopy(tables[index]['source_structure'])
    section['tables'], section['fields'] = result['tables'], result['fields']
    label_fields = {'CountryCode': 'COUNTRY_CODE', 'PayableCurrency': 'CURRENCY',
                    'IncomeCode': 'FOREIGN_INCOME_TYPE_CIT', 'TaxType': 'TAX_TYPE_BY_OTHER_PARTIES'}
    for entry in tuple(result['provenance']):
        source = (page_sources[entry['page_index']] if entry['source'] == 'grid'
                  else footer['event'] if entry['source'] == 'footer' else event)
        entry.update(response_sequence=source['sequence'],
                     container=['Payload', 'CurrentFormData'] if source is event else ['Payload'])
        kind = label_fields.get(entry['path'][-1]) if entry['rule'] == 'bound-reference-label' else None
        if kind is not None and entry['value'] in catalogs[kind]['selected']:
            result['provenance'].append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                'destination': deepcopy(entry['destination'])})
    for kind, catalog in catalogs.items():
        result['provenance'].extend({**entry, 'response_sequence': sources[kind]['sequence'],
            'container': ['Payload'], 'destination': {'table': 'L3', 'reference': kind}}
            for entry in catalog['provenance'])
    return {'form': 'L3', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


# Active L11-A consumers in the pinned corporate build; no taxpayer defaults.
_L11A_ROOT = 'L11AFormData'
_L11A_COSTS = ('ResidencyCost', 'HealthServiceCost', 'EducationCost', 'WorshipCost',
               'TransportationCost', 'SportsCost')
_L11A_RECAP = ('LocationAddress', 'NumberOfDecreeOfSpecificAreasDetermination',
    'DateOfDecreeOfSpecificAreasDetermination', 'NumberOfDecreeOfExtensificationOfSpecificAreasDetermination',
    'DateOfDecreeOfExtensificationOfSpecificAreasDetermination', *_L11A_COSTS, 'TotalAmountofCosts')
_L11A_CAPTIONS = ('Alamat Lokasi', 'Nomor Surat Keputusan Penetapan Daerah Tertentu',
    'Tanggal Surat Keputusan Penetapan Daerah Tertentu',
    'Nomor Surat Keputusan Perpanjangan Penetapan Daerah Tertentu',
    'Tanggal Surat Keputusan Perpanjangan Penetapan Daerah Tertentu',
    'Biaya yang dikeluarkan untuk tempat tinggal, termasuk perumahan untuk pegawai dan keluarganya',
    'Biaya yang dikeluarkan untuk pelayanan kesehatan',
    'Biaya yang dikeluarkan untuk pendidikan bagi pegawai dan keluarganya',
    'Biaya yang dikeluarkan untuk peribadatan',
    'Biaya yang dikeluarkan untuk pengangkutan bagi pegawai dan keluarganya',
    'Biaya yang dikeluarkan untuk olahraga bagi pegawai dan keluarganya, tidak termasuk golf, '
    'power boating, pacuan kuda, dan terbang layang', 'Jumlah Biaya yang dikeluarkan')
_L11A_GROUP = ('IV.B RINCIAN PENGGANTIAN ATAU IMBALAN DALAM BENTUK NATURA DAN/ATAU KENIKMATAN '
               'YANG DIBERIKAN BERKENAAN DENGAN PELAKSANAAN PEKERJAAN DI DAERAH TERTENTU')
_L11A_FIELDS = [
    ('Index', 'RecipientIdentityNumber', 'RecipientName', 'RecipientAddress', 'RecipientDate',
     'RecipientFormAndTypeOfPromotionCost', 'RecipientAmountOfPromotionCost', 'RecipientDescription',
     'IncomeTax', 'WithholdingSlipNumber'),
    ('EntertainmentDate', 'EntertainmentPlace', 'EntertainmentAddress', 'EntertainmentType',
     'EntertainmentAmount', 'PartnerName', 'PartnerPosition', 'PartnerCompanyName', 'PartnerTypeOfBusiness', 'Description'),
    ('Index', 'IdentityNumber', 'Name', 'Address', 'DebtCeiling', 'UncollectibleDebt', 'DeductionMethod', 'TypeOfFulfillment'),
    ('TypeOfTangibleAssets', 'YearOfAcquisition', 'AcquisitionValue', 'UpToPreviousYear', 'CurrentYear', 'UpToCurrentYear'),
    ('Index', 'IdentityNumber', 'Name', 'Address', 'AmountBeginning', 'AmountEnd', 'AmountInterestCurrentYear', 'Category')]
_L11A_HEADERS = [
    ['No.', 'NOMOR IDENTITAS PENERIMA', 'NAMA PENERIMA', 'ALAMAT PENERIMA', 'TANGGAL', 'JENIS BIAYA',
     'NILAI (Rp.)', 'KETERANGAN', 'PPh YANG DIPOTONG/DIPUNGUT (Rp.)Rp.)', 'NOMOR BUKTI POTONG'],
    ['TANGGAL PEMBERIAN ENTERTAINMENT', 'TEMPAT PEMBERIAN ENTERTAINMENT', 'ALAMAT PEMBERIAN ENTERTAINMENT',
     'JENIS PEMBERIAN ENTERTAINMENT', 'NILAI PEMBERIAN ENTERTAINMENTRp.)', 'NAMA RELASI USAHA',
     'JABATAN RELASI USAHA', 'NAMA PERUSAHAAN RELASI USAHA', 'JENIS USAHA RELASI USAHA', 'DESKRIPSI'],
    ['No.', 'NOMOR IDENTITAS', 'NAMA DEBITUR', 'ALAMAT', 'PLAFON PIUTANG',
     'PIUTANG YANG NYATA-NYATA TIDAK DAPAT DITAGIH', 'METODE PEMBEBANAN',
     'JENIS DOKUMEN PEMBUKTIAN PEMENUHAN PERSYARATAN'],
    ['NO.', 'JENIS HARTA BERWUJUD', 'TAHUN PEROLEHAN', 'NILAI PEROLEHAN', 'PENYUSUTAN / S.D. TAHUN LALU',
     'PENYUSUTAN / PENYUSUTAN TAHUN INI', 'PENYUSUTAN / S.D. TAHUN INI'],
    ['No.', 'NOMOR IDENTITAS', 'NAMA DEBITUR', 'ALAMAT', 'NILAI KREDIT KURANG LANCAR AWAL TAHUN BUKU',
     'NILAI KREDIT KURANG LANCAR AKHIR TAHUN BUKU', 'JUMLAH BUNGA PADA TAHUN BUKU (AKRUAL)', 'KATEGORI']]
_L11A_LABELS = {'RecipientFormAndTypeOfPromotionCost': 'TYPE_OF_PROMOTION_COST',
    'TypeOfTangibleAssets': 'TANGIBLE_ASSET_INCLUDING_BUILDINGS', 'Category': 'NON_PERFORMING_LOAN_CATEGORY',
    'DeductionMethod': 'DEDUCTION_METHOD', 'TypeOfFulfillment': 'TYPE_OF_FULFILLMENT'}
_L11A_MONEY = {'RecipientAmountOfPromotionCost', 'IncomeTax', 'EntertainmentAmount', 'DebtCeiling',
    'UncollectibleDebt', 'AcquisitionValue', 'UpToPreviousYear', 'CurrentYear', 'UpToCurrentYear',
    'AmountBeginning', 'AmountEnd', 'AmountInterestCurrentYear'}
_L11A_ENDPOINTS = {index: f'l11a-table-{index + 1}-grid' for index in (0, 1, 2, 4)}
_L11A_OWNERS = ('rshshr-citr-l11a-grid1', 'rshshr-citr-l11a-grid2', 'rshshr-citr-l11a-grid3',
                'rsh-citr-l11a-grid4', 'rshshr-citr-l11a-grid5')
_L11A_GROUPS = [
    ['I. DAFTAR NOMINATIF BIAYA PROMOSI DAN PENJUALAN, SERTA PENGGANTIAN ATAU IMBALAN DALAM BENTUK NATURA DAN/ATAU KENIKMATAN'],
    ['II. DAFTAR NOMINATIF BIAYA ENTERTAINMENT'],
    ['III. DAFTAR PIUTANG YANG NYATA-NYATA TIDAK DAPAT DITAGIH'],
    ['IV. RINCIAN BAGI WAJIB PAJAK PEMBERI NATURA DAN/ATAU KENIKMATAN',
     'IV.A DAFTAR SARANA DAN FASILITAS SERTA PENYUSUTANNYA'],
    ['V. DAFTAR DEBITUR NON-PERFORMING LOAN']]


def _apply_l11a(binding, section, observed_forms, *, root, payload, record, event,
                 reference_packets, auxiliary_packets):
    proof = binding['projection']
    if (not isinstance(proof, dict)
            or set(proof) != {'kind', 'builds', 'route', 'locale', 'timezone', 'tables', 'references'}
            or proof['kind'] != 'corporate-l11a-v1' or proof['builds'] != L11A_BUILD_DIGESTS
            or proof['route'] != event['frame_url'] or binding.get('paths') != [[_L11A_ROOT]]
            or binding.get('grids', []) or binding.get('dependencies', [])
            or event.get('component_lifetime') is None):
        raise _UnsupportedMetadata('unverified_corporate_l11a_semantic_binding')
    fields = record.get('source_fields', {})
    route = ORIGIN + '/returnsheets/id-ID/corporate-income-tax-return/' + '/'.join(
        str(value) for value in (fields.get('TaxpayerAggregateIdentifier'), record['record_id'],
                                fields.get('TaxTypeCode'), fields.get('AggregateIdentifier'))) + '?view=true'
    literal = record.get('meta', {}).get('Model SPT')
    model = ('NORMAL' if literal == 'Normal' else 'AMENDMENT'
             if isinstance(literal, str) and re.fullmatch(r'Amendment [0-9]{3}', literal) else None)
    main = root.get('MainFormData')
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
            or payload.get('ReturnSheetStatusCode') != 'SUBMITTED' or model is None
            or payload.get('ReturnSheetModel') != model or fields.get('ReturnSheetModel') != literal
            or 'Induk' not in [f['name'] for f in observed_forms[:observed_forms.index(binding)]]
            or not isinstance(main, dict)
            or any(type(value) is not _CorporateNumber or _decimal(value) != 1
                   for value in (payload.get('IsDeclareEntertainmentExpense'),
                                 main.get('IsDeclareEntertainmentExpense')))):
        raise _UnsupportedMetadata('unverified_corporate_l11a_submitted_lifecycle')
    if 'PreviousFormData' not in payload:
        raise _UnsupportedMetadata('missing_corporate_l11a_previous_encoding')
    previous = payload['PreviousFormData']
    if previous is not None:
        if type(previous) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11a_previous_encoding')
        previous = _corporate_json(previous)
        if previous is not None and not isinstance(previous, dict):
            raise _UnsupportedMetadata('unsupported_corporate_l11a_previous_shape')
    previous_form = previous.get(_L11A_ROOT) if previous is not None else None
    tables = proof['tables']
    if not isinstance(tables, list) or len(tables) != 5:
        raise _UnsupportedMetadata('unverified_corporate_l11a_table_catalog')
    for index, table in enumerate(tables):
        structure = {'form': 'L11-A', 'component': _L11A_OWNERS[index], 'groups': _L11A_GROUPS[index]}
        if (not isinstance(table, dict)
                or set(table) != {'component', 'source_structure', 'headers', 'footer_spans'}
                or table['component'] != structure['component'] or table['source_structure'] != structure):
            raise _UnsupportedMetadata('unverified_corporate_l11a_grid_owner')
    responses = binding.get('responses')
    if not isinstance(responses, list) or len(responses) != 4:
        raise _UnsupportedMetadata('unverified_corporate_l11a_auxiliary_binding')
    page_sources, pages, expected = {}, {}, set()
    for response in responses:
        if (not isinstance(response, dict) or set(response) != {'name', 'endpoint', 'requests'}
                or response['endpoint'] not in CORPORATE_L11A_GRID_URLS):
            raise _UnsupportedMetadata('unverified_corporate_l11a_auxiliary_binding')
        endpoint = response['endpoint'].rsplit('/', 1)[-1]
        if response['name'] != 'L11-A/' + endpoint or endpoint in pages:
            raise _UnsupportedMetadata('unverified_corporate_l11a_auxiliary_binding')
        requests = response['requests']
        if not isinstance(requests, list) or not 1 <= len(requests) <= 1000:
            raise _UnsupportedMetadata('missing_corporate_l11a_page_requests')
        for request in requests:
            if (not isinstance(request, dict) or set(request) != {'ReturnSheetRecordId',
                    'First', 'Rows', 'SortField', 'SortOrder', 'Filters', 'LanguageId'}
                    or request['ReturnSheetRecordId'] != record['record_id']
                    or request['LanguageId'] != 'id-ID' or type(request['First']) is not int
                    or request['First'] < 0 or type(request['Rows']) is not int or request['Rows'] != 10
                    or request['SortField'] != '' or type(request['SortOrder']) is not int
                    or request['SortOrder'] != 1 or request['Filters'] != []):
                raise _UnsupportedMetadata('unsupported_corporate_l11a_page_request')
        pages[endpoint], page_sources[endpoint] = [], []
        for request in sorted(requests, key=lambda value: value['First']):
            key = (response['endpoint'], _corporate_request_key(request))
            expected.add(key)
            packet = auxiliary_packets.get(key)
            source = packet['payload'] if packet is not None else None
            if not isinstance(source, dict) or set(source) != {'Data', 'TotalRecords'}:
                raise _UnsupportedMetadata('unsupported_corporate_l11a_page_payload')
            pages[endpoint].append({'offset': request['First'], 'rows': request['Rows'],
                'total': _corporate_integer(source['TotalRecords']), 'data': source['Data']})
            page_sources[endpoint].append(packet['event'])
    if expected != {key for key in auxiliary_packets if key[0] in CORPORATE_L11A_GRID_URLS}:
        raise _UnsupportedMetadata('incomplete_corporate_l11a_auxiliary_packets')
    references = proof['references']
    if not isinstance(references, list) or len(references) not in (4, 5):
        raise _UnsupportedMetadata('missing_corporate_l11a_reference_bindings')
    catalogs, sources = {}, {}
    urls = set()
    for ref in references:
        if (not isinstance(ref, dict) or set(ref) != {'endpoint', 'method', 'sequences'}
                or type(ref['endpoint']) is not str or ref['endpoint'] in urls
                or ref['method'] != 'GET' or not isinstance(ref['sequences'], list) or not ref['sequences']):
            raise _UnsupportedMetadata('unsupported_corporate_l11a_reference_binding')
        kinds = CORPORATE_REFERENCE_REQUESTS.get(ref['endpoint'])
        if kinds is None or any(kind not in CORPORATE_L11A_REFERENCE_URLS or kind in catalogs for kind in kinds):
            raise _UnsupportedMetadata('unsupported_corporate_l11a_reference_binding')
        urls.add(ref['endpoint'])
        sequences = ref['sequences']
        if any(type(n) is not int or n <= 0 for n in sequences) or len(set(sequences)) != len(sequences):
            raise JsonSafetyError('Corporate L11-A reference sequence is invalid or repeated')
        actual = {n for n, packet in reference_packets.items() if packet['event']['url'] == ref['endpoint']}
        if set(sequences) != actual or any(not reference_packets[n]['successful'] for n in actual):
            raise _UnsupportedMetadata('missing_or_failed_corporate_l11a_catalog')
        source = reference_packets[sequences[0]]
        for kind in kinds:
            catalogs[kind] = _project_corporate_catalog(source['payload'], kind=kind, requested_types=kinds,
                clock_interval=source['event'].get('clock_interval'))
            sources[kind] = source['event']
    if set(catalogs) != set(CORPORATE_L11A_REFERENCE_URLS):
        raise _UnsupportedMetadata('missing_corporate_l11a_catalogs')
    result = project_l11a(root.get(_L11A_ROOT), previous=previous_form, pages=pages,
        headers=[t['headers'] for t in tables], footer_spans=[t['footer_spans'] for t in tables],
        tax_type=fields.get('TaxTypeCode'), locale=proof['locale'], timezone_name=proof['timezone'],
        labels={kind: catalog['lookups'] for kind, catalog in catalogs.items()})
    for index, table in enumerate(result['tables']):
        table['source_structure'] = deepcopy(tables[index]['source_structure'])
    section['tables'], section['fields'] = result['tables'], result['fields']
    for entry in tuple(result['provenance']):
        source = (page_sources[entry['endpoint']][entry['page_index']] if entry['source'] == 'grid' else event)
        entry.update(response_sequence=source['sequence'],
                     container=['Payload', 'CurrentFormData'] if source is event else ['Payload'])
        kind = _L11A_LABELS.get(entry['path'][-1]) if entry['rule'] == 'bound-reference-description' else None
        if kind is not None and entry['value'] in catalogs[kind]['selected']:
            result['provenance'].append({**deepcopy(catalogs[kind]['selected'][entry['value']]),
                'response_sequence': sources[kind]['sequence'], 'container': ['Payload'],
                'destination': deepcopy(entry['destination'])})
    for kind, catalog in catalogs.items():
        result['provenance'].extend({**entry, 'response_sequence': sources[kind]['sequence'],
            'container': ['Payload'], 'destination': {'table': 'L11-A', 'reference': kind}}
            for entry in catalog['provenance'])
    return {'form': 'L11-A', 'kind': proof['kind'], 'builds': dict(proof['builds']),
            'route': proof['route'], 'values': result['provenance']}


def _l11a_integer(value, *, nullish=False):
    if value is None and nullish:
        return 0
    if type(value) is not _CorporateNumber:
        raise _UnsupportedMetadata('unsupported_corporate_l11a_number_type')
    number = _decimal(value)
    if abs(number) > _MAX_INTEGER or number != number.to_integral_value():
        raise _UnsupportedMetadata('unsupported_corporate_l11a_number_precision')
    return int(number)


def project_l11a(form, *, previous, pages, headers, footer_spans, tax_type, locale,
                  timezone_name, labels):
    """Pure current-only consumer; no native observation or transport admission."""
    if (previous is not None or tax_type != 'ICT_RCIT' or locale != 'id-ID'
            or timezone_name != 'Asia/Jakarta' or headers != _L11A_HEADERS
            or footer_spans != [[], [], [], [], []] or not isinstance(labels, dict)
            or set(labels) != set(_L11A_LABELS.values())
            or any(not isinstance(value, dict) for value in labels.values())):
        raise _UnsupportedMetadata('unverified_corporate_l11a_current_structure')
    if (not isinstance(form, dict) or set(form) != {'Facilities', 'Recapitulation'}
            or not isinstance(form['Recapitulation'], dict) or set(form['Recapitulation']) != set(_L11A_RECAP)
            or not isinstance(pages, dict) or set(pages) != set(_L11A_ENDPOINTS.values())):
        raise _UnsupportedMetadata('unsupported_corporate_l11a_source_shape')
    facilities = [] if form['Facilities'] is None else form['Facilities']
    if not isinstance(facilities, list) or len(facilities) > 10000:
        raise _UnsupportedMetadata('unsupported_corporate_l11a_facilities')
    provenance = []

    def evidence(value, path, destination, *, endpoint=None, page_index=None, rule='literal-source'):
        entry = _evidence(value, path)
        entry.update(source='current' if endpoint is None else 'grid', destination=destination, rule=rule)
        if endpoint is not None:
            entry.update(endpoint=endpoint, page_index=page_index)
        provenance.append(entry)

    def text(value):
        if value is None:
            return ''
        if type(value) is not str:
            raise _UnsupportedMetadata('unsupported_corporate_l11a_text')
        return value

    def number(value, fraction=0):
        if value is None:
            return ''
        _l11a_integer(value)
        return _number(value, fraction, locale=locale)

    def render(value, key):
        if key in _L11A_LABELS:
            choices = labels[_L11A_LABELS[key]]
            if (type(value) is not str or not value or value not in choices
                    or type(choices[value]) is not str or not choices[value].strip()):
                raise _UnsupportedMetadata('unbound_corporate_l11a_description')
            return choices[value], 'bound-reference-description'
        if key in _L11A_MONEY:
            return number(value), 'source-number-id/null-blank'
        if key in ('RecipientDate', 'EntertainmentDate'):
            return _l3_date(value), 'validated-iso/jakarta-dd-MM-yyyy'
        if key == 'PartnerName':
            if type(value) is _CorporateNumber:
                return number(value, 2), 'source-number-id-1.2-2'
            if type(value) is str and re.match(r'^(0[0-9]|1[0-9]|2[0-3]):[0-5][0-9]', value):
                raise _UnsupportedMetadata('unproved_corporate_l11a_time_like_name')
        return text(value), 'literal-string/null-blank'

    tables = []
    for table_index, keys in enumerate(_L11A_FIELDS):
        body, endpoint = [], _L11A_ENDPOINTS.get(table_index)
        if endpoint is None:
            source_pages = [(None, facilities)]
        else:
            declarations = pages[endpoint]
            if not isinstance(declarations, list) or not 1 <= len(declarations) <= 1000:
                raise _UnsupportedMetadata('missing_corporate_l11a_pages')
            source_pages, cursor, total, capacity = [], 0, None, None
            for page_index, page in enumerate(declarations):
                if (not isinstance(page, dict) or set(page) != {'offset', 'rows', 'total', 'data'}
                        or any(type(page[key]) is not int for key in ('offset', 'rows', 'total'))
                        or page['offset'] != cursor or page['rows'] not in (10, 25, 50)
                        or not 0 <= page['total'] <= 100000 or not isinstance(page['data'], list)):
                    raise _UnsupportedMetadata('unsupported_corporate_l11a_page')
                if total is None:
                    total, capacity = page['total'], page['rows']
                if (page['total'] != total or page['rows'] != capacity or page_index and cursor >= total
                        or len(page['data']) != min(capacity, total - cursor)):
                    raise _UnsupportedMetadata('incomplete_corporate_l11a_pages')
                source_pages.append((page_index, page['data']))
                cursor += len(page['data'])
            if cursor != total:
                raise _UnsupportedMetadata('incomplete_corporate_l11a_pages')
        for page_index, values in source_pages:
            for row_index, row in enumerate(values):
                expected = set(keys) | ({'RecordId'} if endpoint is not None else set())
                if not isinstance(row, dict) or set(row) != expected:
                    raise _UnsupportedMetadata('unsupported_corporate_l11a_row')
                path = (['Data', row_index] if endpoint is not None else [_L11A_ROOT, 'Facilities', row_index])
                if endpoint is not None:
                    if type(row['RecordId']) is not str or not row['RecordId']:
                        raise _UnsupportedMetadata('unsupported_corporate_l11a_row_id')
                    evidence(row['RecordId'], [*path, 'RecordId'], {'table': f'L11-A/grid{table_index + 1}',
                        'row': len(body), 'key': 'RecordId'}, endpoint=endpoint, page_index=page_index)
                rendered = [] if endpoint is not None else [str(row_index + 1)]
                for column, key in enumerate(keys, 0 if endpoint is not None else 1):
                    value, rule = render(row[key], key)
                    rendered.append(value)
                    evidence(row[key], [*path, key], {'table': f'L11-A/grid{table_index + 1}',
                        'row': len(body), 'column': column}, endpoint=endpoint, page_index=page_index, rule=rule)
                body.append(rendered)
        tables.append({'name': f'L11-A/grid{table_index + 1}', 'headers': list(headers[table_index]),
            'rows': body, 'footer': [], 'footer_spans': [], 'body_row_count': len(body),
            'source_total': len(body), 'complete': True})

    recap, total = form['Recapitulation'], 0
    for key in _L11A_COSTS:
        operand = _l11a_integer(recap[key], nullish=True)
        # PrimeNG keeps a signed-zero cost control distinct from Angular's
        # normalized number display. Refuse this unproved presentation branch.
        if recap[key] is not None:
            original = _decimal(recap[key])
            if original.is_zero() and original.is_signed():
                raise _UnsupportedMetadata('unproved_corporate_l11a_signed_zero_cost')
        total += operand
        if abs(total) > _MAX_INTEGER:
            raise _UnsupportedMetadata('unsafe_corporate_l11a_ordered_cost_sum')
    if _l11a_integer(recap['TotalAmountofCosts']) != max(0, total):
        raise _UnsupportedMetadata('unreconciled_corporate_l11a_total_costs')
    fields = []
    for key, caption in zip(_L11A_RECAP, _L11A_CAPTIONS):
        value = recap[key]
        if key in _L11A_COSTS or key == 'TotalAmountofCosts':
            display, rule = number(value), 'input-number-id/null-blank'
            if key == 'TotalAmountofCosts':
                rule = 'reconciled-six-cost-ordered-sum/final-nonnegative-clamp'
        elif key.startswith('DateOfDecree'):
            if type(value) is not str or not value:
                raise _UnsupportedMetadata('unsupported_corporate_l11a_decree_date')
            display, rule = _l3_date(value), 'validated-new-Date/jakarta-dd-MM-yyyy'
        else:
            display, rule = text(value), 'literal-input/null-blank'
        fields.append({'group': _L11A_GROUP, 'field': key, 'label': caption, 'value': display})
        evidence(value, [_L11A_ROOT, 'Recapitulation', key], {'field': key}, rule=rule)
    return {'tables': tables, 'fields': fields, 'provenance': provenance}
