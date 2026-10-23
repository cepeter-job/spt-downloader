"""Synthetic late lookup labels; no live browser or taxpayer data."""
from copy import deepcopy
import json

import pytest
import coretax_browser as driver
from support_isolated_browser import browser
from test_json_inventory import synthetic_listing_browser
from test_diagnostics import records as log_records


def inventory(page, folder):
    run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', folder)
    run['records'] = [next(r for r in run['records'] if r['record_id'] == 'fixture-normal')]
    assert run['inventory_complete']
    assert run['records'][0]['meta']['Masa Pajak'] == '01122024'
    assert 'period_equivalence' not in run['records'][0]
    return run


def test_submitted_only_late_label_uses_fresh_catalog_without_rewriting_inventory(browser, monkeypatch, tmp_path):
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, archive_period_conflict=True,
                                   restored_period_label=True, outside_year_padding=0) as (page, metrics):
        run = inventory(page, tmp_path / 'job')
        original = deepcopy(run['records'][0])
        batches = (tmp_path / 'job' / 'inventory-batches.jsonl').read_bytes()
        with driver.diagnostics.session(tmp_path / 'logs', 'worker') as log:
            driver.collect_details(page, run, tmp_path / 'job')
            assert log.flush()
        assert metrics['viewed_record_ids'] == ['fixture-normal']
        record = run['records'][0]
        assert record['meta'] == original['meta']
        assert record['source_occurrences'] == original['source_occurrences']
        assert (tmp_path / 'job' / 'inventory-batches.jsonl').read_bytes() == batches
        assert record['period_equivalence']['code'] == '01122024'
        snapshots = list((tmp_path / 'job').glob('period-catalog-restoration-*.json'))
        assert len(snapshots) == 1
        catalog = json.loads(snapshots[0].read_text())
        assert {'Code': '01122024', 'CodeDescription': 'Januari - Desember 2024'} in catalog['Details']
        assert record['sections']
        assert not run['complete'], 'Synthetic detail lacks a verified financial PDF'
        assert not any('/archived-returnsheets/' in p for p in metrics['list_navigations'])
        assert metrics['unregistered_requests'] == 0
        assert '01122024' not in json.dumps(log_records(tmp_path / 'logs'))


@pytest.mark.parametrize('invalid', ['missing', 'expired', 'ambiguous', 'receipt', 'model',
                                   'legacy_without_proof', 'occurrence_mismatch'])
def test_late_label_still_rejects_unproved_or_changed_metadata(browser, monkeypatch, tmp_path, invalid):
    changes = ({'Nomor Bukti Penerimaan': 'SYNTHETIC_CHANGED_RECEIPT'} if invalid == 'receipt' else
               {'Model SPT': 'SYNTHETIC_CHANGED_MODEL'} if invalid == 'model' else None)
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, archive_period_conflict=True,
                                   restored_period_label=True, expired_catalog=invalid == 'expired',
                                   restored_catalog=invalid, restored_metadata=changes,
                                   outside_year_padding=0) as (page, metrics):
        run = inventory(page, tmp_path)
        selected = run['records'][0]
        if invalid == 'legacy_without_proof':
            selected['source_occurrences'].append({**deepcopy(selected['source_occurrences'][0]),
                                                   'source_status': 'Archieved Return Sheets'})
        elif invalid == 'occurrence_mismatch':
            selected['source_occurrences'][0]['meta']['Masa Pajak'] = 'SYNTHETIC_CHANGED_PERIOD'
        driver.collect_details(page, run, tmp_path)
        assert metrics['viewed_record_ids'] == []
        assert any('metadata changed' in e['message'] for e in run['errors'])
        assert not list(tmp_path.glob('period-catalog-restoration-*.json'))
        assert not run['complete']


@pytest.mark.parametrize('api_period', ['missing', '06062024'])
def test_fresh_catalog_pair_cannot_override_changed_current_api_period(browser, monkeypatch, tmp_path, api_period):
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, archive_period_conflict=True,
                                   restored_period_label=True, restored_api_period=api_period,
                                   outside_year_padding=0) as (page, metrics):
        run = inventory(page, tmp_path)
        driver.collect_details(page, run, tmp_path)
        assert metrics['viewed_record_ids'] == []
        assert run['errors'] and not run['complete']
        assert not list(tmp_path.glob('period-catalog-restoration-*.json'))


def test_stop_during_fresh_period_proof_prevents_view(browser, monkeypatch, tmp_path):
    with synthetic_listing_browser(browser, monkeypatch, year_catalog=True, archive_period_conflict=True,
                                   restored_period_label=True, outside_year_padding=0) as (page, metrics):
        run = inventory(page, tmp_path)
        original = driver.read_period_catalog
        stopped = False

        def read(page):
            nonlocal stopped
            value = original(page)
            stopped = True
            return value

        def cancel():
            if stopped:
                raise driver.CaptureCancelled('Synthetic Stop')

        monkeypatch.setattr(driver, 'read_period_catalog', read)
        with pytest.raises(driver.CaptureCancelled):
            driver.collect_details(page, run, tmp_path, check_cancel=cancel)
        assert metrics['viewed_record_ids'] == []
        assert not list(tmp_path.glob('period-catalog-restoration-*.json'))
