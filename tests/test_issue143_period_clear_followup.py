"""Issue #143 post-merge finite MPN filter diagnosis; synthetic only.

All live taxpayer details remain local. Run product tests on GitHub hosted
Windows runners, not on the user's workstation.
"""
import json

import pytest

from coretax_mpn_ui import AccountingUI
from spt_desktop import diagnostics
from test_diagnostics import records
from test_mpn import scope_run
from test_mpn_capture_browser import portal
from support_isolated_browser import browser


CANCELLED = {'PropertyName': 'IsCancelled', 'Value': '0',
             'MatchMode': 'equals', 'CaseSensitive': True, 'AsString': False}
DATE = {'PropertyName': 'TransactionDate',
        'Value': ['SYNTHETIC_DAY_A', 'SYNTHETIC_DAY_B'],
        'MatchMode': 'between'}


@pytest.mark.parametrize('filters,expected', [
    ([CANCELLED], None),
    ([CANCELLED, DATE], 'date_filter_present'),
    ([CANCELLED, {'PropertyName': 'SyntheticUnsupported', 'Value': 'secret'}],
     'additional_filter'),
    ([], 'cancelled_filter_missing'),
    ([DATE], 'cancelled_filter_missing'),
    ([{**CANCELLED, 'Value': '1'}], 'cancelled_filter_modified'),
    ([{**CANCELLED, 'Unexpected': True}], 'cancelled_filter_modified'),
    ('UNTRUSTED_WRONG_SHAPE', 'request_shape'),
])
def test_mpn_filter_reason_only_describes_existing_strict_admission(filters, expected):
    snapshot = {'request': {'Filters': filters}}
    assert AccountingUI._unfiltered_reason(snapshot) == expected
    assert AccountingUI._unfiltered(snapshot) is (expected is None)


def test_real_synthetic_stuck_period_clear_records_safe_cause_and_never_completes(
        browser, tmp_path, monkeypatch):
    from coretax_mpn_browser import collect_mpn
    with portal(browser, monkeypatch, default_stuck=True) as (page, metrics):
        run = scope_run()
        with diagnostics.session(tmp_path / 'log', 'worker') as log:
            collect_mpn(page, run, tmp_path)
            assert log.flush()
    events = [r for r in records(tmp_path / 'log')
              if r['event'] == 'mpn.unfiltered_refused']
    assert 1 <= len(events) <= 2
    assert all(e['mpn_filter_reason'] == 'date_filter_present' for e in events)
    assert all(e['mpn_clear_state'] == 'absent' for e in events)
    assert not run['complete'] and run['mpn']['status'] == 'PARTIAL'
    assert metrics['detail'] == []
    assert run['mpn']['rows'] == []


def test_mpn_filter_event_never_serializes_values_or_unreviewed_categories(tmp_path):
    secret = 'SYNTHETIC_PRIVATE_TAXPAYER_AND_PERIOD'
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        diagnostics.record('mpn.unfiltered_refused',
                           mpn_filter_reason='date_filter_present',
                           mpn_clear_state='absent', body=secret, npwp=secret)
        diagnostics.record('mpn.unfiltered_refused',
                           mpn_filter_reason=secret,
                           mpn_clear_state=secret)
        assert log.flush()
    events = [r for r in records(tmp_path / 'log')
              if r['event'] == 'mpn.unfiltered_refused']
    assert len(events) == 2
    assert events[0]['mpn_filter_reason'] == 'date_filter_present'
    assert events[0]['mpn_clear_state'] == 'absent'
    assert 'mpn_filter_reason' not in events[1]
    assert 'mpn_clear_state' not in events[1]
    assert secret not in json.dumps(events)
