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
