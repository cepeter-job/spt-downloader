"""Synthetic gui helpers; no collected tests or shared mutable test state."""
from contextlib import contextmanager
import gc
import tkinter as tk
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


class Controller:
    active=False
    operation='export'
    def __init__(self):self.checks=[];self.exports=[];self.stops=0;self.job_id=None
    def start_login_check(self,*args):
        self.checks.append(args);self.operation='login_check';self.active=True
        self.job_id=f'synthetic-login-{len(self.checks)}';return self.job_id
    def start(self,*args):
        self.exports.append(args);self.operation='export';self.active=True
        self.job_id=f'synthetic-export-{len(self.exports)}';return self.job_id
    def stop(self):self.stops+=1
    def poll(self):return self.active
    def close(self):self.active=False
