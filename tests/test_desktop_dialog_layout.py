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


OVERWRITE_FOLDER = r'C:\Users\SYNTHETIC_USER\Downloads\SYNTHETIC_EXPORT'


def open_overwrite(active_app, payload=None):
    root, app, controller = active_app
    controller.payload = ({'files': ['SPT_Badan_2025_Normal.xlsx'], 'folder': OVERWRITE_FOLDER}
                          if payload is None else payload)
    app.on_event(consent_event(controller, 'overwrite'))
    settle(root)
    return app._interaction['dialog']


@pytest.mark.parametrize('folder', [None, '', ' \t\n', 7, False, [], {}])
def test_blank_or_nonstring_folder_never_opens_confirmation(active_app, folder):
    root, app, controller = active_app
    controller.payload = {'files': ['SPT_Badan_2025_Normal.xlsx'], 'folder': folder}
    app.on_event(consent_event(controller, 'overwrite'))
    settle(root)
    assert controller.stopped and controller.replies == []
    assert app._interaction is None
    assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
    assert app._ui_state.terminal_status is None
    assert 'Folder hasil sebelumnya belum tersedia. Keputusan penggantian belum dikirim.' in app.status.get()


def test_missing_folder_is_not_defaulted(active_app):
    root, app, controller = active_app
    payload = {'files': ['SPT_Badan_2025_Normal.xlsx']}
    controller.payload = payload
    app.on_event(consent_event(controller, 'overwrite'))
    settle(root)
    assert app._interaction is None and controller.replies == [] and controller.stopped
    assert payload == {'files': ['SPT_Badan_2025_Normal.xlsx']}
    assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
    assert app._ui_state.terminal_status is None


@pytest.mark.parametrize('folder', [None, ' ', OVERWRITE_FOLDER])
def test_stale_malformed_folder_cannot_stop_new_job(active_app, monkeypatch, folder):
    root, app, controller = active_app
    event = consent_event(controller, 'overwrite')
    def stale_read(request):
        controller.reads.append(request)
        controller.job_id = 'new-synthetic-job'
        return {'files': ['SPT_Badan_2025_Normal.xlsx'], 'folder': folder}
    monkeypatch.setattr(controller, 'read_request', stale_read)
    app.on_event(event)
    settle(root)
    assert controller.job_id == 'new-synthetic-job' and controller.active
    assert not controller.stopped and not controller.replies and app._interaction is None
    assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
    read_count = len(controller.reads)
    app.on_event(event)
    assert len(controller.reads) == read_count, 'Foreign events are rejected before private payload reads'


@pytest.mark.parametrize('folder', [OVERWRITE_FOLDER, '  ' + OVERWRITE_FOLDER + '  '])
def test_long_readonly_values_remain_literal_and_reachable(active_app, folder):
    root, app, controller = active_app
    files = ['SPT Masa 21/' + 'bagian-' * 90 + 'Januari_Normal.xlsx',
             '::synthetic {file}; [literal] / Ω.xlsx', 'resume.xlsx', 'resume.xlsx']
    dialog = open_overwrite(active_app, {'files': files, 'folder': folder})
    field = named_widget(dialog, 'folder')
    tree = named_widget(dialog, 'files')
    assert field.instate(['readonly']) and field.get() == folder
    field.delete(0, 'end')
    field.insert(0, 'must-not-replace-folder')
    field.selection_range(0, 'end')
    assert field.get() == folder and not controller.replies
    assert str(tree.cget('selectmode')) == 'none'
    assert [tree.item(iid, 'values')[0] for iid in tree.get_children()] == files
    assert label_text(named_widget(dialog, 'file_count')) == '4 file akan diganti.'
    assert len(tree.get_children()) == len(files)


@pytest.mark.parametrize('action,expected', [
    ('escape', False), ('x', False), ('alt-s', None), ('approve-click', True),
    ('approve-Return', True), ('approve-space', True), ('decline-Return', False), ('decline-space', False),
])
def test_overwrite_keyboard_decisions_preserve_protocol(active_app, action, expected):
    root, app, controller = active_app
    dialog = open_overwrite(active_app)
    safe = named_widget(dialog, 'decline')
    approve = named_widget(dialog, 'confirm')
    assert root.focus_get() is safe, 'Opening the dialog must not focus approval'
    assert not controller.replies
    if action == 'escape':
        safe.event_generate('<Escape>')
    elif action == 'x':
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
    elif action == 'alt-s':
        named_widget(dialog, 'folder').focus_set()
        root.update()
        named_widget(dialog, 'folder').event_generate('<Alt-s>')
    elif action == 'approve-click':
        approve.invoke()
    else:
        control, key = action.split('-', 1)
        target = approve if control == 'approve' else safe
        target.focus_set()
        root.update()
        target.event_generate(f'<KeyPress-{key}>')
    settle(root)
    assert not dialog.winfo_exists() and app._interaction is None
    if expected is None:
        assert controller.stopped and controller.replies == []
        assert app._ui_state.view_state == 'stopping'
    else:
        assert controller.replies == [('overwrite', 'a' * 32, {'overwrite': expected})]
        assert not controller.stopped
        assert app._ui_state.view_state == ('publishing' if expected else 'cancellation_pending')
    assert app._ui_state.terminal_status is None
    app.on_event(consent_event(controller, 'overwrite'))
    assert app._interaction is None
    assert len(controller.replies) == (0 if expected is None else 1)


@pytest.mark.parametrize('response', ['false', 'io', 'switched-io'])
def test_overwrite_response_false_and_exception_do_not_fabricate_results(active_app, monkeypatch, response):
    root, app, controller = active_app
    dialog = open_overwrite(active_app)
    before, status = app._ui_state, app.status.get()
    def respond(*args):
        if response == 'false':
            return False
        if response == 'switched-io':
            controller.job_id = 'replacement-synthetic-job'
        raise OSError('Synthetic reply failure')
    monkeypatch.setattr(controller, 'respond', respond)
    named_widget(dialog, 'confirm').invoke()
    settle(root)
    assert app._interaction is None and not dialog.winfo_exists()
    assert not controller.replies and app._ui_state.terminal_status is None
    assert app._ui_state.output is None and app._ui_state.selected_count == before.selected_count
    if response == 'io':
        assert controller.stopped and app._ui_state.view_state == 'stopping'
    else:
        assert not controller.stopped and app._ui_state == before and app.status.get() == status


@pytest.mark.parametrize('width,height', [(800, 520), (640, 560), (540, 390)])
def test_overwrite_layout_keeps_actions_visible_and_paths_reachable(active_app, width, height):
    root, app, controller = active_app
    folder = OVERWRITE_FOLDER + '\\' + 'synthetic-segment-' * 30
    files = [f'synthetic/{index:03}-' + 'long-part-' * 40 + '.xlsx' for index in range(45)]
    dialog = open_overwrite(active_app, {'files': files, 'folder': folder})
    dialog.geometry(f'{width}x{height}')
    settle(root)
    actions = named_widget(dialog, 'actions')
    viewport = named_widget(dialog, 'body_viewport')
    field = named_widget(dialog, 'folder')
    tree = named_widget(dialog, 'files')
    assert visible_in(dialog, actions)
    assert visible_in(dialog, named_widget(dialog, 'decline'))
    assert visible_in(dialog, named_widget(dialog, 'confirm'))
    assert viewport.winfo_rooty() + viewport.winfo_height() <= actions.winfo_rooty()
    field.focus_set()
    settle(root)
    assert visible_in(viewport, field)
    field.xview_moveto(1)
    assert field.xview()[1] == 1 and field.get() == folder
    for control in (field, tree):
        control.focus_set()
        root.update()
        control.event_generate('<Return>')
        root.update()
    assert not controller.replies
    tree.xview_moveto(1)
    tree.yview_moveto(1)
    root.update()
    assert tree.xview()[0] > 0 and tree.xview()[1] == 1
    assert tree.yview()[0] > 0 and tree.yview()[1] == 1
    assert tree.bbox('file-44'), 'The last entry must remain reachable'
    assert [tree.item(iid, 'values')[0] for iid in tree.get_children()] == files
    assert label_text(named_widget(dialog, 'file_count')) == '45 file akan diganti.'


def test_dialog_close_cancels_only_owned_callbacks(active_app, monkeypatch):
    root, app, controller = active_app
    dialog = open_overwrite(active_app)
    sentinel = root.after(60000, lambda: None)
    before = set(root.tk.splitlist(root.tk.call('after', 'info')))
    for _ in range(20):
        dialog.event_generate('<Configure>')
    token = app._interaction['layout_after']
    assert token and set(root.tk.splitlist(root.tk.call('after', 'info'))) - before == {token}
    app._close_interaction()
    settle(root)
    baseline_count = len(root.tk.splitlist(root.tk.call('after', 'info')))
    original_start = controller.start
    def start_unique(*args, **kwargs):
        original_start(*args, **kwargs)
        controller.job_id = f'synthetic-overwrite-cycle-{controller.starts}'
        return controller.job_id
    monkeypatch.setattr(controller, 'start', start_unique)
    for ordinal in range(25):
        controller.active = False
        app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                      'percent': 90, 'output': None, 'message': 'Synthetic lifecycle complete'})
        app.start()
        app.on_event(consent_event(controller, 'overwrite', request_id=f'{ordinal:032x}'))
        root.update_idletasks()
        interaction = app._interaction
        assert interaction is not None
        modal = interaction['dialog']
        modal.event_generate('<Configure>')
        pending = interaction['layout_after']
        app._close_interaction()
        assert interaction['layout_after'] is None and interaction['bindings'] == [] and interaction['traces'] == []
        after = set(root.tk.splitlist(root.tk.call('after', 'info')))
        assert sentinel in after and (pending is None or pending not in after)
        assert not modal.winfo_exists() and root.grab_current() is None
    controller.active = False
    app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                  'percent': 90, 'output': None, 'message': 'Synthetic lifecycle complete'})
    settle(root)
    assert len(root.tk.splitlist(root.tk.call('after', 'info'))) == baseline_count
    assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
    assert not controller.replies and not controller.stopped
    root.after_cancel(sentinel)


def _tab_to_widget(root, start, target):
    start.focus_force()
    root.update()
    for _ in range(12):
        if root.focus_get() is target:
            return
        root.focus_get().event_generate('<Tab>')
        root.update()
    pytest.fail(f'Keyboard traversal did not reach {target.winfo_name()}')


@pytest.mark.parametrize('filtered', [False, True])
def test_fresh_selection_keyboard_navigation_can_authorize_only_at_button(active_app, filtered):
    root, app, controller = active_app
    dialog = open_selection(active_app)
    entry, tree = named_widget(dialog, 'search'), named_widget(dialog, 'records')
    if filtered:
        _tab_to_widget(root, entry, tree)
        tree.event_generate('<KeyPress-Down>')
        tree.event_generate('<KeyRelease-Down>')
        settle(root)
        assert tree.selection()
        _tab_to_widget(root, tree, entry)
        entry.insert(0, 'januari')
        settle(root)
    assert not tree.selection() and named_widget(dialog, 'confirm').instate(['disabled'])
    _tab_to_widget(root, entry, tree)
    first = tree.get_children()[0]
    tree.event_generate('<KeyPress-Down>')
    tree.event_generate('<KeyRelease-Down>')
    settle(root)
    assert tree.focus() == first and tree.selection() == (first,)
    assert named_widget(dialog, 'focused_id').get() == tree.set(first, 'identifier')
    assert not controller.replies and not controller.stopped
    expected = tree.set(first, 'identifier')
    confirm = named_widget(dialog, 'confirm')
    _tab_to_widget(root, tree, confirm)
    confirm.event_generate('<Return>')
    root.update()
    assert controller.replies == [('selection', 'a' * 32, {'selected_ids': [expected]})]


@pytest.mark.parametrize('size', [(640, 560), (540, 390)])
def test_overwrite_path_suffix_is_reachable_by_keyboard_without_consent(active_app, size):
    root, app, controller = active_app
    files = ['SPT Masa PPN/' + 'synthetic-long-part-' * 80 + 'UNIQUE_SUFFIX.xlsx'] * 2
    dialog = open_overwrite(active_app, {'files': files, 'folder': OVERWRITE_FOLDER})
    dialog.geometry(f'{size[0]}x{size[1]}')
    settle(root)
    field, tree = named_widget(dialog, 'folder'), named_widget(dialog, 'files')
    _tab_to_widget(root, field, tree)
    before = tree.xview()
    tree.event_generate('<Control-Right>')
    settle(root)
    assert tree.xview()[0] > before[0]
    tree.event_generate('<Control-Left>')
    settle(root)
    assert tree.xview()[0] == before[0]
    tree.event_generate('<Control-End>')
    settle(root)
    assert tree.xview()[0] > before[0] and tree.xview()[1] == 1.0
    tree.event_generate('<Control-Home>')
    settle(root)
    assert tree.xview()[0] == 0.0
    assert [tree.set(iid, 'file') for iid in tree.get_children()] == files
    assert field.get() == OVERWRITE_FOLDER
    assert label_text(named_widget(dialog, 'file_count')) == '2 file akan diganti.'
    assert not tree.selection() and not controller.replies and not controller.stopped
    decline = named_widget(dialog, 'decline')
    _tab_to_widget(root, tree, decline)
    decline.event_generate('<Return>')
    root.update()
    assert controller.replies == [('overwrite', 'a' * 32, {'overwrite': False})]


def test_overwrite_keyboard_navigation_reaches_last_file_without_consent(active_app):
    root, app, controller = active_app
    files = [f'SPT Masa PPN/SYNTHETIC_{index:03}_Normal.xlsx' for index in range(101)]
    controller.payload = {'files': files, 'folder': OVERWRITE_FOLDER}
    app.on_event(consent_event(controller, 'overwrite'))
    settle(root)
    dialog = app._interaction['dialog']
    safe_button, tree = named_widget(dialog, 'decline'), named_widget(dialog, 'files')
    assert root.focus_get() is safe_button
    _tab_to_widget(root, safe_button, tree)
    tree.event_generate('<KeyPress-Down>')
    tree.event_generate('<KeyRelease-Down>')
    root.update()
    assert tree.focus() == 'file-1'
    for _ in range(99):
        tree.event_generate('<KeyPress-Down>')
        tree.event_generate('<KeyRelease-Down>')
        root.update()
    assert tree.focus() == 'file-100' and tree.bbox('file-100')
    assert [tree.set(iid, 'file') for iid in tree.get_children()] == files
    assert label_text(named_widget(dialog, 'file_count')) == '101 file akan diganti.'
    assert named_widget(dialog, 'folder').get() == OVERWRITE_FOLDER
    assert not tree.selection() and not controller.replies and not controller.stopped
