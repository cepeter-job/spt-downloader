"""Real owned-SPA observer, custody and saved export; runners only."""
from copy import deepcopy
import hashlib

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
from coretax_corporate import observe_forms
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture, ASSET
from test_json_hybrid_native import browser
from test_corporate_l1d_native import DETAIL
import support_json_corpus as corpus


def open_selected(fixture, capture):
    page, popup = driver.open_return_readonly(fixture.page, fixture.page.locator('tbody tr'),
        corpus.TAXPAYER_ID, corpus.RECORD_ID, json_capture=capture)
    assert page is fixture.page and popup is False
    page.wait_for_function('window.primaryDone===true')
    assert page.locator('#panel-0').is_visible()
    assert page.locator('rshshr-citr-main-form').is_visible()
    return page


@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
@pytest.mark.parametrize('migrated', [False, True])
def test_actual_owned_spa_observer_to_custody_native_checkpoint_and_saved_export(
        browser, tmp_path, monkeypatch, model, migrated):
    fixture = Fixture(browser, monkeypatch, model=model, migrated=migrated)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms is not None and [f['name'] for f in forms] == ['Induk', 'L1-D']
            proof = forms[1]['projection']
            assert proof['kind'] == 'corporate-l1d-v1' and proof['builds'] == fixture.pins
            assert [t['component'] for t in proof['tables']] == [f'rsh-citr-l1d-grid{i}' for i in (1, 2, 3)]
            assert [t['source_structure'] for t in proof['tables']] == [
                {'form': 'L1-D', 'component': f'rsh-citr-l1d-grid{i}',
                 'groups': ['A. LAPORAN LABA RUGI' if i == 1 else 'B. LAPORAN POSISI KEUANGAN']}
                for i in (1, 2, 3)]
            manifest = capture.drain()
            assert manifest['complete'] and manifest['component_lifetime']['same_document'] is True
            bodies = list(capture.iter_bodies())
            assert len(bodies) == 1 and bodies[0]['body'] == fixture.raw
            before = deepcopy((bodies, forms, fixture.record))
            result = adapt_corporate_detail(bodies, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            assert (bodies, forms, fixture.record) == before
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections']
            assert fixture.page.evaluate('window.businessReads') == 0
            assert fixture.page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        coretax.verify_outputs(run, tmp_path / 'export')
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        workbook = load_workbook(tmp_path / 'export' / name)
        try:
            assert workbook['L1-D']['A20'].value == '5322' and workbook['L1-D']['C20'].value == 77
            assert workbook['L1-D']['J37'].value == (13 if migrated else 0)
            assert workbook['L1-D']['A98'].value == '3300'
        finally:
            workbook.close()
        report, = [r for r in run['template_mapping'] if r['form'] == 'L1-D']
        assert report['complete'] and report['unmapped_rows'] == report['unmapped_tables'] == 0
        assert fixture.unexpected == []
        for url, raw in fixture.assets.items():
            assert fixture.requests.count((url, 'GET')) == 2
            assert hashlib.sha256(raw).hexdigest() == fixture.pins[url]
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['external-context', 'vendor-pin', 'owner', 'header',
    'duplicate-owner', 'hidden-owner', 'non-services', 'missing-5322', 'wrong-group', 'misplaced-grid',
    'corporate-fetch-only', 'corporate-preload-only', 'main-fetch-only', 'main-preload-only',
    'vendor-fetch-only', 'vendor-preload-only', 'financial-wrapper-sibling', 'table-outside-p-table'])
def test_unproved_live_l1d_structure_or_source_retains_whole_record_fallback(
        browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            if defect == 'hidden-owner':
                # This fixture is statically malformed; preserve the production readiness budget.
                assert page.locator('rshshr-citr-l1d-form').get_attribute('style') == 'display:none'
                monkeypatch.setattr(driver, 'DETAIL_PANEL_TIMEOUT', 2)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            manifest = capture.drain()
            assert manifest['complete']
            result = adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms or [])
            assert not result['eligible'] and result['sections'] == []
            assert not result['coverage']['complete']
            assert fixture.page.evaluate('window.businessReads') == 0
            assert fixture.page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
            if fixture.non_script is not None:
                assert fixture.page.evaluate('url=>[...document.scripts].some(s=>s.src===url)',
                                            fixture.non_script[0]) is False
    finally:
        fixture.close()


def test_live_l1d_stop_remains_cancellation_after_owned_view(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            def cancel():
                raise driver.CaptureCancelled('SYNTHETIC STOP')
            with pytest.raises(driver.CaptureCancelled):
                observe_forms(page, fixture.record, corpus.SCOPE, capture,
                    approved_digest=fixture.pins[ASSET], check_cancel=cancel)
            assert not list(tmp_path.rglob('manifest.json'))
        assert capture._component_document is None
    finally:
        fixture.close()


def test_fixture_rejects_business_text_reads_through_enclosing_elements(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            page.evaluate('show(1)')
            for selector in ('rsh-citr-l1d-grid1 table', 'rsh-citr-l1d-grid1 tfoot', '#panel-1'):
                for property_name in ('innerText', 'textContent'):
                    assert page.locator(selector).evaluate('''(e, key) => {
                        try { void e[key]; return false; } catch (_) { return true; }
                    }''', property_name)
            assert page.evaluate('window.businessReads') == 6
            assert page.locator('rsh-citr-l1d-grid1 th').first.inner_text() == 'KODE AKUN'
            assert page.evaluate('window.businessReads') == 6
    finally:
        fixture.close()
