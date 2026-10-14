"""Shared style-preserving primitives for the three approved Masa templates."""
from copy import copy
import re

from openpyxl import load_workbook


def load_template_workbook(resource, expected_names, reserved_titles):
    workbook = load_workbook(resource)
    if workbook.sheetnames != expected_names:
        workbook.close()
        raise ValueError('Resource format SPT Masa tidak sesuai.')
    templates = {}
    reserved = {title.casefold() for title in reserved_titles}
    counter = 0
    for sheet in workbook.worksheets:
        templates[sheet.title.casefold()] = sheet
        while f'_reference_{counter}'.casefold() in reserved:
            counter += 1
        sheet.title = f'_reference_{counter}'
        reserved.add(sheet.title.casefold())
        counter += 1
    return workbook, templates


def _key(value):
    return re.sub(r'[\W_]+', '', str(value or '').casefold())


def _write(sheet, row, column, value):
    cell = sheet.cell(row, column)
    cell.value = value if value is not None else ''
    if isinstance(cell.value, str):
        # Excel-injection protection must not replace the user's number format.
        cell.data_type = 's'


def _mapping(table, labels):
    headers = table.get('headers', [])
    keys = [_key(value) for value in headers]
    target = {_key(value): index + 1 for index, value in enumerate(labels) if value is not None}
    if (not keys or any(not value for value in keys) or len(set(keys)) != len(keys)
            or any(value not in target for value in keys)
            or any(len(row) > len(headers) for row in table.get('rows', []))):
        return None
    return [target[value] for value in keys]


def _copy_row_style(sheet, source_row, target_row, width):
    for column in range(1, width + 1):
        sheet.cell(target_row, column)._style = copy(sheet.cell(source_row, column)._style)
    if source_row in sheet.row_dimensions:
        dimension = copy(sheet.row_dimensions[source_row])
        dimension.index = target_row
        sheet.row_dimensions[target_row] = dimension


def _grow(sheet, boundary, count, style_row):
    if not count:
        return
    # openpyxl shifts cells, not row dimensions or merged ranges.
    merged = [copy(region) for region in sheet.merged_cells.ranges]
    if any(region.min_row < boundary <= region.max_row for region in merged):
        raise ValueError('Baris data SPT Masa memotong merge template.')
    moving_merges = [region for region in merged if region.min_row >= boundary]
    for region in moving_merges:
        sheet.unmerge_cells(str(region))
    sheet.insert_rows(boundary, count)
    for row in sorted(list(sheet.row_dimensions), reverse=True):
        if row >= boundary:
            dimension = sheet.row_dimensions.pop(row)
            dimension.index = row + count
            sheet.row_dimensions[row + count] = dimension
    for region in moving_merges:
        region.shift(row_shift=count)
        sheet.merge_cells(str(region))
    for row in range(boundary, boundary + count):
        _copy_row_style(sheet, style_row, row, sheet.max_column)


def _raw_evidence(sheet, sections, fields, tables, style_row):
    texts = [section.get('text', '') for section in sections if section.get('text')]
    if not fields and not tables and not texts:
        return
    row = sheet.max_row + 2
    original_width = sheet.max_column
    def append(values):
        nonlocal row
        width = max(original_width, len(values))
        for column in range(1, width + 1):
            sheet.cell(row, column)._style = copy(sheet.cell(style_row, min(column, original_width))._style)
        if style_row in sheet.row_dimensions:
            dimension = copy(sheet.row_dimensions[style_row])
            dimension.index = row
            sheet.row_dimensions[row] = dimension
        for column, value in enumerate(values, 1):
            _write(sheet, row, column, value)
        row += 1
    # Unsupported or ambiguous content is still visible source evidence. It must
    # not be guessed into the wrong BPA/BP group, lost, or duplicated as amounts.
    append(['Data sumber tambahan / belum dipetakan'])
    for field in fields:
        append([field.get('label') or field.get('field', ''), field.get('value', '')])
    for table in tables:
        append([table.get('name', 'Tabel')])
        if table.get('headers'):
            append(table['headers'])
        for values in table.get('rows', []):
            append(values)
        if not table.get('complete', True):
            append(['PARTIAL: paginasi tidak selesai'])
    for text in texts:
        append(['Teks halaman / konteks sumber'])
        for start in range(0, len(text), 30000):
            append([text[start:start + 30000]])
