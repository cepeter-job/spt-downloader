"""Full collector binds PPh21 listing bytes before View, then replays custody."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import pytest

import coretax_browser as driver
import coretax_pph21_observer as observer
import support_browser_protocol as protocol
from support_json_hybrid import Scenario
from support_json_network import Request
from pph21_projection_fixture import case as native_case
from masa_json_fixtures import SCOPE, TAXPAYER


@pytest.mark.parametrize('occupied', [False, True], ids=['new-directory', 'reject-existing-file'])
@pytest.mark.parametrize('literal_period', [False, True], ids=['caption', 'literal-code'])
def test_collect_attaches_original_listing_identity_and_replays_native_checkpoint(tmp_path, monkeypatch, occupied, literal_period):
    case = Scenario(tmp_path, monkeypatch, tax_kind='PPh Pasal 21/26')
    record, packets, forms = native_case()
    case.record.update(deepcopy(record))
    if literal_period:
        case.record['meta']['Masa Pajak'] = case.record['source_fields']['TaxPeriodCode']
    row = {**case.record.pop('source_fields'), 'ReturnSheetStatusCode': 'SUBMITTED',
           'ReturnSheetModel': case.record['meta']['Model SPT']}
    case.record.pop('source_identity')
    monkeypatch.setattr(protocol, 'META', dict(case.record['meta']))
    original = json.dumps({'IsSuccessful': True, 'Payload': {'Data': [row], 'TotalRecords': 1}}).encode()
    listing_url = driver.ORIGIN + '/returnsheet/api/returnsheetssubmitted'
    def goto(url, **kwargs):
        case.page.commit_navigation(url)
        request = Request(case.page, url=listing_url, post={
            'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0, 'Rows': 50, 'Filters': [],
            'isArchieved': False, 'LanguageId': 1, 'SortField': None, 'SortOrder': None})
        case.page.emit_grid_response(SimpleNamespace(url=listing_url, request=request, status=200,
                        headers={'content-type': 'application/json'}, body=lambda: original))
    monkeypatch.setattr(case.page, 'goto', goto)
    case.page.exchanges = [{'raw': p['body'], 'url': p['context']['url'], 'status': 200,
                           'post': p['context']['request_json'], 'method': p['context']['method']}
                          for p in packets]
    real_view = protocol.View.evaluate
    view_checked = []
    def view(control, script):
        # Require saved proof before the actual View action emits any detail traffic.
        identity = case.record['source_identity']
        assert identity['body_sha256'] == hashlib.sha256(original).hexdigest()
        assert identity['relative_path'].startswith('listing-responses/pph21-identity-')
        assert (tmp_path / identity['relative_path']).read_bytes() == original
        view_checked.append(True)
        return real_view(control, script)
    monkeypatch.setattr(protocol.View, 'evaluate', view)
    def observe(page, selected, scope, capture, **kwargs):
        assert page is case.page.popup and selected is case.record and scope == SCOPE
        return deepcopy(forms)
    monkeypatch.setattr(observer, 'observe_pph21_forms', observe)
    proof_folder = tmp_path / 'listing-responses'
    assert not proof_folder.exists()
    if occupied:
        proof_folder.write_bytes(b'SYNTHETIC EXISTING FILE')
    result = case.collect()
    if occupied:
        assert not result['complete'] and result['errors']
        assert case.page.view_calls == 0 and view_checked == []
        assert 'source_identity' not in case.record and 'source_fields' not in case.record
        assert proof_folder.read_bytes() == b'SYNTHETIC EXISTING FILE'
        assert not any(case.page.context.listeners.values())
        assert not case.page.listeners.get('response')
        return
    assert result['complete'] and not result['errors'], result['errors']
    assert view_checked == [True]
    assert case.dom_calls == [] and case.pdf_calls == [] and case.page.view_calls == 1
    captured = result['records'][0]
    assert captured['detail_source']['used'] == 'json'
    assert captured['source_fields'] == row
    assert [s['name'] for s in captured['sections']] == ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III']
    restored = driver.read_detail_checkpoint(tmp_path / 'returns' / '0001.json', captured,
                                             SCOPE, detail_source='json-first')
    assert restored is not None and restored['capture_complete']
    assert restored['detail_source']['used'] == 'json'
    assert restored['sections'] == captured['sections']
    case.assert_closed()
