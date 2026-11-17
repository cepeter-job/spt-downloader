"""Closed D manifest facts: validation is not independent production/finality."""
from copy import deepcopy
import hashlib
import json

import pytest

import coretax_corporate_l10d as owner
from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import exchange
from test_corporate_l10d_native import packet, bindings, selected, corpus
from test_corporate_component_lifetime import setup, begin, navigate, DETAIL, SCOPE
from test_corporate_component_lifetime import selected as network_record


KEY = 'corporate_l10d_lifetime'


def fact(component):
    return {key: component[key] for key in ('attempt', 'record_id', 'source_url', 'detail_url')} | {
        'kind': 'corporate-l10d-spa-v1', 'selection_rule': 'submitted-immutable-induk-selection-v1',
        **dict.fromkeys(('fresh_root', 'fresh_main', 'fresh_child', 'stable_root', 'stable_main',
                         'stable_child', 'enabled_boundaries', 'final_joint_snapshot'), True)}


@pytest.mark.parametrize('key', tuple(fact(packet()['context']['component_lifetime'])))
@pytest.mark.parametrize('defect', ['missing', 'wrong-type'])
def test_d_manifest_fact_is_closed_positive_and_exactly_bound(key, defect):
    component = packet()['context']['component_lifetime']
    value = fact(component)
    assert owner.validate_lifetime(value, component) == value
    if defect == 'missing': del value[key]
    else: value[key] = 1
    with pytest.raises(JsonSafetyError): owner.validate_lifetime(value, component)


@pytest.mark.parametrize('defect', ['null', 'no-parent', 'cross-attempt', 'cross-record',
    'cross-source', 'cross-detail', 'wrong-rule', 'extra', 'false-final', 'mixed'])
@pytest.mark.parametrize('observed', [False, True])
def test_supplied_d_history_is_fatal_before_optional_form_fallback(defect, observed):
    raw = packet()
    value = fact(raw['context']['component_lifetime'])
    raw['context'][KEY] = value
    if defect == 'null': raw['context'][KEY] = None
    elif defect == 'no-parent': del raw['context']['component_lifetime']
    elif defect == 'cross-attempt': value['attempt'] = 'f' * 32
    elif defect == 'cross-record': value['record_id'] = 'foreign'
    elif defect == 'cross-source': value['source_url'] += '/foreign'
    elif defect == 'cross-detail': value['detail_url'] += '&foreign=true'
    elif defect == 'wrong-rule': value['selection_rule'] = 'saved-equal-flags'
    elif defect == 'extra': value['checked'] = True
    elif defect == 'false-final': value['final_joint_snapshot'] = False
    bodies = [raw]
    if defect == 'mixed': bodies.append(packet(sequence=2))
    with pytest.raises(JsonSafetyError):
        adapt_corporate_detail(bodies, selected(), corpus.SCOPE, bindings() if observed else [])


def test_well_formed_supplied_fact_is_retained_but_does_not_flip_unproduced_admission():
    raw = packet()
    value = fact(raw['context']['component_lifetime'])
    raw['context'][KEY] = value
    result = adapt_corporate_detail([raw], selected(), corpus.SCOPE, bindings())
    assert result['provenance']['events'][0][KEY] == value
    assert not result['eligible']
    assert result['provenance']['non_display_originals'][0]['native_admission'] is False


@pytest.mark.parametrize('defect', ['none', 'descriptor', 'null', 'no-parent', 'cross-attempt', 'false-final'])
def test_live_and_checkpoint_readers_validate_d_manifest_only_not_descriptor_override(tmp_path, defect):
    context, page = setup()
    record = network_record()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        saved = capture.drain()
        path = tmp_path / saved['manifest']
        manifest = json.loads(path.read_bytes())
        value = fact(manifest['component_lifetime'])
        manifest[KEY] = value
        if defect == 'descriptor': manifest['responses'][0][KEY] = deepcopy(value)
        elif defect == 'null': manifest[KEY] = None
        elif defect == 'no-parent': del manifest['component_lifetime']
        elif defect == 'cross-attempt': value['attempt'] = 'f' * 32
        elif defect == 'false-final': value['final_joint_snapshot'] = False
        # Deliberately injected schema fixture, NOT independent final proof.
        # Production drain is still forbidden to claim D finality. Rehashing
        # isolates the semantic reader check from the existing byte hash gate.
        raw = json.dumps(manifest, sort_keys=True).encode()
        path.write_bytes(raw)
        saved = {**manifest, 'manifest': saved['manifest'], 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
        capture._manifest_hash = saved['manifest_sha256']
        capture._result = deepcopy(saved)
        record['detail_url'] = DETAIL
        page.evaluate = lambda *_: pytest.fail('Held readers must not probe a browser')
        if defect == 'none':
            live = list(capture.iter_bodies())
            assert live[0]['context'][KEY] == value
            assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == live
        else:
            with pytest.raises(JsonSafetyError): list(capture.iter_bodies())
            with pytest.raises(JsonSafetyError): checkpoint_bodies(tmp_path, saved, record, SCOPE)
