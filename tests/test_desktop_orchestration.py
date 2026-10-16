"""The orchestration test mocks only browser capture and uses real Excel publication."""
import importlib
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import pytest
from support_runs import fixture_run


def worker():
    assert importlib.util.find_spec('spt_desktop.worker'), 'Background worker is missing'
    return importlib.import_module('spt_desktop.worker')


from support_selected_capture import (
    synthetic_browser
)

def test_complete_event_is_after_browser_cleanup_and_verified_downloads(tmp_path,monkeypatch):
    module=worker()
    state={}
    synthetic_browser(module,monkeypatch,state)
    run=fixture_run()
    run['inventory_complete']=True
    monkeypatch.setattr(module,'collect_inventory',lambda *a,**k:run)
    def details(page,data,folder,**kwargs):
        data['complete']=True
        kwargs['on_progress'](data,len(data['records']))
        return data
    monkeypatch.setattr(module,'collect_details',details)
    downloads=tmp_path/'Redirected Downloads'
    monkeypatch.setattr(module,'downloads_folder',lambda:downloads)
    messages=[]
    def emit(event):
        if event['type']=='terminal':assert state['browser_closed'] and state['driver_closed']
        messages.append(event)
    def choose(kind, payload, percent):
        assert kind == 'selection'
        return {'selected_ids': [record['record_id'] for record in payload['records']]}
    result=module.run_job('0000000000000001','2025',tmp_path/'workspace','synthetic-job','msedge',True,
                          emit,lambda:False,requests=SimpleNamespace(request=choose))
    assert result==0
    assert messages[-1]['status']=='COMPLETE' and messages[-1]['percent']==100
    assert (Path(messages[-1]['output'])/'resume.xlsx').is_file()
    assert not list(downloads.rglob('*.json'))


def test_stop_during_inventory_closes_browser_and_never_publishes(tmp_path,monkeypatch):
    module=worker()
    state={}
    synthetic_browser(module,monkeypatch,state)
    def inventory(*args,**kwargs):raise module.CaptureCancelled('synthetic stop')
    monkeypatch.setattr(module,'collect_inventory',inventory)
    downloads=tmp_path/'Downloads'
    monkeypatch.setattr(module,'downloads_folder',lambda:downloads)
    messages=[]
    result=module.run_job('0000000000000001','2025',tmp_path/'workspace','synthetic-job','msedge',True,messages.append,lambda:False)
    assert result==4
    assert state['browser_closed'] and state['driver_closed']
    assert messages[-1]['status']=='CANCELLED' and messages[-1]['percent']<100
    assert not downloads.exists()


def test_credential_or_browser_exception_cannot_leak_secret_into_events(tmp_path,monkeypatch):
    module=worker()
    class Manager:
        def __enter__(self):raise RuntimeError('SYNTHETIC_SECRET_DO_NOT_LOG')
        def __exit__(self,*args):pass
    monkeypatch.setattr(module,'playwright_factory',Manager)
    messages=[]
    result=module.run_job('0000000000000001','2025',tmp_path/'workspace','synthetic-job','msedge',True,messages.append,lambda:False)
    assert result==1
    assert messages[-1]['status']=='ERROR'
    assert 'SYNTHETIC_SECRET_DO_NOT_LOG' not in str(messages)



@pytest.mark.parametrize('account', ['', 'SYNTHETIC_ACCOUNT'])
def test_worker_main_json_stays_on_original_stdout_when_diagnostics_are_redirected(tmp_path,account):
    import json,subprocess,sys
    source=Path(__file__).resolve().parents[1]
    script="""import io,json,sys
from spt_desktop import worker
job_id='synthetic-stream'
sys.stdin=io.StringIO(json.dumps({'job_id':job_id,'command':'start'})+'\\n')
def synthetic_run(npwp,year,root,job_id,browser,headless,emit,cancelled,*,requests,account):
    assert requests is not None
    assert account == EXPECTED_ACCOUNT
    print('SYNTHETIC_DIAGNOSTIC_ONLY')
    emit({'job_id':job_id,'type':'progress','percent':20,'message':'Synthetic progress'})
    emit({'job_id':job_id,'type':'terminal','status':'BLOCKED','percent':20,'output':None})
    return 3
worker.run_job=synthetic_run
arguments=['--npwp','0000000000000001','--year','2025','--root','fixture-unused','--job-id',job_id]
if EXPECTED_ACCOUNT:arguments.extend(['--account',EXPECTED_ACCOUNT])
raise SystemExit(worker.main(arguments))
"""
    script=script.replace('EXPECTED_ACCOUNT',repr(account))
    result=subprocess.run([sys.executable,'-c',script],cwd=source,capture_output=True,text=True,timeout=10)
    assert result.returncode==3
    messages=[json.loads(line) for line in result.stdout.splitlines()]
    assert [m['type'] for m in messages]==['progress','terminal']
    assert 'SYNTHETIC_DIAGNOSTIC_ONLY' in result.stderr
    assert 'SYNTHETIC_DIAGNOSTIC_ONLY' not in result.stdout
