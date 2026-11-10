"""Synthetic live-shaped L3 B row contracts; runtime tests are CI-only."""
from copy import deepcopy

from test_corporate_l3_projection import inputs, project


ROW_METADATA = {'IncomeTaxUsd': 0, 'IsManually': True, 'TableSource': None,
                'Index': 0, 'Action': None}


def test_l3_closed_thirteen_key_rows_keep_display_and_every_typed_metadata_leaf():
    form, pages, footer = inputs()
    legacy = project(form, pages, footer)
    for page in pages:
        for row in page['data']:
            row.update(deepcopy(ROW_METADATA))
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
                assert entry['destination']['metadata'] == field
                assert 'column' not in entry['destination']
