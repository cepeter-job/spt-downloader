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


@pytest.mark.parametrize('geometry', ['1120x800', '640x560'])
def test_unchanged_shell_reflow_keeps_visible_panels_mapped(shell, geometry):
    """A redundant layout must not hide/remap the form and summary native windows."""
    root, view, _ = shell
    root.geometry(geometry)
    settle(root)
    panels = (view.content_slot, view.scope_panel)
    assert all(panel.winfo_ismapped() for panel in panels)
    unmaps = []
    bindings = [(panel, panel.bind('<Unmap>', lambda event: unmaps.append(str(event.widget)), add='+'))
                for panel in panels]
    try:
        view.request_reflow()
        settle(root)
        assert all(panel.winfo_ismapped() for panel in panels)
        assert unmaps == [], 'Unchanged shell reflow hid visible panels before mapping them again'
    finally:
        for panel, token in bindings:
            panel.unbind('<Unmap>', token)


def drain_shell_layout_without_timers(root, view):
    """Process native geometry and idle work without hiding a delayed reflow."""
    import _tkinter
    import time
    flags = _tkinter.WINDOW_EVENTS | _tkinter.IDLE_EVENTS | _tkinter.DONT_WAIT
    deadline, quiet = time.monotonic() + 2, 0
    while time.monotonic() < deadline:
        pending = root.tk.dooneevent(flags)
        root.update_idletasks()
        if not pending and view.winfo_ismapped() and view.canvas.winfo_width() > 1:
            quiet += 1
            if quiet == 3:
                return
        else:
            quiet = 0
        time.sleep(.001)
    raise AssertionError('The native shell did not map and settle')


@pytest.mark.parametrize('change', ['progress', 'errors'])
def test_shell_content_layout_completes_without_resize_timer(shell, change):
    root, view, _ = shell
    if change == 'progress':
        from spt_desktop.ui_state import begin_export
        view.render(begin_export('synthetic-job', '0000000000000001', '2025'), active=True)
    else:
        view.show_errors({'npwp': 'form.npwp.error', 'year': 'form.year.error'})
    drain_shell_layout_without_timers(root, view)
    assert view._reflow_after is None, 'Changed content is still waiting for a resize timer'
    assert int(view.canvas.itemcget(view._canvas_window, 'width')) == view.canvas.winfo_width()
    assert view.workspace.winfo_reqheight() <= float(view.canvas.cget('scrollregion').split()[3])
    if change == 'progress':
        assert view.progress_panel.winfo_ismapped() and not view.form.winfo_ismapped()
        assert view.scope_npwp.get() == '0000000000000001' and view.scope_year.get() == '2025'
    else:
        assert view.npwp_error.get() and view.year_error.get()


def test_duplicate_shell_configure_does_not_queue_layout(shell):
    root, view, _ = shell
    before = (view.canvas.winfo_width(), view.canvas.winfo_height(), view.canvas.cget('scrollregion'))
    for _ in range(20):
        view.event_generate('<Configure>')
        view.canvas.event_generate('<Configure>')
    drain_shell_layout_without_timers(root, view)
    assert view._reflow_after is None, 'Unchanged geometry queued a redundant reflow'
    assert (view.canvas.winfo_width(), view.canvas.winfo_height(), view.canvas.cget('scrollregion')) == before


@pytest.mark.parametrize('content_change', [False, True])
def test_shell_resize_coalesces_but_content_can_make_it_ready(shell, content_change):
    root, view, _ = shell
    root.geometry('640x560')
    drain_shell_layout_without_timers(root, view)
    pending = view._reflow_after
    assert pending is not None, 'A genuine native resize must retain coalesced work'
    assert str(root.tk.call('after', 'info', pending)[1]) == 'timer'
    if content_change:
        view.show_errors({'npwp': 'form.npwp.error'})
        drain_shell_layout_without_timers(root, view)
        assert view._reflow_after is None, 'Explicit content invalidation did not replace delayed resizing'
        assert pending not in root.tk.splitlist(root.tk.call('after', 'info'))
        assert view.npwp_error.get()
    else:
        settle(root)
    assert view.scope_panel.winfo_y() < view.content_slot.winfo_y()


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


def _fits_scroll_viewport(view, widget):
    """Actual on-screen bounds; mapped widgets can still be below the fold."""
    top = view.canvas.winfo_rooty()
    bottom = top + view.canvas.winfo_height()
    return top <= widget.winfo_rooty() and widget.winfo_rooty() + widget.winfo_height() <= bottom


def test_compact_idle_has_both_field_entries_immediately_visible(shell):
    root, view, _ = shell
    root.geometry('640x560')
    settle(root)
    assert view.scope_panel.winfo_ismapped()
    assert view.scope_panel.winfo_y() < view.content_slot.winfo_y()
    assert view.scope_panel.winfo_height() <= 125, 'Compact summary must not crowd out the main task'
    assert _fits_scroll_viewport(view, view.npwp_entry)
    assert _fits_scroll_viewport(view, view.year_entry)
    assert _fits_scroll_viewport(view, view.scope_title), 'Compact summary heading must not be scrolled half away'


def test_compact_active_progress_is_visible_without_scrolling(shell):
    root, view, _ = shell
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('synthetic-job', '0000000000000001', '2025')
    state = reduce_export(state, {'job_id':'synthetic-job','type':'progress','stage':'details',
        'percent':66,'processed':6,'total':9,'verified':5},controller_active=True)
    view.render(state, active=True)
    root.geometry('640x560')
    settle(root)
    assert _fits_scroll_viewport(view, view.progress_title_label)
    assert _fits_scroll_viewport(view, view.bar)
    assert _fits_scroll_viewport(view, view.scope_title)
    assert view.percent.get() == '66%'


def test_tiny_initial_window_shows_npwp_entry_without_scroll_action(shell):
    root, view, _ = shell
    root.geometry('540x390')
    settle(root)
    assert view.scope_panel.winfo_ismapped(), 'The summary remains reachable by scrolling up'
    assert _fits_scroll_viewport(view, view.npwp_entry)
    caption = next(widget for widget in view.npwp_field.winfo_children()
                   if widget.winfo_class() == 'TLabel' and widget.cget('text') == 'NPWP (16 digit)')
    assert _fits_scroll_viewport(view, caption), 'Tiny window must keep the first field label with its entry'


def test_compact_terminal_result_is_visible_without_manual_scroll(shell):
    root, view, _ = shell
    from spt_desktop.ui_state import begin_export, reduce_export
    state = begin_export('synthetic-job', '0000000000000001', '2025')
    view.render(state,active=True)
    state = reduce_export(state, {'job_id':'synthetic-job', 'type':'terminal',
        'status':'PARTIAL', 'percent':90, 'output':'synthetic-output'},controller_active=False)
    view.render(state,active=False)
    root.geometry('640x560')
    settle(root)
    assert view.result_panel.winfo_ismapped()
    assert _fits_scroll_viewport(view, view.result_title_label)
    assert _fits_scroll_viewport(view, view.result_status_label)
