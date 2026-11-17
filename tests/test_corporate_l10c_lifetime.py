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


class ChildHistory(History):
    def __init__(self):
        super().__init__()
        self.clock = {'epoch_ms': 2000, 'timezone': 'Asia/Jakarta'}

    def evaluate(self, script, args=None):
        if 'corporate-l10c-final-clock' in script:
            return {'state': super().evaluate('(h) => h.sample()'), 'clock': deepcopy(self.clock)}
        return super().evaluate(script, args)


def fixture():
    context, page = setup()
    make_document = page.evaluate_handle
    guard = ChildHistory()
    evaluate = page.evaluate
    page.evaluate = lambda source: ({'epoch_ms': 1000, 'timezone': 'Asia/Jakarta'}
                                    if 'epoch_ms' in source else evaluate(source))

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
        assert saved['clock_interval']['end_ms'] == 2000
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


def test_c_cannot_append_a_sequential_final_probe_after_reviewed_joint_seam_is_integrated(tmp_path):
    context, page, _ = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        capture._final_lifetimes = lambda *args, **kwargs: None
        saved = capture.drain()
        assert not saved['complete'] and 'corporate_l10c_lifetime' not in saved
        assert 'unsupported-child-history-combination' in saved['reasons']


def test_unoffered_unavailable_c_history_does_not_disable_a_legacy_sibling(tmp_path):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        guard.state['available'] = False
        assert not capture.bind_l10c_structure(*[Element() for _ in range(5)], phase='start')
        capture._l7_requested = True
        saved = capture.drain()
        assert saved['complete'] and 'corporate_l10c_lifetime' not in saved


@pytest.mark.parametrize('clock', [None, {'epoch_ms': 500, 'timezone': 'Asia/Jakarta'},
    {'epoch_ms': 2000, 'timezone': 'UTC'}, {'epoch_ms': True, 'timezone': 'Asia/Jakarta'}])
def test_c_final_rpc_cannot_reuse_an_earlier_clock_when_its_own_clock_is_unavailable(tmp_path, clock):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        guard.clock = clock
        saved = capture.drain()
        assert 'clock_interval' not in saved


def test_c_final_rpc_rechecks_sticky_parent_route_change_without_another_browser_rpc(tmp_path):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert boundaries(capture)

        def detour():
            guard.on_sample = None
            navigate(page, DETAIL.replace('fixture-record', 'foreign-record'))
            navigate(page, DETAIL)

        guard.on_sample = detour
        with pytest.raises(JsonSafetyError):
            capture.drain()


def test_malformed_c_final_reply_cannot_seal_earlier_child_or_clock(tmp_path):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        evaluate = guard.evaluate
        guard.evaluate = lambda source, args=None: (None if 'corporate-l10c-final-clock' in source
                                                   else evaluate(source, args))
        saved = capture.drain()
        assert 'clock_interval' not in saved and 'corporate_l10c_lifetime' not in saved


def adapter_packets():
    from test_corporate_component_lifetime import corporate_packets
    packets, record, scope, observed, _ = corporate_packets()
    fact = proof()
    fact.update(attempt=packets[0]['context']['attempt'], record_id=record['record_id'],
                source_url=record['list_url'], detail_url=packets[0]['context']['frame_url'])
    for packet in packets:
        packet['context']['corporate_l10c_lifetime'] = deepcopy(fact)
    return packets, record, scope, observed, fact


def test_adapter_preserves_c_history_without_granting_c_semantics_to_another_form():
    packets, record, scope, observed, fact = adapter_packets()
    result = adapter.adapt_corporate_detail(packets, record, scope, observed)
    assert result['eligible'], result['reason']
    assert all(event.get('corporate_l10c_lifetime') == fact for event in result['provenance']['events'])
    assert not any(item['form'] == 'L10-C' for item in result['provenance']['projections'])


@pytest.mark.parametrize('defect', ['missing-component', 'null', 'cross-attempt', 'missing-on-reference'])
def test_adapter_c_history_is_checked_before_any_semantic_fallback(defect):
    packets, record, scope, observed, _ = adapter_packets()
    if defect == 'missing-component':
        del packets[0]['context']['component_lifetime']
    elif defect == 'null':
        packets[0]['context']['corporate_l10c_lifetime'] = None
    elif defect == 'cross-attempt':
        packets[0]['context']['corporate_l10c_lifetime']['attempt'] = 'b' * 32
    else:
        del packets[1]['context']['corporate_l10c_lifetime']
    with pytest.raises(JsonSafetyError):
        adapter.adapt_corporate_detail(packets, record, scope, observed)


@pytest.mark.parametrize('defect', ['malformed', 'unavailable', 'missing-history', 'missing-component', 'missing-element'])
def test_l10c_unavailable_structure_never_becomes_a_fact(tmp_path, defect):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        nodes = [Element() for _ in range(5)]
        if defect == 'malformed':
            guard.state = {'available': True}
        elif defect == 'unavailable':
            guard.state['available'] = False
        elif defect == 'missing-history':
            capture._l10c_history = None
        elif defect == 'missing-component':
            capture._component_started = False
        else:
            nodes[0].element_handle = lambda: None
        assert not capture.bind_l10c_structure(*nodes, phase='start')
        assert capture.observe_l10c_lifetime() is None
        if defect == 'missing-history':
            capture._l10c_history = guard  # Return test-disowned handle to its cleanup owner.


@pytest.mark.parametrize('error', [RuntimeError, JsonSafetyError])
def test_l10c_probe_preserves_safety_but_not_driver_exception_text(tmp_path, error):
    context, page, guard = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        original = guard.evaluate

        def fail(*args):
            raise error('SYNTHETIC PRIVATE DRIVER SENTINEL')

        guard.evaluate = fail
        if error is JsonSafetyError:
            with pytest.raises(JsonSafetyError):
                capture.observe_l10c_lifetime()
        else:
            assert capture.observe_l10c_lifetime() is None
        guard.evaluate = original
    assert all(b'SYNTHETIC PRIVATE DRIVER SENTINEL' not in path.read_bytes()
               for path in tmp_path.rglob('*.json'))


def test_l10c_rejects_unknown_boundary_without_sampling_browser(tmp_path):
    context, page, _ = fixture()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        with pytest.raises(ValueError):
            capture.bind_l10c_structure(*[Element() for _ in range(5)], phase='invented')


def test_l10c_stop_at_history_installation_keeps_cleanup_owner(tmp_path):
    context, page = setup()
    make_document = page.evaluate_handle
    guard = History()
    stopped = False

    def cancel():
        if stopped:
            raise CaptureCancelled()

    def document(script):
        handle = make_document(script)

        def install(source):
            nonlocal stopped
            if 'corporate-l10c-history' in source:
                stopped = True
                return guard
            return None

        handle.evaluate_handle = install
        return handle

    page.evaluate_handle = document
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=cancel) as capture:
        with pytest.raises(CaptureCancelled):
            begin(capture)
    assert guard.disconnected and guard.disposed


def test_l10c_stop_after_final_sample_cannot_seal_manifest(tmp_path):
    context, page, guard = fixture()
    stopped = False

    def cancel():
        if stopped:
            raise CaptureCancelled()

    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path, check_cancel=cancel) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)

        def stop():
            nonlocal stopped
            stopped = True

        guard.on_sample = stop
        with pytest.raises(CaptureCancelled):
            capture.drain()
    assert not list(tmp_path.rglob('manifest.json'))
    assert guard.disconnected and guard.disposed


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
