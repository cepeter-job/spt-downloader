"""Render observed PPh21/26 forms without restyling their reference cells."""
from pathlib import Path
import re

from coretax_template_cells import (load_template_workbook, _key, _write, _mapping,
                                    _grow, _raw_evidence)


RESOURCE = Path(__file__).resolve().parent / 'resources' / 'pph21_format.xlsx'
APPENDIX_BLOCKS = {
    'l-ia': [(None, 4, 5, 15)],
    'l-ib': [('BPA1', 5, 6, 8), ('BPA2', 11, 12, 14)],
    'l-ii': [('BPA1', 4, 5, 7), ('BPA2', 10, 11, 14)],
    'l-iii': [('BP21', 4, 5, 7), ('BP26', 10, 11, 13)],
}
INDUK_BLOCKS = [(10, 11, 12, 17), (19, 20, 21, 21),
                (24, 25, 26, 31), (33, 34, 35, 35)]


def template_workbook(reserved_titles):
    return load_template_workbook(RESOURCE, ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III'],
                                  reserved_titles)


def _induk(sheet, sections):
    fields_left, tables_left = [], []
    used_fields, used_rows = set(), set()
    slots = {_key(sheet.cell(row, 1).value): row for row in range(4, 8)}
    for section in sections:
        for field in section.get('fields', []):
            label = field.get('label') or field.get('field', '')
            row = slots.get(_key(label))
            if row is not None and row not in used_fields:
                _write(sheet, row, 4, field.get('value', ''))
                used_fields.add(row)
            else:
                fields_left.append(field)
        for table in section.get('tables', []):
            name = _key(table.get('name', ''))
            block = next((b for b in INDUK_BLOCKS if _key(sheet.cell(b[0], 1).value) == name), None)
            labels = [sheet.cell(block[1], c).value for c in range(1, 5)] if block else []
            mapping = _mapping(table, labels) if block else None
            if mapping is None:
                tables_left.append(table)
                continue
            pending = []
            # Fixed Induk rows are distinguished by section and visible labels,
            # never by the capture order or by recalculating taxpayer amounts.
            for values in table.get('rows', []):
                projected = {column: value for column, value in zip(mapping, values)}
                matches = [r for r in range(block[2], block[3] + 1)
                           if _key(projected.get(1)) == _key(sheet.cell(r, 1).value)
                           and _key(projected.get(2)) == _key(sheet.cell(r, 2).value)]
                if len(matches) != 1 or matches[0] in used_rows:
                    pending.append(values)
                    continue
                row = matches[0]
                for column, value in projected.items():
                    _write(sheet, row, column, value)
                used_rows.add(row)
            if pending:
                tables_left.append({**table, 'rows': pending})
            elif not table.get('complete', True):
                tables_left.append({**table, 'rows': []})
    return fields_left, tables_left


def _appendix(sheet, form, sections):
    blocks = APPENDIX_BLOCKS[form]
    grouped = [[] for _ in blocks]
    fields_left, tables_left = [], []
    for section in sections:
        fields_left.extend(section.get('fields', []))
        for table in section.get('tables', []):
            matches = set(re.findall(r'(?<![A-Za-z0-9])(BPA1|BPA2|BP21|BP26)(?![A-Za-z0-9])',
                                     table.get('name', ''), re.IGNORECASE))
            matches = {match.upper() for match in matches}
            candidates = [index for index, (group, _, _, _) in enumerate(blocks)
                          if group is None or matches == {group}]
            if len(candidates) != 1:
                tables_left.append(table)
                continue
            index = candidates[0]
            header = blocks[index][1]
            width = 14 if form == 'l-ia' else 13
            labels = [sheet.cell(header, column).value for column in range(1, width + 1)]
            mapping = _mapping(table, labels)
            if mapping is None:
                tables_left.append(table)
                continue
            grouped[index].extend((mapping, values) for values in table.get('rows', []))
            if not table.get('complete', True):
                tables_left.append({**table, 'rows': []})
    offset = 0
    for (_, _, first, last), rows in zip(blocks, grouped):
        first, last = first + offset, last + offset
        extra = max(0, len(rows) - (last - first + 1))
        _grow(sheet, last + 1, extra, first)
        for row, (mapping, values) in enumerate(rows, first):
            for column, value in zip(mapping, values):
                _write(sheet, row, column, value)
        offset += extra
    return fields_left, tables_left


def render_template_form(sheet, form, sections):
    key = form.casefold()
    if key == 'induk':
        fields, tables = _induk(sheet, sections)
        style_row = 4
    else:
        fields, tables = _appendix(sheet, key, sections)
        style_row = APPENDIX_BLOCKS[key][0][2]
    _raw_evidence(sheet, sections, fields, tables, style_row)
