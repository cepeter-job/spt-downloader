"""Passive search diagnostics use synthetic Edge pages and network traffic only."""
from contextlib import contextmanager
import json

import pytest
from playwright.sync_api import TimeoutError as BrowserTimeout

import coretax_browser as driver
from support_isolated_browser import browser, isolated_context
from test_diagnostics import records
from test_json_inventory import inventory_browser

NPWP = '0000000000000001'
SECRET = 'SYNTHETIC_SEARCH_PRIVATE_VALUE'


@contextmanager
def search_page(browser, monkeypatch, *, status=403, failed=False, send=True,
                matched=False, distractions=False):
    # Shorten only the real negative locator waits, not fixture scheduling.
    from playwright.sync_api import Locator
    original_wait = Locator.wait_for

    def wait(locator, *args, **kwargs):
        if kwargs.get('timeout') == 45000:
            kwargs['timeout'] = 1000
        return original_wait(locator, *args, **kwargs)

    monkeypatch.setattr(Locator, 'wait_for', wait)
    with isolated_context(browser) as context:
        page = context.new_page()
        page.set_default_timeout(1000)
        metrics = {'queries': [], 'other': []}
        config = json.dumps({'status': status, 'send': send, 'matched': matched,
                             'distractions': distractions, 'secret': SECRET})
        html = '''<main class="main-content"><input id="ObjectPermitNumber">
        <table><tbody></tbody></table><iframe srcdoc="<script>
        onmessage=()=>fetch('/synthetic-frame').catch(()=>{});</script>"></iframe></main>
        <script>const config=''' + config + ''';
        document.querySelector('input').onkeydown=async e=>{
          if(e.key!=='Enter')return;
          window.searchStarted=true;
          if(config.distractions){
            document.querySelector('iframe').contentWindow.postMessage('go','*');
            await fetch('https://synthetic-other.invalid/synthetic-foreign').catch(()=>{});
          }
          if(config.send) await fetch('/synthetic-query?private='+config.secret,{
            method:'POST',headers:{'X-Synthetic-Private':config.secret},
            body:e.target.value+' '+config.secret}).catch(()=>{});
          if(config.matched){
            const row=document.createElement('tr');
            row.innerHTML='<td>0000000000000001</td><td>Synthetic fixture</td>';
            document.querySelector('tbody').append(row);
          }
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
            elif request.url.endswith(('/synthetic-frame', '/synthetic-foreign')):
                metrics['other'].append(request.url.rsplit('/', 1)[-1])
                route.fulfill(status=403, body=SECRET,
                              headers={'Access-Control-Allow-Origin': '*'})
            else:
                raise AssertionError('Unexpected synthetic request')

        context.route('**/*', route_handler)
        yield page, metrics


def search_events(root):
    return [r for r in records(root) if r['event'] == 'search.result']


@pytest.mark.parametrize('status,failed,send,counter', [
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
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(BrowserTimeout) as error:
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job')
            assert log.flush()
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
        if status in (403, 429) and send and not failed:
            assert str(status) in str(error.value)
        assert 'bot detected' not in str(error.value).lower()
        assert SECRET not in json.dumps(records(tmp_path))
        assert NPWP not in json.dumps(records(tmp_path))
        assert NPWP not in str(error.value)
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
        assert sorted(metrics['other']) == ['synthetic-foreign', 'synthetic-frame']


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
        def stop():
            if page.evaluate('Boolean(window.searchStarted)'):
                raise driver.CaptureCancelled('SYNTHETIC STOP')
        with driver.diagnostics.session(tmp_path, 'worker') as log:
            with pytest.raises(driver.CaptureCancelled):
                driver.collect_inventory(page, NPWP, 2025, 'period', tmp_path / 'job', check_cancel=stop)
            assert log.flush()
        event, = search_events(tmp_path)
        assert event['search_result'] == 'cancelled'
        assert event['search_table'] == 'unavailable'
        assert not (tmp_path / 'job' / 'run.json').exists()
