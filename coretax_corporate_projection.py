"""Source-bound corporate presentation; currently the reviewed L7 branch only."""
import re

from coretax_json import (ORIGIN, JsonSafetyError, _CorporateNumber, _UnsupportedMetadata,
                          _corporate_json)
from coretax_masa_bindings import _decimal, _number, _evidence

CIT_SOURCE = ORIGIN + '/returnsheets/id-ID/525.ec1edffbb4a91d20.js'
MAIN_SOURCE = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
BUILD_DIGESTS = {
    CIT_SOURCE: 'fcd6d4a9244d6562a294675e802732562a9510621fbb9abbe651fa4de143048d',
    MAIN_SOURCE: '696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd',
}
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


def apply_projections(sections, observed_forms, *, root, payload, record, event):
    """Replace only explicitly declared semantic sections after packet safety."""
    projected = []
    for binding, section in zip(observed_forms, sections):
        if 'projection' not in binding:
            continue  # Preserve old evidence-leaf captures and caller contracts.
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
