"""Synthetic credential actions and real threads exercise desktop stop/exit races."""
import io
import threading
from types import SimpleNamespace

import pytest

from coretax_browser import CaptureCancelled
from spt_desktop import auth, controller
from spt_desktop.credentials import Login


@pytest.mark.parametrize('stop_after', ['inspection', 'identifier', 'password'])
@pytest.mark.parametrize('operation', ['export', 'login_check'])
def test_stop_between_credential_actions_prevents_the_next_action(monkeypatch, tmp_path, stop_after, operation):
    stopped = threading.Event()
    actions = []

    class Field:
        def __init__(self, name):
            self.name = name

        def fill(self, value, **kwargs):
            actions.append(self.name)
            if self.name == stop_after:
                stopped.set()

    class Button:
        def click(self, **kwargs):
            actions.append('submit')

    origin = 'https://satu.intranet.pajak.go.id'
    fields = origin, Field('identifier'), Field('password'), Button()
    inspections = 0
    def current_form():
        nonlocal inspections
        inspections += 1
        if stop_after == 'inspection' and inspections == 2:
            stopped.set()
        return True
    monkeypatch.setattr(auth, '_login_fields', lambda page: fields)
    monkeypatch.setattr(auth, '_bind_login_fields', lambda page, inspected: (inspected, current_form))
    monkeypatch.setattr(auth, 'read_login', lambda selected: Login('SYNTHETIC_ACCOUNT', 'SYNTHETIC_PASSWORD_ONLY'))

    def check_cancel():
        if stopped.is_set():
            raise CaptureCancelled('Synthetic Stop during credential entry')

    with pytest.raises(CaptureCancelled):
        if operation == 'export':
            auth.try_saved_login(object(), check_cancel)
        else:
            page = SimpleNamespace(url=origin + '/login', goto=lambda *args, **kwargs: None)
            context = SimpleNamespace(pages=[page], route=lambda *args: None, close=lambda: None)
            engine = SimpleNamespace(chromium=SimpleNamespace(launch_persistent_context=lambda *args, **kwargs: context))
            monkeypatch.setattr(auth, 'authenticated', lambda page: False)
            monkeypatch.setattr(auth, '_at_home', lambda page: False)
            monkeypatch.setattr(auth, '_has_challenge', lambda page: False)
            auth.check_saved_credentials(engine, tmp_path, origin, 'SYNTHETIC_ACCOUNT',
                                         'msedge', True, check_cancel, timeout=1)
    assert actions == {'inspection': [], 'identifier': ['identifier'], 'password': ['identifier', 'password']}[stop_after]


def test_exit_waits_for_delayed_terminal_reader_without_blocking_poll(tmp_path):
    events = []
    closed = threading.Event()
    release_reader = threading.Event()
    ctl = controller.JobController(tmp_path, events.append)
    ctl.active = True
    ctl.operation = 'login_check'
    ctl.job_id = 'synthetic-delayed-terminal'
    ctl.process = SimpleNamespace(
        returncode=0, poll=lambda: 0, stdin=io.StringIO(),
        stdout=io.StringIO(), stderr=io.StringIO(),
    )
    ctl._job = SimpleNamespace(close=closed.set)

    def read_terminal():
        release_reader.wait()
        ctl._enqueue({'job_id': ctl.job_id, 'type': 'terminal', 'stage': 'login_check',
                      'status': 'LOGIN_OK', 'percent': 0, 'output': None,
                      'message': 'Synthetic credentials verified'})

    reader = threading.Thread(target=read_terminal)
    ctl._readers = [reader]
    reader.start()
    try:
        assert ctl.poll(), 'A pending final reader must keep the job active'
        assert closed.is_set(), 'Owned descendants must close before waiting for inherited pipes'
        assert events == [], 'Worker exit alone must not emit a premature terminal error'
        assert not ctl.process.stdout.closed, 'A reader must finish before its stream is closed'
        release_reader.set()
        reader.join(timeout=2)
        assert not reader.is_alive()
        assert not ctl.poll()
        assert [event['status'] for event in events] == ['LOGIN_OK']
    finally:
        release_reader.set()
        reader.join(timeout=2)
        ctl.close()
