"""Real collector/Edge regressions for listing-DOM metadata feeding corporate JSON.

Only routed synthetic requests and records. Removing period metadata must not
manufacture a contradictory empty year, nor bypass genuine identity conflicts.
"""
from copy import deepcopy
import json

import pytest

from coretax_json import JsonSafetyError
import support_json_corpus as corpus
from test_json_hybrid_native import NativeFixture, browser  # noqa: F401


class MissingListingPeriod(NativeFixture):
    def __init__(self, *args, metadata='absent', request_year='2025', **kwargs):
        super().__init__(*args, groups=True, **kwargs)
        self.listing_row = deepcopy(self.record['source_fields'])
        self.request_year = request_year
        if metadata == 'absent':
            self.record.pop('source_fields')
            self.record.pop('source_identity')
        else:
            self.record['source_fields'].pop('TaxPeriodCode')
        self.original_metadata = deepcopy(self.record.get('source_fields'))

    def grid_html(self, selector, endpoint, identity, name, total=0):
        if endpoint == '/loadcit/l4-table-a-grid':
            identity = {**identity, 'PeriodYear': self.request_year}
        return super().grid_html(selector, endpoint, identity, name, total)

    def route(self, route):
        request = route.request
        if request.url == corpus.ORIGIN + '/returnsheet/api/returnsheetssubmitted':
            assert request.method == 'POST'
            self.requests.append({'url': request.url, 'method': request.method,
                                  'body': request.post_data_json})
            route.fulfill(content_type='application/json', body=json.dumps({
                'IsSuccessful': True,
                'Payload': {'Data': [self.listing_row], 'TotalRecords': 1}}))
            return
        if request.url == corpus.ORIGIN + '/returnsheet/api/loadcit/l4-table-a-grid':
            body = request.post_data_json
            assert request.method == 'POST'
            assert body['ReturnSheetRecordId'] == corpus.RECORD_ID
            assert body['PeriodYear'] == self.request_year
            self.requests.append({'url': request.url, 'method': request.method, 'body': body})
            route.fulfill(content_type='application/json', body=corpus.wire({
                'IsSuccessful': True, 'Payload': {'Data': [], 'TotalRecords': 0, 'Index': None}}))
            return
        super().route(route)


@pytest.mark.parametrize('metadata', ['absent', 'period-missing'])
def test_missing_listing_period_allows_verified_whole_dom_fallback(
        browser, tmp_path, monkeypatch, metadata):
    fixture = MissingListingPeriod(browser, tmp_path, monkeypatch, metadata=metadata)
    try:
        result = fixture.collect()
        assert result['complete'] is True and result['errors'] == []
        record = result['records'][0]
        assert record['detail_source']['requested'] == 'json-first'
        assert record['detail_source']['used'] == 'dom'
        assert record.get('source_fields') == fixture.original_metadata
        assert any(field.get('value') == '0000777'
                   for section in record['sections'] for field in section.get('fields', []))
        tables = [table for section in record['sections'] if section['name'] == 'L9'
                  for table in section['tables']]
        assert sum(len(table['rows']) for table in tables) == 60
        assert all(table['complete'] for table in tables)
        assert max(table['pages'] for table in tables) == 6
        assert record['attachments'][0]['status'] == 'COMPLETE'
        assert fixture.unexpected == []
    finally:
        fixture.close()


@pytest.mark.parametrize('metadata', ['absent', 'period-missing'])
@pytest.mark.parametrize('request_year', ['2024', 2025])
def test_missing_listing_period_never_hides_wrong_year_or_request_type(
        browser, tmp_path, monkeypatch, metadata, request_year):
    fixture = MissingListingPeriod(browser, tmp_path, monkeypatch,
                                   metadata=metadata, request_year=request_year)
    try:
        with pytest.raises(JsonSafetyError):
            fixture.collect()
        assert fixture.record.get('source_fields') == fixture.original_metadata
        assert not fixture.record.get('detail_source')
        assert fixture.record['sections'] == []
        assert fixture.unexpected == []
    finally:
        fixture.close()


def test_missing_listing_period_never_hides_conflicting_primary_year(
        browser, tmp_path, monkeypatch):
    fixture = MissingListingPeriod(browser, tmp_path, monkeypatch)
    envelope = json.loads(fixture.raw)
    envelope['Payload']['PeriodYear'] = 2024
    fixture.raw = json.dumps(envelope).encode()
    try:
        with pytest.raises(JsonSafetyError):
            fixture.collect()
        assert not fixture.record.get('detail_source')
        assert fixture.record['sections'] == []
        assert fixture.unexpected == []
    finally:
        fixture.close()
