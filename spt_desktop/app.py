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
        root.title('SPT Downloader');root.minsize(540,390)
        style=ttk.Style(root)
        style.configure('Title.TLabel',font=('Segoe UI',18,'bold'))
        style.configure('TButton',padding=(12,12))
        body=ttk.Frame(root,padding=20);body.pack(fill='both',expand=True)
        body.columnconfigure(1,weight=1)
        ttk.Label(body,text='SPT Downloader',style='Title.TLabel').grid(row=0,column=0,columnspan=3,sticky='w')
        ttk.Label(body,text='Coretax → Excel · read-only · data perpajakan rahasia').grid(row=1,column=0,columnspan=3,sticky='w',pady=(4,16))
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
        ttk.Label(body,text='Setup Python/uv otomatis saat Mulai. Password hanya di Windows Credential Manager.\nHasil: Downloads → NPWP - NAMA WP → TAHUN PAJAK → WAKTU EKSPOR.',wraplength=510).grid(row=9,column=0,columnspan=3,sticky='w',pady=(8,0))
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
        if self.controller.active:return
        try:
            npwp,year=validate_job_scope(self.npwp.get(),self.year.get())
            self.controller.start(npwp,str(year),self.preferences['browser'],self.preferences['headless'])
        except (ValueError,RuntimeError) as error:
            messagebox.showerror('Tidak dapat mulai',str(error),parent=self.root);return
        self._result=None;self.open_button.state(['disabled'])
        self.percent.set('0%');self.bar['value']=0;self._running(True)

    def stop(self):
        if self.controller.active:
            self.controller.stop()
            self.status.set('Menghentikan pekerjaan… maksimum 15 detik untuk worker; checkpoint dipertahankan.')
            self.stop_button.state(['disabled'])

    def on_event(self,event):
        kind=event['type']
        if kind=='setup':
            self.bar.configure(mode='indeterminate');self.bar.start(20);self.percent.set('—')
        else:
            self.bar.stop();self.bar.configure(mode='determinate')
            percent=event.get('percent',0);self.bar['value']=percent;self.percent.set(f'{percent}%')
        self.status.set(event.get('message','')[:500])
        if kind=='terminal':
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
        if self._closing and not self.controller.active:
            self.controller.close();self.root.destroy();return
        self.root.after(100,self._poll)

    def request_close(self):
        if self.controller.active:
            if not messagebox.askyesno('Hentikan pekerjaan?','Hentikan worker milik aplikasi dan tutup jendela? Checkpoint lokal tidak dihapus.',parent=self.root,default='no'):return
            self._closing=True;self.stop()
        else:self.controller.close();self.root.destroy()

    def open_result(self):
        if self._result and self._result.is_dir():os.startfile(str(self._result))
        else:messagebox.showerror('Hasil tidak ditemukan','Folder hasil tidak lagi tersedia.',parent=self.root)

    def settings(self):
        if self.controller.active:return
        dialog=tk.Toplevel(self.root);dialog.title('Pengaturan SPT Downloader')
        dialog.transient(self.root);dialog.grab_set()
        frame=ttk.Frame(dialog,padding=20);frame.pack(fill='both',expand=True);frame.columnconfigure(1,weight=1)
        origin=tk.StringVar(dialog,value=self.preferences['login_origin'])
        identifier=tk.StringVar(dialog,value=self.preferences['identifier']);password=tk.StringVar(dialog)
        browser=tk.StringVar(dialog,value=self.preferences['browser']);hidden=tk.BooleanVar(dialog,value=self.preferences['headless'])
        controls=[('Origin login',ttk.Combobox(frame,textvariable=origin,values=ALLOWED_ORIGINS,state='readonly',width=40)),
                  ('Akun / username',ttk.Entry(frame,textvariable=identifier,width=40)),
                  ('Password baru',ttk.Entry(frame,textvariable=password,show='●',width=40)),
                  ('Browser',ttk.Combobox(frame,textvariable=browser,values=('msedge','chrome'),state='readonly',width=20))]
        for row,(label,widget) in enumerate(controls):
            ttk.Label(frame,text=label).grid(row=row,column=0,sticky='w',padx=(0,12),pady=7)
            widget.grid(row=row,column=1,sticky='ew',pady=7)
        ttk.Checkbutton(frame,text='Jalankan headless bila sesi memungkinkan',variable=hidden).grid(row=4,column=0,columnspan=2,sticky='w',pady=8)
        ttk.Label(frame,text='Password tersimpan tidak ditampilkan. Kosongkan untuk mempertahankannya.\nCAPTCHA/MFA tetap diselesaikan langsung di browser.',wraplength=520).grid(row=5,column=0,columnspan=2,sticky='w',pady=8)
        def close():
            password.set('');dialog.grab_release();dialog.destroy();self.settings_button.focus_set()
        def save():
            try:
                if password.get():
                    if not identifier.get().strip():raise ValueError('Masukkan akun sebelum menyimpan password.')
                    save_login(origin.get(),identifier.get(),password.get())
                elif identifier.get()!=self.preferences['identifier']:
                    raise ValueError('Isi password baru ketika mengganti akun; atau pertahankan akun kosong untuk login manual.')
                preferences={'browser':browser.get(),'headless':hidden.get(),'login_origin':origin.get(),'identifier':identifier.get()}
                save_preferences(self.workspace,preferences);self.preferences=preferences
            except ValueError as error:messagebox.showerror('Pengaturan belum disimpan',str(error),parent=dialog);return
            except OSError:messagebox.showerror('Pengaturan belum disimpan','Windows menolak penyimpanan kredensial/preferensi. Periksa izin workspace.',parent=dialog);return
            close();self.status.set('Pengaturan disimpan. Password tidak ditulis ke file preferensi.')
        def remove():
            if not messagebox.askyesno('Hapus kredensial?','Hapus kredensial aplikasi untuk origin terpilih dari Windows Credential Manager?',parent=dialog,default='no'):return
            try:delete_login(origin.get())
            except OSError:messagebox.showerror('Tidak dapat menghapus','Windows menolak penghapusan kredensial aplikasi.',parent=dialog);return
            password.set('');identifier.set('');self.preferences['identifier']=''
            save_preferences(self.workspace,self.preferences)
        buttons=ttk.Frame(frame);buttons.grid(row=6,column=0,columnspan=2,sticky='w',pady=12)
        ttk.Button(buttons,text='Simpan',command=save).pack(side='left',padx=(0,8))
        ttk.Button(buttons,text='Hapus kredensial',command=remove).pack(side='left',padx=(0,8))
        ttk.Button(buttons,text='Batal',command=close).pack(side='left')
        dialog.protocol('WM_DELETE_WINDOW',close);dialog.bind('<Escape>',lambda e:close())
        controls[1][1].focus_set()
