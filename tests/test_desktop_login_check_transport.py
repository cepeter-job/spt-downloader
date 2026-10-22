"""The removed login-check command cannot launch work or admit protocol events."""
import json,subprocess,sys
from spt_desktop import controller,worker

ORIGIN='https://satu.intranet.pajak.go.id'
ACCOUNT='SYNTHETIC_ACCOUNT'


def test_removed_login_check_has_no_callable_entry_points(tmp_path):
    from spt_desktop import auth
    ctl = controller.JobController(tmp_path, lambda event: None)
    assert not hasattr(ctl, 'start_login_check')
    assert not hasattr(worker, 'run_login_check')
    assert not hasattr(auth, 'check_saved_credentials')


def test_removed_login_check_protocol_is_rejected():
    event = terminal()
    assert controller.parse_event(json.dumps(event), 'check', operation='login_check') is None
    event.update(type='progress', stage='login_check')
    event.pop('status')
    assert controller.parse_event(json.dumps(event), 'check', operation='login_check') is None


def test_removed_login_check_cli_is_rejected_before_workspace_or_browser(tmp_path):
    workspace = tmp_path / 'workspace'
    command = [sys.executable, '-m', 'spt_desktop.worker', '--check-login',
               '--root', str(workspace), '--job-id', 'synthetic-removed-check',
               '--origin', ORIGIN, '--account', ACCOUNT]
    incoming = json.dumps({'job_id': 'synthetic-removed-check', 'command': 'stop'}) + '\n'
    result = subprocess.run(command, input=incoming, capture_output=True, text=True, timeout=10)
    assert result.returncode == 2
    assert '--check-login' in result.stderr and 'unrecognized arguments' in result.stderr
    assert not result.stdout
    assert not workspace.exists()


def terminal(job_id='check',status='LOGIN_OK',**extra):
    return dict(job_id=job_id,type='terminal',stage='login_check',status=status,percent=0,
                output=None,message='Login berhasil; synthetic-only fixture',**extra)
