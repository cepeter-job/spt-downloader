"""Simple native Windows interface; settings persist no password/token values."""
from datetime import date
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from .controller import JobController,validate_job_scope
from .credentials import ALLOWED_ORIGINS,save_login,delete_login
from .ui_copy import copy_text
from .ui_state import ExportState, begin_export, scope_errors, reduce_export, mark_stopping, record_reply
from .ui_views import MainView

#punto ami priyono

DEFAULTS={'browser':'msedge','headless':True,'login_origin':ALLOWED_ORIGINS[1],'identifier':''}


def load_preferences(root):
    try:data=json.loads((Path(root)/'preferences.json').read_text(encoding='utf-8'))
    except (OSError,ValueError):return dict(DEFAULTS)
    if not isinstance(data,dict):return dict(DEFAULTS)
    result=dict(DEFAULTS)
    if data.get('browser') in ('msedge','chrome'):result['browser']=data['browser']
    if type(data.get('headless')) is bool:result['headless']=data['headless']
    if data.get('login_origin') in ALLOWED_ORIGINS:result['login_origin']=data['login_origin']
    if isinstance(data.get('identifier'),str) and len(data['identifier'])<=256:result['identifier']=data['identifier']
    return result


def save_preferences(root,data):
    allowed={key:data.get(key,default) for key,default in DEFAULTS.items()}
    if allowed['browser'] not in ('msedge','chrome') or allowed['login_origin'] not in ALLOWED_ORIGINS:
        raise ValueError('Preferensi browser/origin tidak valid.')
    if type(allowed['headless']) is not bool or not isinstance(allowed['identifier'],str):
        raise ValueError('Preferensi tidak valid.')
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    temporary=root/'preferences.tmp'
    temporary.write_text(json.dumps(allowed,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(root/'preferences.json')


class App:
    def __init__(self,root,workspace,controller=None):
        self.root=root;self.workspace=Path(workspace)
        self.preferences=load_preferences(self.workspace)
        self.controller=controller or JobController(self.workspace,self.on_event)
        self._closing=False;self._result=None
        self._settings_dialog=None
        self._credential_status=None
        self._settings_refresh=None
        self._settings_close=None
        self._settings_closing=False
        self._interaction=None
        self._interaction_seen=set()
        self._interaction_stopped_job=None
        self._ui_state = ExportState()
        self._poll_after = None
        self._poll_failed = False
        self._disposed = False
        root.title(copy_text('app.title'))
        self.view = MainView(root, year_default=str(date.today().year),
                            on_start=self.start, on_stop=self.stop,
                            on_settings=self.settings, on_open_result=self.open_result)
        self.view.pack(fill='both', expand=True)
        for name in ('npwp', 'year', 'status', 'percent', 'npwp_entry', 'year_entry',
                     'start_button', 'stop_button', 'settings_button', 'open_button',
                     'bar', 'results_label'):
            setattr(self, name, getattr(self.view, name))
        root.protocol('WM_DELETE_WINDOW', self.request_close)
        root.bind('<Alt-m>', lambda event: self.start())
        root.bind('<Alt-s>', lambda event: self.stop())
        root.bind('<Alt-p>', lambda event: self.settings())
        self.npwp_entry.bind('<Return>', lambda event: self.start())
        self.year_entry.bind('<Return>', lambda event: self.start())
        root.bind('<Destroy>', self._on_destroy, add='+')
        self.npwp_entry.focus_set()
        self._poll_after = root.after(100, self._poll)

    def _running(self, active):
        stopping = (active and getattr(self.controller, 'job_id', None) == self._interaction_stopped_job)
        self.view.set_busy(active, stopping=stopping)

    def start(self):
        if self.controller.active or self._closing or self._disposed:
            return
        errors = scope_errors(self.npwp.get(), self.year.get())
        self.view.show_errors(errors)
        if errors:
            self.status.set('Periksa kembali NPWP dan tahun pajak.')
            (self.npwp_entry if 'npwp' in errors else self.year_entry).focus_set()
            return
        self._close_interaction()
        try:
            npwp, year = validate_job_scope(self.npwp.get(), self.year.get())
            job_id = self.controller.start(npwp, str(year), self.preferences['browser'], self.preferences['headless'])
            self._ui_state = begin_export(job_id, npwp, str(year))
        except (ValueError, RuntimeError) as error:
            messagebox.showerror('Tidak dapat mulai', str(error), parent=self.root)
            return
        self._interaction_seen.clear()
        self._interaction_stopped_job = None
        self._poll_failed = False
        self._result = None
        self.status.set('Menyiapkan aplikasi untuk mengunduh SPT.')
        self.view.render(self._ui_state, active=True)
        self.stop_button.focus_set()

    def stop(self):
        job_id = getattr(self.controller, 'job_id', None)
        if not self.controller.active:
            self._close_interaction()
            return
        if self._interaction_stopped_job == job_id:
            return
        self._interaction_stopped_job = job_id
        self._close_interaction()
        self.controller.stop()
        if getattr(self.controller, 'operation', 'export') == 'login_check':
            message = 'Menghentikan pengecekan… tidak ada ekspor.'
            if self._credential_status is not None:
                self._credential_status.set(message)
            self.status.set(message)
            self._running(True)
        else:
            self._ui_state = mark_stopping(self._ui_state)
            self.status.set('Menghentikan unduhan… data sementara tetap disimpan.')
            self.view.render(self._ui_state, active=True)
        self.stop_button.state(['disabled'])

    def on_event(self, event):
        if self._disposed:
            return
        job_id = getattr(self.controller, 'job_id', None)
        if not job_id or event.get('job_id') != job_id:
            return
        kind = event['type']
        if kind == 'terminal' and self.controller.active:
            return
        if getattr(self.controller, 'operation', 'export') == 'login_check':
            if kind != 'terminal' and self._interaction_stopped_job == job_id:
                return
            message = event.get('message', '')[:500]
            self.status.set(message)
            if self._credential_status is not None:
                self._credential_status.set(message)
            if kind == 'terminal':
                self.bar.stop()
                self.bar.configure(mode='determinate', value=0)
                self.percent.set('—')
                self._running(False)
                if self._settings_refresh:
                    self._settings_refresh(preserve_status=True)
                if self._settings_closing and self._settings_close:
                    self._settings_close()
            else:
                if str(self.bar['mode']) != 'indeterminate':
                    self.bar.configure(mode='indeterminate')
                    self.bar.start(20)
                self.percent.set('—')
            return
        if kind in ('selection_required', 'overwrite_required'):
            if (not self._export_job_active(job_id)
                    or (job_id, event.get('request_id')) in self._interaction_seen):
                return
        state = reduce_export(self._ui_state, event, controller_active=self.controller.active)
        if state is self._ui_state:
            return
        self._ui_state = state
        self.status.set(event.get('message', '')[:500])
        if kind == 'terminal':
            self._interaction_stopped_job = job_id
            self._close_interaction()
            self.status.set(state.terminal_status + ' · ' + event.get('message', '')[:450])
            self._result = Path(state.output) if state.output else None
        self.view.render(state, active=self.controller.active)
        if kind == 'selection_required':
            self.selection_dialog(event)
        elif kind == 'overwrite_required':
            self.overwrite_dialog(event)
        elif kind == 'terminal':
            # The result pane may have scrolled the form out of view.
            # Keep keyboard focus on a visible action rather than the hidden input.
            target = self.open_button if self.open_button.instate(['!disabled']) else self.start_button
            target.focus_set()

    def _poll(self):
        self._poll_after = None
        if self._disposed:
            return
        try:
            self.controller.poll()
        except Exception:
            # A monitoring error is not proof that the owned process has exited.
            # Request cleanup once, but leave the UI busy until the controller is idle.
            if not self._poll_failed:
                self._poll_failed = True
                self._interaction_stopped_job = getattr(self.controller, 'job_id', None)
                self._close_interaction()
                self.controller.close()
                if getattr(self.controller, 'operation', 'export') == 'export':
                    self._ui_state = mark_stopping(self._ui_state)
                    self.view.render(self._ui_state, active=self.controller.active)
                else:
                    self._running(self.controller.active)
            self.status.set('Proses belum bisa dipantau. Menunggu proses berhenti; hasil belum dinyatakan selesai.')
            if not self.controller.active and self._ui_state.job_id == getattr(self.controller, 'job_id', None):
                self.on_event({'job_id': self._ui_state.job_id, 'type': 'terminal', 'status': 'ERROR',
                    'percent': min(99, self._ui_state.percent or 0), 'output': None,
                    'message': 'Proses tidak dapat dipantau. Periksa koneksi dan buka ulang aplikasi.'})
        if self._interaction is not None and not self._interaction_current(self._interaction):
            self._close_interaction()
        if self._closing and not self.controller.active:
            self.controller.close()
            self._dispose()
            self.root.destroy()
            return
        self._poll_after = self.root.after(100, self._poll)

    def _on_destroy(self, event):
        if event.widget is self.root:
            self._dispose()

    def _dispose(self):
        if self._disposed:
            return
        self._disposed = True
        if self._poll_after is not None:
            try:
                self.root.after_cancel(self._poll_after)
            except tk.TclError:
                # Root teardown may already have removed the pending poll command.
                pass
            self._poll_after = None
        self.view.dispose()

    def request_close(self):
        if self._disposed:
            return
        if self.controller.active:
            if not messagebox.askyesno('Hentikan pekerjaan?', 'Hentikan worker milik aplikasi dan tutup jendela? Checkpoint lokal tidak dihapus.',
                                       parent=self.root, default='no'):
                return
            self._closing = True
            self.stop()
        else:
            self._close_interaction()
            self.controller.close()
            self._dispose()
            self.root.destroy()

    def open_result(self):
        if self._result and self._result.is_dir():os.startfile(str(self._result))
        else:messagebox.showerror('Hasil tidak ditemukan','Folder hasil tidak lagi tersedia.',parent=self.root)

    def _export_job_active(self,job_id):
        return (isinstance(job_id,str) and bool(job_id) and not self._closing
                and self.controller.active and getattr(self.controller,'operation','export')=='export'
                and job_id==getattr(self.controller,'job_id',None) and job_id!=self._interaction_stopped_job)

    def _read_interaction(self,event,kind):
        job_id=event.get('job_id');request_id=event.get('request_id')
        if (not self._export_job_active(job_id) or event.get('type')!=kind+'_required'
                or not isinstance(request_id,str) or len(request_id)!=32
                or any(character not in '0123456789abcdef' for character in request_id)):
            return None
        if (job_id,request_id) in self._interaction_seen:return None
        if self._interaction is not None:
            if self._interaction['key'][0]==job_id:return None
            self._close_interaction()
        self._interaction_seen.add((job_id,request_id))
        try:
            payload=self.controller.read_request(event)
            if not isinstance(payload,dict):raise ValueError('Invalid confirmation data')
        except (OSError,ValueError,RuntimeError):
            self._interaction_error(job_id,'Daftar konfirmasi belum bisa dibuka.');return None
        return (job_id,kind,request_id),payload

    def _new_interaction(self,key,title):
        previous_focus=self.root.focus_get()
        dialog=tk.Toplevel(self.root);dialog.title(title)
        dialog.transient(self.root)
        interaction={'key':key,'dialog':dialog,'focus':previous_focus,'traces':[]}
        self._interaction=interaction
        dialog.grab_set()
        dialog.bind('<Alt-s>',lambda event:self._cancel_interaction(interaction))
        return interaction

    def _interaction_current(self,interaction):
        return (self._interaction is interaction and self._export_job_active(interaction['key'][0])
                and interaction['dialog'].winfo_exists())

    def _close_interaction(self,interaction=None):
        current=self._interaction
        if current is None or (interaction is not None and current is not interaction):return
        # Invalidate callbacks before destroying their widgets or releasing the grab.
        self._interaction=None
        for variable,token in current['traces']:
            try:variable.trace_remove('write',token)
            except tk.TclError:
                # Window shutdown may already have removed this Tcl variable or trace.
                pass
        current['traces'].clear()
        dialog=current['dialog']
        try:
            if dialog.grab_current() is dialog:dialog.grab_release()
            dialog.destroy()
        except tk.TclError:
            # Parent shutdown may already have destroyed the dialog and released its grab.
            pass
        focus=current['focus']
        try:
            if (focus is None or not focus.winfo_exists()
                    or (isinstance(focus,ttk.Widget) and focus.instate(['disabled']))):
                focus=self.stop_button if self.controller.active else self.npwp_entry
            focus.focus_set()
        except tk.TclError:
            # Focus cannot be restored after its widget or Tcl interpreter is destroyed.
            pass

    def _cancel_interaction(self,interaction):
        active=self._interaction_current(interaction)
        self._close_interaction(interaction)
        if active:self.stop()
        return 'break'

    def _interaction_error(self,job_id,message):
        if self._export_job_active(job_id):
            self.stop()
            self.status.set(message+' Menghentikan unduhan…')

    def _reply_interaction(self,interaction,payload):
        if not self._interaction_current(interaction):
            self._close_interaction(interaction);return 'break'
        job_id,kind,request_id=interaction['key']
        self._close_interaction(interaction)
        try:
            # A stale response may arrive during terminal cleanup. Do not turn
            # that dismissal into a new cancellation of the worker's result.
            if not self.controller.respond(kind,request_id,payload):return 'break'
            if self._export_job_active(job_id):
                self._ui_state = record_reply(self._ui_state, job_id=job_id, kind=kind,
                    request_id=request_id,
                    selected_count=len(payload['selected_ids']) if kind == 'selection' else None,
                    overwrite=payload.get('overwrite'))
                if kind == 'selection':
                    total = self._ui_state.selected_count
                    self.status.set(f'SPT diproses 0/{total}; terverifikasi 0.')
                self.view.render(self._ui_state, active=True)
        except (OSError,ValueError,RuntimeError):
            self._interaction_error(job_id,'Keputusan belum bisa diproses.')
        return 'break'

    def selection_dialog(self,event):
        request=self._read_interaction(event,'selection')
        if request is None:return
        key,payload=request
        rows={};identifiers=set()
        try:
            records=payload.get('records')
            if not isinstance(records,list):raise ValueError('Invalid inventory')
            for ordinal,record in enumerate(records):
                if not isinstance(record,dict):raise ValueError('Invalid inventory record')
                identifier=record.get('record_id');meta=record.get('meta',{})
                if (not isinstance(identifier,str) or not identifier or len(identifier)>512
                        or identifier in identifiers or not isinstance(meta,dict)):
                    raise ValueError('Invalid inventory identifier or metadata')
                identifiers.add(identifier)
                values=tuple(str(meta.get(field,'')) for field in ('Jenis Pajak','Masa Pajak','Model SPT'))+(identifier,)
                # Source IDs are data, never widget paths or Tcl item identifiers.
                rows[f'record-{ordinal}']=(identifier,values,' '.join(values).casefold())
        except (TypeError,ValueError):
            self._interaction_error(key[0],'Daftar SPT belum bisa ditampilkan.');return
        interaction=self._new_interaction(key,'Pilih SPT yang akan diunduh')
        dialog=interaction['dialog'];dialog.minsize(620,360)
        frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True)
        frame.columnconfigure(0,weight=1);frame.rowconfigure(3,weight=1)
        ttk.Label(frame,text='Pilih satu atau beberapa SPT. Rincian hanya diambil untuk pilihan yang dikonfirmasi.',
                  wraplength=620).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
        ttk.Label(frame,text='Cari jenis pajak, masa, pembetulan, atau ID SPT').grid(row=1,column=0,columnspan=2,sticky='w')
        search=tk.StringVar(dialog)
        entry=ttk.Entry(frame,textvariable=search)
        entry.grid(row=2,column=0,columnspan=2,sticky='ew',pady=(4,12))
        columns=('type','period','model','identifier')
        tree=ttk.Treeview(frame,columns=columns,show='headings',selectmode='extended',height=10)
        for column,label,width in zip(columns,('Jenis pajak','Masa pajak','Normal / pembetulan','ID SPT'),(160,180,160,180)):
            tree.heading(column,text=label);tree.column(column,width=width,minwidth=100)
        tree.grid(row=3,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(frame,orient='vertical',command=tree.yview)
        vertical.grid(row=3,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview)
        horizontal.grid(row=4,column=0,sticky='ew')
        tree.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        summary=tk.StringVar(dialog)
        ttk.Label(frame,textvariable=summary,wraplength=620).grid(row=5,column=0,columnspan=2,sticky='w',pady=(10,0))
        ttk.Label(frame,text='Gunakan Ctrl atau Shift untuk memilih lebih dari satu SPT.',wraplength=620).grid(
            row=6,column=0,columnspan=2,sticky='w',pady=(4,12))
        buttons=ttk.Frame(frame);buttons.grid(row=7,column=0,columnspan=2,sticky='e')
        ttk.Button(buttons,text='Hentikan unduhan',command=lambda:self._cancel_interaction(interaction)).pack(side='left',padx=(0,8))

        def selected_ids():
            chosen=set(tree.selection()) & set(tree.get_children())
            return [row[0] for iid,row in rows.items() if iid in chosen]

        def update_selection(event=None):
            if not self._interaction_current(interaction):return
            count=len(selected_ids());visible=len(tree.get_children())
            submit.state(['!disabled' if count else 'disabled'])
            summary.set(f'{count} SPT dipilih · {visible} dari {len(rows)} SPT ditampilkan.' if visible else
                        'Tidak ada SPT yang cocok dengan pencarian.' if rows else 'Daftar ini tidak memuat SPT yang bisa dipilih.')

        def filter_records(*args):
            if not self._interaction_current(interaction):return
            children=tree.get_children()
            if children:tree.delete(*children)
            query=search.get().strip().casefold()
            for iid,(_,values,text) in rows.items():
                if query in text:tree.insert('', 'end',iid=iid,values=values)
            update_selection()

        def confirm():
            if not self._interaction_current(interaction):
                self._close_interaction(interaction);return
            chosen=selected_ids()
            if chosen:self._reply_interaction(interaction,{'selected_ids':chosen})

        submit=ttk.Button(buttons,text='Sedot SPT terpilih',state='disabled',command=confirm)
        submit.pack(side='left')
        tree.bind('<<TreeviewSelect>>',update_selection)
        interaction['traces'].append((search,search.trace_add('write',filter_records)))
        dialog.protocol('WM_DELETE_WINDOW',lambda:self._cancel_interaction(interaction))
        dialog.bind('<Escape>',lambda event:self._cancel_interaction(interaction))
        filter_records();entry.focus_set()

    def overwrite_dialog(self,event):
        request=self._read_interaction(event,'overwrite')
        if request is None:return
        key,payload=request;files=payload.get('files');folder=payload.get('folder')
        if (not isinstance(files,list) or not files or any(not isinstance(path,str) or not path for path in files)
                or ('folder' in payload and (not isinstance(folder,str) or not folder))):
            self._interaction_error(key[0],'Daftar file yang akan diganti belum bisa ditampilkan.');return
        interaction=self._new_interaction(key,'Ganti hasil sebelumnya?')
        dialog=interaction['dialog'];dialog.minsize(540,320)
        frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True)
        frame.columnconfigure(0,weight=1)
        ttk.Label(frame,text='File berikut sudah ada. Setiap file diganti seluruhnya dengan SPT yang dipilih pada proses ini.',
                  wraplength=540).grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,12))
        tree_row=1
        if folder is not None:
            ttk.Label(frame,text='Folder hasil sebelumnya').grid(row=1,column=0,columnspan=2,sticky='w',pady=(0,4))
            ttk.Label(frame,text=folder,wraplength=540).grid(row=2,column=0,columnspan=2,sticky='w',pady=(0,12))
            tree_row=3
        frame.rowconfigure(tree_row,weight=1)
        tree=ttk.Treeview(frame,columns=('file',),show='headings',selectmode='none',height=min(8,len(files)))
        tree.heading('file',text='File yang akan diganti');tree.column('file',width=540,minwidth=300)
        tree.grid(row=tree_row,column=0,sticky='nsew')
        vertical=ttk.Scrollbar(frame,orient='vertical',command=tree.yview);vertical.grid(row=tree_row,column=1,sticky='ns')
        horizontal=ttk.Scrollbar(frame,orient='horizontal',command=tree.xview);horizontal.grid(row=tree_row+1,column=0,sticky='ew')
        tree.configure(yscrollcommand=vertical.set,xscrollcommand=horizontal.set)
        for ordinal,path in enumerate(files):tree.insert('','end',iid=f'file-{ordinal}',values=(path,))
        ttk.Label(frame,text='Pilih Jangan ganti untuk mempertahankan file yang sudah ada.',wraplength=540).grid(
            row=tree_row+2,column=0,columnspan=2,sticky='w',pady=12)
        buttons=ttk.Frame(frame);buttons.grid(row=tree_row+3,column=0,columnspan=2,sticky='e')
        decline=lambda:self._reply_interaction(interaction,{'overwrite':False})
        safe_button=ttk.Button(buttons,text='Jangan ganti',command=decline)
        safe_button.pack(side='left',padx=(0,8))
        ttk.Button(buttons,text='Ganti file tersebut',command=lambda:self._reply_interaction(interaction,{'overwrite':True})).pack(side='left')
        dialog.protocol('WM_DELETE_WINDOW',decline)
        dialog.bind('<Escape>',lambda event:decline())
        safe_button.focus_set()

    def settings(self):
        if self._settings_dialog is not None:
            self._settings_dialog.focus_set();return
        if self.controller.active:return
        dialog=tk.Toplevel(self.root);dialog.title('Pengaturan SPT Downloader')
        self._settings_dialog=dialog;self._settings_closing=False
        dialog.transient(self.root);dialog.grab_set()
        frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
        origin=tk.StringVar(dialog,value=self.preferences['login_origin'])
        identifier=tk.StringVar(dialog,value=self.preferences['identifier']);password=tk.StringVar(dialog)
        browser=tk.StringVar(dialog,value=self.preferences['browser']);hidden=tk.BooleanVar(dialog,value=self.preferences['headless'])
        self._credential_status=tk.StringVar(dialog,value='Kredensial belum dicek. Cek tidak melakukan scraping atau ekspor.')
        controls=[('Origin login',ttk.Combobox(frame,textvariable=origin,values=ALLOWED_ORIGINS,state='readonly',width=40)),
                  ('Akun / username',ttk.Entry(frame,textvariable=identifier,width=40)),
                  ('Password baru',ttk.Entry(frame,textvariable=password,show='●',width=40)),
                  ('Browser',ttk.Combobox(frame,textvariable=browser,values=('msedge','chrome'),state='readonly',width=20))]
        for row,(label,widget) in enumerate(controls):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=7)
            widget.grid(row=row,column=1,sticky='ew',pady=7)
        hidden_button=ttk.Checkbutton(frame,text='jalankan proses sedot di background',variable=hidden)
        hidden_button.grid(row=4,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Label(frame,text='Password tersimpan tidak ditampilkan. Kosongkan untuk mempertahankannya.\nSimpan perubahan dahulu, lalu Cek Kredensial. CAPTCHA/MFA tidak dilewati.',wraplength=520).grid(row=5,column=0,columnspan=2,sticky='w',pady=8)
        buttons=ttk.Frame(frame);buttons.grid(row=6,column=0,columnspan=2,sticky='w',pady=8)
        check_buttons=ttk.Frame(frame);check_buttons.grid(row=7,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Label(frame,textvariable=self._credential_status,wraplength=520).grid(row=8,column=0,columnspan=2,sticky='w',pady=8)
        traces=[]
        def selected():
            return {'browser':browser.get(),'headless':hidden.get(),'login_origin':origin.get(),'identifier':identifier.get()}
        def refresh(*args,preserve_status=False):
            active=self.controller.active
            dirty=bool(password.get()) or selected()!=self.preferences
            for widget in [w for _,w in controls]+[hidden_button,save_button,remove_button]:
                widget.state(['disabled' if active else '!disabled'])
            check_button.state(['disabled' if active or dirty or not identifier.get().strip() else '!disabled'])
            cancel_button.state(['!disabled' if active and not self._settings_closing else 'disabled'])
            if not active and not preserve_status:
                self._credential_status.set('Simpan perubahan dahulu sebelum Cek Kredensial.' if dirty else
                    'Kredensial belum dicek. Cek tidak melakukan scraping atau ekspor.')
        def close():
            if self.controller.active:
                self._settings_closing=True;self.stop();refresh(preserve_status=True);return
            for variable,token in traces:variable.trace_remove('write',token)
            password.set('');dialog.grab_release();dialog.destroy()
            self._settings_dialog=None;self._credential_status=None
            self._settings_refresh=None;self._settings_close=None;self._settings_closing=False
            self.settings_button.focus_set()
        def save():
            if self.controller.active:return
            try:
                if password.get():
                    if not identifier.get().strip():raise ValueError('Masukkan akun sebelum menyimpan password.')
                    save_login(origin.get(),identifier.get(),password.get())
                elif identifier.get()!=self.preferences['identifier']:
                    raise ValueError('Isi password baru ketika mengganti akun; atau pertahankan akun kosong untuk login manual.')
                preferences=selected()
                save_preferences(self.workspace,preferences);self.preferences=preferences
            except ValueError as error:messagebox.showerror('Pengaturan belum disimpan',str(error),parent=dialog);return
            except OSError:messagebox.showerror('Pengaturan belum disimpan','Windows menolak penyimpanan kredensial/preferensi. Periksa izin workspace.',parent=dialog);return
            password.set('');refresh()
            self._credential_status.set('Pengaturan disimpan. Tekan Cek Kredensial untuk menguji login otomatis.')
            self.status.set('Pengaturan disimpan. Password tidak ditulis ke file preferensi.')
        def remove():
            if self.controller.active:return
            if not messagebox.askyesno('Hapus kredensial?','Hapus kredensial aplikasi untuk origin terpilih dari Windows Credential Manager?',parent=dialog,default='no'):return
            try:delete_login(origin.get())
            except OSError:messagebox.showerror('Tidak dapat menghapus','Windows menolak penghapusan kredensial aplikasi.',parent=dialog);return
            password.set('');identifier.set('');self.preferences['identifier']=''
            save_preferences(self.workspace,self.preferences)
            self._credential_status.set('Kredensial origin terpilih dihapus. Isi akun/password lalu Simpan untuk mengecek lagi.')
        def check():
            if self.controller.active:return
            if password.get() or selected()!=self.preferences:
                self._credential_status.set('Simpan perubahan dahulu sebelum Cek Kredensial.');return
            try:
                self.controller.start_login_check(origin.get(),identifier.get(),browser.get(),hidden.get())
            except (ValueError,RuntimeError) as error:
                self._credential_status.set(str(error));return
            self._poll_failed = False
            self._running(True);refresh(preserve_status=True)
            self._credential_status.set('Menyiapkan pengecekan kredensial tersimpan…')
            self.status.set('Menyiapkan pengecekan kredensial tersimpan…')
            self.bar.configure(mode='indeterminate');self.bar.start(20);self.percent.set('—')
        save_button=ttk.Button(buttons,text='Simpan',command=save);save_button.pack(side='left',padx=(0,8))
        remove_button=ttk.Button(buttons,text='Hapus kredensial',command=remove);remove_button.pack(side='left',padx=(0,8))
        ttk.Button(buttons,text='Tutup',command=close).pack(side='left')
        check_button=ttk.Button(check_buttons,text='Cek Kredensial',command=check,underline=0)
        check_button.pack(side='left',padx=(0,8))
        cancel_button=ttk.Button(check_buttons,text='Batalkan Cek',command=self.stop,state='disabled')
        cancel_button.pack(side='left')
        self._settings_refresh=refresh;self._settings_close=close
        for variable in (origin,identifier,password,browser,hidden):traces.append((variable,variable.trace_add('write',refresh)))
        dialog.protocol('WM_DELETE_WINDOW',close);dialog.bind('<Escape>',lambda e:close())
        dialog.bind('<Alt-c>',lambda e:check());refresh()
        controls[1][1].focus_set()
        return dialog
