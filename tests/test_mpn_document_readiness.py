"""Synthetic retained Document and asynchronous Accounting preparation cases."""
import pytest

from coretax_mpn import MpnSafetyError
from test_mpn_browser import observer, Request, Response, SOURCE


def test_same_document_router_notification_keeps_owned_inventory(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    capture.on_navigation(page.main_frame)
    fresh = Request(page)
    capture.on_request(fresh)
    capture.on_response(Response(fresh))
    assert capture.wait(0, 'list')['total'] == 0
    capture.close()
    assert page.handles and all(handle.disposed for handle in page.handles)


def test_same_url_document_request_is_refused_before_commit(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    request = Request(page)
    request.resource_type = 'document'
    request.method = 'GET'
    request.url = SOURCE
    capture.on_request(request)
    with pytest.raises(MpnSafetyError):
        capture._check_state()
    capture.close()


def test_route_away_and_back_cannot_clear_refusal(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    page.url = page.main_frame.url = SOURCE + '?foreign=1'
    capture.on_navigation(page.main_frame)
    page.url = page.main_frame.url = SOURCE
    capture.on_navigation(page.main_frame)
    with pytest.raises(MpnSafetyError):
        capture._check_state()
    capture.close()


def test_document_replacement_without_notification_is_refused(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    page.document = object()
    with pytest.raises(MpnSafetyError):
        capture._check_state()
    capture.close()


@pytest.mark.parametrize('invalidate', ['close', 'reset'])
def test_late_identity_handle_cannot_replace_new_attempt(tmp_path, invalidate):
    page, capture = observer(tmp_path)
    original = page.evaluate_handle
    late = []
    def acquire(script):
        handle = original(script)
        late.append(handle)
        if invalidate == 'close':
            capture.close()
        else:
            capture.begin_navigation(SOURCE)
            page.evaluate_handle = original
            capture.on_navigation(page.main_frame)
        return handle
    page.evaluate_handle = acquire
    capture.on_navigation(page.main_frame)
    assert late and late[0].disposed
    if invalidate == 'reset':
        fresh = Request(page)
        capture.on_request(fresh)
        capture.on_response(Response(fresh))
        assert capture.wait(0, 'list')['total'] == 0
    capture.close()


def test_rejected_observer_prevents_ui_preparation(tmp_path):
    from coretax_mpn_ui import AccountingUI
    from test_mpn import scope_run
    page, capture = observer(tmp_path)
    ui = AccountingUI(page, scope_run(), tmp_path)
    ui.__enter__()
    ui.observer.begin_navigation(ui.url)
    ui.observer.on_navigation(page.main_frame)
    ui.observer._reject(safety=True)
    with pytest.raises(MpnSafetyError):
        ui._dropdown('acc-balance-sheet-light form ui-dropdown#ShowZeroValue', 'Yes')
    ui.__exit__()
    capture.close()


def test_owned_http_failure_during_document_rpc_stays_recoverable(tmp_path):
    from coretax_mpn import MpnUnsupported
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    bad = Request(page)
    capture.on_request(bad)
    handle = page.handles[-1]
    original = handle.evaluate
    def evaluate(script):
        capture.on_response(Response(bad, status=403, html=True))
        return original(script)
    handle.evaluate = evaluate
    with pytest.raises(MpnUnsupported):
        capture._check_state()
    assert capture.failed and not capture.safety_failed
    capture.close()
