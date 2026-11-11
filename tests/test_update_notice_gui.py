"""Windows Tk notification tests; network and browser launch are stubbed."""
import tkinter as tk

from spt_desktop import app as gui
from spt_desktop import update_notice
from support_gui import Controller, button, widgets


def test_update_button_does_not_access_coretax_or_browser(tmp_path, monkeypatch):
    notices = []
    monkeypatch.setattr(gui, 'read_build_info', lambda: None)
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, text, **kw: notices.append(title))
    root = tk.Tk()
    try:
        app = gui.App(root, tmp_path, controller=Controller())
        root.update()
        settings = app.settings()
        assert button(settings, 'Cek pembaruan') is not None
        button(settings, 'Cek pembaruan').invoke()
        assert notices == ['Identitas build tidak tersedia']
        assert app._update_after is None and not app._update_pending
        assert root.grab_current() is settings
        app._dispose()
    finally:
        root.destroy()


def test_close_only_closes_notice_and_update_opens_fixed_folder(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(gui.webbrowser, 'open',
                        lambda url, new=0: opened.append((url, new)) or True)
    root = tk.Tk()
    try:
        controller = Controller()
        app = gui.App(root, tmp_path, controller=controller)
        root.update()
        notice = update_notice.UpdateNotice('b' * 40, '420', 1)
        app._show_update_notice(notice)
        root.update_idletasks()
        dialog = app._update_dialog
        labels = [w.cget('text') for w in widgets(dialog) if w.winfo_class() == 'TLabel']
        controls = sorted(w.cget('text') for w in widgets(dialog)
                          if w.winfo_class() == 'TButton')
        assert labels == ['update tersedia']
        assert controls == ['Close', 'Update']
        assert root.grab_current() is None
        button(dialog, 'Close').invoke()
        assert app._update_dialog is None and not opened

        app._show_update_notice(notice)
        dialog = app._update_dialog
        button(dialog, 'Update').invoke()
        assert opened == [(gui.UPDATE_FOLDER_URL, 2)]
        assert app._update_dialog is None
        assert controller.active is False
        app._dispose()
    finally:
        root.destroy()


def test_update_from_settings_restores_settings_grab(tmp_path, monkeypatch):
    opened = []
    monkeypatch.setattr(gui.webbrowser, 'open',
                        lambda url, new=0: opened.append(url) or True)
    root = tk.Tk()
    try:
        app = gui.App(root, tmp_path, controller=Controller())
        root.update()
        settings = app.settings()
        assert root.grab_current() is settings
        notice = update_notice.UpdateNotice('b' * 40, '420', 1)
        app._show_update_notice(notice)
        dialog = app._update_dialog
        assert root.grab_current() is dialog
        button(dialog, 'Update').invoke()
        assert opened == [gui.UPDATE_FOLDER_URL]
        assert root.grab_current() is settings
        assert settings.winfo_exists()
        app._dispose()
    finally:
        root.destroy()
