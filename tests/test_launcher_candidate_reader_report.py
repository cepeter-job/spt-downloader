"""Synthetic reader reports cannot turn missing native observations into acceptance."""
import copy
import pytest
from scripts.launcher_candidate import inventory as contracts


def validate(report, inventory):
    validator = getattr(contracts, 'validate_reader_report', None)
    assert validator is not None, 'reader report validation is not implemented'
    return validator(report, inventory)


@pytest.fixture
def evidence():
    inventory = {**contracts.IDENTITY, 'loaded': {'python': 'python314.dll', '_tkinter': '_tkinter.pyd', 'tcl': 'tcl91.dll', 'tk': 'tk91.dll'},
                 'libraries': {'tcl': 'tcl', 'tk': 'tk'},
                 'files': {'python314.dll': '1'*64, '_tkinter.pyd': '2'*64, 'tcl91.dll': '3'*64, 'tk91.dll': '4'*64, 'tcl/init.tcl': '5'*64, 'tk/tk.tcl': '6'*64}}
    report = {'schema': 1, 'reader': {'name': 'NVDA', 'version': 'synthetic-version', 'available': True, 'pid': 101},
              'mode': 'source', 'scenario': 'settings', 'activation_timing': 'before_tk',
              'activation': {'observed': True, 'reader_running': True, 'tk_initialized': True, 'evidence': ['native']},
              'ownership': {'pid': 102, 'windows_verified': True, 'isolated': True},
              'candidate': {**contracts.IDENTITY, 'loaded_sha256': {k: inventory['files'][v] for k,v in inventory['loaded'].items()}, 'resources': inventory['files'].copy()},
              'evidence': {'native': {'path': 'native.json', 'sha256': 'a'*64, 'mode': 'source', 'reader': 'NVDA', 'scenario': 'settings', 'activation_timing': 'before_tk', 'pid': 102}},
              'providers': {'MSAA': {'observed': True, 'evidence': ['native']}, 'UIA': {'observed': True, 'evidence': ['native']}},
              'outcomes': {k: {'status': 'passed', 'evidence': ['native']} for k in ('password', 'names_roles_values_states', 'focus', 'selection', 'speech_navigation')},
              'password_observations': {k: {'observed': True, 'exposed': False, 'evidence': ['native']} for k in ('msaa_value', 'uia_value', 'msaa_selection', 'uia_selection', 'focus_notifications', 'typing_echo', 'reader_copy', 'remap', 'reopen')},
              'speech': {'observed': True, 'method': 'reader_output', 'evidence': ['native']}}
    return report, inventory


def test_accept_complete_independent_source_evidence(evidence):
    assert validate(*evidence) is None


@pytest.mark.parametrize('change', ['absent_activation', 'unverified_late', 'missing_msaa', 'missing_uia', 'source_as_frozen', 'password_missing', 'unavailable', 'speech_inferred', 'wrong_native', 'unowned', 'missing_ref', 'cross_reader', 'exposed', 'unknown_outcome'])
def test_reject_unsupported_acceptance(evidence, change):
    report, inventory = evidence
    if change == 'absent_activation': report.pop('activation')
    elif change == 'unverified_late': report['activation_timing'] = 'late'; report['activation']['observed'] = False
    elif change == 'missing_msaa': report['providers'].pop('MSAA')
    elif change == 'missing_uia': report['providers'].pop('UIA')
    elif change == 'source_as_frozen': report['mode'] = 'frozen'
    elif change == 'password_missing': report['password_observations'].pop('typing_echo')
    elif change == 'unavailable': report['reader']['available'] = False
    elif change == 'speech_inferred': report['speech']['method'] = 'uia'
    elif change == 'wrong_native': report['candidate']['loaded_sha256']['tk'] = '0'*64
    elif change == 'unowned': report['ownership']['windows_verified'] = False
    elif change == 'missing_ref': report['outcomes']['focus']['evidence'] = ['absent']
    elif change == 'cross_reader': report['evidence']['native']['reader'] = 'Narrator'
    elif change == 'exposed': report['password_observations']['msaa_value']['exposed'] = True
    elif change == 'unknown_outcome': report['outcomes']['focus']['status'] = 'ok'
    with pytest.raises(ValueError): validate(report, inventory)


def test_blocked_reader_is_valid_but_never_changed_to_pass(evidence):
    report, inventory = evidence
    report['reader'].update(available=False, pid=None, version=None)
    report['activation'] = {'observed': False, 'reason': 'Reader unavailable on disposable runner'}
    report['providers'] = {}
    report['password_observations'] = {}
    report['speech'] = {'observed': False}
    for outcome in report['outcomes'].values(): outcome.update(status='blocked', reason='Reader unavailable on disposable runner')
    before = copy.deepcopy(report)
    validate(report, inventory)
    assert report == before


def test_exposure_is_valid_failure_and_blocks_general_acceptance(evidence):
    report, inventory = evidence
    report['password_observations']['msaa_value']['exposed'] = True
    report['outcomes']['password']['status'] = 'failed'
    for key in report['outcomes']:
        if key != 'password': report['outcomes'][key].update(status='blocked', reason='Password gate failed')
    validate(report, inventory)


def test_reject_general_pass_after_password_failure(evidence):
    report, inventory = evidence
    report['outcomes']['password']['status'] = 'failed'
    report['password_observations']['msaa_value']['exposed'] = True
    with pytest.raises(ValueError): validate(report, inventory)


def test_host_refuses_existing_directory_before_loading_tk(tmp_path):
    import importlib.util
    spec = importlib.util.find_spec('scripts.launcher_candidate.reader_host')
    assert spec is not None, 'candidate fixture host missing'
    from scripts.launcher_candidate.reader_host import prepare_directory
    marker = tmp_path / 'owner.txt'
    marker.write_text('unrelated synthetic owner')
    with pytest.raises(ValueError): prepare_directory(tmp_path)
    assert marker.read_text() == 'unrelated synthetic owner'


def test_host_refuses_invalid_scenario_before_loading_tk(tmp_path):
    import importlib.util
    spec = importlib.util.find_spec('scripts.launcher_candidate.reader_host')
    assert spec is not None, 'candidate fixture host missing'
    from scripts.launcher_candidate.reader_host import run
    output = tmp_path / 'new'
    with pytest.raises(ValueError): run('arbitrary-code', output)
    assert not output.exists()


def test_exposure_without_activation_is_owned_evidenced_failure(evidence):
    report, inventory = evidence
    report['activation'] = {'observed': False, 'reader_running': True, 'tk_initialized': False}
    report['password_observations']['remap'].update(exposed=True)
    report['outcomes']['password']['status'] = 'failed'
    for key, outcome in report['outcomes'].items():
        if key != 'password': outcome.update(status='blocked', reason='Password exposure')
    validate(report, inventory)
    report['password_observations']['remap']['evidence'] = []
    with pytest.raises(ValueError): validate(report, inventory)


def test_selection_only_remap_exposure_is_reduced_with_refs():
    import subprocess
    from pathlib import Path
    probe = Path(contracts.__file__).with_name('reader_probe.ps1')
    script = r'''
    $tokens=$null; $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile($args[0], [ref]$tokens, [ref]$errors)
    $fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'ReducePhase'}, $true)
    if (-not $fn) { throw 'ReducePhase missing' }
    Invoke-Expression $fn.Extent.Text
    $result=ReducePhase @{msaa_value=@{observed=$true;exposed=$false};uia_selection=@{observed=$true;exposed=$true}}
    if (-not $result.exposed -or -not $result.observed -or $result.evidence[0] -ne 'native') {throw 'selection exposure lost'}
    '''
    # Encoded source avoids path quoting and invokes only this pure reducer.
    import base64
    script = script.replace('$args[0]', "'" + str(probe).replace("'", "''") + "'")
    result = subprocess.run(['powershell', '-NoProfile', '-EncodedCommand', base64.b64encode(script.encode('utf-16-le')).decode()], capture_output=True)
    assert result.returncode == 0, result.stderr.decode(errors='replace')


def test_owned_cleanup_unavailable_handle_fails_closed():
    from scripts.launcher_candidate import reader_runner
    close_owned = getattr(reader_runner, 'close_owned', None)
    assert close_owned is not None, 'owned cleanup helper missing'
    class Kernel:
        def OpenProcess(self, *args): return None
        def WaitForSingleObject(self, *args): raise AssertionError('no handle')
        def CloseHandle(self, *args): raise AssertionError('no handle')
    class Job:
        closed = False
        def close(self): self.closed = True
    job = Job()
    result = close_owned(Kernel(), job, [321], lambda: 5)
    assert job.closed
    assert result['cleanup_complete'] is False
    assert result['unverified_processes'] == [{'pid': 321, 'operation': 'OpenProcess', 'winerror': 5}]


def test_snapshot_publication_does_not_replace_open_previous_snapshot(tmp_path):
    import ctypes
    from ctypes import wintypes
    import json
    from scripts.launcher_candidate import reader_host
    publisher_type = getattr(reader_host, 'SnapshotPublisher', None)
    assert publisher_type is not None, 'immutable snapshot publisher missing'
    publisher = publisher_type(tmp_path)
    first = publisher.publish({'sequence': 0, 'synthetic': 'old'})
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    kernel.CreateFileW.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    kernel.CreateFileW.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = kernel.CreateFileW(str(first), 0x80000000, 1, None, 3, 0, None)
    assert handle != wintypes.HANDLE(-1).value
    try:
        second = publisher.publish({'sequence': 1, 'synthetic': 'new'})
        assert first.name == 'ready-000.json' and second.name == 'ready-001.json'
        assert json.loads(first.read_text()) == {'sequence': 0, 'synthetic': 'old'}
        assert json.loads(second.read_text()) == {'sequence': 1, 'synthetic': 'new'}
    finally:
        kernel.CloseHandle(handle)


def test_snapshot_publication_cap_fails_closed(tmp_path):
    from scripts.launcher_candidate import reader_host
    publisher_type = getattr(reader_host, 'SnapshotPublisher', None)
    assert publisher_type is not None, 'immutable snapshot publisher missing'
    publisher = publisher_type(tmp_path)
    for sequence in range(128): publisher.publish({'sequence': sequence})
    with pytest.raises(ValueError): publisher.publish({'sequence': 128})
    assert len(list(tmp_path.iterdir())) == 128


@pytest.mark.parametrize('case', ['latest', 'malformed_name', 'incomplete_json', 'oversize', 'gap', 'pending_only'])
def test_snapshot_reader_rejects_incomplete_or_malformed_publications(tmp_path, case):
    import base64
    import json
    import subprocess
    from pathlib import Path
    good = {'sequence': 0, 'pid': 1, 'hwnd': 2, 'tk_initialized': False, 'candidate': {}}
    (tmp_path / 'ready-000.json').write_text(json.dumps(good))
    if case == 'latest': (tmp_path / 'ready-001.json').write_text(json.dumps({**good, 'sequence': 1}))
    elif case == 'malformed_name': (tmp_path / 'ready-bad.json').write_text('{}')
    elif case == 'incomplete_json': (tmp_path / 'ready-001.json').write_text('{')
    elif case == 'oversize': (tmp_path / 'ready-001.json').write_text(' ' * 1048577)
    elif case == 'gap': (tmp_path / 'ready-002.json').write_text(json.dumps(good))
    elif case == 'pending_only':
        (tmp_path / 'ready-000.json').unlink()
        (tmp_path / 'ready.pending').write_text('{')
    probe = Path(contracts.__file__).with_name('reader_probe.ps1')
    quoted = lambda value: "'" + str(value).replace("'", "''") + "'"
    script = r'''
    $ErrorActionPreference='Stop'; $tokens=$null; $errors=$null
    $ast=[Management.Automation.Language.Parser]::ParseFile(PROBE,[ref]$tokens,[ref]$errors)
    $fn=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'ReadSnapshot'},$true)
    if (-not $fn) {throw 'ReadSnapshot missing'}
    Invoke-Expression $fn.Extent.Text
    $rejected=$false; $value=$null
    try {$value=ReadSnapshot DIRECTORY} catch {$rejected=$true}
    if (CASE -eq 'latest') {if ($rejected -or $value.sequence -ne 1) {throw 'latest snapshot not read'}}
    elseif (CASE -eq 'pending_only') {if ($rejected -or $null -ne $value) {throw 'incomplete publication used'}}
    elseif (-not $rejected) {throw 'malformed publication accepted'}
    '''.replace('PROBE', quoted(probe)).replace('DIRECTORY', quoted(tmp_path)).replace('CASE', quoted(case))
    result = subprocess.run(['powershell', '-NoProfile', '-EncodedCommand', base64.b64encode(script.encode('utf-16-le')).decode()], capture_output=True)
    assert result.returncode == 0, result.stderr.decode(errors='replace')

def test_wrapper_records_sanitized_early_probe_exit(tmp_path):
    import json
    from scripts.launcher_candidate import reader_runner
    record = getattr(reader_runner, 'record_probe_exit', None)
    assert record is not None, 'early exit evidence missing'
    directory = tmp_path / 'owned-new'
    record(directory, 1, timed_out=False)
    value = json.loads((directory / 'probe-exit.json').read_text())
    assert value == {'schema': 1, 'exit_code': 1, 'timed_out': False,
                     'phase_retained': False, 'report_retained': False, 'failure_retained': False}


def test_probe_existing_output_refusal_never_writes_diagnostics(tmp_path):
    import subprocess
    from pathlib import Path
    marker = tmp_path / 'owner.txt'
    marker.write_text('synthetic unrelated owner')
    probe = Path(contracts.__file__).with_name('reader_probe.ps1')
    result = subprocess.run(['powershell', '-NoProfile', '-File', str(probe), '-Runtime', 'unused',
                             '-Reader', 'Narrator', '-OutputDirectory', str(tmp_path)], capture_output=True)
    assert result.returncode != 0
    assert list(tmp_path.iterdir()) == [marker]
    assert marker.read_text() == 'synthetic unrelated owner'

@pytest.mark.skipif(__import__('sys').platform != 'win32', reason='Native candidate behavioral fixture')
def test_finite_regression_scenario_exercises_real_app_and_owned_cleanup(tmp_path):
    import json
    from scripts.launcher_candidate.reader_host import run
    directory = tmp_path / 'regression'
    assert run('regression', directory) == 0
    report = json.loads((directory / 'regression.json').read_text(encoding='utf-8'))
    assert report['checks'] == {
        'settings_return_discard_save_clear': True,
        'selection_explicit_consent': True,
        'overwrite_preserve_and_explicit_consent': True,
        'stale_and_stop_precedence': True,
        'complete_partial_eligibility': True,
        'owned_cleanup': True,
    }
    assert report['credentials_accessed'] is False
    assert report['live_scrape'] is False
    assert report['accessibility_acceptance'] is False
