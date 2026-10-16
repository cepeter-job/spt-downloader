"""Synthetic financial publication helpers; no collected tests or shared mutable test state."""
import hashlib
from support_runs import fixture_run
import coretax_exporter as exporter
from support_runs import model_run


PDF = b'%PDF-1.7\n1 0 obj\n(ORIGINAL SYNTHETIC FIXTURE)\nendobj\n%%EOF\n'


CHANGED_PDF = PDF.replace(b'ORIGINAL', b'MUTATION')


def declare_pdf(record, folder, data=PDF):
    record['scope'] = ['0000000000000001', 2025, 'period']
    key = hashlib.sha256(record['record_id'].encode()).hexdigest()[:32]
    url = 'https://coretax.synthetic.invalid/pdf/' + record['record_id']
    relative = 'attachments/' + key + '/' + hashlib.sha256(url.encode()).hexdigest() + '.pdf'
    record['attachments'] = [{'label': 'Laporan Keuangan', 'relative_path': relative,
                              'status': 'COMPLETE', 'bytes': len(data),
                              'hash': hashlib.sha256(data).hexdigest()}]
    path = folder / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


def financial_run(folder, count=1, data=PDF):
    run = fixture_run()
    run['records'] = run['records'][:count]
    run['inventory_complete'] = True
    run['complete'] = True
    for record in run['records']:
        declare_pdf(record, folder, data)
    return run


def physical_bytes(folder):
    return {path.relative_to(folder).as_posix(): path.read_bytes()
            for path in folder.rglob('*') if path.is_file()}


def legacy_export(downloads, *, format_name):
    run = model_run()
    target = downloads / (run['npwp'] + ' - ' + run['taxpayer_name']) / '2025' / '20250102-030405-000006-synthetic'
    target.mkdir(parents=True)
    for record in run['records']:
        declare_pdf(record, target)
    exporter.export_workbook(run, target / 'SPT_Badan.xlsx',
                             include_administration=format_name == 'legacy')
    targets = {ordinal: ('SPT_Badan.xlsx', name) for ordinal, name in enumerate(
        ['Induk', 'Induk (2)', 'Induk (3)'], 1)}
    exporter.export_workbook(run, target / 'resume.xlsx', include_details=False, detail_targets=targets)
    return run, target
