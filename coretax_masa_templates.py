"""Fill only observed PPN and Unifikasi forms using approved public layouts."""
from pathlib import Path
from decimal import Decimal
import math
import re

from coretax_template_cells import (load_template_workbook, _key, _write, _mapping,
                                    _grow, _raw_evidence, _body_rows, _header_key, _table_projection)


def canonical_form(tax, form):
    aliases = {
        'PPN': {'a-1': 'a1', 'a-2': 'a2', 'b-1': 'b1', 'b-2': 'b2', 'b-3': 'b3'},
    }
    return aliases.get(tax, {}).get(form.casefold(), form.casefold())


RESOURCES = {
    'PPN': ('ppn_format.xlsx', ['Induk', 'A1', 'A2', 'B1', 'B2', 'B3', 'C']),
    'PPh Unifikasi': ('unifikasi_format.xlsx', ['Induk', 'Daftar I', 'Daftar II', 'Lampiran I']),
}
PPN_BLOCKS = {
    'a1': [(None, 3, 4, 6)],
    'a2': [(None, 4, 5, 15)],
    'b1': [(None, 4, 5, 5)],
    'b2': [(None, 3, 4, 7)],
    'b3': [(None, 3, 4, 7)],
    'c': [(None, 3, 4, 6)],
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


PPN_REQUEST_CHOICES = {
    'CARRY_FORWARD': '1. dikompensasikan',
    'FAST_REFUND': '2. dikembalikan melalui pengembalian pendahuluan',
    'FORWARD_REFUND': '3. dikembalikan melalui pemeriksaan',
}


def _ppn_identity_fields(sheet, sections):
    # This display-only choice does not alter literal period/model proof.
    fields = [field for section in sections for field in section.get('fields', [])]
    periods = [field for field in fields if field.get('field') == 'Period'
               and _key(field.get('group')) == 'header']
    choices = [field for field in fields if field.get('field') == 'AskedTo']
    slots = {_key(sheet.cell(row, 1).value): (row, 4) for row in range(4, 7)}
    slots[_key(sheet['B48'].value)] = (48, 4)
    sheet['A7'].value = None
    sheet['D7'].value = None
    matches, pending = {}, []
    for field in fields:
        label = _key(field.get('label') or field.get('field', ''))
        value = field.get('value', '')
        if label == _key('Status Penyampaian'):
            continue
        if field in periods:
            valid = (isinstance(value, str)
                     and re.fullmatch(r'(0[1-9]|1[0-2])(?:0[1-9]|1[0-2])?[1-9][0-9]{3}', value))
            if valid and len(periods) == 1:
                matches.setdefault((4, 4), []).append((field, value[:2]))
                matches.setdefault((5, 4), []).append((field, value[-4:]))
            else:
                pending.append(field)
            continue
        # Literal Period is authoritative over legacy display-only header text.
        if periods and label in (_key('Masa Pajak'), _key('Tahun Pajak')):
            continue
        position = slots.get(label)
        if field.get('field') == 'AskedTo':
            expected = PPN_REQUEST_CHOICES.get(value) if isinstance(value, str) else None
            if expected and len(choices) == 1 and label in (_key(expected), _key(expected[3:])):
                position, value = (48, 4), expected[3:]
            else:
                position = None
        if label == _key('Normal/Pembetulan') and _key(field.get('group')) == 'header':
            position = (6, 4) if value in ('Normal', 'Pembetulan') else None
        if position is None:
            pending.append(field)
        else:
            matches.setdefault(position, []).append((field, value))
    for position, values in matches.items():
        if len(values) == 1:
            _write(sheet, *position, values[0][1])
        else:
            pending.extend(field for field, _ in values)
    return pending


def _identity_fields(sheet, sections, tax):
    if tax == 'PPN':
        return _ppn_identity_fields(sheet, sections)
    slots = {_key(sheet.cell(row, 1).value): (row, 4) for row in range(4, 8)}
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


def _write_ppn_amount(sheet, row, column, value):
    """Only verified money slots may change from source text to Excel numbers."""
    numeric = value
    if isinstance(value, str) and re.fullmatch(
            r'-?(?:[1-9][0-9]{0,2}(?:\.[0-9]{3})+|0|[1-9][0-9]*)(?:,[0-9]{1,2})?', value):
        source = Decimal(value.replace('.', '').replace(',', '.'))
        # Check the source before float conversion: Excel retains 15 digits.
        if Decimal(format(source, '.15g')) == source:
            converted = float(source)
            if math.isfinite(converted):
                numeric = converted
    _write(sheet, row, column, numeric)


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
                        _write_ppn_amount(sheet, rows[0], column, value)
                used.add(rows[0])
            if rows_left:
                pending.append({**table, 'rows': rows_left})
    return pending


def _ppn_fields(sheet, fields):
    # Single-value rows have a fixed amount slot. Multi-column/repeated labels
    # require observed group/header context; occurrence order is never evidence.
    single = {12: 5, 22: 5, 23: 5, 32: 7, 33: 7, 36: 5, 37: 5,
              **{r: 5 for r in range(41, 48)}, 56: 5,
              **{r: 5 for r in range(60, 65)}}
    matches, pending = {}, []
    for field in fields:
        label = _key(field.get('label') or field.get('field', ''))
        group = _key(field.get('group', ''))
        column = _header_key(field.get('column_label', ''))
        candidates = []
        for block in PPN_INDUK:
            caption = _key(str(sheet.cell(block[0], 1).value or '') + ' ' + str(sheet.cell(block[0], 2).value or ''))
            captions = {caption}
            # The approved reference repeats outgoing/export wording in some
            # input/collection slots. Preserve its cells; bind only the observed
            # section-specific labels, never a global import/export synonym.
            if block[0] == 26 and caption == _key('II. PENYERAHAN BARANG DAN JASA'):
                captions.add(_key('II. PEROLEHAN BARANG DAN JASA'))
            if group and group not in captions:
                continue
            bound_column = column
            observed_dpp = {26: 'Harga Jual/Penggantian/Nilai Impor/DPP (Rupiah)',
                            67: 'HARGA JUAL/PENGGANTIAN/DPP (Rupiah)',
                            73: 'HARGA JUAL/PENGGANTIAN/DPP (Rupiah)'}.get(block[0])
            reference_dpp = _header_key('Harga Jual/Penggantian/ Nilai Ekspor/DPP (Rupiah)')
            if (observed_dpp and column == _header_key(observed_dpp)
                    and _header_key(sheet.cell(block[1], 5).value) == reference_dpp):
                bound_column = reference_dpp
            for row in range(block[2], block[3] + 1):
                labels = {_key(sheet.cell(row, c).value) for c in range(1, 5)
                          if sheet.cell(row, c).value is not None}
                if row == 56 and group == caption and _key(sheet['A56'].value) == _key('PPN terutang'):
                    labels.add(_key('PPN yang wajib dibayar kembali'))
                if (row == 47 and group == caption
                        and label == _key('Ganti SPT sebelumnya')):
                    value = field.get('value')
                    # The checkbox shares this label with a disabled amount input.
                    # Keep its truth value out of money slots, including zero.
                    if isinstance(value, str) and re.fullmatch(r'-?[0-9]+(?:[.,][0-9]+)*', value):
                        labels.add(label)
                if not label or label not in labels:
                    continue
                if column:
                    columns = [c for c in range(5, 9) if bound_column == _header_key(sheet.cell(block[1], c).value)]
                else:
                    columns = [single[row]] if row in single else []
                candidates.extend((row, c) for c in columns)
        if len(candidates) == 1:
            matches.setdefault(candidates[0], []).append(field)
        else:
            pending.append(field)
    for position, values in matches.items():
        if len(values) == 1 and sheet.cell(*position).value is None:
            _write_ppn_amount(sheet, *position, values[0].get('value', ''))
        else:
            pending.extend(values)
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


PPN_TOTAL_COLUMNS = {'a1': (5,), 'a2': (6, 7, 8, 9), 'b1': (6, 7, 8),
                     'b2': (6, 7, 8, 9), 'b3': (6, 7, 8, 9), 'c': (10, 11, 12, 13)}


def _ppn_footer(table, labels, aliases, extras, columns):
    """Expand physical footer spans before applying semantic column bindings."""
    count = table.get('body_row_count')
    rows, footers, spans = table.get('rows', []), table.get('footer', []), table.get('footer_spans', [])
    if (type(count) is not int or not 0 <= count <= len(rows)
            or len(footers) != 1 or len(spans) != 1 or rows[count:] != footers
            or table.get('source_total', count) not in (None, count)):
        return None
    footer, widths = footers[0], spans[0]
    if (not footer or len(footer) != len(widths)
            or any(type(width) is not int or width < 1 for width in widths)
            or sum(widths) != len(table.get('headers', []))
            or _key(footer[0]) not in ('total', 'jumlah')):
        return None
    expanded, scalar = [], []
    for value, width in zip(footer, widths):
        expanded.extend([value] + [None] * (width - 1))
        scalar.extend([width == 1] * width)
    projected, mapping, _ = _table_projection(
        {**table, 'rows': [expanded]}, labels, aliases, extras)
    flags, flag_mapping, _ = _table_projection(
        {**table, 'rows': [scalar]}, labels, aliases, extras)
    if mapping is None or flag_mapping != mapping:
        return None
    values = dict(zip(mapping, projected['rows'][0]))
    single_cells = dict(zip(mapping, flags['rows'][0]))
    if any(column not in values or not single_cells[column] for column in columns):
        return None
    return {column: values[column] for column in columns}


def _ppn_appendix(sheet, blocks, sections, form):
    # Approved PPN appendices each have one body and one trailing total row.
    (_, header, first, last), = blocks
    labels = [sheet.cell(header, c).value for c in range(1, sheet.max_column + 1)]
    aliases = {}
    for alternatives in [('DPP', 'Jumlah DPP', 'DPP (Rupiah)'),
                         ('PPN', 'PPN (Rupiah)'), ('PPnBM', 'PPnBM (Rupiah)'),
                         ('Tanggal', 'Tanggal Faktur Pajak', 'Tanggal Dokumen'),
                         ('DASAR PENGENAAN PAJAK', 'DASAR PENGENAAN PAJAK (Rp)')]:
        targets = [label for label in labels if _header_key(label) in {_header_key(a) for a in alternatives}]
        if len(targets) == 1:
            aliases.update({a: targets[0] for a in alternatives})
    if form in ('b1', 'b3') and _header_key(labels[1]) == _header_key(
            'Nama Penjual Barang Kena Pajak/Barang Kena Pajak Tidak Berwujud/Jasa Kena Pajak'):
        aliases['Nama Penjual BKP/BKP Tidak Berwujud/Pemberi JKP'] = labels[1]
    extras = ['Masa Pajak', 'KODE IP TERKAIT', 'TANGGAL IP TERKAIT', 'Faktur Pajak']
    columns = PPN_TOTAL_COLUMNS[form]
    rows, fields, pending, totals = [], [], [], []
    for section in sections:
        fields.extend(section.get('fields', []))
        for table in section.get('tables', []):
            if not table.get('complete', True):
                pending.append(table)
                continue
            body, leftovers = _body_rows(table)
            projected, mapping, _ = _table_projection(
                {**table, 'rows': body}, labels, aliases, extras)
            if mapping is None:
                pending.append(table)
                continue
            rows.extend((mapping, values) for values in projected['rows'])
            if table.get('footer') or table.get('footer_spans'):
                total = _ppn_footer(table, labels, aliases, extras, columns)
                if total is None or len(body) != table.get('body_row_count'):
                    pending.append({**table, 'rows': leftovers, 'complete': False})
                else:
                    totals.append((table, total))
            elif leftovers:
                pending.append({**table, 'rows': leftovers})
    extra = max(0, len(rows) - (last - first + 1))
    _grow(sheet, last + 1, extra, first)
    for row, (mapping, values) in enumerate(rows, first):
        for column, value in zip(mapping, values):
            writer = _write_ppn_amount if column in columns else _write
            writer(sheet, row, column, value)
    # Different grids/snapshots are not additive, even when their totals agree.
    if len(totals) == 1 and not pending:
        for column, value in totals[0][1].items():
            _write_ppn_amount(sheet, last + extra + 1, column, value)
    elif totals:
        pending.extend({**table, 'rows': table['footer']} for table, _ in totals)
    return fields, pending

def render_template_form(sheet, tax, form, sections):
    form = canonical_form(tax, form)
    if form == 'induk':
        fields = _identity_fields(sheet, sections, tax)
        tables = _ppn_induk(sheet, sections) if tax == 'PPN' else _unifikasi_induk(sheet, sections)
        if tax == 'PPN':
            fields = _ppn_fields(sheet, fields)
        style_row = 4
    else:
        blocks = (PPN_BLOCKS if tax == 'PPN' else UNIFIKASI_BLOCKS)[form.casefold()]
        if tax == 'PPN':
            fields, tables = _ppn_appendix(sheet, blocks, sections, form)
        else:
            fields, tables = _appendix(sheet, blocks, sections)
        style_row = blocks[0][2]
    if tax == 'PPN':
        # The user requests clean PPN forms, not a second copy of raw capture.
        # Omission is presentation only: unresolved bindings remain in Audit
        # and the unchanged private checkpoint, never a fabricated COMPLETE.
        unresolved = [table for table in tables if table.get('rows') or not table.get('complete', True)]
        return {'complete': not fields and not unresolved, 'unmapped_fields': len(fields),
                'unmapped_tables': len(unresolved),
                'unmapped_rows': sum(len(table.get('rows', [])) for table in unresolved)}
    _raw_evidence(sheet, sections, fields, tables, style_row)
    return None
