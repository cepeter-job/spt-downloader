"""Source-bound L11-C contracts; synthetic fixtures, GitHub-runner execution."""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from support_json_corpus import Number, wire

ROOT = 'L11CFormData'
BODY = 'ForeignPrivateDebtReports'
AMOUNTS = (
    'DebtPrincipalBeginningOfYear', 'AdditionOfDebtPrincipal', 'SubstractionOfDebtPrincipal',
    'DebtPrincipalEndOfYear', 'AmountOfInterest', 'BorrowingCostOtherThanInterest',
)
TOTALS = (
    'TotalDebtPrincipalBeginningOfYear', 'TotalAdditionOfDebtPrincipal', 'TotalSubstractionOfDebtPrincipal',
    'TotalDebtPrincipalEndOfYear', 'TotalInterest', 'TotalBorrowingCostOtherThanInterest',
)
HEADERS = [
    'NO.', 'PEMBERI PINJAMAN / NAMA', 'PEMBERI PINJAMAN / ALAMAT',
    'PEMBERI PINJAMAN / NEGARA/YURISDIKSI', 'MATA UANG / KODE', 'MATA UANG / KURS AKHIR TAHUN',
    'POKOK UTANG (Rp) / AWAL TAHUN', 'POKOK UTANG (Rp) / MUTASI / PENAMBAHAN',
    'POKOK UTANG (Rp) / MUTASI / PENGURANGAN', 'POKOK UTANG (Rp) / AKHIR TAHUN',
    'JANGKA WAKTU PINJAMAN / Tanggal Mulai', 'JANGKA WAKTU PINJAMAN / Tanggal Jatuh Tempo',
    'BUNGA / TINGKAT (%)', 'BUNGA / JUMLAH (Rp)',
    'BIAYA TERKAIT PEROLEHAN PINJAMAN SELAIN BUNGA (Rp)', 'PERUNTUKAN PINJAMAN',
]
SPANS = [[1, 5, *([1] * 10)]]


def raw_source():
    row = dict(zip(AMOUNTS, map(Number, ('1000000', '200000', '50000', '1150000', '75000', '12500'))))
    row.update(NameOfCreditor='SYNTHETIC CREDITOR', AddressOfCreditor='00012 SYNTHETIC ADDRESS',
               CountryOfCreditor='SYN_COUNTRY_A', Currency='001', EndOfYearRate='00015000,00',
               LoanStartDate='2025-01-01T20:00:00.000Z', LoanDueDate='2026-12-31',
               InterestRate=Number('5'), LoanAllocation='SYNTHETIC ALLOCATION')
    return {BODY: [row, deepcopy(row)],
            **dict(zip(TOTALS, map(Number, ('2000000', '400000', '100000', '2300000', '150000', '25000'))))}


def source():
    return _corporate_json(wire(raw_source()))


def project(form=None, **overrides):
    helper = getattr(importlib.import_module('coretax_corporate_projection'), 'project_l11c', None)
    assert callable(helper), 'Missing reviewed L11-C source projection'
    options = {'headers': list(HEADERS), 'footer_spans': deepcopy(SPANS), 'tax_type': 'ICT_RCIT',
               'locale': 'id-ID', 'timezone_name': 'Asia/Jakarta',
               'country_labels': {'SYN_COUNTRY_A': 'SYNTHETIC COUNTRY LABEL'}}
    options.update(overrides)
    return helper(source() if form is None else form, **options)


def test_l11c_duplicate_source_rows_keep_literal_strings_and_independent_formats():
    original = source()
    before = deepcopy(original)
    result = project(original)
    table = result['table']
    expected = ['1', 'SYNTHETIC CREDITOR', '00012 SYNTHETIC ADDRESS', 'SYNTHETIC COUNTRY LABEL',
                '001', '00015000,00', '1.000.000', '200.000', '50.000', '1.150.000,00',
                '02-01-2025', '31-12-2026', '5,00', '75.000', '12.500', 'SYNTHETIC ALLOCATION']
    assert table['rows'][:2] == [expected, ['2', *expected[1:]]]
    assert table['body_row_count'] == table['source_total'] == 2
    assert table['headers'] == HEADERS and table['footer_spans'] == SPANS
    assert table['rows'][2:] == table['footer'] == [
        ['', 'JUMLAH', '2.000.000', '400.000', '100.000', '2.300.000,00', '', '', '', '150.000', '25.000', '']]
    assert original == before
    evidence = {tuple(item['path']): item for item in result['provenance']}
    assert evidence[(ROOT, BODY, 0, 'CountryOfCreditor')]['value'] == 'SYN_COUNTRY_A'
    assert evidence[(ROOT, BODY, 0, 'LoanStartDate')]['value'] == '2025-01-01T20:00:00.000Z'
    assert evidence[(ROOT, 'TotalDebtPrincipalEndOfYear')]['value'] == '2300000'


@pytest.mark.parametrize('body', [None, []])
def test_l11c_explicit_empty_body_requires_all_six_reported_zero_totals(body):
    form = _corporate_json(wire({BODY: body, **{key: Number('0') for key in TOTALS}}))
    table = project(form, country_labels={})['table']
    assert table['body_row_count'] == table['source_total'] == 0
    assert table['rows'] == table['footer'] == [
        ['', 'JUMLAH', '0', '0', '0', '0,00', '', '', '', '0', '0', '']]
    form[TOTALS[0]] = _corporate_json(wire(Number('1')))
    with pytest.raises(_UnsupportedMetadata):
        project(form, country_labels={})


@pytest.mark.parametrize('field,value', [
    ('DebtPrincipalBeginningOfYear', '1000000'),
    ('DebtPrincipalBeginningOfYear', Number('1.5')),
    ('DebtPrincipalBeginningOfYear', Number('1000000000000000')),
    ('CountryOfCreditor', 'syn_country_a'),
    ('LoanStartDate', '2025-01-01T20:00:00'),
    ('LoanStartDate', '2025-01-01T20:00:00.0001Z'),
    ('LoanStartDate', '2025-02-30'),
])
def test_l11c_unsupported_source_type_or_date_refuses_projection(field, value):
    form = source()
    form[BODY][0][field] = _corporate_json(wire(value))
    with pytest.raises(_UnsupportedMetadata):
        project(form)


def test_l11c_unsafe_ordered_partial_sum_is_not_hidden_by_later_cancellation():
    form = source()
    form[BODY] = [deepcopy(form[BODY][0]) for _ in range(3)]
    for row, value in zip(form[BODY], ('999999999999999', '1', '-1')):
        row['DebtPrincipalBeginningOfYear'] = _corporate_json(wire(Number(value)))
    form['TotalDebtPrincipalBeginningOfYear'] = _corporate_json(wire(Number('999999999999999')))
    for amount, total in zip(AMOUNTS[1:], TOTALS[1:]):
        for row in form[BODY]:
            row[amount] = _corporate_json(wire(Number('0')))
        form[total] = _corporate_json(wire(Number('0')))
    with pytest.raises(_UnsupportedMetadata):
        project(form)

@pytest.mark.parametrize('option,value', [('locale','en-US'),('timezone_name','UTC'),
    ('tax_type','ICT_CIT_USD'),('headers',HEADERS[1:]+HEADERS[:1]),
    ('footer_spans',[[6,*([1]*10)]])])
def test_l11c_unproved_owner_display_or_span_contract_stays_unsupported(option,value):
    with pytest.raises(_UnsupportedMetadata):
        project(**{option:value})


@pytest.mark.parametrize('field', ['NameOfCreditor', 'AddressOfCreditor', 'CountryOfCreditor',
    'Currency', 'EndOfYearRate', 'LoanStartDate', 'LoanDueDate', 'InterestRate', 'LoanAllocation', *AMOUNTS])
def test_l11c_missing_row_field_is_not_a_fabricated_blank_or_zero(field):
    form=source()
    del form[BODY][0][field]
    with pytest.raises(_UnsupportedMetadata):
        project(form)


@pytest.mark.parametrize('field', TOTALS)
def test_l11c_missing_reported_total_is_not_replaced_by_a_computed_total(field):
    form=source()
    del form[field]
    with pytest.raises(_UnsupportedMetadata):
        project(form)


def test_l11c_inconsistent_reported_total_is_not_replaced_by_a_computed_total():
    form=source()
    form[TOTALS[0]]=_corporate_json(wire(Number('1')))
    with pytest.raises(_UnsupportedMetadata):
        project(form)


@pytest.mark.parametrize('date', ['1969-12-31T17:00:00.000Z','2025-01-01T17:00:00+07:00',
                                '2025-01-01T24:00:00Z','2025-01-01T00:00:60Z'])
def test_l11c_unreviewed_historic_offset_or_timestamp_branch_stays_unsupported(date):
    form=source()
    form[BODY][0]['LoanStartDate']=date
    with pytest.raises(_UnsupportedMetadata):
        project(form)


@pytest.mark.parametrize('defect', ['extra-root', 'extra-row', 'missing-body', 'object-body',
                                  'string-total', 'null-total', 'boolean-amount'])
def test_l11c_unknown_or_unproved_source_fields_do_not_silently_disappear(defect):
    form = source()
    if defect == 'extra-root':
        form['SYNTHETIC_UNREVIEWED'] = '0009'
    elif defect == 'extra-row':
        form[BODY][0]['SYNTHETIC_UNREVIEWED'] = '0009'
    elif defect == 'missing-body':
        del form[BODY]
    elif defect == 'object-body':
        form[BODY] = {}
    elif defect == 'string-total':
        form[TOTALS[0]] = '2000000'
    elif defect == 'null-total':
        form[TOTALS[0]] = None
    else:
        form[BODY][0][AMOUNTS[0]] = True
    with pytest.raises(_UnsupportedMetadata):
        project(form)


def test_l11c_explicit_null_amounts_follow_source_zero_operator_without_mutating_capture():
    form = source()
    for row in form[BODY]:
        for field in AMOUNTS:
            row[field] = None
        row.update(InterestRate=None, LoanStartDate=None, LoanDueDate='', CountryOfCreditor=None)
    for total in TOTALS:
        form[total] = _corporate_json('0')
    before = deepcopy(form)
    table = project(form, country_labels={})['table']
    assert table['rows'][0][6:10] == ['0', '0', '0', '0,00']
    assert table['rows'][0][10:15] == ['', '', '', '0', '0']
    assert form == before


@pytest.mark.parametrize('value,expected', [('0001-01-01T00:00:00.000Z', ''),
    ('1970-01-01T00:00:00Z', '01-01-1970'), ('2100-12-31', '31-12-2100')])
def test_l11c_reviewed_date_boundary_and_normalized_sentinel(value, expected):
    form = source()
    form[BODY][0]['LoanStartDate'] = value
    assert project(form)['table']['rows'][0][10] == expected


def test_l11c_visible_headers_match_approved_reference_by_sheet_name():
    from pathlib import Path
    from openpyxl import load_workbook
    book = load_workbook(Path(__file__).resolve().parents[1] / 'resources/corporate_format.xlsx')
    try:
        assert [c.value for c in book['L11-C'][2]] == HEADERS
        assert 'A4:F4' in {str(area) for area in book['L11-C'].merged_cells.ranges}
    finally:
        book.close()
