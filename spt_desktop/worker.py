"""Console-hidden owned scraper worker; stdout is a bounded event protocol."""
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
from coretax_browser import CaptureCancelled,collect_inventory,collect_details
from .auth import AuthBlocked,authenticate_owned
from .events import Progress
from .output import publish_workbooks
from .paths import downloads_folder


def playwright_factory():
    from playwright.sync_api import sync_playwright
    return sync_playwright()


def run_job(npwp,year,root,job_id,browser,headless,emit,cancelled):
    progress=Progress(job_id,emit)
    run=None
    folder=None
    def check_cancel():
        if cancelled():raise CaptureCancelled('Stop requested')
    def auth_event(kind,message):
        emit({'job_id':job_id,'type':kind,'stage':'authentication',
              'percent':progress.percent,'message':message})
    try:
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
                run['started_at']=datetime.now().astimezone().isoformat()
                def details_progress(data,ordinal):
                    verified=sum(bool(r.get('capture_complete')) for r in data['records'][:ordinal])
                    progress.details(ordinal,len(data['records']),verified)
                run=collect_details(page,run,folder,on_progress=details_progress,check_cancel=check_cancel)
                if not run['records']:progress.details(0,0,0)
            finally:
                context.close()
        check_cancel()
        coretax.save_output(run,folder)
        progress.exported()
        check_cancel()
        progress.publishing()
        final=publish_workbooks(run,folder,downloads_folder(),job_id,check_cancel=check_cancel)
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
        # Do not forward browser/credential exception traces or captured tax data to GUI logs.
        progress.finished(False,None,status='ERROR',message='Ekspor terhenti. Periksa koneksi, izin Downloads, dan checkpoint lokal; tidak ada hasil COMPLETE.')
        return 1


def main(argv=None):
    parser=argparse.ArgumentParser(description='Owned read-only Coretax GUI worker')
    parser.add_argument('--npwp',required=True)
    parser.add_argument('--year',required=True)
    parser.add_argument('--root',required=True,type=Path)
    parser.add_argument('--job-id',required=True)
    parser.add_argument('--browser',choices=['msedge','chrome'],default='msedge')
    parser.add_argument('--visible',action='store_true')
    args=parser.parse_args(argv)
    try:validate_scope(args.npwp,args.year)
    except ValueError:
        return 1
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',args.job_id):return 1
    started,cancelled=threading.Event(),threading.Event()
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
    threading.Thread(target=listen,daemon=True).start()
    output=sys.stdout
    def emit(item):
        output.write(json.dumps(item,ensure_ascii=True)+'\n');output.flush()
    if not started.wait(30):
        Progress(args.job_id,emit).finished(False,None,status='BLOCKED',message='Worker tidak menerima izin mulai dari GUI.')
        return 3
    with contextlib.redirect_stdout(sys.stderr):
        return run_job(args.npwp,args.year,args.root,args.job_id,args.browser,not args.visible,emit,cancelled.is_set)


if __name__=='__main__':
    raise SystemExit(main())
