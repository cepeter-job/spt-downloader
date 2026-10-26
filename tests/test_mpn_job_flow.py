"""Full jobs require MPN before browser close; limited/offline jobs stay explicit."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_mpn import scope_run
from support_runs import fixture_run
from support_selected_capture import synthetic_browser


def capture_result(run, *, complete=True):
    from coretax_mpn import require_mpn
    before = run['complete']
    run['complete'] = False
    value = require_mpn(run, 'dom')
    value.update(status='COMPLETE' if complete else 'PARTIAL', inventory_complete=complete,
                 details_complete=complete)
    run['complete'] = before and complete
    return run


@pytest.mark.parametrize('empty,mpn_complete', [(False, True), (True, True), (False, False)])
def test_worker_collects_required_mpn_with_open_browser_even_for_no_spt(tmp_path, monkeypatch, empty, mpn_complete):
    from spt_desktop import worker
    state = {}
    synthetic_browser(worker, monkeypatch, state)
    run = scope_run() if empty else fixture_run()
    run['sources'] = scope_run()['sources']
    run['inventory_complete'] = True
    calls = []
    def inventory(page, npwp, year, basis, folder, **kwargs):
        (folder / 'inventory.json').write_text(json.dumps(run), encoding='utf-8')
        return run
    monkeypatch.setattr(worker, 'collect_inventory', inventory)
    def details(page, data, folder, **kwargs):
        assert data['mpn']['required'] is True and data['mpn']['status'] == 'PENDING'
        calls.append('SPT')
        data['complete'] = True
        return data
    monkeypatch.setattr(worker, 'collect_details', details)
    def mpn(page, data, folder, **kwargs):
        assert not state.get('browser_closed') and not state.get('driver_closed')
        calls.append('MPN')
        kwargs['check_cancel']()
        kwargs['on_progress'](0, 0, 0)
        return capture_result(data, complete=mpn_complete)
    monkeypatch.setattr(worker, 'collect_mpn', mpn, raising=False)
    monkeypatch.setattr(worker, 'downloads_folder', lambda: tmp_path / 'Downloads')
    request = SimpleNamespace(request=lambda kind, payload, percent:
                              {'selected_ids': [record['record_id'] for record in payload['records']]})
    events = []
    result = worker.run_job(run['npwp'], 2025, tmp_path / 'root', 'synthetic-mpn-flow',
                            'msedge', True, events.append, lambda: False, requests=request)
    assert calls == ['SPT', 'MPN']
    assert result == (0 if mpn_complete else 2)
    assert state['browser_closed'] and state['driver_closed']
    assert events[-1]['status'] == ('COMPLETE' if mpn_complete else 'PARTIAL')
    assert (Path(events[-1]['output']) / 'MPN_2025.xlsx').is_file()
    assert any(event['stage'] == 'mpn' for event in events)
    if not mpn_complete:
        assert all(event['percent'] < 100 for event in events)


def test_stop_during_spt_never_starts_a_later_mpn_stage(tmp_path, monkeypatch):
    from spt_desktop import worker
    state = {}
    synthetic_browser(worker, monkeypatch, state)
    run = scope_run()
    monkeypatch.setattr(worker, 'collect_inventory', lambda *args, **kwargs: run)
    def stop(*args, **kwargs):
        raise worker.CaptureCancelled('Synthetic Stop')
    monkeypatch.setattr(worker, 'collect_details', stop)
    def never(*args, **kwargs):
        pytest.fail('MPN started after Stop')
    monkeypatch.setattr(worker, 'collect_mpn', never, raising=False)
    events = []
    result = worker.run_job(run['npwp'], 2025, tmp_path, 'synthetic-stop', 'msedge', True,
                            events.append, lambda: False, requests=object())
    assert result == 4 and events[-1]['status'] == 'CANCELLED'
    assert not any(event['stage'] == 'mpn' for event in events)


@pytest.mark.parametrize('inventory_only', [False, True])
def test_cli_live_full_job_adds_mpn_before_cleanup_but_inventory_only_does_not(tmp_path, monkeypatch, inventory_only):
    import coretax
    calls = []
    run = scope_run()
    page = SimpleNamespace(set_viewport_size=lambda _: None, is_closed=lambda: False,
                           close=lambda: calls.append('page-close'))
    context = SimpleNamespace(new_page=lambda: page, close=lambda: calls.append('context-close'))
    manager = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=lambda *a, **k: context))
    class Engine:
        def __enter__(self):
            return manager
        def __exit__(self, *args):
            pass
    monkeypatch.setattr(coretax, 'sync_playwright', Engine)
    monkeypatch.setattr(coretax, 'authenticate', lambda *args: None)
    monkeypatch.setattr(coretax, 'collect_inventory', lambda *a, **k: deepcopy(run))
    def details(page, data, folder, **kwargs):
        calls.append('SPT')
        data['complete'] = True
        return data
    monkeypatch.setattr(coretax, 'collect_details', details)
    def mpn(page, data, folder, **kwargs):
        assert 'page-close' not in calls and 'context-close' not in calls
        calls.append('MPN')
        return capture_result(data)
    monkeypatch.setattr(coretax, 'collect_mpn', mpn, raising=False)
    args = ['--npwp', run['npwp'], '--year', '2025', '--output', str(tmp_path / 'output'), '--non-interactive']
    result = coretax._main(args + (['--inventory-only'] if inventory_only else []))
    if inventory_only:
        assert result == 2 and 'SPT' not in calls and 'MPN' not in calls
        assert not (tmp_path / 'output' / 'MPN_2025.xlsx').exists()
    else:
        assert result == 0 and calls.index('SPT') < calls.index('MPN') < calls.index('page-close')
        assert (tmp_path / 'output' / 'MPN_2025.xlsx').is_file()


def test_offline_legacy_export_never_fetches_or_fabricates_mpn(tmp_path, monkeypatch):
    import coretax
    run = scope_run()
    source = tmp_path / 'source.json'
    source.write_text(json.dumps(run), encoding='utf-8')
    def never(*args, **kwargs):
        pytest.fail('Offline legacy export opened the browser')
    monkeypatch.setattr(coretax, 'sync_playwright', never)
    monkeypatch.setattr(coretax, 'collect_mpn', never, raising=False)
    assert coretax._main(['--from-json', str(source), '--output', str(tmp_path / 'offline')]) == 0
    assert not (tmp_path / 'offline' / 'MPN_2025.xlsx').exists()
