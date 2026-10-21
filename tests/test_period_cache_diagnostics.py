"""Synthetic cache diagnostics contracts; GitHub-runner execution only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest
from support_isolated_browser import browser
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


def test_missing_database_is_not_created_and_no_network_is_sent(browser, tmp_path):
    with synthetic_browser(browser) as (page, metrics):
        before = page.evaluate('async()=>await indexedDB.databases()')
        with d.session(tmp_path, 'worker') as log:
            assert inventory.read_period_catalog(page) is None
            assert log.flush()
        assert page.evaluate('async()=>await indexedDB.databases()') == before
        assert metrics == {'requests':[], 'unknown':0}
    events = [e for e in records(tmp_path) if e['event']=='catalog.read']
    assert len(events)==1, 'Missing reader diagnostic'
    assert events[0]['catalog_reason']=='database_missing'


@pytest.mark.parametrize('mode,reason', [('store_missing','store_missing'),
    ('record_missing','record_missing'), ('projection_error','projection_error'), ('valid','available')])
def test_existing_cache_is_readonly_and_reports_exact_state(browser, tmp_path, mode, reason):
    with synthetic_browser(browser) as (page, metrics):
        page.evaluate('''async mode=>new Promise((resolve,reject)=>{
          const q=indexedDB.open('e-tax-database',1);
          q.onupgradeneeded=()=>q.result.createObjectStore(mode==='store_missing'?'otherStore':'referenceDataStore',
            {keyPath:['ReferenceDataType','language']});
          q.onerror=reject;
          q.onsuccess=()=>{const db=q.result;
            if(mode==='store_missing'||mode==='record_missing'){db.close();resolve();return;}
            const tx=db.transaction('referenceDataStore','readwrite');
            tx.objectStore('referenceDataStore').put({ReferenceDataType:'PERIOD',language:'id-ID',
              Checksum:'PRIVATE-CACHE',ExpiryDate:new Date('2099-01-01'),
              Details:mode==='projection_error'?[null]:[{Code:'01122024',CodeDescription:'Synthetic period 2024'}]});
            tx.oncomplete=()=>{db.close();resolve();};tx.onerror=reject;
          };
        })''', mode)
        before=page.evaluate('async()=>await indexedDB.databases()')
        page.evaluate('''()=>{window.writes=0;
          for(const k of ['put','add','delete','clear'])IDBObjectStore.prototype[k]=function(){
            window.writes++;throw Error('Forbidden cache mutation');};}''')
        with d.session(tmp_path,'worker') as log:
            value=inventory.read_period_catalog(page)
            assert log.flush()
        assert (value is not None) is (mode=='valid')
        if mode=='valid': assert value['Checksum']=='PRIVATE-CACHE'
        assert page.evaluate('window.writes')==0
        assert page.evaluate('async()=>await indexedDB.databases()')==before
        assert metrics=={'requests':[],'unknown':0}
    events=[e for e in records(tmp_path) if e['event']=='catalog.read']
    assert len(events)==1, 'Missing reader diagnostic'
    assert events[0]['catalog_reason']==reason
    assert 'PRIVATE-CACHE' not in json.dumps(records(tmp_path))


@pytest.mark.parametrize('mode,reason', [('race','upgrade_refused'), ('hung','read_timeout')])
def test_cache_enumeration_race_cannot_create_database_or_wait_forever(browser, tmp_path, mode, reason):
    with synthetic_browser(browser) as (page, metrics):
        page.evaluate("""mode=>{
          window.actualDatabases=indexedDB.databases.bind(indexedDB);
          indexedDB.databases=mode==='race'?async()=>[{name:'e-tax-database'}]:()=>new Promise(()=>{});
        }""", mode)
        with d.session(tmp_path,'worker') as log:
            assert inventory.read_period_catalog(page) is None
            assert log.flush()
        assert page.evaluate('async()=>await window.actualDatabases()')==[]
        assert metrics=={'requests':[],'unknown':0}
    events=[e for e in records(tmp_path) if e['event']=='catalog.read']
    assert len(events)==1 and events[0]['catalog_reason']==reason


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
def test_post_inventory_snapshot_does_not_change_selection_or_filters(browser, tmp_path, monkeypatch, late):
    import coretax_browser as driver
    from test_json_inventory import synthetic_listing_browser
    calls = []
    def read(page):
        calls.append(True)
        if len(calls)<=2: return None
        if late=='failure': raise RuntimeError('PRIVATE-EXCEPTION-SENTINEL')
        if late=='cancel': raise driver.CaptureCancelled()
        value = catalog()
        value['ExpiryDate'] = (datetime.now(timezone.utc)+timedelta(days=1)).isoformat()
        return value
    monkeypatch.setattr(driver, 'read_period_catalog', read)
    with synthetic_listing_browser(browser, monkeypatch) as (page, metrics):
        with d.session(tmp_path/'telemetry', 'worker') as log:
            if late=='cancel':
                with pytest.raises(driver.CaptureCancelled):
                    driver.collect_inventory(page,'0000000000000001',2024,'period',tmp_path/'job',max_pages=5)
            else:
                result = driver.collect_inventory(page,'0000000000000001',2024,'period',tmp_path/'job',max_pages=5)
                assert result['inventory_complete'], result['errors']
                assert [r['record_id'] for r in result['records']]==['fixture-normal','fixture-amend-001']
                assert all(p['Filters']==[] for p in metrics['submitted_requests'])
            assert log.flush()
        assert len(calls)==3, 'Missing readiness read or post-inventory snapshot'
        assert metrics['unregistered_requests']==metrics['detail_actions']==0
    events = records(tmp_path/'telemetry')
    assert [e['catalog_stage'] for e in events if e['event']=='catalog.checkpoint']==['planning','readiness','after_inventory']
    assert 'PRIVATE-EXCEPTION-SENTINEL' not in json.dumps(events)
