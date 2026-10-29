"""Bounded missing-list response recovery through the public detail collector."""
import pytest

import coretax_browser as driver
from support_browser_protocol import (
    DETAIL_URL, LIST_URL, TAXPAYER, SourcePage, response, run_fixture, capture_failures,
)


class MissingListPage(SourcePage):
    def __init__(self, *, recover=True, replay=None):
        super().__init__()
        self.recover, self.replay = recover, replay
        self.timed_out = False

    def goto(self, url, **kwargs):
        self.commit_navigation(url)
        if self.recover and len(self.navigated) == 2:
            self.emit_grid_response(self.replay or response())


@pytest.fixture
def collector(monkeypatch):
    captured = []
    monkeypatch.setattr(driver, 'wait_idle', lambda page: None)
    original = driver.ListObserver.wait

    def immediate(self, after, timeout=45):
        try:
            return original(self, after, timeout=0)
        except RuntimeError:
            self.page.timed_out = True
            raise

    monkeypatch.setattr(driver.ListObserver, 'wait', immediate)

    def capture(page, **kwargs):
        captured.append(page.url)
        return {'sections': [{'name': 'SYNTHETIC', 'fields': [], 'tables': []}],
                'capture_complete': True, 'errors': []}

    monkeypatch.setattr(driver, 'capture_detail', capture)
    return captured


@pytest.fixture
def observed_failures(monkeypatch):
    return capture_failures(monkeypatch)


def test_missing_initial_list_response_retries_once_then_captures(tmp_path, collector):
    page = MissingListPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert result['complete'], result['errors']
    assert page.navigated == [LIST_URL, LIST_URL]
    assert collector == [DETAIL_URL]
    assert result['records'][0]['capture_complete']
    assert not any(page.listeners.values())


def test_second_missing_list_response_stays_partial_without_third_navigation(tmp_path, collector, observed_failures):
    page = MissingListPage(recover=False)
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL, LIST_URL]
    assert not result['complete'] and not result['records'][0]['capture_complete']
    assert result['records'][0]['sections'] == []
    assert len(result['errors']) == 1 and result['errors'][0]['message'] == 'capture_failed'
    assert any('No verifiable' in str(error) for error in observed_failures)
    assert collector == []


def test_retry_requires_a_new_marker_and_cannot_reuse_previous_response(tmp_path, collector):
    class StalePage(MissingListPage):
        def on(self, name, callback):
            super().on(name, callback)
            if name == 'response':
                callback(response())  # Before the first navigation's marker.

    page = StalePage(recover=False)
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert not result['complete']
    assert page.navigated == [LIST_URL, LIST_URL]
    assert collector == []


def test_retry_response_still_requires_the_selected_record(tmp_path, collector, observed_failures):
    page = MissingListPage(replay=response([{'RecordId': 'synthetic-other-record'}]))
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL, LIST_URL]
    assert not result['complete']
    assert result['errors'][0]['message'] == 'capture_failed'
    assert any('Inventoried SPT' in str(error) for error in observed_failures)
    assert collector == []


def test_stop_after_timeout_prevents_retry_or_capture(tmp_path, collector):
    page = MissingListPage()

    def cancel():
        if page.timed_out:
            raise driver.CaptureCancelled()

    with pytest.raises(driver.CaptureCancelled):
        driver.collect_details(page, run_fixture(), tmp_path, check_cancel=cancel)
    assert page.navigated == [LIST_URL]
    assert collector == []


@pytest.mark.parametrize('changed_url', [
    LIST_URL.replace(TAXPAYER, 'synthetic-other-taxpayer'),
    driver.ORIGIN + '/returnsheets/id-ID/auth-callback',
    'https://untrusted.invalid/returnsheets/id-ID/submitted-returnsheets/' + TAXPAYER,
    LIST_URL.replace('/submitted-', '/archived-'),
    LIST_URL + '?synthetic-unreviewed-query=1',
])
def test_changed_owner_during_missing_wait_is_not_hidden_by_retry(tmp_path, collector, monkeypatch, changed_url):
    original = driver.ListObserver.wait

    def redirected(self, after, timeout=45):
        self.page.url = changed_url
        return original(self, after, timeout)

    monkeypatch.setattr(driver.ListObserver, 'wait', redirected)
    page = MissingListPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL]
    assert not result['complete'] and collector == []


@pytest.mark.parametrize('changes', [{'successful': False}, {'status': 403}, {'status': 500}])
def test_unsuccessful_list_response_is_not_a_retryable_timeout(tmp_path, collector, changes, observed_failures):
    class FailedPage(SourcePage):
        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            self.emit_grid_response(response(**changes))

    page = FailedPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL]
    assert not result['complete'] and collector == []
    assert result['errors'][0]['message'] == 'capture_failed'
    assert any('unsuccessful' in str(error) for error in observed_failures)


@pytest.mark.parametrize('fault', ['foreign_request', 'extra_commit', 'pending_overflow'])
def test_changed_or_unbounded_document_requests_never_authorize_view(tmp_path, collector, fault, observed_failures):
    class ChangedPage(SourcePage):
        def goto(self, url, **kwargs):
            self.commit_navigation(url)
            if fault == 'extra_commit':
                self.replace_document()
            else:
                for _ in range(129 if fault == 'pending_overflow' else 1):
                    item = response()
                    item.request.frame = self.main_frame
                    if fault == 'foreign_request':
                        item.request.post_data_json['TaxpayerAggregateIdentifier'] = 'synthetic-other-taxpayer'
                    self.emit('request', item.request)
            self.emit_grid_response(response())

    page = ChangedPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL]
    assert not result['complete'] and collector == []
    assert result['errors'][0]['message'] == 'capture_failed'
    assert any('ownership' in str(error) for error in observed_failures)
    assert not any(page.listeners.values())


@pytest.mark.parametrize('failure', [RuntimeError('synthetic navigation failure'),
                                    driver.JsonSafetyError('synthetic binding contradiction')])
def test_other_restore_failure_is_not_retried(tmp_path, collector, failure):
    class FailedPage(SourcePage):
        def goto(self, url, **kwargs):
            self.navigated.append(url)
            raise failure

    page = FailedPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL]
    assert not result['complete'] and collector == []


@pytest.mark.parametrize('starts_during_retry', [False, True])
@pytest.mark.parametrize('finishes_after_commit', [False, True])
def test_late_old_document_request_cannot_satisfy_retry(tmp_path, collector, starts_during_retry, finishes_after_commit):
    class LatePage(MissingListPage):
        def __init__(self):
            super().__init__(recover=False)
            self.main_frame = self
            self.late = response()
            self.late.request.frame = self

        def goto(self, url, **kwargs):
            self.navigated.append(url)
            self.url = url
            if len(self.navigated) == 1:
                self.emit('framenavigated', self.main_frame)
                if not starts_during_retry:
                    self.emit('request', self.late.request)
            else:
                # The previous document can finish/start work before replacement.
                if starts_during_retry:
                    self.emit('request', self.late.request)
                if not finishes_after_commit:
                    self.emit('response', self.late)
                self.emit('framenavigated', self.main_frame)
                if finishes_after_commit:
                    self.emit('response', self.late)
                # No qualifying request is made by the replacement document.

    page = LatePage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL, LIST_URL]
    assert not result['complete'] and collector == []
    assert result['records'][0]['sections'] == []


@pytest.mark.parametrize('kind', ['html403', 'html500', 'unsuccessful_without_payload'])
@pytest.mark.parametrize('later_success', [False, True])
def test_owned_error_envelope_without_rows_does_not_retry(tmp_path, collector, kind, later_success, observed_failures):
    class ErrorPage(SourcePage):
        def goto(self, url, **kwargs):
            self.navigated.append(url)
            self.url = url
            self.main_frame = self
            self.emit('framenavigated', self.main_frame)
            failed = response()
            failed.request.frame = self
            self.emit('request', failed.request)
            if kind.startswith('html'):
                failed.status = int(kind[4:])
                failed.headers = {'content-type': 'text/html'}
                failed.json = lambda: (_ for _ in ()).throw(ValueError('not JSON'))
            else:
                failed.json = lambda: {'IsSuccessful': False, 'Payload': None}
            self.emit('response', failed)
            if later_success:
                self.emit_grid_response(response())

    page = ErrorPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL]
    assert not result['complete'] and collector == []
    assert result['errors'][0]['message'] == 'capture_failed'
    assert any('unsuccessful' in str(error) for error in observed_failures)
