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
    root.update()
    # A runner may leave the previous test's window foreground. Establish only
    # the initial application's OS focus; every modal must manage its own focus.
    root.focus_force()
    root.update()
    dialog = app.settings()
    root.update()
    yield root, app, controller, dialog, tmp_path, writes, errors
    controller.active = False
    if window_exists(root):
        app._dispose()
        for token in root.tk.splitlist(root.tk.call('after', 'info')):
            root.after_cancel(token)
        root.destroy()
    del app
    gc.collect()
    assert not callbacks


def window_exists(widget):
    try:
        return bool(widget.winfo_exists())
    except tk.TclError:
        # Closing the root removes Tk's winfo command as well as its windows.
        return False


def change_browser(dialog):
    browser = next(w for w in widgets(dialog)
                   if w.winfo_class() == 'TCombobox' and 'chrome' in tuple(w.cget('values')))
    browser.set('chrome')


def password_entry(dialog):
    return next(w for w in widgets(dialog) if w.winfo_class() == 'TEntry' and w.cget('show'))


def decision(root, app, dialog):
    app._settings_close()
    root.update()
    return current_decision(root, app, dialog)


def current_decision(root, app, dialog):
    assert window_exists(root), 'Unsaved settings must prevent immediate application shutdown'
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


def test_settings_actions_preserve_credentials_without_starting_a_job(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    labels = [w.cget('text') for w in widgets(dialog) if w.winfo_class() == 'TButton']
    assert {'Simpan', 'Hapus login', 'Tutup'} <= set(labels)
    assert 'Cek login' not in labels and 'Batalkan cek' not in labels
    button(dialog, 'Tutup').invoke()
    root.update()
    assert app._settings_dialog is None and root.grab_current() is None
    assert not ctl.active and not ctl.exports and not writes and not errors


def test_partial_delete_keeps_saved_preferences_honest_and_requires_retry(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *args, **kwargs: True)
    def fail(*args):
        raise OSError('SYNTHETIC_DELETE_PREFERENCES_FAILURE')
    monkeypatch.setattr(gui, 'save_preferences', fail)
    button(dialog, 'Hapus login').invoke()
    root.update()
    assert app.preferences['identifier'] == 'SYNTHETIC_ACCOUNT'
    assert (path / 'preferences.json').read_bytes() == original
    assert errors and 'Login sudah dihapus' in app._credential_status.get()
    prompt = decision(root, app, dialog)
    button(prompt, 'Kembali').invoke()


def test_deleted_login_cannot_be_reselected_without_new_password(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *args, **kwargs: True)
    button(dialog, 'Hapus login').invoke()
    account = next(w for w in widgets(dialog) if w.winfo_class() == 'TEntry' and not w.cget('show'))
    account.insert(0, 'SYNTHETIC_ACCOUNT')
    button(dialog, 'Simpan').invoke()
    root.update()
    assert errors and persisted(path)['identifier'] == ''
    assert not writes


@pytest.mark.parametrize('close_method', ['escape', 'window'])
def test_settings_escape_and_window_close_offer_one_dirty_decision(settings, close_method):
    root, app, ctl, dialog, path, writes, errors = settings
    password_entry(dialog).insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    if close_method == 'escape':
        dialog.event_generate('<Escape>')
    else:
        dialog.tk.call(dialog.protocol('WM_DELETE_WINDOW'))
    root.update()
    prompt = current_decision(root, app, dialog)
    assert root.focus_get() is button(prompt, 'Kembali')
    assert root.grab_current() is prompt
    button(prompt, 'Kembali').invoke()
    root.update()
    assert password_entry(dialog).get() == 'SYNTHETIC_NEW_PASSWORD_ONLY'
    assert root.grab_current() is dialog and not writes and not errors


@pytest.mark.parametrize('prompt_already_open', [False, True])
def test_root_close_return_preserves_settings_and_cancels_shutdown(settings, prompt_already_open):
    root, app, ctl, dialog, path, writes, errors = settings
    change_browser(dialog)
    previous_prompt = decision(root, app, dialog) if prompt_already_open else None
    root.tk.call(root.protocol('WM_DELETE_WINDOW'))
    prompt = current_decision(root, app, dialog)
    root.update()
    if previous_prompt is not None:
        assert prompt is previous_prompt
    assert root.grab_current() is prompt
    button(prompt, 'Kembali').invoke()
    root.update()
    assert window_exists(root) and dialog.winfo_exists()
    assert root.grab_current() is dialog
    assert persisted(path)['browser'] == 'msedge' and not writes and not errors
    # Returning must clear the application-close intent: a later Settings-only
    # discard should close just Settings, leaving the application running.
    prompt = decision(root, app, dialog)
    button(prompt, 'Abaikan').invoke()
    assert window_exists(root)
    root.update()
    assert app._settings_dialog is None and root.grab_current() is None


@pytest.mark.parametrize('choice', ['Simpan', 'Abaikan'])
def test_root_close_waits_for_settings_save_or_discard(settings, choice):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    change_browser(dialog)
    root.tk.call(root.protocol('WM_DELETE_WINDOW'))
    prompt = current_decision(root, app, dialog)
    root.update()
    button(prompt, choice).invoke()
    assert not window_exists(root), 'An accepted application-close decision must finish shutdown'
    if choice == 'Simpan':
        assert persisted(path)['browser'] == 'chrome'
    else:
        assert (path / 'preferences.json').read_bytes() == original
    assert not writes and not errors


def test_root_close_failed_save_keeps_settings_open_and_cancels_shutdown(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    change_browser(dialog)
    def fail(*args):
        raise OSError('SYNTHETIC_ROOT_CLOSE_PREFERENCES_FAILURE')
    monkeypatch.setattr(gui, 'save_preferences', fail)
    root.tk.call(root.protocol('WM_DELETE_WINDOW'))
    prompt = current_decision(root, app, dialog)
    root.update()
    button(prompt, 'Simpan').invoke()
    assert window_exists(root)
    root.update()
    assert dialog.winfo_exists() and root.grab_current() is dialog
    assert errors and (path / 'preferences.json').read_bytes() == original
    assert 'Pengaturan disimpan.' not in app._credential_status.get()
    prompt = decision(root, app, dialog)
    button(prompt, 'Abaikan').invoke()
    assert window_exists(root), 'A failed save must cancel the earlier application-close intent'
    root.update()
    assert app._settings_dialog is None and not writes


def test_changed_account_partial_save_retries_once_and_rejects_old_account_without_password(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    account = next(w for w in widgets(dialog) if w.winfo_class() == 'TEntry' and not w.cget('show'))
    account.delete(0, 'end')
    account.insert(0, 'SYNTHETIC_SECOND_ACCOUNT')
    password_entry(dialog).insert(0, 'SYNTHETIC_NEW_PASSWORD_ONLY')
    real_save = gui.save_preferences
    def fail(*args):
        raise OSError('SYNTHETIC_CHANGED_ACCOUNT_PREFERENCES_FAILURE')
    monkeypatch.setattr(gui, 'save_preferences', fail)
    button(dialog, 'Simpan').invoke()
    root.update()
    assert writes == [(gui.LOGIN_ORIGIN, 'SYNTHETIC_SECOND_ACCOUNT', 'SYNTHETIC_NEW_PASSWORD_ONLY')]
    assert password_entry(dialog).get() == ''
    assert persisted(path)['identifier'] == 'SYNTHETIC_ACCOUNT'
    assert app.preferences['identifier'] == 'SYNTHETIC_ACCOUNT'
    monkeypatch.setattr(gui, 'save_preferences', real_save)
    account.delete(0, 'end')
    account.insert(0, 'SYNTHETIC_ACCOUNT')
    error_count = len(errors)
    button(dialog, 'Simpan').invoke()
    root.update()
    assert len(errors) == error_count + 1
    account.delete(0, 'end')
    account.insert(0, 'SYNTHETIC_SECOND_ACCOUNT')
    button(dialog, 'Simpan').invoke()
    root.update()
    assert len(writes) == 1
    assert persisted(path)['identifier'] == 'SYNTHETIC_SECOND_ACCOUNT'
    assert app.preferences['identifier'] == 'SYNTHETIC_SECOND_ACCOUNT'
    assert 'password' not in persisted(path)


def test_return_discard_reopen_and_save_retire_old_dialog_callbacks(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    change_browser(dialog)
    first_prompt = decision(root, app, dialog)
    button(first_prompt, 'Kembali').invoke()
    root.update()
    assert not first_prompt.winfo_exists() and root.grab_current() is dialog
    second_prompt = decision(root, app, dialog)
    assert second_prompt is not first_prompt
    button(second_prompt, 'Abaikan').invoke()
    root.update()
    assert not dialog.winfo_exists() and not second_prompt.winfo_exists()
    assert (path / 'preferences.json').read_bytes() == original
    assert root.grab_current() is None and root.focus_get() is app.settings_button
    reopened = app.settings()
    root.update()
    assert reopened is not dialog and root.grab_current() is reopened
    change_browser(reopened)
    final_prompt = decision(root, app, reopened)
    assert root.focus_get() is button(final_prompt, 'Kembali')
    button(final_prompt, 'Simpan').invoke()
    root.update()
    assert app._settings_dialog is None and root.grab_current() is None
    assert root.focus_get() is app.settings_button
    assert persisted(path)['browser'] == 'chrome' and not writes and not errors
