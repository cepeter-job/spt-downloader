"""Windows executable entrypoint; runtime preparation starts only from Mulai."""
import argparse
import json
from pathlib import Path
import platform
import struct
import sys
import sysconfig
import tempfile
import tkinter as tk
from tkinter import messagebox
from spt_desktop.app import App
from spt_desktop.paths import workspace_root,downloads_folder
from spt_desktop.runtime import resource_root, WORKER_FILES, python_version
from spt_desktop.windows import InstanceLock


def self_test(report=None):
    root=tk.Tk();root.withdraw()
    try:
        with tempfile.TemporaryDirectory(prefix='spt-desktop-selftest-') as folder:
            app=App(root,Path(folder));root.update_idletasks()
            assert app.start_button.cget('text')=='Mulai'
            assert app.stop_button.instate(['disabled'])
            dialog=app.settings();root.update_idletasks()
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child;yield from descendants(child)
            main_labels={w.cget('text') for w in descendants(root) if w.winfo_class()=='TLabel'}
            personal_use_labels=sorted(text for text in main_labels if 'for personal use' in text)
            assert personal_use_labels==['Coretax → Excel · for personal use only','for personal use : punto ap']
            assert not any('read-only' in text or 'data perpajakan rahasia' in text for text in main_labels)
            widgets=list(descendants(dialog))
            labels={w.cget('text') for w in widgets if w.winfo_class()=='TButton'}
            assert {'Cek Kredensial','Batalkan Cek','Simpan','Tutup'}<=labels
            assert any(w.winfo_class()=='TEntry' and w.cget('show')=='●' for w in widgets)
            app._settings_close()
            assert all((resource_root()/name).is_file() for name in WORKER_FILES)
            if getattr(sys,'frozen',False):assert (resource_root()/'tools'/'uv.exe').is_file()
            app.on_event({'type':'progress','percent':42,'message':'Self-test synthetic progress'})
            assert app.percent.get()=='42%'
            data={'ok':True,'python':sys.version.split()[0],'bits':struct.calcsize('P')*8,
                  'python_implementation':platform.python_implementation(),
                  'free_threaded':bool(sysconfig.get_config_var('Py_GIL_DISABLED')),
                  'tcl':str(root.tk.call('info','patchlevel')),
                  'tk':str(root.tk.call('package','provide','Tk')),
                  'worker_python':python_version(),
                  'frozen':bool(getattr(sys,'frozen',False)),
                  'worker_resources':list(WORKER_FILES),'uv_bundled':(resource_root()/'tools'/'uv.exe').is_file(),
                  'gui_controls':['NPWP','Tahun pajak','Mulai','Stop','Pengaturan','Buka Hasil','Cek Kredensial','Batalkan Cek'],
                  'credential_check_controls':True,'personal_use_labels':personal_use_labels,
                  'known_folder_resolution':bool(workspace_root() and downloads_folder()),
                  'live_scrape':False,'credentials_accessed':False}
            if report:
                report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
                report.write_text(json.dumps(data,indent=2),encoding='utf-8')
            elif sys.stdout:print(json.dumps(data))
            return 0
    finally:root.destroy()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Simple authorized Coretax to Excel desktop app')
    parser.add_argument('--self-test',action='store_true');parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv)
    if args.self_test:return self_test(args.report)
    root=tk.Tk();root.withdraw();app=None
    try:
        workspace=workspace_root()
        with InstanceLock(workspace):
            app=App(root,workspace);root.deiconify();root.mainloop()
        return 0
    except RuntimeError:
        messagebox.showerror('SPT Downloader','Aplikasi sudah berjalan. Gunakan jendela yang sudah terbuka.',parent=root)
        return 1
    except Exception:
        messagebox.showerror('SPT Downloader','Aplikasi tidak dapat dibuka. Periksa izin LocalAppData dan kelengkapan executable.',parent=root)
        return 1
    finally:
        if app:app.controller.close()
        try:root.destroy()
        except tk.TclError:pass


if __name__=='__main__':raise SystemExit(main())
