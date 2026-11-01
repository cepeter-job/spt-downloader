# Real Edge contracts: no DOM tax values, guessed requests or partial coverage.
import hashlib
import importlib
import json

import pytest
from playwright.sync_api import sync_playwright as sync_playwright

import coretax_browser as driver
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture as DetailJsonCapture
from masa_json_fixtures import SCOPE
from masa_observer_fixture import ASSETS, BUILD, FORMS, FRAME as FRAME, MAIN, Fixture as Fixture


from support_masa_native import browser as browser, observed, observer_module as observer_module


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('layout', ['direct', 'wrapped'])
def test_all_masa_tabs_bind_real_requests_without_reading_tax_values(browser, tmp_path, monkeypatch, tax, layout):
    with observed(browser, tmp_path, monkeypatch, tax, layout=layout) as (module, fixture, capture):
        forms = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert forms is not None
        assert [f['name'] for f in forms] == [f[0] for f in FORMS[tax]]
        assert forms[0]['fields'] == [{'field': 'FullName', 'label': 'NAME', 'group': 'IDENTITY', 'column_label': '', 'tag': 'INPUT'}]
        assert forms[0]['builds'] == {MAIN: hashlib.sha256(BUILD).hexdigest(), ASSETS[tax]: hashlib.sha256(BUILD).hexdigest()}
        assert forms[0]['timezone'] == 'Asia/Jakarta'
        assert forms[0]['locale'] == 'id-ID'
        assert forms[0]['primary']['requests']
        bindings = [t for f in forms for t in f['tables'] if 'endpoint' in t]
        assert len(bindings) == (6 if tax == 'PPN' else 5)
        for table in bindings:
            assert table['headers'] == ['No.', 'Document / Number', 'Document / Date']
            assert table['footer_spans'] == [[2, 1]]
            assert table['source_total'] == 12
            assert [p['offset'] for p in table['pages']] == [0, 10]
            assert all(p['sequences'] for p in table['pages'])
            events = {e['sequence']: e for e in capture.request_observations()}
            for page in table['pages']:
                for sequence in page['sequences']:
                    assert events[sequence]['request_json'] == page['request_json']
                    assert events[sequence]['url'] == table['endpoint']
        if tax == 'PPh Unifikasi':
            assert forms[0]['tables'][0]['name'] == 'income-taxes'
            assert forms[0]['tables'][0]['headers'] == ['No.', 'DETAIL']
        if tax == 'PPN':
            source = forms[-1]['tables'][0]['footer_source']
            assert source['endpoint'].endswith('/loadndvat/lc-grid/footer')
            assert len(source['requests']) == 1
            footer_request = source['requests'][0]
            assert footer_request['request_json'] == {
                'ReturnSheetRecordId': '00000000-0000-4000-8000-000000000001', 'IsNormalVAT': True}
            assert footer_request['sequences']
            events = {e['sequence']: e for e in capture.request_observations()}
            for sequence in footer_request['sequences']:
                assert events[sequence]['url'] == source['endpoint']
                assert events[sequence]['request_json'] == footer_request['request_json']
        assert 'TRAP' not in json.dumps(forms)
        assert fixture.page.evaluate('window.valueReads') == 0
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert not fixture.unexpected
        assert capture.drain()['complete']


@pytest.mark.parametrize('defect', ['changed-build', 'changed-main', 'missing-form', 'extra-form',
                                    'duplicate-form', 'extra-table', 'missing-request', 'filtered',
                                    'missing-footer', 'wrong-footer-kind', 'untyped-footer-kind'])
def test_unknown_or_incomplete_structure_never_claims_observed_coverage(browser, tmp_path, monkeypatch, defect):
    if defect in {'missing-form', 'extra-form', 'duplicate-form'}:
        # These catalogs stay invalid; exercise the real readiness rejection
        # without spending the production deadline waiting for a repair.
        monkeypatch.setattr(driver, 'DETAIL_READY_TIMEOUT', 0.05)
    with observed(browser, tmp_path, monkeypatch, defect=defect) as (module, fixture, capture):
        assert module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5) is None
        assert fixture.page.evaluate('window.forbiddenClicks') == 0


@pytest.mark.parametrize('defect', ['foreign-request', 'unauthorized'])
@pytest.mark.parametrize('unknown_build', [False, True])
def test_source_contradictions_fail_closed_even_without_build_eligibility(browser, tmp_path, monkeypatch, defect, unknown_build):
    with observed(browser, tmp_path, monkeypatch, defect=defect) as (module, fixture, capture):
        if unknown_build:
            monkeypatch.setitem(module.BUILD_DIGESTS, MAIN, '0' * 64)
        with pytest.raises(JsonSafetyError):
            module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)


def test_page_budget_cannot_certify_incomplete_traversal(browser, tmp_path, monkeypatch):
    with observed(browser, tmp_path, monkeypatch) as (module, fixture, capture):
        assert module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=1) is None


def test_cancellation_propagates_instead_of_fallback(browser, tmp_path, monkeypatch):
    with observed(browser, tmp_path, monkeypatch) as (module, fixture, capture):
        def stop():
            raise driver.CaptureCancelled()
        with pytest.raises(driver.CaptureCancelled):
            module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, check_cancel=stop)


@pytest.mark.parametrize('defect', ['nested-panel-target', 'duplicate-panel-target'])
@pytest.mark.parametrize('layout', ['direct', 'wrapped'])
def test_aria_controls_must_identify_one_panel_owned_by_the_main_view(browser, tmp_path, monkeypatch, defect, layout):
    with observed(browser, tmp_path, monkeypatch, defect=defect, layout=layout) as (module, fixture, capture):
        if defect == 'nested-panel-target':
            # The owned panel is already present; a nested target cannot become its owner.
            assert fixture.page.locator('[data-main-panel]#outer0').count() == 1
            assert fixture.page.locator('[id="p0"]').count() == 1
            monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
        assert module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5) is None
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert fixture.page.evaluate('window.valueReads') == 0


def test_foreign_footer_request_cannot_hide_behind_final_tab_or_fallback(browser, tmp_path, monkeypatch):
    with observed(browser, tmp_path, monkeypatch, defect='foreign-footer') as (module, fixture, capture):
        with pytest.raises(JsonSafetyError):
            module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
