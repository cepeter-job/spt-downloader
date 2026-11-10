"""Synthetic live-shaped L3 B row contracts; runtime tests are CI-only."""
from copy import deepcopy
import json

import pytest

from coretax_json import _UnsupportedMetadata, _corporate_json
from test_corporate_l3_projection import HEADERS, LABELS, SPANS, inputs, project, projection


ROW_METADATA = {'IncomeTaxUsd': 0, 'IsManually': True, 'TableSource': None,
                'Index': 0, 'Action': None}
BASE_FIELDS = ('RecordId', 'Name', 'TIN', 'TaxType', 'TaxBase', 'IncomeTax',
               'WithholdingSlipsNumber', 'WithholdingSlipsDate')


def _extend(pages):
    for page in pages:
        for row in page['data']:
            row.update(deepcopy(ROW_METADATA))


def test_l3_closed_thirteen_key_rows_keep_display_and_every_typed_metadata_leaf():
    form, pages, footer = inputs()
    legacy = project(form, pages, footer)
    _extend(pages)
    before = deepcopy((form, pages, footer))

    result = project(form, pages, footer)

    assert (form, pages, footer) == before
    assert result['tables'] == legacy['tables']
    assert result['fields'] == legacy['fields']
    assert all(entry in result['provenance'] for entry in legacy['provenance'])
    expected = {'IncomeTaxUsd': ('number', '0'), 'IsManually': ('boolean', True),
                'TableSource': ('null', None), 'Index': ('number', '0'),
                'Action': ('null', None)}
    for page_index, page in enumerate(pages):
        for local_index, _ in enumerate(page['data']):
            for field, (kind, value) in expected.items():
                entries = [entry for entry in result['provenance']
                           if entry.get('source') == 'grid'
                           and entry.get('page_index') == page_index
                           and entry.get('path') == ['Data', local_index, field]]
                assert len(entries) == 1
                entry = entries[0]
                assert (entry['type'], entry['value']) == (kind, value)
                assert entry['destination'] == {'table': 'L3/domestic',
                    'row': page['offset'] + local_index, 'metadata': field}
                assert entry['rule'] == 'non-displayed-domestic-row-metadata'
                assert 'column' not in entry['destination']


@pytest.mark.parametrize(('value', 'display'), [
    ('2024-02-29T00:00:00+07:00', '29-02-2024'),
    ('1970-01-01T00:00:00+07:00', '01-01-1970'),
    ('2100-12-31T00:00:00+07:00', '31-12-2100'),
])
def test_active_b_jakarta_midnight_dates_keep_the_source_and_render_the_local_day(value, display):
    # Legacy eight-key schema: metadata refusal must not mask the date gate.
    form, pages, footer = inputs()
    pages[0]['data'][0]['WithholdingSlipsDate'] = value
    result = project(form, pages, footer)
    assert result['tables'][1]['rows'][0][7] == display
    entries = [entry for entry in result['provenance']
               if entry.get('source') == 'grid' and entry.get('page_index') == 0
               and entry.get('path') == ['Data', 0, 'WithholdingSlipsDate']]
    assert len(entries) == 1
    assert (entries[0]['type'], entries[0]['value']) == ('string', value)


@pytest.mark.parametrize('value', [
    '', '2025-12-01T00:00:00', '2025-12-01T00:00:00+00:00',
    '2025-12-01T00:00:00-00:00', '2025-12-01T00:00:00+08:00',
    '2025-12-01T00:00:00-07:00',
    '2025-12-01T00:00:00+0700', '2025-12-01T00:00:00+7:00',
    '2025-12-01T00:00:00.000+07:00', '2025-12-01T12:00:00+07:00',
    '2025-12-01T24:00:00+07:00', '2025-12-01T00:00:60+07:00',
    '2025-02-29T00:00:00+07:00', '1969-12-31T00:00:00+07:00',
    '2101-01-01T00:00:00+07:00', '2025-12-01t00:00:00+07:00',
    ' 2025-12-01T00:00:00+07:00', '2025-12-01T00:00:00+07:00 ',
    '2025-12-01T00:00:00+07:00\n', '\u0662\u0660\u0662\u0664-02-29T00:00:00+07:00',
    True, False, 0, [], {},
])
def test_active_b_unreviewed_offset_or_malformed_date_stays_unsupported(value):
    form, pages, footer = inputs()
    pages[0]['data'][0]['WithholdingSlipsDate'] = value
    with pytest.raises(_UnsupportedMetadata):
        project(form, pages, footer)


def test_jakarta_offset_does_not_widen_shared_helper_or_offline_a():
    value = '2024-02-29T00:00:00+07:00'
    # L11-A also uses this helper without the active-B opt-in.
    with pytest.raises(_UnsupportedMetadata):
        projection._l3_date(value)
    form, pages, footer = inputs()
    form['IncomeOverseas'][0]['DateOfTransaction'] = value
    with pytest.raises(_UnsupportedMetadata):
        project(form, pages, footer)


@pytest.mark.parametrize('field', (*BASE_FIELDS, *ROW_METADATA))
def test_closed_extended_row_refuses_each_missing_field_without_mutation(field):
    form, pages, footer = inputs()
    _extend(pages)
    del pages[0]['data'][0][field]
    before = deepcopy((form, pages, footer))
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l3_domestic_row'):
        project(form, pages, footer)
    assert (form, pages, footer) == before


@pytest.mark.parametrize('field', tuple(ROW_METADATA))
def test_partial_metadata_extension_is_not_silently_stripped(field):
    form, pages, footer = inputs()
    pages[0]['data'][0][field] = ROW_METADATA[field]
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l3_domestic_row'):
        project(form, pages, footer)


@pytest.mark.parametrize(('field', 'value'), [
    ('Index', False), ('Index', True), ('Index', '0'), ('Index', 1), ('Index', None),
    ('IncomeTaxUsd', False), ('IncomeTaxUsd', '0'), ('IncomeTaxUsd', 1),
    ('IncomeTaxUsd', None), ('IncomeTaxUsd', 0.5), ('IncomeTaxUsd', 1000000000000000),
    ('IsManually', False), ('IsManually', 1), ('IsManually', 'true'), ('IsManually', None),
    ('TableSource', 'TAXPAYER_ACCOUNTING'), ('TableSource', ''), ('TableSource', False),
    ('TableSource', {}), ('Action', 'download'), ('Action', False), ('Action', []),
])
def test_extended_row_rejects_nonreviewed_metadata_values(field, value):
    form, pages, footer = inputs()
    _extend(pages)
    pages[0]['data'][0][field] = value
    before = deepcopy((form, pages, footer))
    with pytest.raises(_UnsupportedMetadata):
        project(form, pages, footer)
    assert (form, pages, footer) == before


@pytest.mark.parametrize('extended', [False, True])
def test_unknown_fourteenth_or_ninth_field_is_not_accepted(extended):
    form, pages, footer = inputs()
    if extended:
        _extend(pages)
    pages[0]['data'][0]['SYNTHETIC_UNREVIEWED_FIELD'] = None
    with pytest.raises(_UnsupportedMetadata, match='unsupported_corporate_l3_domestic_row'):
        project(form, pages, footer)


@pytest.mark.parametrize('lexeme', ['0', '0.0', '0e0', '-0'])
def test_extended_numeric_zero_metadata_preserves_original_json_number_lexemes(lexeme):
    form, pages, footer = inputs()
    _extend(pages)
    captured = _corporate_json(json.dumps(form))
    captured_footer = _corporate_json(json.dumps(footer))
    observed_pages = [{**page, 'data': _corporate_json(json.dumps(page['data']))} for page in pages]
    for page in observed_pages:
        for row in page['data']:
            for field in ('Index', 'IncomeTaxUsd'):
                row[field] = _corporate_json(lexeme)
    before = deepcopy((captured, observed_pages, captured_footer))
    result = projection.project_l3(captured, pages=observed_pages, footer_payload=captured_footer,
        headers=deepcopy(HEADERS), footer_spans=deepcopy(SPANS), tax_type='ICT_RCIT',
        locale='id-ID', timezone_name='Asia/Jakarta', labels=deepcopy(LABELS))
    assert (captured, observed_pages, captured_footer) == before
    for field in ('Index', 'IncomeTaxUsd'):
        entries = [entry for entry in result['provenance'] if entry.get('source') == 'grid'
                   and entry.get('path', [])[-1:] == [field]]
        assert len(entries) == 12
        assert all((entry['type'], entry['value']) == ('number', lexeme) for entry in entries)


def test_466_complete_pages_preserve_4654_duplicate_rows_without_summing_footer_operands():
    form, pages, footer = inputs()
    row = deepcopy(pages[0]['data'][0])
    row.update(deepcopy(ROW_METADATA), WithholdingSlipsDate='2024-02-29T00:00:00+07:00')
    pages = [{'offset': offset, 'rows': 10, 'total': 4654,
              'data': [deepcopy(row) for _ in range(min(10, 4654 - offset))]}
             for offset in range(0, 4654, 10)]
    assert len(pages) == 466
    result = project(form, pages, footer)
    body = result['tables'][1]
    assert body['source_total'] == body['body_row_count'] == 4654
    rows = body['rows'][:body['body_row_count']]
    assert [value[0] for value in rows] == [str(index % 10 + 1) for index in range(4654)]
    assert all(value[1:] == rows[0][1:] for value in rows)
    assert rows[0][7] == '29-02-2024'
    assert body['footer'] == [['JUMLAH', '50', '40', ''],
                              ['KREDIT PAJAK LUAR NEGERI', '', '1', ''],
                              ['JUMLAH KREDIT PAJAK', '', '41', '']]
    metadata = [entry for entry in result['provenance']
                if entry.get('source') == 'grid' and entry.get('destination', {}).get('metadata') in ROW_METADATA]
    assert len(metadata) == len(ROW_METADATA) * 4654
