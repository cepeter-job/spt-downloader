"""The launcher does not scrape or certify a check before worker cleanup."""
import io,json,subprocess,sys,time
from pathlib import Path
import pytest
from spt_desktop import controller,worker

ORIGIN='https://satu.intranet.pajak.go.id'
ACCOUNT='SYNTHETIC_ACCOUNT'


def terminal(job_id='check',status='LOGIN_OK',**extra):
    return dict(job_id=job_id,type='terminal',stage='login_check',status=status,percent=0,
                output=None,message='Login berhasil; synthetic-only fixture',**extra)


def test_check_protocol_is_not_export_success(tmp_path):
    assert 'operation' in __import__('inspect').signature(controller.parse_event).parameters
    event=controller.parse_event(json.dumps(terminal()),'check',operation='login_check')
    assert event and event['status']=='LOGIN_OK' and not event['output'] and event['percent']==0
    assert controller.parse_event(json.dumps(terminal()),'check') is None
    wrong=terminal();wrong['status']='COMPLETE';wrong['percent']=100
    assert controller.parse_event(json.dumps(wrong),'check',operation='login_check') is None
    wrong=terminal();wrong['output']=str(tmp_path);wrong['percent']=100
    assert controller.parse_event(json.dumps(wrong),'check',operation='login_check') is None


@pytest.fixture
def controlled_check(tmp_path,monkeypatch):
    assert hasattr(controller.JobController,'start_login_check'), 'Async credential-check launcher is missing'
    state={}
    class Child:
        returncode=None
        stdin=io.StringIO()
        stderr=io.StringIO('SYNTHETIC_SECRET_MUST_NOT_LEAK')
        def poll(self):return self.returncode
    child=Child()
    class Job:
        def spawn(self,argv,**kwargs):
            state['argv']=argv
            job=argv[argv.index('--job-id')+1]
            child.stdout=io.StringIO(json.dumps(terminal(job))+'\n')
            return child
        def close(self):
            state['closed']=True
            if child.returncode is None:child.returncode=4
    monkeypatch.setattr(controller,'ProcessJob',Job)
    monkeypatch.setattr(controller,'downloads_folder',lambda:tmp_path/'Downloads')
    monkeypatch.setattr(controller,'ensure_runtime',lambda *args:Path(sys.executable))
    monkeypatch.setattr(controller,'worker_source',lambda root:tmp_path)
    events=[]
    def on_event(event):
        if event['type']=='terminal':assert state['closed']
        events.append(event)
    ctl=controller.JobController(tmp_path/'workspace',on_event)
    ctl.start_login_check(ORIGIN,ACCOUNT)
    deadline=time.monotonic()+2
    while ctl.process is None and time.monotonic()<deadline:ctl.poll();time.sleep(0.001)
    assert ctl.process is child
    yield ctl,child,state,events
    ctl.close()


def finish(ctl):
    deadline=time.monotonic()+2
    while ctl.active and time.monotonic()<deadline:ctl.poll();time.sleep(0.001)
    assert not ctl.active


def test_check_has_no_npwp_no_export_and_waits_for_owned_cleanup(controlled_check):
    ctl,child,state,events=controlled_check
    assert ctl.operation=='login_check'
    assert '--check-login' in state['argv'] and '--origin' in state['argv'] and '--account' in state['argv']
    assert '--npwp' not in state['argv'] and '--year' not in state['argv']
    assert 'password' not in str(state['argv'])
    for _ in range(5):ctl.poll();time.sleep(0.001)
    assert not any(e['type']=='terminal' for e in events)
    with pytest.raises(RuntimeError,match='berjalan'):ctl.start('0000000000000001','2025')
    with pytest.raises(RuntimeError,match='berjalan'):ctl.start_login_check(ORIGIN,ACCOUNT)
    child.returncode=0;finish(ctl)
    assert events[-1]['status']=='LOGIN_OK' and state['closed']
    assert 'SYNTHETIC_SECRET_MUST_NOT_LEAK' not in str(events)


def test_check_exit_mismatch_is_error_not_credential_valid(controlled_check):
    ctl,child,state,events=controlled_check
    child.returncode=1;finish(ctl)
    assert events[-1]['status']=='ERROR' and events[-1]['percent']==0


def test_cancel_overrides_pending_login_success(controlled_check):
    ctl,child,state,events=controlled_check
    ctl.stop();child.returncode=4;finish(ctl)
    assert events[-1]['status']=='CANCELLED'


def test_invalid_origin_and_empty_account_rejected_before_setup(tmp_path):
    assert hasattr(controller.JobController,'start_login_check')
    ctl=controller.JobController(tmp_path,lambda event:None)
    with pytest.raises(ValueError):ctl.start_login_check('https://example.com',ACCOUNT)
    with pytest.raises(ValueError):ctl.start_login_check(ORIGIN,'')
    assert not ctl.active and not tmp_path.joinpath('profile').exists()


def test_real_check_cli_stop_needs_no_npwp_no_browser_no_live_login(tmp_path):
    job='synthetic-check-stop'
    command=[sys.executable,'-m','spt_desktop.worker','--check-login','--root',str(tmp_path/'workspace'),
             '--job-id',job,'--origin',ORIGIN,'--account',ACCOUNT]
    result=subprocess.run(command,input=json.dumps({'job_id':job,'command':'stop'})+'\n',
                          capture_output=True,text=True,timeout=10)
    assert result.returncode==4
    events=[json.loads(line) for line in result.stdout.splitlines()]
    assert events[-1]['status']=='CANCELLED'
    assert events[-1]['stage']=='login_check' and events[-1]['percent']==0 and events[-1]['output'] is None
    assert not (tmp_path/'workspace').exists()
