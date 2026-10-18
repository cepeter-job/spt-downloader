"""Complete synthetic native PPh21 attempt; no collected taxpayer records."""
from copy import deepcopy
import json

from coretax_json import ORIGIN
from masa_json_fixtures import RECORD, packet
from test_pph21_json_primary import TAX, case as primary_case
from test_pph21_json_grids import GRIDS, LOOKUPS, fixture as grid_fixture
from support_pph21_dom import appendix_table, induk_tables
from pph21_observer_fixture import INDUK_CONTROLS

MAIN = ORIGIN + '/returnsheets/id-ID/main.cccfdb820c20596c.js'
ARTICLE = ORIGIN + '/returnsheets/id-ID/803.8681206e4827011e.js'
BUILDS = {MAIN: '696ac66dc2897c937c7df7b466382dffdf25651837a20e0a4d4235787f3c9afd',
          ARTICLE: 'cd7b51042384a63e1d1fae9b9b284a38a0a942ab9f95a7fceb46b3c76fcd9add'}
PREFILL = ORIGIN + '/returnsheet/api/prefillreturnsheet/article-2126'
REFERENCE = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/EBUPOT_TAX_CERTIFICATE,COUNTRY_CODE,EBUPOT_STATUS'
MODEL_REFERENCE = REFERENCE.rsplit('/', 1)[0] + '/RETURN_SHEET_MODEL'
TOTAL = 'TotalGrossIncomeAndIncomeTaxBorneByGovernmentAndIncomeTaxWithheld'


def case():
    record, outer, form = primary_case()
    form.update({name: 5 for name in INDUK_CONTROLS})
    for root, tax in [('Form1A', 12), ('Form1B', 13)]:
        form[root] = {'GrossIncomeAndIncomeTaxWithheld': {'GrossIncome': 700, 'IncomeTax': tax},
                      'GrossIncomeAndIncomeTaxBorneByGovernment': {'GrossIncome': 800, 'IncomeTax': 8},
                      TOTAL: {'GrossIncome': 900, 'IncomeTax': 9}}
    form['Form2'] = {'TotalGrossIncome': 600, 'TotalIncomeTax': 6}
    form['Form3'] = {TOTAL: {'GrossIncome': 500, 'IncomeTax': 5}}
    for article, tax in [('21', 14), ('26', 15)]:
        form['Form3']['Article' + article + 'GrossIncomeAndIncomeTaxWithheld'] = {'GrossIncome': 400, 'IncomeTax': tax}
        form['Form3']['Article' + article + 'GrossIncomeAndIncomeTaxBorneByGovernment'] = {'GrossIncome': 300, 'IncomeTax': 3}
    outer.update(FormData=json.dumps(form), SubmitInProgressStatus=False)
    primary_request = {'RecordId': RECORD, 'onManualClick': False}
    primary = packet(TAX, outer, sequence=1, request=primary_request)
    primary['context']['url'] = PREFILL
    catalogs = []
    for kind, field in zip(('EBUPOT_TAX_CERTIFICATE', 'COUNTRY_CODE', 'EBUPOT_STATUS'),
                           ('TaxCertificate', 'CountryCode', 'Status')):
        catalogs.append({'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
            {'Code': code, 'CodeDescription': label, 'ValidTo': None} for code, label in LOOKUPS[field].items()]})
    model = [{'ReferenceDataType': 'RETURN_SHEET_MODEL', 'language': 'id-ID', 'Details': [
        {'Code': 'NORMAL', 'CodeDescription': 'SYNTHETIC MODEL', 'ValidTo': None}]}]
    bodies = [primary]
    for sequence, endpoint, payload in [(2, REFERENCE, catalogs), (3, MODEL_REFERENCE, model)]:
        item = packet(TAX, payload, sequence=sequence)
        item['context'].update(url=endpoint, method='GET', request_json=None)
        bodies.append(item)
    forms = [{'name': name, 'builds': dict(BUILDS), 'locale': 'id-ID', 'timezone': 'Asia/Jakarta',
              'fields': [], 'tables': []} for name in ('Induk', 'L-IA', 'L-IB', 'L-II', 'L-III')]
    induk = forms[0]
    induk['primary'] = {'endpoint': PREFILL, 'requests': [{'request_json': primary_request, 'sequences': [1]}]}
    induk['references'] = [{'endpoint': REFERENCE, 'method': 'GET', 'sequences': [2]},
                           {'endpoint': MODEL_REFERENCE, 'method': 'GET', 'sequences': [3]}]
    for field, label, tag in [('TaxPeriodMonth', 'Masa Pajak', 'INPUT'), ('TaxPeriodYear', 'Tahun Pajak', 'INPUT'),
                              ('Status', 'Status SPT', 'UI-DROPDOWN'), ('SubmitInProgressStatus', 'Status Penyampaian', 'INPUT')]:
        induk['fields'].append({'field': field, 'label': label, 'tag': tag, 'group': 'HEADER', 'column_label': ''})
    tables, _ = induk_tables()
    position = 0
    for table in tables:
        fields = list(INDUK_CONTROLS[position:position + len(table['rows'])])
        position += len(fields)
        induk['tables'].append({'name': table['name'], 'group': table['group'], 'headers': table['headers'],
            'footer_spans': [], 'row_spans': [[1, 1, 1, 1]] * (len(fields) + 1),
            'row_fields': [[]] + [[field] for field in fields]})
        induk['fields'].extend({'field': field, 'label': field, 'group': table['group'],
                               'tag': 'P-INPUTNUMBER', 'column_label': ''} for field in fields)
    sequence = 4
    for suffix, name, group in GRIDS:
        headers, pages = grid_fixture(suffix, name, group)
        target = next(f for f in forms if f['name'] == name)
        endpoint = ORIGIN + '/returnsheet/api/loadarticle2126/' + suffix + '-grid'
        metadata = {'name': suffix, 'group': group, 'headers': headers, 'endpoint': endpoint,
                    'source_total': 2, 'pages': [], 'footer_spans': []}
        if suffix not in ('l1b-bpa1', 'l2-bpa1'):
            metadata['footer_spans'] = appendix_table(name, group, 0, with_totals=True)[0]['footer_spans']
            if suffix == 'l3-bp21':
                metadata['footer_spans'] = [[], [4, 4, 1, 1, 4], [4, 4, 1, 1, 4]]
        for page in pages:
            row = deepcopy(page['payload']['Data'][0])
            for key in ('GrossIncome', 'IncomeTax', 'TaxRate'):
                row[key] = int(row[key])
            request = {**page['request'], 'Filters': [], 'SortField': '', 'SortOrder': 1}
            item = packet(TAX, {'Data': [row], 'TotalRecords': 2}, sequence=sequence, request=request)
            item['context']['url'] = endpoint
            bodies.append(item)
            metadata['pages'].append({'offset': request['First'], 'request_json': request, 'sequences': [sequence]})
            sequence += 1
        target['tables'].append(metadata)
    return record, bodies, forms
