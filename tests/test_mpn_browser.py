"""Owned request protocol cases use only synthetic identities and responses."""
import importlib
import json
from types import SimpleNamespace

import pytest


TAXPAYER = '00000000-0000-4000-8000-000000000001'
PARENT = '00000000-0000-4000-8000-000000000002'
ORIGIN = 'https://coretax.intranet.pajak.go.id'
SOURCE = ORIGIN + '/accounting/id-ID/balancesheet/' + TAXPAYER
LIST = ORIGIN + '/accounting/api/taxpayeraccounting/list'
DETAIL = ORIGIN + '/accounting/api/taxpayeraccounting/listdetail'


class Page:
    def __init__(self):
        self.url = SOURCE
        self.main_frame = SimpleNamespace(url=SOURCE, parent_frame=None)
        self.handlers = {}

    def on(self, event, callback):
        self.handlers.setdefault(event, []).append(callback)

    def remove_listener(self, event, callback):
        self.handlers[event].remove(callback)

    def wait_for_timeout(self, timeout):
        raise AssertionError('This protocol case must fail or resolve before polling')


class Request:
    def __init__(self, page, *, taxpayer=TAXPAYER, kind='list', parent=PARENT):
        self.frame = page.main_frame
        self.method = 'POST'
        self.resource_type = 'xhr'
        self.url = LIST if kind == 'list' else DETAIL
        body = {'First': 0, 'Rows': 10, 'SortField': 'PostingDate' if kind == 'list' else 'TransactionDate',
                'SortOrder': -1, 'LanguageId': 'en-US', 'Filters':
                    [{'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals'}] if kind == 'list' else []}
        body['TaxpayerAggregateIdentifier' if kind == 'list' else 'RecordId'] = taxpayer if kind == 'list' else parent
        self.post_data_json = body
        self.post_data = json.dumps(body)


class Response:
    def __init__(self, request, *, status=200, successful=True, html=False):
        self.request, self.url, self.status = request, request.url, status
        self.headers = {'content-type': 'text/html' if html else 'application/json'}
        self._body = (b'<html>Synthetic failure</html>' if html else json.dumps({
            'IsSuccessful': successful, 'Payload': {'TotalRecords': 0, 'Data': [], 'Index': None}}).encode())

    def body(self):
        return self._body


def observer(tmp_path):
    module = importlib.import_module('coretax_mpn_browser')
    page = Page()
    capture = module.AccountingObserver(page, TAXPAYER, tmp_path)
    capture.begin_navigation(SOURCE)
    return page, capture


def test_precommit_request_and_its_late_response_cannot_satisfy_current_inventory(tmp_path):
    page, capture = observer(tmp_path)
    old = Request(page)
    capture.on_request(old)
    capture.on_navigation(page.main_frame)
    capture.on_response(Response(old))
    assert capture.sequence == 0
    fresh = Request(page)
    capture.on_request(fresh)
    capture.on_response(Response(fresh))
    assert capture.wait(0, 'list')['total'] == 0
    capture.close()


def test_old_request_object_does_not_cross_a_navigation_reset(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    old = Request(page)
    capture.on_request(old)
    capture.begin_navigation(SOURCE)
    capture.on_navigation(page.main_frame)
    capture.on_response(Response(old))
    assert capture.sequence == 0
    capture.close()


def test_foreign_taxpayer_is_fatal_before_wait_or_fallback(tmp_path):
    from coretax_mpn import MpnSafetyError
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    capture.on_request(Request(page, taxpayer='00000000-0000-4000-8000-000000000099'))
    with pytest.raises(MpnSafetyError):
        capture.wait(0, 'list')
    capture.close()


@pytest.mark.parametrize('status,successful,html', [(403, True, True), (200, False, False)])
def test_owned_failed_response_is_terminal_even_after_successful_traffic(tmp_path, status, successful, html):
    from coretax_mpn import MpnUnsupported
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    bad = Request(page)
    capture.on_request(bad)
    capture.on_response(Response(bad, status=status, successful=successful, html=html))
    good = Request(page)
    capture.on_request(good)
    capture.on_response(Response(good))
    with pytest.raises(MpnUnsupported):
        capture.wait(0, 'list')
    capture.close()


def test_detail_request_must_bind_the_inspected_parent(tmp_path):
    from coretax_mpn import MpnSafetyError
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    capture.begin_detail(PARENT)
    capture.on_request(Request(page, kind='detail', parent='00000000-0000-4000-8000-000000000099'))
    with pytest.raises(MpnSafetyError):
        capture.wait(0, 'detail')
    capture.close()


def test_second_main_frame_transition_invalidates_owned_capture(tmp_path):
    from coretax_mpn import MpnSafetyError
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    capture.on_navigation(page.main_frame)
    with pytest.raises(MpnSafetyError):
        capture.wait(0, 'list')
    capture.close()


def test_close_releases_request_references_and_registered_handlers(tmp_path):
    page, capture = observer(tmp_path)
    capture.on_navigation(page.main_frame)
    capture.on_request(Request(page))
    capture.close()
    assert not capture.pending
    assert all(not handlers for handlers in page.handlers.values())


def paginator_fixture(tmp_path):
    from coretax_mpn_ui import AccountingUI
    from test_mpn_capture_protocol import snapshot
    from test_mpn import payment_source
    header, _ = payment_source()
    first = snapshot([header] * 10, total=11)
    second = snapshot([header], first=10, total=11)
    second['sequence'] = 2
    capture = SimpleNamespace(sequence=1, latest={'list': first}, _check_state=lambda: None)
    capture.wait = lambda marker, kind: capture.latest[kind]
    clicked = []
    class Button:
        def count(self):
            current = capture.latest['list']
            return int(current['first'] + len(current['rows']) < current['total'])
        def is_visible(self):
            return True
        def click(self, **kwargs):
            clicked.append('next')
            capture.latest['list'] = second
            capture.sequence = 2
    owner = SimpleNamespace(locator=lambda selector: Button())
    ui = AccountingUI.__new__(AccountingUI)
    ui.page = object()
    ui.check_cancel = None
    ui.source_failed = ui.source_safety = False
    ui.observer = capture
    return ui, owner, first, second, clicked


def test_owned_paginator_visits_all_pages_and_keeps_one_query(tmp_path):
    ui, owner, first, second, clicked = paginator_fixture(tmp_path)
    pages = list(ui._pages('list', owner, first, 2))
    assert [page['first'] for page in pages] == [0, 10]
    assert clicked == ['next']


def test_page_cap_is_checked_before_another_ui_navigation(tmp_path):
    from coretax_mpn import MpnUnsupported
    ui, owner, first, second, clicked = paginator_fixture(tmp_path)
    pages = ui._pages('list', owner, first, 1)
    assert next(pages) is first
    with pytest.raises(MpnUnsupported):
        next(pages)
    assert clicked == []


def test_changed_paginator_query_is_fatal_before_accepting_its_page(tmp_path):
    from coretax_mpn import MpnSafetyError
    ui, owner, first, second, clicked = paginator_fixture(tmp_path)
    second['request']['SortField'] = 'SYNTHETIC CHANGED SORT'
    pages = ui._pages('list', owner, first, 2)
    assert next(pages) is first
    with pytest.raises(MpnSafetyError):
        next(pages)
