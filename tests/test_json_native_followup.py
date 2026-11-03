"""Synthetic live-shape JSON regressions; product execution is runner-only."""
from copy import deepcopy
import json

import pytest

import coretax_corporate as observer
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture
from spt_desktop import diagnostics
from l11a_observer_fixture import Fixture
from test_corporate_l11a_observer import open_selected
from test_json_hybrid_native import browser as browser
import test_corporate_l11a_native as l11a
import test_corporate_l3_native as l3
import support_json_corpus as corpus


def overlapping_catalogs(kinds):
    raw, forms = l11a.packets(transport='pair'), l11a.bindings('pair')
    for index, kind in enumerate(kinds, 99):
        raw.append(l11a.packet({'IsSuccessful': True, 'Payload': [l11a.catalog(kind)]},
            index, l11a.REFERENCES[kind], None, method='GET'))
        forms[1]['projection']['references'].append(
            {'endpoint': l11a.REFERENCES[kind], 'method': 'GET', 'sequences': [index]})
    return raw, forms


@pytest.mark.parametrize('kinds', [l11a.TYPES[3:4], l11a.TYPES[4:], l11a.TYPES[3:]])
@pytest.mark.parametrize('completion_order', [False, True])
def test_matching_l11a_catalog_overlaps_preserve_every_original_source(kinds, completion_order):
    raw, forms = overlapping_catalogs(kinds)
    if completion_order:
        raw = [raw[0], *reversed(raw[1:])]
    before = deepcopy((raw, forms))
    result = adapt_corporate_detail(iter(raw), l11a.selected(), corpus.SCOPE, forms)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    evidence = next(p['values'] for p in result['provenance']['projections'] if p['form'] == 'L11-A')
    references = {p['context']['sequence'] for p in raw if p['context']['method'] == 'GET'}
    assert references <= {p['response_sequence'] for p in evidence}
    assert (raw, forms) == before


def test_l11a_failed_secondary_catalog_is_not_hidden_by_matching_pair():
    raw, forms = overlapping_catalogs(l11a.TYPES[4:])
    value = json.loads(raw[-1]['body'])['Payload']
    l11a.replace_payload(raw, len(raw) - 1, value, status=500)
    result = adapt_corporate_detail(iter(raw), l11a.selected(), corpus.SCOPE, forms)
    assert not result['eligible']
    assert 'missing_or_failed_corporate_l11a_catalog' in result['reason']


@pytest.mark.parametrize('defect,reason', [
    ('wrong-ui-owner', 'grid_ownership'),
    ('table-outside-p-table', 'grid_ownership'),
    ('missing-reference', 'reference_request_missing'),
    ('missing-grid', 'grid_request_missing'),
    ('changed-header-after-page', 'stable_table_metadata'),
])
def test_l11a_refusal_reports_fixed_reason(browser, tmp_path, monkeypatch, defect, reason):
    fixture = Fixture(browser, monkeypatch, defect=defect)
    events = []
    monkeypatch.setattr(diagnostics, 'record', lambda event, **fields: events.append((event, fields)))
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[l11a.corpus.ORIGIN + '/returnsheets/id-ID/525.ec1edffbb4a91d20.js'])
            assert forms is None
        refusal = [fields for event, fields in events if event == 'corporate.observe_unavailable'][-1]
        assert refusal['corporate_observer_stage'] == 'l11a'
        assert refusal['corporate_l11a_reason'] == reason
        assert diagnostics._safe_fields({'corporate_l11a_reason': reason}) == {'corporate_l11a_reason': reason}
        assert diagnostics._safe_fields({'corporate_l11a_reason': 'SYNTHETIC PRIVATE BAIT'}) == {}
    finally:
        fixture.close()


@pytest.mark.parametrize('module,flag', [
    (l3, 'IsIncomeTaxOverseas'), (l11a, 'IsDeclareEntertainmentExpense')])
def test_current_induk_visibility_supports_absent_outer_flag_only_with_explicit_proof(module, flag):
    raw, forms = module.packets(), module.bindings()
    value = json.loads(raw[0]['body'])
    del value['Payload'][flag]
    raw[0] = module.fresh_packet(value)
    forms[1]['projection']['visibility_binding'] = 'current-induk-enabled-v1'
    before = deepcopy((raw, forms))
    result = adapt_corporate_detail(iter(raw), module.selected(), corpus.SCOPE, forms)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert (raw, forms) == before


@pytest.mark.parametrize('module,flag', [
    (l3, 'IsIncomeTaxOverseas'), (l11a, 'IsDeclareEntertainmentExpense')])
@pytest.mark.parametrize('outer', [None, False, 0, '1'])
def test_current_induk_visibility_does_not_override_present_unproved_outer_flags(module, flag, outer):
    raw, forms = module.packets(), module.bindings()
    value = json.loads(raw[0]['body'])
    value['Payload'][flag] = outer
    raw[0] = module.fresh_packet(value)
    forms[1]['projection']['visibility_binding'] = 'current-induk-enabled-v1'
    assert not adapt_corporate_detail(iter(raw), module.selected(), corpus.SCOPE, forms)['eligible']
