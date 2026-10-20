"""Approved corporate layout; ambiguous source blocks remain visible evidence."""
from decimal import Decimal
from pathlib import Path
import math
import re

from coretax_template_cells import load_template_workbook, _write, _grow, _raw_evidence

FORMS = ['L1-D', 'L2', 'L3', 'L4', 'L6', 'L7', 'L9', 'L10-A', 'L10-C',
         'L11-A', 'L11-B', 'L11-C']
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
    resource = Path(__file__).resolve().parent / 'resources/corporate_format.xlsx'
    return load_template_workbook(resource, FORMS, reserved_titles)


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


def _write_amount(sheet, row, column, value):
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


def _money_columns(sheet, form, header, columns):
    if form == 'l1-d':
        return {3, 4, 5, 6, 7, 8, 10} if sheet.cell(header, 4).value else {3}
    return {column for column in columns
            if re.search(r'\((?:rp\.?|rupiah)\)', str(sheet.cell(header, column).value), re.I)}


def _footer_plan(sheet, table, target, money, columns):
    footer = table.get('footer', [])
    if not footer:
        return []
    # Colspans describe physical source columns; do not reorder them by guess.
    if columns != list(range(1, len(table['headers']) + 1)):
        return None
    spans = table.get('footer_spans', [])
    if len(footer) != 1 or len(spans) != 1 or len(footer[0]) != len(spans[0]):
        return None
    if any(type(span) is not int or span < 1 for span in spans[0]):
        return None
    if not any(value not in ('', None) for value in footer[0]):
        return []
    if sum(spans[0]) != len(table['headers']):
        return None
    result, column = [], 1
    for value, span in zip(footer[0], spans[0]):
        if value not in ('', None):
            if span == 1 and column in money:
                result.append((column, value))
            else:
                labels = [c for c in range(column, column + span)
                          if sheet.cell(target, c).value is not None
                          and _label(sheet.cell(target, c).value) == _label(value)]
                if len(labels) != 1:
                    return None
        column += span
    return result


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


def render_template_form(sheet, form, sections):
    form = form.casefold()
    blocks = BLOCKS[form]
    grouped = [[] for _ in blocks]
    fields = [field for section in sections for field in section.get('fields', [])]
    pending = []
    for section in sections:
        for table in section.get('tables', []):
            rows = table.get('rows', [])
            count = table.get('body_row_count', len(rows))
            footer = table.get('footer', [])
            candidates = [(index, _columns(table, sheet, header))
                          for index, (header, _, _) in enumerate(blocks)]
            candidates = [(index, columns) for index, columns in candidates if columns]
            role = _l1d_role(table) if form == 'l1-d' else None
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
    offset = 0
    for (header, first, last), items in zip(blocks, grouped):
        if len(items) != 1:
            pending.extend({**table, 'complete': False} for table, _, _ in items)
            continue
        table, columns, rows = items[0]
        header, first, last = header + offset, first + offset, last + offset
        money = _money_columns(sheet, form, header, columns)
        foot = _footer_plan(sheet, table, last + 1, money, columns)
        body, style_row = _body_plan(sheet, form, first, last, columns, rows)
        if foot is None or body is None:
            pending.append({**table, 'complete': False})
            continue
        extra = max(0, len(rows) - (last - first + 1))
        _grow(sheet, last + 1, extra, style_row)
        for index, cells in enumerate(body):
            row, safe = first + index, True
            for column, value in cells.items():
                if column in money:
                    safe = _write_amount(sheet, row, column, value) and safe
                else:
                    _write(sheet, row, column, value)
            if not safe:
                pending.append({**table, 'rows': [rows[index]], 'complete': False})
        for column, value in foot:
            if not _write_amount(sheet, last + extra + 1, column, value):
                pending.append({**table, 'rows': table['footer'], 'complete': False})
        offset += extra
    return _raw_evidence(sheet, sections, fields, pending, blocks[0][1] if blocks else 2)
