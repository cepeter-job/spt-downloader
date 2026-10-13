"""Real ttk shell contracts; all execution belongs on the Windows runner."""
import gc
import pytest


def widgets(root):
    for child in root.winfo_children():
        yield child
        yield from widgets(child)


def settle(root):
    import tkinter as tk
    finished = tk.BooleanVar(root)
    root.after(220, lambda: finished.set(True))
    root.wait_variable(finished)
    root.update_idletasks()


@pytest.fixture
def shell():
    from spt_desktop.ui_views import MainView
    import tkinter as tk
    root = tk.Tk()
    errors, calls = [], []
    root.report_callback_exception = lambda *args: errors.append(args)
    view = None
    try:
        view = MainView(root, year_default='2025',
            on_start=lambda: calls.append('start'), on_stop=lambda: calls.append('stop'),
            on_settings=lambda: calls.append('settings'), on_open_result=lambda: calls.append('open'))
        view.pack(fill='both', expand=True)
        root.geometry('1120x800')
        settle(root)
        yield root, view, calls
    finally:
        if view is not None:
            view.dispose()
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.destroy()
        del view
        gc.collect()
        assert not errors, f'Unexpected Tk callback error: {errors!r}'


def test_shell_has_one_real_heading_and_downloads_hint(shell):
    root, view, calls = shell
    from tkinter import ttk
    headings = [w for w in widgets(root) if isinstance(w, ttk.Label)
                and str(w.cget('style')) == 'Title.TLabel']
    assert len(headings) == 1 and headings[0] is view.heading
    assert view.heading.cget('text') == 'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang'
    assert [w.cget('text') for w in widgets(root) if isinstance(w, ttk.Label)].count(
        'Hasil Sedot berada di folder Downloads Windows') == 1
    assert len(view.stage_labels) == 4
    assert all(str(w.cget('takefocus')) == '0' for w in view.stage_labels)
    assert isinstance(view.npwp_entry, ttk.Entry) and isinstance(view.year_entry, ttk.Entry)
    assert view.npwp.get() == '' and view.year.get() == '2025'
    assert calls == []
    view.start_button.invoke()
    assert calls == ['start']


def test_compact_reorders_summary_without_hiding_it(shell):
    root, view, _ = shell
    from spt_desktop.ui_state import begin_export
    state = begin_export('job-a', '0000000000000001', '2025')
    view.render(state, active=True)
    root.geometry('640x560')
    settle(root)
    assert view.scope_panel.winfo_ismapped()
    assert view.scope_panel.winfo_y() < view.content_slot.winfo_y()
    assert view.scope_npwp.get() == '0000000000000001' and view.scope_year.get() == '2025'
    assert len({label.grid_info()['row'] for label in view.stage_labels}) == 2
    root.geometry('1120x800')
    settle(root)
    assert view.scope_panel.winfo_x() > view.content_slot.winfo_x()
    assert len({label.grid_info()['row'] for label in view.stage_labels}) == 1


def test_render_reuses_widgets_and_does_not_steal_focus(shell):
    root, view, _ = shell
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', '0000000000000001', '2025')
    state = reduce_export(state, {'job_id': 'job-a', 'type': 'progress', 'stage': 'details',
        'percent': 30, 'processed': 1, 'total': 3, 'verified': 1}, controller_active=True)
    view.render(state, active=True)
    settle(root)
    root.focus_force()
    view.stop_button.focus_set()
    root.update_idletasks()
    before = tuple(str(w) for w in widgets(root))
    focus = root.focus_get()
    for _ in range(100):
        view.render(state, active=True)
    root.update_idletasks()
    assert tuple(str(w) for w in widgets(root)) == before
    assert root.focus_get() == focus
    assert view.percent.get() == '30%' and int(view.bar['value']) == 30


def test_reflow_has_one_pending_callback_and_dispose_cancels_only_its_own(shell):
    root, view, _ = shell
    unrelated = root.after(60000, lambda: None)
    before = set(root.tk.splitlist(root.tk.call('after', 'info')))
    for _ in range(20):
        view.request_reflow()
    after = set(root.tk.splitlist(root.tk.call('after', 'info')))
    assert len(after - before) == 1
    view.dispose()
    remaining = set(root.tk.splitlist(root.tk.call('after', 'info')))
    assert unrelated in remaining and not (after - before) & remaining


@pytest.mark.parametrize('width,height', [(540, 390), (640, 560), (900, 700), (1120, 800)])
def test_error_labels_wrap_without_overlapping_action_bar(shell, width, height):
    root, view, _ = shell
    view.show_errors({'npwp': 'form.npwp.error', 'year': 'form.year.error'})
    root.geometry(f'{width}x{height}')
    settle(root)
    assert view.npwp_error.get() and view.year_error.get()
    for widget in [view.heading, view.results_label, view.action_bar]:
        left = widget.winfo_rootx() - root.winfo_rootx()
        top = widget.winfo_rooty() - root.winfo_rooty()
        assert left >= 0 and top >= 0
        assert left + widget.winfo_width() <= root.winfo_width()
        assert top + widget.winfo_height() <= root.winfo_height()
    for label in (view.heading, view.results_label):
        assert label.winfo_height() >= label.winfo_reqheight()
        assert label.winfo_width() >= label.winfo_reqwidth()
    assert view.npwp_entry.get() == ''


def test_progress_never_opens_output_or_restarts_indeterminate_timer(shell):
    root, view, _ = shell
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('job-a', '0000000000000001', '2025')
    view.render(state, active=True)
    timers = set(root.tk.splitlist(root.tk.call('after', 'info')))
    for _ in range(20):
        view.render(state, active=True)
    assert set(root.tk.splitlist(root.tk.call('after', 'info'))) == timers
    assert str(view.bar['mode']) == 'indeterminate' and view.percent.get() == '—'
    state = reduce_export(state, {'job_id':'job-a', 'type':'progress', 'stage':'publish',
                                  'percent':99}, controller_active=True)
    view.render(state, active=True)
    assert str(view.bar['mode']) == 'determinate' and view.percent.get() == '99%'
    assert view.open_button.instate(['disabled'])
    view.set_busy(True, stopping=True)
    assert all(w.instate(['disabled']) for w in (view.start_button, view.stop_button, view.settings_button))
