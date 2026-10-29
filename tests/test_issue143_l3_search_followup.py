"""Synthetic Issue #143 follow-up: reason-only L3 telemetry and one Search click.

No live accounts or source payloads; hosted runners alone execute these tests.
"""
import json

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from test_diagnostics import records
from test_json_hybrid_native import browser
from test_mpn_source_custody import source_ui


@pytest.mark.parametrize('case,expected', [
    ('cit_digest', 'cit_digest'),
    ('lifetime_start', 'lifetime_start'),
    ('script_providers', 'script_providers'),
    ('provider_digest_or_table_count', 'provider_digest_or_table_count'),
])
def test_l3_early_rejection_has_fixed_reason_and_no_observed_values(case, expected):
    from coretax_corporate import _observe_l3, CIT_SOURCE_URL
    from coretax_corporate_projection import L3_BUILD_DIGESTS

    class SyntheticCapture:
        def observe_component_lifetime(self, *, check_cancel=None):
            return None if case == 'lifetime_start' else {}

    class SyntheticPage:
        def evaluate(self, *args):
            return False  # Provider absent or deliberately wrong pinned digest.

    result = {}
    digest = 'UNTRUSTED_SYNTHETIC_DIGEST' if case == 'cit_digest' else L3_BUILD_DIGESTS[CIT_SOURCE_URL]
    assert _observe_l3(SyntheticPage(), object(), SyntheticCapture(), digest,
                       {}, 20, None, reason_out=result) is None
    assert result == {'reason': expected}
    assert 'UNTRUSTED_SYNTHETIC_DIGEST' not in json.dumps(result)


@pytest.mark.parametrize('defect,reason', [
    ('wrong-group', 'table_structure'),
    ('missing-reference', 'reference_request'),
    ('missing-footer', 'grid_or_footer_missing'),
])
def test_actual_synthetic_l3_owner_refusal_keeps_dom_fallback_and_logs_fixed_subreason(
        browser, tmp_path, monkeypatch, defect, reason):
    from coretax_corporate import observe_forms
    from coretax_json_capture import DetailJsonCapture
    from l3_observer_fixture import Fixture, ASSET
    from test_corporate_l3_observer import open_selected
    from spt_desktop import diagnostics
    import support_json_corpus as corpus

    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with diagnostics.session(tmp_path / 'log', 'worker') as log:
            with DetailJsonCapture(fixture.context, fixture.page, fixture.record,
                                   corpus.SCOPE, tmp_path) as capture:
                page = open_selected(fixture, capture)
                forms = observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                      approved_digest=fixture.pins[ASSET])
            assert log.flush()
        assert forms is None
        events = [e for e in records(tmp_path / 'log')
                  if e['event'] == 'corporate.observe_unavailable']
        assert len(events) == 1
        assert events[0]['corporate_observer_stage'] == 'l3'
        assert events[0]['corporate_l3_reason'] == reason
        assert events[0]['form_ordinal'] >= 0
        assert fixture.unexpected == []
    finally:
        fixture.close()


def test_l3_reason_allowlist_rejects_hostile_private_values(tmp_path):
    from spt_desktop import diagnostics

    class Poison:
        def __str__(self):
            raise AssertionError('Untrusted values must not be converted')

    secret = 'UNTRUSTED_SYNTHETIC_TAX_RECORD'
    with diagnostics.session(tmp_path, 'worker') as log:
        diagnostics.record('corporate.observe_unavailable',
                           corporate_observer_stage='l3',
                           corporate_l3_reason=secret, url=secret)
        diagnostics.record('corporate.observe_unavailable',
                           corporate_observer_stage='l3',
                           corporate_l3_reason=Poison())
        diagnostics.record('corporate.observe_unavailable',
                           corporate_observer_stage='l3',
                           corporate_l3_reason='table_structure')
        assert log.flush()
    rows = [r for r in records(tmp_path) if r['event'] == 'corporate.observe_unavailable']
    assert len(rows) == 3
    assert 'corporate_l3_reason' not in rows[0]
    assert 'corporate_l3_reason' not in rows[1]
    assert rows[2]['corporate_l3_reason'] == 'table_structure'
    assert secret not in json.dumps(rows)


def test_one_real_search_click_uses_longer_bounded_timeout_after_successful_trial(
        tmp_path, monkeypatch):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    trials, actual = [], []

    class Search:
        def click(self, *, trial=False, timeout):
            (trials if trial else actual).append(timeout)
            if not trial and timeout <= 1000:
                raise PlaywrightTimeoutError('Synthetic slow scheduling')

    try:
        ui._click_ready(Search(), actual_timeout_ms=5000)
        assert len(trials) == len(actual) == 1
        assert 0 < trials[0] <= 1000
        assert 1000 < actual[0] <= 5000
    finally:
        ui.observer.close()


@pytest.mark.parametrize('search', [False, True])
def test_actual_click_timeout_never_causes_second_real_click(tmp_path, monkeypatch, search):
    ui, _, _ = source_ui(tmp_path, monkeypatch)
    trials, actual = [], []

    class Search:
        def click(self, *, trial=False, timeout):
            (trials if trial else actual).append(timeout)
            if not trial:
                raise PlaywrightTimeoutError('Synthetic uncertain delivery')

    try:
        with pytest.raises(PlaywrightTimeoutError):
            ui._click_ready(Search(), **({'actual_timeout_ms': 5000} if search else {}))
        assert len(trials) == len(actual) == 1
        assert actual[0] <= (5000 if search else 1000)
        assert not ui.source_safety and not ui.source_failed
    finally:
        ui.observer.close()


def test_search_open_path_keeps_single_real_click_and_explicit_bounded_budget():
    import inspect
    from coretax_mpn_ui import AccountingUI

    # This static wiring contract prevents tests of a helper from diverging
    # from the actual open() Search invocation.
    source = inspect.getsource(AccountingUI.open)
    assert 'self._click_ready(search, actual_timeout_ms=5000)' in source
    assert source.count('self._click_ready(search,') == 1
