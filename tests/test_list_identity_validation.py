"""Validation RPCs retain attempt custody and retire their acquisition budget."""
from greenlet import greenlet, getcurrent

import pytest

import coretax_browser as driver
from support_browser_protocol import LIST_URL, RECORD, SourcePage, response
from test_list_view_custody import deferred_page


class ValidationPage(SourcePage):
    def __init__(self):
        super().__init__()
        self.suspend_next = False
        self.tasks = []

    def evaluate_handle(self, script):
        handle = super().evaluate_handle(script)
        original = handle.evaluate
        def sample(source):
            same = original(source)
            if self.suspend_next:
                self.suspend_next = False
                getcurrent().parent.switch()
            return same
        handle.evaluate = sample
        return handle

    def notification(self):
        task = greenlet(lambda: self.emit('framenavigated', self.main_frame))
        self.tasks.append(task)
        task.switch()
        return task

    def goto(self, url, **kwargs):
        self.navigated.append(url)
        self.url = url
        self.document_token = object()
        self.notification()
        self.emit_grid_response(response())


@pytest.mark.parametrize('phase', ['initial', 'repeat'])
@pytest.mark.parametrize('action', ['reset', 'new-pending'])
def test_stale_validation_rpc_cannot_refuse_the_new_attempt(monkeypatch, phase, action):
    page = ValidationPage()
    observer = driver.ListObserver(page)
    monkeypatch.setattr(driver, 'wait_idle', lambda page: None)
    try:
        observer.begin_navigation(LIST_URL)
        page.suspend_next = phase == 'initial'
        page.goto(LIST_URL)
        if phase == 'repeat':
            page.suspend_next = True
            page.notification()
        old_task = page.tasks[-1]
        old_handle = page.document_handles[-1]
        assert not old_task.dead and observer._document is old_handle
        assert observer._binding_document is (phase == 'initial')
        observer.begin_navigation(LIST_URL)
        new_handle = None
        if action == 'new-pending':
            page.suspend_next = True
            page.goto(LIST_URL)
            new_handle = page.document_handles[-1]
            assert observer._binding_document and observer._document is new_handle
        old_task.switch()
        assert old_task.dead and old_handle.disposed
        assert observer.navigation_failed is False
        assert observer._document is new_handle
        assert observer._binding_document is (action == 'new-pending')
        if action == 'new-pending':
            page.tasks[-1].switch()
            assert observer.wait(1, timeout=1)['rows'] == [{'RecordId': RECORD}]
    finally:
        observer.close()
        for task in page.tasks:
            if not task.dead:
                task.switch()
        disposed_after_close = all(handle.disposed for handle in page.document_handles)
        for handle in page.document_handles:
            if not handle.disposed:
                handle.dispose()
    assert disposed_after_close and not any(page.listeners.values())


def test_timely_identity_does_not_shorten_the_existing_healthy_idle_wait(monkeypatch):
    page = deferred_page(monkeypatch, 'complete')
    def healthy_idle(target):
        assert target is page and page.elapsed == pytest.approx(0.1)
        page.elapsed += 1.1
    monkeypatch.setattr(driver, 'wait_idle', healthy_idle)
    observer = driver.ListObserver(page)
    try:
        observer.begin_navigation(LIST_URL)
        page.goto(LIST_URL)
        assert observer.wait(0, timeout=1)['rows'] == [{'RecordId': RECORD}]
        assert page.elapsed == pytest.approx(1.2) and not observer.navigation_failed
    finally:
        observer.close()
        page.drain()
    assert all(handle.disposed for handle in page.document_handles)


def test_absent_response_after_timely_identity_keeps_the_timeout_only_retry_category(monkeypatch):
    page = deferred_page(monkeypatch, 'complete')
    page.emit_grid_response = lambda item: None
    observer = driver.ListObserver(page)
    try:
        observer.begin_navigation(LIST_URL)
        page.goto(LIST_URL)
        with pytest.raises(driver.ListResponseTimeout):
            observer.wait(0, timeout=1)
        assert 1 <= page.elapsed <= 1.1 and not observer.navigation_failed
        assert page.acquisitions[-1].dead and observer._document is page.document_handles[-1]
    finally:
        observer.close()
        page.drain()
    assert all(handle.disposed for handle in page.document_handles)
