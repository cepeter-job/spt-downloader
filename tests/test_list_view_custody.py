"""Fatal events during final probes and before View never authorize capture."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

import coretax_browser as driver
from coretax_json_capture import DetailJsonCapture
from support_browser_protocol import (DETAIL_URL, LIST_URL, META, RECORD,
    DetailPage, SourcePage, Table, response, run_fixture)
from test_list_restore_recovery import collector


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


@pytest.mark.parametrize('kind', ['document-request', 'route', 'query', 'taxpayer', 'same'])
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
                    interrupt(self, kind)
                return same
            handle.evaluate = interrupted
            return handle

    page = ProbePage()
    monkeypatch.setattr(driver, 'wait_idle', lambda target: setattr(target, 'idle_completed', True))
    observer = driver.ListObserver(page)
    try:
        observer.begin_navigation(LIST_URL)
        page.goto(LIST_URL)
        if kind == 'same':
            assert observer.wait(0)['rows'] == [{'RecordId': RECORD}]
        else:
            with pytest.raises(RuntimeError, match='ownership'):
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
    assert scenario.dom_calls == [] and result['records'][0]['sections'] == []
    assert all(handle.disposed for handle in scenario.page.document_handles + scenario.page.view_handles)
