"""Full collector binds PPh21 listing bytes before View, then replays custody."""
from copy import deepcopy
import hashlib
import json
from types import SimpleNamespace

import coretax_browser as driver
import coretax_pph21_observer as observer
import support_browser_protocol as protocol
from support_json_hybrid import Scenario
from support_json_network import Request
from pph21_projection_fixture import case as native_case
from masa_json_fixtures import SCOPE, TAXPAYER


def test_collect_attaches_original_listing_identity_and_replays_native_checkpoint(tmp_path, monkeypatch):
    case = Scenario(tmp_path, monkeypatch, tax_kind='PPh Pasal 21/26')
    record, packets, forms = native_case()
    case.record.update(deepcopy(record))
    row = {**case.record.pop('source_fields'), 'ReturnSheetStatusCode': 'SUBMITTED',
           'ReturnSheetModel': case.record['meta']['Model SPT']}
    case.record.pop('source_identity')
    monkeypatch.setattr(protocol, 'META', dict(case.record['meta']))
    original = json.dumps({'IsSuccessful': True, 'Payload': {'Data': [row], 'TotalRecords': 1}}).encode()
    listing_url = driver.ORIGIN + '/returnsheet/api/returnsheetssubmitted'
    def goto(url, **kwargs):
        case.page.navigated.append(url)
        case.page.url = url
        request = Request(case.page, url=listing_url, post={
            'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0, 'Rows': 50, 'Filters': [],
            'isArchieved': False, 'LanguageId': 1, 'SortField': None, 'SortOrder': None})
        case.page.emit('response', SimpleNamespace(url=listing_url, request=request, status=200,
                        headers={'content-type': 'application/json'}, body=lambda: original))
    monkeypatch.setattr(case.page, 'goto', goto)
    case.page.exchanges = [{'raw': p['body'], 'url': p['context']['url'], 'status': 200,
                           'post': p['context']['request_json'], 'method': p['context']['method']}
                          for p in packets]
    def observe(page, selected, scope, capture, **kwargs):
        assert page is case.page.popup and selected is case.record and scope == SCOPE
        # Absence before collection proves this came from the original list response.
        identity = selected['source_identity']
        assert identity['body_sha256'] == hashlib.sha256(original).hexdigest()
        assert identity['relative_path'].startswith('listing-responses/pph21-identity-')
        assert (tmp_path / identity['relative_path']).read_bytes() == original
        return deepcopy(forms)
    monkeypatch.setattr(observer, 'observe_pph21_forms', observe)
    result = case.collect()
    assert result['complete'] and not result['errors']
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
