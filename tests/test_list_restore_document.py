"""Restore the submitted grid across same-document router notifications only."""
import html
import json
from types import SimpleNamespace

import pytest

import coretax_browser as driver
from support_browser_protocol import DETAIL_URL, LIST_URL, META, RECORD, TAXPAYER, run_fixture
from support_isolated_browser import browser as browser, context as context
from support_browser_protocol import SourcePage, response
from test_list_restore_recovery import MissingListPage, collector as collector


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


@pytest.mark.parametrize('failure', ['capture', 'sample', 'false'])
def test_unreadable_committed_document_never_authorizes_view(tmp_path, collector, failure):
    class UnreadablePage(SourcePage):
        def evaluate_handle(self, script):
            if failure == 'capture':
                raise RuntimeError('SYNTHETIC DOCUMENT UNAVAILABLE')
            handle = super().evaluate_handle(script)
            def sample(_):
                if failure == 'sample':
                    raise RuntimeError('SYNTHETIC DOCUMENT UNAVAILABLE')
                return False
            handle.evaluate = sample
            return handle

    page = UnreadablePage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert not result['complete'] and collector == []
    assert page.navigated == [LIST_URL]
    assert all(handle.disposed for handle in page.document_handles)
    assert not any(page.listeners.values())


@pytest.mark.parametrize('mutation', ['same', 'replacement', 'navigation-request'])
def test_document_acquisition_reentrancy_keeps_only_the_same_owned_document(
        tmp_path, collector, mutation):
    class AcquiringPage(SourcePage):
        queued = None

        def evaluate_handle(self, script):
            self.queued = response()
            self.queued.request.frame = self.main_frame
            # Identity acquisition pumps events. This actual post-commit grid
            # request is the only one whose response will arrive after goto.
            self.emit('request', self.queued.request)
            if mutation == 'navigation-request':
                self.emit('request', SimpleNamespace(url=LIST_URL, resource_type='document',
                    frame=self.main_frame, is_navigation_request=lambda: True))
                self.replace_document()
                return super().evaluate_handle(script)
            handle = super().evaluate_handle(script)
            if mutation == 'replacement':
                self.replace_document()
            else:
                self.emit('framenavigated', self.main_frame)
            return handle

        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            if self.queued is None:
                # The old implementation never asks for Document identity.
                self.emit_grid_response(response())
            else:
                self.emit('response', self.queued)

    page = AcquiringPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert result['complete'] is (mutation == 'same')
    assert collector == ([DETAIL_URL] if mutation == 'same' else [])
    assert page.navigated == [LIST_URL]
    assert all(handle.disposed for handle in page.document_handles)
    assert not any(page.listeners.values())


def test_stop_during_document_identity_probe_prevents_view_and_releases_handle(tmp_path, collector):
    class StoppingPage(SourcePage):
        stopped = False

        def evaluate_handle(self, script):
            handle = super().evaluate_handle(script)
            sample = handle.evaluate
            def stop_on_sample(source):
                result = sample(source)
                self.stopped = True
                return result
            handle.evaluate = stop_on_sample
            return handle

    page = StoppingPage()
    def cancel():
        if page.stopped:
            raise driver.CaptureCancelled()
    with pytest.raises(driver.CaptureCancelled):
        driver.collect_details(page, run_fixture(), tmp_path, check_cancel=cancel)
    assert collector == [] and page.navigated == [LIST_URL]
    assert len(page.document_handles) == 1 and page.document_handles[0].disposed
    assert not any(page.listeners.values())


@pytest.mark.parametrize('retry', [False, True])
def test_document_handles_are_released_before_retry_and_on_close(tmp_path, collector, retry):
    class CustodyPage(MissingListPage if retry else SourcePage):
        def evaluate_handle(self, script):
            assert all(handle.disposed for handle in self.document_handles)
            return super().evaluate_handle(script)

    page = CustodyPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert result['complete'] and collector == [DETAIL_URL]
    assert len(page.document_handles) == (2 if retry else 1)
    assert all(handle.disposed for handle in page.document_handles)
    assert not any(page.listeners.values())
