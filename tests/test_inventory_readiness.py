"""Synthetic stability/navigation regressions; execute on GitHub runners only."""
from copy import deepcopy
from datetime import datetime, timedelta

import pytest

from support_isolated_browser import browser
from test_inventory_year_filter import catalog, plan
from test_json_inventory import synthetic_listing_browser


@pytest.mark.parametrize('change', ['renewal', 'reorder'])
def test_catalog_binding_stable_without_losing_raw_snapshot_digest(change):
    original = catalog()
    changed = deepcopy(original)
    if change == 'renewal':
        changed['ExpiryDate'] = '2026-01-03T00:00:00Z'
    else:
        changed['Details'].reverse()
    before, after = plan(original), plan(changed)
    assert before['eligible'] and after['eligible']
    assert before['catalog_sha256'] != after['catalog_sha256']
    assert before.get('catalog_binding_sha256'), 'Missing semantic catalog binding'
    assert before['catalog_binding_sha256'] == after.get('catalog_binding_sha256')
    assert before['filters'] == after['filters']


@pytest.mark.parametrize('change', ['code', 'label', 'checksum'])
def test_catalog_binding_detects_semantic_change(change):
    original = catalog()
    changed = deepcopy(original)
    if change == 'checksum':
        changed['Checksum'] = 'synthetic-catalog-v2'
    else:
        changed['Details'][0]['Code' if change == 'code' else 'CodeDescription'] += '-changed'
    before, after = plan(original), plan(changed)
    assert before['eligible'] and after['eligible']
    assert before.get('catalog_binding_sha256'), 'Missing semantic catalog binding'
    assert before['catalog_binding_sha256'] != after.get('catalog_binding_sha256')


@pytest.mark.parametrize('change', ['renewal', 'semantic', 'expired'])
def test_collector_rechecks_freshness_and_semantics_not_cache_timestamp(browser, tmp_path, monkeypatch, change):
    import coretax_browser as driver
    original = driver.read_period_catalog
    reads = []

    def changed_catalog(page):
        value = original(page)
        if value is not None:
            value = deepcopy(value)
            reads.append(True)
            if len(reads) > 1:
                if change == 'semantic':
                    value['Checksum'] += '-changed'
                else:
                    expiry = datetime.fromisoformat(value['ExpiryDate'].replace('Z', '+00:00'))
                    value['ExpiryDate'] = (expiry + timedelta(days=1 if change == 'renewal' else -3)).isoformat()
        return value

    monkeypatch.setattr(driver, 'read_period_catalog', changed_catalog)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True) as (page, metrics):
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=10)
        assert len(reads) >= 2
        assert result['inventory_complete'] is (change == 'renewal'), result['errors']
        if change != 'renewal':
            assert any(e['message'] == 'capture_safety_refusal' for e in result['errors'])
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0


@pytest.mark.parametrize('kind', ['aria', 'ancestor'])
def test_inventory_does_not_click_semantically_disabled_previous(browser, tmp_path, monkeypatch, kind):
    import coretax_browser as driver
    script = r'''kind => {
      window.addEventListener('click', e=>{
        if(e.target.closest('.p-paginator-prev'))
          localStorage.setItem('previousClicks',String(Number(localStorage.getItem('previousClicks')||0)+1));
      },true);
      new MutationObserver(()=>{
        const button=document.querySelector('.p-paginator-prev');
        if(!button||!button.disabled)return;
        if(kind==='aria')button.setAttribute('aria-disabled','true');
        else button.parentElement.setAttribute('aria-disabled','true');
        button.disabled=false;
      }).observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:['disabled']});
    }'''
    import json
    with synthetic_listing_browser(browser, monkeypatch, empty=True) as (page, metrics):
        page.add_init_script('(' + script + ')(' + json.dumps(kind) + ')')
        result = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path, max_pages=3)
        assert page.evaluate("Number(localStorage.getItem('previousClicks')||0)") == 0
        assert result['inventory_complete'], result['errors']
        assert metrics['unregistered_requests'] == metrics['detail_actions'] == 0
