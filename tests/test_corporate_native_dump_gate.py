"""Native Corporate capture is refused while one of its forms is still a payload dump.

The adapter emits a generic ``JSON path / JSON type / Source value`` table for
any payload root it cannot project. Such a table is audit evidence, not a form
projection, so a capture containing one is not interchangeable with the DOM
capture of the same SPT.
"""
from coretax_json import has_audit_dump_tables

DUMP = {'name': '/MainFormData', 'complete': True,
        'headers': ['JSON path', 'JSON type', 'Source value'],
        'rows': [['/MainFormData/NPWP', 'string', 'placeholder']]}


def section(name, tables, fields=()):
    return {'name': name, 'fields': list(fields), 'tables': tables, 'text': ''}


def test_payload_dump_table_refuses_the_capture():
    assert has_audit_dump_tables([section('Induk', [DUMP])]) is True
    assert has_audit_dump_tables([section('L3', [{'headers': ['A', 'B'], 'rows': [[1, 2]]}]),
                                  section('L9', [DUMP])]) is True


def test_projected_section_keeps_its_dump_as_custody_only():
    identity = {'group': 'A. IDENTITAS WAJIB PAJAK', 'field': 'Tin', 'label': '1. NPWP',
                'value': '0000000000000001'}
    assert has_audit_dump_tables([section('Induk', [DUMP], [identity])]) is False
    # A projected form does not launder an unprojected one.
    assert has_audit_dump_tables([section('Induk', [DUMP], [identity]),
                                  section('L9', [DUMP])]) is True


def test_projected_tables_pass():
    table = {'name': '/ListOfGrossTurnover', 'complete': True,
             'headers': ['Kode', 'Jumlah'], 'rows': [['1', '2']]}
    assert has_audit_dump_tables([section('L3', [table])]) is False


def test_recap_fields_cannot_launder_unprojected_detail_grids():
    recap = {'name': 'L9', 'fields': [{'field': 'TotalFiscalAmortization', 'value': '0'}],
             'tables': [DUMP], 'projection_complete': False,
             'projection_reason': 'unprojected_l9_grid_rows',
             'unprojected_grids': ['L9/l9-table-1-grid/Group 1']}
    assert has_audit_dump_tables([recap]) is True
    # Even accidental downstream loss of the table array cannot upgrade it.
    assert has_audit_dump_tables([{**recap, 'tables': []}]) is True


def test_capture_without_tables_has_no_dump():
    assert has_audit_dump_tables([]) is False
    assert has_audit_dump_tables([section('Induk', [])]) is False
