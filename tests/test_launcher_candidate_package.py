"""Synthetic exact launcher-report contract; no native runtime execution."""
import copy

import pytest

from scripts.launcher_candidate.inventory import validate_candidate_report


@pytest.fixture
def proof():
    files = {name: str(index) * 64 for index, name in enumerate((
        'python314.dll', 'DLLs/_tkinter.pyd', 'DLLs/tcl91.dll', 'DLLs/tcl9tk91.dll',
        'tcl/tcl9.1/init.tcl', 'tcl/tk9.1/tk.tcl'), 1)}
    identity = {'schema': 1, 'python': '3.14.8', 'architecture': 'x64',
                'gil': True, 'tcl': '9.1.0', 'tk': '9.1.0'}
    inventory = {**identity, 'files': files,
        'loaded': dict(zip(('python', '_tkinter', 'tcl', 'tk'), list(files)[:4])),
        'libraries': {'tcl': 'tcl/tcl9.1', 'tk': 'tcl/tk9.1'}}
    report = {'python': '3.14.8', 'tcl': '9.1.0', 'tk': '9.1.0', 'ok': True, 'frozen': True, 'credentials_accessed': False,
              'live_scrape': False, 'worker_python': '3.14.8',
              'launcher_candidate': {**identity, 'loaded': inventory['loaded'].copy(),
                  'loaded_sha256': {role: files[name] for role, name in inventory['loaded'].items()},
                  'resources': files.copy()}}
    return report, inventory


def test_accept_complete_synthetic_candidate_report(proof):
    assert validate_candidate_report(*proof) is None


@pytest.mark.parametrize('version', ['9.0.4', '9.1.1', '9.2.0'])
@pytest.mark.parametrize('key', ['tcl', 'tk'])
def test_reject_syntactically_valid_wrong_versions(proof, key, version):
    report, inventory = proof
    report['launcher_candidate'][key] = version
    with pytest.raises(ValueError):
        validate_candidate_report(report, inventory)


@pytest.mark.parametrize('role', ['python', '_tkinter', 'tcl', 'tk'])
def test_reject_wrong_native_resource_identity(proof, role):
    report, inventory = proof
    report['launcher_candidate']['loaded_sha256'][role] = '0' * 64
    with pytest.raises(ValueError):
        validate_candidate_report(report, inventory)


def test_reject_old_runtime_selftest_attached_to_candidate(proof):
    report, inventory = proof
    report.pop('launcher_candidate')
    report.update(python='3.14.8', tcl='9.0.4', tk='9.0.4')
    with pytest.raises(ValueError):
        validate_candidate_report(report, inventory)


@pytest.mark.parametrize('name', ['DLLs/_tkinter.pyd', 'tcl/tcl9.1/init.tcl', 'tcl/tk9.1/tk.tcl'])
def test_reject_missing_frozen_resources(proof, name):
    report, inventory = proof
    del report['launcher_candidate']['resources'][name]
    with pytest.raises(ValueError):
        validate_candidate_report(report, inventory)


@pytest.mark.parametrize('key,value', [('ok', False), ('credentials_accessed', True),
                                     ('live_scrape', True), ('worker_python', '3.15.0')])
def test_reject_unsafe_or_wrong_worker_report(proof, key, value):
    report, inventory = proof
    report[key] = value
    with pytest.raises(ValueError):
        validate_candidate_report(report, inventory)


def test_accept_source_candidate_independently_of_freezing(proof):
    report, inventory = proof
    report['frozen'] = False
    validate_candidate_report(report, inventory)

@pytest.mark.parametrize('key,value', [('python', '3.14.7'), ('tcl', '9.0.4'), ('tk', '9.0.4')])
def test_reject_old_selftest_fields_attached_to_correct_candidate_proof(proof, key, value):
    report, inventory = proof
    report[key] = value
    with pytest.raises(ValueError):
        validate_candidate_report(report, inventory)
