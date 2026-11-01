"""New live inventory observes submitted returns only; fixtures are synthetic."""
import json

import pytest

import coretax_browser as driver
from support_isolated_browser import browser as browser
from test_json_inventory import synthetic_listing_browser


@pytest.mark.parametrize('empty', [False, True])
def test_dom_inventory_never_visits_discovered_archive_or_other_statuses(browser, tmp_path, monkeypatch, empty):
    with synthetic_listing_browser(
        browser, monkeypatch, unknown=True, empty=empty,
        archive_period_conflict=True, extra_status_links=True,
    ) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)

    assert metrics['list_navigations'] == [
        '/returnsheets/id-ID/not-submitted-returnsheets/fixture-taxpayer',
        '/returnsheets/id-ID/submitted-returnsheets/fixture-taxpayer',
    ], 'Taxpayer selection may land on draft; inventory must visit only submitted'
    assert run['inventory_complete'], run['errors']
    assert run['scope_description'].startswith('Hanya SPT Dilaporkan ')
    assert 'Semua status' not in run['scope_description']
    assert len(run['sources']) == len(run['audit']) == 1
    assert run['sources'][0]['label'] == run['audit'][0]['status'] == 'SPT Dilaporkan'
    # An empty, source-bound response has no unsupported row schema to adapt.
    assert run['audit'][0]['used_source'] == ('json' if empty else 'dom-fallback')
    assert run['audit'][0]['scanned'] == (0 if empty else 3)
    assert len(run['records']) == (0 if empty else 2)
    assert all(record['source_status'] == 'SPT Dilaporkan' for record in run['records'])
    assert all(len(record['source_occurrences']) == 1 for record in run['records'])
    assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0
    assert json.loads((tmp_path / 'inventory.json').read_text(encoding='utf-8')) == run
    batches = [json.loads(line) for line in (tmp_path / 'inventory-batches.jsonl').read_text(encoding='utf-8').splitlines()]
    assert len(batches) == (0 if empty else 2)
    assert 'Archieved Return Sheets' not in json.dumps(batches)


def test_json_inventory_declares_same_submitted_only_scope(browser, tmp_path, monkeypatch):
    with synthetic_listing_browser(browser, monkeypatch, extra_status_links=True) as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)

    assert run['inventory_complete'], run['errors']
    assert len(run['audit']) == len(run['sources']) == 1
    assert run['audit'][0]['used_source'] == 'json'
    assert metrics['submitted_full_grid_reads'] == 0
    assert len(metrics['list_navigations']) == 2
    assert metrics['detail_actions'] == metrics['unregistered_requests'] == 0


@pytest.mark.parametrize('link', ['missing', 'foreign', 'wrong_label', 'ambiguous'])
def test_no_unique_inspected_submitted_navigation_cannot_certify_inventory(browser, tmp_path, monkeypatch, link):
    with synthetic_listing_browser(browser, monkeypatch, submitted_link=link) as (page, metrics):
        try:
            run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        except RuntimeError:
            run = None
    assert run is None or not run['inventory_complete']
    assert metrics['list_navigations'] == ['/returnsheets/id-ID/not-submitted-returnsheets/fixture-taxpayer']
    assert metrics['submitted_api_requests'] == metrics['detail_actions'] == metrics['unregistered_requests'] == 0


@pytest.mark.parametrize('redirect', [True, 'archive'])
def test_submitted_navigation_redirect_cannot_capture_wrong_scope(browser, tmp_path, monkeypatch, redirect):
    with synthetic_listing_browser(browser, monkeypatch, submitted_redirect=redirect) as (page, metrics):
        try:
            run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
        except RuntimeError:
            run = None
    assert run is None or not run['inventory_complete']
    assert run is None or not run['records']
    assert metrics['submitted_api_requests'] == metrics['detail_actions'] == metrics['unregistered_requests'] == 0


def test_identical_inspected_submitted_links_are_one_source(browser, tmp_path, monkeypatch):
    with synthetic_listing_browser(browser, monkeypatch, submitted_link='duplicate') as (page, metrics):
        run = driver.collect_inventory(page, '0000000000000001', 2024, 'period', tmp_path)
    assert run['inventory_complete'], run['errors']
    assert len(run['sources']) == len(run['audit']) == 1
    assert len(metrics['list_navigations']) == 2


def test_desktop_selection_retains_submitted_inventory_scope_without_changing_evidence():
    from copy import deepcopy
    from spt_desktop.interaction import select_records
    run = {'records': [{'record_id': 'synthetic-selected'}, {'record_id': 'synthetic-other'}],
           'scope_description': 'Hanya SPT Dilaporkan dalam tahun pilihan.'}
    original = deepcopy(run)
    selected = select_records(run, ['synthetic-selected'])
    assert selected['scope_description'] == 'Pilihan pengguna: 1 dari 2 SPT teramati. ' + run['scope_description']
    assert run == original
