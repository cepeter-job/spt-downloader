"""Manifest-only L7 custody protocols. Source-only RED until hosted execution."""
from copy import deepcopy
import hashlib
import json

import pytest

import coretax_json as adapter
from coretax_json import JsonSafetyError
from coretax_browser import CaptureCancelled
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import exchange
from test_corporate_component_lifetime import setup, selected, begin, navigate, LIST, DETAIL, SCOPE
from test_corporate_l7_negative_native import lifetime


def proof(capture=None):
    return lifetime(capture.attempt if capture else 'a' * 32,
                    record_id='fixture-record', source_url=LIST, detail_url=DETAIL)


@pytest.mark.parametrize('key', tuple(proof()))
@pytest.mark.parametrize('mutation', ['missing', 'wrong-type'])
def test_l7_fact_schema_is_closed_and_bound(key, mutation):
    validate = getattr(adapter, '_capture_l7_lifetime', None)
    assert callable(validate), 'Strict L7 manifest validator absent (source-only RED)'
    options = dict(attempt='a' * 32, record_id='fixture-record', source_url=LIST, detail_url=DETAIL)
    value = proof()
    assert validate(value, **options) == value
    if mutation == 'missing': del value[key]
    else: value[key] = 1
    with pytest.raises(JsonSafetyError): validate(value, **options)


class History:
    def __init__(self):
        self.state = {'available': True, 'changed': False, 'complete': False}
        self.phases, self.on_sample = [], None
        self.disposed = self.disconnected = False
        self.reason = 'ok'

    def evaluate(self, script, args=None):
        if 'disconnect' in script:
            self.disconnected = True
            return None
        if 'why()' in script:
            return self.reason
        if args is not None:
            self.phases.append(args['phase'])
            self.state['complete'] = self.phases == ['start', 'end']
            return dict(self.state)
        if self.on_sample: self.on_sample()
        return dict(self.state)

    def dispose(self): self.disposed = True


class Element:
    def __init__(self): self.disposed = False
    def element_handle(self): return self
    def dispose(self): self.disposed = True


def history_setup():
    context, page = setup()
    make_document = page.evaluate_handle
    guard = History()
    def document(script):
        handle = make_document(script)
        # Distinct protocol: no accidental sharing with the L8 history.
        handle.evaluate_handle = lambda source: guard if 'corporate-l7-history' in source else None
        return handle
    page.evaluate_handle = document
    return context, page, guard


def boundaries(capture):
    args = [Element() for _ in range(5)]
    assert capture.bind_l7_structure(*args, phase='start')
    assert capture.bind_l7_structure(*args, phase='end')
    assert all(item.disposed for item in args)
    return capture.observe_l7_lifetime()


def test_l7_manifest_only_live_and_held_readers_equal_without_replay_browser(tmp_path):
    context, page, guard = history_setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        assert guard.phases == []
        navigate(page, DETAIL)
        response = exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture) == proof(capture)
        saved = capture.drain()
        assert saved['corporate_l7_lifetime'] == proof(capture)
        assert 'corporate_l7_lifetime' not in saved['responses'][0]
        packets = list(capture.iter_bodies())
        assert packets[0]['context']['corporate_l7_lifetime'] == proof(capture)
        assert response.reads == 1 and packets[0]['body'] == response.raw
        record['detail_url'] = DETAIL
        page.evaluate_handle = lambda _: pytest.fail('Held replay must not use browser')
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == packets
        assert capture.drain() == saved
    assert guard.disconnected and guard.disposed
    assert not any(page.listeners.values()) and not any(context.listeners.values())


@pytest.mark.parametrize('mime', ['text/html', 'application/json'])
def test_l7_final_sample_is_inside_late_response_fence(tmp_path, mime):
    context, page, guard = history_setup()
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


@pytest.mark.parametrize('state', ['unavailable', 'changed', 'incomplete'])
def test_final_l7_sample_cannot_reuse_earlier_candidate(tmp_path, state):
    context, page, guard = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        guard.state[{'unavailable': 'available', 'changed': 'changed', 'incomplete': 'complete'}[state]] = state == 'changed'
        if state == 'changed':
            with pytest.raises(JsonSafetyError): capture.drain()
        else:
            saved = capture.drain()
            assert saved['complete'] and 'corporate_l7_lifetime' not in saved
    assert guard.disconnected and guard.disposed


@pytest.mark.parametrize('defect', ['descriptor', 'null', 'component-missing', 'cross-attempt'])
def test_both_l7_readers_reject_manifest_or_descriptor_overrides(tmp_path, defect):
    context, page, _ = history_setup()
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
        if defect == 'descriptor': changed['responses'][0]['corporate_l7_lifetime'] = proof(capture)
        elif defect == 'null': changed['corporate_l7_lifetime'] = None
        elif defect == 'component-missing': del changed['component_lifetime']
        else: changed['corporate_l7_lifetime']['attempt'] = 'b' * 32
        raw = json.dumps(changed, sort_keys=True).encode()
        path.write_bytes(raw)
        saved = {**changed, 'manifest': saved['manifest'], 'manifest_sha256': hashlib.sha256(raw).hexdigest()}
        capture._manifest_hash = saved['manifest_sha256']
        capture._result = deepcopy(saved)
        record['detail_url'] = DETAIL
        with pytest.raises(JsonSafetyError): list(capture.iter_bodies())
        with pytest.raises(JsonSafetyError): checkpoint_bodies(tmp_path, saved, record, SCOPE)


@pytest.mark.parametrize('operation', ['bind', 'sample'])
def test_l7_rpc_cannot_demote_explicit_safety_refusal(tmp_path, operation):
    context, page, guard = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        if operation == 'sample': assert boundaries(capture)
        def fail(*args): raise JsonSafetyError('SYNTHETIC safety refusal')
        guard.evaluate = fail
        with pytest.raises(JsonSafetyError):
            if operation == 'bind': capture.bind_l7_structure(*[Element() for _ in range(5)], phase='start')
            else: capture.observe_l7_lifetime()


def test_l7_rpc_stop_outranks_simultaneous_explicit_safety_failure(tmp_path):
    context, page, guard = history_setup()
    stopped = False
    def cancel():
        if stopped: raise CaptureCancelled()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        def fail(*args):
            nonlocal stopped
            stopped = True
            raise JsonSafetyError('SYNTHETIC concurrent safety failure')
        guard.evaluate = fail
        with pytest.raises(CaptureCancelled): capture.observe_l7_lifetime(check_cancel=cancel)


def test_stop_after_l7_element_acquisition_disposes_that_handle(tmp_path):
    context, page, guard = history_setup()
    stopped = False
    def cancel():
        if stopped: raise CaptureCancelled()
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
            capture.bind_l7_structure(node, *[Element() for _ in range(4)], phase='start', check_cancel=cancel)
        assert node.disposed, 'Source-only RED: Stop must not orphan the just-returned handle'
    assert guard.disconnected and guard.disposed


def test_stop_after_l7_history_installation_still_cleans_owned_history(tmp_path):
    context, page = setup()
    make_document = page.evaluate_handle
    guard = History()
    stopped = False
    def cancel():
        if stopped: raise CaptureCancelled()
    def document(script):
        handle = make_document(script)
        def install(source):
            nonlocal stopped
            if 'corporate-l7-history' in source:
                stopped = True
                return guard
            return None
        handle.evaluate_handle = install
        return handle
    page.evaluate_handle = document
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=cancel) as capture:
        with pytest.raises(CaptureCancelled): begin(capture)
    assert guard.disconnected and guard.disposed
    assert all(document.disposed for document in page.documents)


@pytest.mark.parametrize('bad', [None, {}, {'available': 1, 'changed': False, 'complete': True},
    {'available': True, 'changed': False, 'complete': True, 'unexpected': True}])
def test_unreadable_history_never_creates_partial_proof_and_does_not_rearm(tmp_path, bad):
    context, page, guard = history_setup()
    original = guard.evaluate
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        guard.evaluate = lambda *_: deepcopy(bad)
        assert capture.observe_l7_lifetime() is None
        guard.evaluate = original
        saved = capture.drain()
        assert saved['complete'] and 'corporate_l7_lifetime' not in saved


def test_known_child_contradiction_outranks_optional_unavailability(tmp_path):
    context, page, guard = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        guard.state.update(available=False, changed=True)
        with pytest.raises(JsonSafetyError): capture.drain()
