"""Pinned grid version selection uses captured browser time, never replay time."""
from copy import deepcopy

import pytest

from coretax_json import _UnsupportedMetadata
from coretax_pph21_json_bindings import project_pph21_references
from coretax_unifikasi_json import project_references
from test_pph21_json_references import source, TYPES
from test_unifikasi_json_references import catalogs


START = 1735689600000  # 2025-01-01T00:00:00.000Z, synthetic.
CLOCK = {'attempt': 'a' * 32, 'start_ms': START, 'end_ms': START + 1000,
         'timezone': 'Asia/Jakarta'}


def project(family, rows, clock=CLOCK):
    payload = source() if family == 'pph21' else catalogs()
    payload[0]['Details'] = deepcopy(rows)
    before = deepcopy(payload)
    if family == 'pph21':
        result = project_pph21_references(payload, requested_types=TYPES, locale='id-ID',
                                         clock_interval=deepcopy(clock))
        label = result['lookups']['TaxCertificate']['0001']
    else:
        result = project_references(payload, clock_interval=deepcopy(clock))
        label = result['lookups']['EBUPOT_TAX_CERTIFICATE']['0001']
    assert payload == before
    return label, result['provenance']


def row(label, **dates):
    return {'Code': '0001', 'CodeDescription': label, **dates}


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
@pytest.mark.parametrize('rows,expected', [
    # Cache sorts descriptions before the active-version consumer runs.
    ([row('FIRST FUTURE', ValidTo='2030-01-01'), row('EARLIER FUTURE', ValidTo='2029-01-01')], 'EARLIER FUTURE'),
    ([row('OLD', ValidTo='2021-01-01', ValidFrom='2019-01-01'),
      row('LATEST FROM', ValidTo='2020-01-01', ValidFrom='2022-01-01')], 'LATEST FROM'),
    ([row('FIRST TIED', ValidTo='2021-01-01', ValidFrom='2022-01-01'),
      row('SECOND TIED', ValidTo='2020-01-01', ValidFrom='2022-01-01')], 'FIRST TIED'),
    ([row('FIRST FALLBACK', ValidTo='2021-01-01'), row('SECOND', ValidTo='2020-01-01')], 'FIRST FALLBACK'),
    ([row('EXACT CUTOFF', ValidTo='2025-01-01T00:00:00.000Z'),
      row('STRICTLY LATER', ValidTo='2025-01-01T00:00:02.000Z')], 'STRICTLY LATER'),
    ([row('UTC DATE CUTOFF', ValidTo='2025-01-01'),
      row('FUTURE', ValidTo='2025-01-02')], 'FUTURE'),
    ([row('LOCAL CUTOFF', ValidTo='2025-01-01T07:00:00'),
      row('FUTURE', ValidTo='2025-01-02')], 'FUTURE'),
    ([row('OFFSET CUTOFF', ValidTo='2025-01-01T07:00:00.000+07:00'),
      row('FUTURE', ValidTo='2025-01-02')], 'FUTURE'),
])
def test_dated_grid_labels_follow_reviewed_order_and_date_semantics(family, rows, expected):
    actual, evidence = project(family, rows)
    assert actual == expected
    paths = [entry['path'] for entry in evidence]
    for index, candidate in enumerate(rows):
        for key in ('Code', 'CodeDescription', 'ValidTo', 'ValidFrom'):
            assert [0, 'Details', index, key] in paths
    chosen = next(index for index, candidate in enumerate(rows) if candidate['CodeDescription'] == expected)
    assert any(entry['path'] == [0, 'Details', chosen, 'CodeDescription']
               and entry.get('projection_rule', '').startswith('reviewed-grid-active-version:')
               for entry in evidence)


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
@pytest.mark.parametrize('rows', [
    [row('A', ValidTo='2025-01-01T00:00:00.500Z'), row('B', ValidTo='2026-01-01')],
    # Same row at both endpoints is insufficient: A -> B -> fallback A.
    [row('A', ValidTo='2025-01-01T00:00:00.250Z'),
     row('B', ValidTo='2025-01-01T00:00:00.750Z')],
])
def test_selection_must_be_stable_at_every_cutoff_inside_interval(family, rows):
    with pytest.raises(_UnsupportedMetadata):
        project(family, rows)


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
@pytest.mark.parametrize('bad_date', ['tomorrow', '2025-02-30', '01/02/2025',
    '2025-01-01T24:00:00Z', '2025-01-01T00:00:00.0001Z'])
def test_unreviewed_or_missing_dated_validity_does_not_grant_new_branch(family, bad_date):
    first = row('UNKNOWN', ValidTo='2020-01-01', ValidFrom=bad_date)
    with pytest.raises(_UnsupportedMetadata):
        project(family, [first, row('OTHER', ValidTo='2021-01-01')])


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
def test_missing_clock_does_not_resolve_multiple_closed_versions(family):
    with pytest.raises(_UnsupportedMetadata):
        project(family, [row('A', ValidTo='2029-01-01'), row('B', ValidTo='2030-01-01')], None)


def test_clock_does_not_relax_period_or_model_dropdown_unique_code_rules():
    from coretax_pph21_json_bindings import project_pph21_model_references
    payload = catalogs()
    payload[-1]['Details'] *= 2
    with pytest.raises(_UnsupportedMetadata):
        project_references(payload, clock_interval=CLOCK)
    model = [{'ReferenceDataType': 'RETURN_SHEET_MODEL', 'Details': [
        {'Code': 'NORMAL', 'CodeDescription': 'A', 'ValidTo': '2029-01-01'},
        {'Code': 'NORMAL', 'CodeDescription': 'B', 'ValidTo': '2030-01-01'}]}]
    with pytest.raises(_UnsupportedMetadata):
        project_pph21_model_references(model, locale='id-ID')
