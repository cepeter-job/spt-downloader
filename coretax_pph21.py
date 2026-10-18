"""Render observed PPh21/26 forms without restyling their reference cells."""
from pathlib import Path
from decimal import Decimal
import math
import re

from coretax_template_cells import (load_template_workbook, _key, _write, _mapping,
                                    _grow, _table_projection)


RESOURCE = Path(__file__).resolve().parent / 'resources' / 'pph21_format.xlsx'
APPENDIX_BLOCKS = {
    'l-ia': [(None, 4, 5, 15)],
    'l-ib': [('BPA1', 5, 6, 8), ('BPA2', 11, 12, 14)],
    'l-ii': [('BPA1', 4, 5, 7), ('BPA2', 10, 11, 14)],
    'l-iii': [('BP21', 4, 5, 7), ('BP26', 10, 11, 13)],
}
INDUK_BLOCKS = [(10, 11, 12, 17), (19, 20, 21, 21),
                (24, 25, 26, 31), (33, 34, 35, 35)]
TOOLTIP = ' This row contain the total amount of payment before amendment.'
FOOTER_SPANS = {
    'l-ia': [5, 3, 1, 1, 1, 5], 'l-ib': [5, 3, 1, 1, 5],
    'l-ii': [5, 5, 1, 1, 4], 'l-iii': [5, 7, 1, 1, 4],
}
BP21_SUBTOTAL_LABELS = (
    'JUMLAH PENGHASILAN BRUTO UNTUK PASAL 21 DAN PAJAK PENGHASILAN PASAL 21 YANG DITANGGUNG OLEH PEMERINTAH',
    'JUMLAH UNTUK PASAL 21 DAN PENGHASILAN BRUTO PASAL 21 SERTA PAJAK PENGHASILAN YANG DIPOTONG',
)


def template_workbook(reserved_titles):
    return load_template_workbook(RESOURCE, ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III'],
                                  reserved_titles)


def _parts(table):
    """Validate the capture boundary before interpreting condensed footer cells."""
    rows = table.get('rows', [])
    headers = table.get('headers', [])
    if not isinstance(rows, list) or not isinstance(headers, list):
        return None
    count = table.get('body_row_count', len(rows))
    footer = table.get('footer', [])
    spans = table.get('footer_spans', [])
    if (table.get('complete', True) is not True
            or type(count) is not int or not 0 <= count <= len(rows)
            or not isinstance(footer, list) or not isinstance(spans, list)
            or rows[count:] != footer or len(footer) != len(spans)
            or any(not isinstance(row, list) or len(row) != len(headers) for row in rows[:count])):
        return None
    return rows[:count], footer, spans


def _unresolved(table):
    # Even an empty unknown/contradictory table must not silently certify mapping.
    return {**table, 'complete': False}


def _write_amount(sheet, row, column, value):
    """Convert verified monetary slots only; retain unsafe source literals."""
    numeric, source = value, None
    valid = value is None or value == ''
    if isinstance(value, str) and re.fullmatch(
            r'-?(?:[1-9][0-9]{0,2}(?:\.[0-9]{3})+|0|[1-9][0-9]*)(?:,[0-9]{1,2})?', value):
        source = Decimal(value.replace('.', '').replace(',', '.'))
    # Check the decimal source before float conversion, which could already
    # have rounded an unsafe value. Blank source cells are not invented zeroes.
    if source is not None and source.is_finite() and Decimal(format(source, '.15g')) == source:
        converted = float(source)
        if math.isfinite(converted) and Decimal(str(converted)) == source:
            numeric, valid = converted, True
    _write(sheet, row, column, numeric)
    return valid


def _display_only_field(field, form):
    """Only observed controls outside the reference layout may be omitted."""
    name, label, group = (field.get(key, '') for key in ('field', 'label', 'group'))
    value = field.get('value')
    if form == 'induk':
        identity = {'Tin': '1. NPWP', 'Name': '2. Nama',
                    'Address': '3. Alamat', 'PhoneNumber': '4. Nomor Telepon'}
        if group == 'A. IDENTITAS PEMOTONG' and name in identity and label == identity[name]:
            return isinstance(value, str) and (name != 'Tin' or re.fullmatch(r'[0-9]{16}', value) is not None)
        if group == 'D. PERNYATAAN DAN TANDA TANGAN':
            if (name, label) == ('MyCheckBox', 'DITANDATANGANI OLEH / Wajib Pajak / Kuasa / NAMA / KODE QR'):
                return type(value) is bool or (isinstance(value, str) and value in ('true', 'false'))
            return ((name, label) in (('DeclarationBy', 'Wajib Pajak'), ('DeclaratorName', 'NAMA'))
                    and isinstance(value, str))
        return False
    if (name, label, group) == ('Tin', 'Nomor Identitas WP', 'HEADER'):
        return isinstance(value, str) and re.fullmatch(r'[0-9]{16}', value) is not None
    if (name, label, group) == ('TaxPeriod', 'MASA PAJAK (MM-YYYY)', 'HEADER'):
        return isinstance(value, str) and re.fullmatch(r'(0[1-9]|1[0-2])-[0-9]{4}', value) is not None
    groups = ('LIST-IA',) if form == 'l-ia' else tuple(block[0] for block in APPENDIX_BLOCKS[form])
    return (name == '' and label == 'Unnamed field' and group in groups
            and isinstance(value, str) and value in ('10', '25', '50', '100'))


def _induk(sheet, sections):
    fields_left, tables_left = [], []
    used_fields, used_rows = set(), set()
    slots = {_key(sheet.cell(row, 1).value): row for row in range(4, 8)}
    captions = {_key(sheet.cell(block[0], 1).value): block for block in INDUK_BLOCKS}
    for section in sections:
        for field in section.get('fields', []):
            label = field.get('label') or field.get('field', '')
            row = slots.get(_key(label))
            if row is not None and row not in used_fields:
                _write(sheet, row, 4, field.get('value', ''))
                used_fields.add(row)
            elif not _display_only_field(field, 'induk'):
                fields_left.append(field)
        for table in section.get('tables', []):
            group, name = _key(table.get('group')), _key(table.get('name'))
            block = captions.get(group or name)
            if group and name in captions and captions[name] != block:
                block = None
            parts = _parts(table)
            labels = [sheet.cell(block[1], c).value for c in range(1, 5)] if block else []
            mapping = _mapping(table, labels) if block and parts else None
            if mapping is None or parts[1]:
                tables_left.append(_unresolved(table))
                continue
            pending = []
            # Fixed Induk rows are distinguished by section and visible labels,
            # never by the capture order or by recalculating taxpayer amounts.
            for values in parts[0]:
                projected = {column: value for column, value in zip(mapping, values)}
                label = str(projected.get(2, '')).removesuffix(TOOLTIP)
                if block[2] in (21, 35):
                    tax = 21 if block[2] == 21 else 26
                    if _key(label) == _key(f'PAJAK PENGHASILAN PASAL {tax} DITANGGUNG PEMERINTAH'):
                        label = sheet.cell(block[2], 2).value
                matches = [r for r in range(block[2], block[3] + 1)
                           if _key(projected.get(1)) == _key(sheet.cell(r, 1).value)
                           and _key(label) == _key(sheet.cell(r, 2).value)]
                if len(matches) != 1 or matches[0] in used_rows:
                    pending.append(values)
                    continue
                row = matches[0]
                # Source aliases identify slots without replacing reference labels.
                for column in (3, 4):
                    if column in projected:
                        if column == 4:
                            if not _write_amount(sheet, row, column, projected[column]):
                                pending.append(values)
                        else:
                            _write(sheet, row, column, projected[column])
                used_rows.add(row)
            if pending:
                tables_left.append({**table, 'rows': pending})
    return fields_left, tables_left


def _appendix_group(table, form, blocks):
    if form == 'l-ia':
        group = _key(table.get('group'))
        name = _key(table.get('name'))
        if group:
            return 0 if group in ('lia', 'listia') else None
        return 0 if name in ('lia', 'listia') else None

    def groups(value):
        return {v.upper() for v in re.findall(r'(?<![A-Za-z0-9])(BPA1|BPA2|BP21|BP26)(?![A-Za-z0-9])',
                                              value or '', re.IGNORECASE)}

    group_text = table.get('group', '')
    actual, named = groups(group_text), groups(table.get('name'))
    selected = actual if group_text else named
    if group_text and named and named != actual:
        return None
    matches = [index for index, (group, _, _, _) in enumerate(blocks) if selected == {group}]
    return matches[0] if len(matches) == 1 else None


def _footer_targets(sheet, form, index, footer, spans):
    first = 16 if form in ('l-ia', 'l-ib') else 15
    last = first if form == 'l-ii' else first + 2
    labels = {_key(sheet.cell(row, 1).value): row for row in range(first, last + 1)}
    targets, spacer = {}, False
    omitted = set()
    bp21 = form == 'l-iii' and index == 0
    expected_spans = [4, 4, 1, 1, 4] if bp21 else FOOTER_SPANS[form]
    for position, (values, widths) in enumerate(zip(footer, spans)):
        if values == [] and widths == [] and position == 0:
            spacer = True
            continue
        if (not isinstance(values, list) or not isinstance(widths, list)
                or any(type(width) is not int for width in widths)
                or widths != expected_spans or len(values) != len(widths)
                or (form not in ('l-ia', 'l-iii') and index != 1)):
            return None
        if bp21:
            # These explicitly Pasal21 subtotals have no reference slots. Never
            # use them for the Pasal26 totals even if their amounts coincide.
            label = _key(values[1])
            if (label not in {_key(v) for v in BP21_SUBTOTAL_LABELS} or label in omitted
                    or any(values[c] not in ('', None) for c in (0, 4))):
                return None
            omitted.add(label)
            continue
        target = labels.get(_key(values[1]))
        blanks = (0, 3, 5) if form == 'l-ia' else (0, 4)
        if target is None or target in targets or any(values[c] not in ('', None) for c in blanks):
            return None
        targets[target] = (values[2], values[4] if form == 'l-ia' else values[3])
    return targets, spacer


def _appendix(sheet, form, sections):
    blocks = APPENDIX_BLOCKS[form]
    grouped = [[] for _ in blocks]
    spacers = [False for _ in blocks]
    fields_left, tables_left = [], []
    totals = {}
    numeric_failures = set()
    money_columns = (7, 9) if form == 'l-ia' else (7, 8)
    for section in sections:
        fields_left.extend(field for field in section.get('fields', []) if not _display_only_field(field, form))
        for table in section.get('tables', []):
            index = _appendix_group(table, form, blocks)
            parts = _parts(table)
            if index is None or parts is None:
                tables_left.append(_unresolved(table))
                continue
            body, footer, spans = parts
            header = blocks[index][1]
            width = 14 if form == 'l-ia' else 13
            labels = [sheet.cell(header, column).value for column in range(1, width + 1)]
            extra_headers = {'l-ii': ('MASA PEEROLEHAN PENGHASILAN',),
                             'l-iii': ('JENIS PAJAK', 'OBJEK PAJAK')}.get(form, ())
            projected, mapping, _ = _table_projection({**table, 'rows': body}, labels,
                                                     extra_headers=extra_headers)
            mapped_footer = _footer_targets(sheet, form, index, footer, spans)
            if mapping is None or mapped_footer is None:
                tables_left.append(_unresolved(table))
                continue
            footer_values, spacer = mapped_footer
            grouped[index].extend((mapping, values, table) for values in projected['rows'])
            spacers[index] = spacers[index] or spacer
            for row, values in footer_values.items():
                totals.setdefault(row, []).append((values, table))
    offset = 0
    for index, (_, _, first, last) in enumerate(blocks):
        first, last = first + offset, last + offset
        rows = grouped[index]
        # The observed blank footer row is a spacer, not an employee. Reuse
        # existing capacity before growing, moving later labels and totals too.
        needed = len(rows) + int(spacers[index])
        extra = max(0, needed - (last - first + 1))
        _grow(sheet, last + 1, extra, first)
        for row, (mapping, values, table) in enumerate(rows, first):
            valid = True
            for column, value in zip(mapping, values):
                if column in money_columns:
                    valid = _write_amount(sheet, row, column, value) and valid
                else:
                    _write(sheet, row, column, value)
            if not valid and id(table) not in numeric_failures:
                numeric_failures.add(id(table))
                tables_left.append(_unresolved(table))
        offset += extra
    for row, candidates in totals.items():
        if len(candidates) != 1:
            tables_left.extend(_unresolved(table) for _, table in candidates)
            continue
        values, table = candidates[0]
        valid = True
        for column, value in zip(money_columns, values):
            valid = _write_amount(sheet, row + offset, column, value) and valid
        if not valid and id(table) not in numeric_failures:
            numeric_failures.add(id(table))
            tables_left.append(_unresolved(table))
    return fields_left, tables_left


def render_template_form(sheet, form, sections):
    key = form.casefold()
    fields, tables = _induk(sheet, sections) if key == 'induk' else _appendix(sheet, key, sections)
    # Hiding redundant source text must not certify unresolved source data.
    # Checkpoints stay unchanged; the existing resume Audit receives failures.
    unresolved = [t for t in tables if t.get('rows') or not t.get('complete', True)]
    return {'complete': not fields and not unresolved, 'unmapped_fields': len(fields),
            'unmapped_tables': len(unresolved),
            'unmapped_rows': sum(len(t.get('rows', [])) for t in unresolved)}
