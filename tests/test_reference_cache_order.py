"""Pinned cache order precedes version selection; raw paths never move."""
from copy import deepcopy

import pytest

from coretax_corporate_projection import project_countries
from coretax_json import _UnsupportedMetadata
from coretax_pph21_json_bindings import project_pph21_references
from coretax_unifikasi_json import project_references
from test_dated_reference_catalogs import CLOCK, row
from test_pph21_json_references import source, TYPES
from test_unifikasi_json_references import catalogs


FAMILIES = ('pph21', 'unifikasi', 'country')


def project(family, rows, clock=None):
    if family == 'country':
        payload = [{'ReferenceDataType': 'COUNTRY_CODE', 'Details': deepcopy(rows)}]
    else:
        payload = source() if family == 'pph21' else catalogs()
        payload[0]['Details'] = deepcopy(rows)
    before = deepcopy(payload)
    try:
        if family == 'pph21':
            result = project_pph21_references(payload, requested_types=TYPES,
                                             locale='id-ID', clock_interval=clock)
            label = result['lookups']['TaxCertificate']['0001']
        elif family == 'unifikasi':
            result = project_references(payload, clock_interval=clock)
            label = result['lookups']['EBUPOT_TAX_CERTIFICATE']['0001']
        else:
            result = project_countries(payload, clock_interval=clock)
            label = result['lookups']['0001']
        selected, = [entry for entry in result['provenance']
                     if entry['path'][0] == 0 and entry['path'][-1] == 'CodeDescription'
                     and entry['path'][2] < len(rows)
                     and rows[entry['path'][2]]['Code'] == '0001'
                     and (entry.get('rule', '').startswith('reviewed-country-active-version:')
                          or entry.get('projection_rule', '').startswith('reviewed-grid-active-version:'))]
        return label, selected, result['provenance']
    finally:
        assert payload == before


def active(label, parameter=None):
    value = row(label, ValidTo=None)
    if parameter is not None:
        value['ParameterData'] = parameter
    return value


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('rows,chosen', [
    ([active('ZULU'), active('ALPHA')], 1),
    ([active('SAME'), active('SAME')], 0),
    # JS string relational order compares UTF-16 units, unlike Python ord().
    ([active('\ue000 LABEL'), active('\U00010000 LABEL')], 1),
    ([active('ALPHA', '{"DisplayIndex":2}'), active('ZULU', '{"DisplayIndex":1}')], 1),
    # Homogeneous string keys use lexical ordering, not numeric conversion.
    ([active('ALPHA', '{"DisplayIndex":"2"}'), active('ZULU', '{"DisplayIndex":"10"}')], 1),
    ([active('ZULU', '{"DisplayIndex":1}'), active('ALPHA', '{"DisplayIndex":1}')], 0),
    ([active('ALPHA', '{"DisplayIndex":9007199254740991}'),
      active('ZULU', '{"DisplayIndex":-9007199254740991}')], 1),
    ([active('ZULU', '{"DisplayIndex":0}'), active('ALPHA', '{"DisplayIndex":-0}')], 0),
    ([active('ALPHA', '{"DisplayIndex":"\ue000"}'),
      active('ZULU', '{"DisplayIndex":"\U00010000"}')], 1),
    # Only the first raw row decides the global branch; later metadata is inert.
    ([active('ZULU', '{}'), active('ALPHA', '{"DisplayIndex":99}')], 1),
    ([active('ZULU', '{"DisplayIndex" : 0}'), active('ALPHA', '{"DisplayIndex":99}')], 1),
    ([active('ZULU', '{}'), active('ALPHA', 'not parsed in description branch')], 1),
    ([{**active('OTHER', '{"DisplayIndex":9}'), 'Code': 'OTHER'},
      active('ALPHA', '{"DisplayIndex" : 2}'), active('ZULU', '{"DisplayIndex" : 1}')], 2),
])
def test_cache_order_selects_original_row_with_literal_provenance(family, rows, chosen):
    label, selected, evidence = project(family, rows)
    assert label == rows[chosen]['CodeDescription']
    assert selected['path'] == [0, 'Details', chosen, 'CodeDescription']
    for index, value in enumerate(rows):
        entry, = [e for e in evidence if e['path'] == [0, 'Details', index, 'ParameterData']]
        assert entry['value'] == value.get('ParameterData')
        assert entry['type'] == ('string' if 'ParameterData' in value else 'missing')


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('dates,chosen', [
    ([{'ValidTo': '2030-01-01'}, {'ValidTo': '2029-01-01'}], 1),
    ([{'ValidTo': '2020-01-01'}, {'ValidTo': '2021-01-01'}], 1),
    ([{'ValidTo': '2020-01-01', 'ValidFrom': '2022-01-01'},
      {'ValidTo': '2021-01-01', 'ValidFrom': '2022-01-01'}], 1),
])
def test_all_order_dependent_dated_rules_consume_cache_order(family, dates, chosen):
    rows = [row('ZULU', **dates[0]), row('ALPHA', **dates[1])]
    label, selected, _ = project(family, rows, deepcopy(CLOCK))
    assert label == rows[chosen]['CodeDescription']
    assert selected['path'][2] == chosen
    assert selected['clock_interval'] == CLOCK


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('parameter', [True, 1, [], {}, '{"DisplayIndex":null}',
    '{"DisplayIndex":true}', '{"DisplayIndex":1.5}', '{"DisplayIndex":9007199254740992}',
    '{"DisplayIndex":1,"DisplayIndex":2}', '{"DisplayIndex":NaN}',
    '{"DisplayIndex":[]}', '{"DisplayIndex":{}}', '{"DisplayIndex":'])
def test_unproved_global_cache_key_never_uses_response_order(family, parameter):
    rows = [active('ZULU'), active('ALPHA', '{"DisplayIndex":1}')]
    rows[0]['ParameterData'] = parameter
    with pytest.raises(_UnsupportedMetadata):
        project(family, rows)


@pytest.mark.parametrize('family', FAMILIES)
@pytest.mark.parametrize('other', ['{}', '{"DisplayIndex":null}', '{"DisplayIndex":"1"}', 'invalid'])
def test_triggered_sort_requires_every_key_and_one_proved_comparator_type(family, other):
    with pytest.raises(_UnsupportedMetadata):
        project(family, [active('ZULU', '{"DisplayIndex":2}'), active('ALPHA', other)])


@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
def test_country_cache_order_reaches_final_saved_workbook_and_original_response_path(tmp_path, model):
    import coretax
    from openpyxl import load_workbook
    from coretax_json import adapt_corporate_detail
    import support_json_corpus as corpus
    from test_corporate_l11c_native import packets, envelope, bindings, selected

    rows = [{**active('ZULU'), 'Code': 'SYN_COUNTRY_A'},
            {**active('ALPHA'), 'Code': 'SYN_COUNTRY_A'}]
    raw = packets(envelope(model), [{'ReferenceDataType': 'COUNTRY_CODE', 'Details': rows}])
    before = deepcopy(raw)
    record = selected(model)
    result = adapt_corporate_detail(iter(raw), record, corpus.SCOPE, bindings())
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [s for s in result['sections'] if s['name'] == 'L11-C']
    assert section['tables'][0]['rows'][0][3] == 'ALPHA'
    assert any(e['response_sequence'] == 2 and e['path'] == [0, 'Details', 1, 'CodeDescription']
               and e['value'] == 'ALPHA' for e in result['provenance']['projections'][0]['values'])
    record.update(capture_complete=True, sections=result['sections'])
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
           'complete': True, 'errors': [], 'records': [record]}
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    name, = [n for n in run['output_files'] if n != 'resume.xlsx']
    assert model in name
    book = load_workbook(tmp_path / name)
    try:
        assert book['L11-C']['D3'].value == book['L11-C']['D4'].value == 'ALPHA'
    finally:
        book.close()
    assert raw == before
