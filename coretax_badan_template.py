"""Approved corporate layout; ambiguous source blocks remain visible evidence."""
from copy import copy
from decimal import Decimal
from pathlib import Path
import math
import re

from openpyxl.cell.cell import MergedCell
from openpyxl.styles import Border, Color, Side

from coretax_template_cells import load_template_workbook, _write, _grow, _raw_evidence

FORMS = ['L1-D', 'L2', 'L3', 'L4', 'L6', 'L7', 'L9', 'L10-A', 'L10-C',
         'L11-A', 'L11-B', 'L11-C']
ACCOUNTING = '_-[$Rp-421]* #,##0_-;\\-[$Rp-421]* #,##0_-;_-[$Rp-421]* "-"??_-;_-@_-'
ACCOUNTING_LITERAL = '_-"Rp"* #,##0_-;\\-"Rp"* #,##0_-;_-"Rp"* "-"??_-;_-@_-'
ACCOUNTING_WHOLE = ACCOUNTING_LITERAL
# Header and reserved body boundaries in the approved, sanitized reference.
BLOCKS = {
    'l1-d': [(5, 6, 39), (42, 43, 68), (71, 72, 100)],
    'l2': [(2, 3, 8), (12, 13, 21)],
    'l3': [(2, 3, 3), (7, 8, 4661)],
    'l4': [(2, 3, 3), (8, 9, 9)],
    'l6': [], 'l7': [(2, 3, 12)],
    'l9': [(4, 5, 187), (192, 193, 193), (198, 199, 199),
           (204, 205, 205), (210, 211, 211), (216, 217, 217),
           (222, 223, 223), (231, 232, 232), (237, 238, 238),
           (243, 244, 244), (249, 250, 250), (255, 256, 256)],
    'l10-a': [(2, 3, 33)], 'l10-c': [(2, 3, 3)],
    'l11-a': [(3, 4, 4), (7, 8, 292), (296, 297, 297),
              (300, 301, 301), (304, 305, 305)],
    'l11-b': [(11, 12, 12), (17, 18, 22), (30, 31, 31)],
    'l11-c': [(2, 3, 3)],
}


def template_workbook(reserved_titles):
    reserved_titles = list(reserved_titles)
    resource = Path(__file__).resolve().parent / 'resources/corporate_format.xlsx'
    workbook, templates = load_template_workbook(resource, FORMS, reserved_titles)
    reserved = {title.casefold() for title in [*reserved_titles, *workbook.sheetnames]}
    for form in ('induk', 'l8'):
        counter = 0
        while f'_reference_{counter}'.casefold() in reserved:
            counter += 1
        sheet = workbook.create_sheet(f'_reference_{counter}')
        reserved.add(sheet.title.casefold())
        templates[form] = sheet
    return workbook, templates


def _present(value):
    return value is not None and bool(str(value).strip())


def _clean_report(fields, tables, **derived):
    unresolved = [table for table in tables if table.get('rows') or not table.get('complete', True)]
    return {'complete': not fields and not unresolved and derived.get('derived_complete', True),
            'unmapped_fields': len(fields), 'unmapped_tables': len(unresolved),
            'unmapped_rows': sum(len(table.get('rows', [])) for table in unresolved), **derived}


# Approved clean Induk captions. Match the observed owner, field and caption
# together; an ordinal, repeated value or JSON alias is never binding evidence.
_INDUK_IDENTITY = [
    ('HEADER', 'TaxYear', 'Tahun Pajak/Bagian Tahun Pajak'),
    ('HEADER', 'Status', 'Status'),
    ('HEADER', 'AccountingPeriodStart', 'Periode Pembukuan'),
    ('HEADER', 'AccountingPeriodEnd', 'Periode Pembukuan'),
    ('A. IDENTITAS WAJIB PAJAK', 'Tin', '1. NPWP'),
    ('A. IDENTITAS WAJIB PAJAK', 'Name', '2. Nama'),
    ('B. INFORMASI LAPORAN KEUANGAN', 'TinAccountant', '2.b. NPWP Kantor Akuntan Publik'),
    ('B. INFORMASI LAPORAN KEUANGAN', 'NameAccountant', '2.c. Nama Kantor Akuntan Publik'),
    ('A. IDENTITAS WAJIB PAJAK', 'EmailAddress', '3. Alamat Email'),
    ('A. IDENTITAS WAJIB PAJAK', 'PhoneNumber', '4. Nomor Telepon'),
]
_INDUK_CALCULATIONS = [
    ('D. PENGHITUNGAN PPh', '', '4. Penghasilan Neto Fiskal sebelum Fasilitas Pajak'),
    ('D. PENGHITUNGAN PPh', '', '7. Penghasilan Neto Fiskal Setelah Fasilitas Pajak'),
    ('D. PENGHITUNGAN PPh', '', '9. Penghasilan Kena Pajak'),
    ('D. PENGHITUNGAN PPh', '', '12. PPh Terutang'),
    ('E. PENGURANG PPh TERUTANG', '', '13. Apakah terdapat kredit pajak yang dibayarkan di luar negeri dan/atau dipotong/pungut oleh pihak lain? / Tidak / Ya'),
    ('E. PENGURANG PPh TERUTANG', '', '14. Angsuran PPh Pasal 25'),
    ('E. PENGURANG PPh TERUTANG', '', '15. Surat Tagihan Pajak PPh Pasal 25 (hanya pokok pajak)'),
    ('E. PENGURANG PPh TERUTANG', '', '16. Apakah Wajib Pajak memperoleh Fasilitas Pengurangan PPh Badan? * / Tidak / Ya'),
    ('F. PPh KURANG/LEBIH BAYAR', '', '17.a. PPh yang Kurang/Lebih Bayar'),
    ('F. PPh KURANG/LEBIH BAYAR', '', '17.b. Apakah terdapat Surat Keputusan Persetujuan Pengangsuran atau Penundaan Pembayaran Pajak? / Tidak / Ya'),
    ('F. PPh KURANG/LEBIH BAYAR', '', '17.c. PPh yang masih harus dibayar atau lebih dibayar'),
    ('F. PPh KURANG/LEBIH BAYAR', '', 'Ganti SPT sebelumnya'),
    ('F. PPh KURANG/LEBIH BAYAR', '', '18.a. PPh yang kurang atau lebih bayar pada SPT yang dibetulkan / Ganti SPT sebelumnya'),
    ('F. PPh KURANG/LEBIH BAYAR', '', '18.b. PPh yang kurang atau lebih bayar karena pembetulan'),
    ('D. PENGHITUNGAN PPh', 'TaxRate', '11. Tarif Pajak *'),
]
_L8_GROUP = ('PERHITUNGAN FASILITAS PENGURANGAN TARIF PPh BAGI WAJIB PAJAK BADAN '
             'DALAM NEGERI BERDASARKAN PASAL 31E AYAT (1) UNDANG-UNDANG PPh')
_L8_HEADERS = ['NO.', 'DESKRIPSI', 'AMOUNT (Rupiah)']


def _clean_page(sheet, widths):
    for column, width in widths.items():
        sheet.column_dimensions[column].width = width
    sheet.page_setup.paperSize = '8'
    sheet.page_setup.orientation = 'landscape'
    sheet.page_setup.fitToHeight = 0


def _thin_grid(sheet, first, last, width):
    side = Side(style='thin', color=Color(indexed=64))
    border = Border(left=side, right=side, top=side, bottom=side)
    for cells in sheet.iter_rows(min_row=first, max_row=last, min_col=1, max_col=width):
        for cell in cells:
            if not isinstance(cell, MergedCell):
                cell.border = border


def _induk(sheet, sections):
    _clean_page(sheet, {'A': 110.7109375, 'B': 49.7109375, 'C': 36})
    sheet.column_dimensions['B'].bestFit = True
    _write(sheet, 1, 1, 'INDUK')
    _write(sheet, 1, 2, None)
    title_font = copy(sheet['A1'].font)
    title_font.bold = True
    sheet['A1'].font = title_font
    fields = [field for section in sections for field in section.get('fields', [])]
    used, blocks = set(), []
    for slots, strip_number in ((_INDUK_IDENTITY, False), (_INDUK_CALCULATIONS, True)):
        output = []
        for group, name, caption in slots:
            matches = [(index, field) for index, field in enumerate(fields)
                       if (field.get('group'), field.get('field', ''), field.get('label'))
                       == (group, name, caption)]
            if len(matches) != 1:
                continue
            index, field = matches[0]
            used.add(index)
            if _present(field.get('value')):
                label = re.sub(r'^[0-9]+(?:\.[a-z])?\.\s+', '', caption) if strip_number else caption
                kind = ('money' if strip_number and name != 'TaxRate' and caption != 'Ganti SPT sebelumnya'
                        else 'tariff' if name == 'TaxRate' else 'choice' if strip_number else 'identity')
                output.append((index, label, field['value'], kind))
        blocks.append(output)
    row = 2
    for index, block in enumerate(blocks):
        if index and blocks[0] and block:
            row += 2  # Approved identity/calculation separator.
        first = row
        for field_index, caption, value, kind in block:
            _write(sheet, row, 1, caption)
            if kind == 'money':
                if not _write_amount(sheet, row, 2, value):
                    used.remove(field_index)
                sheet.cell(row, 2).number_format = ACCOUNTING_LITERAL
            else:
                if kind == 'tariff' and isinstance(value, str):
                    value = re.sub(r'^[0-9]+\.(?=\s*[A-Za-z])\s*', '', value, count=1)
                _write(sheet, row, 2, value)
                if kind == 'choice':
                    sheet.cell(row, 2).number_format = ACCOUNTING_LITERAL
            row += 1
        if block:
            _thin_grid(sheet, first, row - 1, 2)
    return _clean_report([field for index, field in enumerate(fields) if index not in used],
                         [{**table, 'complete': False} for section in sections
                          for table in section.get('tables', [])])


def _l8_body(table, count):
    rows = table['rows'][:count]
    if not any(key in table for key in ('source_structure', 'body_spans', 'body_rowspans')):
        return [(list(values), False) for values in rows] if all(len(values) == 3 for values in rows) else None
    if (table.get('source_structure') != {'form': 'L8', 'component': 'rsh-citr-l8-form-grid1', 'groups': [_L8_GROUP]}
            or type(table.get('pages')) is not int or table['pages'] != 1):
        return None
    spans, rowspans = table.get('body_spans'), table.get('body_rowspans')
    if (not isinstance(spans, list) or not isinstance(rowspans, list)
            or len(spans) != count or len(rowspans) != count):
        return None
    result = []
    for values, columns, heights in zip(rows, spans, rowspans):
        if (not isinstance(columns, list) or not isinstance(heights, list)
                or len(columns) != len(values) or len(heights) != len(values)
                or any(type(span) is not int for span in columns)
                or any(type(span) is not int or span != 1 for span in heights)):
            return None
        if columns == [1, 2]:
            # C belongs to the observed merged caption; it is not a missing amount.
            result.append(([values[0], values[1], None], True))
        elif columns == [1, 1, 1]:
            result.append((list(values), False))
        else:
            return None
    return result


def _l8(sheet, sections):
    _clean_page(sheet, {'A': 4.42578125, 'B': 96.28515625, 'C': 36})
    for column in ('A', 'B'):
        sheet.column_dimensions[column].bestFit = True
    for column, caption in enumerate(_L8_HEADERS, 1):
        _write(sheet, 1, column, caption)
        _write(sheet, 2, column, None)
    sheet['C2'].number_format = ACCOUNTING_WHOLE
    fields = [field for section in sections for field in section.get('fields', [])]
    tables = [table for section in sections for table in section.get('tables', [])]
    matches = [table for table in tables if table.get('group') == _L8_GROUP
               and table.get('headers') == _L8_HEADERS]
    pending = [{**table, 'complete': False} for table in tables]
    merges = []
    if len(matches) == 1:
        table = matches[0]
        rows, footer = table.get('rows', []), table.get('footer', [])
        count = table.get('body_row_count', len(rows))
        if (table.get('complete', True) and type(count) is int and 0 <= count <= len(rows)
                and rows[count:] == footer and len(rows) == count + len(footer)
                and table.get('source_total', count) in (None, count)
                and len(footer) <= 1 and table.get('footer_spans', []) == [[1, 1, 1]] * len(footer)
                and all(len(values) == 3 for values in footer)):
            body = _l8_body(table, count)
        else:
            body = None
        if body is not None:
            pending = [{**item, 'complete': False} for item in tables if item is not table]
            body = [(values, merged) for values, merged in body if any(map(_present, values))]
            output = body + ([(['', '', ''], False)] if not body else []) + [(values, False) for values in footer]
            for row, (values, merged) in enumerate(output, 2):
                _write(sheet, row, 1, values[0])
                _write(sheet, row, 2, values[1])
                if merged:
                    merges.append(row)
                    continue
                safe = _write_amount(sheet, row, 3, values[2])
                sheet.cell(row, 3).number_format = ACCOUNTING_WHOLE
                if not safe:
                    pending.append({**table, 'rows': [values], 'complete': False})
    _thin_grid(sheet, 1, sheet.max_row, 3)
    for row in merges:
        sheet.merge_cells(start_row=row, start_column=2, end_row=row, end_column=3)
    return _clean_report(fields, pending)


def _remove_rows(sheet, first, count):
    """Delete an approved body range while moving merges and row dimensions."""
    last = first + count - 1
    moving = [copy(region) for region in sheet.merged_cells.ranges if region.max_row >= first]
    if any(region.min_row < first <= region.max_row or region.min_row <= last < region.max_row
           for region in moving):
        raise ValueError('Pemadatan body memotong merge template.')
    for region in moving:
        sheet.unmerge_cells(str(region))
    dimensions = [(row, sheet.row_dimensions.pop(row)) for row in list(sheet.row_dimensions) if row >= first]
    sheet.delete_rows(first, count)
    for row, dimension in dimensions:
        if row > last:
            dimension.index = row - count
            sheet.row_dimensions[row - count] = dimension
    for region in moving:
        if region.min_row > last:
            region.shift(row_shift=-count)
            sheet.merge_cells(str(region))


def _compact_layout(sheet, form, deleted, der_row, averages):
    # Mapping is completed against original reference geometry first. Remove
    # only known body empties, in descending runs, so account-heading merges
    # travel with their captured rows instead of being guessed at a new index.
    if form == 'l1-d':
        deleted.update(range(1, 5))
    ordered = sorted(deleted)
    runs = []
    for row in ordered:
        if runs and runs[-1][0] + runs[-1][1] == row:
            runs[-1][1] += 1
        else:
            runs.append([row, 1])
    for first, count in reversed(runs):
        _remove_rows(sheet, first, count)

    def moved(row):
        return row - sum(old < row for old in ordered)

    return moved(der_row), {index: re.sub(r'[0-9]+$', lambda match: str(moved(int(match[0]))), address)
                            for index, address in averages.items()}


def _label(value):
    return ' '.join(str(value or '').split()).casefold()


def _columns(table, sheet, header):
    labels = {column: _label(sheet.cell(header, column).value)
              for column in range(1, sheet.max_column + 1)
              if sheet.cell(header, column).value is not None}
    keys = [_label(value) for value in table.get('headers', [])]
    if (not keys or not all(keys) or len(keys) != len(set(keys))
            or len(labels) != len(set(labels.values())) or set(keys) != set(labels.values())):
        return None
    targets = {value: column for column, value in labels.items()}
    return [targets[key] for key in keys]


def _write_amount(sheet, row, column, value, *, subtract=False):
    # Display precision never rounds or rewrites the captured numeric value.
    sheet.cell(row, column).number_format = ACCOUNTING
    text = value
    if isinstance(text, str):
        if text in ('', 'Rp.', 'Rp'):
            _write(sheet, row, column, None)
            return True
        marker = re.fullmatch(r'Rp\.?\s*\|\s*([^|]+)', text)
        if marker:
            text = marker.group(1)
        if not re.fullmatch(r'-?(?:[1-9][0-9]{0,2}(?:\.[0-9]{3})+|0|[1-9][0-9]*)(?:,[0-9]{1,2})?', text):
            _write(sheet, row, column, value)
            return False
        number = Decimal(text.replace('.', '').replace(',', '.'))
    elif type(text) in (int, float):
        number = Decimal(str(text))
    elif text is None:
        _write(sheet, row, column, None)
        return True
    else:
        _write(sheet, row, column, value)
        return False
    if not number.is_finite() or Decimal(format(number, '.15g')) != number:
        _write(sheet, row, column, value)
        return False
    converted = float(number)
    if not math.isfinite(converted):
        _write(sheet, row, column, value)
        return False
    _write(sheet, row, column, -abs(converted) if subtract else converted)
    return True


def _write_percentage(sheet, row, column, value):
    # Captured L2 values are percentage points, including four decimal places.
    # Currency markers and malformed locale syntax are not percentage aliases.
    if value is None or value == '':
        _write(sheet, row, column, None)
        return True
    if isinstance(value, str):
        if not re.fullmatch(r'-?(?:[1-9][0-9]{0,2}(?:\.[0-9]{3})+|0|[1-9][0-9]*)(?:,[0-9]{1,4})?', value):
            _write(sheet, row, column, value)
            return False
        number = Decimal(value.replace('.', '').replace(',', '.'))
    elif type(value) in (int, float):
        number = Decimal(str(value))
    else:
        _write(sheet, row, column, value)
        return False
    # Guard before division, so Decimal context cannot round a long source.
    if not number.is_finite() or Decimal(format(number, '.15g')) != number:
        _write(sheet, row, column, value)
        return False
    fraction = number / 100
    converted = float(fraction)
    if not math.isfinite(converted) or (converted == 0 and fraction != 0):
        _write(sheet, row, column, value)
        return False
    _write(sheet, row, column, converted)
    return True


def _l1d_role(table):
    structure = table.get('source_structure')
    if structure is None:
        return None
    if not isinstance(structure, dict) or structure.get('form') != 'L1-D':
        return -1
    roles = {
        'rsh-citr-l1d-grid1': (0, ['A. LAPORAN LABA RUGI']),
        'rsh-citr-l1d-grid2': (1, ['B. LAPORAN POSISI KEUANGAN']),
        'rsh-citr-l1d-grid3': (2, ['B. LAPORAN POSISI KEUANGAN']),
    }
    index, groups = roles.get(structure.get('component'), (-1, None))
    return index if structure.get('groups') == groups else -1


def _l9_role(table):
    structure = table.get('source_structure')
    if structure is None:
        return None
    if not isinstance(structure, dict) or structure.get('form') != 'L9':
        return -1
    groups = ['KELOMPOK 1', 'KELOMPOK 2', 'KELOMPOK 3', 'KELOMPOK 4', 'LAINNYA']
    roles = [('grid1', 'HARTA BERWUJUD', group) for group in groups]
    roles += [('grid2', 'BANGUNAN', 'PERMANEN'), ('grid2', 'BANGUNAN', 'TIDAK PERMANEN')]
    roles += [('grid3', 'HARTA TIDAK BERWUJUD', group) for group in groups]
    for index, (component, outer, inner) in enumerate(roles):
        inspected_groups = [[outer, inner]]
        if inner == 'LAINNYA':
            inspected_groups.append([outer, 'KELOMPOK LAINNYA'])
        if (structure.get('component') == 'rshshr-citr-l9-form-' + component
                and structure.get('groups') in inspected_groups):
            return index
    return -1


def _scalar_fields(sheet, form, fields):
    anchors = {
        'l1-d': [(2, 2), (3, 2)],
        'l6': [(row, 2) for row in range(2, 9)],
        'l11-b': [(row, 2) for row in range(2, 8)],
        'l9': [(row, 8) for row in (226, 227, 228, 259, 260, 261)],
    }
    slots = {}
    for row, column in anchors.get(form, []):
        label = _label(sheet.cell(row, 1).value)
        if label:
            slots.setdefault(label, []).append((row, column))
    grouped = {}
    for field in fields:
        grouped.setdefault(_label(field.get('label')), []).append(field)
    pending = []
    for label, items in grouped.items():
        matches = slots.get(label, [])
        if len(items) != 1 or len(matches) != 1 or type(items[0].get('value')) is bool:
            pending.extend(items)
            continue
        row, column = matches[0]
        if form == 'l1-d':
            _write(sheet, row, column, items[0].get('value'))
        elif not _write_amount(sheet, row, column, items[0].get('value')):
            pending.extend(items)
    return pending


def _money_columns(sheet, form, header, columns, block):
    if form == 'l1-d':
        return {3, 4, 5, 6, 7, 8, 10} if sheet.cell(header, 4).value else {3}
    # These approved captions omit a normal currency marker. This is reached
    # only after exact template-header binding, never by fuzzy source aliases.
    explicit = {('l11-a', 1): {5}, ('l11-b', 2): {2, 3, 4, 5}}
    return explicit.get((form, block), set()) | {
        column for column in columns
        if re.search(r'\((?:rp\.?|rupiah)\)', str(sheet.cell(header, column).value), re.I)}


def _footer_plan(sheet, form, block, table, target, money, columns):
    footer = table.get('footer', [])
    if not footer:
        return []
    # Colspans describe physical source columns; do not reorder them by guess.
    if columns != list(range(1, len(table['headers']) + 1)):
        return None
    spans = table.get('footer_spans', [])
    capacity = 3 if (form, block) == ('l3', 1) else 1
    if len(footer) > capacity or len(spans) != len(footer):
        return None
    result = []
    for index, (values, widths) in enumerate(zip(footer, spans)):
        row = target + index
        if (len(values) != len(widths)
                or any(type(span) is not int or span < 1 for span in widths)
                or sum(widths) != len(table['headers'])):
            return None
        if not any(value not in ('', None) for value in values):
            continue
        # These captions were sanitized out of the reference. Accept only the
        # observed form/slot caption, never an arbitrary label in a blank cell.
        captions = {}
        if form == 'l1-d':
            caption = ['Laba (Rugi) Sebelum Pajak', 'Jumlah Aset',
                       'Jumlah Liabilitas dan Ekuitas'][block]
            if widths != [1] * len(columns) or _label(values[1]) != _label(caption):
                return None
            captions[2] = caption
        elif (form, block, index) == ('l3', 1, 1):
            captions[1] = 'KREDIT PAJAK LUAR NEGERI'
        column, claimed = 1, set()
        for value, span in zip(values, widths):
            if value not in ('', None):
                if span == 1 and column in money:
                    destination, numeric = column, True
                elif form == 'l1-d' and column == 1 and span == 1:
                    destination, numeric = column, False
                else:
                    # A blank source prefix may share the template's merged
                    # label. A second nonempty value may not claim that label.
                    candidates = set(range(column, column + span))
                    for region in sheet.merged_cells.ranges:
                        if (region.min_row == region.max_row == row
                                and region.min_col <= column
                                and column + span - 1 <= region.max_col):
                            candidates.add(region.min_col)
                    labels = [c for c in candidates
                              if not isinstance(sheet.cell(row, c), MergedCell)
                              and (sheet.cell(row, c).value or captions.get(c))
                              and _label(sheet.cell(row, c).value or captions.get(c)) == _label(value)]
                    if len(labels) != 1:
                        return None
                    destination, numeric = labels[0], False
                if destination in claimed or isinstance(sheet.cell(row, destination), MergedCell):
                    return None
                claimed.add(destination)
                result.append((index, destination, value, numeric))
            column += span
    return result


def _accounting_format(sheet, form):
    for row in sheet:
        for cell in row:
            if not isinstance(cell, MergedCell) and 'Rp' in cell.number_format and '*' in cell.number_format:
                cell.number_format = cell.number_format.replace('0.00', '0')
    ranges = {
        'l2': ['E13:E21', 'G13:G22', 'J13:J22', 'G3:G9', 'I3:I9'],
        'l3': ['E8:E4662', 'F8:F4664'],
        'l6': ['B2:B8'], 'l7': ['C1:I13'],
        'l9': ['D5:E187', 'H5:H188', 'D193:E193', 'G193:H194',
               'H226:H228', 'H259:H261'],
        'l10-a': ['G3:G33'], 'l11-a': ['E8:E292'],
        'l11-b': ['B2:B7', 'D12:P13', 'B18:N23'],
    }
    # The approved reference's rupiah accounting display; only number format
    # changes. Apply before growth so copied rows inherit these formats.
    for area in ranges.get(form, []):
        for row in sheet[area]:
            for cell in row:
                if not isinstance(cell, MergedCell):
                    cell.number_format = ACCOUNTING
    if form == 'l2':
        for area in ('H3:H9', 'F1:F21'):
            for row in sheet[area]:
                for cell in row:
                    if not isinstance(cell, MergedCell):
                        cell.number_format = '0.00%'
    elif form == 'l3':
        for address in ('F4', 'G4', 'J4'):
            sheet[address].number_format = ACCOUNTING_LITERAL


def _l11b_der(sheet, row, averages):
    cells = [sheet[averages[index]] if index in averages else None for index in (0, 1)]
    values = [cell.value if cell is not None else None for cell in cells]
    if any(value in (None, '') for value in values):
        reason = 'missing_average'
    elif any(type(value) not in (int, float) or not math.isfinite(value) for value in values):
        reason = 'unsafe_average'
    elif values[1] == 0:
        reason = 'zero_capital_average'
    else:
        # Formula references are generated only from verified captured footer
        # cells, never source formula strings or recomputed body totals.
        sheet.cell(row, 3).value = '=' + cells[0].coordinate
        sheet.cell(row + 1, 3).value = '=' + cells[1].coordinate
        sheet.cell(row, 4).value = f'=C{row}/C{row + 1}'
        return {'derived_complete': True}
    # Keep derivation availability separate from actual unmapped source counts.
    return {'derived_complete': False, 'derived_reason': reason}


def _body_plan(sheet, form, first, last, columns, rows):
    merges = list(sheet.merged_cells.ranges)
    style_row = next((row for row in range(first, last + 1)
                      if not any(region.min_row <= row <= region.max_row for region in merges)), first)
    result = []
    for index, values in enumerate(rows):
        row = first + index if first + index <= last else style_row
        cells = dict(zip(columns, values))
        for region in merges:
            if not region.min_row <= row <= region.max_row:
                continue
            # The inspected account heading is blank code + one description.
            # Do not collapse two nonempty account values into a merged cell.
            if (form != 'l1-d' or region.min_row != region.max_row
                    or (region.min_col, region.max_col) != (1, 2)
                    or cells.get(1) not in ('', None) or 2 not in cells):
                return None, style_row
            cells[1] = cells.pop(2)
        result.append(cells)
    return result, style_row


def _current_l7_header(sheet, sections, period):
    match = re.fullmatch(r'Januari - Desember ([0-9]{4})', period or '')
    if not match:
        return
    caption = f'KOMPENSASI KERUGIAN FISKAL / {match[1]} / TAHUN PAJAK INI - NILAI (Rp)'
    tables = [table for section in sections for table in section.get('tables', [])]
    # The reference's year-bearing slot is blank deliberately. Populate it only
    # from the single captured table whose other headers and literal year agree.
    if len(tables) != 1 or not tables[0].get('complete', True):
        return
    headers = tables[0].get('headers', [])
    reference = [sheet.cell(2, column).value for column in range(1, 10)]
    if reference[7] is not None:
        return
    reference[7] = caption
    if (len(headers) == 9 and len(set(map(_label, headers))) == 9
            and set(map(_label, headers)) == set(map(_label, reference))):
        captured_caption = next(header for header in headers if _label(header) == _label(caption))
        _write(sheet, 2, 8, captured_caption)


def render_template_form(sheet, form, sections, *, period=None):
    form = form.casefold()
    if form == 'induk':
        return _induk(sheet, sections)
    if form == 'l8':
        return _l8(sheet, sections)
    _accounting_format(sheet, form)
    if form == 'l7':
        _current_l7_header(sheet, sections, period)
    der_row, averages = 26, {}
    if form == 'l11-b':
        _write(sheet, der_row, 1, 'PERHITUNGAN DER')
        _write(sheet, der_row, 2, 'Jumlah Saldo Rata-Rata Utang')
        _write(sheet, der_row + 1, 2, 'Jumlah Saldo Rata-Rata Modal')
        sheet.cell(der_row, 4).number_format = '0.00'
    blocks = BLOCKS[form]
    grouped = [[] for _ in blocks]
    fields = [field for section in sections for field in section.get('fields', [])]
    fields = _scalar_fields(sheet, form, fields)
    if form == 'l6':
        _thin_grid(sheet, 2, 8, 2)
    pending = []
    for section in sections:
        for table in section.get('tables', []):
            rows = table.get('rows', [])
            count = table.get('body_row_count', len(rows))
            footer = table.get('footer', [])
            candidates = [(index, _columns(table, sheet, header))
                          for index, (header, _, _) in enumerate(blocks)]
            candidates = [(index, columns) for index, columns in candidates if columns]
            role = (_l1d_role(table) if form == 'l1-d' else
                    _l9_role(table) if form == 'l9' else None)
            if role is not None:
                candidates = [(index, columns) for index, columns in candidates if index == role]
            if (not table.get('complete', True) or len(candidates) != 1
                    or type(count) is not int or count < 0 or count > len(rows)
                    or rows[count:] != footer or len(rows) != count + len(footer)
                    or table.get('source_total', count) not in (None, count)
                    or any(len(row) != len(table.get('headers', [])) for row in rows[:count])):
                pending.append({**table, 'complete': False})
                continue
            index, columns = candidates[0]
            grouped[index].append((table, columns, rows[:count]))
    offset, deleted = 0, set()
    for block, ((header, first, last), items) in enumerate(zip(blocks, grouped)):
        header, first, last = header + offset, first + offset, last + offset
        if len(items) != 1:
            pending.extend({**table, 'complete': False} for table, _, _ in items)
            deleted.update(range(first + 1, last + 1))
            continue
        table, columns, rows = items[0]
        money = _money_columns(sheet, form, header, columns, block)
        percentages = {column for column in columns
                       if form == 'l2' and '%' in str(sheet.cell(header, column).value)}
        footer_numbers = money | percentages
        foot = _footer_plan(sheet, form, block, table, last + 1, footer_numbers, columns)
        body, style_row = _body_plan(sheet, form, first, last, columns, rows)
        if foot is None or body is None:
            pending.append({**table, 'complete': False})
            deleted.update(range(first + 1, last + 1))
            continue
        extra = max(0, len(rows) - (last - first + 1))
        _grow(sheet, last + 1, extra, style_row)
        occupied = {first + index for index, values in enumerate(rows) if any(map(_present, values))}
        if not occupied:
            occupied.add(first)
        deleted.update(set(range(first, last + extra + 1)) - occupied)
        if form == 'l11-b' and last + 1 <= der_row:
            der_row += extra
        for index, cells in enumerate(body):
            row, safe = first + index, True
            for column, value in cells.items():
                if column in percentages:
                    safe = _write_percentage(sheet, row, column, value) and safe
                elif column in money:
                    subtract = (form == 'l1-d' and _l1d_role(table) == 1 and column == 3
                                and _label(cells.get(2)) == _label(
                                    'Dikurangi: Akumulasi penyusutan aset tetap dan inventaris'))
                    safe = _write_amount(sheet, row, column, value, subtract=subtract) and safe
                    if form == 'l9' and block >= 2 and column == 8 and _present(value):
                        sheet.cell(row, column).number_format = ACCOUNTING_WHOLE
                else:
                    _write(sheet, row, column, value)
            if not safe:
                pending.append({**table, 'rows': [rows[index]], 'complete': False})
        footer_safe = True
        for row_offset, column, value, numeric in foot:
            row = last + extra + 1 + row_offset
            if numeric:
                writer = _write_percentage if column in percentages else _write_amount
                footer_safe = writer(sheet, row, column, value) and footer_safe
                if form == 'l9' and block >= 2 and column == 8 and _present(value):
                    sheet.cell(row, column).number_format = ACCOUNTING_WHOLE
                if form == 'l11-b' and ((block, column) in ((0, 16), (1, 14))):
                    averages[block] = sheet.cell(row, column).coordinate
            else:
                _write(sheet, row, column, value)
        if not footer_safe:
            pending.append({**table, 'rows': table['footer'], 'complete': False})
        if form == 'l1-d' and block == 0:
            for cells in sheet.iter_rows(min_row=first + 1, max_row=last + extra + 1,
                                         min_col=3, max_col=5):
                for cell in cells:
                    if cell.value not in (None, ''):
                        cell.number_format = ACCOUNTING
        offset += extra
    der_row, averages = _compact_layout(sheet, form, deleted, der_row, averages)
    derived = _l11b_der(sheet, der_row, averages) if form == 'l11-b' else {}
    if form in ('l1-d', 'l2', 'l3', 'l4', 'l6', 'l7', 'l9', 'l10-a', 'l10-c', 'l11-a', 'l11-b'):
        # Approved display-only omission. Keep unresolved audit counts and the
        # unchanged checkpoint; never promote an unmapped form to COMPLETE.
        return _clean_report(fields, pending, **derived)
    return _raw_evidence(sheet, sections, fields, pending, blocks[0][1] if blocks else 2)
