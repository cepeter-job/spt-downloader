"""Job lifecycle consent uses synthetic signals and never opens a browser."""
import io
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

from spt_desktop.controller import JobController


def controller(tmp_path, events):
    result = JobController(tmp_path, events.append)
    result.active = True
    result.job_id = 'synthetic-job'
    result.process = SimpleNamespace(stdin=io.StringIO(), poll=lambda: None)
    return result


def selection_event():
    return {'job_id': 'synthetic-job', 'type': 'selection_required',
            'stage': 'selection', 'request_id': 'a' * 32,
            'percent': 20, 'message': 'Pilih SPT sintetis.'}


def test_stop_discards_a_consent_event_already_in_the_queue(tmp_path):
    events = []
    ctl = controller(tmp_path, events)
    ctl._enqueue(selection_event())
    ctl.stop()
    ctl._drain()
    assert events == []
    assert json.loads(ctl.process.stdin.getvalue()) == {
        'command': 'stop', 'job_id': 'synthetic-job'}


def test_terminal_prevents_a_later_consent_event_from_reopening_a_dialog(tmp_path):
    events = []
    ctl = controller(tmp_path, events)
    ctl._enqueue({'job_id': ctl.job_id, 'type': 'terminal', 'status': 'ERROR',
                  'percent': 20, 'output': None, 'message': 'Synthetic failure'})
    ctl._enqueue(selection_event())
    ctl._drain()
    assert events == []


def test_exited_worker_cannot_request_consent(tmp_path):
    events = []
    ctl = controller(tmp_path, events)
    ctl.process.poll = lambda: 1
    ctl._enqueue(selection_event())
    ctl._drain()
    assert events == []


def test_worker_main_routes_job_bound_consent_signals_using_private_reply_files(tmp_path):
    script = r'''
import json
from pathlib import Path
import queue
import sys
from spt_desktop import worker
from spt_desktop.interaction import write_reply

job_id = 'synthetic-worker-consent'
root = Path(sys.argv[1])
messages = queue.Queue()
messages.put(json.dumps({'job_id': job_id, 'command': 'start'}) + '\n')

class Input:
    def readline(self, limit):
        return messages.get(timeout=10)

original_output = sys.stdout

class Output:
    selection_requests = 0

    def write(self, text):
        original_output.write(text)
        event = json.loads(text)
        if event['type'] not in ('selection_required', 'overwrite_required'):
            return
        kind = event['type'].removesuffix('_required')
        payload = {'selected_ids': ['PRIVATE_SYNTHETIC_RETURN']} if kind == 'selection' else {'overwrite': True}
        write_reply(root / 'jobs' / job_id, job_id, event['request_id'], payload)
        if kind == 'selection':
            self.selection_requests += 1
            if self.selection_requests == 1:
                messages.put(json.dumps({'job_id': 'different-job', 'command': kind,
                                         'request_id': event['request_id']}) + '\n')
                return
        messages.put(json.dumps({'job_id': job_id, 'command': kind,
                                 'request_id': event['request_id']}) + '\n')

    def flush(self):
        original_output.flush()

sys.stdin = Input()
sys.stdout = Output()

def run(npwp, year, workspace, identifier, browser, headless, emit, cancelled, *, requests=None, account):
    assert account == ''
    assert requests is not None, 'Worker main must provide the private consent channel'
    try:
        requests.request('selection', {'records': [{'record_id': 'PRIVATE_SYNTHETIC_RETURN'}]}, 20,
                         timeout=0.5)
    except TimeoutError:
        pass
    else:
        raise AssertionError('A foreign-job signal authorized selection')
    assert requests.request('selection', {'records': [{'record_id': 'PRIVATE_SYNTHETIC_RETURN'}]}, 20) == {
        'selected_ids': ['PRIVATE_SYNTHETIC_RETURN']}
    assert requests.request('overwrite', {'files': ['resume.xlsx']}, 99) == {'overwrite': True}
    emit({'job_id': identifier, 'type': 'terminal', 'status': 'CANCELLED',
          'percent': 99, 'output': None, 'message': 'Synthetic transport completed'})
    return 4

worker.run_job = run
raise SystemExit(worker.main(['--npwp', '0000000000000001', '--year', '2025',
                            '--root', str(root), '--job-id', job_id]))
'''
    result = subprocess.run([sys.executable, '-c', script, str(tmp_path)],
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 4, result.stderr
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [event['type'] for event in events] == [
        'selection_required', 'selection_required', 'overwrite_required', 'terminal']
    assert 'PRIVATE_SYNTHETIC_RETURN' not in result.stdout
    assert result.stderr == ''
