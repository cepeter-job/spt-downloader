"""Runner-only real Tk dialogs; no scraper, credentials or live taxpayer records."""
from contextlib import contextmanager
import gc
import tkinter as tk
import pytest

from spt_desktop.app import App


class ConsentController:
    active = False
    operation = 'export'
    job_id = 'synthetic-job'

    def __init__(self, payload):
        self.payload = payload
        self.replies = []
        self.reads = []
        self.stopped = False
        self.starts = 0

    def start(self, *args):
        assert not self.active
        self.starts += 1
        self.job_id = 'synthetic-job' if self.starts == 1 else 'next-synthetic-job'
        self.active = True
        return self.job_id

    def read_request(self, event):
        assert event['job_id'] == self.job_id
        self.reads.append(event)
        return self.payload

    def respond(self, kind, request_id, payload):
        self.replies.append((kind, request_id, payload))
        return True

    def poll(self):
        return self.active

    def stop(self):
        self.stopped = True

    def close(self):
        pass


def consent_event(controller, kind='selection', request_id='a' * 32):
    return {'job_id': controller.job_id, 'type': kind + '_required', 'request_id': request_id,
            'stage': kind, 'percent': 20 if kind == 'selection' else 99, 'message': 'Synthetic consent request'}


@contextmanager
def window(tmp_path, payload, kind='selection'):
    assert hasattr(App, 'selection_dialog') and hasattr(App, 'overwrite_dialog'), 'Consent dialogs are missing'
    root = tk.Tk()
    root.withdraw()
    callback_errors = []
    root.report_callback_exception = lambda *error: callback_errors.append(error)
    controller = ConsentController(payload)
    app = App(root, tmp_path, controller=controller)
    app.npwp.set('0000000000000001');app.year.set('2025');app.start()
    event = consent_event(controller, kind)
    try:
        app.on_event(event)
        root.update()
        dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
        assert len(dialogs) == 1
        yield root, app, controller, dialogs[0]
    finally:
        app._dispose()
        for token in root.tk.call('after', 'info'):
            root.after_cancel(token)
        if hasattr(app, '_close_interaction'):
            app._close_interaction()
        root.destroy()
        del app
        gc.collect()
        assert not callback_errors, f'Tk callback errors: {callback_errors!r}'


def widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from widgets(child)


def button(dialog, text):
    return next(widget for widget in widgets(dialog)
                if widget.winfo_class() == 'TButton' and widget.cget('text') == text)


def select_first(root, dialog):
    tree = next(widget for widget in widgets(dialog) if widget.winfo_class() == 'Treeview')
    tree.selection_set(tree.get_children()[0])
    tree.event_generate('<<TreeviewSelect>>')
    root.update()
    return tree


def records():
    return {'records': [
        {'record_id': '21-january', 'meta': {'Jenis Pajak': 'PPh Pasal 21/26', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}},
        {'record_id': '21-february', 'meta': {'Jenis Pajak': 'PPh Pasal 21/26', 'Masa Pajak': 'Februari 2025', 'Model SPT': 'Normal'}},
        {'record_id': 'badan-amendment', 'meta': {'Jenis Pajak': 'PPh Badan', 'Masa Pajak': 'Januari - Desember 2025', 'Model SPT': 'Amendment 001'}},
    ]}


def test_selection_starts_empty_and_search_sends_only_the_clicked_return(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        tree = next(widget for widget in widgets(dialog) if widget.winfo_class() == 'Treeview')
        button = next(widget for widget in widgets(dialog)
                      if widget.winfo_class() == 'TButton' and widget.cget('text') == 'Sedot SPT terpilih')
        assert not tree.selection() and button.instate(['disabled']) and not controller.replies
        entry = next(widget for widget in widgets(dialog) if widget.winfo_class() == 'TEntry')
        entry.insert(0, 'Februari')
        root.update()
        assert len(tree.get_children()) == 1
        tree.selection_set(tree.get_children()[0])
        tree.event_generate('<<TreeviewSelect>>')
        root.update()
        assert not button.instate(['disabled'])
        button.invoke()
        root.update()
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': ['21-february']})]
        assert app._ui_state.selected_count == 1 and app.view.scope_selected.get() == '1'
        assert not dialog.winfo_exists() and not controller.stopped


def test_closing_selection_cancels_without_implicitly_selecting_every_record(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
        root.update()
        assert controller.stopped and not controller.replies and not dialog.winfo_exists()


def test_overwrite_dialog_defaults_to_preserving_existing_files(tmp_path):
    with window(tmp_path, {'files': ['resume.xlsx', 'SPT Masa 21/SPT_21_Januari 2025.xlsx']}, 'overwrite') as (root, app, controller, dialog):
        buttons = [widget for widget in widgets(dialog) if widget.winfo_class() == 'TButton']
        decline = next(widget for widget in buttons if widget.cget('text') == 'Jangan ganti')
        assert not controller.replies
        decline.invoke()
        root.update()
        assert controller.replies == [('overwrite', 'a' * 32, {'overwrite': False})]
        assert app._ui_state.view_state == 'cancellation_pending'
        assert app._ui_state.terminal_status is None
        assert not dialog.winfo_exists()


def test_selection_uses_local_row_ids_and_preserves_the_observed_identifier(tmp_path):
    identifier = '::synthetic {return}; [literal] / \\ identifier'
    payload = {'records': [{'record_id': identifier, 'meta': {'Jenis Pajak': 'PPh Badan'}}]}
    with window(tmp_path, payload) as (root, app, controller, dialog):
        tree = select_first(root, dialog)
        assert identifier not in tree.get_children()
        button(dialog, 'Sedot SPT terpilih').invoke()
        assert controller.replies == [('selection', 'a' * 32, {'selected_ids': [identifier]})]


def test_filtering_clears_hidden_selections_before_consent(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        tree = select_first(root, dialog)
        entry = next(widget for widget in widgets(dialog) if widget.winfo_class() == 'TEntry')
        entry.insert(0, 'februari')
        root.update()
        assert len(tree.get_children()) == 1 and not tree.selection()
        submit = button(dialog, 'Sedot SPT terpilih')
        assert submit.instate(['disabled'])
        submit.invoke()
        assert not controller.replies


def test_empty_inventory_cannot_implicitly_authorize_all_returns(tmp_path):
    with window(tmp_path, {'records': []}) as (root, app, controller, dialog):
        assert button(dialog, 'Sedot SPT terpilih').instate(['disabled'])
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
        assert controller.stopped and not controller.replies


@pytest.mark.parametrize('kind,payload', [
    ('selection', records()), ('overwrite', {'files': ['resume.xlsx']})])
def test_stop_destroys_pending_consent_and_does_not_allow_a_late_reopen(tmp_path, kind, payload):
    with window(tmp_path, payload, kind) as (root, app, controller, dialog):
        app.stop()
        assert controller.stopped and not dialog.winfo_exists() and not controller.replies
        assert root.grab_current() is None
        app.on_event(consent_event(controller, kind, 'b' * 32))
        root.update()
        assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
        assert len(controller.reads) == 1 and not controller.replies


@pytest.mark.parametrize('kind,payload', [
    ('selection', records()), ('overwrite', {'files': ['resume.xlsx']})])
def test_terminal_destroys_pending_consent_before_another_job_can_start(tmp_path, kind, payload):
    with window(tmp_path, payload, kind) as (root, app, controller, dialog):
        controller.active = False
        app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'ERROR',
                      'percent': 20, 'output': None, 'message': 'Synthetic terminal failure'})
        root.update()
        assert not dialog.winfo_exists() and root.grab_current() is None
        assert not controller.replies and not controller.stopped


@pytest.mark.parametrize('kind,payload', [
    ('selection', records()), ('overwrite', {'files': ['resume.xlsx']})])
def test_dialog_callback_cannot_authorize_a_different_job(tmp_path, kind, payload):
    with window(tmp_path, payload, kind) as (root, app, controller, dialog):
        if kind == 'selection':
            select_first(root, dialog)
            approve = button(dialog, 'Sedot SPT terpilih')
        else:
            approve = button(dialog, 'Ganti file tersebut')
        controller.job_id = 'next-synthetic-job'
        approve.invoke()
        root.update()
        assert not controller.replies and not controller.stopped
        assert not dialog.winfo_exists()


def test_closing_an_old_selection_dialog_does_not_stop_the_new_job(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        controller.job_id = 'next-synthetic-job'
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
        assert not controller.stopped and not controller.replies and not dialog.winfo_exists()


def test_duplicate_selection_requests_keep_one_dialog_and_cannot_reopen_after_reply(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        tree = select_first(root, dialog)
        selected = tree.selection()
        app.on_event(consent_event(controller))
        root.update()
        assert [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)] == [dialog]
        assert tree.selection() == selected and len(controller.reads) == 1
        button(dialog, 'Sedot SPT terpilih').invoke()
        app.on_event(consent_event(controller))
        root.update()
        assert not any(isinstance(child, tk.Toplevel) for child in root.winfo_children())
        assert len(controller.replies) == 1 and len(controller.reads) == 1


def test_foreign_request_does_not_replace_the_pending_dialog(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        app.on_event({**consent_event(controller, 'overwrite', 'b' * 32), 'job_id': 'foreign-job'})
        root.update()
        assert dialog.winfo_exists() and len(controller.reads) == 1
        assert not controller.replies and not controller.stopped


def test_closing_filtered_selection_keeps_the_next_job_search_independent(tmp_path):
    with window(tmp_path, records()) as (root, app, controller, dialog):
        entry = next(widget for widget in widgets(dialog) if widget.winfo_class() == 'TEntry')
        entry.insert(0, 'Februari')
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
        assert root.grab_current() is None
        controller.active = False
        app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                      'percent': 20, 'message': 'Synthetic cancellation completed'})
        controller.stopped = False
        app.start()
        assert controller.job_id == 'next-synthetic-job'
        app.on_event(consent_event(controller, request_id='b' * 32))
        root.update()
        reopened = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
        assert len(reopened) == 1
        new_entry = next(widget for widget in widgets(reopened[0]) if widget.winfo_class() == 'TEntry')
        tree = next(widget for widget in widgets(reopened[0]) if widget.winfo_class() == 'Treeview')
        assert new_entry.get() == '' and len(tree.get_children()) == 3
        new_entry.insert(0, 'Februari')
        root.update()
        assert len(tree.get_children()) == 1 and not tree.selection()
        assert not controller.replies and not controller.stopped


def test_only_the_explicit_overwrite_button_authorizes_replacement(tmp_path):
    with window(tmp_path, {'files': ['resume.xlsx']}, 'overwrite') as (root, app, controller, dialog):
        assert not controller.replies
        button(dialog, 'Ganti file tersebut').invoke()
        root.update()
        assert controller.replies == [('overwrite', 'a' * 32, {'overwrite': True})]
        assert not dialog.winfo_exists() and not controller.stopped


def test_closing_overwrite_preserves_existing_files(tmp_path):
    with window(tmp_path, {'files': ['resume.xlsx']}, 'overwrite') as (root, app, controller, dialog):
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
        root.update()
        assert controller.replies == [('overwrite', 'a' * 32, {'overwrite': False})]
        assert app._ui_state.view_state == 'cancellation_pending'
        assert app._ui_state.terminal_status is None
        assert not dialog.winfo_exists()


@pytest.mark.parametrize('kind,payload', [
    ('selection', records()), ('overwrite', {'files': ['resume.xlsx']})])
def test_rejected_consent_dismisses_without_cancelling_terminal_cleanup(tmp_path, monkeypatch, kind, payload):
    with window(tmp_path, payload, kind) as (root, app, controller, dialog):
        monkeypatch.setattr(controller, 'respond', lambda *args: False)
        if kind == 'selection':
            select_first(root, dialog)
            approve = button(dialog, 'Sedot SPT terpilih')
        else:
            approve = button(dialog, 'Ganti file tersebut')
        approve.invoke()
        root.update()
        assert app._ui_state.selected_count is None
        assert not dialog.winfo_exists() and not controller.replies and not controller.stopped
        controller.active = False
        app.on_event({'job_id': controller.job_id, 'type': 'terminal', 'status': 'ERROR',
                      'percent': 20, 'output': None, 'message': 'Synthetic original worker failure'})
        assert app.status.get() == 'ERROR · Synthetic original worker failure'


def test_overwrite_displays_the_exact_prior_export_folder(tmp_path):
    folder = r'C:\Users\SYNTHETIC_USER\Downloads\SYNTHETIC_WP\2025\SYNTHETIC_EXPORT'
    with window(tmp_path, {'files': ['resume.xlsx'], 'folder': folder}, 'overwrite') as (root, app, controller, dialog):
        visible_text = [str(widget.cget('text')) for widget in widgets(dialog) if 'text' in widget.keys()]
        assert any(folder in text for text in visible_text)
        assert not controller.replies
