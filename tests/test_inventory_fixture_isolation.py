"""Helper inventaris berbagi proses tanpa berbagi katalog, route, atau metrik."""
from copy import deepcopy

from support_isolated_browser import browser
from test_inventory_year_browser import URL, send, synthetic_browser
from test_json_inventory import SOURCE_URL, synthetic_listing_browser


def test_inventory_helpers_isolate_catalog_routes_and_metrics(browser, monkeypatch):
    with monkeypatch.context() as scoped:
        with synthetic_listing_browser(browser, scoped, year_catalog=True) as (old_page, old_metrics):
            previous = old_page.context
            assert previous.browser is browser
            old_page.goto(SOURCE_URL)
            old_page.wait_for_function(
                "() => document.querySelectorAll('tbody tr').length === 2", timeout=5000)
            assert old_page.evaluate('Intl.DateTimeFormat().resolvedOptions().timeZone') == 'Asia/Jakarta'
            assert old_page.evaluate('''async () => (await indexedDB.databases()).map(
                ({name, version}) => ({name, version}))''') == [
                    {'name': 'e-tax-database', 'version': 2}]
            assert old_metrics['submitted_api_requests'] == 1
            assert old_metrics['unregistered_requests'] == 0
            with old_page.expect_popup(timeout=5000) as pending:
                old_page.locator('#ViewButton').first.click()
            popup = pending.value
            popup.wait_for_load_state('load', timeout=5000)
            assert popup.context is previous
            assert old_metrics['detail_actions'] == 1
            assert old_metrics['viewed_record_ids'] == ['fixture-normal']

        assert old_page.is_closed() and popup.is_closed()
        assert browser.contexts == [] and browser.is_connected()

    previous_metrics = deepcopy(old_metrics)
    with synthetic_browser(browser) as (fresh_page, metrics):
        fresh = fresh_page.context
        assert fresh is not previous and fresh.browser is browser
        assert fresh_page.url == URL
        assert fresh_page.evaluate('async () => await indexedDB.databases()') == []
        assert metrics == {'requests': [], 'unknown': 0}
        assert send(fresh_page) == 200
        assert len(metrics['requests']) == 1
        assert metrics['requests'][0]['TaxpayerAggregateIdentifier'] == 'synthetic-taxpayer'
        assert metrics['unknown'] == 0
        assert fresh_page.evaluate('''async url => {
            try { return (await fetch(url)).status; }
            catch { return 'blocked'; }
        }''', SOURCE_URL) == 'blocked'
        assert metrics['unknown'] == 1
        assert old_metrics == previous_metrics

    assert fresh_page.is_closed()
    assert browser.contexts == [] and browser.is_connected()
