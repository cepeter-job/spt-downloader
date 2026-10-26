"""Synthetic Accounting payments; no taxpayer records or credentials."""
import copy
import importlib
import json

import pytest


TAXPAYER = '00000000-0000-4000-8000-000000000001'
HEADER = '00000000-0000-4000-8000-000000000002'
DETAIL = '00000000-0000-4000-8000-000000000003'


def adapter():
    return importlib.import_module('coretax_mpn')


def payment_source(*, amount='-1250.50', period='01012025', paid='2026-02-01T00:00:00Z'):
    header = {'RecordId': HEADER, 'TaxpayerAggregateIdentifier': TAXPAYER,
              'TaxpayerTIN': '0000000000000001', 'PeriodCode': '01012026',
              'ReferenceNumber': 'SYNTHETIC-PARENT-0001', 'IsCancelled': False}
    detail = {'RecordId': DETAIL, 'HeaderRecordId': HEADER, 'PeriodCode': period,
              'Amount': '__amount__', 'CurrencyAmount': '__amount__',
              'HeaderExchangeRate': 1, 'CurrencyCode': 'IDR',
              'TransactionDate': paid, 'PostingDate': paid,
              'TransactionNumber': '0000000000000007',
              'AccountingTypeCode': 'OtherTaxReturn', 'AccountingTypeDetailCode': 'DBP',
              'ReferenceNumber': '=SYNTHETIC-REFERENCE', 'RevenueCode': '411211'}
    raw = json.dumps({'header': header, 'detail': detail}).replace('"__amount__"', amount).encode()
    decoded = adapter().decode_mpn(raw)
    return decoded['header'], decoded['detail']


def scope_run():
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'taxpayer_name': 'Synthetic authorized taxpayer', 'records': [],
            'audit': [], 'errors': [], 'complete': True, 'inventory_complete': True,
            'sources': [{'url': 'https://coretax.intranet.pajak.go.id/returnsheets/id-ID/'
                         'submitted-returnsheets/' + TAXPAYER, 'label': 'SPT Dilaporkan'}]}


def test_negative_payment_uses_detail_tax_year_even_when_parent_and_payment_are_later():
    header, detail = payment_source()
    row = adapter().project_payment(header, detail, year=2025)
    assert row['record_id'] == DETAIL and row['header_id'] == HEADER
    assert row['period_code'] == '01012025'
    assert row['amount'] == '-1250.50'
    assert row['transaction_date'] == '2026-02-01T00:00:00Z'
    assert row['transaction_number'] == '0000000000000007'
    assert row['reference'] == '=SYNTHETIC-REFERENCE'


@pytest.mark.parametrize('amount', ['0', '-0', '0.00', '-0.00', '25', '1e-10'])
def test_zero_and_positive_details_are_excluded(amount):
    header, detail = payment_source(amount=amount)
    assert adapter().project_payment(header, detail, year=2025) is None


def test_known_other_tax_year_is_excluded():
    header, detail = payment_source(period='12122024')
    assert adapter().project_payment(header, detail, year=2025) is None


@pytest.mark.parametrize('amount', ['-0.001', '-1234567890123456', '-1e-309'])
def test_negative_source_lexemes_are_retained_without_rounding(amount):
    header, detail = payment_source(amount=amount)
    assert adapter().project_payment(header, detail, year=2025)['amount'] == amount


@pytest.mark.parametrize('period', [None, '', '2025', '13252025', 'Januari 2025', '02012025'])
def test_unproved_periods_are_not_repaired_from_parent_or_caption(period):
    header, detail = payment_source(period=period)
    with pytest.raises(adapter().MpnUnsupported):
        adapter().project_payment(header, detail, year=2025)


def test_foreign_header_is_fatal_before_out_of_year_exclusion():
    header, detail = payment_source(period='12122024')
    detail['HeaderRecordId'] = '00000000-0000-4000-8000-000000000099'
    with pytest.raises(adapter().MpnSafetyError):
        adapter().project_payment(header, detail, year=2025)


@pytest.mark.parametrize('field', ['Amount', 'CurrencyAmount', 'HeaderExchangeRate'])
def test_source_numeric_strings_and_booleans_are_not_numeric_evidence(field):
    header, detail = payment_source()
    for value in ('-12', True, None):
        altered = copy.deepcopy(detail)
        altered[field] = value
        with pytest.raises(adapter().MpnUnsupported):
            adapter().project_payment(header, altered, year=2025)


@pytest.mark.parametrize('raw', [b'{"Amount":-1,"Amount":-2}', b'{"Amount":NaN}',
    b'{"Authorization":"synthetic-secret"}', b'{"v":"Bearer synthetic-secret"}'])
def test_unsafe_json_is_refused_without_source_excerpt(raw):
    with pytest.raises(adapter().MpnSafetyError) as caught:
        adapter().decode_mpn(raw)
    assert 'synthetic-secret' not in str(caught.value)


@pytest.mark.parametrize('text', ['Basic authorized taxpayer', 'Bearer bonds paid'])
def test_ordinary_business_text_is_not_misclassified_as_an_authentication_header(text):
    body = json.dumps({'TaxpayerName': text}).encode()
    assert adapter().decode_mpn(body)['TaxpayerName'] == text


def test_dom_rounding_requires_whole_detail_json_fallback():
    _, detail = payment_source(amount='-1250.501')
    row = ['01-02-2026', '01-02-2026', '0000000000000007', 'OtherTaxReturn',
           'DBP', '-1.250,501', '1,00', '-1.250,501', '=SYNTHETIC-REFERENCE']
    assert adapter().dom_numbers_match([row], [detail])
    rounded = [*row[:7], '-1.250,50', row[8]]
    assert not adapter().dom_numbers_match([rounded], [detail])
    assert not adapter().dom_numbers_match([], [detail])


def test_required_mpn_cannot_certify_a_complete_job_before_capture():
    from coretax_exporter import validate_export_run
    run = scope_run()
    adapter().require_mpn(run, 'dom')
    run['complete'] = True
    with pytest.raises(ValueError, match='MPN'):
        validate_export_run(run)


def test_legacy_export_has_no_invented_mpn_scope():
    run = scope_run()
    assert adapter().mpn_filename(run) is None
    adapter().validate_mpn(run)
    assert 'mpn' not in run
