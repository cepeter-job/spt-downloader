"""Synthetic cache diagnostics contracts; GitHub-runner execution only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest
import coretax_inventory as inventory
from spt_desktop import diagnostics as d
from test_diagnostics import records
from test_inventory_year_filter import catalog, NOW
from test_inventory_year_browser import synthetic_browser


@pytest.mark.parametrize('defect,reason', [
    ('missing','catalog_missing'), ('type','catalog_type'),
    ('language','catalog_language'), ('checksum','catalog_checksum'),
    ('details','catalog_details'), ('expiry','catalog_expiry_invalid'),
    ('expired','catalog_expired_or_unbound'), ('row','catalog_row'),
    ('code','catalog_code'), ('label','catalog_label'),
    ('duplicate','catalog_duplicate'), ('valid','available'),
])
def test_planner_logs_exact_gate_without_values(tmp_path, defect, reason):
    source = catalog()
    source['Checksum'] = 'PRIVATE-SENTINEL'
    if defect == 'missing': source = None
    elif defect == 'type': source['ReferenceDataType'] = 'OTHER'
    elif defect == 'language': source['language'] = 'en-US'
    elif defect == 'checksum': source['Checksum'] = ''
    elif defect == 'details': source['Details'] = None
    elif defect == 'expiry': source['ExpiryDate'] = 'PRIVATE-SENTINEL'
    elif defect == 'expired': source['ExpiryDate'] = '2025-01-01T00:00:00Z'
    elif defect == 'row': source['Details'][0] = None
    elif defect == 'code': source['Details'][0]['Code'] = ''
    elif defect == 'label': source['Details'][0]['CodeDescription'] = ''
    elif defect == 'duplicate': source['Details'].append(deepcopy(source['Details'][0]))
    before = deepcopy(source)
    with d.session(tmp_path, 'worker') as log:
        result = inventory.plan_year_filters(source, 2024, 'period', now=NOW)
        assert log.flush()
    assert source == before
    assert result['eligible'] is (defect == 'valid')
    events = [e for e in records(tmp_path) if e['event']=='catalog.validation']
    assert len(events)==1, 'Missing validation diagnostic'
    assert events[0]['catalog_reason']==reason
    assert 'PRIVATE-SENTINEL' not in json.dumps(records(tmp_path))


def test_missing_database_is_not_created_and_no_network_is_sent(tmp_path):
    with synthetic_browser() as (page, metrics):
        before = page.evaluate('async()=>await indexedDB.databases()')
        with d.session(tmp_path, 'worker') as log:
            assert inventory.read_period_catalog(page) is None
            assert log.flush()
        assert page.evaluate('async()=>await indexedDB.databases()') == before
        assert metrics == {'requests':[], 'unknown':0}
    events = [e for e in records(tmp_path) if e['event']=='catalog.read']
    assert len(events)==1, 'Missing reader diagnostic'
    assert events[0]['catalog_reason']=='database_missing'


def test_sink_drops_untrusted_catalog_values(tmp_path):
    class Private:
        def __str__(self): raise AssertionError('Do not stringify')
        def __hash__(self): raise AssertionError('Do not hash')
    with d.session(tmp_path, 'worker') as log:
        d.record('catalog.read', catalog_reason='database_missing', count=0, payload=Private())
        d.record('catalog.checkpoint', catalog_stage='after_inventory', url=Private())
        d.record('catalog.validation', catalog_reason=Private(), catalog_stage='PRIVATE', count=True)
        assert log.flush()
    events = [e for e in records(tmp_path) if e['event'].startswith('catalog.')]
    assert len(events)==3, 'Missing catalog diagnostic events'
    assert events[0]['catalog_reason']=='database_missing' and events[0]['count']==0
    assert events[1]['catalog_stage']=='after_inventory'
    assert not {'catalog_reason','catalog_stage','count','payload','url'} & events[2].keys()
    assert 'PRIVATE' not in json.dumps(events)


@pytest.mark.parametrize('late', ['available','failure','cancel'])
def test_post_inventory_snapshot_does_not_change_selection_or_filters(tmp_path, monkeypatch, late):
    import coretax_browser as driver
    from test_json_inventory import synthetic_listing_browser
    calls = []
    def read(page):
        calls.append(True)
        if len(calls)==1: return None
        if late=='failure': raise RuntimeError('PRIVATE-EXCEPTION-SENTINEL')
        if late=='cancel': raise driver.CaptureCancelled()
        value = catalog()
        value['ExpiryDate'] = (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        return value
    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(monkeypatch) as (page, metrics):
        with d.session(tmp_path/'telemetry', 'worker') as log:
            if late=='cancel':
                with pytest.raises(driver.CaptureCancelled):
                    driver.collect_inventory(page,'0000000000000001',2024,'period',tmp_path/'job',max_pages=5)
            else:
                result = driver.collect_inventory(page,'0000000000000001',2024,'period',tmp_path/'job',max_pages=5)
                assert result['inventory_complete'], result['errors']
                assert [r['record_id'] for r in result['records']]==['fixture-normal','fixture-amend-001']
                assert all(p['Filters']==[] for p in metrics['requests'])
            assert log.flush()
        assert len(calls)==2, 'Missing post-inventory cache snapshot'
        assert metrics['unregistered_requests']==metrics['detail_actions']==0
    events = records(tmp_path/'telemetry')
    assert [e['catalog_stage'] for e in events if e['event']=='catalog.checkpoint']==['planning','after_inventory']
    assert 'PRIVATE-EXCEPTION-SENTINEL' not in json.dumps(events)
