"""Windows runner contracts for the approved UI shell; synthetic jobs only."""
import gc
import json
import pytest


NPWP = '0000000000000001'


class Controller:
    def __init__(self):
        self.active = False
        self.operation = 'export'
        self.job_id = None
        self.starts = []
        self.stops = 0
        self.closes = 0

    def start(self, *args):
        assert not self.active
        self.starts.append(args)
        self.job_id = f'synthetic-{len(self.starts)}'
        self.active = True
        self.operation = 'export'
        return self.job_id

    def start_login_check(self, *args):
        assert not self.active
        self.job_id = 'synthetic-login-check'
        self.operation = 'login_check'
        self.active = True
        return self.job_id

    def poll(self):
        return self.active

    def stop(self):
        self.stops += 1

    def close(self):
        self.closes += 1
        self.active = False


def settle(root):
    import tkinter as tk
    done = tk.BooleanVar(root)
    root.after(250, lambda: done.set(True))
    root.wait_variable(done)
    root.update_idletasks()


@pytest.fixture
def window(tmp_path, monkeypatch):
    import tkinter as tk
    from spt_desktop import app as gui
    root = tk.Tk()
    messages, errors = [], []
    root.report_callback_exception = lambda *args: errors.append(args)
    monkeypatch.setattr(gui.messagebox, 'showerror', lambda *args, **kwargs: messages.append(args))
    controller = Controller()
    app = gui.App(root, tmp_path, controller=controller)
    root.geometry('900x700')
    settle(root)
    root.focus_force()
    try:
        yield root, app, controller, messages
    finally:
        controller.active = False
        try:
            if root.winfo_exists():
                app._close_interaction()
                if app._settings_close:
                    app._settings_close()
                app._dispose()
                for token in root.tk.splitlist(root.tk.call('after', 'info')):
                    root.after_cancel(token)
                root.destroy()
        except tk.TclError:
            pass
        del app
        gc.collect()
        assert not errors, errors


def begin(app):
    app.npwp.set(NPWP)
    app.year.set('2025')
    app.start()


def progress(controller, **values):
    return {'job_id': controller.job_id, 'type': 'progress', 'stage': 'details',
            'percent': 42, 'message': 'Synthetic progress', **values}


@pytest.mark.parametrize('npwp,year,first', [
    ('０００００００００００００００１', '2025', 'npwp'),
    (' ' + NPWP, '2025', 'npwp'), ('00.000.000.0-001.000', '2025', 'npwp'),
    (NPWP, '2025 ', 'year'), (NPWP, '2101', 'year'), ('', '', 'npwp'),
])
def test_invalid_fields_do_not_start_and_focus_first_error(window, npwp, year, first):
    root, app, controller, messages = window
    app.npwp.set(npwp)
    app.year.set(year)
    app.start()
    root.update()
    assert not controller.starts and not messages
    assert (app.npwp.get(), app.year.get()) == (npwp, year)
    assert getattr(app.view, first + '_error').get()
    assert root.focus_get() is getattr(app, first + '_entry')


@pytest.mark.parametrize('first', ['click', 'enter', 'alt'])
def test_click_enter_and_alt_m_share_one_start_guard(window, first):
    root, app, controller, _ = window
    app.npwp.set(NPWP)
    app.year.set('2025')
    app.npwp_entry.focus_set()
    root.update()
    actions = {'click': app.start_button.invoke,
               'enter': lambda: app.npwp_entry.event_generate('<Return>'),
               'alt': lambda: root.event_generate('<Alt-m>')}
    actions[first]()
    root.update()
    assert len(controller.starts) == 1
    for action in actions.values():
        action()
    app.start()
    root.update()
    assert len(controller.starts) == 1
    assert app._ui_state.job_id == controller.job_id
    assert all(w.instate(['disabled']) for w in (app.start_button, app.settings_button, app.npwp_entry, app.year_entry))
    assert app.stop_button.instate(['!disabled'])


def test_scope_snapshot_does_not_follow_later_stringvar_changes(window):
    root, app, controller, _ = window
    begin(app)
    app.npwp.set('0000000000000002')
    app.year.set('2024')
    app.on_event(progress(controller, processed=1, total=3, verified=1))
    assert app.view.scope_npwp.get() == NPWP and app.view.scope_year.get() == '2025'


def test_setup_login_required_and_counts_use_correct_presentation(window):
    root, app, controller, _ = window
    begin(app)
    assert str(app.bar['mode']) == 'indeterminate' and app.percent.get() == '—'
    app.on_event(progress(controller, type='login_required', stage='authentication', percent=5))
    assert app.view.process_title.get() == 'Selesaikan login di browser'
    app.on_event(progress(controller, stage='inventory', processed=4, total=4, scanned=90, percent=20))
    assert 'Baris terbaca: 90' in app.view.metric_text.get()
    app.on_event(progress(controller, processed=1, total=3))
    assert '1 / 3' in app.view.metric_text.get()
    assert '90' not in app.view.metric_text.get() and 'Lengkap:' not in app.view.metric_text.get()


@pytest.mark.parametrize('output', [None, 'SYNTHETIC_NOT_VERIFIED'])
def test_99_percent_cannot_open_a_result(window, output):
    root, app, controller, _ = window
    begin(app)
    app.on_event(progress(controller, stage='publish', percent=99, output=output))
    assert app._ui_state.output is None and app._result is None
    assert app.open_button.instate(['disabled']) and controller.active


def test_premature_terminal_does_not_release_controls(window):
    root, app, controller, _ = window
    begin(app)
    before = app._ui_state
    app.on_event(progress(controller, type='terminal', percent=100, status='COMPLETE', output='SYNTHETIC_OUTPUT'))
    assert app._ui_state == before and app._result is None
    assert app.start_button.instate(['disabled']) and app.stop_button.instate(['!disabled'])


def test_duplicate_stop_and_late_progress_do_not_reenable_actions(window):
    root, app, controller, _ = window
    begin(app)
    app.stop()
    app.stop()
    app.on_event(progress(controller, processed=2, total=3, verified=2))
    assert controller.stops == 1 and app._ui_state.view_state == 'stopping'
    assert app.start_button.instate(['disabled']) and app.stop_button.instate(['disabled'])
    controller.active = False
    app.on_event(progress(controller, type='terminal', status='CANCELLED'))
    assert app._ui_state.view_state == 'cancelled' and app.start_button.instate(['!disabled'])


def test_old_or_missing_job_events_cannot_replace_current_presentation(window):
    root, app, controller, _ = window
    begin(app)
    before = app._ui_state
    app.on_event({'type': 'progress', 'stage': 'details', 'percent': 10})
    app.on_event(progress(controller, job_id='old-job', message='Must not replace status'))
    assert app._ui_state == before and app.status.get() != 'Must not replace status'


def test_poll_failure_does_not_claim_terminal_or_repeat_cleanup(window, monkeypatch):
    root, app, controller, _ = window
    begin(app)
    def broken():
        raise RuntimeError('Synthetic monitor failure')
    def close_owned():
        controller.closes += 1
    monkeypatch.setattr(controller, 'poll', broken)
    monkeypatch.setattr(controller, 'close', close_owned)
    settle(root)
    assert controller.active and controller.closes == 1
    assert app._ui_state.terminal_status is None and app._ui_state.view_state == 'stopping'
    assert app.start_button.instate(['disabled'])


def test_self_test_uses_job_bound_progress_and_real_captions(tmp_path, monkeypatch):
    from spt_desktop import app as gui
    from spt_gui import self_test
    def forbidden_controller(*args, **kwargs):
        raise AssertionError('Self-test must inject a synthetic controller')
    monkeypatch.setattr(gui, 'JobController', forbidden_controller)
    original = gui.App.on_event
    seen = []
    def observed(self, item):
        assert item['job_id'] == self.controller.job_id and item['job_id']
        seen.append(item)
        return original(self, item)
    monkeypatch.setattr(gui.App, 'on_event', observed)
    report = tmp_path / 'synthetic-self-test.json'
    assert self_test(report) == 0
    data = json.loads(report.read_text(encoding='utf-8'))
    assert seen and seen[-1]['percent'] == 42
    assert {'Mulai unduh', 'Hentikan unduhan', 'Buka folder hasil', 'Cek Kredensial'} <= set(data['gui_controls'])
    assert data['credentials_accessed'] is False and data['live_scrape'] is False


def test_closing_root_disposes_view_and_poll_callbacks(window, monkeypatch):
    root, app, controller, _ = window
    app.view.request_reflow()
    owned = {app._poll_after, app.view._reflow_after}
    assert None not in owned
    before_destroy = []
    destroy = root.destroy
    def observed_destroy():
        before_destroy.extend(root.tk.splitlist(root.tk.call('after', 'info')))
        destroy()
    monkeypatch.setattr(root, 'destroy', observed_destroy)
    app.request_close()
    assert not owned & set(before_destroy)


def test_new_login_check_gets_its_own_poll_failure_cleanup(window, monkeypatch):
    root, app, controller, _ = window
    begin(app)
    def broken():
        raise RuntimeError('Synthetic monitoring failure')
    def cleanup():
        controller.closes += 1
    monkeypatch.setattr(controller, 'poll', broken)
    monkeypatch.setattr(controller, 'close', cleanup)
    settle(root)
    assert controller.closes == 1
    monkeypatch.setattr(controller, 'poll', lambda: controller.active)
    controller.active = False
    app.on_event(progress(controller, type='terminal', status='CANCELLED'))
    app.preferences['identifier'] = 'SYNTHETIC_ACCOUNT'
    dialog = app.settings()
    def descendants(widget):
        for child in widget.winfo_children():
            yield child
            yield from descendants(child)
    check = next(w for w in descendants(dialog) if w.winfo_class() == 'TButton'
                 and w.cget('text') == 'Cek Kredensial')
    check.invoke()
    assert controller.operation == 'login_check' and controller.active
    monkeypatch.setattr(controller, 'poll', broken)
    settle(root)
    assert controller.closes == 2, 'A new login job must request its own cleanup'


@pytest.mark.parametrize('status,has_output,focus_name', [
    ('PARTIAL', True, 'open_button'),
    ('CANCELLED', False, 'start_button'),
])
def test_compact_terminal_focus_targets_visible_outcome_after_reveal(
        window, tmp_path, status, has_output, focus_name):
    root, app, controller, _ = window
    root.geometry('540x390')
    settle(root)
    begin(app)
    root.update_idletasks()
    controller.active = False
    output = tmp_path / 'synthetic-output'
    if has_output:
        output.mkdir()
    event = progress(controller, type='terminal', status=status, percent=90,
                     output=str(output) if has_output else None)
    app.on_event(event)
    settle(root)  # Allows both reflow and delayed scroll reveal to finish.
    focus = root.focus_get()
    expected = getattr(app, focus_name)
    assert focus is expected, 'Focus must remain on an actionable visible control after result scroll'
    assert expected.winfo_ismapped() and expected.instate(['!disabled'])
    assert app.view.result_title_label.winfo_ismapped()
    top = app.view.canvas.winfo_rooty()
    bottom = top + app.view.canvas.winfo_height()
    title = app.view.result_title_label
    assert top <= title.winfo_rooty()
    assert title.winfo_rooty() + title.winfo_height() <= bottom
    assert root.focus_get() is not app.npwp_entry
