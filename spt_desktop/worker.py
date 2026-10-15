"""Worker scraper milik aplikasi; stdout hanya memuat protokol event terbatas."""
import argparse
import contextlib
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import threading
import coretax
from coretax_exporter import validate_scope
from coretax_json import validate_detail_source
from coretax_browser import CaptureCancelled,collect_inventory,collect_details
from .auth import AuthBlocked,authenticate_owned,check_saved_credentials
from .credentials import ALLOWED_ORIGINS
from .events import Progress
from .interaction import Requests, select_records
from .output import existing_outputs, publish_workbooks
from .paths import downloads_folder


def playwright_factory():
    from playwright.sync_api import sync_playwright
    return sync_playwright()


def run_job(npwp,year,root,job_id,browser,headless,emit,cancelled,*,requests=None,detail_source='dom'):
    progress=Progress(job_id,emit)
    run=None
    folder=None
    def check_cancel():
        if cancelled():raise CaptureCancelled('Stop requested')
    def auth_event(kind,message):
        emit({'job_id':job_id,'type':kind,'stage':'authentication',
              'percent':progress.percent,'message':message})
    try:
        validate_detail_source(detail_source)
        npwp,year=validate_scope(npwp,year)
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',job_id):raise ValueError('Invalid job identifier')
        check_cancel()
        root=Path(root)
        folder=root/'jobs'/job_id
        folder.mkdir(parents=True,exist_ok=False)
        with playwright_factory() as playwright:
            context,page=authenticate_owned(playwright,root/'profile',browser,headless,auth_event,check_cancel)
            try:
                progress.authenticated()
                run=collect_inventory(page,npwp,year,'period',folder,
                    on_progress=lambda item:progress.inventory(item['completed'],item['total'],item['scanned']),
                    check_cancel=check_cancel)
                check_cancel()
                if requests is None:
                    raise RuntimeError('A private selection channel is required before detail capture')
                if run['records']:
                    inventory = {'records': [{'record_id': record['record_id'], 'meta': record['meta']}
                                              for record in run['records']]}
                    reply = requests.request('selection', inventory, progress.percent)
                    check_cancel()
                    if not isinstance(reply, dict) or set(reply) != {'selected_ids'}:
                        raise ValueError('Invalid selection response')
                    run = select_records(run, reply['selected_ids'])
                run['started_at']=datetime.now().astimezone().isoformat()
                verified=0
                def details_progress(data,ordinal):
                    nonlocal verified
                    # collect_details melapor sekali per urutan, termasuk checkpoint.
                    # Baca hanya detail terbaru agar total biaya progress tetap linear.
                    verified+=bool(data['records'][ordinal-1].get('capture_complete'))
                    progress.details(ordinal,len(data['records']),verified)
                if run['records']:
                    progress.details(0,len(run['records']),0)
                run=collect_details(page,run,folder,on_progress=details_progress,check_cancel=check_cancel,
                                    detail_source=detail_source)
                if not run['records']:progress.details(0,0,0)
            finally:
                context.close()
        check_cancel()
        coretax.save_output(run,folder)
        progress.exported()
        check_cancel()
        progress.publishing()
        downloads = downloads_folder()
        previous = existing_outputs(run, downloads)
        overwrite = False
        # The refreshed index is automatic; selected SPT/PDF bytes still need consent.
        overwrite_files = ([] if previous is None else
                           [name for name in previous['files'] if name != 'resume.xlsx'])
        if overwrite_files:
            reply = requests.request('overwrite', {'files': overwrite_files,
                                                   'folder': previous['target']}, progress.percent)
            check_cancel()
            if (not isinstance(reply, dict) or set(reply) != {'overwrite'}
                    or type(reply['overwrite']) is not bool):
                raise ValueError('Invalid overwrite response')
            if not reply['overwrite']:
                raise CaptureCancelled('Existing files were kept by user choice')
            overwrite = True
        final=publish_workbooks(run,folder,downloads,job_id,check_cancel=check_cancel,
                                overwrite=overwrite,expected_outputs=previous)
        progress.finished(bool(run['complete']),final)
        return 0 if run['complete'] else 2
    except CaptureCancelled:
        if run is not None and folder is not None:
            run['complete']=False
            run.setdefault('errors',[]).append({'object':'Cancellation','message':'User stopped the job; capture is PARTIAL'})
            (folder/'run.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding='utf-8')
        progress.finished(False,None,status='CANCELLED',message='Dihentikan. Checkpoint lokal tetap tersedia; tidak ada hasil COMPLETE.')
        return 4
    except AuthBlocked as error:
        progress.finished(False,None,status='BLOCKED',message=str(error))
        return 3
    except Exception:
        # Jangan kirim trace browser/kredensial atau data pajak ke log GUI.
        progress.finished(False,None,status='ERROR',message='Ekspor terhenti. Periksa koneksi, izin Downloads, dan checkpoint lokal; tidak ada hasil COMPLETE.')
        return 1


def run_login_check(root,job_id,browser,headless,origin,account,emit,cancelled):
    def check_cancel():
        if cancelled():raise CaptureCancelled('Stop requested')
    try:
        check_cancel()
        emit({'job_id':job_id,'type':'progress','stage':'login_check','percent':0,
              'message':'Mengecek kredensial tersimpan dengan sesi baru…'})
        with playwright_factory() as playwright:
            status,message=check_saved_credentials(playwright,root,origin,account,browser,headless,check_cancel)
        check_cancel()
    except CaptureCancelled:
        status,message='CANCELLED','Pengecekan kredensial dibatalkan; tidak ada ekspor.'
    except Exception:
        status,message='LOGIN_ERROR','Pengecekan gagal; periksa koneksi intranet, browser, dan izin workspace.'
    emit({'job_id':job_id,'type':'terminal','stage':'login_check','status':status,
          'percent':0,'output':None,'message':message})
    return {'LOGIN_OK':0,'LOGIN_UNVERIFIED':5,'LOGIN_MANUAL':6,'LOGIN_BLOCKED':3,
            'LOGIN_ERROR':1,'CANCELLED':4}[status]


def main(argv=None):
    parser=argparse.ArgumentParser(description='Owned read-only Coretax GUI worker')
    parser.add_argument('--npwp')
    parser.add_argument('--year')
    parser.add_argument('--check-login',action='store_true')
    parser.add_argument('--origin',choices=ALLOWED_ORIGINS)
    parser.add_argument('--account')
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--job-id',required=True)
    parser.add_argument('--browser',choices=['msedge','chrome'],default='msedge')
    parser.add_argument('--visible',action='store_true')
    parser.add_argument('--detail-source',choices=['dom','json-first'],default='dom')
    args=parser.parse_args(argv)
    if args.check_login:
        if not args.origin or not args.account or len(args.account)>256 or not args.account.strip():return 1
    else:
        try:validate_scope(args.npwp,args.year)
        except ValueError:return 1
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.job_id):return 1
    started,cancelled=threading.Event(),threading.Event()
    output=sys.stdout
    def emit(item):
        output.write(json.dumps(item,ensure_ascii=True)+'\n');output.flush()
    def check_cancel():
        if cancelled.is_set():raise CaptureCancelled('Stop requested')
    requests = None if args.check_login else Requests(
        args.root/'jobs'/args.job_id, args.job_id, emit, check_cancel)
    def listen():
        while True:
            line=sys.stdin.readline(8193)
            if not line:
                cancelled.set();return
            if len(line)>8192:
                cancelled.set();return
            try:item=json.loads(line)
            except ValueError:continue
            if not isinstance(item,dict) or item.get('job_id')!=args.job_id:continue
            if item.get('command')=='start':started.set()
            elif item.get('command')=='stop':cancelled.set();started.set()
            elif (requests is not None and not cancelled.is_set()
                  and set(item)=={'job_id','command','request_id'}
                  and item['command'] in ('selection','overwrite')):
                requests.respond(item['command'],item['request_id'])
    threading.Thread(target=listen,daemon=True).start()
    if not started.wait(30):
        Progress(args.job_id,emit).finished(False,None,status='BLOCKED',message='Worker tidak menerima izin mulai dari GUI.')
        return 3
    with contextlib.redirect_stdout(sys.stderr):
        if args.check_login:
            return run_login_check(args.root,args.job_id,args.browser,not args.visible,args.origin,args.account,emit,cancelled.is_set)
        return run_job(args.npwp,args.year,args.root,args.job_id,args.browser,not args.visible,
                       emit,cancelled.is_set,requests=requests,detail_source=args.detail_source)


if __name__=='__main__':
    raise SystemExit(main())
