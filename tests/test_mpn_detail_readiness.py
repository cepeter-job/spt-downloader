"""Value-free observations at the existing MPN detail readiness refusal."""
import json
from types import SimpleNamespace

import pytest

from coretax_mpn import MpnSafetyError, MpnUnsupported
from coretax_mpn_ui import AccountingUI
from spt_desktop import diagnostics
from test_diagnostics import records


SECRET = 'SYNTHETIC_PRIVATE_SELECTOR_AND_BUSINESS_VALUE'


class Control:
    def __init__(self, count=1, visible=True):
        self.matches = count
        self.visible = visible
        self.reads = []

    def count(self):
        self.reads.append('count')
        return self.matches

    def is_visible(self):
        self.reads.append('visible')
        return self.visible


def ready_ui(monkeypatch, *, count=1, visible=True, pending=False, stage='detail_grid'):
    import coretax_mpn_ui as module
    clock = [100.0]
    control = Control(count, visible)
    waits = []
    def wait(milliseconds):
        waits.append(milliseconds)
        clock[0] += milliseconds / 1000
    ui = AccountingUI.__new__(AccountingUI)
    ui.diagnostic_stage = stage
    ui.preparation_deadline = None
    ui.observer = SimpleNamespace(_binding_document=pending)
    ui.page = SimpleNamespace(locator=lambda selector: control, wait_for_timeout=wait)
    ui._stop = lambda: None
    ui._state = lambda **kwargs: None
    monkeypatch.setattr(module.time, 'monotonic', lambda: clock[0])
    return ui, control, clock, waits


def failure_records(root):
    return [row for row in records(root) if row['event'] == 'mpn.detail_readiness_failed']


@pytest.mark.parametrize('count,visible,state,reason,reads', [
    (0, False, 'missing', 'deadline', ['count']),
    (1, False, 'hidden', 'deadline', ['count', 'visible']),
    (1, True, 'visible', 'deadline', ['count', 'visible']),
    (2, False, 'ambiguous', 'ambiguous', ['count']),
])
@pytest.mark.parametrize('stage', ['detail_dialog', 'detail_title', 'detail_grid'])
def test_refusal_retains_last_observation_without_a_diagnostic_rpc(
        tmp_path, monkeypatch, count, visible, state, reason, reads, stage):
    ui, control, _, waits = ready_ui(monkeypatch, count=count, visible=visible, stage=stage)
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnUnsupported):
            ui._ready_one(SECRET, deadline=100.0)
        assert log.flush()
    events = failure_records(root)
    assert len(events) == 1
    event = events[0]
    assert event['mpn_ui_stage'] == stage
    assert event['mpn_readiness_state'] == state
    assert event['mpn_readiness_reason'] == reason
    assert event['mpn_readiness_budget_ms'] == 0
    assert event['duration_ms'] == 0
    assert control.reads == reads and waits == []
    assert SECRET not in json.dumps(records(root))


def test_visible_control_after_final_state_rpc_does_not_gain_capture_permission(tmp_path, monkeypatch):
    ui, control, clock, waits = ready_ui(monkeypatch)
    def state(**kwargs):
        clock[0] += 1
    ui._state = state
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnUnsupported):
            ui._ready_one(SECRET, deadline=102.5)
        assert log.flush()
    event, = failure_records(root)
    assert event['mpn_readiness_state'] == 'visible'
    assert event['mpn_readiness_budget_ms'] == 2500
    assert event['duration_ms'] == 3000
    assert control.reads == ['count', 'visible'] and waits == []


def test_pending_document_deadline_logs_unobserved_without_touching_dom(tmp_path, monkeypatch):
    ui, control, _, waits = ready_ui(monkeypatch, pending=True)
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnUnsupported):
            ui._ready_one(SECRET, deadline=100.1)
        assert log.flush()
    event, = failure_records(root)
    assert event['mpn_readiness_state'] == 'unobserved'
    assert event['mpn_readiness_budget_ms'] == 100
    assert control.reads == [] and waits == [99, 1]


@pytest.mark.parametrize('stage', ['detail_dialog', 'detail_title', 'detail_grid', 'search'])
def test_successful_ready_control_remains_silent(tmp_path, monkeypatch, stage):
    ui, control, _, waits = ready_ui(monkeypatch, stage=stage)
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        assert ui._ready_one(SECRET, deadline=105.0) is control
        assert log.flush()
    assert failure_records(root) == []
    assert control.reads == ['count', 'visible'] and waits == []


@pytest.mark.parametrize('failure', [KeyboardInterrupt, MpnSafetyError])
def test_stop_and_callback_safety_outrank_readiness_evidence(tmp_path, monkeypatch, failure):
    ui, control, _, waits = ready_ui(monkeypatch)
    calls = []
    def state(**kwargs):
        calls.append(True)
        if len(calls) == 2:
            raise failure(SECRET)
    ui._state = state
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(failure):
            ui._ready_one(SECRET, deadline=100.0)
        assert log.flush()
    assert failure_records(root) == []
    assert control.reads == ['count'] and waits == []


def test_nondetail_refusal_and_logging_off_preserve_original_result(tmp_path, monkeypatch):
    ui, control, _, waits = ready_ui(monkeypatch, stage='search')
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        with pytest.raises(MpnUnsupported):
            ui._ready_one(SECRET, deadline=100.0)
        assert log.flush()
    assert failure_records(root) == []
    ui.diagnostic_stage = 'detail_grid'
    with diagnostics.session(tmp_path / 'off', 'worker', level='OFF'):
        with pytest.raises(MpnUnsupported):
            ui._ready_one(SECRET, deadline=100.0)
    assert control.reads == ['count', 'visible'] * 2 and waits == []


def test_readiness_schema_drops_untrusted_categories_and_budget_values(tmp_path):
    class Untrusted:
        def __str__(self):
            raise AssertionError('Never stringify a diagnostic value')
    class Number(float):
        pass
    root = tmp_path / 'diag'
    with diagnostics.session(root, 'worker') as log:
        diagnostics.record('mpn.detail_readiness_failed', mpn_ui_stage='detail_grid',
                           mpn_readiness_state='hidden', mpn_readiness_reason='deadline',
                           mpn_readiness_budget_ms=5000, selector=SECRET, body=SECRET)
        for value in (SECRET, Untrusted(), True, -1, 5001, float('nan'), float('inf'), Number(1)):
            diagnostics.record('mpn.detail_readiness_failed', mpn_ui_stage=value,
                               mpn_readiness_state=value, mpn_readiness_reason=value,
                               mpn_readiness_budget_ms=value, url=SECRET, message=SECRET)
        assert log.flush()
    events = failure_records(root)
    assert len(events) == 9
    assert events[0]['mpn_readiness_state'] == 'hidden'
    assert events[0]['mpn_readiness_budget_ms'] == 5000
    for event in events[1:]:
        assert not {'mpn_ui_stage', 'mpn_readiness_state', 'mpn_readiness_reason',
                    'mpn_readiness_budget_ms'} & event.keys()
    assert SECRET not in json.dumps(events)
