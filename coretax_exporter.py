"""Validasi data Coretax dan bentuk workbook tanpa mengubah nilai sumber.

Modul ini tidak mengakses browser. coretax.save_output menangani staging,
verifikasi, dan publikasi set workbook yang dihasilkan di sini.
"""
from pathlib import Path

from collections import Counter, defaultdict
from copy import deepcopy
from decimal import Decimal
import hashlib
import json
import math
import re
import sys
from urllib.parse import urlsplit
from openpyxl import Workbook
from coretax_pph21 import template_workbook, render_template_form
from coretax_masa_templates import (RESOURCES as MASA_RESOURCES,
                                    template_workbook as masa_template_workbook,
                                    render_template_form as render_masa_template, canonical_form)
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.worksheet.hyperlink import Hyperlink
from openpyxl.chart import BarChart, Reference
from openpyxl.utils import get_column_letter

NAVY, BLUE, PALE, GRAY = '17365D', '2463A0', 'EDF3FA', '64748B'
INVALID_XML_TEXT = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\ud800-\udfff\ufffe\uffff]')
FINANCIAL_LABELS = frozenset({
    'Laporan Keuangan', 'Laporan Keuangan yang Telah Diaudit*',
    'Laporan Keuangan/Laporan Keuangan yang Telah Diaudit*',
    'a. 1. Laporan Keuangan/Laporan Keuangan yang Telah Diaudit*',
})


def validate_scope(npwp, year):
    """Tolak NPWP yang bukan 16 digit ASCII persis dan tahun di luar kontrak."""
    if not isinstance(npwp, str) or not re.fullmatch(r'[0-9]{16}', npwp):
        raise ValueError('NPWP must be exactly 16 digits, without separators or spaces. The input is not normalized.')
    if not re.fullmatch(r'[0-9]{4}', str(year)) or not 1900 <= int(year) <= 2100:
        raise ValueError('Tax year must be four digits between 1900 and 2100.')
    return npwp, int(year)


def in_scope(meta, year, basis):
    """Tentukan tahun dari metadata teramati; format tak dikenal menjadi error."""
    if basis not in ('period', 'submission'):
        raise ValueError('Year basis must be period or submission.')
    value = meta.get('Masa Pajak' if basis == 'period' else 'Tanggal Submit SPT', '')
    if not isinstance(value, str):
        raise ValueError(f'Cannot establish {basis} year from non-text source metadata.')
    years = re.findall(r'(?<![0-9])(?:19|20|21)[0-9]{2}(?![0-9])', value)
    # Masa bulanan migrasi yang teramati memakai MM-MM-YYYY tanpa pemisah.
    # Tafsirkan akhiran tahun hanya pada pola tervalidasi; teks sumber tetap utuh.
    if not years and basis == 'period' and re.fullmatch(r'(?:0[1-9]|1[0-2]){2}(?:19|20|21)[0-9]{2}', value):
        years = [value[-4:]]
    if not years:
        raise ValueError(f'Cannot establish {basis} year from source value {value!r}; record not silently excluded.')
    return str(year) in years


def deduplicate_inventory(records, *, period_catalog=None, year=None):
    """Gabungkan kemunculan ID yang sama tanpa melebur pembetulan berbeda."""
    unique = {}
    for record in records:
        identifier = record['record_id']
        occurrence = {k: record[k] for k in ('key', 'source_status', 'list_url', 'list_page', 'row_position') if k in record}
        occurrence['meta'] = deepcopy(record['meta'])
        if identifier not in unique:
            unique[identifier] = {**record, 'meta': deepcopy(record['meta']), 'source_occurrences': [occurrence]}
        else:
            original = unique[identifier]
            for field in ('Jenis Pajak', 'Jenis Surat Pemberitahuan Pajak', 'Masa Pajak', 'Model SPT', 'Nomor Bukti Penerimaan', 'Tanggal Submit SPT'):
                if original['meta'].get(field, '') != record['meta'].get(field, ''):
                    if field == 'Masa Pajak':
                        from coretax_inventory import prove_period_equivalence
                        proof = prove_period_equivalence(original['meta'].get(field), record['meta'].get(field),
                                                         period_catalog, year)
                        if proof is not None:
                            original['period_equivalence'] = proof
                            continue
                    raise ValueError(f'Conflicting source metadata for SPT identifier {identifier}; no amendment is silently merged')
            original['source_occurrences'].append(occurrence)
    return list(unique.values())


def validate_excel_value(value, location, *, long_text=False):
    """Tolak nilai yang akan terpotong, berubah, atau gagal dibaca sebagai XLSX."""
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
            # Excel membatasi presisi 15 digit signifikan dengan floating-point biner.
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
        # Tunjukkan lokasi field tanpa menyertakan teks sumber rahasia dalam log.
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


def _validate_financial_attachments(record, scope, seen_paths):
    attachments = record.get('attachments', [])
    if not isinstance(attachments, list):
        raise ValueError('Financial attachments must be a list.')
    if not attachments:
        return
    identifier = record.get('record_id')
    if (not isinstance(identifier, str) or not identifier or len(identifier) > 512
            or record.get('scope') != scope or record['meta'].get('Jenis Pajak') != 'PPh Badan'):
        raise ValueError('Financial attachments require a bound corporate return and export scope.')
    validate_excel_value(identifier, 'financial attachment return identifier')
    record_key = hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:32]
    for attachment in attachments:
        if not isinstance(attachment, dict) or not isinstance(attachment.get('label'), str):
            raise ValueError('Financial attachment metadata or label is invalid.')
        validate_excel_value(attachment['label'], 'financial attachment label')
        status = attachment.get('status')
        size = attachment.get('bytes')
        path = attachment.get('relative_path')
        digest = attachment.get('hash')
        if status == 'PARTIAL':
            if (record.get('capture_complete') or type(size) is not int or size != 0
                    or path not in ('', None) or digest not in ('', None)):
                raise ValueError('PARTIAL financial attachments cannot declare a file or complete capture.')
            continue
        if (status != 'COMPLETE' or type(size) is not int or not 0 < size <= 20 * 1024 * 1024
                or not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest)
                or attachment['label'].strip() not in FINANCIAL_LABELS):
            raise ValueError('Financial PDF completion, byte count, hash or label is invalid.')
        # Pemeriksaan ini mengikat nama ke scope; publikasi tetap harus mengunci file
        # dan memeriksa byte serta hash yang sebenarnya. Deklarasi bersubfolder
        # lama tetap dapat dibaca tanpa menulis ulang bukti sumber.
        if (not isinstance(path, str)
                or not (re.fullmatch(r'LK_' + record_key + r'_[0-9a-f]{64}\.pdf', path)
                        or re.fullmatch(r'attachments/' + record_key + r'/[0-9a-f]{64}\.pdf', path))
                or path.casefold() in seen_paths):
            raise ValueError('Financial PDF path is unsafe, repeated or belongs to another return.')
        seen_paths.add(path.casefold())


def validate_export_run(run):
    """Periksa scope, flag kelengkapan, dan nilai sel sebelum menulis hasil."""
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
    seen_attachment_paths = set()
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
        _validate_financial_attachments(record, expected_scope, seen_attachment_paths)
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
    """Aktifkan hanya URL web; URL sumber lainnya disimpan sebagai teks literal."""
    if not isinstance(value, str) or re.search(r'[\s\\]', value):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme in ('http', 'https') and bool(parsed.hostname)
    except ValueError:
        return False


def put(ws, row, col, value):
    """Simpan teks sumber sebagai teks literal agar tidak menjadi formula Excel."""
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
    return record_sheet_titles(ordinal, record)[0]


def amendment_label(record):
    value = record['meta'].get('Model SPT', '')
    if value.casefold() == 'normal':
        return 'Normal'
    if re.search(r'pembetulan|amendment', value, re.I):
        number = re.search(r'[0-9]+', value)
        return 'Pembetulan' + (' ' + str(int(number.group())) if number else '')
    return re.sub(r'[\[\]:*?/\\]', '-', value)[:14] or 'Status belum ada'


def _display_sections(record, *, presentation=True):
    sections = record.get('sections', [])
    if presentation and record.get('meta', {}).get('Jenis Pajak') == 'PPh Badan':
        # Exclusion affects the new workbook only, never checkpoint custody.
        return [section for section in sections if section['name'] not in ('L10-B', 'L10-D')]
    return sections


def record_forms(record, *, presentation=True):
    sections = _display_sections(record, presentation=presentation)
    if not sections:
        return [('SPT', sections)]
    groups = {}
    for section in sections:
        # Jalur induk membedakan form dengan label anak yang sama.
        name = section['name']
        groups.setdefault(name, []).append(section)
    return list(groups.items())


def record_sheet_titles(ordinal, record, *, used=None, legacy=False, presentation=True):
    used = set() if used is None else used
    result = []
    for index, (form, _) in enumerate(record_forms(record, presentation=presentation), 1):
        form = re.sub(r'[\[\]:*?/\\]', '-', form)
        if legacy:
            # Exact historical names remain a valid physical proof, not a rename wildcard.
            prefix = f'{ordinal:03d}.{index:02d} {amendment_label(record)} '
            result.append((prefix + form)[:31])
            continue
        base = form[:31] or 'SPT'
        title = base
        number = 2
        while title.casefold() in used:
            suffix = f' ({number})'
            title = base[:31 - len(suffix)] + suffix
            number += 1
        used.add(title.casefold())
        result.append(title)
    return result


def workbook_sheet_titles(records, *, reserved=(), legacy=False, presentation=True):
    """One source-ordered namespace shared by writers, links and physical proof."""
    used = {title.casefold() for title in reserved}
    return [record_sheet_titles(ordinal, record, used=used, legacy=legacy, presentation=presentation)
            for ordinal, record in enumerate(records, 1)]


def workbook_groups(run, *, legacy=False):
    """Pemisahan model memakai identitas literal, bukan label pembetulan turunan."""
    groups, identities = {}, {}
    periodic = {'PPh Pasal 21/26': '21', 'PPh Unifikasi': 'Unifikasi', 'PPN': 'PPN'}
    for record in run['records']:
        tax = record['meta'].get('Jenis Pajak')
        filename = tax_type_filename(tax)
        period = record['meta'].get('Masa Pajak', '')
        if legacy:
            # Old physical proof stays readable; this branch never writes new exports.
            identity = (tax, period) if tax in periodic else (tax,)
            if tax in periodic:
                component = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', period).strip(' .')
                if not component or len(component) > 120:
                    raise ValueError('Unsupported source period filename')
                filename = f'SPT Masa {periodic[tax]}/{Path(filename).stem}_{component}.xlsx'
        else:
            model = record['meta'].get('Model SPT', '')
            identity = (tax, period, model)
            components = []
            for label, value in (('period', period), ('model', model)):
                if not isinstance(value, str):
                    raise ValueError(f'Unsupported source {label} filename')
                component = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', value).strip(' .')
                if not component or len(component) > 120:
                    raise ValueError(f'Unsupported source {label} filename')
                components.append(component)
            filename = f'{Path(filename).stem}_{components[0]}_{components[1]}.xlsx'
            if len(filename.encode('utf-16-le')) // 2 > 255:
                raise ValueError('Unsupported source period/model filename length')
            if tax in periodic:
                filename = f'SPT Masa {periodic[tax]}/{filename}'
        # Sanitasi nama Windows dapat menyamakan teks periode/model yang berbeda;
        # identitas literal tetap pembeda agar satu workbook tidak menimpa lainnya.
        folded = filename.casefold()
        if folded in identities and identities[folded] != identity:
            raise ValueError('Tax type, period or model filename collision; no workbook was overwritten')
        identities[folded] = identity
        groups.setdefault(filename, []).append(record)
    return groups


def numeric_analysis(value, label):
    """Nilai numerik opsional tanpa mengganti pengenal atau nilai sumber."""
    if not isinstance(value, str) or re.search(r'npwp|nik|nomor|kode|tanggal|rekening|faktur', label, re.I):
        return None
    if not re.search(r'nilai|jumlah|pendapatan|penghasilan|biaya|saldo|total|amount|revenue|dpp|harga|pajak', label, re.I):
        return None
    text = re.sub(r'^Rp\s*', '', value.strip(), flags=re.I)
    if not re.fullmatch(r'-?(?:[1-9][0-9]{0,2}(?:\.[0-9]{3})+|0|[1-9][0-9]*)(?:,[0-9]{1,2})?', text):
        return None
    try:
        source = Decimal(text.replace('.', '').replace(',', '.'))
        # Periksa presisi 15 digit pada nilai sumber sebelum konversi float.
        if Decimal(format(source, '.15g')) != source:
            return None
        number = float(source)
        validate_excel_value(number, 'numeric analysis')
        return number
    except (ValueError, OverflowError):
        return None


def render_form(detail, sections, ordinal, form_index, *, start_row=5):
    row, serial = start_row, 0
    def data_table(labels, values):
        nonlocal row, serial
        header(detail, row, labels)
        first = row
        row += 1
        for values_row in values:
            for col, value in enumerate(values_row, 1):
                put(detail, row, col, value)
            row += 1
        if row > first + 1:
            serial += 1
            table = Table(displayName=f'Data_{ordinal}_{form_index}_{serial}',
                ref=f'A{first}:{get_column_letter(len(labels))}{row-1}')
            table.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
            detail.add_table(table)
        row += 2
    for section in sections:
        put(detail, row, 1, section['name']).font = Font(bold=True, color=NAVY)
        row += 1
        fields = section.get('fields', [])
        if fields:
            values = []
            for field in fields:
                label = field.get('label') or field.get('field', '')
                raw = field.get('value', '')
                values.append([section['name'], label, raw, numeric_analysis(raw, label)])
            data_table(['Bagian', 'Field', 'Nilai sumber', 'Nilai numerik (opsional)'], values)
        for table in section.get('tables', []):
            put(detail, row, 1, table.get('name', 'Tabel'))
            row += 1
            width = max(len(table.get('headers', [])), max((len(r) for r in table.get('rows', [])), default=1))
            source_headers = table.get('headers') or [f'Kolom {i+1}' for i in range(width)]
            source_headers = source_headers + [f'Kolom {i+1}' for i in range(len(source_headers), width)]
            # Simpan label sumber terpisah ketika header filter perlu dibedakan.
            for col, value in enumerate(source_headers, 1):
                put(detail, row, col, value)
            row += 1
            numeric_cols = [i for i, label in enumerate(source_headers) if any(
                numeric_analysis(values[i] if i < len(values) else None, str(label)) is not None for values in table.get('rows', []))]
            captions = source_headers + [f'Numerik {i+1} ({source_headers[i]})' for i in numeric_cols]
            labels, used, seen = [], set(), Counter()
            for value in captions:
                caption = str(value) or 'Kolom'
                key = caption.casefold()
                seen[key] += 1
                label = caption if seen[key] == 1 else f'{caption} ({seen[key]})'
                # Label sumber dapat sama dengan hasil penambahan sufiks pada kolom lain.
                while label.casefold() in used:
                    seen[key] += 1
                    label = f'{caption} ({seen[key]})'
                used.add(label.casefold())
                labels.append(label)
            rows = []
            for values in table.get('rows', []):
                raw = list(values) + [''] * (width-len(values))
                rows.append(raw + [numeric_analysis(raw[i], str(source_headers[i])) for i in numeric_cols])
            data_table(labels, rows)
            if not table.get('complete', True):
                put(detail, row, 1, 'PARTIAL: paginasi tidak selesai')
                row += 1
        text = section.get('text', '')
        if text:
            put(detail, row, 1, 'Teks halaman / konteks sumber')
            row += 1
            for offset in range(0, len(text), 30000):
                put(detail, row, 1, text[offset:offset+30000])
                row += 1
    detail.print_title_rows = '1:3' if start_row == 5 else None
    detail.print_area = f'A1:{get_column_letter(max(detail.max_column, 4))}{max(row, 5)}'


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


def workbook_proof(run, *, presentation=True):
    """Keep scope and PDF custody declarations outside visible form cells."""
    meta_keys = ('Jenis Pajak', 'Jenis Surat Pemberitahuan Pajak', 'Masa Pajak',
                 'Model SPT', 'Nomor Bukti Penerimaan', 'Tanggal Submit SPT')
    records = []
    for record in run['records']:
        proof = {
            'meta': {key: record['meta'][key] for key in meta_keys if key in record['meta']},
            'capture_complete': record.get('capture_complete', False),
            'sections': [{'name': section['name']} for section in _display_sections(record, presentation=presentation)],
        }
        for key in ('record_id', 'scope', 'attachments', 'source_status'):
            if key in record:
                proof[key] = record[key]
        records.append(proof)
    return {'format': 'spt-downloader-forms', 'version': 1,
            'npwp': run['npwp'], 'year': run['year'], 'year_basis': run['year_basis'],
            'complete': run['complete'], 'records': records}


def _unique_proof_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate workbook proof key')
        result[key] = value
    return result


def read_workbook_proof(workbook):
    """Validate physical forms-only evidence; absent metadata permits legacy reads.

    This is a scope declaration, not a signature or proof of authentic tax data.
    Native PDF byte/hash custody is still required independently.
    """
    raw = workbook.properties.identifier
    if raw is None:
        return None
    try:
        proof = json.loads(raw, object_pairs_hook=_unique_proof_keys)
        required = {'format', 'version', 'npwp', 'year', 'year_basis', 'complete', 'records'}
        if (not isinstance(proof, dict) or set(proof) != required
                or proof['format'] != 'spt-downloader-forms'
                or type(proof['version']) is not int or proof['version'] != 1
                or not isinstance(proof['records'], list)):
            raise ValueError('Invalid workbook proof schema')
        allowed = {'meta', 'capture_complete', 'sections', 'record_id', 'scope',
                   'attachments', 'source_status'}
        for record in proof['records']:
            if (not isinstance(record, dict) or not set(record).issubset(allowed)
                    or not {'meta', 'capture_complete', 'sections'}.issubset(record)
                    or not isinstance(record['meta'], dict)
                    or not isinstance(record['sections'], list)
                    or any(not isinstance(section, dict) or set(section) != {'name'}
                           or not isinstance(section['name'], str) for section in record['sections'])):
                raise ValueError('Invalid workbook record proof')
        validate_export_run(proof)
        if workbook_proof(proof, presentation=False) != proof:
            raise ValueError('Workbook proof contains unsupported source metadata')
        # Bukti lama diperiksa terhadap sheet fisiknya; pengecualian tampilan
        # ekspor baru tidak boleh menghapus form dari pembuktian workbook lama.
        expected = [title for titles in workbook_sheet_titles(proof['records'], presentation=False) for title in titles]
        historical = [title for titles in workbook_sheet_titles(proof['records'], legacy=True, presentation=False)
                      for title in titles]
        if (workbook.sheetnames not in (expected, historical)
                or any(sheet.sheet_state != 'visible' for sheet in workbook)):
            raise ValueError('Workbook form sheets differ from their proof')
        workbook_groups(proof, legacy=True)
        return proof
    except (ValueError, TypeError, KeyError, AttributeError) as error:
        raise ValueError('Workbook scope/PDF proof cannot be verified') from error


def _export_form_workbook(run, path):
    reports = []
    title_plan = workbook_sheet_titles(run['records'])
    taxes = {record['meta']['Jenis Pajak'] for record in run['records']}
    tax = next(iter(taxes)) if len(taxes) == 1 else None
    if tax == 'PPh Pasal 21/26':
        wb, templates = template_workbook([title for titles in title_plan for title in titles])
    elif tax in MASA_RESOURCES:
        wb, templates = masa_template_workbook(tax, [title for titles in title_plan for title in titles])
    elif tax == 'PPh Badan':
        from coretax_badan_template import template_workbook as corporate_template_workbook
        from coretax_badan_template import render_template_form as render_corporate_template
        wb, templates = corporate_template_workbook([title for titles in title_plan for title in titles])
    else:
        wb = Workbook()
        wb.remove(wb.active)
        templates = {}
    wb.properties.identifier = json.dumps(workbook_proof(run), ensure_ascii=False,
                                          sort_keys=True, allow_nan=False)
    for ordinal, (record, titles) in enumerate(zip(run['records'], title_plan), 1):
        for form_index, (title, (form, sections)) in enumerate(
                zip(titles, record_forms(record)), 1):
            template = templates.get(canonical_form(tax, form))
            if template is not None:
                detail = wb.copy_worksheet(template)
                detail.title = title
                if tax == 'PPh Pasal 21/26':
                    report = render_template_form(detail, form, sections)
                elif tax == 'PPh Badan':
                    report = render_corporate_template(
                        detail, form, sections, period=record['meta'].get('Masa Pajak'))
                else:
                    report = render_masa_template(detail, tax, form, sections)
                if report is not None:
                    reports.append({'file': Path(path).name, 'form': form, **report})
            else:
                detail = wb.create_sheet(title)
                setup_sheet(detail, [36, 44, 36, 28, 28, 28, 28, 28, 28, 28, 28, 28], 'A3')
                detail.oddFooter.center.text = None
                render_form(detail, sections, ordinal, form_index, start_row=1)
                if tax == 'PPN':
                    reports.append({'file': Path(path).name, 'form': form, 'complete': False,
                                    'unmapped_fields': sum(len(s.get('fields', [])) for s in sections),
                                    'unmapped_tables': sum(len(s.get('tables', [])) for s in sections)})
    for template in templates.values():
        wb.remove(template)
    if templates:
        wb.active = 0
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    wb.close()
    return reports


def export_workbook(run, path, *, include_details=True, detail_targets=None, resume_file=None,
                    include_administration=True):
    validate_export_run(run)
    if not include_administration:
        if not include_details or not run['records']:
            raise ValueError('A forms-only workbook requires selected return details')
        return _export_form_workbook(run, path)
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
    mapping_reports = run.get('template_mapping', [])
    if mapping_reports:
        put(summary, 23, 1, 'Pemetaan template pengambilan terbaru')
        put(summary, 23, 2, 'COMPLETE' if all(r['complete'] for r in mapping_reports) else 'PARTIAL')
        header(audit, ar, ['Status / Objek', 'Field belum dipetakan', 'Tabel belum dipetakan',
                           'Baris belum dipetakan', 'Hasil', 'Keterangan'])
        ar += 1
        for report in mapping_reports:
            reviewed_note = ''
            if report.get('reviewed_redundant_fields') or report.get('reviewed_redundant_tables'):
                reviewed_note = (f" {report.get('reviewed_redundant_fields', 0)} field dan "
                    f"{report.get('reviewed_redundant_tables', 0)} tabel disetujui sebagai tampilan redundan; "
                    'hitungan belum dipetakan tetap mencakupnya.')
            derivation_note = {
                'missing_average': ' DER belum dihitung: saldo rata-rata utang atau modal belum tersedia.',
                'unsafe_average': ' DER belum dihitung: saldo rata-rata utang atau modal bukan angka Excel yang aman.',
                'zero_capital_average': ' DER belum dihitung: saldo rata-rata modal nol.',
            }.get(report.get('derived_reason'), '') if report.get('derived_complete') is False else ''
            values = ['Pemetaan template', report.get('unmapped_fields', 0),
                      report.get('unmapped_tables', 0), report.get('unmapped_rows', 0),
                      'COMPLETE' if report['complete'] else 'PARTIAL',
                      f"{report['file']} / {report['form']}: jumlah field/tabel/baris belum dipetakan; lihat capture sumber pada checkpoint job.{reviewed_note}{derivation_note}"]
            for col, value in enumerate(values, 1):
                put(audit, ar, col, value)
            ar += 1
    if any(record.get('attachments') for record in records):
        header(audit, ar, ['ID SPT', 'Lampiran PDF', 'Status', 'Byte', 'SHA-256', 'Berkas relatif'])
        ar += 1
        for record in records:
            for attachment in record.get('attachments', []):
                values = [record['record_id'], attachment['label'], attachment['status'],
                          attachment['bytes'], attachment.get('hash'), attachment.get('relative_path')]
                for col, value in enumerate(values, 1):
                    cell = put(audit, ar, col, value)
                    if col == 6 and attachment['status'] == 'COMPLETE':
                        cell.hyperlink = value
                        cell.font = Font(color=BLUE, underline='single')
                ar += 1
    title_groups = workbook_sheet_titles(records, reserved=wb.sheetnames) if include_details else []
    for ordinal, record in enumerate(records, 1):
        meta = record['meta']
        url = record.get('detail_url', '')
        if include_details:
            title_label, scope_label = detail_labels(run, record)
            titles = title_groups[ordinal - 1]
            for form_index, (sheet_title, (_, sections)) in enumerate(zip(titles, record_forms(record)), 1):
                detail = wb.create_sheet(sheet_title)
                setup_sheet(detail, [36, 44, 36, 28, 28, 28, 28, 28, 28, 28, 28, 28], 'A6')
                band(detail, 1, title_label, 12)
                back = put(detail, 2, 1, 'Resume' if resume_file else 'Daftar SPT')
                if resume_file:
                    back.hyperlink = Hyperlink(ref=back.coordinate, target=resume_file, location="'Daftar SPT'!A1")
                else:
                    back.hyperlink = "#'Daftar SPT'!A1"
                back.font = Font(color=BLUE, underline='single')
                put(detail, 2, 2, scope_label)
                if url:
                    source_cell = put(detail, 3, 1, url)
                    if web_source_url(url):
                        source_cell.hyperlink = url
                render_form(detail, sections, ordinal, form_index)
            # Indeks selalu menarget form pertama sesuai urutan sumber.
            detail = wb[titles[0]]
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


def export_split_workbooks(run, folder, *, mapping_reports=None):
    """Buat resume, workbook masa, dan form Badan; publikasi ditangani pemanggil."""
    validate_export_run(run)
    folder = Path(folder)
    groups = workbook_groups(run)
    for records in groups.values():
        validate_excel_value(type_scope_description(run, records[0]['meta']['Jenis Pajak']), 'type scope description')
    targets = {}
    reports = []
    files = {'resume.xlsx': folder / 'resume.xlsx'}
    ordinals = {id(record): index for index, record in enumerate(run['records'], 1)}
    for filename, records in groups.items():
        for record, titles in zip(records, workbook_sheet_titles(records)):
            global_ordinal = ordinals[id(record)]
            targets[global_ordinal] = (filename, titles[0])
        group_run = {**run, 'records': records,
            'scope_description': type_scope_description(run, records[0]['meta']['Jenis Pajak'])}
        path = folder / filename
        reports.extend(export_workbook(group_run, path, include_administration=False))
        files[filename] = path
    if mapping_reports is not None:
        mapping_reports.extend(reports)
    export_workbook({**run, 'template_mapping': reports}, files['resume.xlsx'],
                    include_details=False, detail_targets=targets)
    return files
