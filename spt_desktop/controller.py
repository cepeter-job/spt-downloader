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
from . import diagnostics
from .windows import ProcessJob
from .paths import downloads_folder
from .credentials import ALLOWED_ORIGINS
from .interaction import read_message, select_records, write_reply
from .profile_lifecycle import reap_profiles
from coretax_json import validate_detail_source


def validate_job_scope(npwp,year):
    # Keep this small GUI-side contract independent of openpyxl/Playwright imports.
    if not isinstance(npwp,str) or not re.fullmatch(r'[0-9]{16}',npwp):
        raise ValueError('NPWP harus tepat 16 digit ASCII, tanpa spasi atau pemisah.')
    text=str(year)
    if not re.fullmatch(r'[0-9]{4}',text) or not 1900<=int(text)<=2100:
        raise ValueError('Tahun pajak harus 4 digit, antara 1900 dan 2100.')
    return npwp,int(text)


def parse_event(line,job_id,operation='export'):
    # Stdout worker adalah kanal protokol; hanya event terbatas milik job
    # dan operasi aktif yang boleh diteruskan ke state GUI.
    if len(line)>16384:return None
    try:event=json.loads(line)
    except (ValueError,TypeError):return None
    if not isinstance(event,dict) or event.get('job_id')!=job_id:return None
    allowed={'job_id','type','stage','percent','message','processed','total','verified','scanned','status','output','request_id'}
    if set(event)-allowed:return None
    percent=event.get('percent')
    if type(percent) is not int or not 0<=percent<=100:return None
    kind=event.get('type')
    if kind not in ('progress','login_required','terminal','selection_required','overwrite_required'):return None
    interaction=kind in ('selection_required','overwrite_required')
    if interaction:
        if operation!='export' or not isinstance(event.get('request_id'),str) or not re.fullmatch(r'[0-9a-f]{32}',event['request_id']):return None
    elif 'request_id' in event:return None
    if any(not isinstance(event[k],str) or len(event[k])>500 for k in ('message','stage') if k in event):return None
    if any(type(event[k]) is not int or event[k]<0 for k in ('processed','total','verified','scanned') if k in event):return None
    if operation=='login_check':
        if percent!=0 or event.get('output') is not None:return None
        if kind=='terminal' and event.get('status') not in (
                'LOGIN_OK','LOGIN_UNVERIFIED','LOGIN_MANUAL','LOGIN_BLOCKED','LOGIN_ERROR','CANCELLED','ERROR'):return None
        return event
    if operation!='export':return None
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
        self.operation='export'
        self.job_id=None
        self.process=None
        self._job=None
        self._queue=queue.Queue(maxsize=128)
        self._cancel=threading.Event()
        self._preparing=False
        self._prepare_thread=None
        self._profile_cleanup_thread=None
        self._readers=[]
        self._terminal=None
        self._stop_at=None
        self._percent=0
        self._pending_request=None
        self._seen_requests=set()

    def _enqueue(self,event):
        try:self._queue.put_nowait(event)
        except queue.Full:
            try:self._queue.get_nowait()
            except queue.Empty:pass
            try:self._queue.put_nowait(event)
            except queue.Full:pass

    def start(self,npwp,year,browser='msedge',headless=True,*,detail_source='dom',account=''):
        if self.active:raise RuntimeError('Pekerjaan masih berjalan.')
        validate_detail_source(detail_source)
        npwp,year=validate_job_scope(npwp,year)
        if not isinstance(account,str) or (account and (not account.strip() or len(account)>256 or '\0' in account)):
            raise ValueError('Akun login tidak valid; simpan ulang Pengaturan.')
        arguments=['--npwp',npwp,'--year',str(year),'--detail-source',detail_source]
        if account:arguments.extend(['--account',account])
        return self._start_worker(arguments,browser,headless,'export')

    def start_login_check(self,origin,account,browser='msedge',headless=True):
        if self.active:raise RuntimeError('Pekerjaan masih berjalan.')
        if origin not in ALLOWED_ORIGINS:raise ValueError('Origin login tidak disetujui.')
        if not isinstance(account,str) or not account.strip() or len(account)>256 or '\0' in account:
            raise ValueError('Simpan akun sebelum mengecek kredensial.')
        return self._start_worker(['--check-login','--origin',origin,'--account',account],browser,headless,'login_check')

    def _start_worker(self,arguments,browser,headless,operation):
        if browser not in ('msedge','chrome'):raise ValueError('Browser tidak valid.')
        self.operation=operation
        self.job_id=uuid.uuid4().hex
        self.active=True
        self._preparing=True
        self._terminal=None
        self._stop_at=None
        self._percent=0
        self._readers=[]
        self._cancel.clear()
        self._profile_cleanup_thread=None
        self._pending_request=None
        self._seen_requests.clear()
        job_id=self.job_id
        diagnostics.record('operation.started', job_id=job_id, operation=operation, browser=browser, headless=headless)
        def status(message):
            self._enqueue({'job_id':job_id,'type':'setup','percent':0,'message':message})
        def prepare():
            try:
                with diagnostics.job_context(job_id):
                    reap_profiles(self.root)
                    python=ensure_runtime(self.root,status,self._cancel.is_set)
                if self._cancel.is_set():raise SetupCancelled('Persiapan dibatalkan.')
                environment=os.environ.copy()
                environment.update({'PYTHONUTF8':'1','PYTHONIOENCODING':'utf-8'})
                environment.pop('PYTHONPATH',None);environment.pop('PYTHONHOME',None)
                environment.pop('DEBUG',None);environment.pop('PWDEBUG',None)
                argv=[str(python),'-u','-m','spt_desktop.worker',*arguments,
                      '--root',str(self.root),'--job-id',job_id,'--browser',browser]
                if not headless:argv.append('--visible')
                self._job=ProcessJob()
                self.process=self._job.spawn(argv,cwd=worker_source(self.root),env=environment,
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                    text=True,encoding='utf-8',errors='replace',bufsize=1)
                process=self.process
                diagnostics.record('worker.spawned', job_id=job_id, operation=operation)
                def read_events():
                    try:
                        while True:
                            line=process.stdout.readline(16385)
                            if not line:return
                            if len(line)>16384:
                                diagnostics.record('worker.protocol_rejected', job_id=job_id, level='DEBUG')
                                while line and not line.endswith('\n'):line=process.stdout.readline(16385)
                                continue
                            event=parse_event(line,job_id,operation=operation)
                            if event:self._enqueue(event)
                            else:diagnostics.record('worker.protocol_rejected', job_id=job_id, level='DEBUG')
                    except (OSError,ValueError):pass
                def drain_errors():
                    discarded=0
                    try:
                        while True:
                            chunk=process.stderr.read(4096)
                            if not chunk:break
                            discarded+=len(chunk)
                    except (OSError,ValueError):pass
                    finally:
                        if discarded:diagnostics.record('worker.stderr_discarded', job_id=job_id, count=discarded, level='DEBUG')
                for target in (read_events,drain_errors):
                    reader=threading.Thread(target=target,daemon=True)
                    self._readers.append(reader);reader.start()
                # Stop dapat tiba selama persiapan runtime; izin mulai yang
                # terlambat tidak boleh menghidupkan kembali pekerjaan itu.
                command='stop' if self._cancel.is_set() else 'start'
                process.stdin.write(json.dumps({'command':command,'job_id':job_id})+'\n')
                process.stdin.flush()
                diagnostics.record('worker.authorized', job_id=job_id, kind=command)
            except Exception as error:
                diagnostics.record('operation.failed', job_id=job_id, phase='runtime', level='ERROR', error=error)
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
        self._pending_request=None
        if self._stop_at is None:
            diagnostics.record('worker.stop', job_id=self.job_id)
            self._stop_at=time.monotonic()+15
        process=self.process
        if process and process.poll() is None:
            try:
                process.stdin.write(json.dumps({'command':'stop','job_id':self.job_id})+'\n')
                process.stdin.flush()
            except (OSError,ValueError):pass

    def _request_active(self,job_id,kind,request_id):
        return (self.active and self.operation=='export' and job_id==self.job_id
                and not self._cancel.is_set() and self._terminal is None
                and self._pending_request==(job_id,kind,request_id)
                and self.process is not None and self.process.poll() is None)

    def read_request(self,event):
        kind={'selection_required':'selection','overwrite_required':'overwrite'}.get(event.get('type'))
        if not self._request_active(event.get('job_id'),kind,event.get('request_id')):
            raise ValueError('Consent request is not pending for the active job')
        return read_message(self.root/'jobs'/self.job_id,self.job_id,event['request_id'])

    def respond(self,kind,request_id,payload):
        job_id=self.job_id
        if not self._request_active(job_id,kind,request_id):return False
        request=self.read_request({'job_id':job_id,'type':kind+'_required','request_id':request_id})
        if not isinstance(payload,dict):raise ValueError('Invalid consent response')
        if kind=='selection':
            if set(payload)!={'selected_ids'}:raise ValueError('Invalid selection response')
            select_records(request,payload['selected_ids'])
        elif set(payload)!={'overwrite'} or type(payload['overwrite']) is not bool:
            raise ValueError('Invalid overwrite response')
        if not self._request_active(job_id,kind,request_id):return False
        write_reply(self.root/'jobs'/job_id,job_id,request_id,payload)
        if not self._request_active(job_id,kind,request_id):return False
        # Consume before signalling: repeated callbacks cannot authorize a second answer.
        self._pending_request=None
        try:
            self.process.stdin.write(json.dumps({'job_id':job_id,'command':kind,
                                                 'request_id':request_id})+'\n')
            self.process.stdin.flush()
        except (OSError,ValueError):
            self.stop()
            return False
        diagnostics.record('consent.replied', job_id=job_id, kind=kind,
                           accepted=payload.get('overwrite', True),
                           count=len(payload['selected_ids']) if kind=='selection' else 0)
        return True

    def _drain(self):
        for _ in range(128):
            try:event=self._queue.get_nowait()
            except queue.Empty:break
            if event.get('job_id')!=self.job_id:continue
            if event['type']=='terminal':
                # Tahan hasil terminal sampai exit dan pembersihan proses
                # dikonfirmasi oleh _finish, meskipun pesan sudah diterima.
                self._terminal=event
                self._pending_request=None
            else:
                if self._cancel.is_set() or self._terminal is not None:continue
                if event['type'] in ('selection_required','overwrite_required'):
                    if (not self.active or self.operation!='export' or self.process is None
                            or self.process.poll() is not None):continue
                    request_id=event['request_id']
                    if request_id in self._seen_requests:continue
                    if self._pending_request is not None:
                        self.stop()
                        continue
                    diagnostics.record('consent.requested', job_id=self.job_id, kind=event['type'].removesuffix('_required'))
                    self._seen_requests.add(request_id)
                    self._pending_request=(self.job_id,event['type'].removesuffix('_required'),request_id)
                self._percent=max(self._percent,min(99,event.get('percent',0)))
                event={**event,'percent':self._percent}
                self.on_event(event)

    def _finish(self,exit_code):
        if self._job:
            self._job.close();self._job=None
        # Anak proses dapat mewarisi stdout/stderr. Tutup pohon milik aplikasi
        # sebelum menunggu EOF melalui poll; jangan tutup pipe yang masih
        # dimiliki thread pembaca.
        if any(reader.is_alive() for reader in self._readers):return
        # The owned tree has exited. Recover any temporary login profiles left
        # by forced termination before reporting terminal state. Filesystem work
        # runs off the UI thread; unverifiable/locked profiles retry next start.
        if self._profile_cleanup_thread is None and (self.root/'cache').is_dir():
            self._profile_cleanup_thread=threading.Thread(
                target=reap_profiles,args=(self.root,),daemon=True)
            self._profile_cleanup_thread.start()
        if self._profile_cleanup_thread is not None and self._profile_cleanup_thread.is_alive():return
        self._drain()
        if self.process:
            for stream in (self.process.stdin,self.process.stdout,self.process.stderr):
                if stream:
                    try:stream.close()
                    except OSError:pass
        event=self._terminal
        # Status harus cocok dengan kontrak operasi dan exit code;
        # exit 0 sendiri belum membuktikan keberhasilan.
        expected={'COMPLETE':0,'PARTIAL':2,'BLOCKED':3,'CANCELLED':4,'ERROR':1}
        if self.operation=='login_check':
            expected={'LOGIN_OK':0,'LOGIN_UNVERIFIED':5,'LOGIN_MANUAL':6,'LOGIN_BLOCKED':3,
                      'LOGIN_ERROR':1,'ERROR':1,'CANCELLED':4}
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
        self._pending_request=None
        self._seen_requests.clear()
        self._readers=[]
        self.active=False
        diagnostics.record('worker.finished', job_id=self.job_id, operation=self.operation,
                           status=event.get('status'), exit_code=exit_code)
        self.on_event(event)

    def poll(self):
        if not self.active:return False
        self._drain()
        process=self.process
        if (process and process.poll() is None and self._stop_at is not None
                and time.monotonic()>=self._stop_at and self._job):
            diagnostics.record('worker.forced_stop', job_id=self.job_id, level='WARNING')
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
