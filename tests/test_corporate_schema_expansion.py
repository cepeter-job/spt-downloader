"""525-rebuild corporate schema expansion; synthetic sources, runner-only."""
import copy
import hashlib
import json

import pytest

from support_json_corpus import Number, current_form, observed, packet, primary, wire
from test_json_adapter import adapt, eligible

SCHEMA_NULL = ['CalculationAfterTaxIncome5Years', 'CalculationLetterOfTheIncomeTax',
    'ConsolidatedFinancialStatement', 'CopyOfIncomeTaxReturn', 'CorporateType',
    'FinancialStatementControlledForeignCompany', 'FinancialStatementXlsx',
    'L12AFormData', 'L12BNotificationReinvestmentNetIncome',
    'L13AListOfTaxFacilityInInvestment', 'L13BListOfAdditionalGrossIncomeDeduction',
    'L13CListOfTaxFacilityOfCorporateIncomeTaxReduction', 'L14UtilizationOfRemainingExcess',
    'L1aFormData', 'L1cFormData', 'L1eFormData', 'L1fFormData', 'L1gFormData',
    'L1hFormData', 'L1iFormData', 'L1jFormData', 'L1kFormData', 'L1lFormData',
    'ListOfGrossTurnover', 'MonthlyReport', 'PeriodCode', 'ProofOfIncomeTax',
    'ProofOfReinvestment', 'ProofOfZakat', 'ReportOfShareholders', 'WithholdingSlip']

DOC = {'DocumentId': 'SYNTHETIC', 'DocumentAggregateIdentifier': 'SYNTHETIC-AGGREGATE',
       'DocumentType': 'FinancialStatement', 'FileName': 'SYNTHETIC-metadata-only.pdf',
       'CreationDate': '02-01-2025'}


def with_schema(form, *, nulls=None, months=None, prefill='11111111-2222-4000-8000-333333333333',
                receipt=True):
    for key in (nulls or SCHEMA_NULL):
        form[key] = None
    form.update({'ActualMonths': Number('6') if months is None else months,
                 'PrefillFromId': prefill,
                 'ElectronicReceiptSubmission': receipt})
    return form


def primary_with_outer_periods(form):
    item = primary(form)
    envelope = json.loads(item['body'])
    envelope['Payload'].update(PeriodMonthStart=1, PeriodMonthEnd=6)
    item['body'] = wire(envelope).encode()
    item['context'].update(bytes=len(item['body']),
                           sha256=hashlib.sha256(item['body']).hexdigest())
    return item


def test_null_allowlist_and_metadata_pass_together():
    form = with_schema(current_form())
    result = adapt([primary_with_outer_periods(form)])
    eligible(result)
    assert result['provenance']['omitted_null_keys'] == sorted(SCHEMA_NULL)
    assert result['provenance']['corporate_metadata']['ActualMonths'] == 6
    prefill = result['provenance']['corporate_metadata']['PrefillFromId']
    assert prefill['format'] == 'uuid' and len(prefill['sha256']) == 64
    dump = json.dumps(result['provenance'])
    assert '11111111-2222-4000-8000-333333333333' not in dump


def test_document_leaves_retained_in_private_provenance_only():
    form = with_schema(current_form())
    form['AuditOpinion'] = dict(DOC)
    result = adapt([primary_with_outer_periods(form)])
    eligible(result)
    rows = result['provenance']['corporate_metadata']['AuditOpinion']['rows']
    assert any(row[2] == DOC['FileName'] for row in rows)
    assert 'attachments' not in result


@pytest.mark.parametrize('start,end,months', [(1, 12, '12'), (6, 6, '1'), (3, 9, '7')])
def test_actual_months_normal_ranges_pass(start, end, months):
    form = with_schema(current_form())
    form['ActualMonths'] = Number(months)
    item = primary(form)
    envelope = json.loads(item['body'])
    envelope['Payload'].update(PeriodMonthStart=start, PeriodMonthEnd=end)
    item['body'] = wire(envelope).encode()
    item['context'].update(bytes=len(item['body']),
                           sha256=hashlib.sha256(item['body']).hexdigest())
    eligible(adapt([item]))


@pytest.mark.parametrize('start,end', [(11, 2), (12, 1)])
def test_actual_months_cross_year_wraps_fail_closed(start, end):
    form = with_schema(current_form())
    form['ActualMonths'] = Number('4' if (start, end) == (11, 2) else '2')
    item = primary(form)
    envelope = json.loads(item['body'])
    envelope['Payload'].update(PeriodMonthStart=start, PeriodMonthEnd=end)
    item['body'] = wire(envelope).encode()
    item['context'].update(bytes=len(item['body']),
                           sha256=hashlib.sha256(item['body']).hexdigest())
    result = adapt([item])
    assert result['eligible'] is False
    assert 'unverified_corporate_actual_months' in result['reason']


@pytest.mark.parametrize('defect', ['nonnull-null-key', 'bad-months', 'string-months', 'months-mismatch',
    'bad-prefill', 'nonbool-receipt'])
def test_schema_expansion_malformed_values_refuse(defect):
    form = with_schema(current_form())
    if defect == 'nonnull-null-key':
        form['L1aFormData'] = {}
    elif defect == 'bad-months':
        form['ActualMonths'] = 'Synthetic-not-a-number'
    elif defect == 'string-months':
        form['ActualMonths'] = '6'
    elif defect == 'months-mismatch':
        form['ActualMonths'] = Number('5')
    elif defect == 'bad-prefill':
        form['PrefillFromId'] = 'not-a-uuid'
    else:
        form['ElectronicReceiptSubmission'] = 1
    result = adapt([primary_with_outer_periods(form)])
    assert result['eligible'] is False


def test_unmapped_unknown_key_still_refuses():
    form = with_schema(current_form())
    form['TotallyUnreviewedKey'] = {'Nested': 'SYNTHETIC'}
    result = adapt([primary_with_outer_periods(form)])
    assert result['eligible'] is False
    assert 'unmapped_corporate_source_subtree' in result['reason']


def test_document_metadata_is_evidence_not_pdf_custody():
    form = with_schema(current_form())
    form['AuditOpinion'] = dict(DOC)
    form['FinancialStatement'] = [dict(DOC)]
    result = adapt([primary_with_outer_periods(form)])
    eligible(result)
    counts = result['provenance']['corporate_metadata']
    assert counts['AuditOpinion']['count'] == 1
    assert counts['FinancialStatement']['count'] == 1
    assert 'attachments' not in result


def test_document_metadata_malformed_refuses():
    form = with_schema(current_form())
    form['FinancialStatement'] = [{'DocumentId': 1, 'DocumentAggregateIdentifier': 'x',
                                   'DocumentType': 'FinancialStatement',
                                   'FileName': 'x.pdf', 'CreationDate': 'y'}]
    result = adapt([primary_with_outer_periods(form)])
    assert result['eligible'] is False


def test_declared_l10a_path_skips_only_when_absent():
    form = with_schema(current_form())
    forms = observed([['DeclarationTransactionRelatedParties'], ['FinancialStatement']])
    result = adapt([primary_with_outer_periods(form)], forms=forms)
    eligible(result)


def _l4_footer_events(*requests, url=None):
    from coretax_json import ORIGIN
    base = url or (ORIGIN + '/returnsheet/api/loadcit/l4-table-a-grid/footer')
    return [{'url': base, 'method': 'POST', 'request_json': request}
            for request in requests]


def test_l4_footer_accepts_both_proven_request_shapes():
    from coretax_corporate import _l4_footer_requests
    found = _l4_footer_requests(
        _l4_footer_events({'ReturnSheetRecordId': 'R'},
                          {'ReturnSheetRecordId': 'R', 'PeriodYear': '2025'}),
        record_id='R', period='01122025')
    assert found == [{'ReturnSheetRecordId': 'R'},
                     {'ReturnSheetRecordId': 'R', 'PeriodYear': '2025'}]


def test_l4_footer_refuses_missing_footer():
    from coretax_corporate import _l4_footer_requests
    assert _l4_footer_requests([], record_id='R', period='01122025') is None
    assert _l4_footer_requests(
        _l4_footer_events({'ReturnSheetRecordId': 'R', 'Unexpected': True}),
        record_id='R', period='01122025') is None


def test_l4_footer_contradictions_are_fatal():
    from coretax_corporate import _l4_footer_requests
    from coretax_json import JsonSafetyError
    with pytest.raises(JsonSafetyError):
        _l4_footer_requests(_l4_footer_events({'ReturnSheetRecordId': 'OTHER'}),
                            record_id='R', period='01122025')
    with pytest.raises(JsonSafetyError):
        _l4_footer_requests(_l4_footer_events({'ReturnSheetRecordId': 'R', 'PeriodYear': '2024'}),
                            record_id='R', period='01122025')


def _l4_packets(*, footer_tax_base='100', with_footer=True):
    form = with_schema(current_form())
    form['ListOfIncomeSubjectToFinalTaxAndNonTaxableObject'] = {
        'TotalTaxBase': Number('100'), 'TotalFinalIncomeTaxPayable': Number('7'),
        'TotalGrossIncome': Number('100'), 'TotalFinalIncomeTaxPayableUsd': Number('0')}
    return form


def _l4_forms():
    from support_json_corpus import ORIGIN, RECORD_ID
    grid_url = ORIGIN + '/returnsheet/api/loadcit/l4-table-a-grid'
    footer_url = grid_url + '/footer'
    forms = observed(['ListOfIncomeSubjectToFinalTaxAndNonTaxableObject'])
    forms[0]['grids'].append({'name': 'L4/a', 'endpoint': grid_url,
        'pages': [{'request_json': {'ReturnSheetRecordId': RECORD_ID, 'First': 0, 'Rows': 10},
                   'offset': 0}]})
    forms[0]['dependencies'].append({'endpoint': footer_url,
        'request_json': {'ReturnSheetRecordId': RECORD_ID}})
    return forms, grid_url, footer_url


def test_l4_footer_reconciles_with_stored_totals():
    from support_json_corpus import RECORD_ID, source_row
    form = _l4_packets()
    forms, grid_url, footer_url = _l4_forms()
    bodies = [primary_with_outer_periods(form)]
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'Data': [source_row()], 'TotalRecords': 1, 'Index': None}}, 2,
        endpoint=grid_url,
        request={'ReturnSheetRecordId': RECORD_ID, 'First': 0, 'Rows': 10}))
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'TaxBase': Number('100'), 'TaxBaseUsd': Number('0'),
                    'IncomeTax': Number('7'), 'IncomeTaxUsd': Number('0')}}, 3,
        endpoint=footer_url, request={'ReturnSheetRecordId': RECORD_ID}))
    eligible(adapt(bodies, forms=forms))


def test_l4_footer_contradiction_is_fatal_and_missing_footer_refuses():
    from support_json_corpus import RECORD_ID, source_row
    form = _l4_packets()
    forms, grid_url, footer_url = _l4_forms()
    bodies = [primary_with_outer_periods(form)]
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'Data': [source_row()], 'TotalRecords': 1, 'Index': None}}, 2,
        endpoint=grid_url,
        request={'ReturnSheetRecordId': RECORD_ID, 'First': 0, 'Rows': 10}))
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'TaxBase': Number('101'), 'TaxBaseUsd': Number('0'),
                    'IncomeTax': Number('7'), 'IncomeTaxUsd': Number('0')}}, 3,
        endpoint=footer_url, request={'ReturnSheetRecordId': RECORD_ID}))
    with pytest.raises(Exception) as excinfo:
        adapt(copy.deepcopy(bodies), forms=forms)
    assert 'L4 footer contradicts' in str(excinfo.value)
    result = adapt(copy.deepcopy(bodies[:2]), forms=forms)
    assert result['eligible'] is False


def test_l4_footer_non_numeric_usd_refuses():
    from support_json_corpus import RECORD_ID, source_row
    form = _l4_packets()
    forms, grid_url, footer_url = _l4_forms()
    bodies = [primary_with_outer_periods(form)]
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'Data': [source_row()], 'TotalRecords': 1, 'Index': None}}, 2,
        endpoint=grid_url,
        request={'ReturnSheetRecordId': RECORD_ID, 'First': 0, 'Rows': 10}))
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'TaxBase': Number('100'), 'TaxBaseUsd': 'SYNTHETIC-USD',
                    'IncomeTax': Number('7'), 'IncomeTaxUsd': Number('0')}}, 3,
        endpoint=footer_url, request={'ReturnSheetRecordId': RECORD_ID}))
    result = adapt(bodies, forms=forms)
    assert result['eligible'] is False
    assert 'unverified_corporate_l4_footer' in result['reason']


@pytest.mark.parametrize('usd', ['NaN', 'Infinity'])
def test_l4_footer_nonfinite_usd_refuses(usd):
    from support_json_corpus import RECORD_ID, source_row
    form = _l4_packets()
    forms, grid_url, footer_url = _l4_forms()
    bodies = [primary_with_outer_periods(form)]
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'Data': [source_row()], 'TotalRecords': 1, 'Index': None}}, 2,
        endpoint=grid_url,
        request={'ReturnSheetRecordId': RECORD_ID, 'First': 0, 'Rows': 10}))
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'TaxBase': Number('100'), 'TaxBaseUsd': usd,
                    'IncomeTax': Number('7'), 'IncomeTaxUsd': Number('0')}}, 3,
        endpoint=footer_url, request={'ReturnSheetRecordId': RECORD_ID}))
    result = adapt(bodies, forms=forms)
    assert result['eligible'] is False
    assert 'unverified_corporate_l4_footer' in result['reason']


@pytest.mark.parametrize('usd', ['0', '100'])
def test_l4_footer_string_numeric_usd_refuses(usd):
    from support_json_corpus import RECORD_ID, source_row
    form = _l4_packets()
    forms, grid_url, footer_url = _l4_forms()
    bodies = [primary_with_outer_periods(form)]
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'Data': [source_row()], 'TotalRecords': 1, 'Index': None}}, 2,
        endpoint=grid_url,
        request={'ReturnSheetRecordId': RECORD_ID, 'First': 0, 'Rows': 10}))
    bodies.append(packet({'IsSuccessful': True, 'ErrorCode': 0,
        'Payload': {'TaxBase': Number('100'), 'TaxBaseUsd': usd,
                    'IncomeTax': Number('7'), 'IncomeTaxUsd': Number('0')}}, 3,
        endpoint=footer_url, request={'ReturnSheetRecordId': RECORD_ID}))
    result = adapt(bodies, forms=forms)
    assert result['eligible'] is False
    assert 'unverified_corporate_l4_footer' in result['reason']
