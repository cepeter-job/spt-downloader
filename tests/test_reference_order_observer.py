"""A loaded synthetic vendor is hashed; missing assets are never forced."""
import hashlib

import pytest

import coretax_json
from masa_json_fixtures import SCOPE
from pph21_observer_fixture import browser

VENDOR_BUILD = b'/* SYNTHETIC ORDER VENDOR -- no portal code */'


def non_script_asset(fixture, vendor):
    if vendor not in ('fetch-only', 'preload-only'):
        return
    from pph21_observer_fixture import VENDOR
    fixture.vendor = VENDOR_BUILD
    fixture.page.evaluate('''async ({url, mode}) => {
      if(mode === 'fetch-only') { await (await fetch(url)).arrayBuffer(); return; }
      await new Promise((resolve, reject) => {
        const link=document.createElement('link'); link.rel='preload'; link.as='script'; link.href=url;
        const timer=setTimeout(()=>{link.remove();reject(Error('synthetic preload timeout'));},10000);
        link.onload=()=>{clearTimeout(timer);resolve();};
        link.onerror=()=>{clearTimeout(timer);reject(Error('synthetic preload failed'));};
        document.head.append(link);
      });
    }''', {'url': VENDOR, 'mode': vendor})
    assert fixture.page.evaluate('url => [...document.scripts].some(s=>s.src===url)', VENDOR) is False
    initiators = fixture.page.evaluate('url => performance.getEntriesByType("resource").filter(e=>e.name===url).map(e=>e.initiatorType)', VENDOR)
    assert initiators == (['fetch'] if vendor == 'fetch-only' else ['link'])
    assert fixture.vendor_requests == ['GET']


@pytest.mark.parametrize('family', ['pph21', 'unifikasi'])
@pytest.mark.parametrize('vendor', ['verified', 'changed', 'missing', 'fetch-only', 'preload-only'])
def test_optional_induk_proof_requires_loaded_digest_without_business_reads(
        browser, tmp_path, monkeypatch, family, vendor):
    digest = hashlib.sha256(VENDOR_BUILD).hexdigest()
    monkeypatch.setattr(coretax_json, 'REFERENCE_ORDER_SHA256', digest, raising=False)
    raw = (None if vendor in ('missing', 'fetch-only', 'preload-only') else
           VENDOR_BUILD + (b'/* CHANGED */' if vendor == 'changed' else b''))
    requests = [] if vendor == 'missing' else ['GET'] if vendor in ('fetch-only', 'preload-only') else ['GET', 'GET']
    if family == 'pph21':
        from pph21_observer_fixture import observed
        from test_pph21_json_observer import feature, assert_no_values_or_actions
        observer = feature(monkeypatch)
        with observed(browser, tmp_path, native=True, vendor=raw) as (fixture, capture):
            non_script_asset(fixture, vendor)
            forms = observer(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
            assert forms is not None
            induk, = [form for form in forms if form['name'] == 'Induk']
            assert_no_values_or_actions(fixture)
            assert fixture.vendor_requests == requests
    else:
        from support_masa_native import observed
        from unifikasi_observer_fixture import NativeFixture
        monkeypatch.setattr('support_masa_native.Fixture', NativeFixture)
        with observed(browser, tmp_path, monkeypatch, 'PPh Unifikasi', vendor=raw) as (module, fixture, capture):
            non_script_asset(fixture, vendor)
            forms = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
            assert forms is not None
            induk, = [form for form in forms if form['name'] == 'INDUK']
            assert fixture.unexpected == []
            assert fixture.page.evaluate('window.valueReads') == 0
            assert fixture.page.evaluate('window.forbiddenClicks') == 0
            assert fixture.vendor_requests == requests
    if vendor == 'verified':
        assert induk.get('reference_order_build') == digest
    else:
        assert 'reference_order_build' not in induk
