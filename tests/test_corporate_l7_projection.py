"""Source-bound L7 values; synthetic fixtures, GitHub-runner-only execution."""
from copy import deepcopy
import importlib
import importlib.util

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from support_json_corpus import Number, wire


ROOT = 'CalculationOfFiscalLossCompensation'
BODY = 'FiscalNetProfitAndLossCompensation'
SUFFIXES = ('YearMinus4', 'YearMinus3', 'YearMinus2', 'YearMinus1', 'YearCurrent', 'YearNext')
HEADERS = [
    'NO.', 'LABA (RUGI) NETTO FISKAL / TAHUN/BAGIAN TAHUN PAJAK',
    'LABA (RUGI) NETTO FISKAL / NILAI (Rp)',
    *[f'KOMPENSASI KERUGIAN FISKAL / Y-{year} / NILAI (Rp)' for year in (4, 3, 2, 1)],
    'KOMPENSASI KERUGIAN FISKAL / 2025 / TAHUN PAJAK INI - NILAI (Rp)',
    'KOMPENSASI KERUGIAN FISKAL / Y+1 / TAHUN PAJAK BERJALAN - NILAI (Rp)',
]
SPANS = [[3, 1, 1, 1, 1, 1, 1]]


def raw_source():
    rows = [{'TaxYear': year, 'FiscalNetProfitIncome': Number(profit),
             **{'FiscalLossCompensation' + suffix: Number(str(100 * (index + 1)))
                for index, suffix in enumerate(SUFFIXES)}}
            for year, profit in (('02023', '12345'), ('2025', '0'))]
    return {BODY: rows,
        **{'TotalFiscalLossCompensation' + suffix: Number(str(200 * (index + 1)))
           for index, suffix in enumerate(SUFFIXES)}}


def source():
    return _corporate_json(wire(raw_source()))


def main(value=Number('1000')):
    return _corporate_json(wire({'NetIncomeBeforeTax': value}))


def project(form=None, *, main_form=None, period_year=Number('2025'), **overrides):
    spec = importlib.util.find_spec('coretax_corporate_projection')
    assert spec is not None, 'Missing source-bound corporate semantic projector'
    helper = getattr(importlib.import_module('coretax_corporate_projection'), 'project_l7', None)
    assert callable(helper), 'Missing reviewed L7 projection entrypoint'
    options = {'headers': list(HEADERS), 'footer_spans': deepcopy(SPANS),
               'tax_type': 'ICT_RCIT', 'locale': 'id-ID'}
    options.update(overrides)
    return helper(source() if form is None else form,
                  main_form=main() if main_form is None else main_form,
                  period_year=_corporate_json(wire(period_year)), **options)


def test_l7_headers_are_the_approved_reference_with_source_year_only():
    from openpyxl import load_workbook
    from pathlib import Path
    resource = Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx'
    workbook = load_workbook(resource)
    try:
        headers = [cell.value for cell in workbook['L7'][2]]
        assert headers[7] is None
        headers[7] = HEADERS[7]
        assert headers == HEADERS
    finally:
        workbook.close()


def test_l7_preserves_rows_literals_reported_totals_and_all_contributing_paths():
    form, original_main = source(), main()
    before, before_main = deepcopy(form), deepcopy(original_main)
    result = project(form, main_form=original_main)
    table = result['table']
    assert table['headers'] == HEADERS and table['footer_spans'] == SPANS
    assert table['rows'][:2] == [
        ['1', '02023', '12.345', '100', '200', '300', '400', '500', '600'],
        ['2', '2025', '1.000', '100', '200', '300', '400', '500', '600'],
    ]
    assert table['footer'] == [['JUMLAH', '200', '400', '600', '800', '1.000', '1.200']]
    assert table['rows'][2:] == table['footer']
    assert table['body_row_count'] == table['source_total'] == 2 and table['complete'] is True
    assert form == before and original_main == before_main
    evidence = result['provenance']
    for index, row in enumerate(form[BODY]):
        for key in row:
            assert any(entry['path'] == [ROOT, BODY, index, key] for entry in evidence)
    for suffix in SUFFIXES:
        assert any(entry['path'] == [ROOT, 'TotalFiscalLossCompensation' + suffix]
                   and entry['type'] == 'number' for entry in evidence)
    assert any(entry['path'] == [ROOT, BODY, 1, 'FiscalNetProfitIncome'] and entry['value'] == '0'
               for entry in evidence)
    assert any(entry['path'] == ['MainFormData', 'NetIncomeBeforeTax'] and entry['value'] == '1000'
               for entry in evidence)


@pytest.mark.parametrize('profit,expected', [(Number('0'), '1.000'), (Number('-5'), '-5'),
                                          (Number('1000'), '1.000'), (Number('77'), '77')])
def test_first_current_year_profit_follows_reviewed_submitted_main_input(profit, expected):
    form = source()
    form[BODY][1]['FiscalNetProfitIncome'] = _corporate_json(wire(profit))
    assert project(form)['table']['rows'][1][2] == expected


def test_l7_keeps_duplicates_and_only_first_current_year_row_receives_main_override():
    form = source()
    form[BODY] = [deepcopy(form[BODY][1]), deepcopy(form[BODY][1])]
    before = deepcopy(form)
    rows = project(form)['table']['rows']
    assert rows[0][1:] == ['2025', '1.000', '100', '200', '300', '400', '500', '600']
    assert rows[1][1:] == ['2025', '0', '100', '200', '300', '400', '500', '600']
    assert form == before and len(rows) == 3


def test_l7_empty_body_keeps_unsupported_main_callback_initialization_on_fallback():
    form = _corporate_json(wire({BODY: [], **{'TotalFiscalLossCompensation' + suffix: Number('0')
                                               for suffix in SUFFIXES}}))
    with pytest.raises(_UnsupportedMetadata):
        project(form)


@pytest.mark.parametrize('defect', ['reported-mismatch', 'missing-total', 'missing-body', 'unknown-root',
    'unknown-row', 'string-money', 'null-money', 'fractional-loss', 'unsafe-loss', 'bool-year',
    'invalid-year', 'negative-main', 'missing-main', 'wrong-currency', 'unknown-tax',
    'unknown-locale', 'changed-header-year', 'wrong-footer-span', 'no-current-year'])
def test_l7_unproved_source_or_structure_keeps_semantic_projection_unsupported(defect):
    form, parent, options = source(), main(), {}
    if defect == 'reported-mismatch':
        form['TotalFiscalLossCompensationYearMinus4'] = _corporate_json('999')
    elif defect == 'missing-total':
        del form['TotalFiscalLossCompensationYearMinus4']
    elif defect == 'missing-body':
        del form[BODY]
    elif defect == 'unknown-root':
        form['SYNTHETIC_UNREVIEWED_FIELD'] = '0009'
    elif defect == 'unknown-row':
        form[BODY][0]['SYNTHETIC_UNREVIEWED_FIELD'] = '0009'
    elif defect in ('string-money', 'null-money', 'fractional-loss', 'unsafe-loss'):
        form[BODY][0]['FiscalLossCompensationYearMinus4'] = {
            'string-money': '100', 'null-money': None, 'fractional-loss': _corporate_json('100.5'),
            'unsafe-loss': _corporate_json('9007199254740993')}[defect]
    elif defect == 'bool-year':
        form[BODY][0]['TaxYear'] = True
    elif defect == 'invalid-year':
        form[BODY][0]['TaxYear'] = '2023-extra'
    elif defect == 'negative-main':
        parent = main(Number('-1'))
    elif defect == 'missing-main':
        parent = {}
    elif defect in ('wrong-currency', 'unknown-tax'):
        options['tax_type'] = 'ICT_DCIT' if defect == 'wrong-currency' else 'SYNTHETIC_UNKNOWN'
    elif defect == 'unknown-locale':
        options['locale'] = 'en-US'
    elif defect == 'changed-header-year':
        options['headers'] = [value.replace('2025', '2024') for value in HEADERS]
    elif defect == 'wrong-footer-span':
        options['footer_spans'] = [[2, 2, 1, 1, 1, 1, 1]]
    elif defect == 'no-current-year':
        form[BODY][1]['TaxYear'] = '2024'
    with pytest.raises(_UnsupportedMetadata):
        project(form, main_form=parent, **options)
