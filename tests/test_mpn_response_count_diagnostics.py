"""Issue #156: private-free subcategories of MPN original grid count refusals.

Exercise real owned list/detail request/response callbacks with invented
identities. No Coretax network traffic or original taxpayer records.
"""

import json

import pytest

from coretax_mpn import MpnUnsupported
from spt_desktop import diagnostics
from test_diagnostics import records
from test_mpn_browser import PARENT, TAXPAYER, Request, Response, observer

PRIVATE = 'SYNTHETIC_PRIVATE_COUNT_PAYLOAD_NEVER_LOG'


@pytest.mark.parametrize('kind', ['list', 'detail'])
@pytest.mark.parametrize(
    ('case', 'reason'),
    [
        ('missing_total', 'response_total_invalid'),
        ('string_total', 'response_total_invalid'),
        ('negative_total', 'response_total_invalid'),
        ('decimal_total', 'response_total_invalid'),
        ('oversized_total', 'response_total_invalid'),
        ('offset_past_total', 'response_offset_exceeds_total'),
        ('missing_page_row', 'response_row_count_mismatch'),
        ('extra_page_row', 'response_row_count_mismatch'),
        ('malformed_row', 'response_row_shape_invalid'),
    ],
)
def test_count_refusals_emit_exact_first_safe_predicate(tmp_path, kind, case, reason):
    page, capture = observer(tmp_path)
    root = tmp_path / 'diagnostics'
    try:
        capture.on_navigation(page.main_frame)
        if kind == 'detail':
            capture.begin_detail(PARENT)
        request = Request(page, kind=kind)
        if case == 'offset_past_total':
            request.post_data_json['First'] = 10
            request.post_data = json.dumps(request.post_data_json)
        response = Response(request)
        payload = {'TotalRecords': 1, 'Data': [PRIVATE]}
        if case == 'missing_total':
            del payload['TotalRecords']
        elif case == 'string_total':
            payload['TotalRecords'] = PRIVATE
        elif case == 'negative_total':
            payload['TotalRecords'] = -1
        elif case == 'decimal_total':
            payload['TotalRecords'] = 2.5
        elif case == 'oversized_total':
            payload['TotalRecords'] = 1000000000
        elif case == 'offset_past_total':
            payload.update(TotalRecords=9, Data=[])
        elif case == 'missing_page_row':
            payload.update(TotalRecords=2, Data=[{}])
        elif case == 'extra_page_row':
            payload.update(TotalRecords=1, Data=[{}, {}])
        elif case == 'malformed_row':
            payload.update(TotalRecords=1, Data=[PRIVATE])
        response._body = json.dumps({'IsSuccessful': True, 'Payload': payload}).encode()

        with diagnostics.session(root, 'worker') as log:
            capture.on_request(request)
            capture.on_response(response)
            with pytest.raises(MpnUnsupported, match='MPN owned grid capture failed'):
                capture.wait(0, kind)
            # Neither subsequent valid traffic nor another event may replace
            # the original refusal or reclassify an incomplete grid COMPLETE.
            capture.on_response(Response(request))
            assert log.flush()

        emitted = records(root)
        refused = [item for item in emitted if item['event'] == 'mpn.observer_refused']
        assert len(refused) == 1
        assert refused[0]['mpn_observer_reason'] == reason
        assert refused[0]['mpn_paginator_kind'] == kind
        assert capture.failure_reason == reason
        assert capture.failed and not capture.safety_failed
        assert capture.sequence == 0
        assert not capture.latest
        public_text = json.dumps(emitted)
        assert PRIVATE not in public_text
        assert 'url' not in json.dumps(refused).lower()
        assert 'TotalRecords' not in public_text
    finally:
        capture.close()


@pytest.mark.parametrize('kind', ['list', 'detail'])
def test_valid_exact_count_still_certifies_owned_grid(tmp_path, kind):
    page, capture = observer(tmp_path)
    root = tmp_path / 'diagnostics'
    try:
        capture.on_navigation(page.main_frame)
        if kind == 'detail':
            capture.begin_detail(PARENT)
        request = Request(page, kind=kind)
        response = Response(request)
        row = {'RecordId': PARENT}
        if kind == 'list':
            row['TaxpayerAggregateIdentifier'] = TAXPAYER
        else:
            row['HeaderRecordId'] = PARENT
        response._body = json.dumps({
            'IsSuccessful': True, 'Payload': {'TotalRecords': 1, 'Data': [row]},
        }).encode()
        with diagnostics.session(root, 'worker') as log:
            capture.on_request(request)
            capture.on_response(response)
            snapshot = capture.wait(0, kind)
            assert log.flush()
        assert snapshot['total'] == 1
        assert len(snapshot['rows']) == 1
        assert not capture.failed and not capture.safety_failed
        assert capture.failure_reason is None
        assert not [x for x in records(root) if x['event'] == 'mpn.observer_refused']
    finally:
        capture.close()
