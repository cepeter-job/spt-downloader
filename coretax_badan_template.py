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


def render_template_form(sheet, form, sections):
    form = form.casefold()
    blocks = BLOCKS[form]
    grouped = [[] for _ in blocks]
    fields = [field for section in sections for field in section.get('fields', [])]
    pending = []
    for section in sections:
        for table in section.get('tables', []):
            rows = table.get('rows', [])
            candidates = [(index, _columns(table, sheet, header))
                          for index, (header, _, _) in enumerate(blocks)]
            candidates = [(index, columns) for index, columns in candidates if columns]
            if (not table.get('complete', True) or len(candidates) != 1
                    or table.get('footer') or table.get('body_row_count', len(rows)) != len(rows)
                    or table.get('source_total', len(rows)) not in (None, len(rows))
                    or any(len(row) != len(table.get('headers', [])) for row in rows)):
                pending.append({**table, 'complete': False})
                continue
            index, columns = candidates[0]
            grouped[index].append((table, columns))
    offset = 0
    for (header, first, last), items in zip(blocks, grouped):
        if len(items) != 1:
            pending.extend({**table, 'complete': False} for table, _ in items)
            continue
        table, columns = items[0]
        header, first, last = header + offset, first + offset, last + offset
        # Never infer collapsed source cells from the template's merged geometry.
        if any(region.min_row <= last and region.max_row >= first
               for region in sheet.merged_cells.ranges):
            pending.append({**table, 'complete': False})
            continue
        money = {column for column in columns
                 if re.search(r'\((?:rp\.?|rupiah)\)', str(sheet.cell(header, column).value), re.I)}
        extra = max(0, len(table['rows']) - (last - first + 1))
        _grow(sheet, last + 1, extra, first)
        for row, values in enumerate(table['rows'], first):
            safe = True
            for column, value in zip(columns, values):
                if column in money:
                    safe = _write_amount(sheet, row, column, value) and safe
                else:
                    _write(sheet, row, column, value)
            if not safe:
                pending.append({**table, 'rows': [values], 'complete': False})
        offset += extra
    return _raw_evidence(sheet, sections, fields, pending, blocks[0][1] if blocks else 2)
