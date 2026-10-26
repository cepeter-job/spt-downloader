"""Synthetic strict L8 history/custody contracts; runner execution only."""
from copy import deepcopy
import hashlib
import json

import pytest

import coretax_json as adapter
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import exchange
from test_corporate_component_lifetime import setup, selected, begin, navigate, LIST, DETAIL, SCOPE
from test_corporate_l8_native import lifetime


def proof(capture=None):
    return {**lifetime(attempt=capture.attempt if capture else 'a'*32),
        'record_id': 'fixture-record', 'source_url': LIST, 'detail_url': DETAIL}


def validate(value):
    method = getattr(adapter, '_capture_l8_lifetime', None)
    assert callable(method), 'Strict manifest-owned L8 history validation is absent'
    return method(value, attempt='a'*32, record_id='fixture-record', source_url=LIST, detail_url=DETAIL)


def test_strict_l8_history_validator_keeps_literal_evidence_without_mutation():
    value = proof()
    before = deepcopy(value)
    assert validate(value) == value and value == before


@pytest.mark.parametrize('key', tuple(proof()))
@pytest.mark.parametrize('mutation', ['missing', 'wrong-type'])
def test_l8_history_missing_or_wrongly_typed_fact_is_fatal(key, mutation):
    value = proof()
    if mutation == 'missing': del value[key]
    else: value[key] = 1
    with pytest.raises(JsonSafetyError):
        validate(value)


@pytest.mark.parametrize('key', ['fresh_root', 'stable_root', 'no_dependent_forms'])
@pytest.mark.parametrize('value', [False, None, 'true'])
def test_l8_history_qualifying_facts_must_be_exact_true(key, value):
    item = proof()
    item[key] = value
    with pytest.raises(JsonSafetyError):
        validate(item)


@pytest.mark.parametrize('key,value', [('kind', 'corporate-submitted-spa-v1'),
    ('attempt', 'b'*32), ('record_id', 'foreign'), ('source_url', LIST+'/'),
    ('detail_url', DETAIL+'&view=true'), ('detail_url', DETAIL.replace('?view=true', '')),
    ('extra', True)])
def test_l8_history_known_binding_changes_or_extra_fields_are_fatal(key, value):
    item = proof()
    item[key] = value
    with pytest.raises(JsonSafetyError):
        validate(item)


class History:
    """Protocol-only structural facts; actual MutationObserver gets Edge cases."""
    def __init__(self):
        self.state = dict(initial_clear=True, root_seen=True, root_changed=False, dependent_seen=False)
        self.disposed = self.disconnected = False
        self.on_sample = None

    def evaluate(self, script):
        if 'disconnect' in script:
            self.disconnected = True
            return None
        if self.on_sample:
            self.on_sample()
        return dict(self.state)

    def dispose(self):
        self.disposed = True


def history_setup():
    context, page = setup()
    make_document = page.evaluate_handle
    guard = History()
    def document(script):
        handle = make_document(script)
        handle.evaluate_handle = lambda source: guard
        return handle
    page.evaluate_handle = document
    return context, page, guard


def observe(capture):
    method = getattr(capture, 'observe_l8_lifetime', None)
    assert callable(method), 'Owned L8 structural history observation is absent'
    return method()


def test_l8_history_is_manifest_owned_held_once_and_replayed_without_browser(tmp_path):
    context, page, guard = history_setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        response = exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) == proof(capture)
        manifest = capture.drain()
        assert manifest['complete'] and manifest['corporate_l8_lifetime'] == proof(capture)
        assert 'corporate_l8_lifetime' not in manifest['responses'][0]
        packets = list(capture.iter_bodies())
        assert packets[0]['context']['corporate_l8_lifetime'] == proof(capture)
        assert packets[0]['body'] == response.raw and response.reads == 1
        record['detail_url'] = DETAIL
        page.evaluate_handle = lambda _: pytest.fail('Replay cannot synthesize browser history')
        assert checkpoint_bodies(tmp_path, manifest, record, SCOPE) == packets
    assert guard.disconnected and guard.disposed
    assert not any(page.listeners.values()) and not any(context.listeners.values())


@pytest.mark.parametrize('fact,value', [('initial_clear', False), ('root_seen', False),
                                     ('dependent_seen', True)])
def test_unqualified_l8_history_does_not_poison_legacy_capture_or_create_proof(tmp_path, fact, value):
    context, page, guard = history_setup()
    guard.state[fact] = value
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) is None
        manifest = capture.drain()
        assert manifest['complete'] and 'corporate_l8_lifetime' not in manifest


def test_known_l8_root_history_change_is_fatal_even_if_final_owner_is_same(tmp_path):
    context, page, guard = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) is not None
        guard.state['root_changed'] = True
        with pytest.raises(JsonSafetyError):
            capture.drain()
    assert guard.disconnected and guard.disposed


def test_l8_final_history_sampling_preserves_late_response_fence(tmp_path):
    context, page, guard = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) is not None
        def late():
            guard.on_sample = None
            exchange(context, page, content_type='text/html')
        guard.on_sample = late
        manifest = capture.drain()
        assert not manifest['complete'] and 'response-after-final-drain' in manifest['reasons']


@pytest.mark.parametrize('defect', ['descriptor', 'manifest', 'bound-field'])
def test_l8_history_manifest_or_descriptor_mutation_is_fatal(tmp_path, defect):
    context, page, _ = history_setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert observe(capture) is not None
        saved = capture.drain()
        record['detail_url'] = DETAIL
        manifest_path = tmp_path / saved['manifest']
        changed = json.loads(manifest_path.read_bytes())
        if defect == 'descriptor':
            changed['responses'][0]['corporate_l8_lifetime'] = proof(capture)
        elif defect == 'bound-field':
            changed['corporate_l8_lifetime']['record_id'] = 'foreign'
        else:
            changed['corporate_l8_lifetime']['stable_root'] = False
        raw = json.dumps(changed, sort_keys=True).encode()
        manifest_path.write_bytes(raw)
        # Even a rehashed caller declaration cannot authorize malformed history.
        saved = {**changed, 'manifest': saved['manifest'], 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
        with pytest.raises(JsonSafetyError):
            checkpoint_bodies(tmp_path, saved, record, SCOPE)
