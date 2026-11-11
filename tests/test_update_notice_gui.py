"""Windows Tk notification integration; never connects to live release or taxpayer systems."""
import tkinter as tk

from spt_desktop import app as gui
from spt_desktop import update_notice
from support_gui import Controller, button


def test_update_button_reports_unconfigured_endpoint_offline(tmp_path, monkeypatch):
    monkeypatch.setattr(update_notice, 'MANIFEST_URL', '')
    messages = []
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, text, **kw: messages.append((title, text)))
    monkeypatch.setattr(gui, 'read_build_info',
                        lambda: (_ for _ in ()).throw(AssertionError('No build read expected')))
    root = tk.Tk()
    try:
        app = gui.App(root, tmp_path, controller=Controller())
        root.update()
        dialog = app.settings()
        assert button(dialog, 'Cek pembaruan') is not None
        button(dialog, 'Cek pembaruan').invoke()
        assert len(messages) == 1 and messages[0][0] == 'Pembaruan belum aktif'
        assert app._update_after is None and not app._update_pending
        assert root.grab_current() is dialog
        app._dispose()
    finally:
        root.destroy()


def test_update_notice_is_nonmodal_and_does_not_change_job_state(tmp_path, monkeypatch):
    monkeypatch.setattr(update_notice, 'MANIFEST_URL', '')
    root = tk.Tk()
    try:
        controller = Controller()
        app = gui.App(root, tmp_path, controller=controller)
        root.update()
        notice = update_notice.UpdateNotice('2026.11.1', '2026-11-11',
                                            'Perbaikan stabilitas', 'b' * 40, '420', 1)
        app._show_update_notice(notice)
        root.update_idletasks()
        assert app._update_dialog is not None
        assert root.grab_current() is None
        assert controller.active is False
        app._dispose()
        assert app._update_dialog is None
    finally:
        root.destroy()
