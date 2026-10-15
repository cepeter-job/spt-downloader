"""Synthetic local diagnostics contracts; never use real taxpayer inputs."""
from concurrent.futures import ThreadPoolExecutor
import gc
import importlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest


def diagnostics():
    assert importlib.util.find_spec('spt_desktop.diagnostics'), 'Safe diagnostics module is not implemented'
    return importlib.import_module('spt_desktop.diagnostics')


def records(root):
    return [json.loads(line) for file in sorted((root / 'logs').glob('diag-*.jsonl'))
            for line in file.read_text(encoding='utf-8').splitlines()]


def test_diagnostics_are_explicit_jsonl_with_safe_metadata_and_no_stdout(tmp_path, capsys):
    d = diagnostics()
    with d.session(tmp_path, 'worker', job_id='synthetic-job', level='INFO') as log:
        d.record('operation.started', operation='export')
        d.record('operation.finished', status='COMPLETE', exit_code=0)
        assert log.flush()
    rows = records(tmp_path)
    assert {'session.started', 'session.closed', 'operation.started', 'operation.finished'} <= {r['event'] for r in rows}
    assert all(r['schema'] == 1 and r['role'] == 'worker' for r in rows)
    assert len({r['session_id'] for r in rows}) == 1
    assert len({r['sequence'] for r in rows}) == len(rows)
    assert all(r['timestamp'].endswith('Z') for r in rows)
    assert all('job_id' not in r and r.get('job_ref') != 'synthetic-job' for r in rows)
    assert capsys.readouterr() == ('', '')


@pytest.mark.parametrize('field', ['npwp', 'year', 'account', 'password', 'token', 'cookie', 'url', 'path', 'message', 'payload', 'record_id', 'hash'])
def test_sensitive_fields_and_exception_content_never_enter_any_log(tmp_path, field):
    d = diagnostics()
    secret = 'SYNTHETIC_SECRET_0012345678901234'
    try:
        raise ValueError(secret + ' https://user:password@private.invalid/?token=secret')
    except ValueError as error:
        with d.session(tmp_path, 'cli', level='DEBUG') as log:
            d.record('operation.failed', error=error, **{field: secret}, status='ERROR')
            assert log.flush()
    data = '\n'.join(p.read_text(encoding='utf-8') for p in (tmp_path / 'logs').glob('*.jsonl'))
    assert secret not in data and 'private.invalid' not in data and 'user:password' not in data
    row = next(r for r in records(tmp_path) if r['event'] == 'operation.failed')
    assert row['error']['type'] == 'ValueError'
    assert field not in row and 'message' not in row['error']
    assert all(set(frame) == {'file', 'function', 'line'} for frame in row['error']['frames'])
    assert 'test_diagnostics.py' not in data


def test_untrusted_values_are_not_stringified_or_used_as_numeric_counters(tmp_path):
    d = diagnostics()
    class Untrusted:
        def __str__(self):
            raise AssertionError('Must never stringify arbitrary diagnostic values')
    with d.session(tmp_path, 'gui') as log:
        d.record('operation.finished', status=Untrusted(), count=Untrusted(), processed=True,
                 total=1234567890123456, message=Untrusted())
        assert log.flush()
    row = next(r for r in records(tmp_path) if r['event'] == 'operation.finished')
    assert not {'status', 'count', 'processed', 'total', 'message'} & row.keys()


def test_level_filter_and_closed_logger_do_not_write_extra_events(tmp_path):
    d = diagnostics()
    log = d.DiagnosticLog(tmp_path, 'gui', level='INFO')
    assert not log.record('progress', level='DEBUG', processed=1)
    assert log.record('operation.started')
    log.close(); log.close()
    before = records(tmp_path)
    assert not log.record('operation.failed')
    assert records(tmp_path) == before and not any(r['event'] == 'progress' for r in before)


def test_off_and_relative_roots_do_not_create_files(tmp_path, monkeypatch):
    d = diagnostics()
    monkeypatch.chdir(tmp_path)
    with d.session(tmp_path / 'disabled', 'gui', level='OFF'):
        d.record('operation.started')
    with d.session(Path('relative'), 'worker'):
        d.record('operation.started')
    assert list(tmp_path.iterdir()) == []


def test_rotation_is_bounded_and_preserves_unrelated_files(tmp_path):
    d = diagnostics()
    folder = tmp_path / 'logs'; folder.mkdir()
    unrelated = folder / 'user-notes.txt'; unrelated.write_text('DO NOT DELETE')
    with d.DiagnosticLog(tmp_path, 'worker', max_bytes=1024, backup_count=3, queue_size=512) as log:
        for i in range(150):
            log.record('progress', level='INFO', processed=i, total=150)
        assert log.flush()
    files = list(folder.glob('diag-*.jsonl'))
    assert 1 <= len(files) <= 3
    assert all(p.stat().st_size <= 1024 for p in files)
    rows = records(tmp_path)
    assert rows[-1]['event'] == 'session.closed'
    assert any(r.get('processed') == 149 for r in rows)
    assert all(len(line.encode('utf-8')) <= 4096 for p in files for line in p.read_text().splitlines())
    assert unrelated.read_text() == 'DO NOT DELETE'


def test_threads_write_valid_unique_sequences_without_shared_records(tmp_path):
    d = diagnostics()
    with d.DiagnosticLog(tmp_path, 'worker', queue_size=1024) as log:
        def emit(_):
            for i in range(50):
                assert log.record('progress', processed=i)
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(emit, range(4)))
        assert log.flush()
    rows = [r for r in records(tmp_path) if r['event'] == 'progress']
    assert len(rows) == 200 and len({r['sequence'] for r in rows}) == 200


def test_queue_overflow_is_bounded_and_reported_without_blocking(tmp_path, monkeypatch):
    d = diagnostics()
    started, release = threading.Event(), threading.Event()
    original = d.SegmentStore.write
    producer_done = threading.Event()
    writer_threads = []
    def slow_write(store, line):
        writer_threads.append(threading.current_thread())
        started.set()
        assert release.wait(10)
        return original(store, line)
    monkeypatch.setattr(d.SegmentStore, 'write', slow_write)
    log = d.DiagnosticLog(tmp_path, 'worker', queue_size=4)
    try:
        log.record('operation.started')
        assert started.wait(3)
        def produce():
            for _ in range(100):
                log.record('progress', processed=1)
            producer_done.set()
        producer = threading.Thread(target=produce, daemon=True); producer.start()
        assert producer_done.wait(1), 'Producers must not wait for the blocked sink'
        assert not log.flush(timeout=0.05)
        assert log.dropped > 0 and log.pending <= 4
        assert all(t is not threading.current_thread() for t in writer_threads)
    finally:
        release.set(); log.close()
    assert any(r.get('dropped', 0) > 0 for r in records(tmp_path))


def test_storage_failure_is_silent_and_does_not_change_original_exception(tmp_path, monkeypatch, capsys):
    d = diagnostics()
    def fail(*_):
        raise OSError('SYNTHETIC PASSWORD from filesystem')
    monkeypatch.setattr(d.SegmentStore, 'write', fail)
    original = ValueError('SYNTHETIC PRIVATE ORIGINAL')
    @d.traced('export')
    def operation():
        raise original
    with d.session(tmp_path, 'worker') as log:
        with pytest.raises(ValueError) as caught:
            operation()
        assert caught.value is original
        log.flush()
    assert capsys.readouterr() == ('', '')


def test_safe_trace_keeps_application_location_without_source_or_locals(tmp_path):
    d = diagnostics()
    secret = 'SYNTHETIC_SECRET_IN_FRAME'
    namespace = {'__name__': 'coretax'}
    exec(compile("def main():\n    private='" + secret + "'\n    raise ValueError(private)\n", '/private/user/coretax.py', 'exec'), namespace)
    with d.session(tmp_path, 'cli') as log:
        try:
            namespace['main']()
        except ValueError as error:
            d.record('operation.failed', error=error)
        assert log.flush()
    row = next(r for r in records(tmp_path) if r['event'] == 'operation.failed')
    assert {'file': 'coretax.py', 'function': 'main', 'line': 3} in row['error']['frames']
    assert secret not in json.dumps(row) and '/private' not in json.dumps(row)


def test_separate_processes_use_independent_files_with_same_job_reference(tmp_path):
    diagnostics()
    code = "from pathlib import Path; from spt_desktop.diagnostics import session,record\nimport sys\nwith session(Path(sys.argv[1]), 'worker', job_id='same-synthetic-job') as log:\n record('operation.started'); assert log.flush()\n"
    processes = [subprocess.Popen([sys.executable, '-c', code, str(tmp_path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
    for process in processes:
        out, err = process.communicate(timeout=20)
        assert process.returncode == 0 and not out and not err
    rows = [r for r in records(tmp_path) if r['event'] == 'operation.started']
    assert len(rows) == 2 and len({r['session_id'] for r in rows}) == 2
    assert len({r['job_ref'] for r in rows}) == 1
    assert len(rows[0]['job_ref']) == 64 and int(rows[0]['job_ref'], 16) >= 0
    files = list((tmp_path / 'logs').glob('diag-*.jsonl'))
    assert len(files) == 2
    assert all(len({json.loads(line)['session_id'] for line in p.read_text().splitlines()}) == 1 for p in files)


def test_redirected_log_directory_is_rejected_without_touching_target(tmp_path):
    d = diagnostics()
    root = tmp_path / 'workspace'; root.mkdir()
    outside = tmp_path / 'outside'; outside.mkdir()
    alias = root / 'logs'
    if sys.platform == 'win32':
        result = subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(alias), str(outside)], capture_output=True)
        assert result.returncode == 0
    else:
        alias.symlink_to(outside, target_is_directory=True)
    try:
        with d.session(root, 'gui') as log:
            d.record('operation.started'); log.flush()
        assert list(outside.iterdir()) == []
    finally:
        alias.rmdir() if sys.platform == 'win32' else alias.unlink()


def test_worker_error_has_safe_diagnostics_and_keeps_one_terminal(tmp_path, monkeypatch):
    d = diagnostics()
    from spt_desktop import worker
    def fail():
        raise ValueError('SYNTHETIC_PRIVATE_TAX_BODY')
    monkeypatch.setattr(worker, 'playwright_factory', fail)
    events = []
    with d.session(tmp_path, 'worker', job_id='test-worker') as log:
        result = worker.run_job('0000000000000001', '2025', tmp_path, 'test-worker', 'msedge', True,
                                events.append, lambda: False)
        assert log.flush()
    assert result == 1 and len([e for e in events if e['type'] == 'terminal']) == 1
    assert events[-1]['status'] == 'ERROR'
    errors = [r for r in records(tmp_path) if 'error' in r]
    assert errors and 'SYNTHETIC_PRIVATE_TAX_BODY' not in json.dumps(errors)
    assert '0000000000000001' not in json.dumps(records(tmp_path))


def test_controller_exit_mismatch_is_recorded_but_never_certified(tmp_path):
    d = diagnostics()
    from spt_desktop.controller import JobController
    from types import SimpleNamespace
    events = []
    controller = JobController(tmp_path, events.append)
    controller.active = True; controller.job_id = 'controller-fixture'
    controller.process = SimpleNamespace(stdin=None, stdout=None, stderr=None)
    controller._terminal = {'job_id': controller.job_id, 'type': 'terminal', 'status': 'COMPLETE',
                            'percent': 100, 'output': 'SYNTHETIC_PRIVATE_PATH'}
    with d.session(tmp_path, 'gui') as log:
        controller._finish(1)
        assert log.flush()
    assert events[-1]['status'] == 'ERROR' and events[-1]['output'] is None
    assert any(r['event'] == 'worker.finished' and r['status'] == 'ERROR' for r in records(tmp_path))


def test_worker_resources_explicitly_include_diagnostics_modules():
    from spt_desktop.runtime import WORKER_FILES
    assert {'spt_desktop/diagnostics.py', 'spt_desktop/diagnostic_store.py'} <= set(WORKER_FILES)


def test_frozen_report_requires_exercised_diagnostics():
    from test_desktop_build import report
    from build_desktop import validate_report
    data = report(); data.pop('diagnostics', None)
    with pytest.raises(RuntimeError, match='self-test'):
        validate_report(data)


@pytest.mark.parametrize('field', ['phase', 'status', 'operation', 'kind'])
def test_allowlisted_fields_still_reject_arbitrary_private_values(tmp_path, field):
    d = diagnostics()
    secret = 'SYNTHETIC_SECRET_INSIDE_ALLOWED_FIELD'
    with d.session(tmp_path, 'cli', level='DEBUG') as log:
        d.record('operation.started', **{field: secret})
        d.record(secret, message=secret)
        assert log.flush()
    assert secret not in json.dumps(records(tmp_path))


def test_retention_preserves_active_session_and_unrelated_hardlinks(tmp_path):
    d = diagnostics()
    active = d.DiagnosticLog(tmp_path, 'gui', max_files=3)
    active.record('operation.started'); assert active.flush()
    original = list((tmp_path / 'logs').glob('diag-*.jsonl'))[0]
    try:
        for _ in range(5):
            with d.DiagnosticLog(tmp_path, 'worker', max_files=3) as other:
                other.record('operation.started'); assert other.flush()
        assert original.is_file()
        assert len(list((tmp_path / 'logs').glob('diag-*.jsonl'))) <= 3
        active.record('operation.finished'); assert active.flush()
    finally:
        active.close()
    sentinel = tmp_path / 'outside'; sentinel.write_text('SYNTHETIC DO NOT TOUCH')
    link = tmp_path / 'logs' / ('diag-cli-' + 'a' * 32 + '-00000.jsonl')
    os.link(sentinel, link)
    os.utime(link, (0, 0))
    with d.DiagnosticLog(tmp_path, 'cli', max_files=3) as other:
        other.record('operation.started'); other.flush()
    assert sentinel.read_text() == 'SYNTHETIC DO NOT TOUCH' and link.exists()


def test_no_capacity_or_bad_root_disables_logging_not_the_operation(tmp_path, capsys):
    d = diagnostics()
    with d.DiagnosticLog(tmp_path, 'gui', max_files=1) as active:
        active.record('operation.started'); assert active.flush()
        with d.DiagnosticLog(tmp_path, 'worker', max_files=1) as blocked:
            blocked.record('operation.started'); blocked.flush()
        assert len(list((tmp_path / 'logs').glob('diag-*.jsonl'))) == 1
    bad = tmp_path / 'regular-file'; bad.write_text('SENTINEL')
    with d.session(bad, 'cli'):
        d.record('operation.started')
    assert bad.read_text() == 'SENTINEL' and capsys.readouterr() == ('', '')


def test_old_inactive_logs_expire_without_deleting_unrecognized_names(tmp_path):
    d = diagnostics()
    with d.DiagnosticLog(tmp_path, 'cli') as old:
        old.record('operation.started'); assert old.flush()
    old_files = list((tmp_path / 'logs').glob('diag-*.jsonl'))
    for path in old_files:
        os.utime(path, (0, 0))
    note = tmp_path / 'logs' / 'foreign.jsonl'; note.write_text('PRESERVE')
    with d.DiagnosticLog(tmp_path, 'gui') as fresh:
        fresh.record('operation.started'); assert fresh.flush()
    assert all(not path.exists() for path in old_files)
    assert note.read_text() == 'PRESERVE'


def test_close_returns_while_sink_is_stalled(tmp_path, monkeypatch):
    d = diagnostics()
    entered, release, closed = threading.Event(), threading.Event(), threading.Event()
    original = d.SegmentStore.write
    def stalled(store, line):
        entered.set(); release.wait(10); return original(store, line)
    monkeypatch.setattr(d.SegmentStore, 'write', stalled)
    log = d.DiagnosticLog(tmp_path, 'gui')
    try:
        log.record('operation.started'); assert entered.wait(3)
        def close():
            log.close(timeout=0.05); closed.set()
        threading.Thread(target=close, daemon=True).start()
        assert closed.wait(0.5), 'Close cannot wait indefinitely for disk I/O'
    finally:
        release.set(); log.close()


@pytest.mark.parametrize('mode', ['INFO', 'OFF', 'BROKEN'])
def test_worker_protocol_stdout_is_identical_with_logs_off_on_or_failed(tmp_path, mode):
    diagnostics()
    code = r"""import io,json,sys
from pathlib import Path
from spt_desktop import worker,diagnostics
if sys.argv[2]=='BROKEN':
 def fail(*args): raise OSError('SYNTHETIC DISK ERROR PRIVATE')
 diagnostics.SegmentStore.write=fail
import threading
finished=threading.Event()
class Commands:
 sent=False
 def readline(self, *args):
  if not self.sent:
   self.sent=True
   return json.dumps({'job_id':'test-job','command':'start'})+'\n'
  finished.wait(10)
  return ''
sys.stdin=Commands()
def fake(*args,**kwargs):
 print('SYNTHETIC PRIVATE DIAGNOSTIC',file=sys.stderr)
 args[6]({'job_id':'test-job','type':'terminal','status':'BLOCKED','percent':0,'output':None})
 finished.set()
 return 3
worker.run_job=fake
raise SystemExit(worker.main(['--root',sys.argv[1],'--job-id','test-job','--npwp','0000000000000001','--year','2025']))
"""
    env = os.environ.copy(); env['SPT_LOG_LEVEL'] = 'OFF' if mode == 'OFF' else 'INFO'
    result = subprocess.run([sys.executable, '-c', code, str(tmp_path), mode], capture_output=True, text=True, env=env, timeout=20)
    assert result.returncode == 3
    assert result.stdout == json.dumps({'job_id':'test-job','type':'terminal','status':'BLOCKED','percent':0,'output':None})+'\n'
    assert result.stderr == 'SYNTHETIC PRIVATE DIAGNOSTIC\n'
    assert 'SYNTHETIC PRIVATE' not in json.dumps(records(tmp_path))
    if mode == 'INFO':
        assert records(tmp_path), 'Enabled logger must actually run in the parity case'
    elif mode == 'OFF':
        assert not (tmp_path / 'logs').exists()


def test_frozen_diagnostic_evidence_is_positive_and_fail_closed():
    from test_desktop_build import report
    from build_desktop import validate_report
    data = report(); data['diagnostics'] = {'schema': 1, 'safe_logging': True}
    validate_report(data)
    for value in [None, {}, {'schema': 1, 'safe_logging': False}, {'schema': True, 'safe_logging': True}]:
        data['diagnostics'] = value
        with pytest.raises(RuntimeError, match='self-test'):
            validate_report(data)


def test_source_selftest_really_exercises_private_logging(tmp_path):
    from spt_gui import self_test
    target = tmp_path / 'selftest.json'
    try:
        assert self_test(target) == 0
        data = json.loads(target.read_text())
        assert data['diagnostics'] == {'schema': 1, 'safe_logging': True}
    finally:
        # Match the native GUI fixtures: unreachable Tk Variables must be
        # finalized on this test's UI thread, not a later diagnostic sink.
        gc.collect()


@pytest.mark.parametrize('level', ['INFO', 'OFF'])
def test_root_lookup_failure_cannot_prevent_cli_execution(tmp_path, monkeypatch, level):
    d = diagnostics()
    import coretax
    monkeypatch.setenv('SPT_LOG_LEVEL', level)
    monkeypatch.delenv('SPT_LOG_ROOT', raising=False)
    monkeypatch.setattr(d.sys, 'platform', 'linux')
    def unavailable_home(cls):
        raise RuntimeError('SYNTHETIC USER HOME UNAVAILABLE')
    monkeypatch.setattr(Path, 'home', classmethod(unavailable_home))
    monkeypatch.setattr(coretax, '_main', lambda argv: 42)
    assert coretax.main([]) == 42


def test_simultaneous_first_sessions_both_survive_directory_creation_race(tmp_path, monkeypatch):
    d = diagnostics()
    barrier = threading.Barrier(2)
    mkdir = Path.mkdir
    contenders = []
    def concurrent_creation(path, *args, **kwargs):
        if path == tmp_path / 'logs':
            contenders.append(threading.get_ident())
            barrier.wait(timeout=3)
        return mkdir(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'mkdir', concurrent_creation)
    first, second = d.DiagnosticLog(tmp_path, 'gui'), d.DiagnosticLog(tmp_path, 'worker')
    try:
        first.record('operation.started'); second.record('operation.started')
        assert first.flush() and second.flush()
    finally:
        first.close(); second.close()
    assert len(contenders) == 2 and len(set(contenders)) == 2
    assert len({r['session_id'] for r in records(tmp_path)}) == 2


def test_crashed_sessions_without_segments_do_not_leave_unbounded_leases(tmp_path):
    d = diagnostics()
    folder = tmp_path / 'logs'; folder.mkdir()
    stale = [folder / ('diag-cli-' + format(i, '032x') + '.active') for i in range(5)]
    for path in stale:
        path.touch()
    note = folder / 'unrelated.active'; note.write_text('PRESERVE')
    with d.DiagnosticLog(tmp_path, 'gui') as log:
        log.record('operation.started'); assert log.flush()
    assert all(not path.exists() for path in stale)
    assert note.read_text() == 'PRESERVE'


@pytest.mark.parametrize('mode', ['INFO', 'OFF', 'BROKEN'])
def test_cli_offline_output_is_unchanged_and_not_copied_to_logs(tmp_path, monkeypatch, capsys, mode):
    d = diagnostics()
    import coretax
    from test_split_output import fixture_run
    run = fixture_run()
    source = tmp_path / 'source.json'; source.write_text(json.dumps(run), encoding='utf-8')
    destination = tmp_path / 'output'
    log_root = tmp_path / 'diagnostic'
    monkeypatch.setenv('SPT_LOG_ROOT', str(log_root))
    monkeypatch.setenv('SPT_LOG_LEVEL', 'OFF' if mode == 'OFF' else 'INFO')
    if mode == 'BROKEN':
        def fail(*args):
            raise OSError('SYNTHETIC PRIVATE DISK ERROR')
        monkeypatch.setattr(d.SegmentStore, 'write', fail)
    code = coretax.main(['--from-json', str(source), '--output', str(destination)])
    assert code == (0 if run['complete'] else 2)
    stdout, stderr = capsys.readouterr()
    assert stdout.startswith('Resume rebuilt and verified: ' + str((destination / 'resume.xlsx').resolve()) + '\n')
    assert stdout.count('SPT files: ') == 1 and stderr == ''
    data = json.dumps(records(log_root))
    assert run['npwp'] not in data and str(source) not in data and 'SYNTHETIC PRIVATE' not in data
