"""Presentation contracts use bounded synthetic events, not Tk or tax files."""
import ast
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest


NPWP = '0000000000000001'
REQUEST = 'a' * 32


def event(kind='progress', **values):
    return {'job_id': 'job-a', 'type': kind, 'stage': 'details', 'percent': 40, **values}


def test_state_defaults_are_idle_and_immutable():
    from spt_desktop.ui_state import Counters, ExportState
    state = ExportState()
    assert state.view_state == 'idle' and state.percent == 0
    assert state.job_id is None and state.output is None and state.consent is None
    assert state.inventory is None and state.details is None and state.selected_count is None
    assert Counters().verified is None
    with pytest.raises(FrozenInstanceError):
        state.percent = 100


def test_inventory_counts_do_not_become_selected_detail_counts():
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    state = reduce_export(state, event(stage='inventory', percent=20, processed=4,
                                       total=4, scanned=90), controller_active=True)
    assert state.inventory.scanned == 90
    state = reduce_export(state, event(stage='details', percent=43, processed=1,
                                       total=3), controller_active=True)
    assert state.details.total == 3 and state.details.verified is None
    assert state.selected_count is None and state.percent == 43
    state = reduce_export(state, event(), controller_active=True)
    assert state.details is None, 'Missing counts must not reuse stale values'


def test_publish_is_not_complete_and_late_progress_does_not_clear_stop():
    from spt_desktop.ui_state import begin_export, reduce_export, mark_stopping
    state = begin_export('job-a', NPWP, '2025')
    progress = event(stage='publish', percent=99, output='SYNTHETIC_NOT_VERIFIED')
    state = reduce_export(state, progress, controller_active=True)
    assert state.terminal_status is None and state.output is None
    state = mark_stopping(state)
    assert reduce_export(state, progress, controller_active=True) == state
    assert state.view_state == 'stopping' and mark_stopping(state) == state
    complete = event('terminal', status='COMPLETE', percent=100, output='SYNTHETIC_OUTPUT')
    assert reduce_export(state, complete, controller_active=False) == state
    cancelled = reduce_export(state, event('terminal', status='CANCELLED'), controller_active=False)
    assert cancelled.view_state == 'cancelled' and cancelled.output is None


@pytest.mark.parametrize('job_id', [None, '', 'old-job'])
def test_foreign_or_missing_job_id_is_ignored(job_id):
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    assert reduce_export(state, event(job_id=job_id), controller_active=True) == state
    assert reduce_export(state, {'type': 'progress', 'percent': 30}, controller_active=True) == state


def test_new_job_clears_scope_counts_output_and_consent():
    from spt_desktop.ui_state import begin_export, reduce_export
    old = begin_export('job-a', NPWP, '2025')
    old = reduce_export(old, event(processed=1, total=2, verified=1), controller_active=True)
    old = reduce_export(old, event('terminal', status='PARTIAL', output='SYNTHETIC_OUTPUT'), controller_active=False)
    assert old.output and old.details
    new = begin_export('job-b', '0000000000000002', '2024')
    assert new.job_id == 'job-b' and new.npwp == '0000000000000002' and new.year == '2024'
    assert new.percent is None and new.view_state == 'preparing'
    assert (new.inventory, new.details, new.output, new.consent, new.selected_count,
            new.terminal_status) == (None,) * 6


@pytest.mark.parametrize('counts', [
    {'processed': True, 'total': 3, 'verified': 1},
    {'processed': -1, 'total': 3, 'verified': 0},
    {'processed': 2, 'total': 1, 'verified': 1},
    {'processed': 1, 'total': 3, 'verified': 2},
    {'processed': 1, 'total': '3', 'verified': 1},
    {'processed': 1, 'total': 3, 'verified': 1, 'scanned': False},
    {'total': 1, 'verified': 2},
])
def test_details_reject_bool_negative_and_inconsistent_counts(counts):
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    state = reduce_export(state, event(**counts), controller_active=True)
    assert state.details is None


def test_complete_requires_idle_controller_and_matching_terminal():
    from spt_desktop.ui_state import begin_export, reduce_export, mark_stopping
    state = begin_export('job-a', NPWP, '2025')
    complete = event('terminal', status='COMPLETE', percent=100, output='SYNTHETIC_OUTPUT')
    assert reduce_export(state, complete, controller_active=True) == state
    assert reduce_export(state, {**complete, 'output': None}, controller_active=False) == state
    assert reduce_export(state, {**complete, 'type': 'progress'}, controller_active=False) == state
    final = reduce_export(state, complete, controller_active=False)
    assert final.view_state == 'complete' and final.percent == 100
    assert final.output == 'SYNTHETIC_OUTPUT' and final.terminal_status == 'COMPLETE'
    assert reduce_export(final, event(), controller_active=True) == final
    assert mark_stopping(final) == final


@pytest.mark.parametrize('percent', [100, True, -1, '99', None])
def test_partial_cannot_use_100_percent(percent):
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    assert reduce_export(state, event('terminal', status='PARTIAL', percent=percent), controller_active=False) == state


def test_terminal_retains_last_valid_detail_counts():
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    state = reduce_export(state, event(processed=2, total=3, verified=1), controller_active=True)
    for stage, percent in [('export', 95), ('publish', 99)]:
        state = reduce_export(state, event(stage=stage, percent=percent), controller_active=True)
    final = reduce_export(state, event('terminal', status='PARTIAL', percent=99), controller_active=False)
    assert (final.details.processed, final.details.total, final.details.verified) == (2, 3, 1)
    assert final.view_state == 'partial' and final.output is None


@pytest.mark.parametrize('wrong', [
    {'job_id': 'old'}, {'kind': 'overwrite'}, {'request_id': 'b' * 32},
])
def test_reply_requires_matching_job_kind_and_request(wrong):
    from spt_desktop.ui_state import begin_export, reduce_export, record_reply
    state = reduce_export(begin_export('job-a', NPWP, '2025'),
        event('selection_required', request_id=REQUEST), controller_active=True)
    params = {'job_id': 'job-a', 'kind': 'selection', 'request_id': REQUEST, 'selected_count': 2}
    assert record_reply(state, **{**params, **wrong}) == state
    replied = record_reply(state, **params)
    assert replied.selected_count == 2 and replied.consent is None
    assert replied.view_state == 'selection_submitted'
    assert record_reply(replied, **params) == replied


def test_overwrite_decline_is_pending_not_terminal():
    from spt_desktop.ui_state import begin_export, reduce_export, record_reply
    state = reduce_export(begin_export('job-a', NPWP, '2025'),
        event('overwrite_required', request_id=REQUEST, stage='overwrite', percent=99), controller_active=True)
    accepted = record_reply(state, job_id='job-a', kind='overwrite', request_id=REQUEST, overwrite=True)
    assert accepted.view_state == 'publishing' and accepted.output is None
    denied = record_reply(state, job_id='job-a', kind='overwrite', request_id=REQUEST, overwrite=False)
    assert denied.view_state == 'cancellation_pending' and denied.terminal_status is None
    assert reduce_export(denied, event(), controller_active=True) == denied


def test_consent_preserves_waiting_until_valid_reply():
    from spt_desktop.ui_state import begin_export, reduce_export, record_reply
    consent = event('selection_required', request_id=REQUEST, stage='selection', percent=20)
    state = reduce_export(begin_export('job-a', NPWP, '2025'), consent, controller_active=True)
    assert state.consent == ('selection', REQUEST) and state.view_state == 'awaiting_selection'
    for incoming in [consent, event(), {**consent, 'request_id': 'b' * 32}]:
        assert reduce_export(state, incoming, controller_active=True) == state
    for count in [None, False, 0, -1]:
        assert record_reply(state, job_id='job-a', kind='selection', request_id=REQUEST, selected_count=count) == state
    terminal = reduce_export(state, event('terminal', status='ERROR'), controller_active=False)
    assert terminal.consent is None and terminal.view_state == 'error'


@pytest.mark.parametrize('npwp,year', [
    (NPWP, '2025'), (NPWP, '1900'), (NPWP, '2100'), (NPWP, '1899'), (NPWP, '2101'),
    ('0000000000000002', '2024'), ('０００００００００００００００１', '2025'),
    (' '+NPWP, '2025'), (NPWP+' ', '2025'), ('00.000.000.0-001.000', '2025'),
    (NPWP, '２０２５'), (NPWP, '25'), (NPWP, '2025 '), ('', ''),
])
def test_scope_errors_matches_controller_validation(npwp, year):
    from spt_desktop.ui_state import scope_errors
    from spt_desktop.controller import validate_job_scope
    errors = scope_errors(npwp, year)
    try:
        validate_job_scope(npwp, year)
    except ValueError:
        assert errors
    else:
        assert errors == {}
    assert set(errors) <= {'npwp', 'year'}
    assert all(value == f'form.{key}.error' for key, value in errors.items())


@pytest.mark.parametrize('percent', [None, True, -1, '30', 100])
def test_invalid_progress_is_ignored(percent):
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    assert reduce_export(state, event(percent=percent), controller_active=True) == state


def test_setup_auth_login_and_observed_empty_complete_are_distinct():
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    assert state.view_state == 'preparing' and state.percent is None
    state = reduce_export(state, event(stage='authentication', percent=5), controller_active=True)
    assert state.view_state == 'authenticating' and state.terminal_status is None
    state = reduce_export(state, event('login_required', stage='authentication', percent=5), controller_active=True)
    assert state.view_state == 'login_required' and state.output is None
    state = reduce_export(state, event(processed=0, total=0, verified=0, percent=90), controller_active=True)
    state = reduce_export(state, event('terminal', status='COMPLETE', percent=100, output='SYNTHETIC_EMPTY_RESULT'), controller_active=False)
    assert state.view_state == 'empty_complete'


def test_login_terminal_cannot_become_an_export_result():
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', NPWP, '2025')
    assert reduce_export(state, event('terminal', status='LOGIN_OK', percent=0), controller_active=False) == state


def test_state_module_has_no_gui_or_file_dependencies():
    from spt_desktop import ui_state
    tree = ast.parse(Path(ui_state.__file__).read_text(encoding='utf-8'))
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name.split('.')[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            modules.append(node.module.split('.')[0])
    assert set(modules) <= {'dataclasses', 'typing', 're', '__future__', 'collections'}
