"""Private on-disk answers and public signals remain bound to one owned job."""
import io
import json
from types import SimpleNamespace

import pytest

from spt_desktop.controller import JobController
from spt_desktop.interaction import Requests, read_message


def test_controller_reads_only_its_request_and_never_sends_return_ids_on_stdin(tmp_path):
    assert hasattr(JobController, 'read_request') and hasattr(JobController, 'respond'), 'GUI consent transport is missing'
    events = []
    controller = JobController(tmp_path, events.append)
    controller.job_id = 'synthetic-job'
    controller.active = True
    controller.operation = 'export'
    controller.process = SimpleNamespace(stdin=io.StringIO(), poll=lambda: None)
    folder = tmp_path / 'jobs' / 'synthetic-job'
    requests = None

    def emit(event):
        controller._enqueue(event)
        controller._drain()
        assert events[-1]['request_id'] == event['request_id']
        payload = controller.read_request(event)
        assert payload == {'records': [{'record_id': 'synthetic-return', 'meta': {}}]}
        assert not controller.respond('selection', 'b' * 32, {'selected_ids': ['synthetic-return']})
        assert controller.respond('selection', event['request_id'], {'selected_ids': ['synthetic-return']})
        signal = json.loads(controller.process.stdin.getvalue())
        assert signal == {'job_id': 'synthetic-job', 'command': 'selection', 'request_id': event['request_id']}
        assert 'synthetic-return' not in controller.process.stdin.getvalue()
        assert requests.respond(signal['command'], signal['request_id'])
        assert not controller.respond('selection', event['request_id'], {'selected_ids': ['synthetic-return']})

    requests = Requests(folder, 'synthetic-job', emit, lambda: None)
    assert requests.request('selection', {'records': [{'record_id': 'synthetic-return', 'meta': {}}]}, 20) == {
        'selected_ids': ['synthetic-return']}


def test_controller_stop_and_foreign_job_cannot_authorize_a_pending_answer(tmp_path):
    assert hasattr(JobController, 'read_request') and hasattr(JobController, 'respond'), 'GUI consent transport is missing'
    controller = JobController(tmp_path, lambda event: None)
    controller.job_id = 'synthetic-job'
    controller.active = True
    controller.operation = 'export'
    controller.process = SimpleNamespace(stdin=io.StringIO(), poll=lambda: None)
    folder = tmp_path / 'jobs' / 'synthetic-job'
    requests = None

    def emit(event):
        controller._enqueue(event)
        controller._drain()
        with pytest.raises(ValueError):
            controller.read_request({**event, 'job_id': 'other-job'})
        controller.stop()
        assert not controller.respond('overwrite', event['request_id'], {'overwrite': True})
        assert json.loads(controller.process.stdin.getvalue()) == {'command': 'stop', 'job_id': 'synthetic-job'}
        with pytest.raises(FileNotFoundError):
            read_message(folder, 'synthetic-job', event['request_id'], reply=True)
        raise RuntimeError('synthetic test ends a blocked request without waiting')

    requests = Requests(folder, 'synthetic-job', emit, lambda: None)
    with pytest.raises(RuntimeError, match='synthetic test ends'):
        requests.request('overwrite', {'files': ['resume.xlsx']}, 99)