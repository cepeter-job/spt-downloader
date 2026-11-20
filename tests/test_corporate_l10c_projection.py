"""Bounded populated L10-C candidate; synthetic data, runner-only execution.

These tests do not manufacture native packet or component custody. Native
admission remains closed until the separately reviewed producer exists.
"""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from support_json_corpus import Number, wire

ROOT = 'L10cFormData'
BODY = 'ListTaxHavenCountry'
HEADERS = ['NO.', 'NAMA MITRA TRANSAKSI', 'Jenis Transaksi', 'NEGARA',
           'NILAI TRANSAKSI (RUPIAH)']


def raw_source():
    row = {'NameOfTransactionPartner': '00012 SYNTHETIC PARTNER',
           'TypeOfTransaction': 'SYN_TRANSACTION', 'CountryCode': 'SYN_COUNTRY',
           'TransactionValue': Number('1234.125')}
    return {BODY: [row, deepcopy(row)], 'TotalTransactionValue': Number('987654'),
            'DeterminationOfTransactionQuestion': True}


def source():
    return _corporate_json(wire(raw_source()))


def project(form=None, **overrides):
    helper = getattr(importlib.import_module('coretax_corporate_projection'), 'project_l10c', None)
    assert callable(helper), 'Missing populated L10-C candidate renderer'
    options = {'headers': list(HEADERS), 'footer_spans': [], 'tax_type': 'ICT_RCIT',
               'locale': 'id-ID', 'labels': {
                   'TRANSACTION_TYPE': {'SYN_TRANSACTION': 'SYNTHETIC TRANSACTION DESCRIPTION'},
                   'COUNTRY_CODE': {'SYN_COUNTRY': 'SYNTHETIC COUNTRY DESCRIPTION'}}}
    options.update(overrides)
    return helper(source() if form is None else form, **options)


def test_populated_candidate_keeps_duplicates_labels_and_number_not_integer_representation():
    form = source()
    before = deepcopy(form)
    result = project(form)
    table = result['table']
    row = ['1', '00012 SYNTHETIC PARTNER', 'SYNTHETIC TRANSACTION DESCRIPTION',
           'SYNTHETIC COUNTRY DESCRIPTION', '1.234,125']
    assert table['headers'] == HEADERS
    assert table['rows'] == [row, ['2', *row[1:]]]
    assert table['body_row_count'] == table['source_total'] == 2
    assert table['footer'] == table['footer_spans'] == []
    assert result['projection_complete'] is False
    assert result['projection_reason'] == 'unprojected_l10c_controls'
    assert result['fields'] == []  # Neither a guessed radio value nor a new layout.
    assert {field['field'] for field in result['projection_unresolved_fields']} == {
        'PeriodYear', 'CollectorTin', 'Question'}
    evidence = {tuple(entry['path']): entry for entry in result['provenance']}
    assert evidence[(ROOT, BODY, 0, 'TypeOfTransaction')]['value'] == 'SYN_TRANSACTION'
    assert evidence[(ROOT, BODY, 1, 'CountryCode')]['value'] == 'SYN_COUNTRY'
    assert evidence[(ROOT, BODY, 0, 'TransactionValue')]['value'] == '1234.125'
    total = evidence[(ROOT, 'TotalTransactionValue')]
    assert total['value'] == '987654' and 'destination' not in total
    question = evidence[(ROOT, 'DeterminationOfTransactionQuestion')]
    assert question['type'] == 'boolean' and question['value'] is True
    assert 'destination' not in question
    assert form == before


@pytest.mark.parametrize('field,value', [
    ('TransactionValue', '1234.125'), ('TransactionValue', True),
    ('TransactionValue', Number('0.1234567890123456')),
    ('TransactionValue', Number('1000000000000000')), ('TransactionValue', Number('-0')),
    ('NameOfTransactionPartner', Number('12')), ('NameOfTransactionPartner', False),
    ('TypeOfTransaction', 'MISSING_SYNTHETIC_CODE'), ('CountryCode', 'MISSING_SYNTHETIC_CODE'),
    ('TypeOfTransaction', Number('1')), ('CountryCode', {}),
])
def test_unproved_representation_refuses_instead_of_coercing_or_rounding(field, value):
    form = source()
    form[BODY][0][field] = _corporate_json(wire(value))
    with pytest.raises(_UnsupportedMetadata):
        project(form)


@pytest.mark.parametrize('body', [None, []])
def test_explicit_empty_is_not_a_footer_or_a_complete_control_mapping(body):
    form = source()
    form[BODY] = body
    result = project(form, labels={'TRANSACTION_TYPE': {}, 'COUNTRY_CODE': {}})
    assert result['table']['rows'] == result['table']['footer'] == []
    assert result['table']['body_row_count'] == 0
    assert result['projection_complete'] is False
    retained = next(entry for entry in result['provenance'] if entry['path'] == [ROOT, BODY])
    assert retained['type'] == ('null' if body is None else 'array')
    assert form[BODY] == body


@pytest.mark.parametrize('value,expected', [
    (None, ''), (Number('0'), '0'), (Number('12'), '12'),
    (Number('-1234.5'), '-1.234,5'), (Number('1.2500'), '1,25'),
    (Number('999999999999999'), '999.999.999.999.999'),
])
def test_number_default_subset_never_rounds_fractional_values(value, expected):
    form = source()
    form[BODY][0]['TransactionValue'] = _corporate_json(wire(value))
    assert project(form)['table']['rows'][0][-1] == expected


@pytest.mark.parametrize('option,value', [
    ('tax_type', 'ICT_CIT_USD'), ('locale', 'en-US'), ('headers', HEADERS[::-1]),
    ('footer_spans', [[4, 1]]), ('labels', None), ('labels', {}),
    ('labels', {'TRANSACTION_TYPE': [], 'COUNTRY_CODE': {}}),
])
def test_candidate_refuses_unproved_display_structure(option, value):
    with pytest.raises(_UnsupportedMetadata):
        project(**{option: value})


@pytest.mark.parametrize('defect', ['missing-root', 'extra-root', 'null-form', 'object-body',
    'row-not-object', 'missing-column', 'extra-column', 'string-total', 'null-total',
    'question-object', 'too-many-rows'])
def test_candidate_closed_shape_never_drops_unknown_original_content(defect):
    form = source()
    if defect == 'missing-root': del form['TotalTransactionValue']
    elif defect == 'extra-root': form['SYNTHETIC_UNKNOWN'] = None
    elif defect == 'null-form': form = None
    elif defect == 'object-body': form[BODY] = {}
    elif defect == 'row-not-object': form[BODY][0] = None
    elif defect == 'missing-column': del form[BODY][0]['CountryCode']
    elif defect == 'extra-column': form[BODY][0]['SYNTHETIC_UNKNOWN'] = None
    elif defect == 'string-total': form['TotalTransactionValue'] = '987654'
    elif defect == 'null-total': form['TotalTransactionValue'] = None
    elif defect == 'question-object': form['DeterminationOfTransactionQuestion'] = {}
    else: form[BODY] = [deepcopy(form[BODY][0]) for _ in range(10001)]
    helper = getattr(importlib.import_module('coretax_corporate_projection'), 'project_l10c')
    # Call directly for literal None; project() reserves None for its default.
    with pytest.raises(_UnsupportedMetadata):
        helper(form, headers=HEADERS, footer_spans=[], tax_type='ICT_RCIT', locale='id-ID',
               labels={'TRANSACTION_TYPE': {}, 'COUNTRY_CODE': {}})


def test_absent_tax_haven_body_projects_empty_table_not_refusal():
    # No tax-haven transactions -> ListTaxHavenCountry key is omitted entirely;
    # that is an empty table, not a closed-shape drift (the two totals stay
    # mandatory and unknown roots still refuse).
    form = source()
    del form[BODY]
    result = project(form)
    assert result['table']['body_row_count'] == 0


@pytest.mark.parametrize('value', [None, '', '0', '1', False, True, Number('0'), Number('1')])
def test_question_is_typed_unresolved_evidence_never_a_ya_tidak_inference(value):
    form = source()
    form['DeterminationOfTransactionQuestion'] = _corporate_json(wire(value))
    result = project(form)
    evidence = result['provenance'][-1]
    assert evidence['value'] == value
    assert 'destination' not in evidence and result['fields'] == []
    assert result['projection_complete'] is False


@pytest.mark.parametrize('field', ['NameOfTransactionPartner', 'TypeOfTransaction', 'CountryCode'])
@pytest.mark.parametrize('value', [None, ''])
def test_present_null_or_empty_text_and_reference_controls_are_blank_not_missing(field, value):
    form = source()
    form[BODY][0][field] = value
    column = ['NameOfTransactionPartner', 'TypeOfTransaction', 'CountryCode'].index(field) + 1
    assert project(form)['table']['rows'][0][column] == ''


@pytest.mark.parametrize('description', [None, '', ' ', Number('12'), False])
def test_unavailable_or_nonstring_description_never_becomes_raw_code(description):
    choices = {'TRANSACTION_TYPE': {'SYN_TRANSACTION': description},
               'COUNTRY_CODE': {'SYN_COUNTRY': 'SYNTHETIC COUNTRY DESCRIPTION'}}
    with pytest.raises(_UnsupportedMetadata):
        project(labels=choices)


def test_extreme_decimal_source_is_an_unsupported_candidate_not_an_uncaught_decimal_error():
    form = source()
    form[BODY][0]['TransactionValue'] = _corporate_json('1e-9999999999999999999')
    with pytest.raises(_UnsupportedMetadata):
        project(form)
