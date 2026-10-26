"""Synthetic runs helpers; no collected tests or shared mutable test state."""
from copy import deepcopy


def fixture_run():
    rows = [('badan-normal', 'PPh Badan', 'Januari - Desember 2025', 'Normal'),
            ('badan-amendment', 'PPh Badan', 'Januari - Desember 2025', 'Amendment 001'),
            ('21-january', 'PPh Pasal 21/26', 'Januari 2025', 'Normal'),
            ('21-february', 'PPh Pasal 21/26', 'Februari 2025', 'Normal'),
            ('unifikasi', 'PPh Unifikasi', 'Januari 2025', 'Normal')]
    return {'npwp': '0000000000000001', 'year': 2025, 'year_basis': 'period',
            'taxpayer_name': 'SYNTHETIC TEST FIXTURE ONLY', 'complete': False,
            'started_at': 'fixture', 'audit': [], 'errors': [],
            'sources': synthetic_submitted_sources(),
            'records': [{'key': key, 'record_id': key, 'source_status': 'Fixture',
                         'meta': {'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': model},
                         'capture_complete': True, 'detail_url': '',
                         'sections': [{'name': 'Induk', 'text': '', 'tables': [],
                                       'fields': [({'label': 'Status Penyampaian', 'field': 'SubmitInProgressStatus',
                                                    'group': 'HEADER', 'value': key}
                                                   if tax == 'PPh Pasal 21/26' else
                                                   {'label': 'Masa Pajak', 'value': period}
                                                   if tax == 'PPh Unifikasi' else
                                                   {'label': '2. Nama', 'field': 'Name', 'group': 'A. IDENTITAS WAJIB PAJAK', 'value': key}
                                                   if tax == 'PPh Badan' else
                                                   {'label': 'Record marker', 'field': 'Marker', 'value': key})]}]}
                        for key, tax, period, model in rows]}


def synthetic_submitted_sources():
    return [{'url': 'https://coretax.intranet.pajak.go.id/returnsheets/id-ID/'
             'submitted-returnsheets/00000000-0000-4000-8000-000000000001',
             'label': 'SPT Dilaporkan'}]


MODELS = ('Normal', 'Pembetulan 1', 'Pembetulan 2')


def unifikasi_induk_table(amount):
    """Put an isolation sentinel in an inspected writable amount slot."""
    return {'name': 'PAJAK PENGHASILAN', 'group': 'B. PAJAK PENGHASILAN',
            'headers': ['NO', 'DETIL', 'SETOR SENDIRI'],
            'rows': [['1', 'Pasal 4 Ayat 2', str(amount)]],
            'body_row_count': 1, 'source_total': 1, 'complete': True,
            'footer': [], 'footer_spans': []}


def model_run(tax='PPh Badan', period='Januari - Desember 2025', models=MODELS):
    run = fixture_run()
    source = run['records'][0]
    records = []
    for ordinal, model in enumerate(models, 1):
        record = deepcopy(source)
        identifier = f'synthetic-model-return-{ordinal}'
        record.update(key=identifier, record_id=identifier)
        record['meta'].update({'Jenis Pajak': tax, 'Masa Pajak': period, 'Model SPT': model})
        record['sections'] = [
            {'name': form, 'text': '',
             'fields': [{'label': 'Synthetic record marker', 'field': 'FixtureMarker',
                         'value': f'SYNTHETIC {identifier} / {form}'}],
             'tables': [{'name': 'Synthetic duplicate source rows',
                         'headers': ['Kode', 'Nilai'],
                         'rows': [['00007', '1.234,50'], ['00007', '1.234,50']],
                         'complete': True}]}
            for form in ('Induk', 'L-Z')
        ]
        if tax == 'PPh Badan':
            record['sections'][0]['fields'][0].update(
                label='2. Nama', field='Name', group='A. IDENTITAS WAJIB PAJAK')
        if tax == 'PPh Pasal 21/26':
            record['sections'][0]['fields'][0].update(
                label='Status Penyampaian', field='SubmitInProgressStatus', group='HEADER')
        if tax == 'PPh Unifikasi':
            record['sections'][0]['tables'].append(unifikasi_induk_table(100 + ordinal))
        if tax == 'PPN':
            record['sections'][0]['fields'].append({
                'label': 'PPN kurang atau (lebih) bayar (III.A - III.B - III.C - III.D)',
                'field': '', 'value': str(100 + ordinal)})
        records.append(record)
    run.update(records=records, complete=True)
    return run
