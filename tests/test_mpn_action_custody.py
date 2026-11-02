"""Original request identity for the bounded preparation actions only."""
import pytest

from coretax_mpn import MpnSafetyError, MpnUnsupported
from test_mpn_browser import Request, Response, SOURCE, observer


@pytest.mark.parametrize('old_last', [False, True])
def test_action_keeps_its_exact_reply_across_an_older_pending_response(tmp_path, old_last):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    old = Request(page)
    capture.on_request(old)
    token = capture.begin_action('list')
    held = capture._action
    current = Request(page)
    capture.on_request(current)
    assert held['request'] is current
    replies = [current, old] if old_last else [old, current]
    for request in replies:
        capture.on_response(Response(request))
    assert held['request'] is None
    expected_sequence = 1 if old_last else 2
    assert capture.wait(0, 'list', action=token)['sequence'] == expected_sequence
    assert capture.latest['list']['sequence'] == 2
    capture.end_action(token)
    assert held['snapshot'] is None and capture._action is None
    capture.close()


def test_action_wait_does_not_accept_only_an_old_reply(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    old = Request(page)
    capture.on_request(old)
    token = capture.begin_action('list')
    capture.on_response(Response(old))
    with pytest.raises(MpnUnsupported):
        capture.wait(0, 'list', timeout=0, action=token)
    capture.end_action(token)
    capture.close()


@pytest.mark.parametrize('finish', ['failure', 'response_failure', 'reset', 'close'])
def test_action_request_and_snapshot_are_released_on_terminal_paths(tmp_path, finish):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    token = capture.begin_action('list')
    held = capture._action
    request = Request(page)
    capture.on_request(request)
    if finish == 'failure':
        capture.on_request_failed(request)
    elif finish == 'response_failure':
        capture.on_response(Response(request, status=403))
    elif finish == 'reset':
        capture.begin_navigation(SOURCE)
    else:
        capture.close()
    assert held['request'] is None and held['snapshot'] is None
    assert capture._action is None
    capture.end_action(token)
    capture.close()


def test_old_action_cleanup_cannot_clear_a_new_action_or_bind_its_late_reply(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    old = capture.begin_action('list')
    request = Request(page)
    capture.on_request(request)
    capture.begin_navigation(SOURCE)
    capture.on_navigation(page.main_frame)
    new = capture.begin_action('list')
    capture.end_action(old)
    capture.on_response(Response(request))
    assert capture._action['token'] is new and capture._action['snapshot'] is None
    capture.end_action(new)
    capture.close()


@pytest.mark.parametrize('state', ['uncommitted', 'pending', 'closed', 'failed', 'overlap', 'detail'])
def test_unproved_action_cannot_arm(tmp_path, state):
    page, capture = observer(tmp_path)
    if state != 'uncommitted':
        capture.on_navigation(page.main_frame)
    if state == 'pending':
        capture._binding_document = True
    elif state == 'closed':
        capture.close()
    elif state == 'failed':
        capture.failed = True
    elif state == 'overlap':
        capture.begin_action('list')
    with pytest.raises(MpnSafetyError):
        capture.begin_action('detail' if state == 'detail' else 'list')
    capture.close()


@pytest.mark.parametrize('mutation', ['token', 'kind', 'attempt', 'callback'])
def test_action_wait_rejects_changed_custody_even_during_final_document_rpc(tmp_path, mutation, monkeypatch):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    token = capture.begin_action('list')
    request = Request(page)
    capture.on_request(request)
    capture.on_response(Response(request))
    if mutation == 'token':
        token = object()
    elif mutation == 'kind':
        capture._action['kind'] = 'detail'
    elif mutation == 'attempt':
        capture._action['attempt'] = object()
    else:
        original = capture._check_state
        calls = []
        def check(**kwargs):
            original(**kwargs)
            calls.append(1)
            if len(calls) == 2:
                capture.end_action(token)
        monkeypatch.setattr(capture, '_check_state', check)
    with pytest.raises(MpnSafetyError):
        capture.wait(0, 'list', action=token)
    assert capture.safety_failed
    capture.close()
