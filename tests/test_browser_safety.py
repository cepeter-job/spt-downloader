"""Synthetic protocol fixtures exercise safety without tax sites or profiles."""
from pathlib import Path
from types import SimpleNamespace
import gc
import json
import sys
import weakref

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import coretax_browser as driver


from support_browser_protocol import (
    Container, DETAIL_URL, DetailPage, LIST_URL, META, RECORD, SignalSource, SourcePage, TAXPAYER, Table, View, response, run_fixture, write_checkpoint
)

@pytest.fixture(autouse=True)
def no_browser_wait(monkeypatch):
    # The protocol fixtures have no rendering or loading overlays.
    monkeypatch.setattr(driver, 'wait_idle', lambda page: None)


@pytest.mark.parametrize('url', [
    'https://untrusted.invalid/returnsheet/api/returnsheetsfixture',
    'https://untrusted.invalid/?path=/returnsheet/api/returnsheetsfixture',
    driver.ORIGIN.replace('https:', 'http:') + '/returnsheet/api/returnsheetsfixture',
    driver.ORIGIN + ':444/returnsheet/api/returnsheetsfixture',
    driver.ORIGIN.replace('https://', 'https://user@') + '/returnsheet/api/returnsheetsfixture',
])
def test_observer_rejects_list_payloads_outside_trusted_https_origin(url):
    observer = driver.ListObserver(SignalSource())
    observer.on_response(response(url=url))
    with pytest.raises(RuntimeError, match='No verifiable'):
        observer.wait(0, timeout=0)


@pytest.mark.parametrize('changes', [
    {'successful': 'false'}, {'successful': 1}, {'successful': None},
    {'status': 500}, {'total': True}, {'total': -1}, {'rows': ['not-a-record']},
])
def test_observer_rejects_unsuccessful_or_malformed_list_payloads(changes):
    observer = driver.ListObserver(SignalSource())
    observer.on_response(response(**changes))
    with pytest.raises(RuntimeError):
        observer.wait(0, timeout=0)


def test_observer_requires_explicit_success():
    item = response()
    del item.json()['IsSuccessful']
    observer = driver.ListObserver(SignalSource())
    observer.on_response(item)
    with pytest.raises(RuntimeError):
        observer.wait(0, timeout=0)


def test_observer_releases_previous_batches():
    class WeakRow(dict):
        pass

    observer = driver.ListObserver(SignalSource())
    old_row = WeakRow(RecordId='fixture-previous-record')
    old_ref = weakref.ref(old_row)
    observer.on_response(response([old_row]))
    del old_row
    observer.on_response(response())
    gc.collect()
    assert old_ref() is None, 'Completed list batches must not accumulate in the observer'


def test_observer_returns_the_response_that_finished_during_ui_settling(monkeypatch):
    observer = driver.ListObserver(SignalSource())
    observer.on_response(response([{'RecordId': 'fixture-before-render'}]))
    monkeypatch.setattr(driver, 'wait_idle', lambda page: observer.on_response(response()))
    assert observer.wait(0)['rows'] == [{'RecordId': RECORD}]


def test_observer_sequence_does_not_reset_when_old_batches_are_released():
    observer = driver.ListObserver(SignalSource())
    for index in range(3):
        marker = observer.sequence
        observer.on_response(response([{'RecordId': f'fixture-{index}'}]))
        assert observer.wait(marker)['rows'] == [{'RecordId': f'fixture-{index}'}]
    with pytest.raises(RuntimeError, match='No verifiable'):
        observer.wait(observer.sequence, timeout=0)


def test_zero_timeout_expires_even_when_clock_has_not_advanced(monkeypatch):
    observer = driver.ListObserver(SignalSource())
    monkeypatch.setattr(driver.time, 'monotonic', lambda: 123.0)
    with pytest.raises(RuntimeError, match='No verifiable'):
        observer.wait(0, timeout=0)


def install_capture(monkeypatch):
    monkeypatch.setattr(driver, 'capture_detail', lambda page, **kwargs: {
        'sections': [{'name': 'Synthetic fixture', 'fields': [{'label': 'Fixture', 'value': '001'}], 'tables': []}],
        'capture_complete': True, 'errors': [],
    })


@pytest.mark.parametrize('error_type', [RuntimeError, ValueError, driver.PlaywrightError])
def test_detail_failure_keeps_private_exception_text_out_of_outputs(tmp_path, monkeypatch, capsys, error_type):
    secret = 'SYNTHETIC_PRIVATE_DETAIL_TOKEN'
    def failed_capture(*args, **kwargs):
        raise error_type(secret)
    monkeypatch.setattr(driver, 'capture_detail', failed_capture)
    result = driver.collect_details(SourcePage(), run_fixture(), tmp_path)
    assert result['complete'] is False
    assert result['records'][0]['capture_complete'] is False
    assert result['errors'][-1]['message'] == 'capture_failed'
    assert secret not in capsys.readouterr().out
    assert secret not in json.dumps(result)
    assert secret not in (tmp_path / 'run.json').read_text(encoding='utf-8')


def test_detail_failure_does_not_stringify_the_exception(tmp_path, monkeypatch):
    class Unprintable(RuntimeError):
        def __str__(self):
            pytest.fail('Private exception text must never be requested')
    def failed_capture(*args, **kwargs):
        raise Unprintable()
    monkeypatch.setattr(driver, 'capture_detail', failed_capture)
    result = driver.collect_details(SourcePage(), run_fixture(), tmp_path)
    assert result['complete'] is False
    assert result['errors'][-1]['message'] == 'capture_failed'


@pytest.mark.parametrize('list_url', [
    'https://untrusted.invalid/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER,
    LIST_URL.replace('https:', 'http:'),
    driver.ORIGIN + '/returnsheets/id-ID/delete-return/' + TAXPAYER,
])
def test_detail_resume_rejects_unsafe_list_url_before_navigation(tmp_path, monkeypatch, list_url):
    install_capture(monkeypatch)
    page = SourcePage()
    result = driver.collect_details(page, run_fixture(list_url), tmp_path)
    assert page.navigated == [], 'Untrusted checkpoint URLs must be rejected before browser navigation'
    assert not result['complete']


def test_detail_provenance_uses_url_path_when_list_has_query_and_fragment(tmp_path, monkeypatch):
    install_capture(monkeypatch)
    page = SourcePage()
    result = driver.collect_details(page, run_fixture(LIST_URL + '?page=1#fixture'), tmp_path)
    assert result['complete'], result['errors']
    assert result['records'][0]['detail_url'] == DETAIL_URL


def test_detail_capture_rejects_other_record_for_same_taxpayer(tmp_path, monkeypatch):
    install_capture(monkeypatch)
    page = SourcePage(DETAIL_URL.replace(RECORD, 'fixture-other-record'))
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert not result['complete'], 'A matching taxpayer does not establish return identity'
    assert not result['records'][0]['sections']
    assert page.popup.closed


@pytest.mark.parametrize('identifier', [None, '', 123, True])
def test_detail_does_not_substitute_aggregate_or_coerce_record_id_before_view(tmp_path, monkeypatch, identifier):
    calls = []
    original_view = View.evaluate
    def observed_view(view, script):
        calls.append(view.page.url)
        return original_view(view, script)
    monkeypatch.setattr(View, 'evaluate', observed_view)
    install_capture(monkeypatch)

    class InvalidIdentityPage(SourcePage):
        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            self.emit_grid_response(response([{
                'RecordId': identifier, 'AggregateIdentifier': RECORD,
                'TaxpayerAggregateIdentifier': TAXPAYER}]))

    result = driver.collect_details(InvalidIdentityPage(), run_fixture(), tmp_path)
    assert calls == [], 'Fresh list RecordId must be verified before any View action'
    assert not result['complete']
    assert not result['records'][0]['capture_complete']


def test_detail_rejects_foreign_taxpayer_in_fresh_rows_before_view(tmp_path, monkeypatch):
    calls = []
    original_view = View.evaluate
    def observed_view(view, script):
        calls.append(view.page.url)
        return original_view(view, script)
    monkeypatch.setattr(View, 'evaluate', observed_view)
    install_capture(monkeypatch)

    class ForeignIdentityPage(SourcePage):
        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            self.emit_grid_response(response([{
                'RecordId': RECORD, 'TaxpayerAggregateIdentifier': 'fixture-other-taxpayer'}]))

    result = driver.collect_details(ForeignIdentityPage(), run_fixture(), tmp_path)
    assert calls == [], 'Matching metadata and RecordId do not override a foreign taxpayer'
    assert not result['complete']
    assert result['errors']


def test_detail_refinds_record_after_reordering_instead_of_clicking_saved_position(tmp_path, monkeypatch):
    clicked = []
    install_capture(monkeypatch)

    class ReorderedView(View):
        def __init__(self, page, position):
            super().__init__(page)
            self.position = position

        def evaluate(self, script):
            clicked.append(self.position)
            super().evaluate(script)

    class ReorderedTable(Table):
        def __init__(self, page, position=None):
            super().__init__(page)
            self.position = position

        def evaluate(self, script):
            # Identical captions cannot identify which return is selected.
            return {'headers': list(META), 'rows': [list(META.values()), list(META.values())], 'footer': []}

        def locator(self, selector):
            if selector == 'button[id=ViewButton]':
                return ReorderedView(self.page, self.position)
            return self

        def nth(self, index):
            return ReorderedTable(self.page, index)

    class ReorderedPage(SourcePage):
        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            self.emit_grid_response(response([
                {'RecordId': 'fixture-other-record', 'TaxpayerAggregateIdentifier': TAXPAYER},
                {'RecordId': RECORD, 'TaxpayerAggregateIdentifier': TAXPAYER}]))

        def locator(self, selector):
            return ReorderedTable(self)

    run = run_fixture()
    run['records'][0]['row_position'] = 0
    result = driver.collect_details(ReorderedPage(), run, tmp_path)
    assert clicked == [1], 'A saved position is not a RecordId when ordering changes'
    assert result['complete'], result['errors']


def test_readonly_view_uses_popup_from_the_initiating_page():
    page = SourcePage()
    unrelated = DetailPage(DETAIL_URL.replace(RECORD, 'unrelated-fixture-record'))
    page.unrelated_popup = unrelated
    detail, is_popup = driver.open_return_readonly(page, Table(page), TAXPAYER)
    assert detail is page.popup, 'An unrelated tab in a reused context is not the selected return'
    assert is_popup
    assert not unrelated.closed


@pytest.mark.parametrize('target', [
    DETAIL_URL.replace('https:', 'http:'),
    'https://untrusted.invalid/returnsheets/' + TAXPAYER + '/' + RECORD,
    DETAIL_URL.replace(TAXPAYER, 'fixture-other-taxpayer'),
])
def test_readonly_view_closes_rejected_popup(target):
    page = SourcePage(target)
    with pytest.raises(RuntimeError):
        driver.open_return_readonly(page, Table(page), TAXPAYER)
    assert page.popup.closed, 'Failed popup navigation must release the tab it created'
    assert not page.listeners.get('popup')


@pytest.mark.parametrize('changes', [
    {'meta': {**META, 'Masa Pajak': 'Januari 2024'}},
    {'list_url': LIST_URL.replace(TAXPAYER, 'fixture-other-taxpayer')},
    {'list_page': 99}, {'key': 'fixture-other-key'},
    {'detail_url': DETAIL_URL.replace(RECORD, 'fixture-other-record')},
])
def test_resume_rejects_checkpoint_with_different_inventory_provenance(tmp_path, changes):
    run = run_fixture()
    write_checkpoint(tmp_path, run['records'][0], **changes)
    with pytest.raises(RuntimeError, match='checkpoint'):
        driver.collect_details(SourcePage(), run, tmp_path)


def test_resume_copies_capture_fields_without_overwriting_inventory(tmp_path):
    run = run_fixture()
    write_checkpoint(tmp_path, run['records'][0], untrusted_extra='not inventory data')
    result = driver.collect_details(SourcePage(), run, tmp_path)
    assert result['complete']
    assert result['records'][0]['sections'][0]['name'] == 'Synthetic saved section'
    assert 'untrusted_extra' not in result['records'][0]


def test_limited_run_validates_scope_of_later_checkpoints_before_reconciliation(tmp_path, monkeypatch):
    install_capture(monkeypatch)
    run = run_fixture()
    for index in (2, 3):
        run['records'].append({**run['records'][0], 'record_id': f'fixture-record-{index}', 'key': f'fixture-key-{index}'})
    write_checkpoint(tmp_path, run['records'][2], ordinal=3,
                     scope=['0000000000000002', 2024, 'period'])
    with pytest.raises(RuntimeError, match='checkpoint'):
        driver.collect_details(SourcePage(), run, tmp_path, detail_limit=1)


class PagerButton:
    def __init__(self, container, delta):
        self.container, self.delta = container, delta

    def click(self):
        self.container.index += self.delta

    def evaluate(self, script, owner):
        assert owner is self.container
        self.click()
        return True


class PagedTable:
    def __init__(self, pages, start=0):
        self.pages, self.index = pages, start
        self.disposed = False

    def element_handle(self):
        return self

    def evaluate_handle(self, script):
        return self

    def evaluate(self, script):
        number, value = self.pages[self.index]
        if script == driver.STATE_JS:
            return json.dumps({'p': [number], 'rows': [value]})
        return {'headers': ['Fixture'], 'rows': [[value]], 'footer': []}

    def query_selector(self, selector):
        if 'p-paginator-prev' in selector and self.index:
            return PagerButton(self, -1)
        if 'p-paginator-next' in selector and self.index + 1 < len(self.pages):
            return PagerButton(self, 1)
        return None

    def dispose(self):
        self.disposed = True


def test_table_capture_resets_retained_page_with_previous_when_first_is_absent():
    table = PagedTable([(1, 'fixture-one'), (2, 'fixture-two')], start=1)
    captured = driver.capture_table(SignalSource(), table, 1, max_pages=5)
    assert captured['rows'] == [['fixture-one'], ['fixture-two']]
    assert captured['complete']


def test_repeated_final_page_is_partial_even_when_next_becomes_disabled():
    table = PagedTable([(1, 'fixture-one'), (2, 'fixture-two'), (1, 'fixture-one')])
    captured = driver.capture_table(SignalSource(), table, 1, max_pages=5)
    assert not captured['complete'], 'A repeated terminal page is not complete pagination'
    assert captured['rows'] == [['fixture-one'], ['fixture-two']]


class EmptyLocator:
    @property
    def first(self):
        return self

    def count(self):
        return 0


class AccordionControl:
    def __init__(self, panel, position):
        self.panel, self.position = panel, position

    def evaluate(self, script):
        self.panel.expanded[self.position] = True

    def dispose(self):
        pass


class CollapsedControls:
    def __init__(self, panel):
        self.panel = panel

    def count(self):
        return len(self.element_handles())

    def element_handles(self):
        return [AccordionControl(self.panel, i) for i, expanded in enumerate(self.panel.expanded) if not expanded]

    def nth(self, index):
        return self.element_handles()[index]


class AccordionPanel:
    def __init__(self):
        self.expanded = [False, False]
        self.first = self

    def wait_for(self, **kwargs):
        pass

    def locator(self, selector):
        if selector.startswith('.p-accordion-header'):
            return CollapsedControls(self)
        return EmptyLocator()

    def evaluate(self, script):
        return [{'label': f'Fixture {i}', 'value': f'0{i}'}
                for i, expanded in enumerate(self.expanded, 1) if expanded]

    def inner_text(self):
        return 'Synthetic accordion fixture'


def test_detail_captures_every_initially_collapsed_accordion():
    panel = AccordionPanel()
    captured = driver.capture_detail(SimpleNamespace(locator=lambda selector: panel))
    assert captured['capture_complete'], captured['errors']
    assert captured['sections'][0]['fields'] == [
        {'label': 'Fixture 1', 'value': '01'}, {'label': 'Fixture 2', 'value': '02'}]


def test_exclusive_accordion_is_partial_when_earlier_content_closes(monkeypatch):
    def exclusive_open(self, script):
        self.panel.expanded[:] = [False] * len(self.panel.expanded)
        self.panel.expanded[self.position] = True

    monkeypatch.setattr(AccordionControl, 'evaluate', exclusive_open)
    panel = AccordionPanel()
    captured = driver.capture_detail(SimpleNamespace(locator=lambda selector: panel))
    assert not captured['capture_complete'], 'Exclusive accordions must not certify omitted sections'
    assert captured['sections'][0]['fields'] == [{'label': 'Fixture 2', 'value': '02'}]
    assert any('collapsed' in error['message'] for error in captured['errors'])


def test_detail_list_reset_obeys_page_limit(tmp_path, monkeypatch):
    page = SourcePage()

    class StuckPrevious:
        clicks = 0

        def evaluate(self, script, owner=None):
            if owner is not None:
                return True
            self.clicks += 1
            if self.clicks > 2:
                raise RuntimeError('Synthetic watchdog: unbounded Previous loop')
            page.emit_grid_response(response())
            return None

    previous = StuckPrevious()

    class StuckContainer(Container):
        def query_selector(self, selector):
            return previous if 'p-paginator-prev' in selector else None

    monkeypatch.setattr(Table, 'evaluate_handle', lambda self, script: StuckContainer())
    captured = driver.collect_details(page, run_fixture(), tmp_path, max_pages=2)
    assert previous.clicks == 2, 'The owned Previous loop must stop at its exact two-page cap'
    assert not captured['complete']
    assert captured['errors'][0]['message'] == 'capture_failed'
