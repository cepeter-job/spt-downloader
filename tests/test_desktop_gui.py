"""GUI tests never start a live scraper or read saved credentials."""
import importlib
import importlib.util
import json
from pathlib import Path
import threading
import tkinter as tk
import pytest


def module(name):
    assert importlib.util.find_spec('spt_desktop.'+name), f'{name} is not implemented'
    return importlib.import_module('spt_desktop.'+name)


@pytest.mark.parametrize('npwp,year',[('0000000000000001','2025'),('0000000000000002','1900')])
def test_gui_accepts_exact_scope_without_normalizing(npwp,year):
    assert module('controller').validate_job_scope(npwp,year)==(npwp,int(year))


@pytest.mark.parametrize('npwp,year',[(' 0000000000000001','2025'),('0000000000000001','2025 '),
    ('0000000000000001','1800'),('0000000000000001','２０２５'),('00.000.000.0-001.000','2025')])
def test_gui_rejects_malformed_literals(npwp,year):
    with pytest.raises(ValueError):module('controller').validate_job_scope(npwp,year)


def test_stale_malformed_and_false_success_events_are_rejected():
    parse=module('controller').parse_event
    assert parse('not JSON','job') is None
    assert parse(json.dumps({'job_id':'old-job','type':'progress','percent':30}),'job') is None
    assert parse(json.dumps({'job_id':'job','type':'terminal','status':'PARTIAL','percent':100}),'job') is None
    assert parse(json.dumps({'job_id':'job','type':'progress','percent':True}),'job') is None
    event={'job_id':'job','type':'progress','stage':'details','percent':40,'message':'Synthetic progress'}
    assert parse(json.dumps(event),'job')==event


def test_simple_window_controls_and_partial_progress_are_real_tkinter(tmp_path):
    app=module('app')
    root=tk.Tk();root.withdraw()
    try:
        class SyntheticController:
            active=False
            operation='export'
            job_id=None
            def start(self,*args):
                self.active=True;self.job_id='synthetic-view-job';return self.job_id
            def poll(self):return self.active
            def close(self):self.active=False
        ctl=SyntheticController()
        window=app.App(root,tmp_path,controller=ctl)
        root.update_idletasks()
        assert window.npwp.get()==''
        assert not window.start_button.instate(['disabled'])
        assert window.stop_button.instate(['disabled'])
        assert window.open_button.instate(['disabled'])
        window.npwp.set('0000000000000001');window.year.set('2025');window.start()
        window.on_event({'job_id':ctl.job_id,'type':'progress','stage':'details','percent':42,'message':'Synthetic progress'})
        root.update_idletasks()
        assert window.percent.get()=='42%'
        assert int(window.bar['value'])==42
        ctl.active=False
        window.on_event({'job_id':ctl.job_id,'type':'terminal','status':'PARTIAL','percent':99,'output':None,'message':'Synthetic PARTIAL'})
        root.update_idletasks()
        assert window.percent.get()=='99%'
        assert window.open_button.instate(['disabled'])
    finally:
        root.destroy()
        del window
        import gc
        gc.collect()  # Tk variable destruction belongs to this UI test thread.


def test_settings_preferences_never_accept_password_fields(tmp_path):
    app=module('app')
    app.save_preferences(tmp_path,{'browser':'msedge','headless':True,'login_origin':'https://satu.intranet.pajak.go.id','identifier':'SYNTHETIC_ACCOUNT','password':'SYNTHETIC_SECRET','token':'SYNTHETIC_TOKEN'})
    text=(tmp_path/'preferences.json').read_text()
    assert 'SYNTHETIC_SECRET' not in text and 'SYNTHETIC_TOKEN' not in text
    assert 'password' not in text and 'token' not in text
    assert app.load_preferences(tmp_path)['browser']=='msedge'


@pytest.fixture
def controlled_worker(tmp_path,monkeypatch):
    import io,time,sys
    controller=module('controller')
    state={}
    monkeypatch.setenv('DEBUG','pw:api')
    monkeypatch.setenv('PWDEBUG','console')
    downloads=tmp_path/'Downloads'
    final=downloads/'SYNTHETIC_RESULT';final.mkdir(parents=True)
    (final/'resume.xlsx').write_bytes(b'SYNTHETIC TRANSPORT FIXTURE ONLY, NOT AN EXCEL EXPORT')
    monkeypatch.setattr(controller,'downloads_folder',lambda:downloads)
    monkeypatch.setattr(controller,'ensure_runtime',lambda *a:Path(sys.executable))
    monkeypatch.setattr(controller,'worker_source',lambda root:tmp_path)
    class Child:
        returncode=None
        stdin=io.StringIO()
        stderr=io.StringIO('SYNTHETIC_SECRET_STDERR_MUST_NOT_LEAK')
        def poll(self):return self.returncode
    child=Child()
    class Job:
        def spawn(self,argv,**kwargs):
            state['argv']=argv
            state['env_keys']=set(kwargs['env'])
            job_id=argv[argv.index('--job-id')+1]
            event={'job_id':job_id,'type':'terminal','stage':'finished','status':'COMPLETE',
                   'percent':100,'output':str(final),'message':'Synthetic transport complete'}
            child.stdout=io.StringIO(json.dumps(event)+'\n')
            return child
        def close(self):
            state['closed']=True
            if child.returncode is None:child.returncode=1
    monkeypatch.setattr(controller,'ProcessJob',Job)
    events=[]
    main_thread=threading.get_ident()
    def on_event(event):
        assert threading.get_ident()==main_thread
        if event['type']=='terminal':assert state['closed']
        events.append(event)
    ctl=controller.JobController(tmp_path/'workspace',on_event)
    ctl.start('0000000000000001','2025')
    deadline=time.monotonic()+2
    while ctl.process is None and time.monotonic()<deadline:
        ctl.poll();time.sleep(0.001)
    assert ctl.process is child
    yield ctl,child,state,events
    ctl.close()


def test_complete_is_held_until_exit_and_owned_cleanup(controlled_worker):
    import time
    ctl,child,state,events=controlled_worker
    with pytest.raises(RuntimeError,match='berjalan'):ctl.start('0000000000000002','2025')
    for _ in range(5):ctl.poll();time.sleep(0.001)
    assert not any(e['type']=='terminal' for e in events)
    assert ctl.active
    assert json.loads(child.stdin.getvalue().splitlines()[0])['command']=='start'
    child.returncode=0
    finish_controller(ctl)
    assert not ctl.active and state['closed']
    assert events[-1]['status']=='COMPLETE' and events[-1]['percent']==100
    assert 'SYNTHETIC_SECRET_STDERR_MUST_NOT_LEAK' not in str(events)
    assert '--npwp' in state['argv'] and 'password' not in str(state['argv'])


def test_stop_precedence_and_fifteen_second_forced_owned_cleanup(controlled_worker,monkeypatch):
    ctl,child,state,events=controlled_worker
    controller=module('controller')
    clock=[100.0]
    monkeypatch.setattr(controller.time,'monotonic',lambda:clock[0])
    ctl.stop()
    assert json.loads(child.stdin.getvalue().splitlines()[-1])['command']=='stop'
    clock[0]=116.0
    finish_controller(ctl)
    assert not ctl.active and state['closed']
    assert events[-1]['status']=='CANCELLED' and events[-1]['percent']<100


def test_worker_exit_zero_alone_is_not_success(controlled_worker):
    ctl,child,state,events=controlled_worker
    child.returncode=1
    finish_controller(ctl)
    assert events[-1]['status']=='ERROR' and events[-1]['percent']<100


def test_worker_cannot_inherit_credential_logging_debug_flags(controlled_worker):
    ctl,child,state,events=controlled_worker
    assert 'DEBUG' not in state['env_keys'] and 'PWDEBUG' not in state['env_keys']


def finish_controller(ctl):
    import time
    for _ in range(200):
        ctl.poll()
        if not ctl.active:return
        time.sleep(0.001)
    raise AssertionError('Synthetic controller did not reach an idle terminal state')
