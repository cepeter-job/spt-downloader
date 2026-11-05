"""Unmapped identities are persisted alongside the existing counts.

The template engine already computes which captured fields/tables were not
placed; these tests pin that the identities (never values) travel with the
report into run data so the exact not-mapped subset is inspectable.
"""
from coretax_template_cells import _unmapped_identities
from coretax_badan_template import _clean_report


FIELDS = [
    {'label': 'SYNTHETIC-UNMAPPED-LABEL', 'field': 'SyntheticField', 'group': 'G',
     'value': 'SYNTHETIC-SECRET-VALUE'},
]
TABLES = [
    {'name': 'Tabel 1', 'group': 'G', 'headers': ['H1', 'H2'], 'complete': False,
     'rows': [['a', 'b'], ['c', 'd']], 'body_row_count': 2},
    {'name': 'Tabel 2', 'group': 'G', 'headers': [], 'complete': True,
     'rows': [], 'body_row_count': 0},
]


def test_identities_carry_labels_fields_and_groups_but_never_values():
    extra = _unmapped_identities(FIELDS, [TABLES[0]])
    assert extra['unmapped_field_identities'] == [
        {'label': 'SYNTHETIC-UNMAPPED-LABEL', 'field': 'SyntheticField', 'group': 'G'}]
    assert extra['unmapped_table_identities'] == [
        {'name': 'Tabel 1', 'group': 'G', 'headers': ['H1', 'H2'], 'complete': False,
         'row_count': 2, 'body_row_count': 2}]
    # Identities never carry taxpayer values: values stay in the checkpoint.
    assert 'SYNTHETIC-SECRET-VALUE' not in repr(extra)
    assert 'value' not in repr(extra)


def test_no_unmapped_content_adds_no_keys_so_complete_reports_are_unchanged():
    assert _unmapped_identities([], []) == {}
    report = _clean_report([], [TABLES[1]])
    assert report['complete'] is True
    assert 'unmapped_field_identities' not in report
    assert 'unmapped_table_identities' not in report


def test_clean_report_embeds_identities_for_unmapped_content():
    report = _clean_report(FIELDS, [TABLES[0]])
    assert report['complete'] is False
    assert report['unmapped_fields'] == 1 and report['unmapped_tables'] == 1
    assert report['unmapped_rows'] == 2
    assert report['unmapped_field_identities'][0]['label'] == 'SYNTHETIC-UNMAPPED-LABEL'
    assert report['unmapped_table_identities'][0]['name'] == 'Tabel 1'
