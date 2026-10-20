"""Synthetic cross-status aliases through real Edge collection/restoration."""
from copy import deepcopy
import hashlib
import json

import pytest
import coretax_browser as driver
from spt_desktop import diagnostics as d
from test_diagnostics import records as log_records
from test_json_inventory import synthetic_listing_browser


def test_catalog_reconciles_late_period_label_and_preserves_detail_source(tmp_path, monkeypatch):
    with synthetic_listing_browser(monkeypatch, year_catalog=True, archive_period_conflict=True) as (page, metrics):
        with d.session(tmp_path/'logs', 'worker') as log:
            run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path/'job')
            assert log.flush()
        assert run['inventory_complete'], run['errors']
        assert len(run['records']) == 4
        selected = next(r for r in run['records'] if r['record_id'] == 'fixture-normal')
        assert selected['meta']['Masa Pajak'] == '01122024'
        assert [o['meta']['Masa Pajak'] for o in selected['source_occurrences']] == ['01122024', 'Januari - Desember 2024']
        assert selected['source_status'] == 'SPT Dilaporkan'
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
        assert len(metrics['list_navigations']) == 4
        assert all(not p['Filters'] for p in metrics['submitted_requests'])
        snapshot = (tmp_path/'job'/'period-catalog-reconciliation.json').read_bytes()
        value = json.loads(snapshot)
        canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
        assert hashlib.sha256(canonical).hexdigest() == selected['period_equivalence']['catalog_sha256']
        before = (tmp_path/'job'/'inventory-batches.jsonl').read_bytes()
        run['records'] = [deepcopy(selected)]
        driver.collect_details(page, run, tmp_path/'job')
        assert metrics['viewed_record_ids'] == ['fixture-normal']
        assert run['records'][0]['meta'] == selected['meta']
        assert (tmp_path/'job'/'inventory-batches.jsonl').read_bytes() == before
    stages = [e.get('catalog_stage') for e in log_records(tmp_path/'logs') if e['event'] == 'catalog.checkpoint']
    assert stages == ['planning', 'readiness', 'reconciliation', 'after_inventory']
    text = json.dumps(log_records(tmp_path/'logs'))
    assert '01122024' not in text and 'Januari - Desember' not in text


def test_late_expired_catalog_cannot_resolve_conflict(tmp_path, monkeypatch):
    with synthetic_listing_browser(monkeypatch, year_catalog=True, expired_catalog=True,
                                   archive_period_conflict=True) as (page, metrics):
        with pytest.raises(ValueError, match='Conflicting source metadata'):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        assert not (tmp_path/'inventory.json').exists()
        assert not (tmp_path/'period-catalog-reconciliation.json').exists()
        assert (tmp_path/'inventory-batches.jsonl').exists()
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


@pytest.mark.parametrize('changed', ['binding', 'receipt', 'missing_proof'])
def test_restoration_rejects_changed_catalog_or_other_metadata(tmp_path, monkeypatch, changed):
    original = driver.read_period_catalog
    with synthetic_listing_browser(monkeypatch, year_catalog=True, archive_period_conflict=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        selected = deepcopy(next(r for r in run['records'] if r['record_id'] == 'fixture-normal'))
        run['records'] = [selected]
        if changed == 'binding':
            def changed_read(page):
                catalog = original(page)
                catalog['Checksum'] += '-changed'
                return catalog
            monkeypatch.setattr(driver, 'read_period_catalog', changed_read)
        elif changed == 'receipt':
            selected['meta']['Nomor Bukti Penerimaan'] = 'changed-receipt'
        else:
            selected.pop('period_equivalence')
        driver.collect_details(page, run, tmp_path)
        assert metrics['viewed_record_ids'] == []
        assert run['errors']
        assert any('metadata changed' in e['message'] for e in run['errors'])


def test_stop_after_reconciliation_read_prevents_inventory_publication(tmp_path, monkeypatch):
    original = driver.read_period_catalog
    stopped = False
    reads = []

    def read(page):
        nonlocal stopped
        result = original(page)
        reads.append(result is not None)
        if '/archived-returnsheets/' in page.url:
            stopped = True
        return result

    def check_cancel():
        if stopped:
            raise driver.CaptureCancelled()

    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(monkeypatch, year_catalog=True, archive_period_conflict=True) as (page, metrics):
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path,
                                     check_cancel=check_cancel)
        assert reads == [False, False, True]
        assert not (tmp_path/'inventory.json').exists()
        assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
