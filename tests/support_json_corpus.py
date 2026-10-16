"""Synthetic json corpus helpers; no collected tests or shared mutable test state."""
import hashlib
import json
import re


ORIGIN = 'https://coretax.intranet.pajak.go.id'


NPWP = '0000000000000001'


RECORD_ID = '00000000-0000-4000-8000-000000000001'


AGGREGATE_ID = '00000000-0000-4000-8000-000000000002'


TAXPAYER_ID = '00000000-0000-4000-8000-000000000003'


FOREIGN_ID = '00000000-0000-4000-8000-000000000099'


ATTEMPT = 'a' * 32


SCOPE = [NPWP, 2025, 'period']


LIST_URL = ORIGIN + '/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER_ID


FRAME_URL = ORIGIN + '/returnsheets/id-ID/fixture-return/' + TAXPAYER_ID + '/' + RECORD_ID


PRIMARY_URL = ORIGIN + '/returnsheet/api/prefillreturnsheet/corporate-income'


class Number(str):
    """Fixture-only JSON number token; avoids creating source bytes via float."""


def wire(value):
    if isinstance(value, Number):
        assert re.fullmatch(r'-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?', value)
        return str(value)
    if isinstance(value, dict):
        return '{' + ','.join(json.dumps(k) + ':' + wire(v) for k, v in value.items()) + '}'
    if isinstance(value, list):
        return '[' + ','.join(wire(v) for v in value) + ']'
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def selected_record():
    return {'key': 'synthetic-corporate-normal', 'record_id': RECORD_ID,
            'scope': list(SCOPE), 'list_url': LIST_URL, 'source_status': 'SPT Dilaporkan',
            'capture_complete': False,
            'meta': {'Jenis Pajak': 'PPh Badan', 'Masa Pajak': 'Tahun 2025',
                     'Model SPT': 'Normal', 'Tanggal Submit SPT': '02-01-2025'},
            'source_fields': {'RecordId': RECORD_ID, 'AggregateIdentifier': AGGREGATE_ID,
                              'TaxpayerAggregateIdentifier': TAXPAYER_ID,
                              'TaxTypeCode': 'ICT_RCIT', 'TaxPeriodCode': '01122025'},
            'source_identity': {'record_id': RECORD_ID, 'aggregate_id': AGGREGATE_ID,
                                'taxpayer_id': TAXPAYER_ID, 'source_url': LIST_URL}}


def current_form():
    return {'TaxType': 'ICT_RCIT', 'IsDraft': False, 'TaxPeriodCode': '01122025',
            'ReturnSheetRecordIdentifier': RECORD_ID,
            'ReturnSheetAggregateIdentifier': AGGREGATE_ID,
            'MainFormData': {'Tin': NPWP, 'TaxYear': 2025, 'Name': 'SYNTHETIC COMPANY',
                             'NetIncomeBeforeTax': Number('123.4500'),
                             'IsIncomeTaxOverseasWithholding': False,
                             'TaxRate': 'SYNTHETIC RATE'}}


def context(raw, sequence=1, *, endpoint=PRIMARY_URL, request=None, status=200):
    return {'relative_path': f'returns/json/0001/{ATTEMPT}/response-{sequence:04d}.json',
            'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'url': endpoint, 'method': 'POST', 'status': status, 'frame_url': FRAME_URL,
            'sequence': sequence, 'attempt': ATTEMPT, 'record_id': RECORD_ID,
            'scope': list(SCOPE), 'request_json': request, 'identity_validated': False}


def packet(envelope, sequence=1, *, endpoint=PRIMARY_URL, request=None, status=200):
    raw = envelope if isinstance(envelope, bytes) else wire(envelope).encode('utf-8')
    # The collector's parsed payload may have rounded floats; raw bytes win.
    parsed = json.loads(raw) if isinstance(envelope, dict) else None
    return {'body': raw, 'payload': parsed,
            'context': context(raw, sequence, endpoint=endpoint, request=request, status=status)}


def primary(form=None, *, outer_draft=True, sequence=1):
    form = current_form() if form is None else form
    payload = {'TIN': NPWP, 'PeriodYear': 2025, 'IsDraft': outer_draft,
               'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'Normal',
               'PreviousFormData': None, 'LastSubmittedFormData': None,
               'CurrentFormData': wire(form)}
    return packet({'IsSuccessful': True, 'ErrorCode': 0, 'Payload': payload}, sequence)


def observed(*extra_paths):
    return [{'name': 'Induk', 'paths': [['MainFormData'], *extra_paths],
             'primary': {'endpoint': PRIMARY_URL, 'request_json': None},
             'grids': [], 'responses': [], 'dependencies': []}]


def request(group, page=0):
    return {'synthetic_group': group, 'synthetic_page': page}


def source_row(marker='SYNTHETIC SLIP', amount=None):
    return {'Name': marker, 'TIN': '0000000000000002', 'Index': 0,
            'TaxBase': Number('12.3400') if amount is None else amount,
            'IncomeTax': Number('0'), 'IsManually': False, 'Action': None}
