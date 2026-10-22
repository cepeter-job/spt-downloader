"""Synthetic selected capture helpers; no collected tests or shared mutable test state."""
import inspect
import json
from types import SimpleNamespace
from spt_desktop import worker
from support_runs import fixture_run


def synthetic_browser(module,monkeypatch,state):
    class Manager:
        def __enter__(self):state['driver_started']=True;return object()
        def __exit__(self,*args):state['driver_closed']=True
    class Context:
        def close(self):state['browser_closed']=True
    monkeypatch.setattr(module,'playwright_factory',Manager)
    def authenticate(*args, **kwargs):
        state['browser_started'] = True
        return Context(), object()
    monkeypatch.setattr(module,'authenticate_owned',authenticate)


def selected_job(tmp_path, monkeypatch, selected_ids, *, overwrite=None, stop_on_choice=False, marker=None,
                 before_capture=None):
    assert 'requests' in inspect.signature(worker.run_job).parameters, 'Worker selection handshake is missing'
    state = {'captured': [], 'requests': []}
    synthetic_browser(worker, monkeypatch, state)
    run = fixture_run()
    run['inventory_complete'] = True
    if marker is not None:
        run['records'][2]['sections'][0]['fields'][0]['value'] = marker
    def inventory(page, npwp, year, basis, folder, **kwargs):
        # The real inventory collector persists this before asking for consent.
        (folder / 'inventory.json').write_text(json.dumps(run), encoding='utf-8')
        return run
    monkeypatch.setattr(worker, 'collect_inventory', inventory)
    stopped = False

    def request(kind, payload, percent):
        nonlocal stopped
        state['requests'].append(kind)
        if kind == 'selection':
            assert [record['record_id'] for record in payload['records']] == [
                'badan-normal', 'badan-amendment', '21-january', '21-february', 'unifikasi']
            stopped = stop_on_choice
            return {'selected_ids': selected_ids}
        assert kind == 'overwrite' and overwrite is not None
        assert payload['files']
        return {'overwrite': overwrite}

    def capture(page, data, folder, on_progress, check_cancel):
        check_cancel()
        if before_capture is not None:
            before_capture(data, events)
        state['captured'] = [record['record_id'] for record in data['records']]
        for ordinal, record in enumerate(data['records'], 1):
            record['capture_complete'] = True
            on_progress(data, ordinal)
        data['complete'] = True
        return data

    monkeypatch.setattr(worker, 'collect_details', capture)
    monkeypatch.setattr(worker, 'downloads_folder', lambda: tmp_path / 'Downloads')
    events = []
    status = worker.run_job('0000000000000001', '2025', tmp_path / 'workspace',
                            'selected-job', 'msedge', True, events.append, lambda: stopped,
                            requests=SimpleNamespace(request=request))
    return status, events, state, run
