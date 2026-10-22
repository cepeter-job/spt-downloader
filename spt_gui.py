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
from spt_desktop import diagnostics
from spt_desktop.paths import workspace_root,downloads_folder
from spt_desktop.runtime import resource_root, WORKER_FILES, python_version
from spt_desktop.windows import InstanceLock


def self_test(report=None):
    class SyntheticController:
        # Injection proves that constructing/rendering the GUI never prepares a worker.
        active = False
        operation = 'export'
        job_id = None

        def start(self, npwp, year, browser, headless, *, detail_source='dom', account=''):
            self.detail_source = detail_source
            self.account = account
            self.job_id = 'synthetic-self-test'
            self.active = True
            return self.job_id

        def poll(self):
            return self.active

        def read_request(self, event):
            return {'records': [
                {'record_id': '::synthetic {return}; [literal] / id', 'meta': {
                    'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Pembetulan 10'}},
                {'record_id': 'synthetic-badan-one', 'meta': {
                    'Jenis Pajak': 'PPh Badan', 'Masa Pajak': '2025', 'Model SPT': 'Pembetulan 2'}},
                {'record_id': 'synthetic-21', 'meta': {
                    'Jenis Pajak': 'PPh Pasal 21/26', 'Masa Pajak': 'Februari 2025', 'Model SPT': 'Normal'}},
                {'record_id': 'synthetic-badan-two', 'meta': {
                    'Jenis Pajak': 'pph badan', 'Masa Pajak': 'Januari - Desember 2025', 'Model SPT': 'Normal'}},
                {'record_id': 'synthetic-ppn-normal', 'meta': {
                    'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}},
                {'record_id': 'synthetic-ppn-one', 'meta': {
                    'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Pembetulan 1'}},
                {'record_id': 'synthetic-ppn-two', 'meta': {
                    'Jenis Pajak': 'PPN', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Pembetulan 2'}},
                {'record_id': 'synthetic-ppn-feb', 'meta': {
                    'Jenis Pajak': 'PPN', 'Masa Pajak': 'Februari 2025', 'Model SPT': 'Normal'}},
                {'record_id': 'synthetic-unifikasi', 'meta': {
                    'Jenis Pajak': 'PPh Unifikasi', 'Masa Pajak': 'Januari 2025', 'Model SPT': 'Normal'}},
            ]}

        def respond(self, kind, request_id, payload):
            self.selection_reply = (kind, request_id, payload)
            return True

        def stop(self):
            self.active = False

        def close(self):
            self.active = False

    root=tk.Tk();root.withdraw();app=None
    try:
        with tempfile.TemporaryDirectory(prefix='spt-desktop-selftest-') as folder:
            app=App(root,Path(folder),controller=SyntheticController());root.update_idletasks()
            # A mapped window is required: grid options alone do not prove placement.
            root.deiconify()
            contact=app.view.bugreport_label
            positions=[]
            for width,height in ((540,430),(800,620)):
                root.geometry(f'{width}x{height}')
                settled=tk.BooleanVar(root)
                root.after(250,lambda:settled.set(True))
                root.wait_variable(settled)
                root.update_idletasks()
                left=contact.winfo_rootx()-root.winfo_rootx()
                top=contact.winfo_rooty()-root.winfo_rooty()
                right=left+contact.winfo_width()
                bottom=top+contact.winfo_height()
                positions.append(bool(root.winfo_width()==max(width,root.minsize()[0])
                    and root.winfo_height()==max(height,root.minsize()[1])
                    and contact.winfo_viewable()
                    and 0<=left<right<=root.winfo_width()
                    and 0<=top<bottom<=root.winfo_height()
                    and root.winfo_width()-right<=app.view.px(32)
                    and root.winfo_height()-bottom<=app.view.px(32)
                    and contact.winfo_rooty()>=app.results_label.winfo_rooty()+app.results_label.winfo_height()))
                del settled
            bugreport_footer={'text':str(contact.cget('text')),'bottom_right':all(positions)}
            assert bugreport_footer=={'text':'bugreport : sharmila@kemenkeu.go.id','bottom_right':True}
            root.withdraw()
            assert app.start_button.cget('text')=='Mulai unduh'
            assert app.npwp.get()==''
            assert app.stop_button.instate(['disabled'])
            dialog=app.settings();root.update_idletasks()
            def descendants(widget):
                for child in widget.winfo_children():
                    yield child;yield from descendants(child)
            main_labels={w.cget('text') for w in descendants(root) if w.winfo_class()=='TLabel'}
            personal_use_labels=sorted(text for text in main_labels if 'for personal use' in text)
            assert personal_use_labels==['Coretax → Excel · for personal use only']
            assert not any('read-only' in text or 'data perpajakan rahasia' in text for text in main_labels)
            widgets=list(descendants(dialog))
            from spt_desktop.credentials import LOGIN_ORIGIN,ALLOWED_ORIGINS
            origin_selector=any(w.winfo_class()=='TCombobox' and
                any(origin in tuple(w.cget('values')) for origin in ALLOWED_ORIGINS) for w in widgets)
            automatic_login={'origin_selector_present':origin_selector,
                'credential_origin':'satu' if app.preferences['login_origin']==LOGIN_ORIGIN else 'other'}
            assert not origin_selector
            assert 'Origin login' not in {w.cget('text') for w in widgets if w.winfo_class()=='TLabel'}
            labels={w.cget('text') for w in widgets if w.winfo_class()=='TButton'}
            assert {'Cek login','Batalkan cek','Simpan','Tutup','Buka folder log'}<=labels
            assert any(w.winfo_class()=='TEntry' and w.cget('show')=='●' for w in widgets)
            background=[w for w in widgets if w.winfo_class()=='TCheckbutton']
            assert len(background)==1
            headings=[w for w in descendants(root) if w.winfo_class()=='TLabel'
                      and str(w.cget('style'))=='Title.TLabel']
            assert len(headings)==1
            ui_text={'title':headings[0].cget('text'),'background':background[0].cget('text'),
                     'results':app.results_label.cget('text')}
            assert root.title()==ui_text['title']
            assert ui_text=={
                'title':'Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',
                'background':'jalankan proses sedot di background',
                'results':'Hasil Sedot berada di folder Downloads Windows'}
            gui_controls=sorted({w.cget('text') for w in descendants(root)
                                 if w.winfo_class()=='TButton'})
            modes=[w for w in widgets if w.winfo_class()=='TCombobox'
                   and tuple(w.cget('values'))==('DOM','JSON-hybrid (pilot)')]
            assert len(modes)==1 and modes[0].get()=='JSON-hybrid (pilot)' and modes[0].instate(['readonly'])
            mode_control={'labels':list(modes[0].cget('values')),'default':app.preferences['detail_source']}
            modes[0].current(1)
            next(w for w in widgets if w.winfo_class()=='TButton' and w.cget('text')=='Simpan').invoke()
            from spt_desktop.app import load_preferences
            mode_control['saved']=load_preferences(Path(folder))['detail_source']
            assert mode_control['saved']=='json-first'
            app._settings_close()
            assert all((resource_root()/name).is_file() for name in WORKER_FILES)
            if getattr(sys,'frozen',False):assert (resource_root()/'tools'/'uv.exe').is_file()
            app.npwp.set('0000000000000001');app.year.set('2025')
            app.preferences['identifier']='SYNTHETIC_ACCOUNT'
            app.start()
            automatic_login['account_forwarded']=app.controller.account=='SYNTHETIC_ACCOUNT'
            assert automatic_login=={'origin_selector_present':False,'credential_origin':'satu','account_forwarded':True}
            mode_control['started']=app.controller.detail_source
            assert mode_control['started']=='json-first'
            app.on_event({'job_id':app.controller.job_id, 'type':'selection_required',
                          'request_id':'a'*32, 'stage':'selection', 'percent':20,
                          'message':'Synthetic selection self-test'})
            root.update()
            selection=app._interaction['dialog']
            tree=next(w for w in descendants(selection) if w.winfo_class()=='Treeview')
            initial=list(tree.get_children())
            initial_ids=[tree.item(iid,'values')[3] for iid in initial]
            assert initial_ids==[
                'synthetic-badan-two','synthetic-badan-one','synthetic-21','synthetic-unifikasi',
                'synthetic-ppn-normal','synthetic-ppn-one','synthetic-ppn-two',
                '::synthetic {return}; [literal] / id','synthetic-ppn-feb']
            assert not tree.selection()
            # Header and reply oracles refer to inventory order, not the new display order.
            by_id={tree.item(iid,'values')[3]:iid for iid in initial}
            original=[by_id[record['record_id']] for record in app.controller.read_request(None)['records']]
            chosen=(original[0],original[3])
            tree.selection_set(chosen)
            tree.event_generate('<<TreeviewSelect>>')
            root.update()
            sorting={'heading':tree.heading('type','text'), 'directions':[],
                     'hierarchy':['type','year','month','model'], 'ordered_ids':[],
                     'default_ordered_ids':initial_ids}
            values={iid:tuple(tree.item(iid,'values')) for iid in original}
            # Independent literal oracles: never compute expectations with the sort key.
            for expected_order in ((3,1,2,8,4,5,6,0,7),(4,5,6,0,7,8,2,3,1)):
                root.tk.call(tree.heading('type','command'))
                root.update()
                observed=list(tree.get_children())
                assert observed==[original[index] for index in expected_order]
                sorting['ordered_ids'].append([tree.item(iid,'values')[3] for iid in observed])
                assert set(tree.selection())==set(chosen)
                assert {iid:tuple(tree.item(iid,'values')) for iid in observed}==values
                sorting['directions'].append(tree.heading('type','text'))
            next(w for w in descendants(selection) if w.winfo_class()=='TButton'
                 and w.cget('text')=='Sedot SPT terpilih').invoke()
            expected_ids=[values[iid][3] for iid in chosen]
            assert app.controller.selection_reply==('selection','a'*32,{'selected_ids':expected_ids})
            assert app._interaction is None
            sorting['confirmed_ids']=app.controller.selection_reply[2]['selected_ids']
            sorting['selection_preserved']=True
            app.on_event({'job_id':app.controller.job_id,'type':'progress','stage':'details',
                          'percent':42,'message':'Self-test synthetic progress'})
            assert app.percent.get()=='42%'
            diagnostic_report=diagnostics.self_test(Path(folder)/'diagnostic-test')
            data={'diagnostics':diagnostic_report,'ok':True,'python':sys.version.split()[0],'bits':struct.calcsize('P')*8,
                  'python_implementation':platform.python_implementation(),
                  'free_threaded':bool(sysconfig.get_config_var('Py_GIL_DISABLED')),
                  'tcl':str(root.tk.call('info','patchlevel')),
                  'tk':str(root.tk.call('package','provide','Tk')),
                  'worker_python':python_version(),
                  'frozen':bool(getattr(sys,'frozen',False)),
                  'worker_resources':list(WORKER_FILES),'uv_bundled':(resource_root()/'tools'/'uv.exe').is_file(),
                  'gui_controls':gui_controls,
                  'detail_source_control':mode_control,
                  'selection_sorting_control':sorting,
                  'automatic_login_controls':automatic_login,
                  'bugreport_footer':bugreport_footer,
                  'credential_check_controls':True,'personal_use_labels':personal_use_labels,'ui_text':ui_text,
                  'known_folder_resolution':bool(workspace_root() and downloads_folder()),
                  'live_scrape':False,'credentials_accessed':False}
            if report:
                report=Path(report);report.parent.mkdir(parents=True,exist_ok=True)
                report.write_text(json.dumps(data,indent=2),encoding='utf-8')
            elif sys.stdout:print(json.dumps(data))
            return 0
    finally:
        if app is not None:app.controller.close();app._dispose()
        # Retire the self-test's recurring poll before another Tk root exists.
        for callback in root.tk.splitlist(root.tk.call('after','info')):
            root.after_cancel(callback)
        root.destroy()


def main(argv=None):
    parser=argparse.ArgumentParser(description='Simple authorized Coretax to Excel desktop app')
    parser.add_argument('--self-test',action='store_true');parser.add_argument('--report',type=Path)
    args=parser.parse_args(argv)
    if args.self_test:return self_test(args.report)
    with diagnostics.session(diagnostics.default_root(), 'gui'):
        return _run_gui()


def _run_gui():
    root=tk.Tk();root.withdraw();app=None
    try:
        workspace=workspace_root()
        with InstanceLock(workspace):
            app=App(root,workspace);root.deiconify();root.mainloop()
        return 0
    except RuntimeError as error:
        diagnostics.record('gui.failed', error=error, level='ERROR', phase='startup')
        messagebox.showerror('SPT Downloader','Aplikasi sudah berjalan. Gunakan jendela yang sudah terbuka.',parent=root)
        return 1
    except Exception as error:
        diagnostics.record('gui.failed', error=error, level='ERROR', phase='startup')
        messagebox.showerror('SPT Downloader','Aplikasi tidak dapat dibuka. Periksa izin LocalAppData dan kelengkapan executable.',parent=root)
        return 1
    finally:
        if app:app.controller.close()
        try:root.destroy()
        except tk.TclError:pass


if __name__=='__main__':raise SystemExit(main())
