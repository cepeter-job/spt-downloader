"""Production capture failures retain safe proof, never arbitrary error text."""
import json
import threading

import pytest

import coretax_browser as driver
from test_diagnostics import records as diagnostic_records
from test_financial_capture import browser as browser, routed as routed, DETAIL


@pytest.mark.parametrize(('kind', 'message', 'want_type', 'want_message'), [
    (RuntimeError, 'SYNTHETIC_PRIVATE_FAILURE_BODY', 'RuntimeError', 'capture_failed'),
    (type('SYNTHETIC_PRIVATE_CLASS', (Exception,), {}), 'SYNTHETIC_PRIVATE_FAILURE_BODY',
     'Error', 'capture_failed'),
    (driver.PlaywrightTimeoutError, 'SYNTHETIC_PRIVATE_FAILURE_BODY',
     'TimeoutError', 'capture_timeout'),
])
def test_actual_table_failure_keeps_safe_proof_and_recovers_later_panel(
        routed, tmp_path, monkeypatch, kind, message, want_type, want_message):
    page, requests = routed(control='')

    def failed_table(*args, **kwargs):
        raise kind(message)

    monkeypatch.setattr(driver, 'capture_table', failed_table)
    with driver.diagnostics.session(tmp_path / 'logs', 'worker') as log:
        result = driver.capture_detail(page)
        assert log.flush()

    assert result['capture_complete'] is False
    assert [s['name'] for s in result['sections']] == ['Induk', 'L1D']
    assert result['sections'][0]['tables'] == []
    assert result['sections'][1]['fields']
    assert result['errors'] == [{'object': 'Induk/table 1', 'message': want_message}]
    assert requests == [('GET', DETAIL)]
    partial = [r for r in diagnostic_records(tmp_path / 'logs') if r['event'] == 'capture.partial']
    assert len(partial) == 1
    assert partial[0]['error']['type'] == want_type
    assert any(f['file'] == 'coretax_browser.py' for f in partial[0]['error']['frames'])
    serialized = json.dumps([result['errors'], diagnostic_records(tmp_path / 'logs')])
    assert message not in serialized and 'SYNTHETIC_PRIVATE_CLASS' not in serialized


@pytest.mark.parametrize('overlay_kind', ['target', 'foreign', 'blockui'])
def test_first_reset_loading_timeout_records_initial_loading_without_changing_partial(
        routed, tmp_path, monkeypatch, overlay_kind):
    from playwright.sync_api import Locator
    from support_browser_protocol import capture_failures

    page, requests = routed(control='')
    secret = 'SYNTHETIC_PRIVATE_INITIAL_LOADING'
    page.evaluate('''secret => {
        window.syntheticFirstClicks = 0;
        const table = document.querySelector('#induk table');
        const owner = document.createElement('p-table');
        table.replaceWith(owner);
        owner.innerHTML = '<div class="p-datatable"><div class="p-paginator">' +
            '<button class="p-paginator-first" type="button">First</button>' +
            '<span class="p-paginator-page p-highlight">2</span></div>' +
            '<div class="p-datatable-loading-overlay" hidden ' +
            'style="width:20px;height:20px"></div></div>';
        owner.firstElementChild.prepend(table);
        const overlay = owner.querySelector('.p-datatable-loading-overlay');
        overlay.setAttribute('data-private', secret);
        table.querySelector('td').textContent = secret;
        owner.querySelector('button').onclick = event => {
            window.syntheticFirstClicks++;
            event.currentTarget.disabled = true;
            owner.querySelector('.p-highlight').textContent = '1';
            overlay.hidden = false;
        };
    }''', secret)
    if overlay_kind != 'target':
        page.evaluate('''kind => {
            const owner = document.querySelector('#induk p-table');
            const targetOverlay = owner.querySelector('.p-datatable-loading-overlay');
            const container = document.createElement(kind === 'blockui' ? 'div' : 'p-table');
            if(kind === 'blockui') {
                container.className = 'p-blockui';
                container.style.cssText = 'width:20px;height:20px';
                container.hidden = true;
            } else {
                container.innerHTML = '<div class="p-datatable-loading-overlay" hidden ' +
                    'style="width:20px;height:20px"></div>';
            }
            // The sibling/global mask stays within Induk's hiding boundary, so
            // the unmodified later-panel recovery can continue after PARTIAL.
            document.querySelector('#induk').appendChild(container);
            const otherOverlay = kind === 'blockui' ? container :
                container.querySelector('.p-datatable-loading-overlay');
            const button = owner.querySelector('button');
            const originalClick = button.onclick;
            button.onclick = event => {
                originalClick(event);
                targetOverlay.hidden = true;
                otherOverlay.hidden = false;
            };
        }''', overlay_kind)
    timeout = driver.PlaywrightTimeoutError(secret)
    failures = capture_failures(monkeypatch)  # Delegates to the real recorder.
    original_wait = Locator.wait_for
    loading_waits = []

    def controlled_loading_timeout(locator, *args, **kwargs):
        # Keep real wait_idle and the inspected click; avoid a 45-second sleep.
        # The overlay becomes visible only after First, and hides with Induk
        # when later-panel recovery runs. No size or request race is modelled.
        if (locator.page is page and kwargs.get('state') == 'hidden'
                and kwargs.get('timeout') == 45000
                and page.locator('.p-datatable-loading-overlay:visible,.p-blockui:visible').count()):
            loading_waits.append(page.evaluate('window.syntheticFirstClicks'))
            raise timeout
        return original_wait(locator, *args, **kwargs)

    monkeypatch.setattr(Locator, 'wait_for', controlled_loading_timeout)
    # A broken DevTools attach would wait before responding. The diagnostics
    # must never enter this path, regardless of the visible overlay kind.
    cdp_calls = []
    def blocking_cdp_session(*args, **kwargs):
        cdp_calls.append(1)
        threading.Event().wait(1.25)
        raise RuntimeError('SYNTHETIC_PRIVATE_CDP_STALL')
    monkeypatch.setattr(page.context, 'new_cdp_session', blocking_cdp_session)
    root = tmp_path / 'diagnostics'
    with driver.diagnostics.session(root, 'worker') as log:
        result = driver.capture_detail(page)
        assert log.flush()

    # Preconditions must pass before the feature RED: the real initial wait
    # raises the original exception, no table snapshot is accepted, recovery
    # reaches the next panel, and the dispatched First action is never retried.
    assert loading_waits == [1]
    assert cdp_calls == [], 'Timeout diagnostics must not attach blocking DevTools sessions'
    assert len(failures) == 1 and failures[0] is timeout
    assert page.evaluate('window.syntheticFirstClicks') == 1
    assert result['capture_complete'] is False
    assert [section['name'] for section in result['sections']] == ['Induk', 'L1D']
    assert result['sections'][0]['tables'] == []
    assert result['sections'][1]['fields']
    assert result['errors'] == [{'object': 'Induk/table 1', 'message': 'capture_timeout'}]
    assert requests == [('GET', DETAIL)]
    rows = diagnostic_records(root)
    partial = [row for row in rows if row['event'] == 'capture.partial']
    assert len(partial) == 1 and partial[0]['error']['type'] == 'TimeoutError'
    assert not any(row['event'] == 'table.page_timing' for row in rows)
    assert secret not in json.dumps([result['errors'], rows])

    # Diagnostic-feature RED, not evidence of the live loading sub-cause.
    initial = [row for row in rows if row['event'] == 'table.initial_loading'
               and row.get('table_initial_stage') == 'first_idle_timeout']
    assert len(initial) == 1, 'Missing initial-loading diagnostic after First wait timeout'
    event = initial[0]
    assert event['table_initial_stage'] == 'first_idle_timeout'
    assert event['table_loading_scope'] == 'unavailable'
    assert event['table_loading_first_match'] == 'unavailable'
    assert event['table_owner_state'] == 'unavailable'
    assert event['form_ordinal'] == event['table_ordinal'] == 1
    assert event['error']['type'] == 'TimeoutError'




@pytest.mark.parametrize('level', ['INFO', 'OFF'])
def test_initial_loading_diagnostics_use_unchanged_owner_selector(
        routed, tmp_path, monkeypatch, level):
    from playwright.sync_api import ElementHandle

    page, requests = routed(control='')
    original = ElementHandle.evaluate_handle
    expressions = []
    expected = "e=>e.closest('p-table')||e.closest('.p-datatable')||e.parentElement"

    def capture_owner_expression(handle, expression, *args, **kwargs):
        if isinstance(expression, str) and "closest('p-table')" in expression:
            expressions.append(expression)
        return original(handle, expression, *args, **kwargs)

    monkeypatch.setattr(ElementHandle, 'evaluate_handle', capture_owner_expression)
    with driver.diagnostics.session(tmp_path / level, 'worker', level=level) as log:
        result = driver.capture_detail(page)
        # OFF deliberately has no background logger thread to flush.
        assert log.flush() is (level != 'OFF')
    assert result['capture_complete'] and requests == [('GET', DETAIL)]
    assert expressions and all(script == expected for script in expressions)
    assert page.evaluate(
        "Object.getOwnPropertyNames(window).every(key => !key.startsWith('__spt_table_initial_'))")



@pytest.mark.parametrize('level', ['INFO', 'OFF'])
def test_owned_table_handles_are_disposed_once(routed, tmp_path, monkeypatch, level):
    page, requests = routed(control='')
    original = driver._dispose_table_handle
    disposed = []

    def tracked_dispose(handle):
        disposed.append(handle)
        return original(handle)

    monkeypatch.setattr(driver, '_dispose_table_handle', tracked_dispose)
    with driver.diagnostics.session(tmp_path / level, 'worker', level=level) as log:
        result = driver.capture_detail(page)
        # OFF deliberately has no background logger thread to flush.
        assert log.flush() is (level != 'OFF')
    assert result['capture_complete'] and requests == [('GET', DETAIL)]
    assert disposed
    assert len({id(handle) for handle in disposed}) == len(disposed)



def test_partial_initial_loading_listener_registration_is_cleaned():
    class Emitter:
        def __init__(self):
            self.listeners = {}
            self.removed = []

        def on(self, event, callback):
            if event == 'requestfinished':
                raise RuntimeError('SYNTHETIC_LISTENER_FAILURE')
            self.listeners[event] = callback

        def remove_listener(self, event, callback):
            assert self.listeners.pop(event) is callback
            self.removed.append(event)

    page = Emitter()
    observer = driver._InitialLoadingDiagnostics(page, 1)
    assert observer.overflow
    assert tuple(page.listeners) == ('request',)
    observer.close()
    assert page.listeners == {} and page.removed == ['request']
    assert observer.requests == {}



def test_initial_loading_extra_observers_are_disabled_with_logging_off(
        routed, tmp_path, monkeypatch):
    page, requests = routed(control='')

    def forbidden(*args, **kwargs):
        pytest.fail('Diagnostics OFF installed an extra loading observer')

    monkeypatch.setattr(driver, '_InitialLoadingDiagnostics', forbidden)
    with driver.diagnostics.session(tmp_path / 'off', 'worker', level='OFF'):
        result = driver.capture_detail(page)
    assert result['capture_complete'] and requests == [('GET', DETAIL)]



def test_stop_from_actual_table_capture_is_not_demoted_to_partial(routed, tmp_path, monkeypatch):
    page, requests = routed(control='')

    def cancelled(*args, **kwargs):
        raise driver.CaptureCancelled('SYNTHETIC_STOP')

    monkeypatch.setattr(driver, 'capture_table', cancelled)
    with driver.diagnostics.session(tmp_path / 'logs', 'worker') as log:
        with pytest.raises(driver.CaptureCancelled):
            driver.capture_detail(page)
        assert log.flush()
    assert not any(r['event'] == 'capture.partial' for r in diagnostic_records(tmp_path / 'logs'))
    assert requests == [('GET', DETAIL)]


@pytest.mark.parametrize('body', ['{', 'SYNTHETIC_NON_JSON_BODY'])
def test_real_unreadable_request_body_cannot_establish_grid_custody(routed, body):
    page, _ = routed(control='')
    endpoint = driver.ORIGIN + '/returnsheet/api/returnsheets/list'
    page.route(endpoint, lambda route: route.fulfill(body='{}', content_type='application/json'))
    with page.expect_request(endpoint) as observed:
        page.evaluate('''([url, body]) => fetch(url, {method:'POST',
            headers:{'Content-Type':'application/json'},body}).then(reply=>reply.text())''',
            [endpoint, body])
    observer = driver.ListObserver.__new__(driver.ListObserver)
    observer.page = page
    observer.navigation_source = None
    assert observer._grid_request(observed.value, endpoint) is None
