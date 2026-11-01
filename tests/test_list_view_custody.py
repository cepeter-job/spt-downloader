"""Fatal events during final probes and before View never authorize capture."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

import coretax_browser as driver
from coretax_json_capture import DetailJsonCapture
from support_browser_protocol import (DETAIL_URL, LIST_URL, META, RECORD,
    DetailPage, SourcePage, Table, response, run_fixture)
from test_list_restore_recovery import collector as collector


def interrupt(page, kind):
    if kind == 'document-request':
        page.emit('request', SimpleNamespace(url=LIST_URL, resource_type='document',
            frame=page.main_frame, is_navigation_request=lambda: True))
    elif kind == 'replacement':
        page.replace_document()
    elif kind == 'same':
        page.emit('framenavigated', page.main_frame)
    else:
        original = page.url
        if kind == 'route': page.url = original.replace('/submitted-', '/archived-')
        elif kind == 'query': page.url = original + '?synthetic-detour=1'
        elif kind == 'taxpayer': page.url = original.replace('fixture-taxpayer', 'synthetic-other-taxpayer')
        else: raise AssertionError(kind)
        page.emit('framenavigated', page.main_frame)
        page.url = original
        page.emit('framenavigated', page.main_frame)


@pytest.mark.parametrize('kind', ['document-request', 'route', 'query', 'taxpayer', 'same', 'filter-error'])
def test_final_wait_probe_cannot_override_an_event_it_pumps(tmp_path, monkeypatch, collector, kind):
    class ProbePage(SourcePage):
        probes = 0
        idle_completed = False
        injected = False

        def evaluate_handle(self, script):
            handle = super().evaluate_handle(script)
            sample = handle.evaluate
            def interrupted(source):
                same = sample(source)
                self.probes += 1
                if self.idle_completed and not self.injected:
                    self.injected = True
                    # Inject during the final post-idle identity gate, even
                    # if earlier acquisition/probe counts change. The old Document
                    # can still compare True before a replacement commits.
                    if kind == 'filter-error':
                        self.inject_filter_error()
                    else:
                        interrupt(self, kind)
                return same
            handle.evaluate = interrupted
            return handle

    page = ProbePage()
    monkeypatch.setattr(driver, 'wait_idle', lambda target: setattr(target, 'idle_completed', True))
    observer = driver.ListObserver(page)
    if kind == 'filter-error':
        observer.request_filter = SimpleNamespace(error=None)
        error = driver.JsonSafetyError('Owned inventory filter request was rejected')
        page.inject_filter_error = lambda: setattr(observer.request_filter, 'error', error)
    try:
        observer.begin_navigation(LIST_URL)
        page.goto(LIST_URL)
        if kind == 'same':
            assert observer.wait(0)['rows'] == [{'RecordId': RECORD}]
        else:
            with pytest.raises(RuntimeError, match='filter' if kind == 'filter-error' else 'ownership'):
                observer.wait(0)
        assert page.injected and page.probes >= 3
    finally:
        observer.close()
    assert all(handle.disposed for handle in page.document_handles)
    assert not any(page.listeners.values())


@pytest.mark.parametrize('kind', ['replacement', 'route'])
def test_metadata_time_custody_change_prevents_view(tmp_path, monkeypatch, collector, kind):
    page = SourcePage()
    original = Table.evaluate
    mutations = []
    def metadata(table, script):
        result = original(table, script)
        mutations.append(kind)
        interrupt(page, kind)
        return result
    monkeypatch.setattr(Table, 'evaluate', metadata)
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert mutations == [kind]
    assert not result['complete'] and collector == []
    assert result['records'][0]['sections'] == []
    assert page.navigated == [LIST_URL]
    assert all(handle.disposed for handle in page.document_handles + page.view_handles)


def test_reused_group_rejects_source_document_changed_during_prior_popup(
        tmp_path, monkeypatch, collector):
    second_id = 'fixture-record-two'
    second_meta = {**META, 'Model SPT': 'Pembetulan 1'}
    class TwoRows(Table):
        def evaluate(self, script):
            return {'headers': list(META), 'rows': [list(META.values()), list(second_meta.values())], 'footer': []}

        def nth(self, index):
            assert index in (0, 1)
            return self

    class TwoReturns(SourcePage):
        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            self.emit_grid_response(response([{'RecordId': RECORD}, {'RecordId': second_id}]))

        def locator(self, selector):
            return TwoRows(self)

    page = TwoReturns()
    original_capture = driver.capture_detail
    def capture(detail, **kwargs):
        value = original_capture(detail, **kwargs)
        if len(collector) == 1:
            interrupt(page, 'replacement')
            page.popup = DetailPage(DETAIL_URL.replace(RECORD, second_id))
        return value
    monkeypatch.setattr(driver, 'capture_detail', capture)
    run = run_fixture()
    second = deepcopy(run['records'][0])
    second.update(key='fixture-key-two', record_id=second_id, meta=second_meta)
    run['records'].append(second)
    result = driver.collect_details(page, run, tmp_path)
    assert not result['complete'] and collector == [DETAIL_URL]
    assert result['records'][0]['capture_complete'] is True
    assert result['records'][1]['capture_complete'] is False
    assert page.navigated == [LIST_URL], 'A known custody change is not a timeout-only retry'


@pytest.mark.parametrize('kind', ['replacement', 'route'])
def test_json_view_preparation_custody_change_prevents_the_click(tmp_path, monkeypatch, kind):
    from support_json_hybrid import Scenario
    scenario = Scenario(tmp_path, monkeypatch, mode='json-first', tax_kind='Fixture')
    original = DetailJsonCapture.begin_readonly_view
    preparations = []
    def prepare(capture):
        result = original(capture)
        assert capture._view_called is True
        preparations.append(kind)
        interrupt(scenario.page, kind)
        return result
    monkeypatch.setattr(DetailJsonCapture, 'begin_readonly_view', prepare)
    result = scenario.collect()
    assert preparations == [kind]
    assert not result['complete'] and scenario.page.view_calls == 0
    assert scenario.dom_calls == [] and scenario.pdf_calls == []
    assert result['records'][0]['capture_complete'] is False
    assert result['records'][0].get('sections', []) == []
    assert all(handle.disposed for handle in scenario.page.document_handles + scenario.page.view_handles)


def deferred_page(monkeypatch, outcome):
    from greenlet import greenlet, getcurrent

    class DeferredPage(SourcePage):
        elapsed = 0
        stopped = False

        def __init__(self):
            super().__init__()
            self.acquisitions = []

        def evaluate_handle(self, script):
            handle = super().evaluate_handle(script)
            # The event callback yields its identity RPC before goto returns.
            getcurrent().parent.switch()
            return handle

        def goto(self, url, **kwargs):
            self.navigated.append(url)
            self.url = url
            self.document_token = object()
            task = greenlet(lambda: self.emit('framenavigated', self.main_frame))
            self.acquisitions.append(task)
            task.switch()
            self.emit_grid_response(response())

        def wait_for_timeout(self, milliseconds):
            self.elapsed += 1.1 if outcome == 'late' else milliseconds / 1000
            if outcome in ('complete', 'late') and not self.acquisitions[-1].dead:
                self.acquisitions[-1].switch()
            elif outcome == 'stop':
                self.stopped = True

        def drain(self):
            self.stopped = False
            for task in self.acquisitions:
                if not task.dead:
                    task.switch()

    page = DeferredPage()
    monkeypatch.setattr(driver.time, 'monotonic', lambda: page.elapsed)
    monkeypatch.setattr(driver, 'wait_idle', lambda page: None)
    return page


@pytest.mark.parametrize('outcome', ['complete', 'timeout', 'stop', 'late'])
def test_wait_keeps_document_acquisition_pending_without_authorizing_or_failing_early(monkeypatch, outcome):
    page = deferred_page(monkeypatch, outcome)
    def cancel():
        if page.stopped:
            raise driver.CaptureCancelled()
    observer = driver.ListObserver(page, check_cancel=cancel)
    try:
        observer.begin_navigation(LIST_URL)
        page.goto(LIST_URL)
        assert observer._binding_document and observer._document is None
        assert observer.sequence == 1 and not observer.navigation_failed
        if outcome == 'complete':
            assert observer.wait(0, timeout=1)['rows'] == [{'RecordId': RECORD}]
            assert page.acquisitions[-1].dead
        elif outcome in ('timeout', 'late'):
            with pytest.raises(RuntimeError, match='ownership') as caught:
                observer.wait(0, timeout=1)
            assert not isinstance(caught.value, driver.ListResponseTimeout)
            assert 1 <= page.elapsed <= 1.1 and observer.navigation_failed
        else:
            with pytest.raises(driver.CaptureCancelled):
                observer.wait(0, timeout=1)
        assert page.navigated == [LIST_URL]
    finally:
        observer.close()
        page.drain()
        disposed_after_close = all(handle.disposed for handle in page.document_handles)
        for handle in page.document_handles:
            if not handle.disposed:
                handle.dispose()  # Clean a rejected late handle after sampling.
    assert disposed_after_close and not any(page.listeners.values())


@pytest.mark.parametrize('action', ['close', 'reset', 'new-pending'])
def test_late_acquisition_cannot_attach_to_closed_or_newer_attempt(monkeypatch, action):
    page = deferred_page(monkeypatch, 'complete')
    observer = driver.ListObserver(page)
    closed = False
    try:
        observer.begin_navigation(LIST_URL)
        page.goto(LIST_URL)
        old_task = page.acquisitions[0]
        old_handle = page.document_handles[0]
        assert observer._binding_document and not old_task.dead
        if action == 'close':
            observer.close()
            closed = True
        else:
            observer.begin_navigation(LIST_URL)
            if action == 'new-pending':
                page.goto(LIST_URL)
                assert observer._binding_document and observer.navigation_committed
        old_task.switch()
        assert old_task.dead and old_handle.disposed
        assert observer._document is None
        if action == 'close':
            assert observer.navigation_source is None and not observer._binding_document
        elif action == 'reset':
            assert observer.navigation_failed is False
            assert not observer.navigation_committed and not observer._binding_document
        else:
            assert observer.navigation_failed is False
            assert observer.navigation_committed and observer._binding_document
            page.acquisitions[-1].switch()
            assert observer._document is page.document_handles[-1]
            assert observer.wait(1, timeout=1)['rows'] == [{'RecordId': RECORD}]
    finally:
        if not closed:
            observer.close()
        page.drain()
        disposed_after_close = all(handle.disposed for handle in page.document_handles)
        for handle in page.document_handles:
            if not handle.disposed:
                handle.dispose()
    assert disposed_after_close and not any(page.listeners.values())
