"""D-specific continuous structural custody, not native admission by a hint."""
from copy import deepcopy

import pytest

import coretax_corporate_l10d as owner
from coretax_browser import CaptureCancelled
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture
from test_corporate_component_lifetime import setup, selected, begin, navigate, DETAIL, SCOPE


class History:
    def __init__(self):
        self.state = {'available': True, 'changed': False, 'complete': False}
        self.phases = []
        self.disposed = self.disconnected = False
        self.on_read = None

    def evaluate(self, script, args=None):
        if 'disconnect' in script:
            self.disconnected = True
            return None
        if self.on_read:
            self.on_read()
        if args is not None:
            self.phases.append(args['phase'])
            self.state['complete'] = self.phases == ['start', 'end']
        return dict(self.state)

    def dispose(self): self.disposed = True


class Element:
    def __init__(self): self.disposed = False
    def element_handle(self): return self
    def dispose(self): self.disposed = True


def history_setup():
    context, page = setup()
    make_document = page.evaluate_handle
    history = History()
    def document(script):
        handle = make_document(script)
        handle.evaluate_handle = lambda source: history if 'corporate-l10d-history' in source else None
        return handle
    page.evaluate_handle = document
    return context, page, history


def boundaries(capture):
    nodes = [Element() for _ in range(3)]
    assert capture.bind_l10d_structure(*nodes, phase='start')
    assert capture.bind_l10d_structure(*nodes, phase='end')
    assert all(node.disposed for node in nodes)


def test_capture_arms_before_view_and_owns_real_d_boundaries_without_sealing_candidate(tmp_path):
    context, page, history = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        assert capture._l10d_history.handle is history and history.phases == []
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        boundaries(capture)
        assert capture._l10d_history.accept_sample(history.state) == history.state
        # The existing drain is not a joint D/sibling snapshot. It MUST NOT
        # seal an independent D capability from the earlier boundary sample.
        manifest = capture.drain()
        assert 'corporate_l10d_lifetime' not in manifest
    assert history.disposed and history.disconnected


@pytest.mark.parametrize('defect', ['changed', 'unavailable', 'incomplete', 'malformed'])
def test_d_state_is_sticky_and_known_change_outranks_unavailability(defect):
    custody = owner.L10DHistory()
    state = {'available': True, 'changed': False, 'complete': True}
    assert custody.accept_sample(state) == state
    bad = deepcopy(state)
    if defect == 'malformed': bad['complete'] = 1
    else: bad[{'changed': 'changed', 'unavailable': 'available', 'incomplete': 'complete'}[defect]] = defect == 'changed'
    if defect == 'changed':
        with pytest.raises(JsonSafetyError): custody.accept_sample(bad)
    else:
        assert custody.accept_sample(bad) is None
        assert custody.accept_sample(state) is None
    with pytest.raises(JsonSafetyError): custody.accept_sample({**state, 'available': False, 'changed': True})


@pytest.mark.parametrize('phase', ['arm', 'element', 'bind'])
def test_stop_with_d_rpc_reply_releases_just_acquired_handles(tmp_path, phase):
    context, page, history = history_setup()
    stopped = False
    def cancel():
        if stopped: raise CaptureCancelled()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=cancel) as capture:
        if phase == 'arm':
            make_document = page.evaluate_handle
            def document(script):
                result = make_document(script)
                install = result.evaluate_handle
                def arm(source):
                    nonlocal stopped
                    value = install(source)
                    if 'corporate-l10d-history' in source: stopped = True
                    return value
                result.evaluate_handle = arm
                return result
            page.evaluate_handle = document
            with pytest.raises(CaptureCancelled): begin(capture)
        else:
            begin(capture)
            navigate(page, DETAIL)
            capture.bind_detail_page(page)
            class StopElement(Element):
                def element_handle(self):
                    nonlocal stopped
                    stopped = phase == 'element'
                    return self
            node = StopElement()
            if phase == 'bind':
                def stop():
                    nonlocal stopped
                    stopped = True
                history.on_read = stop
            with pytest.raises(CaptureCancelled):
                capture.bind_l10d_structure(node, Element(), Element(), phase='start')
            assert node.disposed
    assert history.disposed and history.disconnected


@pytest.mark.parametrize('exception', [RuntimeError, JsonSafetyError])
def test_history_rpc_exception_does_not_mask_stop(exception):
    custody = owner.L10DHistory()
    stopped = False
    def cancel():
        if stopped: raise CaptureCancelled()
    def fail():
        nonlocal stopped
        stopped = True
        raise exception('SYNTHETIC never disclose this')
    with pytest.raises(CaptureCancelled): custody.probe(fail, cancel)


def test_unavailable_or_invalid_boundaries_do_not_rearm_capture(tmp_path):
    context, page = setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert not capture.bind_l10d_structure(Element(), Element(), Element(), phase='start')
        with pytest.raises(ValueError):
            capture.bind_l10d_structure(Element(), Element(), Element(), phase='unknown')
