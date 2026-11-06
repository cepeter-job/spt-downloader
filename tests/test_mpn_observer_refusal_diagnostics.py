"""Issue #156: fixed-category MPN observer refusal diagnostics.

All request/response data is synthetic; tests exercise the real observer
callbacks and diagnostic store, without a Coretax connection.
"""
import json

import pytest

from coretax_mpn import MpnSafetyError, MpnUnsupported
from spt_desktop import diagnostics
from test_diagnostics import records
from test_mpn_browser import Request, Response, observer

PRIVATE = 'SYNTHETIC_PRIVATE_RESPONSE_MUST_NOT_BE_LOGGED'


@pytest.mark.parametrize(
    ('failure', 'expected'),
    [
        ('request_shape', 'request_shape'),
        ('transport', 'request_transport'),
        ('status', 'response_status'),
        ('content_type', 'response_content_type'),
        ('body', 'response_body'),
        ('envelope', 'response_shape'),
        ('count', 'response_row_count_mismatch'),
        ('identity', 'response_identity'),
    ],
)
def test_first_owned_grid_failure_has_one_safe_reason(tmp_path, failure, expected):
    page, capture = observer(tmp_path)
    root = tmp_path / 'diagnostics'
    try:
        capture.on_navigation(page.main_frame)
        with diagnostics.session(root, 'worker') as log:
            request = Request(page)
            if failure == 'request_shape':
                request.method = 'GET'
            capture.on_request(request)
            if failure == 'transport':
                capture.on_request_failed(request)
            elif failure != 'request_shape':
                response = Response(request)
                if failure == 'status':
                    response.status = 503
                elif failure == 'content_type':
                    response.headers['content-type'] = 'text/html'
                elif failure == 'body':
                    def unreadable():
                        raise OSError(PRIVATE)
                    response.body = unreadable
                elif failure == 'envelope':
                    response = Response(request, successful=False)
                elif failure == 'count':
                    response._body = json.dumps({
                        'IsSuccessful': True, 'Payload': {'TotalRecords': 2, 'Data': []},
                    }).encode()
                elif failure == 'identity':
                    response._body = json.dumps({
                        'IsSuccessful': True,
                        'Payload': {'TotalRecords': 1, 'Data': [
                            {'RecordId': PRIVATE, 'TaxpayerAggregateIdentifier': PRIVATE},
                        ]},
                    }).encode()
                capture.on_response(response)
            with pytest.raises(MpnUnsupported, match='owned grid capture failed'):
                capture.wait(0, 'list')
            # A later good response must neither revive the attempt nor
            # overwrite the original refusal category.
            capture.on_response(Response(request))
            assert log.flush()
        events = [entry for entry in records(root) if entry['event'] == 'mpn.observer_refused']
        assert len(events) == 1
        assert events[0]['mpn_observer_reason'] == expected
        assert events[0]['mpn_paginator_kind'] == 'list'
        assert capture.failure_reason == expected
        assert PRIVATE not in json.dumps(records(root))
        assert 'url' not in json.dumps(events).lower()
    finally:
        capture.close()


@pytest.mark.parametrize('pending', [False, True])
def test_grid_wait_timeout_distinguishes_pending_from_no_pending(tmp_path, pending):
    page, capture = observer(tmp_path)
    root = tmp_path / 'diagnostics'
    try:
        capture.on_navigation(page.main_frame)
        if pending:
            capture.on_request(Request(page))
        with diagnostics.session(root, 'worker') as log:
            with pytest.raises(MpnUnsupported, match='fresh grid response timed out'):
                capture.wait(0, 'list', timeout=0)
            assert log.flush()
        events = [entry for entry in records(root) if entry['event'] == 'mpn.grid_wait_timeout']
        assert len(events) == 1
        assert events[0]['mpn_paginator_kind'] == 'list'
        assert events[0]['mpn_grid_wait_state'] == ('pending_response' if pending else 'no_pending_response')
        assert not capture.failed
    finally:
        capture.close()


def test_unsafe_identity_remains_fatal_without_observer_refusal_event(tmp_path):
    page, capture = observer(tmp_path)
    root = tmp_path / 'diagnostics'
    try:
        capture.on_navigation(page.main_frame)
        request = Request(page, taxpayer='00000000-0000-4000-8000-000000000099')
        with diagnostics.session(root, 'worker') as log:
            capture.on_request(request)
            with pytest.raises(MpnSafetyError):
                capture.wait(0, 'list')
            assert log.flush()
        assert [e for e in records(root) if e['event'] == 'mpn.observer_refused'] == []
        assert capture.safety_failed
    finally:
        capture.close()


def test_late_owned_grid_response_is_not_misreported_as_no_request(tmp_path):
    page, capture = observer(tmp_path)
    root = tmp_path / 'diagnostics'
    try:
        capture.on_navigation(page.main_frame)
        token = capture.begin_action('list')
        request = Request(page)
        capture.on_request(request)
        capture.on_response(Response(request))
        with diagnostics.session(root, 'worker') as log:
            with pytest.raises(MpnUnsupported, match='fresh grid response timed out'):
                capture.wait(0, 'list', timeout=0, action=token)
            assert log.flush()
        events = [entry for entry in records(root) if entry['event'] == 'mpn.grid_wait_timeout']
        assert len(events) == 1
        assert events[0]['mpn_grid_wait_state'] == 'no_pending_response'
        assert capture.sequence == 1
        assert not capture.failed
    finally:
        capture.close()
