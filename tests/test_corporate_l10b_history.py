"""Own L10-B continuous history and unchanged held original bytes (CI only)."""
from copy import deepcopy
import hashlib
import json

import pytest
from playwright.sync_api import sync_playwright

import coretax_json_capture as capture_module
from coretax_json import JsonSafetyError
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import exchange
from test_corporate_component_lifetime import setup, selected, begin, navigate, LIST, DETAIL, SCOPE
from test_corporate_l7_history import History, Element


def history_setup():
    context, page = setup()
    make = page.evaluate_handle
    history = History()
    def document(script):
        handle = make(script)
        handle.evaluate_handle = lambda source: history if 'corporate-l10b-history' in source else None
        return handle
    page.evaluate_handle = document
    return context, page, history


def boundaries(capture):
    elements = [Element() for _ in range(3)]
    assert capture.bind_l10b_structure(*elements, phase='start')
    assert capture.bind_l10b_structure(*elements, phase='end')
    assert all(e.disposed for e in elements)
    return capture.observe_l10b_lifetime()


def test_own_lifetime_manifest_and_both_readers_preserve_same_attempt_bytes(tmp_path):
    context, page, history = history_setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        response = exchange(context, page)
        capture.bind_detail_page(page)
        candidate = boundaries(capture)
        assert candidate['kind'] == 'corporate-l10b-spa-v1'
        saved = capture.drain()
        assert saved['corporate_l10b_lifetime'] == candidate
        assert 'corporate_l10b_lifetime' not in saved['responses'][0]
        packets = list(capture.iter_bodies())
        assert packets[0]['context']['corporate_l10b_lifetime'] == candidate
        assert packets[0]['body'] == response.raw and response.reads == 1
        record['detail_url'] = DETAIL
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == packets
    assert history.disposed and history.disconnected


@pytest.mark.parametrize('defect', ['unavailable', 'incomplete', 'malformed', 'changed', 'late'])
def test_final_drain_rechecks_child_and_never_reuses_candidate(tmp_path, defect):
    context, page, history = history_setup()
    with DetailJsonCapture(context, page, selected(), SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        if defect == 'unavailable': history.state['available'] = False
        elif defect == 'incomplete': history.state['complete'] = False
        elif defect == 'changed': history.state['changed'] = True
        elif defect == 'malformed': history.state = {'available': 1, 'changed': False, 'complete': True}
        else:
            def late():
                history.on_sample = None
                exchange(context, page)
            history.on_sample = late
        if defect == 'changed':
            with pytest.raises(JsonSafetyError): capture.drain()
        else:
            saved = capture.drain()
            if defect == 'late':
                assert not saved['complete'] and 'response-after-final-drain' in saved['reasons']
            else:
                assert 'corporate_l10b_lifetime' not in saved


@pytest.mark.parametrize('reader', ['live', 'held'])
@pytest.mark.parametrize('defect', ['descriptor-override', 'bad-kind', 'no-component'])
def test_both_readers_refuse_lifetime_override_or_unbound_manifest(tmp_path, reader, defect):
    context, page, history = history_setup()
    record = selected()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        begin(capture)
        navigate(page, DETAIL)
        exchange(context, page)
        capture.bind_detail_page(page)
        assert boundaries(capture)
        saved = capture.drain()
        path = tmp_path / saved['manifest']
        changed = json.loads(path.read_bytes())
        if defect == 'descriptor-override':
            changed['responses'][0]['corporate_l10b_lifetime'] = deepcopy(changed['corporate_l10b_lifetime'])
        elif defect == 'bad-kind': changed['corporate_l10b_lifetime']['kind'] = 'borrowed-l7'
        else: del changed['component_lifetime']
        raw = json.dumps(changed).encode()
        path.write_bytes(raw)
        digest = hashlib.sha256(raw).hexdigest()
        saved = {**changed, 'manifest': saved['manifest'], 'manifest_sha256': digest}
        capture._manifest_hash = digest
        capture._result = saved
        record['detail_url'] = DETAIL
        with pytest.raises(JsonSafetyError):
            if reader == 'live': list(capture.iter_bodies())
            else: checkpoint_bodies(tmp_path, saved, record, SCOPE)


HTML = '''<style>rshshr-corporate-income-tax-return,rshshr-citr-l10b-form{display:block}</style>
<rshshr-corporate-income-tax-return><div class="p-tabview">
<ul><li><a role="tab" aria-controls="panel">L10-B</a></li></ul>
<div class="p-tabview-panels"><div class="p-tabview-panel" id="panel">
<rshshr-citr-l10b-form><span>structural fixture</span></rshshr-citr-l10b-form>
</div></div></div></rshshr-corporate-income-tax-return>'''


@pytest.mark.parametrize('defect', ['healthy', 'occupied', 'detach', 'duplicate', 'disable-reenable',
                                    'panel-replace', 'foreign-owner', 'budget'])
def test_real_history_detects_transient_ownership_changes_without_business_reads(defect):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(channel='msedge', headless=True)
        page = browser.new_page()
        try:
            page.set_content(HTML if defect == 'occupied' else '<body></body>')
            document = page.evaluate_handle('() => document')
            history = document.evaluate_handle(capture_module._L10B_HISTORY)
            if defect != 'occupied': page.evaluate('(html) => document.body.innerHTML=html', HTML)
            if defect == 'foreign-owner':
                page.evaluate('''() => {
                    const form=document.querySelector('rshshr-citr-l10b-form');
                    const foreign=document.createElement('foreign-business-form');
                    form.replaceWith(foreign);foreign.append(form);
                }''')
            args = {'form': page.query_selector('rshshr-citr-l10b-form'),
                    'tab': page.query_selector('[role=tab]'),
                    'panel': page.query_selector('#panel'), 'phase': 'start'}
            start = history.evaluate('(h,args) => h.bind(args)', args)
            if defect in ('occupied', 'foreign-owner'):
                assert not start['available'] or start['changed']
                return
            assert start == {'available': True, 'changed': False, 'complete': False}
            args['phase'] = 'end'
            assert history.evaluate('(h,args) => h.bind(args)', args)['complete']
            if defect == 'detach':
                page.evaluate('''() => {const e=document.querySelector('rshshr-citr-l10b-form');
                    const p=e.parentElement;e.remove();p.append(e);}''')
            elif defect == 'duplicate':
                page.evaluate('''() => {const e=document.querySelector('rshshr-citr-l10b-form').cloneNode(true);
                    document.body.append(e);e.remove();}''')
            elif defect == 'disable-reenable':
                page.evaluate('''() => {const e=document.querySelector('li');
                    e.classList.add('p-disabled');e.classList.remove('p-disabled');}''')
            elif defect == 'panel-replace':
                page.evaluate('''() => {const p=document.querySelector('#panel');
                    const next=p.cloneNode(true);p.replaceWith(next);}''')
            elif defect == 'budget':
                page.evaluate('''() => {const p=document.querySelector('rshshr-citr-l10b-form');
                    for(let i=0;i<4100;i++){const e=document.createElement('span');p.append(e);e.remove();}}''')
            state = history.evaluate('(h) => h.sample()')
            if defect == 'healthy': assert state['complete'] and not state['changed']
            elif defect == 'budget': assert not state['available']
            else: assert state['changed']
            history.evaluate('(h) => h.disconnect()')
            history.dispose()
            document.dispose()
        finally:
            browser.close()
