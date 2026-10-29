"""Real Edge submitted-list reloads, fully routed local synthetic responses."""
import html
import json

import pytest

import coretax_browser as driver
from support_browser_protocol import DETAIL_URL, LIST_URL, META, RECORD, TAXPAYER, run_fixture
from support_isolated_browser import browser, context
from support_browser_protocol import capture_failures


@pytest.mark.parametrize('case', ['recover', 'missing', 'http403', 'application_error'])
def test_real_list_restoration_keeps_owned_requests_and_terminal_failures(context, monkeypatch, tmp_path, case):
    failures = capture_failures(monkeypatch)
    api = driver.ORIGIN + '/returnsheet/api/returnsheetssubmitted'
    visits, captured = [], []
    post = {'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0, 'Rows': 50,
            'Filters': [], 'isArchieved': False, 'LanguageId': 1}
    headers = ''.join('<th>' + html.escape(key) + '</th>' for key in META)
    values = ''.join('<td>' + html.escape(value) + '</td>' for value in META.values())

    def route(request_route):
        request = request_route.request
        if request.url == LIST_URL and request.method == 'GET':
            visits.append(request.url)
            should_fetch = case in ('http403', 'application_error') or (case == 'recover' and len(visits) == 2)
            fetch = (f'<script>fetch({json.dumps(api)},{{method:"POST",'
                     'headers:{"Content-Type":"application/json"},'
                     f'body:JSON.stringify({json.dumps(post)})}})</script>') if should_fetch else ''
            body = ('<div class="main-content"><p-table><table><thead><tr>' + headers
                    + '<th>Action</th></tr></thead><tbody><tr>' + values
                    + '<td><button id="ViewButton" onclick=\'window.open('
                    + json.dumps(DETAIL_URL) + ')\'>View</button></td></tr></tbody></table>'
                    + '</p-table></div>' + fetch)
            request_route.fulfill(status=200, content_type='text/html', body=body)
        elif request.url == api and request.method == 'POST':
            assert request.post_data_json == post
            if case == 'http403':
                request_route.fulfill(status=403, content_type='text/html', body='<p>SYNTHETIC DENIED</p>')
            else:
                payload = ({'IsSuccessful': False, 'Payload': None} if case == 'application_error' else {
                    'IsSuccessful': True, 'Payload': {'Data': [{'RecordId': RECORD}], 'TotalRecords': 1}})
                request_route.fulfill(status=200, content_type='application/json', body=json.dumps(payload))
        elif request.url == DETAIL_URL and request.method == 'GET':
            request_route.fulfill(status=200, content_type='text/html', body='<p>SYNTHETIC DETAIL</p>')
        else:
            request_route.abort()

    context.route('**/*', route)
    page = context.new_page()
    original_wait = driver.ListObserver.wait
    monkeypatch.setattr(driver.ListObserver, 'wait',
                        lambda self, after, timeout=45: original_wait(self, after, timeout=2))

    def capture(detail, **kwargs):
        captured.append(detail.url)
        return {'sections': [{'name': 'SYNTHETIC', 'fields': [], 'tables': []}],
                'capture_complete': True, 'errors': []}

    monkeypatch.setattr(driver, 'capture_detail', capture)
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert visits == [LIST_URL] * (1 if case in ('http403', 'application_error') else 2)
    assert result['complete'] is (case == 'recover')
    assert captured == ([DETAIL_URL] if case == 'recover' else [])
    assert len(context.pages) == 1, 'Owned detail popup is closed after capture'
    if case != 'recover':
        assert result['records'][0]['sections'] == []
        assert len(result['errors']) == 1
        if case in ('http403', 'application_error'):
            assert any('unsuccessful' in str(error) for error in failures)
            assert result['errors'][0]['message'] == 'capture_failed'
