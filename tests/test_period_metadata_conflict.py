"""Submitted-only capture and retained synthetic legacy period-alias proof."""
from copy import deepcopy
import json

import pytest
from support_isolated_browser import browser
import coretax_browser as driver
from spt_desktop import diagnostics as d
from test_diagnostics import records as log_records
from test_json_inventory import synthetic_listing_browser


@pytest.mark.parametrize('expired', [False, True])
def test_new_inventory_keeps_submitted_literal_without_visiting_archive(browser, tmp_path, monkeypatch, expired):
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, archive_period_conflict=True,
                                   expired_catalog=expired, outside_year_padding=0) as (page, metrics):
        with d.session(tmp_path / 'logs', 'worker') as log:
            run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path / 'job')
            assert log.flush()
        assert run['inventory_complete'], run['errors']
        assert {r['record_id'] for r in run['records']} == {
            'fixture-normal', 'fixture-amend-001', 'fixture-cross-year', 'fixture-monthly'}
        selected = next(r for r in run['records'] if r['record_id'] == 'fixture-normal')
        assert selected['meta']['Masa Pajak'] == '01122024'
        assert [o['meta']['Masa Pajak'] for o in selected['source_occurrences']] == ['01122024']
        assert 'period_equivalence' not in selected
        assert not (tmp_path / 'job' / 'period-catalog-reconciliation.json').exists()
        assert len(metrics['list_navigations']) == 2
        assert not any('/archived-returnsheets/' in path for path in metrics['list_navigations'])
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
    stages = [e.get('catalog_stage') for e in log_records(tmp_path / 'logs') if e['event'] == 'catalog.checkpoint']
    assert stages == ['planning', 'readiness', 'after_inventory']
    assert '01122024' not in json.dumps(log_records(tmp_path / 'logs'))


def legacy_alias(run, page):
    """Declare old synthetic evidence without performing an archive navigation."""
    coded = deepcopy(next(r for r in run['records'] if r['record_id'] == 'fixture-normal'))
    labelled = deepcopy(coded)
    coded['meta']['Masa Pajak'] = '01122024'
    labelled['source_status'] = 'Archieved Return Sheets'
    labelled['list_url'] = labelled['list_url'].replace('/submitted-returnsheets/', '/archived-returnsheets/')
    labelled['key'] = labelled['key'].replace('/submitted-returnsheets/', '/archived-returnsheets/')
    source = [coded, labelled]
    before = deepcopy(source)
    selected = driver.deduplicate_inventory(source, period_catalog=driver.read_period_catalog(page), year=2024)[0]
    assert source == before
    assert [o['meta']['Masa Pajak'] for o in selected['source_occurrences']] == ['01122024', 'Januari - Desember 2024']
    assert selected['period_equivalence']
    run['records'] = [selected]
    return selected


def test_saved_legacy_alias_can_restore_with_exact_catalog_proof(browser, tmp_path, monkeypatch):
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, outside_year_padding=0) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        selected = legacy_alias(run, page)
        before = (tmp_path / 'inventory-batches.jsonl').read_bytes()
        original_meta = deepcopy(selected['meta'])
        driver.collect_details(page, run, tmp_path)
        assert metrics['viewed_record_ids'] == ['fixture-normal']
        assert run['records'][0]['meta'] == original_meta
        assert (tmp_path / 'inventory-batches.jsonl').read_bytes() == before
        assert not any('/archived-returnsheets/' in path for path in metrics['list_navigations'])


@pytest.mark.parametrize('changed', ['binding', 'receipt', 'missing_proof', 'expired'])
def test_legacy_restoration_rejects_changed_catalog_or_other_metadata(browser, tmp_path, monkeypatch, changed):
    original = driver.read_period_catalog
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, outside_year_padding=0) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        selected = legacy_alias(run, page)
        if changed in ('binding', 'expired'):
            def changed_read(page):
                catalog = original(page)
                if changed == 'binding':
                    catalog['Checksum'] += '-changed'
                else:
                    catalog['ExpiryDate'] = '2000-01-01T00:00:00Z'
                return catalog
            monkeypatch.setattr(driver, 'read_period_catalog', changed_read)
        elif changed == 'receipt':
            selected['meta']['Nomor Bukti Penerimaan'] = 'changed-receipt'
        else:
            selected.pop('period_equivalence')
        driver.collect_details(page, run, tmp_path)
        assert metrics['viewed_record_ids'] == []
        assert any('metadata changed' in e['message'] for e in run['errors'])


def test_stop_after_reconciliation_prevents_inventory_publication(browser, tmp_path, monkeypatch):
    original = driver.deduplicate_inventory
    stopped = False

    def reconcile(*args, **kwargs):
        nonlocal stopped
        result = original(*args, **kwargs)
        stopped = True
        return result

    def check_cancel():
        if stopped:
            raise driver.CaptureCancelled()

    monkeypatch.setattr(driver, 'deduplicate_inventory', reconcile)
    with synthetic_listing_browser(browser, monkeypatch) as (page, metrics):
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                     check_cancel=check_cancel)
        assert not (tmp_path / 'inventory.json').exists()
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_submitted_inventory_preserves_existing_legacy_catalog_snapshot(browser, tmp_path, monkeypatch):
    snapshot = tmp_path / 'period-catalog-reconciliation.json'
    original = b'{"synthetic_previous_evidence":true}'
    snapshot.write_bytes(original)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, archive_period_conflict=True,
                                   outside_year_padding=0) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        assert run['inventory_complete'], run['errors']
        assert snapshot.read_bytes() == original
        assert (tmp_path / 'inventory.json').exists()
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
