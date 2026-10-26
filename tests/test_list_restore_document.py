"""Restore the submitted grid across same-document router notifications only."""
import html
import json

import pytest

import coretax_browser as driver
from support_browser_protocol import DETAIL_URL, LIST_URL, META, RECORD, TAXPAYER, run_fixture
from support_isolated_browser import browser, context


@pytest.mark.parametrize('mutation,after_response', [
    ('none', False),
    ('replace', False), ('replace', True),
    ('push', False), ('push', True),
    ('fragment', False), ('fragment', True),
    ('twice', False), ('twice', True),
    ('reload', False), ('reload', True),
    ('route_detour', False), ('route_detour', True),
    ('query_detour', False), ('query_detour', True),
    ('taxpayer_detour', False), ('taxpayer_detour', True),
])
def test_owned_submitted_list_keeps_same_document_but_refuses_replacements_and_detours(
        context, monkeypatch, tmp_path, mutation, after_response):
    # A router replaceState on the identical URL emits framenavigated too. The
    # guard must preserve this Document, without accepting a reload at that URL
    # or forgetting a temporary route/identity contradiction after it returns.
    api = driver.ORIGIN + '/returnsheet/api/returnsheetssubmitted'
    post = {'TaxpayerAggregateIdentifier': TAXPAYER, 'First': 0, 'Rows': 50,
            'Filters': [], 'isArchieved': False, 'LanguageId': 1}
    visits, requests, captured, transitions = [], [], [], []
    headings = ''.join('<th>' + html.escape(key) + '</th>' for key in META)
    values = ''.join('<td>' + html.escape(value) + '</td>' for value in META.values())
    actions = {
        'none': '',
        'replace': 'history.replaceState({}, "", location.href);',
        'push': 'history.pushState({}, "", location.href);',
        'fragment': 'history.replaceState({}, "", location.href+"#synthetic");',
        'twice': 'history.replaceState({}, "", location.href);history.pushState({}, "", location.href);',
        'reload': 'location.reload();',
        'route_detour': 'history.replaceState({}, "", original.replace("submitted-", "archived-"));history.replaceState({}, "", original);',
        'query_detour': 'history.replaceState({}, "", original+"?synthetic=1");history.replaceState({}, "", original);',
        'taxpayer_detour': 'history.replaceState({}, "", original.replace("fixture-taxpayer", "synthetic-other-taxpayer"));history.replaceState({}, "", original);',
    }

    def route(bound):
        request = bound.request
        if request.url == LIST_URL and request.method == 'GET':
            visits.append(request.url)
            action = actions[mutation] if len(visits) == 1 else ''
            fetch = (f'await fetch({json.dumps(api)}, {{method:"POST",'
                     'headers:{"Content-Type":"application/json"},'
                     f'body:JSON.stringify({json.dumps(post)})}});')
            program = fetch + action if after_response else action + fetch
            body = ('<div class="main-content"><p-table><table><thead><tr>' + headings
                    + '<th>Action</th></tr></thead><tbody><tr>' + values
                    + '<td><button id="ViewButton" onclick=\'window.open('
                    + json.dumps(DETAIL_URL) + ')\'>View</button></td></tr></tbody></table>'
                    + '</p-table></div><script>const original=location.href;'
                    + '(async()=>{' + program + '})()</script>')
            bound.fulfill(status=200, content_type='text/html', body=body)
        elif request.url == api and request.method == 'POST':
            requests.append(request.post_data_json)
            bound.fulfill(status=200, content_type='application/json', body=json.dumps({
                'IsSuccessful': True, 'Payload': {'Data': [{'RecordId': RECORD}], 'TotalRecords': 1}}))
        elif request.url == DETAIL_URL and request.method == 'GET':
            bound.fulfill(status=200, content_type='text/html', body='<p>SYNTHETIC DETAIL</p>')
        else:
            bound.abort()

    context.route('**/*', route)
    page = context.new_page()
    page.on('framenavigated', lambda frame: transitions.append(frame.url)
            if frame == page.main_frame else None)
    original_wait = driver.ListObserver.wait
    monkeypatch.setattr(driver.ListObserver, 'wait',
                        lambda self, after, timeout=45: original_wait(self, after, timeout=2))

    def capture(detail, **kwargs):
        captured.append(detail.url)
        return {'sections': [{'name': 'SYNTHETIC', 'fields': [], 'tables': []}],
                'capture_complete': True, 'errors': []}

    monkeypatch.setattr(driver, 'capture_detail', capture)
    result = driver.collect_details(page, run_fixture(), tmp_path)
    accepted = mutation in ('none', 'replace', 'push', 'fragment', 'twice')
    assert result['complete'] is accepted, result['errors']
    assert captured == ([DETAIL_URL] if accepted else [])
    assert len(context.pages) == 1
    if accepted:
        assert visits == [LIST_URL], 'A same-document event must not trigger a retry'
        assert requests == [post], 'Use the browser-generated submitted-grid POST once'
        assert result['records'][0]['capture_complete']
        if mutation != 'none':
            assert len(transitions) >= 2, 'Exercise the actual same-document frame notification'
    else:
        assert len(visits) <= 2
        assert result['records'][0]['sections'] == []
        assert len(result['errors']) == 1
