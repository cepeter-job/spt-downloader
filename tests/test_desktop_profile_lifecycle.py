"""Owned temporary profiles survive neither normal exit nor verified abandonment.

Native cases use only dummy processes and synthetic files on GitHub Windows
runners. No browser login, Credential Manager access, or real session is used.
"""
from contextlib import contextmanager
import importlib
import importlib.util
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time

import pytest

from spt_desktop import auth, controller, worker, windows


def profiles():
    assert importlib.util.find_spec('spt_desktop.profile_lifecycle'), (
        'Temporary profiles need a leased ownership and abandoned-profile recovery boundary')
    return importlib.import_module('spt_desktop.profile_lifecycle')


def ownership(root, path):
    records = []
    for marker in (root / 'cache').glob('.spt-profile-*.json'):
        record = json.loads(marker.read_text(encoding='utf-8'))
        if record.get('profile') == path.name:
            records.append((marker, record))
    assert len(records) == 1, 'Each managed profile needs exactly one recoverable ownership record'
    return records[0]


def preserve_neighbors(root):
    files = []
    for relative in ('profile/keep.txt', 'jobs/synthetic-recovery/run.json',
                     'jobs/.spt-publish-synthetic/backup/keep.txt',
                     'cache/login-check-' + 'f' * 32 + '/keep.txt',
                     'cache/login-run-' + 'e' * 32 + '/keep.txt', 'cache/unrelated/keep.txt'):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'SYNTHETIC UNRELATED BYTES')
        files.append(path)
    return files


def assert_neighbors(files):
    assert all(path.read_bytes() == b'SYNTHETIC UNRELATED BYTES' for path in files)


@pytest.mark.parametrize('kind', ['login-check', 'login-run'])
def test_active_profile_is_not_reaped_and_normal_exit_removes_only_its_owned_tree(tmp_path, kind):
    module = profiles()
    keep = preserve_neighbors(tmp_path)
    with module.temporary_profile(tmp_path, kind) as value:
        path = Path(value)
        assert path.parent == tmp_path / 'cache'
        assert path.name.startswith(kind + '-')
        marker, record = ownership(tmp_path, path)
        assert record['schema'] == 1 and record['kind'] == kind
        (path / 'Default').mkdir()
        (path / 'Default' / 'synthetic-session').write_bytes(b'SYNTHETIC SESSION ONLY')
        module.reap_profiles(tmp_path)
        assert marker.is_file() and path.is_dir()
        assert (path / 'Default' / 'synthetic-session').read_bytes() == b'SYNTHETIC SESSION ONLY'
        assert_neighbors(keep)

    assert not path.exists() and not marker.exists()
    assert_neighbors(keep)


def test_missing_workspace_reaping_is_read_only_and_unknown_kinds_are_rejected(tmp_path):
    module = profiles()
    missing = tmp_path / 'not-created'
    module.reap_profiles(missing)
    assert not missing.exists()
    with pytest.raises(ValueError):
        with module.temporary_profile(tmp_path, 'profile'):
            pytest.fail('The default persistent profile must not enter temporary ownership')


_OWNER_SCRIPT = r'''
import json,sys,time
from pathlib import Path
from spt_desktop.profile_lifecycle import temporary_profile
with temporary_profile(Path(sys.argv[1]), sys.argv[2]) as profile:
    profile=Path(profile)
    (profile/'Default').mkdir()
    (profile/'Default'/'synthetic-session').write_bytes(b'SYNTHETIC SESSION ONLY')
    print(json.dumps({'profile':str(profile)}),flush=True)
    while True:
        time.sleep(0.1)
'''


@contextmanager
def native_owner(root, kind):
    profiles()
    job = windows.ProcessJob()
    process = None
    reader = None
    try:
        process = job.spawn([sys.executable, '-u', '-c', _OWNER_SCRIPT, str(root), kind],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding='utf-8')
        ready = queue.Queue(maxsize=1)
        reader = threading.Thread(target=lambda: ready.put(process.stdout.readline()), daemon=True)
        reader.start()
        try:
            line = ready.get(timeout=15)
        except queue.Empty:
            pytest.fail('Synthetic profile owner exceeded its bounded ready deadline')
        assert line, 'Synthetic profile owner did not reach its ready barrier'
        path = Path(json.loads(line)['profile'])
        yield job, process, path
    finally:
        job.close()
        if process is not None:
            process.wait(timeout=10)
            if reader is not None:
                reader.join(timeout=2)
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='Native owned process termination and profile leases')
@pytest.mark.parametrize('kind', ['login-check', 'login-run'])
def test_forced_owned_exit_can_be_reaped_without_touching_other_data(tmp_path, kind):
    module = profiles()
    keep = preserve_neighbors(tmp_path)
    with native_owner(tmp_path, kind) as (job, process, path):
        marker, _ = ownership(tmp_path, path)
        module.reap_profiles(tmp_path)
        assert process.poll() is None and path.exists() and marker.exists()
        job.close()
        process.wait(timeout=10)
        assert path.is_dir(), 'The synthetic owner must be killed before normal context cleanup'
        module.reap_profiles(tmp_path)
        assert not path.exists() and not marker.exists()
        assert_neighbors(keep)


@pytest.mark.skipif(sys.platform != 'win32', reason='Native controller-owned termination')
@pytest.mark.parametrize('kind', ['login-check', 'login-run'])
def test_controller_reclaims_profile_after_forced_stop_before_terminal(tmp_path, kind):
    profiles()
    events = []
    ctl = controller.JobController(tmp_path, events.append)
    try:
        with native_owner(tmp_path, kind) as (job, process, path):
            ctl.active = True
            ctl.operation = 'export'
            ctl.job_id = 'synthetic-profile-stop'
            ctl._job, ctl.process = job, process
            ctl.stop()
            ctl._stop_at = time.monotonic() - 1
            deadline = time.monotonic() + 10
            while ctl.active and time.monotonic() < deadline:
                ctl.poll()
                time.sleep(0.01)
            assert not ctl.active, 'Owned profile cleanup must not leave the controller permanently busy'
            assert process.poll() is not None
            assert not path.exists()
            assert [event['status'] for event in events if event['type'] == 'terminal'] == ['CANCELLED']
    finally:
        ctl.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='Next-start recovery of native abandoned leases')
def test_controller_reclaims_prior_abandonment_before_preparing_a_new_worker(tmp_path, monkeypatch):
    profiles()
    with native_owner(tmp_path, 'login-check') as (job, process, path):
        job.close()
        process.wait(timeout=10)
        assert path.exists()
        observed = []

        def no_runtime(root, on_status, cancelled):
            observed.append(path.exists())
            raise controller.SetupCancelled('Synthetic stop before any installation')

        monkeypatch.setattr(controller, 'ensure_runtime', no_runtime)
        ctl = controller.JobController(tmp_path, lambda event: None)
        try:
            ctl.start('0000000000000001', '2025', account='SYNTHETIC_ACCOUNT')
            deadline = time.monotonic() + 5
            while ctl.active and time.monotonic() < deadline:
                ctl.poll()
                time.sleep(0.01)
            assert observed == [False], 'Recovery must happen before preparing the next owned worker'
            assert not ctl.active and not path.exists()
        finally:
            ctl.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='Abrupt exit and Windows namespace safety')
@pytest.mark.parametrize('mutation', ['identity', 'malformed', 'unowned-copy', 'junction', 'marker-hardlink'])
def test_reaper_retains_unverifiable_profile_ownership_and_link_targets(tmp_path, mutation):
    module = profiles()
    keep = preserve_neighbors(tmp_path)
    with native_owner(tmp_path, 'login-check') as (job, process, path):
        marker, record = ownership(tmp_path, path)
        job.close()
        process.wait(timeout=10)
        original = path
        outside = tmp_path / 'outside'
        outside.mkdir()
        sentinel = outside / 'keep.txt'
        sentinel.write_bytes(b'SYNTHETIC OUTSIDE BYTES')
        if mutation == 'identity':
            moved = path.with_name(path.name + '-preserved')
            path.rename(moved)
            path.mkdir()
            (path / 'replacement').write_bytes(b'SYNTHETIC DIFFERENT DIRECTORY')
        elif mutation == 'malformed':
            marker.write_text('{broken', encoding='utf-8')
        elif mutation == 'unowned-copy':
            record['profile'] = 'unrelated'
            marker.write_text(json.dumps(record), encoding='utf-8')
        elif mutation == 'marker-hardlink':
            copied = outside / 'ownership-copy.json'
            os.link(marker, copied)
        else:
            subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(path / 'redirected'), str(outside)],
                           check=True, capture_output=True, text=True, timeout=10)
        try:
            module.reap_profiles(tmp_path)
            assert original.is_dir() and marker.is_file()
            evidence = moved if mutation == 'identity' else original
            assert (evidence / 'Default' / 'synthetic-session').read_bytes() == b'SYNTHETIC SESSION ONLY'
            assert sentinel.read_bytes() == b'SYNTHETIC OUTSIDE BYTES'
            assert_neighbors(keep)
        finally:
            if mutation == 'junction':
                (path / 'redirected').rmdir()


@pytest.mark.skipif(sys.platform != 'win32', reason='Native locked-profile cleanup recovery')
def test_locked_profile_cleanup_preserves_cancellation_and_retries_after_release(tmp_path):
    module = profiles()
    held = None
    try:
        cancelled = False
        try:
            with module.temporary_profile(tmp_path, 'login-run') as value:
                path = Path(value)
                marker, _ = ownership(tmp_path, path)
                held = (path / 'synthetic-locked-session').open('wb')
                held.write(b'SYNTHETIC SESSION ONLY')
                held.flush()
                raise worker.CaptureCancelled('Synthetic Stop with a still-closing profile handle')
        except worker.CaptureCancelled:
            cancelled = True
        assert cancelled, 'Cleanup must preserve the original cancellation'
        assert path.exists() and marker.exists()
        held.close()
        held = None
        module.reap_profiles(tmp_path)
        assert not path.exists() and not marker.exists()
    finally:
        if held is not None:
            held.close()


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows cache redirection')
def test_reaper_never_follows_redirected_cache_root(tmp_path):
    module = profiles()
    outside = tmp_path / 'outside'
    outside.mkdir()
    sentinel = outside / 'keep.txt'
    sentinel.write_bytes(b'SYNTHETIC OUTSIDE BYTES')
    root = tmp_path / 'workspace'
    root.mkdir()
    alias = root / 'cache'
    subprocess.run(['cmd', '/d', '/c', 'mklink', '/J', str(alias), str(outside)],
                   check=True, capture_output=True, text=True, timeout=10)
    try:
        module.reap_profiles(root)
        assert sentinel.read_bytes() == b'SYNTHETIC OUTSIDE BYTES'
        assert list(outside.iterdir()) == [sentinel]
    finally:
        alias.rmdir()


def test_account_bound_export_has_recoverable_profile_ownership_before_browser_start(tmp_path, monkeypatch):
    module = profiles()
    from contextlib import nullcontext
    observed = []
    monkeypatch.setattr(worker, 'playwright_factory', lambda: nullcontext(object()))

    def stop_at_launch(playwright, profile, *args, **kwargs):
        path = Path(profile)
        marker, _ = ownership(tmp_path, path)
        observed.append((path, marker))
        module.reap_profiles(tmp_path)
        assert path.exists() and marker.exists()
        raise worker.CaptureCancelled('Synthetic cancellation before any portal access')

    monkeypatch.setattr(worker, 'authenticate_owned', stop_at_launch)
    events = []
    code = worker.run_job('0000000000000001', '2025', tmp_path, 'synthetic-profile-export',
                          'msedge', True, events.append, lambda: False, account='SYNTHETIC_ACCOUNT')
    assert code == 4 and events[-1]['status'] == 'CANCELLED'
    assert len(observed) == 1 and all(not value.exists() for value in observed[0])
    assert not (tmp_path / 'profile').exists()
