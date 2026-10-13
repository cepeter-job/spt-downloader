"""Simple native Windows interface; settings persist no password/token values."""
from datetime import date
import json
import os
from pathlib import Path
import tkinter as tk
from tkinter import ttk,messagebox
from .controller import JobController,validate_job_scope
from .credentials import ALLOWED_ORIGINS,save_login,delete_login

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
        root.title('Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang');root.minsize(540,390)
        style=ttk.Style(root)
        style.configure('Title.TLabel',font=('Segoe UI',18,'bold'))
        style.configure('TButton',padding=(12,12))
        body=ttk.Frame(root,padding=20);body.pack(fill='both',expand=True)
        body.columnconfigure(1,weight=1)
        ttk.Label(body,text='Coretax SPT downloader : kalau bisa ribet, kenapa dibikin gampang',style='Title.TLabel',wraplength=500).grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Label(body,text='Coretax → Excel · for personal use only').grid(row=1,column=0,columnspan=3,sticky='w',pady=(4,16))
        self.npwp=tk.StringVar(root);self.year=tk.StringVar(root,value=str(date.today().year))
        ttk.Label(body,text='NPWP (16 digit)').grid(row=2,column=0,sticky='w',padx=(0,12))
        self.npwp_entry=ttk.Entry(body,textvariable=self.npwp,width=30)
        self.npwp_entry.grid(row=2,column=1,columnspan=2,sticky='ew',pady=6)
        ttk.Label(body,text='Tahun pajak').grid(row=3,column=0,sticky='w',padx=(0,12))
        self.year_entry=ttk.Entry(body,textvariable=self.year,width=10)
        self.year_entry.grid(row=3,column=1,sticky='w',pady=6)
        buttons=ttk.Frame(body);buttons.grid(row=4,column=0,columnspan=3,sticky='ew',pady=12)
        self.start_button=ttk.Button(buttons,text='Mulai',command=self.start,underline=0)
        self.start_button.pack(side='left',padx=(0,8))
        self.stop_button=ttk.Button(buttons,text='Stop',command=self.stop,underline=0,state='disabled')
        self.stop_button.pack(side='left',padx=(0,8))
        self.settings_button=ttk.Button(buttons,text='Pengaturan',command=self.settings,underline=0)
        self.settings_button.pack(side='left')
        self.percent=tk.StringVar(root,value='0%')
        ttk.Label(body,textvariable=self.percent,font=('Segoe UI',14,'bold')).grid(row=5,column=2,sticky='e')
        self.bar=ttk.Progressbar(body,maximum=100,mode='determinate')
        self.bar.grid(row=6,column=0,columnspan=3,sticky='ew',pady=(6,10))
        self.status=tk.StringVar(root,value='Siap. Masukkan NPWP dan tahun pajak, lalu tekan Mulai.')
        ttk.Label(body,textvariable=self.status,wraplength=500).grid(row=7,column=0,columnspan=3,sticky='w')
        self.open_button=ttk.Button(body,text='Buka Hasil',command=self.open_result,state='disabled')
        self.open_button.grid(row=8,column=0,sticky='w',pady=(14,8))
        hints=ttk.Frame(body);hints.grid(row=9,column=0,columnspan=3,sticky='w',pady=(8,0))
        self.results_label=ttk.Label(hints,text='Hasil Sedot berada di folder Downloads Windows')
        self.results_label.pack(anchor='w')
        ttk.Label(hints,text='Setup Python/uv otomatis saat Mulai. Password hanya di Windows Credential Manager.',wraplength=510).pack(anchor='w')
        body.rowconfigure(10,weight=1)
        ttk.Label(body,text='for personal use : punto ap').grid(row=10,column=0,columnspan=3,sticky='se',pady=(12,0))
        root.update_idletasks()
        root.minsize(max(540,body.winfo_reqwidth()),max(390,body.winfo_reqheight()))
        root.protocol('WM_DELETE_WINDOW',self.request_close)
        root.bind('<Alt-m>',lambda e:self.start());root.bind('<Alt-s>',lambda e:self.stop())
        root.bind('<Alt-p>',lambda e:self.settings())
        self.npwp_entry.bind('<Return>',lambda e:self.start())
        self.year_entry.bind('<Return>',lambda e:self.start())
        self.npwp_entry.focus_set();root.after(100,self._poll)

    def _running(self,active):
        self.start_button.state(['disabled' if active else '!disabled'])
        self.stop_button.state(['!disabled' if active else 'disabled'])
        self.settings_button.state(['disabled' if active else '!disabled'])
        for entry in (self.npwp_entry,self.year_entry):entry.state(['disabled' if active else '!disabled'])

    def start(self):
        if self.controller.active or self._closing:return
        self._close_interaction()
        try:
            npwp,year=validate_job_scope(self.npwp.get(),self.year.get())
            self.controller.start(npwp,str(year),self.preferences['browser'],self.preferences['headless'])
        except (ValueError,RuntimeError) as error:
            messagebox.showerror('Tidak dapat mulai',str(error),parent=self.root);return
        self._interaction_seen.clear();self._interaction_stopped_job=None
        self._result=None;self.open_button.state(['disabled'])
        self.percent.set('0%');self.bar['value']=0;self._running(True)

    def stop(self):
        if self.controller.active:
            self._interaction_stopped_job=getattr(self.controller,'job_id',None)
            self._close_interaction()
            self.controller.stop()
            if getattr(self.controller,'operation','export')=='login_check':
                message='Menghentikan pengecekan… maksimum 15 detik; tidak ada ekspor.'
                if self._credential_status is not None:self._credential_status.set(message)
                self.status.set(message)
            else:self.status.set('Menghentikan pekerjaan… maksimum 15 detik untuk worker; checkpoint dipertahankan.')
            self.stop_button.state(['disabled'])
        else:self._close_interaction()

    def on_event(self,event):
        kind=event['type']
        if event.get('job_id') is not None and event['job_id']!=getattr(self.controller,'job_id',None):return
        if kind=='terminal':
            self._interaction_stopped_job=getattr(self.controller,'job_id',None)
            self._close_interaction()
        if kind in ('selection_required','overwrite_required') and not self._export_job_active(event.get('job_id')):
            return
        if getattr(self.controller,'operation','export')=='login_check':
            message=event.get('message','')[:500]
            self.status.set(message)
            if self._credential_status is not None:self._credential_status.set(message)
            if kind=='terminal':
                self.bar.stop();self.bar.configure(mode='determinate');self.bar['value']=0
                self.percent.set('—');self._running(False)
                if self._settings_refresh:self._settings_refresh(preserve_status=True)
                if self._settings_closing and self._settings_close:self._settings_close()
            else:
                self.bar.configure(mode='indeterminate');self.bar.start(20);self.percent.set('—')
            return
        if kind=='setup':
            self.bar.configure(mode='indeterminate');self.bar.start(20);self.percent.set('—')
        else:
            self.bar.stop();self.bar.configure(mode='determinate')
            percent=event.get('percent',0);self.bar['value']=percent;self.percent.set(f'{percent}%')
        self.status.set(event.get('message','')[:500])
        if kind=='selection_required':
            self.selection_dialog(event)
        elif kind=='overwrite_required':
            self.overwrite_dialog(event)
        elif kind=='terminal':
            self._running(False)
            self.status.set(event.get('status','ERROR')+' · '+event.get('message','')[:450])
            if event.get('output') and event.get('status') in ('COMPLETE','PARTIAL'):
                self._result=Path(event['output']);self.open_button.state(['!disabled'])
            self.npwp_entry.focus_set()

    def _poll(self):
        try:self.controller.poll()
        except Exception:
            self.controller.close()
            self.on_event({'type':'terminal','status':'ERROR','percent':0,'message':'Worker tidak dapat dipantau. Tidak ada hasil COMPLETE.'})
        if self._interaction is not None and not self._interaction_current(self._interaction):
            self._close_interaction()
        if self._closing and not self.controller.active:
            self.controller.close();self.root.destroy();return
        self.root.after(100,self._poll)

    def request_close(self):
        if self.controller.active:
            if not messagebox.askyesno('Hentikan pekerjaan?','Hentikan worker milik aplikasi dan tutup jendela? Checkpoint lokal tidak dihapus.',parent=self.root,default='no'):return
            self._closing=True;self.stop()
        else:self._close_interaction();self.controller.close();self.root.destroy()

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
