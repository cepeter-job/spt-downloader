"""Windows Tk notification tests; network and browser launch are stubbed."""
import tkinter as tk

import pytest

from spt_desktop import app as gui
from spt_desktop import update_notice
from support_gui import Controller, button, widgets


def test_check_updates_without_valid_build_does_not_fetch_or_open_browser(tmp_path, monkeypatch):
    notices = []
    monkeypatch.setattr(gui, 'read_build_info', lambda: None)
    def forbidden(*args, **kwargs):
        raise AssertionError('No update fetch or browser navigation without valid build identity')
    monkeypatch.setattr(update_notice, 'fetch_notice', forbidden)
    monkeypatch.setattr(gui.webbrowser, 'open', forbidden)
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


def test_automatic_notice_deferred_until_active_job_finishes(tmp_path):
    root = tk.Tk()
    controller = Controller()
    try:
        app = gui.App(root, tmp_path, controller=controller)
        controller.active = True
        notice = update_notice.UpdateNotice('b' * 40, '420', 1)
        app._update_pending = True
        app._update_results.put(('ok', notice))
        app._receive_update(manual=False)
        assert app._update_pending
        assert app._update_results.qsize() == 1
        assert app._update_dialog is None
        assert app._update_after is not None
        assert not app._update_seen

        root.after_cancel(app._update_after)
        controller.active = False
        app._receive_update(manual=False)
        assert not app._update_pending
        assert app._update_results.empty()
        assert app._update_dialog is not None
        assert app._update_seen == {'420'}
        button(app._update_dialog, 'Close').invoke()
        app._dispose()
    finally:
        controller.active = False
        root.destroy()


def test_automatic_notice_deferred_until_settings_closed(tmp_path):
    root = tk.Tk()
    try:
        app = gui.App(root, tmp_path, controller=Controller())
        root.update()
        settings = app.settings()
        notice = update_notice.UpdateNotice('b' * 40, '420', 1)
        app._update_pending = True
        app._update_results.put(('ok', notice))
        app._receive_update(manual=False)
        assert app._update_pending
        assert app._update_results.qsize() == 1
        assert app._update_dialog is None
        assert root.grab_current() is settings

        root.after_cancel(app._update_after)
        app._settings_close()
        app._receive_update(manual=False)
        assert not app._update_pending
        assert app._update_results.empty()
        assert app._update_dialog is not None
        assert root.grab_current() is None
        button(app._update_dialog, 'Close').invoke()
        app._dispose()
    finally:
        root.destroy()


@pytest.mark.parametrize('result', [('ok', None), ('unavailable', None)])
def test_automatic_check_reschedules_next_day(tmp_path, monkeypatch, result):
    root = tk.Tk()
    try:
        app = gui.App(root, tmp_path, controller=Controller())
        app._owns_controller = True  # Exercise production scheduling without constructing a real worker.
        scheduled = []
        actual_after = root.after
        def capture_after(milliseconds, callback, *args):
            scheduled.append(milliseconds)
            return actual_after(milliseconds, callback, *args)
        monkeypatch.setattr(root, 'after', capture_after)
        app._update_pending = True
        app._update_results.put(result)
        app._receive_update(manual=False)
        assert not app._update_pending
        assert scheduled == [24 * 60 * 60 * 1000]
        assert app._update_after is not None
        assert app._update_dialog is None
        app._dispose()
    finally:
        root.destroy()


@pytest.mark.parametrize(('outcome', 'factory'), [
    ('up_to_date', lambda: None),
    ('update_available', lambda: update_notice.UpdateNotice('b' * 40, '420', 1)),
    ('unavailable', lambda: update_notice.UpdateLookupError('PRIVATE URL and token')),
])
def test_update_lookup_logs_safe_outcome_and_bounded_elapsed(
        monkeypatch, outcome, factory):
    emitted = []
    monkeypatch.setattr(gui.diagnostics, 'record',
                        lambda event, **fields: emitted.append((event, fields)))
    value = factory()

    def fake_fetch(url, installed):
        assert url == update_notice.MANIFEST_URL
        assert installed == {'synthetic': True}
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(update_notice, 'fetch_notice', fake_fetch)
    state, notice = gui._fetch_update_with_logging({'synthetic': True}, manual=True)
    assert (state, notice) == (('unavailable', None) if outcome == 'unavailable'
                               else ('ok', value))
    assert len(emitted) == 1
    event, fields = emitted[0]
    assert event == 'update.check'
    assert fields['update_check_result'] == outcome
    assert fields['update_check_trigger'] == 'manual'
    assert type(fields['duration_ms']) is float
    assert fields['duration_ms'] >= 0
    assert set(fields) == {'duration_ms', 'update_check_result', 'update_check_trigger'}
    assert 'PRIVATE' not in str(fields)


def test_check_updates_logs_invalid_build_and_throttles_active_deferrals(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(gui.diagnostics, 'record',
                        lambda event, **kw: events.append((event, kw)))
    monkeypatch.setattr(gui, 'read_build_info', lambda: None)
    monkeypatch.setattr(gui.messagebox, 'showinfo', lambda *args, **kwargs: None)
    controller = Controller()
    root = tk.Tk()
    try:
        app = gui.App(root, tmp_path, controller=controller)
        controller.active = True
        app.check_updates()
        assert events[-1] == ('update.check', {'update_check_result': 'deferred_active',
                                              'update_check_trigger': 'automatic'})
        root.after_cancel(app._update_after)
        app.check_updates()
        assert len(events) == 1
        root.after_cancel(app._update_after)
        controller.active = False
        app.check_updates(manual=True)
        assert events[-1] == ('update.check', {'update_check_result': 'invalid_build',
                                              'update_check_trigger': 'manual'})
        assert app._update_after is None and not app._update_pending
        app._dispose()
    finally:
        controller.active = False
        root.destroy()


def test_update_notice_deferral_logs_once_until_presented(tmp_path, monkeypatch):
    events = []
    monkeypatch.setattr(gui.diagnostics, 'record',
                        lambda event, **kw: events.append((event, kw)))
    root = tk.Tk()
    controller = Controller()
    try:
        app = gui.App(root, tmp_path, controller=controller)
        notice = update_notice.UpdateNotice('b' * 40, '420', 1)
        app._update_pending = True
        app._update_results.put(('ok', notice))
        controller.active = True
        app._receive_update(manual=False)
        assert events == [('update.check', {'update_check_result': 'notice_deferred',
                                             'update_check_trigger': 'automatic'})]
        root.after_cancel(app._update_after)
        app._receive_update(manual=False)
        assert len(events) == 1
        root.after_cancel(app._update_after)
        controller.active = False
        app._receive_update(manual=False)
        assert app._update_dialog is not None
        assert not app._update_notice_deferred_logged
        button(app._update_dialog, 'Close').invoke()
        app._dispose()
    finally:
        controller.active = False
        root.destroy()
