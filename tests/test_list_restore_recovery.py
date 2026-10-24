"""Bounded missing-list response recovery through the public detail collector."""
import pytest

import coretax_browser as driver
from support_browser_protocol import (
    DETAIL_URL, LIST_URL, TAXPAYER, SourcePage, response, run_fixture,
)


class MissingListPage(SourcePage):
    def __init__(self, *, recover=True, replay=None):
        super().__init__()
        self.recover, self.replay = recover, replay
        self.timed_out = False

    def goto(self, url, **kwargs):
        self.navigated.append(url)
        self.url = url
        if self.recover and len(self.navigated) == 2:
            self.emit('response', self.replay or response())


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


def test_missing_initial_list_response_retries_once_then_captures(tmp_path, collector):
    page = MissingListPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert result['complete'], result['errors']
    assert page.navigated == [LIST_URL, LIST_URL]
    assert collector == [DETAIL_URL]
    assert result['records'][0]['capture_complete']
    assert not page.listeners['response']


def test_second_missing_list_response_stays_partial_without_third_navigation(tmp_path, collector):
    page = MissingListPage(recover=False)
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL, LIST_URL]
    assert not result['complete'] and not result['records'][0]['capture_complete']
    assert result['records'][0]['sections'] == []
    assert len(result['errors']) == 1 and 'No verifiable' in result['errors'][0]['message']
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


def test_retry_response_still_requires_the_selected_record(tmp_path, collector):
    page = MissingListPage(replay=response([{'RecordId': 'synthetic-other-record'}]))
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL, LIST_URL]
    assert not result['complete']
    assert 'Inventoried SPT' in result['errors'][0]['message']
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


def test_unsuccessful_list_response_is_not_a_retryable_timeout(tmp_path, collector):
    class FailedPage(SourcePage):
        def goto(self, url, **kwargs):
            self.navigated.append(url)
            self.url = url
            self.emit('response', response(successful=False))

    page = FailedPage()
    result = driver.collect_details(page, run_fixture(), tmp_path)
    assert page.navigated == [LIST_URL]
    assert not result['complete'] and collector == []
    assert 'unsuccessful' in result['errors'][0]['message']


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
