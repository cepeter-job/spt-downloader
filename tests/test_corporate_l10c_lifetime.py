"""L10-C-specific manifest custody; synthetic runner execution only."""
from copy import deepcopy
import hashlib
import json

import pytest

import coretax_json as adapter
from coretax_browser import CaptureCancelled
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import exchange
from test_corporate_component_lifetime import setup, selected, begin, navigate, LIST, DETAIL, SCOPE
from test_corporate_l7_history import Element, History


def proof(capture=None):
    return {'kind': 'corporate-l10c-spa-v1', 'attempt': capture.attempt if capture else 'a' * 32,
        'record_id': 'fixture-record', 'source_url': LIST, 'detail_url': DETAIL,
        **dict.fromkeys(('fresh_root', 'fresh_form', 'stable_root', 'stable_form',
                         'stable_grid', 'stable_controls', 'enabled_boundaries'), True)}


def fixture():
    context, page = setup()
    make_document = page.evaluate_handle
    guard = History()

    def document(script):
        handle = make_document(script)
        handle.evaluate_handle = lambda source: guard if 'corporate-l10c-history' in source else None
        return handle

    page.evaluate_handle = document
    return context, page, guard


def boundaries(capture):
    nodes = [Element() for _ in range(5)]
    assert capture.bind_l10c_structure(*nodes, phase='start')
    assert capture.bind_l10c_structure(*nodes, phase='end')
    assert all(node.disposed for node in nodes)
    return capture.observe_l10c_lifetime()


@pytest.mark.parametrize('key', tuple(proof()))
@pytest.mark.parametrize('mutation', ['missing', 'wrong-type'])
def test_l10c_manifest_validator_requires_every_exact_original_fact(key, mutation):
    validate = getattr(adapter, '_capture_l10c_lifetime', None)
    assert callable(validate), 'Source-only RED: no L10-C manifest contract'
    options = dict(attempt='a' * 32, record_id='fixture-record', source_url=LIST, detail_url=DETAIL)
    value = proof()
    assert validate(value, **options) == value
    if mutation == 'missing':
        del value[key]
    else:
        value[key] = 1
    with pytest.raises(JsonSafetyError):
        validate(value, **options)


def test_l10c_capture_manifest_live_and_held_readers_retain_same_original_fact(tmp_path):
    context, page, guard = fixture()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        response = exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture) == proof(capture)
        saved = capture.drain()
        assert saved['corporate_l10c_lifetime'] == proof(capture)
        assert 'corporate_l10c_lifetime' not in saved['responses'][0]
        packets = list(capture.iter_bodies())
        assert response.reads == 1 and packets[0]['body'] == response.raw
        assert packets[0]['context']['corporate_l10c_lifetime'] == proof(capture)
        record['detail_url'] = DETAIL
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == packets
    assert guard.disconnected and guard.disposed


@pytest.mark.parametrize('defect', ['descriptor', 'null', 'component-missing', 'cross-attempt'])
def test_l10c_live_and_held_readers_reject_attestation_overrides(tmp_path, defect):
    context, page, _ = fixture()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        saved = capture.drain()
        path = tmp_path / saved['manifest']
        changed = json.loads(path.read_bytes())
        if defect == 'descriptor':
            changed['responses'][0]['corporate_l10c_lifetime'] = proof(capture)
        elif defect == 'null':
            changed['corporate_l10c_lifetime'] = None
        elif defect == 'component-missing':
            del changed['component_lifetime']
        else:
            changed['corporate_l10c_lifetime']['attempt'] = 'b' * 32
        raw = json.dumps(changed, sort_keys=True).encode()
        path.write_bytes(raw)
        saved = {**changed, 'manifest': saved['manifest'], 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
        capture._manifest_hash, capture._result = saved['manifest_sha256'], deepcopy(saved)
        record['detail_url'] = DETAIL
        with pytest.raises(JsonSafetyError):
            list(capture.iter_bodies())
        with pytest.raises(JsonSafetyError):
            checkpoint_bodies(tmp_path, saved, record, SCOPE)


@pytest.mark.parametrize('state', ['changed', 'unavailable', 'incomplete'])
def test_l10c_final_drain_cannot_reuse_an_earlier_child_candidate(tmp_path, state):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        guard.state[{'changed': 'changed', 'unavailable': 'available', 'incomplete': 'complete'}[state]] = state == 'changed'
        if state == 'changed':
            with pytest.raises(JsonSafetyError):
                capture.drain()
        else:
            assert 'corporate_l10c_lifetime' not in capture.drain()


@pytest.mark.parametrize('mime', ['text/html', 'application/json'])
def test_l10c_last_browser_rpc_stays_inside_late_response_fence(tmp_path, mime):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)

        def late():
            guard.on_sample = None
            exchange(context, page, content_type=mime)

        guard.on_sample = late
        saved = capture.drain()
        assert not saved['complete'] and 'response-after-final-drain' in saved['reasons']


@pytest.mark.parametrize('sibling', ['_l7_requested', '_l8_requested'])
def test_l10c_cannot_seal_sequential_sibling_history_until_joint_owner_is_integrated(tmp_path, sibling):
    context, page, _ = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        setattr(capture, sibling, True)
        saved = capture.drain()
        assert 'corporate_l10c_lifetime' not in saved
        assert not saved['complete'] and 'unsupported-child-history-combination' in saved['reasons']


def test_l10c_stop_at_handle_acquisition_disposes_returned_handle(tmp_path):
    context, page, guard = fixture()
    stopped = False

    def cancel():
        if stopped:
            raise CaptureCancelled()

    class StopElement(Element):
        def element_handle(self):
            nonlocal stopped
            stopped = True
            return self

    node = StopElement()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        with pytest.raises(CaptureCancelled):
            capture.bind_l10c_structure(node, *[Element() for _ in range(4)], phase='start', check_cancel=cancel)
        assert node.disposed
    assert guard.disconnected and guard.disposed
