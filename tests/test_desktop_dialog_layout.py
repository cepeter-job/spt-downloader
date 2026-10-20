"""Real, synthetic dialog contracts; execute only on the GitHub Windows runner."""
from dataclasses import replace
import gc
import tkinter as tk
from tkinter import ttk

import pytest

from support_gui import ConsentController, consent_event, named_widget, widgets


NPWP = '0000000000000001'


def settle(root):
    done = tk.BooleanVar(root)
    root.after(250, lambda: done.set(True))
    root.wait_variable(done)
    root.update_idletasks()


def label_text(widget):
    variable = str(widget.cget('textvariable'))
    return str(widget.getvar(variable)) if variable else str(widget.cget('text'))


def visible_in(container, widget):
    left, top = container.winfo_rootx(), container.winfo_rooty()
    return (widget.winfo_ismapped() and left <= widget.winfo_rootx()
            and top <= widget.winfo_rooty()
            and widget.winfo_rootx() + widget.winfo_width() <= left + container.winfo_width()
            and widget.winfo_rooty() + widget.winfo_height() <= top + container.winfo_height())


@pytest.fixture
def active_app(tmp_path):
    from spt_desktop.app import App
    root = tk.Tk()
    errors = []
    root.report_callback_exception = lambda *error: errors.append(error)
    controller = ConsentController({})
    app = App(root, tmp_path, controller=controller)
    root.geometry('900x700')
    app.npwp.set(NPWP)
    app.year.set('2025')
    app.start()
    settle(root)
    root.focus_force()
    try:
        yield root, app, controller
    finally:
        app._close_interaction()
        app._dispose()
        controller.active = False
        for token in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(token)
        root.destroy()
        del app
        gc.collect()
        assert not errors, f'Tk callback errors: {errors!r}'


def records():
    return [
        {'record_id': '21-january', 'meta': {'Jenis Pajak': 'PPh Pasal 21/26', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}},
        {'record_id': '21-february', 'meta': {'Jenis Pajak': 'PPh Pasal 21/26', 'Masa Pajak': 'Februari 2025', 'Model SPT': 'Normal'}},
        {'record_id': 'badan-normal', 'meta': {'Jenis Pajak': 'PPh Badan', 'Masa Pajak': 'Januari - Desember 2025', 'Model SPT': 'Normal'}},
    ]


def open_selection(active_app, payload=None, request_id='a' * 32):
    root, app, controller = active_app
    controller.payload = {'records': records()} if payload is None else payload
    app.on_event(consent_event(controller, request_id=request_id))
    settle(root)
    dialog = app._interaction['dialog']
    dialog.deiconify()
    dialog.focus_force()
    settle(root)
    return dialog


def test_selection_context_uses_matching_job_snapshot(active_app):
    root, app, controller = active_app
    app.npwp.set('0000000000000002')
    app.year.set('2024')
    dialog = open_selection(active_app, {'records': []})
    scope = label_text(named_widget(dialog, 'scope'))
    assert scope == 'NPWP permintaan: 0000000000000001\nTahun pajak permintaan: 2025'
    assert '0000000000000002' not in scope and '2024' not in scope
    assert controller.replies == []


@pytest.mark.parametrize('missing', [True, False])
def test_selection_missing_snapshot_is_not_guessed_from_form(active_app, missing):
    root, app, controller = active_app
    original = app._ui_state
    app._ui_state = None if missing else replace(original, job_id='another-job')
    controller.payload = {'records': []}
    try:
        # The public builder's fallback is independent of on_event's job/state rejection.
        app.selection_dialog(consent_event(controller))
        settle(root)
        dialog = app._interaction['dialog']
        assert label_text(named_widget(dialog, 'scope')) == 'Konteks permintaan tidak tersedia'
        assert not controller.replies and not controller.stopped
    finally:
        app._ui_state = original


def test_filter_reset_survives_empty_tree_events(active_app):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    tree = named_widget(dialog, 'records')
    search = named_widget(dialog, 'search')
    tree.selection_set('record-0')
    root.update()
    search.insert(0, 'januari')
    settle(root)
    tree.event_generate('<<TreeviewSelect>>')
    settle(root)
    assert not tree.selection() and named_widget(dialog, 'confirm').instate(['disabled'])
    assert 'Pencarian berubah. Pilih lagi SPT yang akan diunduh.' in label_text(named_widget(dialog, 'notice'))
    tree.selection_set('record-0')
    root.update()
    assert 'Pencarian berubah.' not in label_text(named_widget(dialog, 'notice'))
    search.setvar(str(search.cget('textvariable')), ' JAnuari ')
    settle(root)
    assert not tree.selection()
    assert 'Pencarian berubah.' in label_text(named_widget(dialog, 'notice'))
    assert not controller.replies


@pytest.mark.parametrize('empty', [True, False])
def test_selection_empty_and_no_match_keep_exact_counts(active_app, empty):
    root, app, controller = active_app
    dialog = open_selection(active_app, {'records': []} if empty else None)
    if not empty:
        named_widget(dialog, 'search').insert(0, 'synthetic-no-match')
        settle(root)
    assert label_text(named_widget(dialog, 'summary')) == (
        '0 SPT dipilih · 0 dari 0 SPT ditampilkan.' if empty else '0 SPT dipilih · 0 dari 3 SPT ditampilkan.')
    assert label_text(named_widget(dialog, 'notice')) == (
        'Daftar ini tidak memuat SPT yang bisa dipilih.' if empty else 'Tidak ada SPT yang cocok dengan pencarian.')
    assert named_widget(dialog, 'confirm').instate(['disabled']) and not controller.replies


@pytest.mark.parametrize('identifier', ['::synthetic {return}; [literal] / Ω', 'x' * 512])
def test_focused_id_tracks_navigation_without_selecting(active_app, identifier):
    root, app, controller = active_app
    dialog = open_selection(active_app, {'records': [
        {'record_id': 'synthetic-first', 'meta': {}}, {'record_id': identifier, 'meta': {}}]})
    tree = named_widget(dialog, 'records')
    field = named_widget(dialog, 'focused_id')
    tree.selection_set('record-0')
    tree.focus('record-1')
    tree.event_generate('<KeyRelease-Down>')
    root.update()
    assert field.instate(['readonly']) and field.get() == identifier
    assert tree.selection() == ('record-0',) and identifier not in tree.get_children()
    field.delete(0, 'end')
    field.insert(0, 'must-not-replace-id')
    assert field.get() == identifier
    field.selection_range(0, 'end')
    assert not controller.replies
    tree.focus('record-0')
    tree.event_generate('<ButtonRelease-1>', x=0, y=0)
    root.update()
    assert field.get() == 'synthetic-first'
    named_widget(dialog, 'search').insert(0, 'no-visible-row')
    root.update()
    assert field.get() == ''


def test_alt_j_and_header_preserve_filtered_selection_and_reply_order(active_app):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    tree = named_widget(dialog, 'records')
    search = named_widget(dialog, 'search')
    search.insert(0, '2025')
    tree.selection_set(('record-2', 'record-0'))
    tree.focus('record-2')
    search.focus_set()
    root.update()
    search.event_generate('<Alt-j>')
    root.update()
    assert tree.heading('type', 'text') == 'Jenis pajak ▲'
    assert set(tree.selection()) == {'record-0', 'record-2'} and tree.focus() == 'record-2'
    assert search.get() == '2025' and root.focus_get() is search
    dialog.tk.call(tree.heading('type', 'command'))
    root.update()
    assert tree.heading('type', 'text') == 'Jenis pajak ▼'
    assert tree.focus() == 'record-2' and tree.bbox('record-2')
    named_widget(dialog, 'confirm').invoke()
    assert controller.replies == [('selection', 'a' * 32, {'selected_ids': ['21-january', 'badan-normal']})]
    assert app._ui_state.selected_count == 2


@pytest.mark.parametrize('activation', ['click', 'Return', 'space'])
def test_only_focused_submit_activation_sends_selection_once(active_app, activation):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    tree = named_widget(dialog, 'records')
    search = named_widget(dialog, 'search')
    submit = named_widget(dialog, 'confirm')
    for widget in (search, tree):
        widget.focus_set()
        root.update()
        widget.event_generate('<KeyPress-Return>')
        widget.event_generate('<KeyRelease-Return>')
        root.update()
    # Two real button events exercise the native double-click route, not a forbidden Double modifier.
    bounds = tree.bbox(tree.get_children()[0])
    if bounds:
        x, y, width, height = bounds
        for timestamp in (1000, 1100):
            tree.event_generate('<ButtonPress-1>', x=x+8, y=y+height//2, time=timestamp)
            tree.event_generate('<ButtonRelease-1>', x=x+8, y=y+height//2, time=timestamp+30)
    root.update()
    assert not controller.replies
    tree.selection_set('record-0')
    root.update()
    submit.focus_set()
    root.update()
    if activation == 'click':
        submit.invoke()
    else:
        submit.event_generate(f'<KeyPress-{activation}>')
    settle(root)
    assert controller.replies == [('selection', 'a' * 32, {'selected_ids': ['21-january']})]
    assert not dialog.winfo_exists() and not controller.stopped
    app.on_event(consent_event(controller))
    assert len(controller.replies) == 1 and app._interaction is None


@pytest.mark.parametrize('width,height', [(920, 600), (640, 560), (540, 390)])
def test_selection_layout_keeps_actions_visible_and_body_reachable(active_app, width, height):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    dialog.geometry(f'{width}x{height}')
    settle(root)
    actions = named_widget(dialog, 'actions')
    viewport = named_widget(dialog, 'body_viewport')
    search = named_widget(dialog, 'search')
    field = named_widget(dialog, 'focused_id')
    tree = named_widget(dialog, 'records')
    assert visible_in(dialog, actions)
    assert visible_in(dialog, named_widget(dialog, 'stop'))
    assert visible_in(dialog, named_widget(dialog, 'confirm'))
    assert viewport.winfo_rooty() + viewport.winfo_height() <= actions.winfo_rooty()
    assert int(ttk.Style(dialog).lookup('SPT.Dialog.Treeview', 'rowheight')) >= int(
        root.tk.call('font', 'metrics', 'SPTBody', '-linespace'))
    search.focus_set()
    root.update()
    traversal = []
    for _ in range(20):
        current = root.focus_get()
        traversal.append(current)
        current.event_generate('<Tab>')
        root.update()
    assert {search, tree, field, named_widget(dialog, 'stop'), named_widget(dialog, 'confirm')} - {named_widget(dialog, 'confirm')} <= set(traversal)
    field.focus_set()
    settle(root)
    assert visible_in(viewport, field)
    field.event_generate('<Shift-Tab>')
    root.update()
    assert root.focus_get() is tree and not controller.replies


def test_selection_reflow_preserves_data_and_owned_resources(active_app, monkeypatch):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    tree = named_widget(dialog, 'records')
    search = named_widget(dialog, 'search')
    search.insert(0, '2025')
    tree.selection_set('record-0')
    tree.focus('record-0')
    root.update()
    settle(root)
    sentinel = root.after(60000, lambda: None)
    before = set(root.tk.splitlist(root.tk.call('after', 'info')))
    for _ in range(20):
        dialog.event_generate('<Configure>')
    pending = app._interaction['layout_after']
    assert pending and pending not in before
    assert set(root.tk.splitlist(root.tk.call('after', 'info'))) - before == {pending}
    settle(root)
    assert tree.selection() == ('record-0',) and tree.focus() == 'record-0'
    assert search.get() == '2025' and named_widget(dialog, 'focused_id').get() == '21-january'
    app._close_interaction()
    settle(root)
    baseline_count = len(root.tk.splitlist(root.tk.call('after', 'info')))
    original_start = controller.start
    def start_unique(*args, **kwargs):
        original_start(*args, **kwargs)
        controller.job_id = f'synthetic-cycle-{controller.starts}'
        return controller.job_id
    monkeypatch.setattr(controller, 'start', start_unique)
    for ordinal in range(25):
        # Dismissing a modal does not clear outstanding consent. Complete the
        # prior synthetic job before starting another; keep the real guard intact.
        controller.active = False
        app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                      'percent': 20, 'output': None, 'message': 'Synthetic lifecycle complete'})
        app.start()
        app.on_event(consent_event(controller, request_id=f'{ordinal:032x}'))
        root.update_idletasks()
        interaction = app._interaction
        assert interaction is not None
        modal = interaction['dialog']
        modal.event_generate('<Configure>')
        pending = interaction['layout_after']
        traces = [(variable, token) for variable, token in interaction['traces']]
        app._close_interaction()
        assert not modal.winfo_exists() and root.grab_current() is None
        assert interaction['layout_after'] is None and interaction['bindings'] == []
        assert interaction['traces'] == []
        after = set(root.tk.splitlist(root.tk.call('after', 'info')))
        assert sentinel in after and (pending is None or pending not in after)
        for variable, token in traces:
            assert all(token not in str(entry) for entry in variable.trace_info())
    controller.active = False
    app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                  'percent': 20, 'output': None, 'message': 'Synthetic lifecycle complete'})
    settle(root)
    assert len(root.tk.splitlist(root.tk.call('after', 'info'))) == baseline_count
    assert not any(isinstance(w, tk.Toplevel) for w in root.winfo_children())
    assert not controller.replies and not controller.stopped
    root.after_cancel(sentinel)


def test_old_reflow_cannot_steal_terminal_focus(active_app):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    dialog.event_generate('<Configure>')
    interaction = app._interaction
    assert interaction['layout_after'] is not None
    root_binding = root.bind('<Alt-j>')
    controller.active = False
    app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                  'percent': 20, 'output': None, 'message': 'Synthetic cancellation'})
    settle(root)
    assert app._interaction is None and not dialog.winfo_exists()
    assert root.focus_get() is app.start_button
    assert root.bind('<Alt-j>') == root_binding
    assert not controller.replies and not controller.stopped
