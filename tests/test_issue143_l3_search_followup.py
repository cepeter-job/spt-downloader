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
    ('main_digest', 'main_digest'),
    ('vendor_digest', 'vendor_digest'),
    ('table_count_zero', 'table_count'),
    ('table_count_one', 'table_count'),
    ('table_count_extra', 'table_count'),
])
def test_l3_early_rejection_has_fixed_reason_and_no_observed_values(case, expected):
    from coretax_corporate import _observe_l3, CIT_SOURCE_URL
    from coretax_corporate_projection import L3_BUILD_DIGESTS, MAIN_SOURCE, VENDOR_SOURCE

    class SyntheticCapture:
        def observe_component_lifetime(self, *, check_cancel=None):
            return None if case == 'lifetime_start' else {}

    class Form:
        def locator(self, selector):
            assert selector == 'table'
            return self

        def count(self):
            return {'table_count_zero': 0, 'table_count_one': 1,
                    'table_count_extra': 3}.get(case, 2)

        def evaluate(self, *args, **kwargs):
            assert case == 'table_count_extra'
            return 'reviewed_pair_unproved'

    class SyntheticPage:
        def __init__(self):
            self.calls = 0

        def evaluate(self, *args):
            self.calls += 1
            values = (True, L3_BUILD_DIGESTS[MAIN_SOURCE], L3_BUILD_DIGESTS[VENDOR_SOURCE])
            if case == 'script_providers':
                return False
            if case == 'main_digest' and self.calls == 2:
                return 'SYNTHETIC_WRONG_MAIN_HASH'
            if case == 'vendor_digest' and self.calls == 3:
                return 'SYNTHETIC_WRONG_VENDOR_HASH'
            return values[self.calls - 1]

    result = {}
    digest = 'UNTRUSTED_SYNTHETIC_DIGEST' if case == 'cit_digest' else L3_BUILD_DIGESTS[CIT_SOURCE_URL]
    assert _observe_l3(SyntheticPage(), Form(), SyntheticCapture(), digest,
                       {}, 20, None, reason_out=result) is None
    assert result['reason'] == expected
    if case.startswith('table_count_'):
        assert result['table_shape'] == {'table_count_zero': 'zero',
                'table_count_one': 'one',
                'table_count_extra': 'more_than_two'}[case]
        if case == 'table_count_extra':
            assert result['extra_layout'] == 'reviewed_pair_unproved'
    else:
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


def test_l3_form_shape_refusal_is_measured_without_reading_business_content():
    from coretax_corporate import _observe_l3, CIT_SOURCE_URL
    from coretax_corporate_projection import L3_BUILD_DIGESTS, MAIN_SOURCE, VENDOR_SOURCE

    class Capture:
        def observe_component_lifetime(self, *, check_cancel=None):
            return {'same_document': True}

    class Count:
        def count(self):
            return 2

    class Form:
        def locator(self, selector):
            assert selector == 'table'
            return Count()

        def count(self):
            return 2  # Ambiguous form identity must refuse, not read rows.

    class Page:
        def __init__(self):
            self.calls = 0

        def evaluate(self, script, *args):
            self.calls += 1
            return {1: True, 2: L3_BUILD_DIGESTS[MAIN_SOURCE],
                    3: L3_BUILD_DIGESTS[VENDOR_SOURCE]}[self.calls]

    reason = {}
    assert _observe_l3(Page(), Form(), Capture(), L3_BUILD_DIGESTS[CIT_SOURCE_URL],
                       {}, 20, None, reason_out=reason) is None
    assert reason == {'reason': 'form_shape'}


@pytest.mark.parametrize('reason', [
    'request_shape', 'footer_request', 'grid_offset', 'lifetime_end',
])
def test_l3_synthetic_late_refusal_is_named_without_changing_source_admission(
        browser, tmp_path, monkeypatch, reason):
    from coretax_corporate import observe_forms
    from coretax_json import CORPORATE_L3_GRID_URL, CORPORATE_L3_FOOTER_URL
    from coretax_json_capture import DetailJsonCapture
    from l3_observer_fixture import Fixture, ASSET
    from test_corporate_l3_observer import open_selected
    from spt_desktop import diagnostics
    import support_json_corpus as corpus

    fixture = Fixture(browser, monkeypatch)
    try:
        with diagnostics.session(tmp_path / 'log', 'worker') as log:
            with DetailJsonCapture(fixture.context, fixture.page, fixture.record,
                                   corpus.SCOPE, tmp_path) as capture:
                page = open_selected(fixture, capture)
                if reason == 'lifetime_end':
                    original = capture.observe_component_lifetime
                    calls = []

                    def lifetime(*, check_cancel=None):
                        calls.append(True)
                        return original(check_cancel=check_cancel) if len(calls) == 1 else None

                    monkeypatch.setattr(capture, 'observe_component_lifetime', lifetime)
                else:
                    original = capture.request_observations
                    identity = fixture.record['record_id']

                    def observations():
                        existing = original()
                        if reason == 'request_shape':
                            malformed = {'method': 'POST', 'url': CORPORATE_L3_GRID_URL,
                                         'request_json': None}
                        elif reason == 'footer_request':
                            malformed = {'method': 'POST', 'url': CORPORATE_L3_FOOTER_URL,
                                         'request_json': {'ReturnSheetRecordId': identity,
                                                          'SyntheticExtra': True}}
                        else:
                            malformed = {'method': 'POST', 'url': CORPORATE_L3_GRID_URL,
                                         'request_json': {'ReturnSheetRecordId': identity, 'First': -1}}
                        return [*existing, malformed]

                    monkeypatch.setattr(capture, 'request_observations', observations)
                forms = observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                      approved_digest=fixture.pins[ASSET])
            assert log.flush()
        assert forms is None
        events = [row for row in records(tmp_path / 'log')
                  if row['event'] == 'corporate.observe_unavailable']
        assert len(events) == 1
        assert events[0]['corporate_observer_stage'] == 'l3'
        assert events[0]['corporate_l3_reason'] == reason
        assert fixture.unexpected == []
        assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('shape', ['zero', 'one', 'more_than_two'])
def test_l3_count_shape_diagnostics_accept_only_fixed_categories(tmp_path, shape):
    from spt_desktop import diagnostics
    secret = 'SYNTHETIC_TAXPAYER_IDENTIFIER_AND_DOM'
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        diagnostics.record('corporate.observe_unavailable',
                           corporate_observer_stage='l3',
                           corporate_l3_reason='table_count',
                           corporate_l3_table_shape=shape, body=secret, url=secret)
        diagnostics.record('corporate.observe_unavailable',
                           corporate_l3_table_shape=secret)
        assert log.flush()
    events = [r for r in records(tmp_path / 'log')
              if r['event'] == 'corporate.observe_unavailable']
    assert len(events) == 2
    assert events[0]['corporate_l3_table_shape'] == shape
    assert 'corporate_l3_table_shape' not in events[1]
    assert secret not in json.dumps(events)


@pytest.mark.parametrize('extra,expected', [
    ('<p-table><table style="display:none"><tbody></tbody></table></p-table>',
     'reviewed_pair_hidden_extra'),
    ('<p-table><table><tbody></tbody></table></p-table>',
     'reviewed_pair_visible_extra'),
    ('<rsh-citr-l3-grid1><p-table><table></table></p-table></rsh-citr-l3-grid1>',
     'reviewed_pair_visible_extra'),
])
def test_extra_l3_table_owner_classification_does_not_grant_admission(
        browser, extra, expected):
    from coretax_corporate import _l3_extra_table_layout
    page = browser.new_page()
    try:
        page.set_content('<rshshr-citr-l3-form>'
            '<rsh-citr-l3-grid1><ui-grid-offline><p-table><table></table>'
            '</p-table></ui-grid-offline></rsh-citr-l3-grid1>'
            '<rshshr-citr-l3-grid2><ui-grid><p-table><table></table>'
            '</p-table></ui-grid></rshshr-citr-l3-grid2>'
            + extra + '</rshshr-citr-l3-form>')
        assert _l3_extra_table_layout(page.locator('rshshr-citr-l3-form')) == expected
    finally:
        page.close()


def test_l3_pair_unproved_when_source_reviewed_owner_is_absent(browser):
    from coretax_corporate import _l3_extra_table_layout
    page = browser.new_page()
    try:
        page.set_content('<rshshr-citr-l3-form>'
            '<rsh-citr-l3-grid1><ui-grid-offline><p-table><table></table>'
            '</p-table></ui-grid-offline></rsh-citr-l3-grid1>'
            '<p-table><table></table></p-table>'
            '<p-table><table></table></p-table>'
            '</rshshr-citr-l3-form>')
        assert _l3_extra_table_layout(page.locator('rshshr-citr-l3-form')) == 'reviewed_pair_unproved'
    finally:
        page.close()


@pytest.mark.parametrize('kind', ['reviewed_pair_hidden_extra',
                                   'reviewed_pair_visible_extra', 'reviewed_pair_unproved'])
def test_l3_extra_owner_enum_never_logs_private_dom(tmp_path, kind):
    from spt_desktop import diagnostics
    secret='SYNTHETIC_PRIVATE_L3_DOM'
    with diagnostics.session(tmp_path / 'log', 'worker') as log:
        diagnostics.record('corporate.observe_unavailable',
                           corporate_observer_stage='l3',
                           corporate_l3_reason='table_count',
                           corporate_l3_extra_layout=kind,
                           dom=secret, body=secret, url=secret)
        diagnostics.record('corporate.observe_unavailable',
                           corporate_l3_extra_layout=secret)
        assert log.flush()
    events=[e for e in records(tmp_path / 'log')
            if e['event']=='corporate.observe_unavailable']
    assert len(events)==2
    assert events[0]['corporate_l3_extra_layout']==kind
    assert 'corporate_l3_extra_layout' not in events[1]
    assert secret not in json.dumps(events)


@pytest.mark.parametrize('extra,expected', [
    ('<rsh-citr-l3-grid1><table></table></rsh-citr-l3-grid1>', 'reviewed_grid_extra'),
    ('<div><table></table></div>', 'other_form_owner'),
    ('<rsh-citr-l3-grid1><table></table></rsh-citr-l3-grid1>'
     '<div><table></table></div>', 'mixed_owners'),
])
def test_l3_visible_extra_owner_stays_diagnostic_only(browser, extra, expected):
    from coretax_corporate import _l3_visible_extra_owner
    page=browser.new_page()
    try:
        page.set_content('<rshshr-citr-l3-form>'
            '<rsh-citr-l3-grid1><ui-grid-offline><p-table><table></table>'
            '</p-table></ui-grid-offline></rsh-citr-l3-grid1>'
            '<rshshr-citr-l3-grid2><ui-grid><p-table><table></table>'
            '</p-table></ui-grid></rshshr-citr-l3-grid2>'
            + extra + '</rshshr-citr-l3-form>')
        assert _l3_visible_extra_owner(page.locator('rshshr-citr-l3-form')) == expected
    finally:
        page.close()


def test_l3_extra_owner_diagnostic_is_bounded_and_private(tmp_path):
    from spt_desktop import diagnostics
    secret='SYNTHETIC_PRIVATE_CELLS_AND_TAXPAYER'
    with diagnostics.session(tmp_path/'log', 'worker') as log:
        diagnostics.record('corporate.observe_unavailable',
                           corporate_l3_extra_owner='other_form_owner',
                           raw_dom=secret, taxpayer=secret)
        diagnostics.record('corporate.observe_unavailable',
                           corporate_l3_extra_owner=secret)
        assert log.flush()
    events=[e for e in records(tmp_path/'log') if e['event']=='corporate.observe_unavailable']
    assert events[0]['corporate_l3_extra_owner']=='other_form_owner'
    assert 'corporate_l3_extra_owner' not in events[1]
    assert secret not in json.dumps(events)


def test_live_shaped_visible_extra_l3_keeps_json_hybrid_fail_closed(
        browser, tmp_path, monkeypatch):
    from coretax_corporate import observe_forms
    from coretax_json_capture import DetailJsonCapture
    from l3_observer_fixture import Fixture, ASSET
    from test_corporate_l3_observer import open_selected
    from spt_desktop import diagnostics
    import support_json_corpus as corpus

    fixture=Fixture(browser, monkeypatch, defect='visible-extra-form')
    try:
        with diagnostics.session(tmp_path/'log', 'worker') as log:
            with DetailJsonCapture(fixture.context, fixture.page, fixture.record,
                                   corpus.SCOPE, tmp_path) as capture:
                page=open_selected(fixture, capture)
                forms=observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                    approved_digest=fixture.pins[ASSET])
            assert log.flush()
        assert forms is None
        events=[e for e in records(tmp_path/'log')
                if e['event']=='corporate.observe_unavailable']
        assert len(events)==1
        assert events[0]['corporate_l3_reason']=='table_count'
        assert events[0]['corporate_l3_table_shape']=='more_than_two'
        assert events[0]['corporate_l3_extra_layout']=='reviewed_pair_visible_extra'
        assert events[0]['corporate_l3_extra_owner']=='other_form_owner'
        assert fixture.unexpected==[]
        assert page.evaluate('window.businessReads')==0
        assert page.evaluate('window.forbiddenClicks')==0
    finally:
        fixture.close()
