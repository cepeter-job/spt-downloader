"""Synthetic live-shape JSON regressions; product execution is runner-only."""
from copy import deepcopy
import json

import pytest

import coretax_corporate as observer
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture
from spt_desktop import diagnostics
from l11a_observer_fixture import Fixture
from l3_observer_fixture import Fixture as L3Fixture
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
                approved_digest=fixture.pins[observer.CIT_SOURCE_URL])
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


def test_owned_l11a_keeps_matching_pair_and_singleton_provenance(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch, transport='pair-overlap')
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            page.locator('a[role=tab]').filter(has_text='L11-A').click()
            page.wait_for_function('window.l11aReferenceReplies===5')
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[observer.CIT_SOURCE_URL])
            assert forms is not None
            assert len(forms[1]['projection']['references']) == 5
            manifest = capture.drain()
            assert manifest['complete']
            bodies = list(capture.iter_bodies())
            result = adapt_corporate_detail(iter(bodies), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'], result['reason']
            evidence = next(p['values'] for p in result['provenance']['projections'] if p['form'] == 'L11-A')
            references = {p['context']['sequence'] for p in bodies if p['context']['method'] == 'GET'}
            assert references <= {p['response_sequence'] for p in evidence}
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('fixture_class,flag', [
    (L3Fixture, 'IsIncomeTaxOverseas'), (Fixture, 'IsDeclareEntertainmentExpense')])
def test_owned_current_induk_visibility_marks_absent_outer_flag(
        browser, tmp_path, monkeypatch, fixture_class, flag):
    fixture = fixture_class(browser, monkeypatch)
    value = json.loads(fixture.raw)
    del value['Payload'][flag]
    fixture.raw = corpus.wire(value).encode()
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[observer.CIT_SOURCE_URL])
            assert forms is not None
            assert forms[1]['projection']['visibility_binding'] == 'current-induk-enabled-v1'
            assert capture.drain()['complete']
            result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'], result['reason']
            assert result['provenance']['projections'][0]['visibility_binding'] == 'current-induk-enabled-v1'
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('fixture_class,name,method', [
    (L3Fixture, 'L3', '_observe_l3'), (Fixture, 'L11-A', '_observe_l11a')])
@pytest.mark.parametrize('change', ['disabled', 'hidden', 'control'])
def test_visibility_proof_rechecks_enabled_form_after_observation(
        browser, tmp_path, monkeypatch, fixture_class, name, method, change):
    fixture = fixture_class(browser, monkeypatch)
    original = getattr(observer, method)

    def disable_after_observation(page, *args, **kwargs):
        result = original(page, *args, **kwargs)
        if change == 'hidden':
            form = args[0]
            form.evaluate('(e)=>e.style.display="none"')
        else:
            page.locator('a[role=tab]').filter(has_text=name).evaluate(
                '(e, change)=>e.setAttribute(change==="disabled"?"aria-disabled":"aria-controls",'
                'change==="disabled"?"true":"synthetic-foreign-panel")', change)
        return result

    monkeypatch.setattr(observer, method, disable_after_observation)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[observer.CIT_SOURCE_URL]) is None
    finally:
        fixture.close()


@pytest.mark.parametrize('module,flag', [
    (l3, 'IsIncomeTaxOverseas'), (l11a, 'IsDeclareEntertainmentExpense')])
@pytest.mark.parametrize('defect', ['unknown-marker', 'missing-current', 'current-bool', 'no-lifetime'])
def test_current_induk_visibility_keeps_required_source_and_lifetime_proof(module, flag, defect):
    raw, forms = module.packets(), module.bindings()
    value = json.loads(raw[0]['body'])
    del value['Payload'][flag]
    current = json.loads(value['Payload']['CurrentFormData'])
    if defect == 'missing-current':
        del current['MainFormData'][flag]
    elif defect == 'current-bool':
        current['MainFormData'][flag] = True
    value['Payload']['CurrentFormData'] = corpus.wire(current)
    raw[0] = module.fresh_packet(value)
    forms[1]['projection']['visibility_binding'] = (
        'SYNTHETIC UNREVIEWED' if defect == 'unknown-marker' else 'current-induk-enabled-v1')
    if defect == 'no-lifetime':
        for packet in raw:
            del packet['context']['component_lifetime']
    assert not adapt_corporate_detail(iter(raw), module.selected(), corpus.SCOPE, forms)['eligible']


def test_l11a_omitted_secondary_catalog_binding_cannot_hide_original_response():
    raw, forms = overlapping_catalogs(l11a.TYPES[4:])
    forms[1]['projection']['references'].pop()
    result = adapt_corporate_detail(iter(raw), l11a.selected(), corpus.SCOPE, forms)
    assert not result['eligible'] and 'unbound_corporate_l11a_catalog' in result['reason']


@pytest.mark.parametrize('module', [l3, l11a])
@pytest.mark.parametrize('index', [None, 0, '', [], {}])
def test_active_grid_envelope_supports_only_absent_or_null_index(module, index):
    raw, forms = module.packets(), module.bindings()
    urls = {module.GRID} if module is l3 else set(module.GRIDS.values())
    sequences = set()
    for i, packet in enumerate(raw):
        context = packet['context']
        if context['url'] not in urls:
            continue
        value = json.loads(packet['body'])
        value['Payload']['Index'] = index
        raw[i] = module.packet(value, context['sequence'], context['url'], context['request_json'])
        sequences.add(context['sequence'])
    before = deepcopy((raw, forms))
    result = adapt_corporate_detail(iter(raw), module.selected(), corpus.SCOPE, forms)
    assert result['eligible'] is (index is None), result['reason']
    if index is None:
        evidence = result['provenance']['projections'][0]['values']
        assert sequences == {p['response_sequence'] for p in evidence
                             if p.get('rule') == 'unused-null-envelope-index' and p['path'] == ['Index']}
    assert (raw, forms) == before
