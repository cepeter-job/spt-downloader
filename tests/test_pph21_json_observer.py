"""Five-form value-free PPh21 observation; absent feature fails, never skips."""
import hashlib
import importlib
import importlib.util

import pytest

from coretax_json import JsonSafetyError
from masa_json_fixtures import SCOPE
from pph21_observer_fixture import (ARTICLE, BUILD, FIRST, FORMS, GRIDS, INDUK_CONTROLS,
                                    MAIN, TOTAL, browser, observed)


def feature(monkeypatch):
    name = 'coretax_pph21_observer'
    assert importlib.util.find_spec(name) is not None, 'PPh21 observer is not implemented'
    module = importlib.import_module(name)
    monkeypatch.setattr(module, 'BUILD_DIGESTS', {MAIN: hashlib.sha256(BUILD).hexdigest(),
                                               ARTICLE: hashlib.sha256(BUILD).hexdigest()})
    return module.observe_pph21_forms


def assert_no_values_or_actions(fixture):
    assert fixture.page.evaluate('window.valueReads') == 0
    assert fixture.page.evaluate('window.forbiddenClicks') == 0
    assert not fixture.unexpected


def test_fixture_itself_loads_and_captures_a_primary_without_product_observer(browser, tmp_path):
    with observed(browser, tmp_path) as (fixture, capture):
        assert len(fixture.page.locator('[data-main-panel]').all()) == 5
        assert fixture.page.locator('ui-grid').count() == 7
        assert len(capture.request_observations()) == 1
        assert_no_values_or_actions(fixture)


@pytest.mark.parametrize('expression', ["document.querySelector('input').value",
    "document.querySelector('input').checked", "document.querySelector('textarea').value",
    "document.querySelector('tbody td').textContent", "document.querySelector('tfoot td').innerText"])
def test_fixture_getter_traps_reject_attempted_business_value_reads(browser, tmp_path, expression):
    from playwright.sync_api import Error
    with observed(browser, tmp_path) as (fixture, capture):
        with pytest.raises(Error, match='DOM values forbidden'):
            fixture.page.evaluate('() => ' + expression)
        assert fixture.page.evaluate('window.valueReads') == 1
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert not fixture.unexpected


def test_complete_observation_five_forms_seven_grids(browser, tmp_path, monkeypatch):
    observe = feature(monkeypatch)
    with observed(browser, tmp_path) as (fixture, capture):
        forms = observe(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert forms is not None and [f['name'] for f in forms] == list(FORMS)
        grids = [table for form in forms for table in form['tables'] if 'endpoint' in table]
        assert [table['name'] for table in grids] == GRIDS
        posted = [event for event in capture.request_observations() if event['url'].endswith('-grid')]
        assert posted[0]['request_json']['First'] == FIRST
        for table in grids:
            assert [page['offset'] for page in table['pages']] == [0, FIRST]
            assert table['source_total'] == TOTAL
            assert all(page['sequences'] for page in table['pages'])
            if table['name'] in ('l1b-bpa1', 'l2-bpa1'):
                assert table['footer_spans'] == []
        induk = forms[0]
        assert induk['primary']['requests']
        assert induk['builds'] == {MAIN: hashlib.sha256(BUILD).hexdigest(), ARTICLE: hashlib.sha256(BUILD).hexdigest()}
        assert induk['locale'] == 'id-ID' and induk['timezone'] == 'Asia/Jakarta'
        controls = [c['field'] for c in induk['fields'] if c['field'] in INDUK_CONTROLS]
        assert controls == list(INDUK_CONTROLS)
        assert all('value' not in c for c in induk['fields'])
        assert_no_values_or_actions(fixture)
        assert capture.drain()['complete']


@pytest.mark.parametrize('defect', ['missing-form', 'extra-form', 'changed-build',
                                     'invalid-group', 'extra-ui-grid', 'missing-request'])
def test_unsupported_structure_never_becomes_native_coverage(browser, tmp_path, monkeypatch, defect):
    observe = feature(monkeypatch)
    with observed(browser, tmp_path, defect=defect) as (fixture, capture):
        assert observe(fixture.page, fixture.record, SCOPE, capture, max_pages=5) is None
        assert_no_values_or_actions(fixture)


@pytest.mark.parametrize('defect', ['foreign-request', 'unauthorized', 'forbidden'])
def test_identity_and_authorization_failures_never_become_dom_fallback(browser, tmp_path, monkeypatch, defect):
    observe = feature(monkeypatch)
    with observed(browser, tmp_path, defect=defect) as (fixture, capture):
        with pytest.raises(JsonSafetyError):
            observe(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert_no_values_or_actions(fixture)
