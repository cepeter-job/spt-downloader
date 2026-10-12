"""Read-only Coretax SPT exporter; implementation developed test-first."""
from pathlib import Path
from collections import Counter, defaultdict
from decimal import Decimal
import math
import re
import sys
from urllib.parse import urlsplit
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter

NAVY, BLUE, PALE, GRAY = '17365D', '2463A0', 'EDF3FA', '64748B'
INVALID_XML_TEXT = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')


def validate_scope(npwp, year):
    if not isinstance(npwp, str) or not re.fullmatch(r'[0-9]{16}', npwp):
        raise ValueError('NPWP must be exactly 16 digits, without separators or spaces. The input is not normalized.')
    if not re.fullmatch(r'[0-9]{4}', str(year)) or not 1900 <= int(year) <= 2100:
        raise ValueError('Tax year must be four digits between 1900 and 2100.')
    return npwp, int(year)


def in_scope(meta, year, basis):
    if basis not in ('period', 'submission'):
        raise ValueError('Year basis must be period or submission.')
    value = meta.get('Masa Pajak' if basis == 'period' else 'Tanggal Submit SPT', '')
    if not isinstance(value, str):
        raise ValueError(f'Cannot establish {basis} year from non-text source metadata.')
    years = re.findall(r'(?<![0-9])(?:19|20|21)[0-9]{2}(?![0-9])', value)
    # Observed migrated monthly periods use MM-MM-YYYY without separators.
    # Interpret only the validated year suffix; preserve the original source text.
    if not years and basis == 'period' and re.fullmatch(r'(?:0[1-9]|1[0-2]){2}(?:19|20|21)[0-9]{2}', value):
        years = [value[-4:]]
    if not years:
        raise ValueError(f'Cannot establish {basis} year from source value {value!r}; record not silently excluded.')
    return str(year) in years


def deduplicate_inventory(records):
    unique = {}
    for record in records:
        identifier = record['record_id']
        occurrence = {k: record[k] for k in ('key', 'source_status', 'list_url', 'list_page', 'row_position') if k in record}
        if identifier not in unique:
            unique[identifier] = {**record, 'source_occurrences': [occurrence]}
        else:
            original = unique[identifier]
            for field in ('Jenis Pajak', 'Jenis Surat Pemberitahuan Pajak', 'Masa Pajak', 'Model SPT', 'Nomor Bukti Penerimaan', 'Tanggal Submit SPT'):
                if original['meta'].get(field, '') != record['meta'].get(field, ''):
                    raise ValueError(f'Conflicting source metadata for SPT identifier {identifier}; no amendment is silently merged')
            original['source_occurrences'].append(occurrence)
    return list(unique.values())


def validate_excel_value(value, location, *, long_text=False):
    """Reject source values that XLSX would truncate, alter or fail to read."""
    reason = None
    if isinstance(value, str):
        if INVALID_XML_TEXT.search(value):
            reason = 'source text contains characters forbidden by XML'
        elif not long_text and len(value) > 32767:
            reason = 'source text exceeds the 32,767-character cell limit'
    elif isinstance(value, bool) or value is None:
        return
    elif isinstance(value, int):
        try:
            # Excel supports 15 significant digits and binary floating-point storage.
            if Decimal('%.15g' % value) != value or float(value) != value:
                reason = 'numeric digits would be rounded; preserve the source as text'
        except (OverflowError, ValueError):
            reason = 'number exceeds the supported numeric range'
    elif isinstance(value, float):
        if (not math.isfinite(value) or 0 < abs(value) < sys.float_info.min
                or value == 0 and math.copysign(1, value) < 0
                or float('%.15g' % value) != value):
            reason = 'number exceeds Excel precision or range, or has an unsupported sign'
    else:
        reason = 'source cell has an unsupported value type'
    if reason:
        # Identify the field without including confidential source text in logs.
        raise ValueError(f'Cannot represent {location} exactly in Excel: {reason}.')


def detail_labels(run, record):
    meta = record['meta']
    title = re.sub(r'[\[\]:*?/\\]', '-', meta.get('Jenis Pajak', 'SPT'))
    return (
        f"{meta.get('Jenis Surat Pemberitahuan Pajak', title)} | {meta.get('Masa Pajak', '')}",
        f"NPWP {run['npwp']} | {meta.get('Model SPT', '')} | {record.get('source_status', '')}",
    )


def type_scope_description(run, tax):
    return (f'Rincian khusus {tax}. Ringkasan seluruh jenis SPT ada di resume.xlsx. '
            'Audit mencatat keseluruhan proses. ' + run.get('scope_description', ''))


def validate_export_run(run):
    """Preflight scope, completion and source cells before any output is written."""
    validate_scope(run.get('npwp'), run.get('year'))
    basis = run.get('year_basis')
    if basis not in ('period', 'submission'):
        raise ValueError('Year basis must be period or submission.')
    if type(run.get('complete')) is not bool:
        raise ValueError('Run complete must be a boolean, not a truthy value.')
    if 'inventory_complete' in run:
        if type(run['inventory_complete']) is not bool:
            raise ValueError('Run inventory_complete must be a boolean.')
        if run['complete'] and not run['inventory_complete']:
            raise ValueError('A COMPLETE run cannot have incomplete inventory.')
    if run['complete'] and run.get('errors'):
        raise ValueError('A COMPLETE run cannot contain capture errors.')
    for key in ('npwp', 'year', 'taxpayer_name', 'started_at', 'scope_description'):
        validate_excel_value(run.get(key, ''), key)
    for entry in run.get('audit', []):
        for key in ('status', 'total', 'scanned', 'selected', 'result', 'note'):
            validate_excel_value(entry.get(key), f'audit.{key}')
    for error in run.get('errors', []):
        validate_excel_value(error.get('object', 'Run'), 'error.object')
        validate_excel_value(error.get('message', str(error)), 'error.message')
    expected_scope = [run['npwp'], run['year'], basis]
    seen_identifiers = set()
    for ordinal, record in enumerate(run['records'], 1):
        location = f'record {ordinal}'
        meta = record['meta']
        if 'record_id' in record:
            if record['record_id'] in seen_identifiers:
                raise ValueError(f'Duplicate return identifier at {location}; count cannot be certified.')
            seen_identifiers.add(record['record_id'])
        if 'scope' in record and record['scope'] != expected_scope:
            raise ValueError(f'{location} scope differs from the export scope.')
        if not in_scope(meta, run['year'], basis):
            raise ValueError(f'{location} year is outside the selected export scope.')
        captured = record.get('capture_complete', False)
        if type(captured) is not bool:
            raise ValueError(f'{location} capture_complete must be a boolean.')
        if run['complete'] and not captured:
            raise ValueError(f'A COMPLETE run contains an incomplete capture at {location}.')
        for key in ('Jenis Pajak', 'Jenis Surat Pemberitahuan Pajak', 'Masa Pajak',
                    'Model SPT', 'Nomor Bukti Penerimaan', 'Tanggal Submit SPT'):
            validate_excel_value(meta.get(key, ''), f'{location} metadata.{key}')
        for key in ('source_status', 'detail_url'):
            validate_excel_value(record.get(key, ''), f'{location}.{key}')
        for label in detail_labels(run, record):
            validate_excel_value(label, f'{location} combined source label')
        for section in record.get('sections', []):
            validate_excel_value(section['name'], f'{location} section name')
            validate_excel_value(section.get('text', ''), f'{location} page context', long_text=True)
            for field in section.get('fields', []):
                validate_excel_value(field.get('label') or field.get('field', ''), f'{location} field label')
                validate_excel_value(field.get('value', ''), f'{location} field value')
            for table in section.get('tables', []):
                complete = table.get('complete', True)
                if type(complete) is not bool or captured and not complete:
                    raise ValueError(f'{location} capture completion contradicts a table completion flag.')
                validate_excel_value(table.get('name', 'Tabel'), f'{location} table name')
                for value in table.get('headers', []):
                    validate_excel_value(value, f'{location} table header')
                for row in table.get('rows', []):
                    for value in row:
                        validate_excel_value(value, f'{location} table cell')


def web_source_url(value):
    """Only web navigation becomes active; all other source URLs stay literal."""
    if not isinstance(value, str) or re.search(r'[\s\\]', value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False


def put(ws, row, col, value):
    """Store untrusted source text literally, never as an Excel formula."""
    validate_excel_value(value, f'{ws.title}!{get_column_letter(col)}{row}')
    cell = ws.cell(row, col)
    cell.value = value if value is not None else ''
    if isinstance(value, str):
        cell.data_type = 's'
        cell.number_format = '@'
    cell.alignment = Alignment(vertical='top', wrap_text=True)
    return cell


def band(ws, row, text, cols=8, color=NAVY):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=cols)
    c = put(ws, row, 1, text)
    c.fill = PatternFill('solid', fgColor=color)
    c.font = Font(name='Calibri', size=12, bold=True, color='FFFFFF')
    ws.row_dimensions[row].height = 28


def setup_sheet(ws, widths, freeze='A5'):
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = freeze
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_options.horizontalCentered = False
    ws.oddFooter.center.text = 'Coretax | Confidential | &P / &N'
    for i, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = width


def header(ws, row, labels):
    for col, label in enumerate(labels, 1):
        c = put(ws, row, col, label)
        c.font = Font(bold=True, color='FFFFFF')
        c.fill = PatternFill('solid', fgColor=BLUE)
    ws.row_dimensions[row].height = 36


def detail_sheet_title(ordinal, record):
    title = re.sub(r'[\[\]:*?/\\]', '-', record['meta'].get('Jenis Pajak', 'SPT'))
    return f'{ordinal:03d} {title}'[:31]


def tax_type_filename(tax_type):
    names = {'PPh Badan': 'SPT_Badan.xlsx', 'PPh Pasal 21/26': 'SPT_21.xlsx',
             'PPh Unifikasi': 'SPT_Unifikasi.xlsx'}
    if not isinstance(tax_type, str) or not tax_type.strip():
        raise ValueError('Missing tax type; cannot choose a type workbook')
    if tax_type in names:
        return names[tax_type]
    title = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', tax_type)
    title = re.sub(r'\s+', '_', title).strip(' .')
    return f'SPT_{title}.xlsx'


def export_workbook(run, path, *, include_details=True, detail_targets=None, resume_file=None):
    validate_export_run(run)
    wb = Workbook()
    summary = wb.active
    summary.title = 'Ringkasan'
    setup_sheet(summary, [30, 58, 20, 20, 20, 20, 20, 20], 'A12')
    band(summary, 1, 'CORETAX | EKSPOR SPT')
    put(summary, 2, 1, 'READ-ONLY • Data perpajakan rahasia / Confidential')
    records = run['records']
    captured = sum(bool(r.get('capture_complete')) for r in records)
    for row, label, value in [(4, 'NPWP', run['npwp']), (5, 'Tahun', run['year']),
                              (6, 'Wajib Pajak', run.get('taxpayer_name', '')),
                              (7, 'Dasar Tahun', 'Masa/Tahun Pajak' if run['year_basis'] == 'period' else 'Tanggal Submit SPT'),
                              (8, 'Status', 'COMPLETE' if run['complete'] else 'PARTIAL'),
                              (9, 'SPT dalam lingkup', len(records)),
                              (10, 'SPT berhasil ditangkap', captured),
                              (11, 'Waktu mulai', run.get('started_at', ''))]:
        put(summary, row, 1, label).font = Font(bold=True, color=NAVY)
        put(summary, row, 2, value)
    summary['B8'].fill = PatternFill('solid', fgColor='DDF1E2' if run['complete'] else 'FFE5CC')
    put(summary, 13, 1, 'Ruang lingkup')
    summary.merge_cells('B13:H14')
    put(summary, 13, 2, run.get('scope_description', 'Semua status SPT yang tersedia, jenis SPT dan pembetulan dalam tahun pilihan. Isi halaman, tab, dan tabel ditangkap; isi file lampiran/PDF dan dialog rincian per baris tidak termasuk. Lihat Audit untuk batasan dan kegagalan.'))
    summary.row_dimensions[13].height = 46
    header(summary, 16, ['Jenis Pajak', 'Jumlah SPT'])
    counts = Counter(r['meta'].get('Jenis Pajak', 'Tidak diketahui') for r in records)
    for row, (tax, count) in enumerate(sorted(counts.items()), 17):
        put(summary, row, 1, tax)
        put(summary, row, 2, count)
    if counts:
        chart = BarChart()
        chart.title = 'SPT menurut jenis pajak'
        chart.add_data(Reference(summary, min_col=2, min_row=16, max_row=16 + len(counts)), titles_from_data=True)
        chart.set_categories(Reference(summary, min_col=1, min_row=17, max_row=16 + len(counts)))
        chart.width, chart.height = 18, 9
        summary.add_chart(chart, 'D16')
    index = wb.create_sheet('Daftar SPT')
    setup_sheet(index, [8, 23, 40, 23, 24, 23, 36, 20, 28, 18, 45], 'D5')
    band(index, 1, f"DAFTAR SPT | {run['year']} | {run['npwp']}", 11)
    index.merge_cells('A2:K2')
    index.row_dimensions[2].height = 30
    put(index, 2, 1, 'Klik nomor untuk membuka lembar detail; tautan sumber membuka Coretax.' if include_details else 'Klik nomor untuk membuka file SPT terpisah. Simpan semua file Excel dalam satu folder.')
    columns = ['No.', 'Jenis Pajak', 'Jenis SPT', 'Masa Pajak', 'Model / Pembetulan', 'Status Daftar', 'Bukti Penerimaan', 'Tanggal Submit', 'Hasil Capture', 'Bagian', 'URL Sumber']
    header(index, 4, columns)
    audit = wb.create_sheet('Audit')
    setup_sheet(audit, [26, 18, 18, 18, 55, 80], 'A5')
    band(audit, 1, 'AUDIT | Kelengkapan & Batasan', 6)
    header(audit, 4, ['Status / Objek', 'Total sumber', 'Baris dibaca', 'Dipilih', 'Hasil', 'Keterangan'])
    for i, entry in enumerate(run.get('audit', []), 5):
        values = [entry.get('status', ''), entry.get('total'), entry.get('scanned'), entry.get('selected'), entry.get('result', ''), entry.get('note', '')]
        for j, value in enumerate(values, 1):
            put(audit, i, j, value)
    ar = audit.max_row + 1
    for error in run.get('errors', []):
        put(audit, ar, 1, error.get('object', 'Run'))
        put(audit, ar, 5, 'ERROR / PARTIAL')
        put(audit, ar, 6, error.get('message', str(error)))
        ar += 1
    for ordinal, record in enumerate(records, 1):
        meta = record['meta']
        url = record.get('detail_url', '')
        if include_details:
            title_label, scope_label = detail_labels(run, record)
            detail = wb.create_sheet(detail_sheet_title(ordinal, record))
            setup_sheet(detail, [12, 36, 28, 25, 25, 25, 25, 25, 25, 25, 25, 25], 'C6')
            band(detail, 1, title_label, 12)
            back = put(detail, 2, 1, 'Resume' if resume_file else 'Daftar SPT')
            if resume_file:
                back.hyperlink = Hyperlink(ref=back.coordinate, target=resume_file, location="'Daftar SPT'!A1")
            else:
                back.hyperlink = "#'Daftar SPT'!A1"
            back.font = Font(color=BLUE, underline='single')
            detail.merge_cells('B2:L2')
            put(detail, 2, 2, scope_label)
            detail.merge_cells('A3:L3')
            if url:
                source_cell = put(detail, 3, 1, url)
                if web_source_url(url):
                    source_cell.hyperlink = url
            row = 5
            for section in record.get('sections', []):
                band(detail, row, section['name'], 12, BLUE)
                row += 1
                for field in section.get('fields', []):
                    detail.merge_cells(start_row=row, start_column=1, end_row=row, end_column=5)
                    put(detail, row, 1, field.get('label') or field.get('field', '')).font = Font(color=NAVY)
                    detail.merge_cells(start_row=row, start_column=6, end_row=row, end_column=12)
                    put(detail, row, 6, field.get('value', ''))
                    detail.row_dimensions[row].height = 30
                    row += 1
                for table in section.get('tables', []):
                    row += 1
                    width = max(len(table.get('headers', [])), max((len(r) for r in table.get('rows', [])), default=1))
                    band(detail, row, table.get('name', 'Tabel'), max(12, width), GRAY)
                    row += 1
                    headers = table.get('headers') or [f'Kolom {i+1}' for i in range(width)]
                    header(detail, row, headers)
                    row += 1
                    for values in table.get('rows', []):
                        for col, value in enumerate(values, 1):
                            put(detail, row, col, value)
                            if col > 12:
                                detail.column_dimensions[get_column_letter(col)].width = 25
                        detail.row_dimensions[row].height = 36
                        row += 1
                    if not table.get('complete', True):
                        put(detail, row, 1, 'PARTIAL: paginasi tidak selesai')
                        row += 1
                # Keep visible text to preserve captions, declarations and non-input figures.
                text = section.get('text', '')
                if text:
                    row += 1
                    band(detail, row, 'Teks halaman / konteks sumber', 12, GRAY)
                    row += 1
                    for offset in range(0, len(text), 30000):
                        detail.merge_cells(start_row=row, start_column=1, end_row=row, end_column=12)
                        put(detail, row, 1, text[offset:offset+30000])
                        detail.row_dimensions[row].height = min(220, max(40, text[offset:offset+30000].count('\n') * 12))
                        row += 1
                row += 2
            detail.print_title_rows = '1:3'
            detail.print_area = f'A1:{get_column_letter(max(detail.max_column, 12))}{max(row, 5)}'
        ir = ordinal + 4
        values = [ordinal, meta.get('Jenis Pajak', ''), meta.get('Jenis Surat Pemberitahuan Pajak', ''), meta.get('Masa Pajak', ''), meta.get('Model SPT', ''), record.get('source_status', ''), meta.get('Nomor Bukti Penerimaan', ''), meta.get('Tanggal Submit SPT', ''), 'OK' if record.get('capture_complete') else 'PARTIAL', len(record.get('sections', [])), url]
        for col, value in enumerate(values, 1):
            put(index, ir, col, value)
        if include_details:
            index.cell(ir, 1).hyperlink = f"#'{detail.title.replace(chr(39), chr(39)*2)}'!A1"
        elif detail_targets and ordinal in detail_targets:
            filename, sheet_title = detail_targets[ordinal]
            index.cell(ir, 1).hyperlink = Hyperlink(ref=index.cell(ir, 1).coordinate,
                target=filename, location=f"'{sheet_title.replace(chr(39), chr(39)*2)}'!A1")
        if web_source_url(url):
            index.cell(ir, 11).hyperlink = url
        index.row_dimensions[ir].height = 36
    if records:
        table = Table(displayName='SPTIndex', ref=f'A4:K{4+len(records)}')
        table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
        index.add_table(table)
    for ws in [summary, index, audit]:
        ws.print_area = f'A1:{get_column_letter(ws.max_column)}{ws.max_row}'
    index.print_title_rows = '1:4'
    audit.print_title_rows = '1:4'
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def export_split_workbooks(run, folder):
    validate_export_run(run)
    folder = Path(folder)
    groups = defaultdict(list)
    for ordinal, record in enumerate(run['records'], 1):
        groups[record['meta'].get('Jenis Pajak')].append((ordinal, record))
    filenames = {tax: tax_type_filename(tax) for tax in groups}
    # Windows filenames are case-insensitive: reject a collision before any write.
    normalized = [name.casefold() for name in filenames.values()]
    if len(normalized) != len(set(normalized)):
        raise ValueError('Tax type filename collision; no workbook was overwritten')
    for tax in groups:
        validate_excel_value(type_scope_description(run, tax), 'type scope description')
    targets = {}
    files = {'resume.xlsx': folder / 'resume.xlsx'}
    for tax, entries in groups.items():
        filename = filenames[tax]
        for local_ordinal, (global_ordinal, record) in enumerate(entries, 1):
            targets[global_ordinal] = (filename, detail_sheet_title(local_ordinal, record))
        group_run = {**run, 'records': [record for _, record in entries],
            'scope_description': type_scope_description(run, tax)}
        path = folder / filename
        export_workbook(group_run, path, resume_file='resume.xlsx')
        files[filename] = path
    export_workbook(run, files['resume.xlsx'], include_details=False, detail_targets=targets)
    return files
