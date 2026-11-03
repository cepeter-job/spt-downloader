"""Synthetic regressions for the November L3/MPN capture obstacles; runners only."""
import html
import re
import time

import pytest
from playwright.sync_api import Locator, ElementHandle

import coretax_browser as driver
import coretax_corporate as corporate
from coretax_corporate import observe_forms
from coretax_corporate_projection import _L3_CAPTIONS
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from coretax_mpn_browser import collect_mpn
from coretax_mpn_ui import AccountingUI
from l3_observer_fixture import Fixture, ASSET
from support_isolated_browser import browser as browser, context as context
from test_corporate_dom_page_size import fixture as dom_fixture, assert_rows
from test_corporate_l3_observer import open_selected
from test_mpn import scope_run
from test_mpn_capture_browser import portal
import support_json_corpus as corpus


class StandaloneFixture(Fixture):
    variant = 'valid'

    def detail(self):
        markup = super().detail()
        markup = markup.replace('<p-accordion>', '<form><p-accordion>').replace(
            '</p-accordion>', '</p-accordion></form>')
        markup = markup.replace('p-accordiontab', 'p-panel').replace(
            'p-accordion-header-text', 'p-panel-title')
        # The pinned PrimeNG paginator uses type=button. The legacy fixture
        # had no enclosing form and omitted it; keep this actual-shaped form
        # from turning a read-only paginator action into a synthetic submit.
        markup = markup.replace('<button class="p-paginator-', '<button type="button" class="p-paginator-')
        controls = ('RefundDeductionCreditOverseas', 'TotalIncomeTaxPaidOverseas')
        rows = ''.join('<tr><th colspan="10" width="1099">' + html.escape(caption)
            + '</th><th width="116"><p-inputnumber formcontrolname="' + name
            + '"><input id="' + name + '" value="SYNTHETIC BUSINESS BAIT">'
            '</p-inputnumber></th></tr>' for name, caption in zip(controls, _L3_CAPTIONS))
        standalone = ('<p-table responsivelayout="scroll"><div class="p-datatable '
            'scaled-datatable p-datatable-sm p-datatable-gridlines p-datatable-striped '
            'p-datatable-responsiveness"><table><thead>' + rows
            + '</thead><tbody></tbody></table></div></p-table>')
        changes = {
            'caption': lambda s: s.replace(html.escape(_L3_CAPTIONS[0]), 'UNKNOWN HEADER'),
            'span': lambda s: s.replace('colspan="10"', 'colspan="9"', 1),
            'control': lambda s: s.replace('formcontrolname="RefundDeductionCreditOverseas"',
                                         'formcontrolname="Unknown"'),
            'body': lambda s: s.replace('<tbody></tbody>', '<tbody><tr><td>BAIT</td></tr></tbody>'),
            'duplicate': lambda s: s + s,
            'nested-grid': lambda s: '<ui-grid>' + s + '</ui-grid>',
        }
        standalone = changes.get(self.variant, lambda s: s)(standalone)
        markup = re.sub(r'(<rsh-citr-l3-grid1>.*?</rsh-citr-l3-grid1>)',
                        lambda m: '<div style="overflow-x:auto">' + m[0] + '<br>'
                        + standalone + '</div>', markup, count=1)
        if self.variant == 'foreign-owner':
            markup = markup.replace('<br>' + standalone, '')
            markup = markup.replace('</form>', standalone + '</form>')
        return markup


def test_source_shaped_standalone_l3_is_native_and_replays_original_bytes(browser, tmp_path, monkeypatch):
    from spt_desktop import diagnostics
    from test_diagnostics import records
    owned = StandaloneFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(owned.context, owned.page, owned.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(owned, capture)
            with diagnostics.session(tmp_path/'diagnostics', 'worker') as log:
                forms = observe_forms(page, owned.record, corpus.SCOPE, capture, approved_digest=owned.pins[ASSET])
                assert log.flush()
            reasons = [{k: r[k] for k in ('corporate_observer_stage', 'corporate_l3_reason', 'error') if k in r}
                       for r in records(tmp_path/'diagnostics') if r['event']=='corporate.observe_unavailable']
            assert forms is not None, ('Source-proven standalone L3 table was refused', reasons)
            assert forms[1]['projection']['standalone_layout'] == 'overseas-controls-v1'
            manifest = capture.drain()
            result = adapt_corporate_detail(capture.iter_bodies(), owned.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            owned.record['detail_url'] = page.url
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, owned.record, corpus.SCOPE),
                                           owned.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert owned.unexpected == []
    finally:
        owned.close()


@pytest.mark.parametrize('variant', ['caption', 'span', 'control', 'body', 'duplicate',
                                    'nested-grid', 'foreign-owner'])
def test_unproved_standalone_l3_keeps_whole_record_fallback(browser, tmp_path, monkeypatch, variant):
    monkeypatch.setattr(StandaloneFixture, 'variant', variant)
    owned = StandaloneFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(owned.context, owned.page, owned.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(owned, capture)
            assert observe_forms(page, owned.record, corpus.SCOPE, capture,
                                 approved_digest=owned.pins[ASSET]) is None
            assert page.evaluate('window.businessReads') == 0
    finally:
        owned.close()


def test_standalone_l3_change_between_passes_cannot_grant_native(browser, tmp_path, monkeypatch):
    original = corporate._turn_grid
    owned = StandaloneFixture(browser, monkeypatch)
    def turn(page, *args):
        result = original(page, *args)
        page.locator('p-inputnumber[formcontrolname=RefundDeductionCreditOverseas]').evaluate(
            "e=>e.setAttribute('formcontrolname','Changed')")
        return result
    monkeypatch.setattr(corporate, '_turn_grid', turn)
    try:
        with DetailJsonCapture(owned.context, owned.page, owned.record, corpus.SCOPE, tmp_path) as capture:
            open_selected(owned, capture)
            assert observe_forms(owned.page, owned.record, corpus.SCOPE, capture,
                                 approved_digest=owned.pins[ASSET]) is None
            assert owned.page.evaluate('window.businessReads') == 0
    finally:
        owned.close()


@pytest.mark.parametrize('marker', [None, '', True, 'unreviewed-layout'])
def test_explicit_unknown_standalone_replay_marker_is_unsupported(marker):
    from test_corporate_l3_native import packets, bindings, selected
    observed = bindings()
    observed[1]['projection']['standalone_layout'] = marker
    result = adapt_corporate_detail(packets(), selected(), corpus.SCOPE, observed)
    assert not result['eligible'] and not result['sections']


@pytest.mark.parametrize('remaining_budget', [None, .3])
def test_clear_date_dispatch_can_wait_above_one_second_without_repeating_click(
        browser, tmp_path, monkeypatch, remaining_budget):
    original = Locator.click
    state = {'trial': False, 'actual': 0}
    original_clear = AccountingUI._clear_initial_transaction_date
    def clear(owned, *args):
        state['owned'] = owned
        if remaining_budget is not None:
            # The remaining budget already exists when _click_ready enters;
            # do not replace its retained deadline after a readiness trial.
            owned.preparation_deadline = time.monotonic()+remaining_budget
        return original_clear(owned, *args)
    monkeypatch.setattr(AccountingUI, '_clear_initial_transaction_date', clear)
    with portal(browser, monkeypatch, default_stuck=True, transaction_date_clear='valid') as (page, metrics):
        def click(locator, *args, **kwargs):
            if locator.get_attribute('aria-label', timeout=1000) != 'Clear date':
                return original(locator, *args, **kwargs)
            if kwargs.get('trial'):
                result = original(locator, *args, **kwargs)
                if not state['trial']:
                    state['trial'] = True
                    locator.evaluate('''e => {
                        const cover=document.createElement('div');
                        e.parentElement.style.position='relative';
                        cover.style.cssText='position:absolute;z-index:99999;inset:0';
                        e.parentElement.append(cover);setTimeout(()=>cover.remove(),1700);
                    }''')
                return result
            state['actual'] += 1
            return original(locator, *args, **kwargs)
        monkeypatch.setattr(Locator, 'click', click)
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        if remaining_budget is None:
            assert state['trial'] and state['actual'] == 1
            assert run['mpn']['status'] == 'COMPLETE', 'One-second clear dispatch truncated preparation'
            assert page.evaluate('window.syntheticDateClicks') == 1
            assert page.evaluate('window.syntheticSearchClicks') == 2
            assert len(metrics['detail']) == 1
        else:
            assert state['actual'] <= 1
            assert run['mpn']['status'] == 'PARTIAL' and not run['complete']
            assert page.evaluate('window.syntheticDateClicks') == 0
            assert page.evaluate('window.syntheticSearchClicks') == 1
            assert metrics['detail'] == []


def test_owned_dom_cursor_combines_idle_and_snapshot_without_separate_wait_rpc(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = dom_fixture(page, total=601, selected=250)
    original = driver.wait_idle
    advanced_waits = []
    def wait(p):
        if p.evaluate('moves'):
            advanced_waits.append(True)
        return original(p)
    monkeypatch.setattr(driver, 'wait_idle', wait)
    result = driver.capture_table(page, table, 1, 1000, max_page_size=250)
    assert_rows(result, 601)
    assert page.evaluate('moves') == 2
    assert not advanced_waits, 'Advanced owned pages still use separate idle RPCs'
    page.close()


def test_owned_snapshot_waits_for_loading_and_settling_before_reading_rows(context):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = dom_fixture(page, total=601, selected=250)
    page.evaluate('''() => {
        const next=document.querySelector('.p-paginator-next'), original=next.onclick;
        next.onclick=function(event){
            const result=original.call(this,event), overlay=document.createElement('div');
            overlay.className='p-blockui';overlay.style.cssText='width:20px;height:20px';
            document.body.append(overlay);window.removedAt=null;
            setTimeout(()=>{overlay.remove();window.removedAt=performance.now()},300);
            return result;
        };
    }''')
    result = driver.capture_table(page, table, 1, 1000, max_page_size=250)
    assert_rows(result, 601)
    assert page.evaluate('performance.now()-removedAt') >= 175
    assert page.evaluate('moves') == 2
    page.close()


def test_snapshot_pending_allows_stop_without_another_paginator_click(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = dom_fixture(page, total=601, selected=250)
    page.evaluate('''() => document.querySelector('.p-paginator-next').addEventListener('click',()=>{
        const overlay=document.createElement('div');overlay.className='p-blockui';
        overlay.style.cssText='width:20px;height:20px';document.body.append(overlay);
    })''')
    original = ElementHandle.evaluate
    state = {'pending': False}
    def evaluated(handle, expression, arg=None):
        result = original(handle, expression, arg)
        if expression == driver.TABLE_VERIFIED_JS and isinstance(result, dict) and result.get('pending'):
            state['pending'] = True
        return result
    def stop():
        if state['pending']:
            raise driver.CaptureCancelled()
    monkeypatch.setattr(ElementHandle, 'evaluate', evaluated)
    original_idle = driver.wait_idle
    def idle(p):
        if p.evaluate('moves'):
            pytest.fail('Owned cursor used an uninterruptible separate idle wait')
        return original_idle(p)
    monkeypatch.setattr(driver, 'wait_idle', idle)
    with pytest.raises(driver.CaptureCancelled):
        driver.capture_table(page, table, 1, 1000, max_page_size=250, check_cancel=stop)
    assert state['pending'] and page.evaluate('moves') == 1
    page.close()


def test_pending_snapshot_cannot_refresh_original_deadline(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = dom_fixture(page, total=601, selected=250)
    page.evaluate('''() => document.querySelector('.p-paginator-next').addEventListener('click',()=>{
        const overlay=document.createElement('div');overlay.className='p-blockui';
        overlay.style.cssText='width:20px;height:20px';document.body.append(overlay);
    })''')
    monkeypatch.setattr(driver, 'TABLE_CAPTURE_BUDGET_SECONDS', 1.8)
    started = time.monotonic()
    result = driver.capture_table(page, table, 1, 1000, max_page_size=250)
    assert time.monotonic()-started < 5
    assert result['body_row_count'] == 250 and result['pages'] == 1
    assert result['warning'] == 'Table capture elapsed budget exceeded'
    assert not result['complete'] and page.evaluate('moves') == 1
    page.close()


def test_snapshot_cannot_refresh_an_expired_overlay_wait_deadline(context, monkeypatch):
    page = context.new_page()
    page.route('**/*', lambda route: route.abort())
    table = dom_fixture(page, total=601, selected=250)
    original = ElementHandle.evaluate
    def expired(handle, expression, arg=None):
        if expression == driver.TABLE_VERIFIED_JS:
            arg.evaluate('c=>{c.idleDeadline=performance.now()-1}')
        return original(handle, expression, arg)
    monkeypatch.setattr(ElementHandle, 'evaluate', expired)
    result = driver.capture_table(page, table, 1, 1000, max_page_size=250)
    assert not result['complete']
    assert result['warning'] == 'Table DOM read timed out after pagination'
    assert result['body_row_count'] == 250 and page.evaluate('moves') == 1
    page.close()
