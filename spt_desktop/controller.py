"""A thin stdlib GUI controller owns workers and distrusts stale/partial events."""
import json
import os
from pathlib import Path
import queue
import re
import subprocess
import threading
import time
import uuid
from .runtime import SetupCancelled,ensure_runtime,worker_source
from .windows import ProcessJob
from .paths import downloads_folder


def validate_job_scope(npwp,year):
    # Keep this small GUI-side contract independent of openpyxl/Playwright imports.
    if not isinstance(npwp,str) or not re.fullmatch(r'[0-9]{16}',npwp):
        raise ValueError('NPWP harus tepat 16 digit ASCII, tanpa spasi atau pemisah.')
    text=str(year)
    if not re.fullmatch(r'[0-9]{4}',text) or not 1900<=int(text)<=2100:
        raise ValueError('Tahun pajak harus 4 digit, antara 1900 dan 2100.')
    return npwp,int(text)


def parse_event(line,job_id):
    if len(line)>16384:return None
    try:event=json.loads(line)
    except (ValueError,TypeError):return None
    if not isinstance(event,dict) or event.get('job_id')!=job_id:return None
    allowed={'job_id','type','stage','percent','message','processed','total','verified','scanned','status','output'}
    if set(event)-allowed:return None
    percent=event.get('percent')
    if type(percent) is not int or not 0<=percent<=100:return None
    kind=event.get('type')
    if kind not in ('progress','login_required','terminal'):return None
    if any(not isinstance(event[k],str) or len(event[k])>500 for k in ('message','stage') if k in event):return None
    if any(type(event[k]) is not int or event[k]<0 for k in ('processed','total','verified','scanned') if k in event):return None
    if kind=='terminal':
        status=event.get('status')
        if status not in ('COMPLETE','PARTIAL','CANCELLED','BLOCKED','ERROR'):return None
        if (status=='COMPLETE')!=(percent==100):return None
        output=event.get('output')
        if output is not None and (not isinstance(output,str) or len(output)>4096):return None
        if status=='COMPLETE' and not output:return None
    elif percent==100:return None
    return event


class JobController:
    def __init__(self,root,on_event):
        self.root=Path(root)
        self.on_event=on_event
        self.active=False
        self.job_id=None
        self.process=None
        self._job=None
        self._queue=queue.Queue(maxsize=128)
        self._cancel=threading.Event()
        self._preparing=False
        self._prepare_thread=None
        self._readers=[]
        self._terminal=None
        self._stop_at=None
        self._percent=0

    def _enqueue(self,event):
        try:self._queue.put_nowait(event)
        except queue.Full:
            try:self._queue.get_nowait()
            except queue.Empty:pass
            try:self._queue.put_nowait(event)
            except queue.Full:pass

    def start(self,npwp,year,browser='msedge',headless=True):
        if self.active:raise RuntimeError('Pekerjaan masih berjalan.')
        npwp,year=validate_job_scope(npwp,year)
        if browser not in ('msedge','chrome'):raise ValueError('Browser tidak valid.')
        self.job_id=uuid.uuid4().hex
        self.active=True
        self._preparing=True
        self._terminal=None
        self._stop_at=None
        self._percent=0
        self._readers=[]
        self._cancel.clear()
        job_id=self.job_id
        def status(message):
            self._enqueue({'job_id':job_id,'type':'setup','percent':0,'message':message})
        def prepare():
            try:
                python=ensure_runtime(self.root,status,self._cancel.is_set)
                if self._cancel.is_set():raise SetupCancelled('Persiapan dibatalkan.')
                environment=os.environ.copy()
                environment.update({'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
                environment.pop('PYTHONPATH',None);environment.pop('PYTHONHOME',None)
                environment.pop('DEBUG',None);environment.pop('PWDEBUG',None)
                argv=[str(python),'-u','-m','spt_desktop.worker','--npwp',npwp,'--year',str(year),
                      '--root',str(self.root),'--job-id',job_id,'--browser',browser]
                if not headless:argv.append('--visible')
                self._job=ProcessJob()
                self.process=self._job.spawn(argv,cwd=worker_source(self.root),env=environment,
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,encoding='utf-8',errors='replace',bufsize=1)
                process=self.process
                def read_events():
                    try:
                        while True:
                            line=process.stdout.readline(16385)
                            if not line:return
                            if len(line)>16384:
                                while line and not line.endswith('\n'):line=process.stdout.readline(16385)
                                continue
                            event=parse_event(line,job_id)
                            if event:self._enqueue(event)
                    except (OSError,ValueError):pass
                def drain_errors():
                    try:
                        while process.stderr.read(4096):pass
                    except (OSError,ValueError):pass
                for target in (read_events,drain_errors):
                    reader=threading.Thread(target=target,daemon=True)
                    self._readers.append(reader);reader.start()
                command='stop' if self._cancel.is_set() else 'start'
                process.stdin.write(json.dumps({'command':command,'job_id':job_id})+'\n')
                process.stdin.flush()
            except Exception:
                cancelled=self._cancel.is_set()
                self._enqueue({'job_id':job_id,'type':'terminal','status':'CANCELLED' if cancelled else 'ERROR',
                    'percent':0,'output':None,'message':'Persiapan dibatalkan.' if cancelled else 'Persiapan gagal. Periksa koneksi/proxy, izin workspace, dan kelengkapan resource aplikasi; coba lagi.'})
            finally:self._preparing=False
        self._prepare_thread=threading.Thread(target=prepare,daemon=True)
        self._prepare_thread.start()
        return job_id

    def stop(self):
        if not self.active:return
        self._cancel.set()
        if self._stop_at is None:self._stop_at=time.monotonic()+15
        process=self.process
        if process and process.poll() is None:
            try:
                process.stdin.write(json.dumps({'command':'stop','job_id':self.job_id})+'\n')
                process.stdin.flush()
            except (OSError,ValueError):pass

    def _drain(self):
        for _ in range(128):
            try:event=self._queue.get_nowait()
            except queue.Empty:break
            if event.get('job_id')!=self.job_id:continue
            if event['type']=='terminal':self._terminal=event
            else:
                self._percent=max(self._percent,min(99,event.get('percent',0)))
                event={**event,'percent':self._percent}
                self.on_event(event)

    def _finish(self,exit_code):
        for reader in self._readers:reader.join(timeout=0.05)
        self._drain()
        if self._job:
            self._job.close();self._job=None
        if self.process:
            for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                if stream:
                    try:stream.close()
                    except OSError:pass
        event=self._terminal
        expected={'COMPLETE':0,'PARTIAL':2,'BLOCKED':3,'CANCELLED':4,'ERROR':1}
        if self._cancel.is_set():
            event={'job_id':self.job_id,'type':'terminal','status':'CANCELLED','percent':self._percent,
                   'output':None,'message':'Dihentikan. Checkpoint lokal dipertahankan.'}
        elif event is None or (self.process is not None and expected.get(event['status'])!=exit_code):
            event={'job_id':self.job_id,'type':'terminal','status':'ERROR','percent':self._percent,
                   'output':None,'message':'Worker berakhir tanpa hasil terverifikasi; checkpoint lokal dipertahankan.'}
        if event.get('output'):
            try:
                output=Path(event['output']).resolve()
                valid=(output.is_dir() and output.is_relative_to(downloads_folder().resolve())
                       and (output/'resume.xlsx').is_file())
            except OSError:valid=False
            if not valid:
                event={**event,'status':'ERROR','percent':min(99,self._percent),'output':None,
                       'message':'Folder hasil tidak dapat diverifikasi; tidak ada hasil COMPLETE.'}
        self.process=None
        self._terminal=None
        self._readers=[]
        self.active=False
        self.on_event(event)

    def poll(self):
        if not self.active:return False
        self._drain()
        process=self.process
        if (process and process.poll() is None and self._stop_at is not None
                and time.monotonic()>=self._stop_at and self._job):
            self._job.close();self._job=None
        if not self._preparing:
            if process is not None and process.poll() is not None:self._finish(process.returncode)
            elif process is None and self._terminal is not None:self._finish(None)
        return self.active

    def close(self):
        self.stop()
        if self._job:self._job.close();self._job=None
        if self._prepare_thread and self._prepare_thread.is_alive():self._prepare_thread.join(timeout=1)
        if self._job:self._job.close();self._job=None
