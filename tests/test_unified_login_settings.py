"""Origin-free settings use synthetic accounts; no native credential access."""
import gc
import json
import tkinter as tk

import pytest
from spt_desktop import app as gui
from support_gui import Controller, widgets, button

SATU = 'https://satu.intranet.pajak.go.id'
CORETAX = 'https://coretax.intranet.pajak.go.id'
ACCOUNT = 'SYNTHETIC_ACCOUNT'


class AccountController(Controller):
    def __init__(self):
        super().__init__()
        self.start_options = []
    def start(self, *args, **kwargs):
        self.start_options.append(kwargs)
        return super().start(*args)


def legacy_preferences(root):
    (root / 'preferences.json').write_text(json.dumps({
        'browser': 'msedge', 'headless': True, 'login_origin': CORETAX,
        'identifier': ACCOUNT, 'detail_source': 'dom'}), encoding='utf-8')


@pytest.fixture
def settings(tmp_path, monkeypatch):
    legacy_preferences(tmp_path)
    writes, deletes, errors = [], [], []
    monkeypatch.setattr(gui, 'save_login', lambda *args: writes.append(args))
    monkeypatch.setattr(gui, 'delete_login', lambda *args: deletes.append(args))
    monkeypatch.setattr(gui.messagebox, 'showerror', lambda *args, **kwargs: errors.append(args))
    root = tk.Tk(); root.withdraw()
    root.report_callback_exception = lambda *args: errors.append(args)
    controller = AccountController()
    app = gui.App(root, tmp_path, controller)
    app.settings(); root.update()
    yield root, app, controller, writes, deletes
    controller.active = False
    app._dispose()
    for token in root.tk.call('after', 'info'):
        root.after_cancel(token)
    root.destroy()
    del app
    gc.collect()
    assert not errors


def test_default_preferences_choose_satu_without_user_origin_choice(tmp_path):
    assert gui.load_preferences(tmp_path)['login_origin'] == SATU


def test_legacy_coretax_preference_does_not_copy_or_delete_any_credential(tmp_path, monkeypatch):
    legacy_preferences(tmp_path)
    def deny(*args):
        raise AssertionError('Loading preferences cannot migrate credentials')
    monkeypatch.setattr(gui, 'save_login', deny)
    monkeypatch.setattr(gui, 'delete_login', deny)
    loaded = gui.load_preferences(tmp_path)
    assert loaded['login_origin'] == SATU and loaded['identifier'] == ACCOUNT
    gui.save_preferences(tmp_path, loaded)
    persisted = json.loads((tmp_path / 'preferences.json').read_text(encoding='utf-8'))
    assert persisted['login_origin'] == SATU and 'password' not in persisted


def test_settings_has_no_origin_label_or_origin_selector(settings):
    root, app, controller, writes, deletes = settings
    controls = list(widgets(app._settings_dialog))
    assert 'Origin login' not in [w.cget('text') for w in controls if w.winfo_class() == 'TLabel']
    assert not any(SATU in tuple(w.cget('values')) or CORETAX in tuple(w.cget('values'))
                   for w in controls if w.winfo_class() == 'TCombobox')
    assert not writes and not deletes


def test_save_and_check_use_satu_even_after_legacy_coretax_settings(settings):
    root, app, controller, writes, deletes = settings
    password = next(w for w in widgets(app._settings_dialog)
                    if w.winfo_class() == 'TEntry' and w.cget('show'))
    password.insert(0, 'SYNTHETIC_PASSWORD_ONLY')
    button(app._settings_dialog, 'Simpan').invoke(); root.update()
    assert writes == [(SATU, ACCOUNT, 'SYNTHETIC_PASSWORD_ONLY')]
    assert password.get() == '' and not deletes
    button(app._settings_dialog, 'Cek login').invoke(); root.update()
    assert controller.checks == [(SATU, ACCOUNT, 'msedge', True)]


def test_start_passes_the_selected_saved_account_without_password(settings):
    root, app, controller, writes, deletes = settings
    app._settings_close()
    app.npwp.set('0000000000000001'); app.year.set('2025')
    app.start(); root.update()
    assert controller.start_options == [{'account': ACCOUNT}]
    assert not writes and not deletes

def test_switch_to_manual_mode_keeps_saved_secret_and_invalidates_check(settings):
    root, app, controller, writes, deletes = settings
    app._credential_status.set('Login berhasil; kredensial tersimpan terverifikasi.')
    account = next(w for w in widgets(app._settings_dialog)
                   if w.winfo_class() == 'TEntry' and not w.cget('show'))
    account.delete(0, 'end'); root.update()
    assert 'Login berhasil' not in app._credential_status.get()
    button(app._settings_dialog, 'Simpan').invoke(); root.update()
    assert app.preferences['identifier'] == '' and not writes and not deletes
    assert button(app._settings_dialog, 'Cek login').instate(['disabled'])



def test_visible_settings_keeps_account_password_and_actions_inside_dialog(settings):
    root, app, controller, writes, deletes = settings
    root.deiconify(); app._settings_dialog.deiconify(); root.update()
    dialog = app._settings_dialog
    for widget in widgets(dialog):
        if widget.winfo_class() in ('TEntry', 'TCombobox', 'TButton'):
            assert widget.winfo_viewable()
            right = widget.winfo_rootx() + widget.winfo_width()
            bottom = widget.winfo_rooty() + widget.winfo_height()
            assert right <= dialog.winfo_rootx() + dialog.winfo_width()
            assert bottom <= dialog.winfo_rooty() + dialog.winfo_height()
    assert not writes and not deletes
