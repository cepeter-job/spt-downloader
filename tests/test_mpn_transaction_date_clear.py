"""Original-query date preparation; synthetic portals only, hosted runners."""
import pytest

from support_isolated_browser import browser as browser
from coretax_mpn_browser import collect_mpn
from test_mpn import scope_run
from test_mpn_capture_browser import portal


@pytest.mark.parametrize('empty', [False, True])
def test_owned_transaction_calendar_clear_then_second_search_completes(browser, tmp_path, monkeypatch, empty):
    with portal(browser, monkeypatch, default_stuck=True, empty=empty,
                transaction_date_clear='valid') as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['mpn']['status'] == 'COMPLETE' and run['complete']
        assert page.evaluate('window.syntheticDateClicks') == 1
        assert page.evaluate('window.syntheticSearchClicks') == 2
        assert all([f['PropertyName'] for f in query['Filters']] == ['IsCancelled', 'TransactionDate']
                   for query in metrics['list'][:-1])
        assert [f['PropertyName'] for f in metrics['list'][-1]['Filters']] == ['IsCancelled']
        assert len(metrics['detail']) == (0 if empty else 1)


@pytest.mark.parametrize('variant', ['duplicate_calendar', 'duplicate_button', 'wrong_input',
                                    'wrong_icon', 'disabled', 'hidden', 'foreign'])
def test_unproved_transaction_date_control_never_clears_or_admits_inventory(browser, tmp_path, monkeypatch, variant):
    with portal(browser, monkeypatch, default_stuck=True,
                transaction_date_clear=variant) as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['mpn']['status'] == 'PARTIAL' and not run['complete']
        assert page.evaluate('window.syntheticDateClicks') == 0
        assert page.evaluate('window.syntheticSearchClicks') <= 2
        assert metrics['detail'] == []


def test_date_clear_does_not_certify_its_stale_reply_or_retry_after_second_search(browser, tmp_path, monkeypatch):
    with portal(browser, monkeypatch, default_stuck=True,
                transaction_date_clear='ineffective') as (page, metrics):
        run = scope_run()
        collect_mpn(page, run, tmp_path)
        assert run['mpn']['status'] == 'PARTIAL' and not run['complete']
        assert page.evaluate('window.syntheticDateClicks') == 1
        assert page.evaluate('window.syntheticSearchClicks') == 2
        assert all(any(f['PropertyName'] == 'TransactionDate' for f in query['Filters'])
                   for query in metrics['list'])
        assert metrics['detail'] == []
