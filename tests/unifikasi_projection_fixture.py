"""Clearly synthetic Unifikasi with all five grid families and catalog labels."""
from copy import deepcopy
import json
from coretax_json import ORIGIN
from coretax_masa_bindings import _UNIFIKASI_GRID_COLUMNS
from masa_json_fixtures import RECORD, packet
from masa_projection_fixture import field, response
from test_unifikasi_json_identity import source_case
from test_unifikasi_json_references import TYPES, catalogs

TAX = 'PPh Unifikasi'
URL = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + ','.join(TYPES)


def case(*, populated=True, model='Normal'):
    result = source_case(model)
    outer = json.loads(result['packets'][0]['body'])['Payload']
    inner = json.loads(outer['FormData'])
    inner.update(ReturnSheetStatusCode='SUBMITTED', SubmitInProgressStatus=False,
                 Signer={'StatementTIN': '0000000000000001', 'StatementFullName': 'SYNTHETIC SIGNER'},
                 StatementSignature='SYNTHETIC SIGNATURE')
    outer['FormData'] = json.dumps(inner)
    result['packets'] = [packet(TAX, outer)]
    induk = result['forms'][0]
    for control, label in [('TaxPeriodCode', 'Masa Pajak'), ('SubmitInProgressStatus', 'Status Penyampaian'),
                           ('StatementTIN', 'NPWP Penandatangan'), ('StatementFullName', 'Nama Penandatangan'),
                           ('StatementSignature', 'Tanda Tangan'), ('MyCheckBox', 'Pernyataan')]:
        item = field(control, label)
        if control == 'TaxPeriodCode':
            item['tag'] = 'UI-DROPDOWN'
        induk['fields'].append(item)
    for option, label in [('0', 'Wajib Pajak'), ('1', 'Kuasa Wajib Pajak')]:
        induk['fields'].append({**field('DeclarationBy', label), 'tag': 'P-RADIOBUTTON', 'option': option})
    for form in result['forms']:
        for table in form['tables']:
            if table['name'] == 'income-taxes':
                continue
            columns = _UNIFIKASI_GRID_COLUMNS[table['name']]
            row = {key: ('2025-01-02T00:00:00' if kind == 'date' else
                         1200 if key == 'TaxBase' else 30 if key == 'IncomeTax' else
                         2.5 if kind == 'number2' else 0 if kind == 'number' else
                         'SYNTHETIC' if kind == 'reference' else '0000123')
                   for key, kind in columns}
            rows = [row] if populated else []
            sequence = len(result['packets']) + 1
            request = {'ReturnSheetRecordId': RECORD, 'First': 0, 'Rows': 5, 'Filters': []}
            result['packets'].append(response(TAX, {'Data': rows, 'TotalRecords': len(rows)},
                'loadwtr/' + table['name'] + '-grid', request, sequence))
            table.update(source_total=len(rows), pages=[{'request_json': request, 'offset': 0, 'sequences': [sequence]}])
    sequence = len(result['packets']) + 1
    reference = packet(TAX, catalogs(), sequence=sequence)
    reference['context'].update(url=URL, method='GET', request_json=None)
    result['packets'].append(reference)
    for form in result['forms']:
        form['references'] = [{'endpoint': URL, 'sequences': [sequence]}]
    return deepcopy(result)
