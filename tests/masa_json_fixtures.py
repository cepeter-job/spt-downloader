"""Synthetic observed Masa envelopes; never copied taxpayer records."""
import hashlib
import json

from coretax_json import ORIGIN

NPWP = '0000000000000001'
RECORD = '00000000-0000-4000-8000-000000000001'
AGGREGATE = '00000000-0000-4000-8000-000000000002'
TAXPAYER = '00000000-0000-4000-8000-000000000003'
FOREIGN = '00000000-0000-4000-8000-000000000099'
SCOPE = [NPWP, 2025, 'period']
ATTEMPT = 'a' * 32


def page(rows, total, first=0, size=2):
    from coretax_json import _corporate_json
    return {'request': {'ReturnSheetRecordId': RECORD, 'First': first, 'Rows': size},
            'payload': {'Data': rows, 'TotalRecords': _corporate_json(str(total))},
            'sequence': first + 1}


def selected(tax):
    source = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER
    return {'record_id': RECORD, 'scope': list(SCOPE), 'list_url': source,
            'meta': {'Jenis Pajak': tax, 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'},
            'source_fields': {'RecordId': RECORD, 'AggregateIdentifier': AGGREGATE,
                              'TaxpayerAggregateIdentifier': TAXPAYER, 'TaxPeriodCode': '01012025'},
            'source_identity': {'record_id': RECORD, 'aggregate_id': AGGREGATE,
                                'taxpayer_id': TAXPAYER, 'source_url': source}}


def payload(tax):
    form = {'ReturnSheetRecordIdentifier': RECORD, 'ReturnSheetAggregateIdentifier': AGGREGATE,
            'TaxPeriodCode': '01012025'}
    outer = {'IsFound': True, 'TaxpayerIdentifier': TAXPAYER, 'TIN': NPWP,
             'PeriodCode': '01012025', 'ReturnSheetModel': 'NORMAL'}
    if tax == 'PPN':
        form.update(TIN=NPWP, TaxType='VAT_VAT', ReturnSheetModel='NORMAL')
        outer.update(PeriodYear=2025, PeriodMonth=1, ReturnSheetType='VAT_VATR',
                     ReturnSheetStatusCode='SUBMITTED')
    else:
        form.update(TaxIdentificationNumber=NPWP)
        outer.update(PeriodYear='2025', PeriodStartMonth='1', PeriodEndMonth='1')
        if tax == 'PPh Unifikasi':
            outer.update(ReturnSheetType='ICT_WTR', ReturnSheetStatusCode='SUBMITTED')
    outer['FormData'] = json.dumps(form)
    return outer


def packet(tax, data=None, *, sequence=1, request=None, status=200, successful=True):
    data = payload(tax) if data is None else data
    endpoint = 'nvat' if tax == 'PPN' else 'withholding-tax'
    body = json.dumps({'IsSuccessful': successful, 'Payload': data}, allow_nan=False).encode()
    return {'body': body, 'context': {
        'relative_path': f'returns/json/0001/{ATTEMPT}/response-{sequence:04d}.json',
        'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
        'url': ORIGIN + '/returnsheet/api/prefillreturnsheet/' + endpoint,
        'method': 'POST', 'status': status,
        'frame_url': ORIGIN + '/returnsheets/id-ID/synthetic-masa/' + TAXPAYER + '/' + RECORD,
        'sequence': sequence, 'attempt': ATTEMPT, 'record_id': RECORD, 'scope': list(SCOPE),
        'request_json': {'RecordId': RECORD} if request is None else request,
        'identity_validated': False}}
