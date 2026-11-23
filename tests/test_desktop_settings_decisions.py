"""Settings decisions exercise native Tk with synthetic credential boundaries."""
import gc
import json
import tkinter as tk

import pytest

from spt_desktop import app as gui
from spt_desktop.ui_copy import copy_text
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
               if isinstance(w, tk.Toplevel) and w.title() == copy_text('settings.dirty.title')]
    assert len(matches) == 1, 'Closing dirty settings must offer one explicit decision'
    return matches[0]


def persisted(path):
    return json.loads((path / 'preferences.json').read_text(encoding='utf-8'))


def test_settings_shows_requested_cache_and_login_copy(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    labels = [str(w.cget('text')) for w in widgets(dialog)
              if w.winfo_class() == 'TLabel']
    assert copy_text('settings.field.label.jumlah.cache.job.0.nonaktif') in labels
    assert copy_text('settings.widget.login.otomatis.melalui.satu.kemenkeu') in labels
    assert button(dialog, copy_text('settings.widget.bersihkan.cache.job'))
    assert not writes and not errors


def test_dirty_close_defaults_to_return_and_preserves_edits(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    change_browser(dialog)
    prompt = decision(root, app, dialog)
    assert root.focus_get() is button(prompt, copy_text('settings.widget.kembali'))
    assert root.grab_current() is prompt
    app._settings_close()
    root.update()
    assert len([w for w in widgets(root) if isinstance(w, tk.Toplevel)
                and w.title() == copy_text('settings.dirty.title')]) == 1
    button(prompt, copy_text('settings.widget.kembali')).invoke()
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
    button(prompt, copy_text('settings.widget.abaikan')).invoke()
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
    button(prompt, copy_text('settings.widget.simpan')).invoke()
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
    button(prompt, copy_text('settings.widget.simpan')).invoke()
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
    button(dialog, copy_text('settings.widget.simpan')).invoke()
    root.update()
    assert len(writes) == 1 and password_entry(dialog).get() == ''
    assert copy_text('settings.message.password.sudah.disimpan') in app._credential_status.get()
    prompt = decision(root, app, dialog)
    monkeypatch.setattr(gui, 'save_preferences', real_save)
    button(prompt, copy_text('settings.widget.simpan')).invoke()
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
    assert {copy_text('settings.widget.simpan'), copy_text('settings.delete'), copy_text('settings.widget.tutup')} <= set(labels)
    assert 'Cek login' not in labels and 'Batalkan cek' not in labels
    button(dialog, copy_text('settings.widget.tutup')).invoke()
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
    button(dialog, copy_text('settings.delete')).invoke()
    root.update()
    assert app.preferences['identifier'] == 'SYNTHETIC_ACCOUNT'
    assert (path / 'preferences.json').read_bytes() == original
    assert errors and copy_text('settings.message.login.sudah.dihapus') in app._credential_status.get()
    prompt = decision(root, app, dialog)
    button(prompt, copy_text('settings.widget.kembali')).invoke()


def test_deleted_login_cannot_be_reselected_without_new_password(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *args, **kwargs: True)
    button(dialog, copy_text('settings.delete')).invoke()
    account = next(w for w in widgets(dialog) if w.winfo_class() == 'TEntry' and not w.cget('show'))
    account.insert(0, 'SYNTHETIC_ACCOUNT')
    button(dialog, copy_text('settings.widget.simpan')).invoke()
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
    assert root.focus_get() is button(prompt, copy_text('settings.widget.kembali'))
    assert root.grab_current() is prompt
    button(prompt, copy_text('settings.widget.kembali')).invoke()
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
    button(prompt, copy_text('settings.widget.kembali')).invoke()
    root.update()
    assert window_exists(root) and dialog.winfo_exists()
    assert root.grab_current() is dialog
    assert persisted(path)['browser'] == 'msedge' and not writes and not errors
    # Returning must clear the application-close intent: a later Settings-only
    # discard should close just Settings, leaving the application running.
    prompt = decision(root, app, dialog)
    button(prompt, copy_text('settings.widget.abaikan')).invoke()
    assert window_exists(root)
    root.update()
    assert app._settings_dialog is None and root.grab_current() is None


@pytest.mark.parametrize('choice', [copy_text('settings.widget.simpan'), copy_text('settings.widget.abaikan')])
def test_root_close_waits_for_settings_save_or_discard(settings, choice):
    root, app, ctl, dialog, path, writes, errors = settings
    original = (path / 'preferences.json').read_bytes()
    change_browser(dialog)
    root.tk.call(root.protocol('WM_DELETE_WINDOW'))
    prompt = current_decision(root, app, dialog)
    root.update()
    button(prompt, choice).invoke()
    assert not window_exists(root), 'An accepted application-close decision must finish shutdown'
    if choice == copy_text('settings.widget.simpan'):
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
    button(prompt, copy_text('settings.widget.simpan')).invoke()
    assert window_exists(root)
    root.update()
    assert dialog.winfo_exists() and root.grab_current() is dialog
    assert errors and (path / 'preferences.json').read_bytes() == original
    assert 'Pengaturan disimpan.' not in app._credential_status.get()
    prompt = decision(root, app, dialog)
    button(prompt, copy_text('settings.widget.abaikan')).invoke()
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
    button(dialog, copy_text('settings.widget.simpan')).invoke()
    root.update()
    assert writes == [(gui.LOGIN_ORIGIN, 'SYNTHETIC_SECOND_ACCOUNT', 'SYNTHETIC_NEW_PASSWORD_ONLY')]
    assert password_entry(dialog).get() == ''
    assert persisted(path)['identifier'] == 'SYNTHETIC_ACCOUNT'
    assert app.preferences['identifier'] == 'SYNTHETIC_ACCOUNT'
    monkeypatch.setattr(gui, 'save_preferences', real_save)
    account.delete(0, 'end')
    account.insert(0, 'SYNTHETIC_ACCOUNT')
    error_count = len(errors)
    button(dialog, copy_text('settings.widget.simpan')).invoke()
    root.update()
    assert len(errors) == error_count + 1
    account.delete(0, 'end')
    account.insert(0, 'SYNTHETIC_SECOND_ACCOUNT')
    button(dialog, copy_text('settings.widget.simpan')).invoke()
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
    button(first_prompt, copy_text('settings.widget.kembali')).invoke()
    root.update()
    assert not first_prompt.winfo_exists() and root.grab_current() is dialog
    second_prompt = decision(root, app, dialog)
    assert second_prompt is not first_prompt
    button(second_prompt, copy_text('settings.widget.abaikan')).invoke()
    root.update()
    assert not dialog.winfo_exists() and not second_prompt.winfo_exists()
    assert (path / 'preferences.json').read_bytes() == original
    assert root.grab_current() is None and root.focus_get() is app.settings_button
    reopened = app.settings()
    root.update()
    assert reopened is not dialog and root.grab_current() is reopened
    change_browser(reopened)
    final_prompt = decision(root, app, reopened)
    assert root.focus_get() is button(final_prompt, copy_text('settings.widget.kembali'))
    button(final_prompt, copy_text('settings.widget.simpan')).invoke()
    root.update()
    assert app._settings_dialog is None and root.grab_current() is None
    assert root.focus_get() is app.settings_button
    assert persisted(path)['browser'] == 'chrome' and not writes and not errors


def test_retention_setting_defaults_to_ten_and_persists_without_credential_changes(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    spinner = next(w for w in widgets(dialog) if w.winfo_class() == 'TSpinbox')
    assert spinner.get() == '10'
    spinner.delete(0, 'end')
    spinner.insert(0, '3')
    root.update()
    assert app.preferences['keep_jobs'] == 10  # Dirty until saved.
    button(dialog, copy_text('settings.widget.simpan')).invoke()
    root.update()
    assert persisted(path)['keep_jobs'] == 3
    assert app.preferences['keep_jobs'] == 3
    assert not writes and not errors


def test_invalid_retention_input_does_not_get_saved_or_claim_success(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    spinner = next(w for w in widgets(dialog) if w.winfo_class() == 'TSpinbox')
    spinner.delete(0, 'end')
    spinner.insert(0, '101')
    root.update()
    button(dialog, copy_text('settings.widget.simpan')).invoke()
    root.update()
    assert errors and persisted(path)['keep_jobs'] == 10
    assert app.preferences['keep_jobs'] == 10
    assert app._settings_dialog is dialog and dialog.winfo_exists()
    assert not writes


def _pump_manual_prune(root):
    # Tk receives the worker result only through the main-thread after queue.
    root.after(300, root.quit)
    root.mainloop()


@pytest.mark.parametrize('confirmed', [True, False])
def test_manual_prune_previews_then_requires_explicit_confirmation(
        settings, monkeypatch, confirmed):
    from types import SimpleNamespace
    root, app, ctl, dialog, path, writes, errors = settings
    calls, prompts, notices = [], [], []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'downloads_folder', lambda: path / 'Downloads')
    monkeypatch.setattr(gui, 'preview_published_jobs',
                        lambda *a, **kw: calls.append('preview') or
                        {'eligible_jobs': 2, 'estimated_bytes': 2 * 1024 * 1024,
                         'candidate_ids': ('1' * 32, '2' * 32), 'scan_complete': True})
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: calls.append(('delete', kw['allowed_ids'])) or
                        {'removed': 2, 'incomplete': False})
    monkeypatch.setattr(gui.messagebox, 'askyesno',
                        lambda title, message, **kw: prompts.append((title, message)) or confirmed)
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kw: notices.append((title, message)))
    button(dialog, copy_text('settings.widget.bersihkan.cache.job')).invoke()
    assert app._manual_prune_busy  # New export cannot begin during preview/delete.
    _pump_manual_prune(root)
    assert calls == (['preview', ('delete', ('1' * 32, '2' * 32))]
                     if confirmed else ['preview'])
    assert len(prompts) == 1 and '2 job' in prompts[0][1]
    assert '2.0 MiB' in prompts[0][1]
    assert all('0000000000000001' not in message for _, message in prompts + notices)
    assert not app._manual_prune_busy
    assert not ctl.active and not ctl.exports and not writes and not errors


def test_manual_prune_refuses_unsaved_retention_change(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    spinner = next(w for w in widgets(dialog) if w.winfo_class() == 'TSpinbox')
    spinner.delete(0, 'end')
    spinner.insert(0, '1')
    root.update()
    notices = []
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kw: notices.append((title, message)))
    monkeypatch.setattr(gui, 'preview_published_jobs',
                        lambda *a, **kw: pytest.fail('No preview before saved settings'))
    button(dialog, copy_text('settings.widget.bersihkan.cache.job')).invoke()
    assert notices and copy_text('settings.dialog.title.simpan.pengaturan') == notices[0][0]
    assert not app._manual_prune_busy
    assert app.preferences['keep_jobs'] == 10 and not writes


def test_incomplete_preview_never_presents_delete_confirmation(settings, monkeypatch):
    from types import SimpleNamespace
    root, app, ctl, dialog, path, writes, errors = settings
    notices, calls = [], []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'downloads_folder', lambda: path / 'Downloads')
    monkeypatch.setattr(gui, 'preview_published_jobs',
                        lambda *a, **kw: calls.append('preview') or {
                            'eligible_jobs': 1, 'estimated_bytes': 1024,
                            'candidate_ids': ('1' * 32,), 'scan_complete': False})
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: pytest.fail('Incomplete preview must not delete'))
    monkeypatch.setattr(gui.messagebox, 'askyesno',
                        lambda *a, **kw: pytest.fail('Incomplete preview must not ask confirmation'))
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kw: notices.append((title, message)))
    button(dialog, copy_text('settings.widget.bersihkan.cache.job')).invoke()
    _pump_manual_prune(root)
    assert calls == ['preview']
    assert len(notices) == 1 and 'belum lengkap' in notices[0][0]
    assert not app._manual_prune_busy
    assert not ctl.active and not ctl.exports and not writes and not errors


def test_manual_prune_warns_after_partial_source_removal(settings, monkeypatch):
    from types import SimpleNamespace
    root, app, ctl, dialog, path, writes, errors = settings
    warnings, infos, calls = [], [], []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'downloads_folder', lambda: path / 'Downloads')
    monkeypatch.setattr(gui, 'preview_published_jobs',
                        lambda *a, **kw: {'eligible_jobs': 1, 'estimated_bytes': 1000,
                                         'candidate_ids': ('1' * 32,), 'scan_complete': True})
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: calls.append(kw) or
                        {'removed': 0, 'incomplete': True})
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a, **kw: True)
    monkeypatch.setattr(gui.messagebox, 'showwarning',
                        lambda title, message, **kw: warnings.append((title, message)))
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kw: infos.append((title, message)))
    button(dialog, copy_text('settings.widget.bersihkan.cache.job')).invoke()
    _pump_manual_prune(root)
    assert calls and calls[0]['report'] is True
    assert calls[0]['allowed_ids'] == ('1' * 32,)
    assert len(warnings) == 1 and 'belum tuntas' in warnings[0][0]
    assert 'checkpoint' in warnings[0][1]
    assert not infos and not errors and not writes
    assert not app._manual_prune_busy and not ctl.active and not ctl.exports


def test_storage_dashboard_shows_aggregate_fields_and_manual_action(settings):
    root, app, ctl, dialog, path, writes, errors = settings
    labels = [str(w.cget('text')) for w in widgets(dialog)
              if w.winfo_class() in ('TLabel', 'TLabelframe')]
    assert copy_text('settings.widget.dashboard.penyimpanan.job') in labels or any(
        copy_text('settings.widget.dashboard.penyimpanan.job') in str(w.cget('text'))
        for w in widgets(dialog) if w.winfo_class() == 'TLabelframe')
    assert copy_text('settings.storage.label.complete') in labels
    assert copy_text('settings.storage.label.partial') in labels
    assert copy_text('settings.storage.label.gagal.dibatalkan') in labels
    assert copy_text('settings.storage.label.protected.auto.clean') in labels
    assert button(dialog, copy_text('settings.widget.hapus.job.partial.gagal'))
    assert button(dialog, 'Perbarui penggunaan storage')


def test_incomplete_manual_cleanup_requires_selected_rows_and_confirmation(
        settings, monkeypatch):
    from types import SimpleNamespace
    root, app, ctl, dialog, path, writes, errors = settings
    calls, prompts, notices = [], [], []
    token = 'a' * 32
    # A finished job ID remains on the controller; it is not an active lease.
    ctl.job_id = token
    digest = 'b' * 64

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    preview = {'total': 1, 'complete': 0, 'partial': 1, 'failed': 0,
               'protected': 1, 'estimated_bytes': 2048,
               'scan_complete': True,
               'removable': ({'id': token, 'status': 'PARTIAL',
                              'bytes': 2048, 'digest': digest,
                              'modified_ns': 1_700_000_000_000_000_000},)}
    monkeypatch.setattr(gui, 'inspect_job_storage',
                        lambda *a, **kw: calls.append(('preview', kw['active_id'])) or preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *a, **kw: calls.append(('delete', a[1])) or
                        {'removed': 1, 'incomplete': False})
    monkeypatch.setattr(gui.messagebox, 'askyesno',
                        lambda title, body, **kwargs: prompts.append(body) or True)
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kwargs: notices.append((title, message)))
    button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
    _pump_manual_prune(root)
    picker = next(w for w in widgets(root)
                  if isinstance(w, tk.Toplevel) and w.title() == copy_text('settings.window.title.pilih.job.partial.gagal'))
    assert app._manual_prune_busy
    assert not prompts
    table = next(w for w in widgets(picker) if w.winfo_class() == 'Treeview')
    assert token in table.get_children()
    assert token not in str(table.item(token, 'values'))
    button(picker, copy_text('settings.widget.hapus.terpilih')).invoke()
    assert notices and copy_text('settings.dialog.title.pilih.job') == notices[-1][0]
    assert not prompts
    table.selection_set(token)
    button(picker, copy_text('settings.widget.hapus.terpilih')).invoke()
    _pump_manual_prune(root)
    assert calls[:2] == [('preview', None), ('delete', ((token, digest),))]
    assert len(prompts) == 1
    assert token not in prompts[0]
    assert not app._manual_prune_busy and not ctl.active and not ctl.exports


@pytest.mark.parametrize('confirmed', [False, True])
def test_incomplete_select_all_tracks_manual_selection_without_skipping_confirmation(
        settings, monkeypatch, confirmed):
    from types import SimpleNamespace
    root, app, ctl, dialog, path, writes, errors = settings
    ids = tuple(str(number) * 32 for number in (1, 2, 3))
    digests = tuple(letter * 64 for letter in 'abc')
    approvals_seen, prompts, notices = [], [], []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    preview = {
        'total': 3, 'complete': 0, 'partial': 2, 'failed': 1,
        'protected': 3, 'estimated_bytes': 6144, 'scan_complete': True,
        'removable': tuple(
            {'id': job_id, 'status': 'FAILED' if i == 2 else 'PARTIAL',
             'bytes': (i + 1) * 1024, 'digest': digests[i],
             'modified_ns': 1_700_000_000_000_000_000 + i}
            for i, job_id in enumerate(ids)),
    }

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *a, **kw: approvals_seen.append(a[1]) or
                        {'removed': len(a[1]), 'incomplete': False})
    monkeypatch.setattr(gui.messagebox, 'askyesno',
                        lambda title, body, **kw:
                        prompts.append((body, kw.get('default'))) or confirmed)
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, body, **kw: notices.append(title))

    button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
    _pump_manual_prune(root)
    picker = next(w for w in widgets(root)
                  if isinstance(w, tk.Toplevel) and w.title() == copy_text('settings.window.title.pilih.job.partial.gagal'))
    table = next(w for w in widgets(picker) if w.winfo_class() == 'Treeview')
    select_all = next(w for w in widgets(picker)
                      if w.winfo_class() == 'TCheckbutton'
                      and w.cget('text') == copy_text('settings.widget.select.all'))
    assert not table.selection()
    assert not select_all.instate(('selected',))

    select_all.invoke()
    root.update()
    assert set(table.selection()) == set(ids)
    assert select_all.instate(('selected',))
    assert not prompts and not approvals_seen  # Selection is never deletion.

    select_all.invoke()
    root.update()
    assert not table.selection()
    assert not select_all.instate(('selected',))

    table.selection_set(*ids[:2])
    root.update()
    assert not select_all.instate(('selected',))
    table.selection_add(ids[2])
    root.update()
    assert select_all.instate(('selected',))
    table.selection_remove(ids[1])
    root.update()
    assert not select_all.instate(('selected',))

    select_all.invoke()
    root.update()
    assert set(table.selection()) == set(ids)
    button(picker, copy_text('settings.widget.hapus.terpilih')).invoke()
    assert len(prompts) == 1
    assert prompts[0][1] == 'no' and '3 job' in prompts[0][0]
    assert all(job_id not in prompts[0][0] for job_id in ids)

    if confirmed:
        _pump_manual_prune(root)
        assert approvals_seen == [tuple(zip(ids, digests))]
        assert 'Pembersihan selesai' in notices
        assert not app._manual_prune_busy
    else:
        assert not approvals_seen and picker.winfo_exists()
        button(picker, 'Batal').invoke()
        assert not app._manual_prune_busy
    assert not ctl.active and not ctl.exports and not writes and not errors


def test_incomplete_cleanup_refuses_unsaved_changes(settings, monkeypatch):
    root, app, ctl, dialog, path, writes, errors = settings
    change_browser(dialog)
    root.update()
    notices = []
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kwargs: notices.append(title))
    monkeypatch.setattr(gui, 'inspect_job_storage',
                        lambda *args, **kwargs: pytest.fail('No scan before save'))
    button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
    assert notices == [copy_text('settings.dialog.title.simpan.pengaturan')]
    assert not app._manual_prune_busy


def test_owned_app_starts_inventory_and_async_auto_prune_only(
        tmp_path, monkeypatch):
    from types import SimpleNamespace
    preview = {'total': 1, 'complete': 0, 'partial': 1, 'failed': 0,
               'protected': 1, 'estimated_bytes': 1234,
               'scan_complete': True, 'removable': ()}
    calls = []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'JobController', lambda *args: Controller())
    monkeypatch.setattr(gui.App, 'check_updates', lambda *args, **kwargs: None)
    monkeypatch.setattr(gui, 'inspect_job_storage',
                        lambda *args, **kwargs: calls.append('inspect') or preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *args, **kwargs: pytest.fail('Startup must not delete PARTIAL/FAILED'))
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: calls.append(('prune', a[2], kw.get('exclude'))) or 0)
    root = tk.Tk()
    app = gui.App(root, tmp_path)
    try:
        _pump_manual_prune(root)
        assert calls == ['inspect', ('prune', 10, None)]
        assert app._storage_snapshot == preview
        assert not app._storage_pending
    finally:
        app._dispose()
        root.destroy()


def test_startup_auto_prune_respects_zero_retention(tmp_path, monkeypatch):
    prefs = dict(gui.load_preferences(tmp_path))
    prefs['keep_jobs'] = 0
    monkeypatch.setattr(gui, 'load_preferences', lambda *args: prefs)
    monkeypatch.setattr(gui, 'JobController', lambda *args: Controller())
    monkeypatch.setattr(gui.App, 'check_updates', lambda *args, **kwargs: None)
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: {
        'total': 0, 'complete': 0, 'partial': 0, 'failed': 0,
        'protected': 0, 'estimated_bytes': 0, 'scan_complete': True,
        'removable': ()})
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: pytest.fail('keep_jobs=0 disables pruning'))
    root = tk.Tk()
    app = gui.App(root, tmp_path)
    try:
        _pump_manual_prune(root)
        assert app.preferences['keep_jobs'] == 0
    finally:
        app._dispose()
        root.destroy()


def test_startup_auto_prune_excludes_active_job(tmp_path, monkeypatch):
    from types import SimpleNamespace
    token = 'a' * 32
    active = Controller()
    active.active = True
    active.job_id = token
    calls = []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'JobController', lambda *args: active)
    monkeypatch.setattr(gui.App, 'check_updates', lambda *args, **kwargs: None)
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: {
        'total': 1, 'complete': 0, 'partial': 0, 'failed': 0,
        'protected': 1, 'estimated_bytes': 0, 'scan_complete': True,
        'removable': ()})
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: calls.append(kw.get('exclude')) or 0)
    root = tk.Tk()
    app = gui.App(root, tmp_path)
    try:
        _pump_manual_prune(root)
        assert calls == [token]
    finally:
        app._dispose()
        root.destroy()


def test_gui_close_does_not_block_on_startup_prune(tmp_path, monkeypatch):
    import threading as real_threading
    import time

    release = real_threading.Event()
    monkeypatch.setattr(gui, 'JobController', lambda *args: Controller())
    monkeypatch.setattr(gui.App, 'check_updates', lambda *args, **kwargs: None)
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: {
        'total': 0, 'complete': 0, 'partial': 0, 'failed': 0,
        'protected': 0, 'estimated_bytes': 0, 'scan_complete': True,
        'removable': ()})
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: release.wait(10))
    root = tk.Tk()
    app = gui.App(root, tmp_path)
    try:
        _pump_manual_prune(root)
        worker = app._startup_prune_thread
        assert worker is not None and worker.is_alive()
        assert worker.daemon is False
        began = time.monotonic()
        app._dispose()
        assert time.monotonic() - began < 1
        assert worker.is_alive() and worker.daemon is False
        assert app._startup_prune_thread is None
        release.set()
        worker.join(5)
        assert not worker.is_alive()
    finally:
        release.set()
        app._dispose()
        root.destroy()


def test_startup_prune_ignores_injected_controller(tmp_path, monkeypatch):
    from types import SimpleNamespace

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui.App, 'check_updates', lambda *a, **kw: None)
    monkeypatch.setattr(gui, 'prune_published_jobs',
                        lambda *a, **kw: pytest.fail('No auto-clean without owned controller'))
    root = tk.Tk()
    app = gui.App(root, tmp_path, Controller())
    try:
        app._startup_prune()
        assert app._startup_prune_thread is None
    finally:
        app._dispose()
        root.destroy()


def test_startup_prune_swallows_downloads_and_prune_failures(tmp_path, monkeypatch):
    from types import SimpleNamespace

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'JobController', lambda *args: Controller())
    monkeypatch.setattr(gui.App, 'check_updates', lambda *a, **kw: None)
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: {
        'total': 0, 'complete': 0, 'partial': 0, 'failed': 0,
        'protected': 0, 'estimated_bytes': 0, 'scan_complete': True,
        'removable': ()})
    failures = []

    def failing_downloads():
        failures.append('downloads')
        raise OSError('SYNTHETIC')

    monkeypatch.setattr(gui, 'downloads_folder', failing_downloads)
    root = tk.Tk()
    app = gui.App(root, tmp_path)
    try:
        _pump_manual_prune(root)
        assert failures == ['downloads']

        monkeypatch.setattr(gui, 'downloads_folder', lambda: tmp_path)
        monkeypatch.setattr(gui, 'prune_published_jobs',
                            lambda *a, **kw: (_ for _ in ()).throw(ValueError('SYNTHETIC')))
        app._startup_prune()
        assert failures == ['downloads']
    finally:
        app._dispose()
        root.destroy()


def test_dispose_tolerates_retired_startup_callback(tmp_path, monkeypatch):
    monkeypatch.setattr(gui, 'JobController', lambda *args: Controller())
    monkeypatch.setattr(gui.App, 'check_updates', lambda *a, **kw: None)
    root = tk.Tk()
    app = gui.App(root, tmp_path)
    original_cancel = root.after_cancel
    pending = app._startup_prune_after
    assert pending is not None

    def cancel(token):
        if token == pending:
            raise tk.TclError('SYNTHETIC_RETIRED')
        return original_cancel(token)

    monkeypatch.setattr(root, 'after_cancel', cancel)
    try:
        app._dispose()
        assert app._startup_prune_after is None
    finally:
        app._dispose()
        root.destroy()

def test_incomplete_cleanup_partial_scan_offers_verified_candidates_only(
        settings, monkeypatch):
    from types import SimpleNamespace

    root, app, ctl, dialog, path, writes, errors = settings
    token, digest = 'a' * 32, 'b' * 64
    warnings, prompts, approvals = [], [], []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    preview = {'total': 2, 'complete': 0, 'partial': 1, 'failed': 0,
               'protected': 2, 'estimated_bytes': 4096,
               'scan_complete': False,
               'removable': ({'id': token, 'status': 'PARTIAL',
                              'bytes': 2048, 'digest': digest,
                              'modified_ns': 1_700_000_000_000_000_000},)}
    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *a, **kw: approvals.append(a[1]) or
                        {'removed': 1, 'incomplete': False})
    monkeypatch.setattr(gui.messagebox, 'askyesno',
                        lambda title, body, **kw: prompts.append(body) or True)
    monkeypatch.setattr(gui.messagebox, 'showwarning',
                        lambda title, message, **kw: warnings.append((title, message)))
    monkeypatch.setattr(gui.messagebox, 'showinfo', lambda *a, **kw: None)

    button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
    _pump_manual_prune(root)
    assert warnings and warnings[-1][1] == copy_text(
        'settings.dialog.body.inventaris.sebagian.tidak.diverifikasi')
    picker = next(w for w in widgets(root)
                  if isinstance(w, tk.Toplevel) and w.title() ==
                  copy_text('settings.window.title.pilih.job.partial.gagal'))
    table = next(w for w in widgets(picker) if w.winfo_class() == 'Treeview')
    assert tuple(table.get_children()) == (token,)
    table.selection_set(token)
    button(picker, copy_text('settings.widget.hapus.terpilih')).invoke()
    _pump_manual_prune(root)
    assert approvals == [((token, digest),)]
    assert len(prompts) == 1 and token not in prompts[0]
    assert not app._manual_prune_busy and not ctl.active

def test_incomplete_cleanup_partial_scan_without_candidates_stops(
        settings, monkeypatch):
    from types import SimpleNamespace

    root, app, ctl, dialog, path, writes, errors = settings
    notices = []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    preview = {'total': 1, 'complete': 0, 'partial': 0, 'failed': 0,
               'protected': 1, 'estimated_bytes': 2048,
               'scan_complete': False, 'removable': ()}
    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *a, **kw: pytest.fail('No candidate to delete'))
    monkeypatch.setattr(gui.messagebox, 'showinfo',
                        lambda title, message, **kw: notices.append(title))

    button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
    _pump_manual_prune(root)
    assert notices == [copy_text('settings.dialog.title.inventaris.belum.lengkap')]
    assert not any(isinstance(w, tk.Toplevel) and w.title() ==
                   copy_text('settings.window.title.pilih.job.partial.gagal')
                   for w in widgets(root))
    assert not app._manual_prune_busy and not ctl.active

def test_incomplete_cleanup_records_counts_without_job_identity(
        settings, monkeypatch):
    from types import SimpleNamespace
    from spt_desktop import diagnostics
    from test_diagnostics import records

    root, app, ctl, dialog, path, writes, errors = settings
    token, digest = 'a' * 32, 'b' * 64
    preview = {'total': 1, 'complete': 0, 'partial': 1, 'failed': 0,
               'protected': 1, 'estimated_bytes': 2048,
               'scan_complete': True,
               'removable': ({'id': token, 'status': 'PARTIAL',
                              'bytes': 2048, 'digest': digest,
                              'modified_ns': 1_700_000_000_000_000_000},)}

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *a, **kw: {'removed': 1, 'incomplete': False,
                                          'rejected': ()})
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a, **kw: True)
    monkeypatch.setattr(gui.messagebox, 'showinfo', lambda *a, **kw: None)

    with diagnostics.session(path, 'gui'):
        button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
        _pump_manual_prune(root)
        picker = next(w for w in widgets(root)
                      if isinstance(w, tk.Toplevel) and w.title() ==
                      copy_text('settings.window.title.pilih.job.partial.gagal'))
        table = next(w for w in widgets(picker) if w.winfo_class() == 'Treeview')
        table.selection_set(token)
        button(picker, copy_text('settings.widget.hapus.terpilih')).invoke()
        _pump_manual_prune(root)

    rows = records(path)
    cleanup = [row for row in rows if row['event'] == 'jobs.incomplete_cleanup']
    assert len(cleanup) == 1
    assert (cleanup[0]['selected'], cleanup[0]['removed'],
            cleanup[0]['rejected']) == (1, 1, 0)
    assert not any(row['event'] == 'jobs.incomplete_rejected' for row in rows)
    assert not any(token in str(row) for row in rows)

def test_incomplete_cleanup_counts_rejected_jobs_not_reason_rows(
        settings, monkeypatch):
    from types import SimpleNamespace
    from spt_desktop import diagnostics
    from test_diagnostics import records

    root, app, ctl, dialog, path, writes, errors = settings
    ids = ('a' * 32, 'b' * 32)
    digests = ('c' * 64, 'd' * 64)
    preview = {'total': 2, 'complete': 0, 'partial': 2, 'failed': 0,
               'protected': 2, 'estimated_bytes': 4096,
               'scan_complete': True,
               'removable': tuple(
                   {'id': job_id, 'status': 'PARTIAL', 'bytes': 2048,
                    'digest': digest, 'modified_ns': 1_700_000_000_000_000_000 + index}
                   for index, (job_id, digest) in enumerate(zip(ids, digests)))}
    calls = []

    class ImmediateThread:
        def __init__(self, *, target, name, daemon):
            self.target = target

        def start(self):
            self.target()

    monkeypatch.setattr(gui, 'threading', SimpleNamespace(Thread=ImmediateThread))
    monkeypatch.setattr(gui, 'inspect_job_storage', lambda *a, **kw: preview)
    monkeypatch.setattr(gui, 'delete_incomplete_jobs',
                        lambda *a, **kw: calls.append(kw.get('report_reasons')) or
                        {'removed': 1, 'incomplete': True,
                         'rejected': ('changed', 'error')})
    monkeypatch.setattr(gui.messagebox, 'askyesno', lambda *a, **kw: True)
    monkeypatch.setattr(gui.messagebox, 'showwarning', lambda *a, **kw: None)
    monkeypatch.setattr(gui.messagebox, 'showinfo', lambda *a, **kw: None)

    with diagnostics.session(path, 'gui'):
        button(dialog, copy_text('settings.widget.hapus.job.partial.gagal')).invoke()
        _pump_manual_prune(root)
        picker = next(w for w in widgets(root)
                      if isinstance(w, tk.Toplevel) and w.title() ==
                      copy_text('settings.window.title.pilih.job.partial.gagal'))
        table = next(w for w in widgets(picker) if w.winfo_class() == 'Treeview')
        table.selection_set(*ids)
        button(picker, copy_text('settings.widget.hapus.terpilih')).invoke()
        _pump_manual_prune(root)

    assert calls == [True]
    rows = records(path)
    cleanup = [row for row in rows if row['event'] == 'jobs.incomplete_cleanup']
    assert len(cleanup) == 1
    assert (cleanup[0]['selected'], cleanup[0]['removed'],
            cleanup[0]['rejected']) == (2, 1, 1)
    assert len([row for row in rows
                if row['event'] == 'jobs.incomplete_rejected']) == 2
