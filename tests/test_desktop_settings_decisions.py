"""Settings decisions exercise native Tk with synthetic credential boundaries."""
import gc
import json
import tkinter as tk

import pytest

from spt_desktop import app as gui
from support_gui import Controller, button, widgets


@pytest.fixture
def settings(tmp_path, monkeypatch):
    gui.save_preferences(tmp_path, dict(gui.DEFAULTS, identifier='SYNTHETIC_ACCOUNT'))
    writes, errors, callbacks = [], [], []
    monkeypatch.setattr(gui, 'save_login', lambda *args: writes.append(args))
    monkeypatch.setattr(gui, 'delete_login', lambda *args: None)
    monkeypatch.setattr(gui.messagebox, 'showerror', lambda *args, **kwargs: errors.append(args))
    root = tk.Tk()
    root.report_callback_exception = lambda *args: callbacks.append(args)
    controller = Controller()
    app = gui.App(root, tmp_path, controller)
    dialog = app.settings()
    root.update()
    yield root, app, controller, dialog, tmp_path, writes, errors
    controller.active = False
    app._dispose()
    for token in root.tk.splitlist(root.tk.call('after', 'info')):
        root.after_cancel(token)
    root.destroy()
    del app
    gc.collect()
    assert not callbacks


def change_browser(dialog):
    browser = next(w for w in widgets(dialog)
                   if w.winfo_class() == 'TCombobox' and 'chrome' in tuple(w.cget('values')))
    browser.set('chrome')


def password_entry(dialog):
    return next(w for w in widgets(dialog) if w.winfo_class() == 'TEntry' and w.cget('show'))


def decision(root, app, dialog):
    app._settings_close()
    root.update()
    assert app._settings_dialog is dialog, 'Unsaved settings must remain open for a decision'
    matches = [w for w in widgets(root)
               if isinstance(w, tk.Toplevel) and w.title() == 'Perubahan belum disimpan']
    assert len(matches) == 1, 'Closing dirty settings must offer one explicit decision'
    return matches[0]


def persisted(path):
    return json.loads((path / 'preferences.json').read_text(encoding='utf-8'))


def test_dirty_close_defaults_to_return_and_preserves_edits(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    change_browser(dialog)
    prompt = decision(root, app, dialog)
    assert root.focus_get() is button(prompt, 'Kembali')
    assert root.grab_current() is prompt
    app._settings_close()
    root.update()
    assert len([w for w in widgets(root) if isinstance(w, tk.Toplevel)
                and w.title() == 'Perubahan belum disimpan']) == 1
    button(prompt, 'Kembali').invoke()
    root.update()
    assert dialog.winfo_exists() and root.grab_current() is dialog
    assert persisted(path)['browser'] == 'msedge' and not writes and not errors
    assert button(dialog, 'Cek login').instate(['disabled'])


@pytest.mark.parametrize('close_method', ['escape', 'window'])
def test_escape_and_window_close_return_without_discarding(settings, close_method):
    root, app, ctl, dialog, path, writes, errors = settings
    password_entry(dialog).insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    prompt = decision(root, app, dialog)
    if close_method == 'escape':
        prompt.event_generate('<Escape>')
    else:
        prompt.tk.call(prompt.protocol('WM_DELETE_WINDOW'))
    root.update()
    assert dialog.winfo_exists() and not prompt.winfo_exists()
    assert password_entry(dialog).get() == 'SYNTHETIC_NEW_PASSWORD_ONLY'
    assert root.grab_current() is dialog and not writes and not errors


def test_discard_closes_without_writing_preferences_or_credentials(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    change_browser(dialog)
    password_entry(dialog).insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    prompt = decision(root, app, dialog)
    button(prompt, 'Abaikan').invoke()
    root.update()
    assert app._settings_dialog is None and not dialog.winfo_exists()
    assert root.grab_current() is None
    assert root.focus_get() is app.settings_button
    assert (path / 'preferences.json').read_bytes() == original
    assert not writes and not errors


def test_save_from_decision_persists_then_closes(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    change_browser(dialog)
    prompt = decision(root, app, dialog)
    button(prompt, 'Simpan').invoke()
    root.update()
    assert persisted(path)['browser'] == 'chrome'
    assert app.preferences['browser'] == 'chrome'
    assert app._settings_dialog is None and root.grab_current() is None
    assert not writes and not errors


@pytest.mark.parametrize('failure', ['credentials', 'preferences'])
def test_failed_save_keeps_settings_and_does_not_claim_success(settings, monkeypatch, failure):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    change_browser(dialog)
    password_entry(dialog).insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    def fail(*args):
        raise OSError('SYNTHETIC_SECRET_MUST_NOT_APPEAR')
    monkeypatch.setattr(gui, 'save_login' if failure == 'credentials' else 'save_preferences', fail)
    prompt = decision(root, app, dialog)
    button(prompt, 'Simpan').invoke()
    root.update()
    assert app._settings_dialog is dialog and dialog.winfo_exists()
    assert not prompt.winfo_exists() and root.grab_current() is dialog
    assert (path / 'preferences.json').read_bytes() == original
    assert app.preferences['browser'] == 'msedge'
    assert errors and 'SYNTHETIC_SECRET_MUST_NOT_APPEAR' not in repr(errors)
    assert 'Pengaturan disimpan.' not in app._credential_status.get()
    assert button(dialog, 'Cek login').instate(['disabled'])
    assert len(writes) == (1 if failure == 'preferences' else 0)


def test_partial_password_save_stays_pending_and_retry_does_not_repeat_vault_write(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    password_entry(dialog).insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    real_save = gui.save_preferences
    def fail(*args):
        raise OSError('SYNTHETIC_PREFERENCES_FAILURE')
    monkeypatch.setattr(gui, 'save_preferences', fail)
    button(dialog, 'Simpan').invoke()
    root.update()
    assert len(writes) == 1 and password_entry(dialog).get() == ''
    assert 'Password sudah disimpan' in app._credential_status.get()
    assert button(dialog, 'Cek login').instate(['disabled'])
    prompt = decision(root, app, dialog)
    monkeypatch.setattr(gui, 'save_preferences', real_save)
    button(prompt, 'Simpan').invoke()
    root.update()
    assert len(writes) == 1 and app._settings_dialog is None
    assert 'password' not in persisted(path)


def test_reverted_preferences_close_without_a_false_dirty_prompt(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    browser = next(w for w in widgets(dialog)
                   if w.winfo_class() == 'TCombobox' and 'chrome' in tuple(w.cget('values')))
    browser.set('chrome'); browser.set('msedge')
    app._settings_close()
    root.update()
    assert app._settings_dialog is None and not writes and not errors


def test_login_captions_start_and_cancel_the_existing_check(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    labels = [w.cget('text') for w in widgets(dialog) if w.winfo_class() == 'TButton']
    assert {'Cek login', 'Batalkan cek', 'Hapus login'} <= set(labels)
    button(dialog, 'Cek login').invoke()
    assert ctl.checks == [(gui.LOGIN_ORIGIN, 'SYNTHETIC_ACCOUNT', 'msedge', True)]
    app._settings_close()
    assert ctl.stops == 1 and dialog.winfo_exists()
    ctl.active = False
    app.on_event({'job_id': ctl.job_id, 'type': 'terminal', 'status': 'CANCELLED',
                  'percent': 0, 'output': None, 'message': 'Cek login dibatalkan.'})
    root.update()
    assert app._settings_dialog is None and root.grab_current() is None
    assert not ctl.exports and not writes and not errors
