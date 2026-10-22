"""Passive search diagnostics use synthetic Edge pages and network traffic only."""
from contextlib import contextmanager
import json
import time

import pytest
from playwright.sync_api import TimeoutError as BrowserTimeout

import coretax_browser as driver
from support_isolated_browser import browser, isolated_context
from test_diagnostics import records
from test_json_inventory import synthetic_listing_browser as inventory_browser

NPWP = '0000000000000001'
SECRET = 'SYNTHETIC_SEARCH_PRIVATE_VALUE'


@contextmanager
def search_page(browser, monkeypatch, *, status=403, failed=False, send=True,
                matched=False, distractions=False, row_mode=None, storm=1):
    # Shorten only the real negative locator waits, not fixture scheduling.
    from playwright.sync_api import Locator
    original_wait = Locator.wait_for

    def wait(locator, *args, **kwargs):
        if kwargs.get('timeout') == 45000:
            kwargs['timeout'] = 1000
        return original_wait(locator, *args, **kwargs)

    monkeypatch.setattr(Locator, 'wait_for', wait)
    monkeypatch.setattr(driver, 'SEARCH_RESULT_TIMEOUT_MS', 1000, raising=False)
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_default_timeout(1000)
        metrics = {'queries': [], 'other': [], 'before_route': None}
        config = json.dumps({'status': status, 'send': send, 'matched': matched,
                             'distractions': distractions, 'secret': SECRET,
                             'rowMode': row_mode, 'storm': storm})
        html = '''<main class="main-content"><input id="ObjectPermitNumber">
        <table><tbody></tbody></table><iframe></iframe></main>
        <script>const config=''' + config + ''';
        const child=document.querySelector('iframe');
        const childReady=new Promise(resolve=>addEventListener('message',e=>{
          if(e.source===child.contentWindow&&e.data==='synthetic-ready')resolve();
        }));
        child.srcdoc="<script>onmessage=async()=>{await fetch('/synthetic-frame');parent.postMessage('synthetic-done','*')};parent.postMessage('synthetic-ready','*');<\\/script>";
        const before=config.distractions?fetch('/synthetic-before'):Promise.resolve();
        document.querySelector('input').onkeydown=async e=>{
          if(e.key!=='Enter')return;
          window.searchStarted=true;
          if(config.distractions){
            await before;await childReady;
            const done=new Promise(resolve=>addEventListener('message',e=>{
              if(e.source===child.contentWindow&&e.data==='synthetic-done')resolve();
            }));
            child.contentWindow.postMessage('go','*');await done;
            await fetch('https://synthetic-other.invalid/synthetic-foreign').catch(()=>{});
            await new Promise(resolve=>{const img=new Image();img.onload=img.onerror=resolve;
              img.src='/synthetic-image';document.body.append(img);});
          }
          if(config.send) for(let i=0;i<config.storm;i++) await fetch('/synthetic-query?private='+config.secret,{
            method:'POST',headers:{'X-Synthetic-Private':config.secret},
            body:e.target.value+' '+config.secret}).catch(()=>{});
          if(config.matched||config.rowMode){
            for(let i=0;i<(config.rowMode==='duplicate'?2:1);i++){
            const row=document.createElement('tr');
            row.innerHTML='<td>'+(config.rowMode==='substring'?'prefix':'')+'0000000000000001</td><td>Synthetic fixture</td>';
            if(config.rowMode){const cell=row.insertCell(),button=document.createElement('button');
              button.textContent='Pilih';button.onclick=()=>window.syntheticSelections=(window.syntheticSelections||0)+1;cell.append(button);}
            document.querySelector('tbody').append(row);
            }
          }
          window.searchDone=true;
        };</script>'''

        def route_handler(route):
            request = route.request
            if request.url == driver.SEARCH_URL:
                route.fulfill(body=html, content_type='text/html')
            elif '/synthetic-query?' in request.url:
                metrics['queries'].append({'body': request.post_data,
                                           'headers': request.all_headers()})
                if failed:
                    route.abort('failed')
                else:
                    route.fulfill(status=status, body=SECRET,
                                  content_type='text/plain')
            elif request.url.endswith('/synthetic-before'):
                metrics['other'].append('synthetic-before')
                metrics['before_route'] = route
            elif request.url.endswith(('/synthetic-frame', '/synthetic-foreign', '/synthetic-image')):
                metrics['other'].append(request.url.rsplit('/', 1)[-1])
                route.fulfill(status=403, body=SECRET,
                              headers={'Access-Control-Allow-Origin': '*'})
            else:
                raise AssertionError('Unexpected synthetic request')

        context.route('**/*', route_handler)
        original_fill, original_press = Locator.fill, Locator.press

        def fill(locator, *args, **kwargs):
            result = original_fill(locator, *args, **kwargs)
            if distractions:
                deadline = time.monotonic() + 10
                while metrics['before_route'] is None and time.monotonic() < deadline:
                    page.wait_for_timeout(20)
                assert metrics['before_route'] is not None
            return result

        def press(locator, *args, **kwargs):
            result = original_press(locator, *args, **kwargs)
            if distractions:
                metrics['before_route'].fulfill(status=401, body=SECRET)
            if storm > 1:
                page.wait_for_function('window.searchDone === true', timeout=10000)
            return result

        monkeypatch.setattr(Locator, 'fill', fill)
        monkeypatch.setattr(Locator, 'press', press)
        yield page, metrics


def search_events(root):
    return [r for r in records(root) if r['event'] == 'search.result']


def track_listeners(page, monkeypatch):
    listeners = []
    original_on, original_remove = page.on, page.remove_listener

    def on(event, listener):
        result = original_on(event, listener)
        listeners.append((event, listener))
        return result

    def remove(event, listener):
        result = original_remove(event, listener)
        listeners.remove((event, listener))
        return result

    monkeypatch.setattr(page, 'on', on)
    monkeypatch.setattr(page, 'remove_listener', remove)
    return listeners


@pytest.mark.parametrize('status,failed,send,counter', [
    (401, False, True, 'search_http_401'),
    (403, False, True, 'search_http_403'),
    (429, False, True, 'search_http_429'),
    (500, False, True, 'search_http_5xx'),
    (200, False, True, 'search_http_2xx'),
    (200, True, True, 'search_failed'),
    (200, False, False, None),
])
def test_search_timeout_reports_observed_traffic_without_private_values(
        browser, monkeypatch, tmp_path, status, failed, send, counter):
    with search_page(browser, monkeypatch, status=status, failed=failed, send=send) as (page, metrics):
        listeners = track_listeners(page, monkeypatch)
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(BrowserTimeout) as error:
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
            assert listeners == []
            before = search_events(tmp_path)
            page.route('**/synthetic-after', lambda route: route.fulfill(status=429, body=SECRET))
            page.evaluate("async () => (await fetch('/synthetic-after')).status")
            assert log.flush()
            assert search_events(tmp_path) == before
        events = search_events(tmp_path)
        assert len(events) == 1
        event = events[0]
        assert event['search_result'] == 'timeout'
        assert event['search_observation'] == 'complete'
        assert event['search_table'] == 'empty'
        assert event['search_requests'] == int(send)
        assert event['search_responses'] == int(send and not failed)
        assert event['search_failed'] == int(failed)
        assert 0 <= event['duration_ms'] < 15000
        if counter:
            assert event[counter] == 1
        if status in (401, 403, 429) and send and not failed:
            assert str(status) in str(error.value)
        assert 'bot detected' not in str(error.value).lower()
        assert SECRET not in json.dumps(records(tmp_path))
        assert NPWP not in json.dumps(records(tmp_path))
        assert NPWP not in str(error.value)
        assert SECRET not in str(error.value)
        assert len(metrics['queries']) == int(send)
        assert not metrics['other']
        if send:
            request = metrics['queries'][0]
            assert request['body'] == NPWP + ' ' + SECRET
            assert request['headers']['x-synthetic-private'] == SECRET
            assert request['headers']['user-agent'] == page.evaluate('navigator.userAgent')


def test_search_traffic_excludes_other_origins_and_child_frames(browser, monkeypatch, tmp_path):
    with search_page(browser, monkeypatch, distractions=True) as (page, metrics):
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(BrowserTimeout):
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
        event, = search_events(tmp_path)
        assert event['search_requests'] == event['search_responses'] == event['search_http_403'] == 1
        assert event.get('search_http_401', 0) == 0
        assert sorted(metrics['other']) == ['synthetic-before', 'synthetic-foreign', 'synthetic-frame', 'synthetic-image']


def test_matching_row_is_not_rejected_by_unattributed_403(browser, monkeypatch, tmp_path):
    with search_page(browser, monkeypatch, matched=True) as (page, metrics):
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            # The intentionally absent Pilih control stops this fixture after
            # exact row verification, outside the observed search window.
            with pytest.raises(BrowserTimeout):
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
        event, = search_events(tmp_path)
        assert event['search_result'] == 'matched'
        assert event['search_table'] == 'rows_present'
        assert event['search_http_403'] == 1
        assert page.locator('input').input_value() == NPWP
        assert len(metrics['queries']) == 1


def test_successful_inventory_preserves_search_scope_and_removes_observers(browser, monkeypatch, tmp_path):
    with inventory_browser(browser, monkeypatch, year_catalog=True) as (page, metrics):
        # Keep Playwright real; observe our ownership of its public listeners.
        listeners = track_listeners(page, monkeypatch)
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            run = driver.collect_inventory(page, NPWP, 2024, 'period', tmp_path / 'job')
            assert run['inventory_complete'] is True
            before = search_events(tmp_path) if log.flush() else []
            assert len(before) == 1
            assert before[0]['search_result'] == 'matched'
            assert before[0]['search_requests'] == before[0]['search_responses'] == 0
            assert metrics['unregistered_requests'] == 0
            assert listeners == []
            # Emit a real later browser request while diagnostics remain open.
            page.route('**/synthetic-after', lambda route: route.fulfill(status=429, body=SECRET))
            page.evaluate("async () => (await fetch('/synthetic-after')).status")
            assert log.flush()
            assert search_events(tmp_path) == before


def test_search_stop_propagates_and_records_no_dom_snapshot(browser, monkeypatch, tmp_path):
    with search_page(browser, monkeypatch) as (page, metrics):
        from playwright.sync_api import Locator
        listeners = track_listeners(page, monkeypatch)
        stopped, snapshots = False, []
        original_evaluate = Locator.evaluate

        def evaluate(locator, *args, **kwargs):
            if stopped:
                snapshots.append(True)
            return original_evaluate(locator, *args, **kwargs)

        monkeypatch.setattr(Locator, 'evaluate', evaluate)
        def stop():
            nonlocal stopped
            if page.evaluate('Boolean(window.searchStarted)'):
                stopped = True
                raise driver.CaptureCancelled('SYNTHETIC STOP')
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(driver.CaptureCancelled):
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job', check_cancel=stop)
            assert log.flush()
            assert listeners == [] and snapshots == []
        event, = search_events(tmp_path)
        assert event['search_result'] == 'cancelled'
        assert event['search_table'] == 'unavailable'
        assert not (tmp_path / 'job' / 'run.json').exists()


@pytest.mark.parametrize('row_mode', ['substring', 'duplicate'])
def test_search_does_not_certify_nonunique_or_nonliteral_rows(
        browser, monkeypatch, tmp_path, row_mode):
    with search_page(browser, monkeypatch, row_mode=row_mode) as (page, metrics):
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(RuntimeError):
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
        event, = search_events(tmp_path)
        assert event['search_result'] == 'error'
        assert page.evaluate('window.syntheticSelections || 0') == 0
        assert not (tmp_path / 'job' / 'run.json').exists()


def test_search_request_storm_reports_bounded_lower_counts(browser, monkeypatch, tmp_path):
    with search_page(browser, monkeypatch, status=200, storm=130) as (page, metrics):
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(BrowserTimeout):
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
        event, = search_events(tmp_path)
        assert len(metrics['queries']) == 130
        assert event['search_observation'] == 'limited'
        assert event['search_requests'] == event['search_responses'] == event['search_http_2xx'] == 128
        assert SECRET not in json.dumps(records(tmp_path))


def test_search_observer_failure_is_unavailable_and_cleans_partial_registration(
        browser, monkeypatch, tmp_path):
    with search_page(browser, monkeypatch) as (page, metrics):
        listeners = track_listeners(page, monkeypatch)
        original_on = page.on

        def on(event, listener):
            if event == 'requestfailed':
                raise RuntimeError(SECRET)
            return original_on(event, listener)

        monkeypatch.setattr(page, 'on', on)
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(BrowserTimeout) as error:
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
            assert listeners == []
        event, = search_events(tmp_path)
        assert event['search_observation'] == 'unavailable'
        assert 'search_requests' not in event and 'search_responses' not in event
        assert SECRET not in str(error.value) and SECRET not in json.dumps(records(tmp_path))


def worker_failure(error, monkeypatch, root):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from spt_desktop import worker

    closed, emitted = [], []
    monkeypatch.setattr(worker, 'playwright_factory', lambda: nullcontext(object()))
    context = SimpleNamespace(close=lambda: closed.append(True))
    monkeypatch.setattr(worker, 'authenticate_owned', lambda *args, **kwargs: (context, object()))

    def collect(*args, **kwargs):
        raise error

    monkeypatch.setattr(worker, 'collect_inventory', collect)
    result = worker.run_job(NPWP, 2025, root, 'synthetic-search-worker',
                            'msedge', False, emitted.append, lambda: False)
    assert result == 1 and closed == [True]
    assert emitted[-1]['status'] == 'ERROR' and emitted[-1]['percent'] < 100
    assert not list(root.rglob('*.xlsx')) and not list(root.rglob('run.json'))
    return emitted


def test_desktop_receives_only_the_owned_safe_search_hint(browser, monkeypatch, tmp_path):
    with search_page(browser, monkeypatch) as (page, metrics):
        with pytest.raises(BrowserTimeout) as captured:
            driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'capture')
        error = captured.value
        # Even arbitrary exception args must never become the worker UI message.
        error.args = (SECRET + ' ' + NPWP,)
        monkeypatch.setattr(type(error), '__str__', lambda self: SECRET + ' ' + NPWP)
        emitted = worker_failure(error, monkeypatch, tmp_path / 'worker')
        assert '403' in emitted[-1]['message']
        assert SECRET not in json.dumps(emitted) and NPWP not in json.dumps(emitted)


def test_owned_search_hint_validates_reason_and_flags_without_coercion():
    assert hasattr(driver, 'TaxpayerSearchTimeout'), 'Owned private-safe search timeout is missing'

    class Untrusted:
        def __str__(self):
            raise AssertionError('Public search hints must not stringify arbitrary input')

        def __bool__(self):
            raise AssertionError('Public search flags must not coerce arbitrary input')

    error = driver.TaxpayerSearchTimeout(Untrusted(), limited=Untrusted())
    error.args = (SECRET,)
    assert SECRET not in error.public_message
    assert 'HTTP' not in error.public_message
    assert 'Pengamatan terbatas' not in error.public_message
    assert SECRET not in driver.TaxpayerSearchTimeout(SECRET).public_message


def test_desktop_keeps_arbitrary_browser_errors_generic(monkeypatch, tmp_path):
    emitted = worker_failure(BrowserTimeout(SECRET + ' ' + NPWP), monkeypatch, tmp_path)
    assert SECRET not in json.dumps(emitted) and NPWP not in json.dumps(emitted)
    assert '403' not in emitted[-1]['message']
