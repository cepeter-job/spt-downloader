"""Real isolated Edge history/observer/native/checkpoint tests; runners only."""
from copy import deepcopy

import pytest

from coretax_corporate import observe_forms
from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l8_observer_fixture import Fixture
from l1d_observer_fixture import ASSET
from test_corporate_l1d_observer import open_selected
from test_json_hybrid_native import browser
from test_corporate_l8_native import DETAIL
import support_json_corpus as corpus


def history(capture, check_cancel=None):
    method = getattr(capture, 'observe_l8_lifetime', None)
    assert callable(method), 'Value-free L8 history observation is absent'
    return method(check_cancel=check_cancel)


@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
def test_owned_l8_observer_native_custody_and_replay_never_read_business_values(
        browser, tmp_path, monkeypatch, model):
    fixture = Fixture(browser, monkeypatch, model=model)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms is not None and [f['name'] for f in forms] == ['Induk', 'L8']
            assert forms[1]['projection']['kind'] == 'corporate-l8-v1'
            assert forms[1]['projection']['builds'] == fixture.pins
            saved = capture.drain()
            assert saved['complete'] and saved['corporate_l8_lifetime']['stable_root'] is True
            bodies = list(capture.iter_bodies())
            assert len(bodies) == 1 and bodies[0]['body'] == fixture.raw
            before = deepcopy((bodies, forms, fixture.record))
            result = adapt_corporate_detail(bodies, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            assert (bodies, forms, fixture.record) == before
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, saved, fixture.record, corpus.SCOPE),
                                           fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
            assert fixture.requests.count((corpus.PRIMARY_URL, 'POST')) == 1
            assert fixture.requests.count((corpus.LIST_URL, 'GET')) == 1
            assert all(fixture.requests.count((url, 'GET')) == 2 for url in fixture.assets)
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['external-context', 'vendor-pin', 'owner', 'header', 'footer',
    'duplicate-owner', 'hidden-owner', 'wrong-group', 'table-outside-p-table',
    'hidden-initial-root', 'hidden-initial-dependent',
    'corporate-fetch-only', 'corporate-preload-only', 'main-fetch-only', 'main-preload-only',
    'vendor-fetch-only', 'vendor-preload-only'])
def test_l8_unproved_owner_history_or_provider_uses_whole_record_fallback(browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms is None
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('tag', ['rshshr-citr-l7-form', 'rshshr-citr-l13a-form', 'rshshr-citr-l13b-form'])
@pytest.mark.parametrize('nested', [False, True])
def test_l8_history_retains_transient_forbidden_hosts_removed_in_same_turn(
        browser, tmp_path, monkeypatch, tag, nested):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert history(capture) is not None
            page.evaluate('''({tag,nested})=>{
                const host=document.createElement(tag), wrapper=document.createElement('div');
                const root=document.querySelector('rshshr-corporate-income-tax-return');
                if(nested){wrapper.append(host);root.append(wrapper);wrapper.remove();}
                else {root.append(host);host.remove();}
            }''', {'tag': tag, 'nested': nested})
            assert history(capture) is None
            saved = capture.drain()
            assert 'corporate_l8_lifetime' not in saved
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('mutation', ['remove-reinsert', 'remove-parent-reinsert', 'replace', 'duplicate'])
def test_l8_root_history_contradictions_are_fatal_even_with_final_connected_owner(
        browser, tmp_path, monkeypatch, mutation):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert history(capture) is not None
            page.evaluate('''mode=>{
                const root=document.querySelector('rshshr-corporate-income-tax-return');
                if(mode==='remove-reinsert'){const parent=root.parentNode;root.remove();parent.append(root);}
                if(mode==='remove-parent-reinsert'){
                    const wrap=document.createElement('div');root.replaceWith(wrap);wrap.append(root);
                }
                if(mode==='replace'){const replacement=root.cloneNode(true);root.replaceWith(replacement);}
                if(mode==='duplicate'){root.parentNode.append(root.cloneNode(true));}
            }''', mutation)
            with pytest.raises(JsonSafetyError):
                capture.drain()
    finally:
        fixture.close()


def test_l8_history_stop_propagates_without_fallback_or_restart(browser, tmp_path, monkeypatch):
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            open_selected(fixture, capture)
            def stop():
                raise RuntimeError('SYNTHETIC STOP')
            with pytest.raises(RuntimeError, match='SYNTHETIC STOP'):
                history(capture, check_cancel=stop)
    finally:
        fixture.close()
