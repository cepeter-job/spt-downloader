"""Native settings retain credential management without a login-check operation."""
import gc
import tkinter as tk
import pytest
from spt_desktop import app as gui

ORIGIN='https://satu.intranet.pajak.go.id'
ACCOUNT='SYNTHETIC_ACCOUNT'


from support_gui import (
    Controller
)

def descendants(widget):
    for child in widget.winfo_children():
        yield child;yield from descendants(child)


def button(root,text):
    return next(widget for widget in descendants(root) if widget.winfo_class()=='TButton' and widget.cget('text')==text)


@pytest.fixture
def window(tmp_path,monkeypatch):
    gui.save_preferences(tmp_path,dict(gui.DEFAULTS,login_origin=ORIGIN,identifier=ACCOUNT))
    def deny(*args):raise AssertionError('GUI test must not read/write/delete actual Windows credentials')
    monkeypatch.setattr(gui,'save_login',deny);monkeypatch.setattr(gui,'delete_login',deny)
    root=tk.Tk();root.withdraw();ctl=Controller();app=gui.App(root,tmp_path,ctl)
    yield root,app,ctl,tmp_path
    ctl.active=False
    root.destroy()
    del app
    gc.collect()  # Tk variable disposal stays on the UI test thread.


def test_settings_has_no_login_check_controls_or_shortcut(window):
    root, app, ctl, path = window
    app.settings(); root.update_idletasks()
    labels = [widget.cget('text') for widget in descendants(root)
              if widget.winfo_class() == 'TButton']
    assert 'Cek login' not in labels
    assert 'Batalkan cek' not in labels
    assert {'Simpan', 'Hapus login', 'Tutup'} <= set(labels)
    assert not app._settings_dialog.bind('<Alt-c>')
    assert not ctl.exports and not ctl.checks
    assert not (path / 'jobs').exists()


def test_saving_password_keeps_settings_open_without_starting_a_worker(window, monkeypatch):
    root, app, ctl, path = window
    app.settings(); root.update_idletasks()
    entry = next(w for w in descendants(root) if w.winfo_class() == 'TEntry' and w.cget('show'))
    entry.insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    writes = []
    monkeypatch.setattr(gui, 'save_login', lambda *args: writes.append(args))
    button(root, 'Simpan').invoke()
    assert writes == [(ORIGIN, ACCOUNT, 'SYNTHETIC_NEW_PASSWORD_ONLY')]
    assert entry.get() == '' and app._settings_dialog.winfo_exists()
    assert not ctl.active and not ctl.exports and not ctl.checks
    assert 'SYNTHETIC_NEW_PASSWORD_ONLY' not in (path / 'preferences.json').read_text()
    assert not (path / 'jobs').exists()


def test_settings_save_preserves_previous_export_result(window):
    root, app, ctl, path = window
    previous = path / 'old-export'
    previous.mkdir()
    app._result = previous
    app.open_button.state(['!disabled'])
    export_state = app._ui_state
    app.settings(); root.update_idletasks()
    button(root, 'Simpan').invoke()
    button(root, 'Tutup').invoke()
    assert app._result == previous and app.open_button.instate(['!disabled'])
    assert app._ui_state == export_state and not ctl.active


def test_source_selftest_exercises_masked_settings_without_login_check(tmp_path):
    import json, spt_gui
    report = tmp_path / 'selftest.json'
    assert spt_gui.self_test(report) == 0
    data = json.loads(report.read_text())
    assert {'Simpan', 'Hapus login', 'Tutup'} <= set(data['gui_controls'])
    assert 'Cek login' not in data['gui_controls'] and 'Batalkan cek' not in data['gui_controls']
    assert data['credential_check_controls'] is False
    assert not data['credentials_accessed'] and not data['live_scrape']
