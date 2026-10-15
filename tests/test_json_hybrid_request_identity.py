"""Known request identities must fail closed before schema eligibility.

Synthetic protocol events only; run on the GitHub Windows runner. Missing
bindings deliberately model an unknown build, not permission to trust a body.
"""
from copy import deepcopy

import pytest

import coretax_browser as driver
import coretax_json as native
import test_json_adapter as corpus
import test_json_capture as network
from test_json_hybrid import DOM_SECTIONS, PRIMARY_REQUEST, Scenario, collector


# Independent literals from the inspected read-only contracts, not a production
# catalog import that could make an incorrect catalog validate its own tests.
GRID_REQUESTS = [
    ('loadcit/l4-table-a-grid', {'ReturnSheetRecordId': corpus.RECORD_ID,
                              'PeriodYear': '2025', 'First': 0, 'Rows': 10}),
    ('loadcit/l9-table-1-grid', {'ReturnSheetRecordId': corpus.RECORD_ID,
                              'GroupType': 'Group 1', 'First': 0, 'Rows': 10}),
    ('loadcit/l9-table-2-grid', {'ReturnSheetRecordId': corpus.RECORD_ID,
                              'GroupType': 'Permanent', 'First': 0, 'Rows': 10}),
    ('loadcit/l9-table-3-grid', {'ReturnSheetRecordId': corpus.RECORD_ID,
                              'GroupType': 'Group 1', 'First': 0, 'Rows': 10}),
    ('loadcit/l10a-grid', {'ReturnSheetRecordId': corpus.RECORD_ID,
                         'First': 0, 'Rows': 10}),
]
PRIMARY_PATH = 'prefillreturnsheet/corporate-income'
KNOWN_REQUESTS = [(PRIMARY_PATH, PRIMARY_REQUEST), *GRID_REQUESTS]
GRID_BODY = corpus.wire({'IsSuccessful': True,
                         'Payload': {'TotalRecords': 0, 'Data': [], 'Index': None}}).encode()


def scenario(tmp_path, monkeypatch, path, request, suffix='', content_type='application/json'):
    collector()
    case = Scenario(tmp_path, monkeypatch)
    case.forms = None
    raw = corpus.primary()['body'] if path == PRIMARY_PATH else GRID_BODY
    if content_type == 'text/html':
        raw = b'<html>SYNTHETIC unsupported response</html>'
    case.page.exchanges[0].update(url=corpus.ORIGIN + '/returnsheet/api/' + path + suffix,
                                  post=deepcopy(request), raw=raw, content_type=content_type)
    return case


def assert_rejected(case, *, before_body=False):
    with pytest.raises(native.JsonSafetyError):
        case.collect()
    assert case.dom_calls == [] and case.pdf_calls == []
    assert not case.run['complete'] and not case.record.get('capture_complete')
    assert case.record.get('sections', []) == []
    if before_body:
        assert case.observation_calls == []
        assert all(response.reads == 0 for response in case.page.body_responses)
    case.assert_closed()


@pytest.mark.parametrize('path,request', GRID_REQUESTS)
@pytest.mark.parametrize('suffix', ['', '?source=synthetic'])
@pytest.mark.parametrize('content_type', ['application/json', 'text/html'])
def test_unknown_binding_rejects_foreign_request_on_every_known_grid(
        tmp_path, monkeypatch, path, request, suffix, content_type):
    request = {**request, 'ReturnSheetRecordId': 'synthetic-different-return'}
    case = scenario(tmp_path, monkeypatch, path, request, suffix, content_type)
    assert_rejected(case, before_body=True)


@pytest.mark.parametrize('suffix', ['', '?source=synthetic'])
@pytest.mark.parametrize('content_type', ['application/json', 'text/html'])
def test_matching_primary_body_does_not_hide_foreign_primary_request(
        tmp_path, monkeypatch, suffix, content_type):
    request = {**PRIMARY_REQUEST, 'RecordId': 'synthetic-different-return'}
    case = scenario(tmp_path, monkeypatch, PRIMARY_PATH, request, suffix, content_type)
    assert_rejected(case, before_body=True)


@pytest.mark.parametrize('year', ['2024', 2024])
@pytest.mark.parametrize('suffix', ['', '?source=synthetic'])
def test_known_l4_request_rejects_a_different_supplied_year(
        tmp_path, monkeypatch, year, suffix):
    path, request = GRID_REQUESTS[0]
    case = scenario(tmp_path, monkeypatch, path, {**request, 'PeriodYear': year}, suffix)
    assert_rejected(case, before_body=True)


@pytest.mark.parametrize('content_type', ['application/json', 'text/html'])
def test_foreign_grid_request_arriving_during_drain_cannot_disappear(
        tmp_path, monkeypatch, content_type):
    case = scenario(tmp_path, monkeypatch, PRIMARY_PATH, PRIMARY_REQUEST)
    observe = driver.observe_corporate_forms
    path, request = GRID_REQUESTS[1]

    def emit_late():
        response = network.exchange(
            case.page.context, case.page.popup,
            url=corpus.ORIGIN + '/returnsheet/api/' + path,
            post={**request, 'ReturnSheetRecordId': 'synthetic-different-return'},
            raw=GRID_BODY if content_type == 'application/json' else b'<html>SYNTHETIC</html>',
            content_type=content_type)
        case.page.body_responses.append(response)

    def install_late_request(*args, **kwargs):
        case.page.body_responses[0].on_read = emit_late
        return observe(*args, **kwargs)

    monkeypatch.setattr(driver, 'observe_corporate_forms', install_late_request)
    assert_rejected(case)
    assert len(case.page.body_responses) == 2


@pytest.mark.parametrize('path,request', KNOWN_REQUESTS)
@pytest.mark.parametrize('suffix', ['', '?source=synthetic'])
def test_matching_known_request_without_bindings_still_uses_whole_dom(
        tmp_path, monkeypatch, path, request, suffix):
    case = scenario(tmp_path, monkeypatch, path, request, suffix)
    result = case.collect()
    assert result['complete'] is True and result['errors'] == []
    assert case.record['sections'] == DOM_SECTIONS
    assert case.record['detail_source']['used'] == 'dom'
    assert len(case.dom_calls) == len(case.pdf_calls) == 1
    case.assert_closed()


@pytest.mark.parametrize('path,request', KNOWN_REQUESTS)
def test_missing_request_identity_is_unsupported_not_an_invented_conflict(
        tmp_path, monkeypatch, path, request):
    case = scenario(tmp_path, monkeypatch, path, {})
    result = case.collect()
    assert result['complete'] is True and result['errors'] == []
    assert case.record['sections'] == DOM_SECTIONS
    assert case.record['detail_source']['used'] == 'dom'
    assert len(case.dom_calls) == len(case.pdf_calls) == 1
    case.assert_closed()
