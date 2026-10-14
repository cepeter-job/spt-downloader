"""Fill only observed PPN and Unifikasi forms using approved public layouts."""
from pathlib import Path

from coretax_template_cells import (load_template_workbook, _key, _write, _mapping,
                                    _grow, _raw_evidence)

RESOURCES = {
    'PPN': ('ppn_format.xlsx', ['Induk', 'A1', 'A2', 'B1', 'B2', 'B3', 'C']),
    'PPh Unifikasi': ('unifikasi_format.xlsx', ['Induk', 'Daftar I', 'Daftar II', 'Lampiran I']),
}
PPN_BLOCKS = {
    'a1': [(None, 3, 4, 6)],
    'a2': [(None, 4, 5, 15)],
    'b1': [(None, 4, 5, 6)],
    'b2': [(None, 3, 4, 7)],
    'b3': [(None, 3, 4, 7)],
    'c': [(None, 3, 4, 7)],
}
UNIFIKASI_BLOCKS = {
    'daftar i': [('B3', 4, 5, 8), ('B9', 10, 11, 14)],
    'daftar ii': [('B3', 4, 5, 8), ('B12', 13, 14, 17)],
    'lampiran i': [(None, 4, 5, 9)],
}
# Group, amount-header and body positions are structural reference coordinates.
PPN_INDUK = [(9, 10, 11, 23), (26, 27, 28, 37), (39, 40, 41, 48),
             (50, 51, 52, 52), (54, 55, 56, 56), (58, 59, 60, 65),
             (67, 68, 69, 71), (73, 74, 75, 78)]


def template_workbook(tax, reserved_titles):
    filename, names = RESOURCES[tax]
    resource = Path(__file__).resolve().parent / 'resources' / filename
    return load_template_workbook(resource, names, reserved_titles)


def _identity_fields(sheet, sections, tax):
    slots = {_key(sheet.cell(row, 1).value): (row, 4) for row in range(4, 8)}
    if tax == 'PPN':
        slots[_key(sheet['B48'].value)] = (48, 4)
    used, pending = set(), []
    for section in sections:
        for field in section.get('fields', []):
            position = slots.get(_key(field.get('label') or field.get('field', '')))
            if position is None or position in used:
                pending.append(field)
            else:
                _write(sheet, *position, field.get('value', ''))
                used.add(position)
    return pending


def _ppn_mapping(table, sheet, header):
    # The reference has an unnamed merged description header (A:D). Treat that
    # one structural column as description, not as an invented source alias.
    labels = [('', 0)] + [(sheet.cell(header, c).value, c) for c in range(5, 9)
                          if sheet.cell(header, c).value is not None]
    target = {_key(label): column for label, column in labels}
    headers = table.get('headers', [])
    keys = [_key(label) for label in headers]
    if (len(target) != len(labels) or not keys or len(keys) != len(set(keys))
            or any(key not in target for key in keys) or '' not in keys
            or any(len(row) > len(headers) for row in table.get('rows', []))):
        return None
    return [target[key] for key in keys]


def _ppn_induk(sheet, sections):
    used, pending = set(), []
    for section in sections:
        for table in section.get('tables', []):
            name = _key(table.get('name', ''))
            matches = [b for b in PPN_INDUK if name == _key(
                str(sheet.cell(b[0], 1).value or '') + ' ' + str(sheet.cell(b[0], 2).value or ''))]
            if not table.get('complete', True) or len(matches) != 1:
                pending.append(table)
                continue
            block = matches[0]
            mapping = _ppn_mapping(table, sheet, block[1])
            if mapping is None:
                pending.append(table)
                continue
            rows_left = []
            for values in table.get('rows', []):
                projected = dict(zip(mapping, values))
                description = projected.get(0)
                rows = [row for row in range(block[2], block[3] + 1)
                        if description is not None and any(
                            sheet.cell(row, column).value == description for column in (2, 3))]
                if len(rows) != 1 or rows[0] in used:
                    rows_left.append(values)
                    continue
                for column, value in projected.items():
                    if column:
                        _write(sheet, rows[0], column, value)
                used.add(rows[0])
            if rows_left:
                pending.append({**table, 'rows': rows_left})
    return pending


def _unifikasi_induk(sheet, sections):
    labels = [sheet['A10'].value, sheet['B10'].value, sheet['C11'].value,
              sheet['D11'].value] + [sheet.cell(10, c).value for c in range(5, 9)]
    used, pending = set(), []
    for section in sections:
        for table in section.get('tables', []):
            mapping = _mapping(table, labels)
            if not table.get('complete', True) or mapping is None:
                pending.append(table)
                continue
            rows_left = []
            for values in table.get('rows', []):
                projected = dict(zip(mapping, values))
                matches = [row for row in range(12, 28)
                           if _key(projected.get(1)) == _key(sheet.cell(row, 1).value)
                           and projected.get(2) == sheet.cell(row, 2).value]
                if len(matches) != 1 or matches[0] in used:
                    rows_left.append(values)
                    continue
                for column, value in projected.items():
                    _write(sheet, matches[0], column, value)
                used.add(matches[0])
            if rows_left:
                pending.append({**table, 'rows': rows_left})
    return pending


def _appendix(sheet, blocks, sections):
    grouped = [[] for _ in blocks]
    fields, pending = [], []
    for section in sections:
        fields.extend(section.get('fields', []))
        for table in section.get('tables', []):
            if not table.get('complete', True):
                pending.append(table)
                continue
            name = _key(table.get('name', ''))
            candidates = [i for i, (caption, _, _, _) in enumerate(blocks)
                          if caption is None or name == _key(sheet[caption].value)]
            if len(candidates) != 1:
                pending.append(table)
                continue
            index = candidates[0]
            labels = [sheet.cell(blocks[index][1], c).value for c in range(1, sheet.max_column + 1)]
            mapping = _mapping(table, labels)
            if mapping is None:
                pending.append(table)
                continue
            grouped[index].extend((mapping, values) for values in table.get('rows', []))
    offset = 0
    for (_, _, first, last), rows in zip(blocks, grouped):
        first, last = first + offset, last + offset
        extra = max(0, len(rows) - (last - first + 1))
        _grow(sheet, last + 1, extra, first)
        for row, (mapping, values) in enumerate(rows, first):
            for column, value in zip(mapping, values):
                _write(sheet, row, column, value)
        offset += extra
    return fields, pending


def render_template_form(sheet, tax, form, sections):
    if form.casefold() == 'induk':
        fields = _identity_fields(sheet, sections, tax)
        tables = _ppn_induk(sheet, sections) if tax == 'PPN' else _unifikasi_induk(sheet, sections)
        style_row = 4
    else:
        blocks = (PPN_BLOCKS if tax == 'PPN' else UNIFIKASI_BLOCKS)[form.casefold()]
        fields, tables = _appendix(sheet, blocks, sections)
        style_row = blocks[0][2]
    _raw_evidence(sheet, sections, fields, tables, style_row)
