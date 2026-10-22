"""Packaged bootstrap evidence is explicit, account-free and bound to the tested EXE."""
import copy
import hashlib
import importlib
import json
from pathlib import Path
import sys

import pytest


def runtime_checks():
    module = importlib.import_module('scripts.ci_runtime')
    assert callable(getattr(module, 'validate_packaged_report', None)), \
        'The packaged bootstrap evidence validator is missing.'
    return module


@pytest.fixture
def packaged_evidence(tmp_path):
    runtime = importlib.import_module('spt_desktop.runtime')
    executable = tmp_path / 'SPTDownloader.exe'
    executable.write_bytes(b'SYNTHETIC EXECUTABLE IDENTITY ONLY; NEVER EXECUTED')
    report = {
        'schema': 1, 'kind': 'packaged-bootstrap', 'ok': True, 'frozen': True,
        'executable_sha256': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'python': runtime.python_version(), 'worker_python': runtime.python_version(),
        'implementation': 'CPython', 'bits': 64, 'free_threaded': False,
        'uv_version': runtime.UV_VERSION, 'uv_source': 'bundled', 'path_uv_absent': True,
        'worker_resources': list(runtime.WORKER_FILES),
        'packages': runtime.locked_requirements(runtime.resource_root() / runtime.RUNTIME_LOCK),
        'checks': {'cold_install': True, 'reuse': True, 'cancelled': True, 'owned_cleanup': True},
        'credentials_accessed': False, 'live_scrape': False,
    }
    return executable, report


def test_packaged_report_requires_complete_matching_runtime_evidence(packaged_evidence):
    executable, report = packaged_evidence
    runtime_checks().validate_packaged_report(report, executable, 'production')


@pytest.mark.parametrize('damage', [
    'other_executable', 'source_only', 'numeric_success', 'wrong_python', 'wrong_package',
    'missing_resource', 'path_uv', 'path_present', 'live_credentials', 'live_scrape',
    'cold_missing', 'reuse_missing', 'cancel_missing', 'cleanup_missing',
])
def test_packaged_report_rejects_wrong_bytes_or_incomplete_execution(packaged_evidence, damage):
    executable, original = packaged_evidence
    report = copy.deepcopy(original)
    if damage == 'other_executable':
        executable.write_bytes(b'SYNTHETIC DIFFERENT EXECUTABLE')
    elif damage == 'source_only':
        report['frozen'] = False
    elif damage == 'numeric_success':
        report['ok'] = 1
    elif damage == 'wrong_python':
        report['worker_python'] = '3.11.17'
    elif damage == 'wrong_package':
        report['packages']['openpyxl'] = '0.0.0'
    elif damage == 'missing_resource':
        report['worker_resources'].pop()
    elif damage == 'path_uv':
        report['uv_source'] = 'PATH'
    elif damage == 'path_present':
        report['path_uv_absent'] = False
    elif damage == 'live_credentials':
        report['credentials_accessed'] = True
    elif damage == 'live_scrape':
        report['live_scrape'] = True
    else:
        name = {'cold_missing': 'cold_install', 'reuse_missing': 'reuse',
                'cancel_missing': 'cancelled', 'cleanup_missing': 'owned_cleanup'}[damage]
        del report['checks'][name]
    module = runtime_checks()
    with pytest.raises(ValueError, match='packaged|bootstrap|executable|runtime'):
        module.validate_packaged_report(report, executable, 'production')


def test_explicit_runtime_self_test_routes_away_from_gui_and_accounts(monkeypatch, tmp_path):
    gui = importlib.import_module('spt_gui')
    checks = importlib.import_module('scripts.ci_runtime')
    report = tmp_path / 'packaged.json'
    called = []

    def smoke(path):
        called.append(path)
        path.write_text(json.dumps({'synthetic_route': True}), encoding='utf-8')
        return 0

    def reject_gui():
        pytest.fail('The account-free bootstrap mode entered the ordinary GUI.')

    monkeypatch.setattr(checks, 'packaged_self_test', smoke, raising=False)
    monkeypatch.setattr(gui, '_run_gui', reject_gui)
    try:
        result = gui.main(['--runtime-self-test', '--report', str(report)])
    except SystemExit as error:
        result = error.code
    assert result == 0, 'The packaged-bootstrap entry point is unavailable.'
    assert called == [report]
    assert json.loads(report.read_text(encoding='utf-8')) == {'synthetic_route': True}


@pytest.mark.parametrize('arguments', [
    ['--runtime-self-test'], ['--runtime-self-test', '--self-test'],
])
def test_runtime_self_test_requires_a_report_and_a_distinct_mode(monkeypatch, arguments):
    gui = importlib.import_module('spt_gui')
    checks = importlib.import_module('scripts.ci_runtime')

    def reject_smoke(*args):
        pytest.fail('Invalid bootstrap arguments started product execution.')

    monkeypatch.setattr(checks, 'packaged_self_test', reject_smoke, raising=False)
    with pytest.raises(SystemExit) as error:
        gui.main(arguments)
    assert error.value.code == 2


@pytest.mark.skipif(sys.platform != 'win32', reason='Native Windows owned-process cancellation')
def test_packaged_cancellation_probe_closes_its_real_owned_process_tree(tmp_path):
    checks = importlib.import_module('scripts.ci_runtime')
    assert callable(getattr(checks, 'check_owned_cancellation', None)), \
        'Packaged bootstrap does not verify cancellation of a real owned process tree.'
    result = checks.check_owned_cancellation(Path(sys.executable), tmp_path)
    assert result == {'cancelled': True, 'owned_cleanup': True}
