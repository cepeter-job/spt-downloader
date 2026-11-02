"""Original-query date preparation; synthetic portals only, hosted runners."""
import pytest

from support_isolated_browser import browser as browser
from coretax_mpn_browser import collect_mpn
from coretax_mpn_ui import AccountingUI
from test_mpn import scope_run
from test_mpn_capture_browser import portal


CANCELLED = {'PropertyName': 'IsCancelled', 'Value': '0', 'MatchMode': 'equals'}
DATE = {'PropertyName': 'TransactionDate', 'Value': ['SYNTHETIC_A', 'SYNTHETIC_B'], 'MatchMode': 'between'}


@pytest.mark.parametrize('snapshot', [
    None, {}, {'request': None}, {'request': {'Filters': None}},
    {'request': {'Filters': [None]}}, {'request': {'Filters': [CANCELLED]}},
    *({'request': {'Filters': [CANCELLED, changed]}} for changed in [
        {**DATE, 'Unexpected': True}, {**DATE, 'MatchMode': 'equals'},
        {**DATE, 'CaseSensitive': False}, {**DATE, 'AsString': True},
        {**DATE, 'Value': None}, {**DATE, 'Value': ['SYNTHETIC']},
        {**DATE, 'Value': [None, 'SYNTHETIC']},
    ]),
    {'request': {'Filters': [CANCELLED, DATE, DATE]}},
    {'request': {'Filters': [{**CANCELLED, 'Value': '1'}, DATE]}},
])
def test_unqualified_source_query_cannot_even_inspect_a_clear_control(snapshot):
    class NoUI:
        def locator(self, *args, **kwargs):
            pytest.fail('Unqualified source query inspected a clear control')
    owned = AccountingUI.__new__(AccountingUI)
    assert owned._clear_initial_transaction_date(snapshot, NoUI()) is False


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
                                    'wrong_icon', 'disabled', 'hidden', 'foreign',
                                    'sibling_table',
                                    'extra_filter', 'different_date_mode', 'modified_cancelled'])
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
