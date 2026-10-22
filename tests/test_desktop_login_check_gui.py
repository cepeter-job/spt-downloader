"""Native settings checks are async, secret-free, and separate from exporting."""
import gc
from pathlib import Path
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


def test_check_button_launches_only_saved_account_no_npwp_no_password(window):
    root,app,ctl,path=window
    app.settings();root.update_idletasks()
    buttons=[widget.cget('text') for widget in descendants(root) if widget.winfo_class()=='TButton']
    assert 'Cek login' in buttons, 'Native settings credential-check button is missing'
    button(root,'Cek login').invoke()
    assert ctl.checks==[(ORIGIN,ACCOUNT,'msedge',True)]
    assert ctl.exports==[] and app.npwp.get()==''
    assert app.start_button.instate(['disabled'])
    assert button(root,'Simpan').instate(['disabled'])
    ctl.active=False
    app.on_event({'job_id':ctl.job_id,'type':'terminal','status':'LOGIN_OK','percent':0,'output':None,'message':'Login berhasil; kredensial tersimpan terverifikasi.'})
    assert 'Login berhasil' in app._credential_status.get()
    assert button(root,'Cek login').instate(['!disabled'])
    assert app.open_button.instate(['disabled']) and app.percent.get()!='100%'
    assert not (path/'jobs').exists()


def test_unsaved_password_disables_check_until_save(window,monkeypatch):
    root,app,ctl,path=window
    app.settings();root.update_idletasks()
    assert 'Cek login' in [w.cget('text') for w in descendants(root) if w.winfo_class()=='TButton']
    entry=next(w for w in descendants(root) if w.winfo_class()=='TEntry' and w.cget('show'))
    entry.insert(0,'SYNTHETIC_NEW_PASSWORD_ONLY')
    button(root,'Cek login').invoke()
    assert ctl.checks==[]
    assert 'Simpan' in app._credential_status.get()
    writes=[]
    monkeypatch.setattr(gui,'save_login',lambda *args:writes.append(args))
    button(root,'Simpan').invoke()
    assert writes==[(ORIGIN,ACCOUNT,'SYNTHETIC_NEW_PASSWORD_ONLY')]
    assert entry.get()=='' and button(root,'Cek login').instate(['!disabled'])
    assert 'SYNTHETIC_NEW_PASSWORD_ONLY' not in (path/'preferences.json').read_text()
    button(root,'Cek login').invoke()
    assert len(ctl.checks)==1


def test_closing_settings_cancels_and_waits_for_terminal_cleanup(window):
    root,app,ctl,path=window
    app.settings();root.update_idletasks()
    assert 'Cek login' in [w.cget('text') for w in descendants(root) if w.winfo_class()=='TButton']
    button(root,'Cek login').invoke()
    dialog=app._settings_dialog
    button(root,'Tutup').invoke()
    assert ctl.stops==1 and dialog.winfo_exists()
    ctl.active=False
    app.on_event({'job_id':ctl.job_id,'type':'terminal','status':'CANCELLED','percent':0,'output':None,'message':'Pengecekan dibatalkan.'})
    assert not dialog.winfo_exists() and app._settings_dialog is None


def test_check_keeps_previous_export_result_and_displays_honest_failure(window):
    root,app,ctl,path=window
    previous=path/'old-export';previous.mkdir();(previous/'resume.xlsx').write_bytes(b'SYNTHETIC_UNREAD_TRANSPORT_ONLY')
    app._result=previous;app.open_button.state(['!disabled'])
    export_state=app._ui_state
    app.settings();root.update_idletasks()
    assert 'Cek login' in [w.cget('text') for w in descendants(root) if w.winfo_class()=='TButton']
    button(root,'Cek login').invoke()
    ctl.active=False
    app.on_event({'job_id':ctl.job_id,'type':'terminal','status':'LOGIN_UNVERIFIED','percent':0,'output':None,'message':'Login belum terverifikasi; periksa koneksi.'})
    assert app._result==previous and app.open_button.instate(['!disabled'])
    assert app._ui_state==export_state
    assert 'belum terverifikasi' in app._credential_status.get()


def test_source_selftest_exercises_masked_settings_and_check_controls(tmp_path):
    import json,spt_gui
    report=tmp_path/'selftest.json'
    assert spt_gui.self_test(report)==0
    data=json.loads(report.read_text())
    assert 'Cek login' in data['gui_controls']
    assert data['credential_check_controls'] and not data['credentials_accessed'] and not data['live_scrape']
