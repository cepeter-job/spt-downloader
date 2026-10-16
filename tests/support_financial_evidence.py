"""Synthetic financial evidence helpers; no collected tests or shared mutable test state."""
import hashlib


PDF = b'%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n'


LABEL = 'Laporan Keuangan yang Telah Diaudit*'


def metadata(record_id, *, status='COMPLETE'):
    record_key = hashlib.sha256(record_id.encode('utf-8')).hexdigest()[:32]
    filename = hashlib.sha256(b'https://coretax.synthetic.invalid/existing/statement.pdf').hexdigest() + '.pdf'
    return {'label': LABEL, 'relative_path': f'attachments/{record_key}/{filename}',
            'status': status, 'bytes': len(PDF), 'hash': hashlib.sha256(PDF).hexdigest()}
