"""Create a data-free OOXML presentation resource from the approved workbook.

This standalone package operation uses no product code or workbook engine.
Only the closed static-caption map survives; dynamic cells retain styles only.
"""
from pathlib import Path
import argparse
import hashlib
import zipfile
import xml.etree.ElementTree as ET

M = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
P = 'http://schemas.openxmlformats.org/package/2006/relationships'
C = 'http://schemas.openxmlformats.org/drawingml/2006/chart'
ET.register_namespace('', M)
ET.register_namespace('r', R)

CAPTIONS = {
    'xl/worksheets/sheet1.xml': {
        'A1': 'Laporan Sedot SPT', 'A2': 'NPWP', 'A3': 'Tahun',
        'A4': 'Wajib Pajak', 'A5': 'Dasar Tahun', 'A6': 'Status',
        'A7': 'Total Pilihan SPT', 'A8': 'SPT disedot status COMPLETE', 'A9': 'Waktu mulai',
        'A13': 'Jenis Pajak', 'B13': 'Jumlah SPT',
        'A18': 'mapping template sedot terbaru',
    },
    'xl/worksheets/sheet2.xml': {
        'A1': 'DAFTAR SPT',
        'A2': 'Klik nomor untuk membuka file SPT terpisah. Simpan semua file Excel dalam satu folder.',
        **{f'{col}4': value for col, value in zip('ABCDEFGHIJK', (
            'No.', 'Jenis Pajak', 'Jenis SPT', 'Masa Pajak', 'Model / Pembetulan',
            'Status Daftar', 'Bukti Penerimaan', 'Tanggal Submit', 'Hasil Capture',
            'Bagian', 'URL Sumber'))},
    },
    'xl/worksheets/sheet3.xml': {
        'A1': 'AUDIT | Kelengkapan',
        **{f'{col}3': value for col, value in zip('ABCDEF', (
            'Status / Objek', 'Total sumber', 'Baris dibaca', 'Dipilih', 'Hasil', 'Keterangan'))},
        **{f'{col}10': value for col, value in zip('ABCDEF', (
            'Status / Objek', 'Field belum dipetakan', 'Tabel belum dipetakan',
            'Baris belum dipetakan', 'Hasil', 'Keterangan'))},
    },
}


def sanitize(source, destination):
    with zipfile.ZipFile(source) as archive:
        if archive.testzip() is not None:
            raise ValueError('Invalid template package')
        parts = {name: archive.read(name) for name in archive.namelist()}
    allowed = {
        '[Content_Types].xml', '_rels/.rels', 'docProps/core.xml', 'docProps/app.xml',
        'xl/workbook.xml', 'xl/_rels/workbook.xml.rels', 'xl/styles.xml',
        'xl/sharedStrings.xml', 'xl/theme/theme1.xml', 'xl/tables/table1.xml',
        'xl/drawings/drawing1.xml', 'xl/drawings/_rels/drawing1.xml.rels',
        'xl/charts/chart1.xml', 'xl/worksheets/_rels/sheet1.xml.rels',
        'xl/worksheets/_rels/sheet2.xml.rels', 'xl/worksheets/_rels/sheet3.xml.rels',
        'xl/printerSettings/printerSettings1.bin', *CAPTIONS,
    }
    if set(parts) - allowed:
        raise ValueError('Unreviewed template package part')
    removed = {'xl/sharedStrings.xml', 'xl/printerSettings/printerSettings1.bin'}
    removed |= {name for name in parts if name.startswith('docProps/')}
    output = {}
    for name, raw in parts.items():
        if name in removed:
            continue
        root = ET.fromstring(raw)
        if name in CAPTIONS:
            for cell in root.findall(f'.//{{{M}}}sheetData/{{{M}}}row/{{{M}}}c'):
                for child in list(cell):
                    cell.remove(child)
                cell.attrib.pop('t', None)
                value = CAPTIONS[name].get(cell.get('r'))
                if value is not None:
                    cell.set('t', 'inlineStr')
                    ET.SubElement(ET.SubElement(cell, f'{{{M}}}is'), f'{{{M}}}t').text = value
            links = root.find(f'{{{M}}}hyperlinks')
            if links is not None:
                root.remove(links)
            setup = root.find(f'{{{M}}}pageSetup')
            if setup is not None:
                setup.attrib.pop(f'{{{R}}}id', None)
            # No hidden operational data, comments, inputs or custom extensions.
            if any(root.findall(f'{{{M}}}{tag}') for tag in
                   ('extLst', 'legacyDrawing', 'dataValidations', 'conditionalFormatting')):
                raise ValueError('Unreviewed worksheet metadata')
        if name.endswith('.rels'):
            for relation in list(root):
                kind = relation.get('Type', '').rsplit('/', 1)[-1]
                if kind in ('hyperlink', 'printerSettings', 'sharedStrings', 'core-properties', 'extended-properties'):
                    root.remove(relation)
                elif relation.get('TargetMode') == 'External':
                    raise ValueError('Unreviewed external relationship')
            if not len(root):
                continue
        if name == '[Content_Types].xml':
            for item in list(root):
                if item.get('PartName', '').lstrip('/') in removed or item.get('Extension') == 'bin':
                    root.remove(item)
        if name == 'xl/charts/chart1.xml':
            for parent in root.iter():
                for child in list(parent):
                    if child.tag in {f'{{{C}}}{t}' for t in ('strCache', 'numCache', 'multiLvlStrCache')}:
                        parent.remove(child)
        output[name] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, 'w', zipfile.ZIP_DEFLATED) as archive:
        for name, raw in output.items():
            archive.writestr(name, raw)
    # Detect accidental retention in chart metadata or another non-cell part.
    if 'xl/sharedStrings.xml' in parts:
        approved = {text for cells in CAPTIONS.values() for text in cells.values()}
        approved.add('SPT menurut jenis pajak')
        original_strings = [''.join(item.itertext())
                            for item in ET.fromstring(parts['xl/sharedStrings.xml'])]
        retained = {node.text for raw in output.values() for node in ET.fromstring(raw).iter()}
        if any(len(text) >= 8 and text not in approved and text in retained
               for text in original_strings):
            destination.unlink()
            raise ValueError('Unapproved original string remains in sanitized package')
    # Do not emit any source values, source filename or source metadata.
    print(f'Sanitized {len(output)} parts; SHA256 {hashlib.sha256(destination.read_bytes()).hexdigest()}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    sanitize(args.source, args.destination)
