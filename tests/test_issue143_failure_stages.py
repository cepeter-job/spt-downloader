"""Issue #143: synthetic, privacy-safe failure-stage evidence only.

These tests exercise existing fallback and PARTIAL gates; they do not perform
live Coretax calls, relax owned-source evidence or publish private data.
"""
import json
from types import SimpleNamespace

import pytest

from test_diagnostics import records
from test_mpn import scope_run
from test_mpn_capture_protocol import SyntheticUI


@pytest.mark.parametrize('stage', ['build', 'tabs'])
def test_corporate_unsupported_stage_keeps_whole_record_fallback(monkeypatch, tmp_path, stage):
    import coretax_browser
    import coretax_corporate
    import coretax_json
    from spt_desktop import diagnostics

    monkeypatch.setattr(coretax_browser, 'verify_detail_url', lambda *a: None)
    monkeypatch.setattr(coretax_browser, 'list_taxpayer_id', lambda url: 'SYNTHETIC-ID')
    monkeypatch.setattr(coretax_json, '_corporate_selected', lambda *a: {})
    monkeypatch.setattr(coretax_json, '_check_corporate_route', lambda *a: None)
    if stage == 'tabs':
        monkeypatch.setattr(coretax_corporate, '_tabs',
                            lambda page: (object(), SimpleNamespace(count=lambda: 0)))
    page = SimpleNamespace(url='https://synthetic.invalid/view',
                           evaluate=lambda *a: 'approved')
    record = {'list_url': 'https://synthetic.invalid/list', 'record_id': 'SYNTHETIC-ID'}
    approved = 'different' if stage == 'build' else 'approved'
    with diagnostics.session(tmp_path, 'worker') as log:
        forms = coretax_corporate.observe_forms(
            page, record, ('synthetic', 2025, 'period'), object(), approved_digest=approved)
        assert log.flush()
    assert forms is None
    events = [e for e in records(tmp_path) if e['event'] == 'corporate.observe_unavailable']
    assert len(events) == 1 and events[0]['corporate_observer_stage'] == stage
    assert events[0].get('form_ordinal') is None
    assert 'SYNTHETIC-ID' not in json.dumps(events)


def test_corporate_observer_exception_keeps_safe_type_not_exception_text(monkeypatch, tmp_path):
    import coretax_browser
    import coretax_corporate
    import coretax_json
    from spt_desktop import diagnostics

    secret = 'SYNTHETIC_PRIVATE_CORPORATE_VALUE'
    monkeypatch.setattr(coretax_browser, 'verify_detail_url', lambda *a: None)
    monkeypatch.setattr(coretax_browser, 'list_taxpayer_id', lambda url: secret)
    monkeypatch.setattr(coretax_json, '_corporate_selected', lambda *a: {})
    monkeypatch.setattr(coretax_json, '_check_corporate_route', lambda *a: None)

    def refuse(*args):
        raise RuntimeError(secret)
    page = SimpleNamespace(url=secret, evaluate=refuse)
    with diagnostics.session(tmp_path, 'worker') as log:
        result = coretax_corporate.observe_forms(
            page, {'list_url': secret, 'record_id': secret},
            ('synthetic', 2025, 'period'), object(), approved_digest='approved')
        assert log.flush()
    assert result is None
    event, = [e for e in records(tmp_path) if e['event'] == 'corporate.observe_unavailable']
    assert event['corporate_observer_stage'] == 'build'
    assert event['error']['type'] == 'RuntimeError'
    assert secret not in json.dumps(event)


@pytest.mark.parametrize('phase', ['session', 'open', 'parent_inventory', 'final_drain'])
def test_mpn_unsupported_stage_does_not_grant_completion(monkeypatch, tmp_path, phase):
    import coretax_mpn_browser as browser
    from coretax_mpn import MpnUnsupported
    from spt_desktop import diagnostics

    secret = 'SYNTHETIC_PRIVATE_MPN_VALUE'

    class Refusal(SyntheticUI):
        def open(self):
            if phase == 'open':
                raise MpnUnsupported(secret)

        def list_pages(self, max_pages):
            if phase == 'parent_inventory':
                raise MpnUnsupported(secret)
            yield from super().list_pages(max_pages)

        def finish(self):
            if phase == 'final_drain':
                raise MpnUnsupported(secret)

    def owned(*args, **kwargs):
        if phase == 'session':
            raise MpnUnsupported(secret)
        return Refusal(*args, **kwargs)

    monkeypatch.setattr(browser, 'AccountingUI', owned)
    run = scope_run()
    with diagnostics.session(tmp_path, 'worker') as log:
        result = browser.collect_mpn(object(), run, tmp_path)
        assert log.flush()
    assert result is run
    assert not run['complete']
    assert run['mpn']['status'] == 'PARTIAL'
    assert not run['mpn']['inventory_complete'] or phase == 'final_drain'
    event, = [e for e in records(tmp_path) if e['event'] == 'mpn.capture_failed']
    assert event['mpn_capture_stage'] == phase
    assert event['status'] == 'PARTIAL'
    assert event['error']['type'] == 'MpnUnsupported'
    assert secret not in json.dumps(event)


def test_mpn_proven_empty_inventory_remains_complete_without_failure_event(monkeypatch, tmp_path):
    import coretax_mpn_browser as browser
    from spt_desktop import diagnostics

    monkeypatch.setattr(browser, 'AccountingUI', SyntheticUI)
    run = scope_run()
    with diagnostics.session(tmp_path, 'worker') as log:
        browser.collect_mpn(object(), run, tmp_path)
        assert log.flush()
    assert run['mpn']['status'] == 'COMPLETE'
    assert run['mpn']['inventory_complete'] and run['mpn']['details_complete']
    assert run['mpn']['evidence']
    assert not [e for e in records(tmp_path) if e['event'] == 'mpn.capture_failed']


@pytest.mark.parametrize('event,field', [
    ('mpn.capture_failed', 'mpn_capture_stage'),
    ('corporate.observe_unavailable', 'corporate_observer_stage'),
])
def test_failure_stage_schema_refuses_arbitrary_private_values(monkeypatch, tmp_path, event, field):
    from spt_desktop import diagnostics

    class Poison:
        def __str__(self):
            raise AssertionError('Must not stringify')
    secret = 'SYNTHETIC_PRIVATE_STAGE'
    with diagnostics.session(tmp_path, 'worker') as log:
        diagnostics.record(event, **{field: secret}, url=secret, body=secret)
        diagnostics.record(event, **{field: Poison()}, headers=secret)
        diagnostics.record(event, **{field: True}, message=secret)
        assert log.flush()
    rows = [e for e in records(tmp_path) if e['event'] == event]
    assert len(rows) == 3
    assert all(field not in e for e in rows)
    assert secret not in json.dumps(rows)
