# Real Edge contracts: no DOM tax values, guessed requests or partial coverage.
from contextlib import contextmanager
import hashlib
import importlib
import importlib.util
import json

import pytest
from playwright.sync_api import sync_playwright

from coretax_browser import CaptureCancelled
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture
from masa_json_fixtures import SCOPE
from masa_observer_fixture import ASSETS, BUILD, FORMS, FRAME, MAIN, Fixture


def observer_module():
    assert importlib.util.find_spec('coretax_masa_observer'), 'Value-free Masa observer is not implemented'
    module = importlib.import_module('coretax_masa_observer')
    assert callable(getattr(module, 'observe_masa_forms', None)), 'Masa traversal is not implemented'
    return module


@pytest.fixture(scope='module')
def browser():
    with sync_playwright() as playwright:
        instance = playwright.chromium.launch(channel='msedge', headless=True)
        yield instance
        instance.close()


@contextmanager
def observed(browser, tmp_path, monkeypatch, tax='PPN', *, defect=None):
    module = observer_module()
    monkeypatch.setattr(module, 'BUILD_DIGESTS', {
        MAIN: hashlib.sha256(BUILD).hexdigest(),
        **{url: hashlib.sha256(BUILD).hexdigest() for url in ASSETS.values()},
    })
    fixture = Fixture(browser, tax, defect=defect)
    try:
        fixture.page.goto(fixture.record['list_url'])
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, SCOPE, tmp_path) as capture:
            fixture.page.goto(FRAME)
            capture.bind_detail_page(fixture.page)
            fixture.page.wait_for_timeout(200)
            yield module, fixture, capture
    finally:
        fixture.context.close()


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_all_masa_tabs_bind_real_requests_without_reading_tax_values(browser, tmp_path, monkeypatch, tax):
    with observed(browser, tmp_path, monkeypatch, tax) as (module, fixture, capture):
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
        assert 'TRAP' not in json.dumps(forms)
        assert fixture.page.evaluate('window.valueReads') == 0
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert not fixture.unexpected
        assert capture.drain()['complete']


@pytest.mark.parametrize('defect', ['changed-build', 'changed-main', 'missing-form', 'extra-form',
                                    'duplicate-form', 'extra-table', 'missing-request', 'filtered'])
def test_unknown_or_incomplete_structure_never_claims_observed_coverage(browser, tmp_path, monkeypatch, defect):
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
            raise CaptureCancelled()
        with pytest.raises(CaptureCancelled):
            module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, check_cancel=stop)
