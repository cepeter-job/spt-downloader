"""Source-bound corporate presentation with separately proved form branches."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import re

from coretax_json import (ORIGIN, CORPORATE_COUNTRY_REFERENCE_URL, JsonSafetyError,
                          _CorporateNumber, _UnsupportedMetadata, _corporate_json,
                          _select_reference_version)
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
    if (not isinstance(payload, list) or len(payload) != 1 or not isinstance(payload[0], dict)
            or payload[0].get('ReferenceDataType') != 'COUNTRY_CODE'
            or not isinstance(payload[0].get('Details'), list)):
        raise _UnsupportedMetadata('unsupported_corporate_country_catalog')
    catalog, groups, evidence = payload[0], {}, []
    if 'language' in catalog and catalog['language'] != 'id-ID':
        raise JsonSafetyError('Corporate country locale contradicts observed source')
    evidence.append(_evidence('COUNTRY_CODE', [0, 'ReferenceDataType']))
    descriptions = {}
    for index, row in enumerate(catalog['Details']):
        if (not isinstance(row, dict) or type(row.get('Code')) is not str or not row['Code']
                or type(row.get('CodeDescription')) is not str or not row['CodeDescription'].strip()):
            raise _UnsupportedMetadata('unsupported_corporate_country_description')
        if 'language' in row and row['language'] != 'id-ID':
            raise JsonSafetyError('Corporate country locale contradicts observed source')
        for key in ('ValidFrom', 'ValidTo'):
            if key in row and row[key] is not None and type(row[key]) is not str:
                raise _UnsupportedMetadata('unsupported_corporate_country_validity')
        groups.setdefault(row['Code'], []).append((index, row))
        for key in ('Code', 'CodeDescription', 'ValidFrom', 'ValidTo'):
            entry = (_evidence(row[key], [0, 'Details', index, key]) if key in row else
                     {'path': [0, 'Details', index, key], 'type': 'missing', 'value': None})
            evidence.append(entry)
            if key == 'CodeDescription':
                descriptions[index] = entry
    lookups, selected = {}, {}
    for code, candidates in groups.items():
        index, row, rule = _select_reference_version(candidates, clock_interval)
        lookups[code] = row['CodeDescription']
        entry = descriptions[index]
        entry['rule'] = 'reviewed-country-active-version:' + rule
        if clock_interval is not None and rule not in ('first-open-ended', 'only-version'):
            entry['clock_interval'] = dict(clock_interval)
        selected[code] = deepcopy(entry)
    return {'lookups': lookups, 'provenance': evidence, 'selected': selected}


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
    if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
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


def apply_projections(sections, observed_forms, *, root, payload, record, event, country_packets=None):
    """Replace only explicitly declared semantic sections after packet safety."""
    projected = []
    for binding, section in zip(observed_forms, sections):
        if 'projection' not in binding:
            continue  # Preserve old evidence-leaf captures and caller contracts.
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
        if (proof['route'] != route or record.get('source_status') != 'SPT Dilaporkan'
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
    data_fields = {*_L1D_FIELDS, 'AccountCode', 'Description', 'CorrectionCode', 'BlockFields'}

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
            if (not data_fields <= set(data) or set(data) - data_fields - {'RowOptions', 'StyleOptions'}
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
            masks = data['BlockFields']
            if (not isinstance(masks, dict) or set(masks) - _L1D_MASKS - {'CorrectionCode'}
                    or any(value is not None and type(value) is not bool for value in masks.values())):
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
        if code in _L1D_UNCHANGED:
            for field in sorted(_L1D_MASKS):
                value = data['BlockFields'].get(field)
                provenance.append({'path': ['L1dFormData', *path, 'BlockFields', field],
                    'type': 'missing' if field not in data['BlockFields'] else
                            'null' if value is None else 'boolean',
                    'value': value, 'destination': dict(destination), 'rule': 'captured-mask-truthiness'})
        for column, field in enumerate(_L1D_FIELDS[:6], 2):
            masked = field in _L1D_MASKS and (
                field in ('NonTaxableObject', 'SubjectToFinalTax') and code not in _L1D_UNCHANGED
                or code in _L1D_SUBTOTALS
                or code in _L1D_UNCHANGED and data['BlockFields'].get(field) is True)
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
            or set(reported) - data_fields - {'RowOptions', 'StyleOptions'}):
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
