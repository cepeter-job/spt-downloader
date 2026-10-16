"""Render observed PPh21/26 forms without restyling their reference cells."""
from pathlib import Path
import re

from coretax_template_cells import (load_template_workbook, _key, _write, _mapping,
                                    _grow, _raw_evidence, _body_rows, _table_projection)


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


def _induk_row_matches(sheet, row, values):
    if _key(values.get(1)) != _key(sheet.cell(row, 1).value):
        return False
    label = str(values.get(2) or '')
    # Match observed annotations/labels only in their fixed semantic slots;
    # the original label is still written unchanged as source evidence.
    if row in (16, 30):
        label = label.removesuffix(' This row contain the total amount of payment before amendment.')
    government_tax = {21: '21', 35: '26'}.get(row)
    if government_tax and _key(label) == _key(f'PAJAK PENGHASILAN PASAL {government_tax} DITANGGUNG PEMERINTAH'):
        return True
    return _key(label) == _key(sheet.cell(row, 2).value)


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
            name = _key(table.get('group') or table.get('name', ''))
            body, pending = _body_rows(table)
            candidates = []
            for candidate in INDUK_BLOCKS:
                labels = [sheet.cell(candidate[1], c).value for c in range(1, 5)]
                projection = _mapping(table, labels)
                if projection is None:
                    continue
                named = name == _key(sheet.cell(candidate[0], 1).value)
                ordinal = not table.get('group') and re.fullmatch(r'Tabel\s+\d+', table.get('name', ''), re.I)
                matches = body and all(
                    any(_induk_row_matches(sheet, r, dict(zip(projection, values)))
                        for r in range(candidate[2], candidate[3] + 1))
                    for values in body)
                if named or (ordinal and matches):
                    candidates.append((candidate, projection))
            if len(candidates) != 1 or not table.get('complete', True):
                tables_left.append(table)
                continue
            block, mapping = candidates[0]
            # Fixed Induk rows are distinguished by section and visible labels,
            # never by the capture order or by recalculating taxpayer amounts.
            for values in body:
                projected = {column: value for column, value in zip(mapping, values)}
                matches = [r for r in range(block[2], block[3] + 1)
                           if _induk_row_matches(sheet, r, projected)]
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
                                     table.get('group') or table.get('name', ''), re.IGNORECASE))
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
            body, pending = _body_rows(table)
            extra_headers = {'l-ii': ('MASA PEEROLEHAN PENGHASILAN',),
                             'l-iii': ('JENIS PAJAK', 'OBJEK PAJAK')}.get(form, ())
            projected, mapping, has_extras = _table_projection(
                {**table, 'rows': body}, labels, extra_headers=extra_headers)
            if mapping is None or not table.get('complete', True):
                tables_left.append(table)
                continue
            grouped[index].extend((mapping, values) for values in projected['rows'])
            if has_extras:
                tables_left.append(table)
            elif pending:
                tables_left.append({**table, 'rows': pending})
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
    return _raw_evidence(sheet, sections, fields, tables, style_row)
