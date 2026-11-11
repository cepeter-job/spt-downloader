"""Real synthetic SPA/history/held/export seam. Source-only RED until hosted CI."""
from copy import deepcopy

import pytest
from openpyxl import load_workbook

import coretax
import coretax_corporate as observer
import coretax_browser as driver
from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l7_observer_fixture import Fixture, mutate, churn
from l1d_observer_fixture import ASSET
from test_corporate_l1d_observer import open_selected
from test_corporate_l7_negative_native import ROUTE, CHAIN
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


def observe(fixture, capture):
    return observer.observe_forms(fixture.page, fixture.record, corpus.SCOPE, capture,
                                  approved_digest=fixture.pins[ASSET])


def adapt(fixture, capture, forms):
    return adapt_corporate_detail(list(capture.iter_bodies()), fixture.record, corpus.SCOPE, forms)


@pytest.mark.parametrize('large_main', [False, True])
@pytest.mark.parametrize('duplicate_rows', [False, True])
def test_actual_spa_negative_observer_held_replay_and_reopened_workbook(
        browser, tmp_path, monkeypatch, large_main, duplicate_rows):
    fixture = Fixture(browser, monkeypatch, large_main=large_main, duplicate_rows=duplicate_rows)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe(fixture, capture)
            assert forms is not None
            l7, = [form for form in forms if form['name'] == 'L7']
            assert l7['projection']['kind'] == 'corporate-l7-v1'
            strong = l7['raw_negative_projection']
            assert strong['builds'] == fixture.pins
            assert strong['tables'][0]['owner_chain'] == CHAIN
            page.get_by_role('tab', name='Induk', exact=True).click()
            # Final sealing must not require L7 to remain the active panel.
            saved = capture.drain()
            assert saved['complete'] and saved['corporate_l7_lifetime']['stable_table'] is True
            packets = list(capture.iter_bodies())
            assert len(packets) == 1 and packets[0]['body'] == fixture.raw
            before = deepcopy((packets, forms))
            result = adapt_corporate_detail(packets, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'], result['reason']
            fixture.record['detail_url'] = ROUTE
            held = checkpoint_bodies(tmp_path, saved, fixture.record, corpus.SCOPE)
            replay = adapt_corporate_detail(held, fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
            assert (packets, forms) == before
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
        # Retain only the independently proved L7 section for this workbook seam;
        # this fixture grants no whole-record/PDF/live acceptance.
        section, = [s for s in result['sections'] if s['name'] == 'L7']
        fixture.record.update(capture_complete=True, sections=[section])
        fixture.record['detail_source'] = {'version': 1, 'requested': 'json-first',
            'used': 'json', 'reason': 'native_verified', 'capture': saved}
        checkpoint = tmp_path / 'returns' / '0001.json'
        driver._atomic_checkpoint(checkpoint, fixture.record)
        reusable = driver.read_detail_checkpoint(checkpoint, fixture.record, corpus.SCOPE, detail_source='json-first')
        assert reusable['detail_source']['capture'] == saved
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        folder = tmp_path / 'export'
        coretax.save_output(run, folder, json_source=tmp_path)
        coretax.verify_outputs(run, folder)
        published = checkpoint_bodies(folder, saved, fixture.record, corpus.SCOPE,
            published=True, output_layout=run['json_output_layout'])
        assert published == packets
        replay = adapt_corporate_detail(published, fixture.record, corpus.SCOPE, forms)
        assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
        copied = deepcopy(run)
        coretax.save_output(copied, tmp_path / 'reexport', json_source=folder)
        coretax.verify_outputs(copied, tmp_path / 'reexport')
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        book = load_workbook(folder / name)
        try:
            sheet = book['L7']
            assert sheet['B3'].value == '02023' and sheet['B4'].value == '2025'
            assert sheet['C3'].value == 12345 and sheet['C4'].value == -1234
            assert sheet['C4'].data_type == 'n' and 'Rp' in sheet['C4'].number_format
            assert '0.00' not in sheet['C4'].number_format
            footer = 7 if duplicate_rows else 5
            assert sheet.cell(footer, 1).value == 'JUMLAH' and sheet.max_row == footer
            assert [sheet.cell(footer, col).value for col in range(4, 10)] == (
                [400, 800, 1200, 1600, 2000, 2400] if duplicate_rows else [200, 400, 600, 800, 1000, 1200])
            if duplicate_rows:
                assert [(sheet.cell(row, 2).value, sheet.cell(row, 3).value) for row in (4, 5, 6)] == [
                    ('2025', -1234), ('2025', 0), ('02025', -7)]
        finally: book.close()
    finally: fixture.close()


@pytest.mark.parametrize('selector', ['rshshr-corporate-income-tax-return', 'rshshr-citr-l7-form',
    'rsh-citr-l7-grid1', 'rsh-citr-l7-grid1 p-table', 'rsh-citr-l7-grid1 table', '#l7-wrapper'])
@pytest.mark.parametrize('mode', ['remove-reinsert', 'replace', 'duplicate', 'nested-duplicate'])
def test_real_history_remembers_transient_identity_changes(browser, tmp_path, monkeypatch, selector, mode):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe(fixture, capture)
            assert forms is not None and any('raw_negative_projection' in form for form in forms)
            mutate(page, selector, mode)
            # Unknown ordinary wrapper duplicates are harmless. A duplicated
            # wrapper here contains the retained grid/table and is not ordinary.
            with pytest.raises(JsonSafetyError): capture.drain()
            assert page.evaluate('window.businessReads') == 0
    finally: fixture.close()


@pytest.mark.parametrize('selector', ['rshshr-citr-l7-form', 'rsh-citr-l7-grid1', 'rsh-citr-l7-grid1 table'])
def test_hidden_child_history_is_not_first_armed_when_l7_is_activated(browser, tmp_path, monkeypatch, selector):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert not page.locator('rshshr-citr-l7-form').is_visible()
            mutate(page, selector, 'nested-duplicate')
            with pytest.raises(JsonSafetyError): observe(fixture, capture)
    finally: fixture.close()


@pytest.mark.parametrize('change', ['route-detour', 'same-url-new-document'])
def test_real_l7_strong_offer_does_not_weaken_route_or_document_fatality(browser, tmp_path, monkeypatch, change):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert observe(fixture, capture) is not None
            if change == 'route-detour':
                page.evaluate('''()=>{const url=location.href;
                    history.pushState({},'',url+'&synthetic=detour');history.pushState({},'',url);}''')
            else:
                fixture.context.route(ROUTE, lambda route: route.fulfill(content_type='text/html',
                    body='<html><body>'+fixture.detail()+'</body></html>'))
                page.goto(ROUTE, wait_until='domcontentloaded')
            with pytest.raises(JsonSafetyError): capture.drain()
    finally: fixture.close()


def test_same_turn_removed_wrapper_cannot_lend_historical_child_ownership(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert observe(fixture, capture) is not None
            mutate(page, 'rsh-citr-l7-grid1', 'removed-wrapper-move-child')
            with pytest.raises(JsonSafetyError): capture.drain()
    finally: fixture.close()


@pytest.mark.parametrize('detach_after', [False, True])
def test_more_than_4096_unrelated_l3_mutations_do_not_spend_l7_budget(
        browser, tmp_path, monkeypatch, detach_after):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            churn(page)  # Before L7 is activated: hidden L7 still tracked.
            forms = observe(fixture, capture)
            assert any('raw_negative_projection' in form for form in forms)
            churn(page)  # After both inspected boundaries.
            assert capture.observe_l7_lifetime() is not None
            if detach_after:
                mutate(page, 'rsh-citr-l7-grid1 table', 'remove-reinsert')
                with pytest.raises(JsonSafetyError): capture.drain()
            else:
                saved = capture.drain()
                assert saved['complete'] and 'corporate_l7_lifetime' in saved
                assert adapt(fixture, capture, forms)['eligible']
            assert page.evaluate('window.businessReads') == 0
    finally: fixture.close()


@pytest.mark.parametrize('negative', [False, True])
@pytest.mark.parametrize('late', ['budget', 'rpc-unavailable'])
def test_late_optional_history_unavailability_preserves_nonnegegative_v1_only(
        browser, tmp_path, monkeypatch, negative, late):
    fixture = Fixture(browser, monkeypatch, negative=negative)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe(fixture, capture)
            assert any('raw_negative_projection' in form for form in forms)
            if late == 'budget':
                page.evaluate('''()=>{
                    const form=document.querySelector('rshshr-citr-l7-form');
                    for(let i=0;i<4200;i++)form.append(document.createElement('span'));
                }''')
            else:
                original = capture._l7_history.evaluate
                def unavailable(script, *args):
                    if 'sample' in script: raise RuntimeError('SYNTHETIC RPC unavailable')
                    return original(script, *args)
                monkeypatch.setattr(capture._l7_history, 'evaluate', unavailable)
            saved = capture.drain()
            assert saved['complete'] and 'corporate_l7_lifetime' not in saved
            result = adapt(fixture, capture, forms)
            assert result['eligible'] is (not negative)
            if not negative:
                report, = result['provenance']['projections']
                assert report['kind'] == 'corporate-l7-v1'
    finally: fixture.close()


@pytest.mark.parametrize('defect', ['hidden-initial-root', 'hidden-initial-l7', 'vendor-pin',
    'corporate-fetch-only', 'corporate-preload-only', 'main-fetch-only', 'main-preload-only',
    'vendor-fetch-only', 'vendor-preload-only', 'table-outside-p-table', 'foreign-form', 'foreign-grid'])
def test_optional_offer_refuses_unproved_history_providers_or_chain_without_poisoning_v1(
        browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, defect=defect, negative=False)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe(fixture, capture)
            assert forms is not None
            assert not any('raw_negative_projection' in form for form in forms)
            assert capture.drain()['complete']
            assert adapt(fixture, capture, forms)['eligible']
            assert page.evaluate('window.businessReads') == 0
    finally: fixture.close()
