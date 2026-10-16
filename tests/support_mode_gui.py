"""Synthetic mode gui helpers; no collected tests or shared mutable test state."""
import gc
import json
import threading
import tkinter as tk
import pytest


CAPTIONS = ('DOM', 'JSON-hybrid (pilot)')


class StartInput:
    def __init__(self, job):
        self.job = job
        self.first = True
        self.release = threading.Event()

    def readline(self, limit):
        if self.first:
            self.first = False
            return json.dumps({'job_id': self.job, 'command': 'start'}) + '\n'
        self.release.wait(10)
        return ''


def descendants(widget):
    for child in widget.winfo_children():
        yield child
        yield from descendants(child)


def mode_control(dialog):
    matches = [w for w in descendants(dialog) if w.winfo_class() == 'TCombobox'
               and tuple(w.cget('values')) == CAPTIONS]
    assert len(matches) == 1, 'Real DOM / JSON-hybrid mode widget is missing: intentional feature RED'
    return matches[0]


def button(dialog, caption):
    return next(w for w in descendants(dialog) if w.winfo_class() == 'TButton' and w.cget('text') == caption)


@pytest.fixture
def window(tmp_path, monkeypatch):
    from spt_desktop import app as gui
    from support_gui import Controller
    class ModeController(Controller):
        def start(self, npwp, year, browser, headless, *, detail_source='dom'):
            self.exports.append((npwp, year, browser, headless, detail_source))
            self.active = True
            self.job_id = 'synthetic-mode-window'
            return self.job_id
    def forbidden(*args):
        raise AssertionError('Mode control must not access credentials')
    monkeypatch.setattr(gui, 'save_login', forbidden)
    monkeypatch.setattr(gui, 'delete_login', forbidden)
    root = tk.Tk()
    controller = ModeController()
    app = None
    try:
        root.withdraw()
        app = gui.App(root, tmp_path, controller)
        yield root, app, controller, tmp_path
    finally:
        controller.active = False
        if app is not None:
            app._dispose()
        for callback in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(callback)
        root.destroy()
        del app
        gc.collect()
