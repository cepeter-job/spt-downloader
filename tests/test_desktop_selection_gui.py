"""Runner-only real Tk dialogs; no scraper, credentials or live taxpayer records."""
from contextlib import contextmanager
import gc
import tkinter as tk

from spt_desktop.app import App


class ConsentController:
    active = True
    operation = 'export'
    job_id = 'synthetic-job'

    def __init__(self, payload):
        self.payload = payload
        self.replies = []
        self.stopped = False

    def read_request(self, event):
        assert event['job_id'] == self.job_id
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


@contextmanager
def window(tmp_path, payload, kind='selection'):
    assert hasattr(App, 'selection_dialog') and hasattr(App, 'overwrite_dialog'), 'Consent dialogs are missing'
    root = tk.Tk()
    root.withdraw()
    controller = ConsentController(payload)
    app = App(root, tmp_path, controller=controller)
    event = {'job_id': controller.job_id, 'type': kind + '_required', 'request_id': 'a' * 32,
             'stage': kind, 'percent': 20 if kind == 'selection' else 99, 'message': 'Synthetic consent request'}
    try:
        app.on_event(event)
        root.update()
        dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
        assert len(dialogs) == 1
        yield root, app, controller, dialogs[0]
    finally:
        for token in root.tk.call('after', 'info'):
            root.after_cancel(token)
        if hasattr(app, '_close_interaction'):
            app._close_interaction()
        root.destroy()
        del app
        gc.collect()


def widgets(widget):
    for child in widget.winfo_children():
        yield child
        yield from widgets(child)


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
        assert not dialog.winfo_exists()