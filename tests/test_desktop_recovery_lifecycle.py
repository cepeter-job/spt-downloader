"""Cancellation durability uses synthetic captures and real local export I/O."""
from copy import deepcopy
import errno
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import coretax
import coretax_browser
from spt_desktop import worker
from support_runs import fixture_run
from support_selected_capture import synthetic_browser


def _cancelled_capture(tmp_path, monkeypatch, fault):
    root = tmp_path / 'workspace'
    folder = root / 'jobs' / 'synthetic-cancel'
    state = {'armed': False, 'fault_seen': False}
    synthetic_browser(worker, monkeypatch, state)
    run = fixture_run()
    run['records'] = run['records'][2:3]
    run['inventory_complete'] = True

    def inventory(*args, **kwargs):
        (folder / 'inventory.json').write_text(json.dumps(run), encoding='utf-8')
        return deepcopy(run)

    def capture(page, current, destination, **kwargs):
        current['complete'] = False
        checkpoint = destination / 'returns' / '0001.json'
        checkpoint.parent.mkdir()
        checkpoint.write_text(json.dumps(current['records'][0]), encoding='utf-8')
        (destination / 'run.json').write_text(json.dumps(current), encoding='utf-8')
        state['aggregate'] = (destination / 'run.json').read_bytes()
        state['detail'] = checkpoint.read_bytes()
        state['armed'] = True
        raise worker.CaptureCancelled('Synthetic Stop after a durable detail')

    original_open = Path.open
    original_replace = coretax_browser.os.replace

    class BrokenWrite:
        def __init__(self, stream):
            self.stream = stream

        def __enter__(self):
            self.stream.__enter__()
            return self

        def __exit__(self, *args):
            return self.stream.__exit__(*args)

        def __getattr__(self, name):
            return getattr(self.stream, name)

        def write(self, value):
            state['fault_seen'] = True
            self.stream.write(value[:17])
            self.stream.flush()
            raise OSError(errno.ENOSPC, 'SYNTHETIC PRIVATE STORAGE FAILURE')

    def interrupted_open(path, mode='r', *args, **kwargs):
        stream = original_open(path, mode, *args, **kwargs)
        aggregate_write = (path.parent == folder and
                           (path.name == 'run.json' or
                            path.name.startswith('run.json.') and path.name.endswith('.tmp')))
        if state['armed'] and fault == 'partial_write' and aggregate_write and any(x in mode for x in 'wax'):
            return BrokenWrite(stream)
        return stream

    def interrupted_replace(source, target):
        if state['armed'] and fault == 'replace' and Path(target) == folder / 'run.json':
            state['fault_seen'] = True
            raise PermissionError('SYNTHETIC PRIVATE REPLACEMENT FAILURE')
        return original_replace(source, target)

    monkeypatch.setattr(worker, 'collect_inventory', inventory)
    monkeypatch.setattr(worker, 'collect_details', capture)
    monkeypatch.setattr(worker, 'downloads_folder', lambda: tmp_path / 'Downloads')
    monkeypatch.setattr(Path, 'open', interrupted_open)
    monkeypatch.setattr(coretax_browser.os, 'replace', interrupted_replace)
    events = []
    reply = SimpleNamespace(request=lambda kind, payload, percent: {
        'selected_ids': [record['record_id'] for record in payload['records']]})
    try:
        code = worker.run_job('0000000000000001', '2025', root, 'synthetic-cancel',
                              'msedge', True, events.append, lambda: False, requests=reply)
    except OSError:
        pytest.fail('Stop must retain its terminal result when checkpoint persistence fails')
    finally:
        state['armed'] = False
    return folder, code, events, state


@pytest.mark.parametrize('fault', ['partial_write', 'replace'])
def test_cancel_checkpoint_failure_preserves_previous_aggregate_and_terminal(tmp_path, monkeypatch, fault):
    folder, code, events, state = _cancelled_capture(tmp_path, monkeypatch, fault)

    assert state['fault_seen'], 'The cancellation checkpoint did not cross the injected write boundary'
    assert code == 4
    terminal = [event for event in events if event['type'] == 'terminal']
    assert len(terminal) == 1 and terminal[0]['status'] == 'CANCELLED'
    assert terminal[0]['percent'] < 100 and terminal[0]['output'] is None
    assert 'SYNTHETIC PRIVATE' not in json.dumps(events)
    assert state['browser_closed'] and state['driver_closed']
    assert (folder / 'run.json').read_bytes() == state['aggregate']
    assert json.loads(state['aggregate'])['complete'] is False
    assert (folder / 'returns' / '0001.json').read_bytes() == state['detail']
    assert not list(folder.glob('run.json.*.tmp'))
    assert not (tmp_path / 'Downloads').exists()

    rebuilt = tmp_path / 'recovered-copy'
    assert coretax._main(['--from-json', str(folder / 'run.json'), '--output', str(rebuilt)]) == 2
    saved = json.loads((rebuilt / 'run.json').read_text(encoding='utf-8'))
    coretax.verify_outputs(saved, rebuilt)
    assert (folder / 'run.json').read_bytes() == state['aggregate']


def test_successful_cancel_checkpoint_is_partial_and_keeps_detail_bytes(tmp_path, monkeypatch):
    folder, code, events, state = _cancelled_capture(tmp_path, monkeypatch, None)

    assert code == 4 and events[-1]['status'] == 'CANCELLED'
    saved = json.loads((folder / 'run.json').read_text(encoding='utf-8'))
    assert saved['complete'] is False
    assert any(error['object'] == 'Cancellation' for error in saved['errors'])
    assert (folder / 'returns' / '0001.json').read_bytes() == state['detail']
    assert not list(folder.glob('run.json.*.tmp'))
