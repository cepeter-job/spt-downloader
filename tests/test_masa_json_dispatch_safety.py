"""Masa's real JSON-first dispatch must reject contradictions before DOM fallback."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

import coretax_browser as browser
from coretax_json import JsonSafetyError, ORIGIN
from masa_json_fixtures import FOREIGN, SCOPE, packet, payload, selected


class Capture:
    def __init__(self, packets=(), observations=(), late=()):
        self.packets = list(packets)
        self.observations = list(observations)
        self.late = list(late)
        self.drained = False

    def request_observations(self):
        return deepcopy(self.observations + (self.late if self.drained else []))

    def drain(self, **kwargs):
        self.drained = True
        return {'complete': True, 'reasons': []}

    def iter_bodies(self, **kwargs):
        return iter(self.packets)


def collect(monkeypatch, tax, capture, calls, record=None):
    def dom(*args, **kwargs):
        calls.append('dom')
        return {'sections': [{'name': 'DOM SENTINEL'}], 'capture_complete': True,
                'attachments': [], 'errors': []}
    monkeypatch.setattr(browser, 'capture_detail', dom)
    return browser._hybrid_detail(None, selected(tax) if record is None else record,
                                  SCOPE, None, capture, 10, None)


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('conflict', ['outer_tin', 'inner_record', 'inner_period',
                                     'request_record', 'custody', 'privacy', 'snapshot', 'family'])
def test_masa_dispatch_cannot_hide_response_contradictions_behind_missing_observer(monkeypatch, tax, conflict):
    data = payload(tax)
    request = None
    if conflict == 'outer_tin':
        data['TIN'] = '0000000000000099'
    elif conflict in ('inner_record', 'inner_period'):
        form = json.loads(data['FormData'])
        form['ReturnSheetRecordIdentifier' if conflict == 'inner_record' else 'TaxPeriodCode'] = FOREIGN if conflict == 'inner_record' else '02022025'
        data['FormData'] = json.dumps(form)
    elif conflict == 'request_record':
        request = {'RecordId': FOREIGN}
    elif conflict == 'privacy':
        data['Authorization'] = 'SYNTHETIC-NOT-A-CREDENTIAL'
    packets = [packet(tax, data, request=request)]
    if conflict == 'custody':
        packets[0]['context']['sha256'] = '0' * 64
    elif conflict == 'snapshot':
        changed = payload(tax)
        changed['SyntheticMarker'] = 'CHANGED'
        packets.append(packet(tax, changed, sequence=2))
    elif conflict == 'family':
        packets = [packet('PPh Unifikasi' if tax == 'PPN' else 'PPN')]
    calls = []
    with pytest.raises(JsonSafetyError):
        collect(monkeypatch, tax, Capture(packets), calls)
    assert calls == []


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('late', [False, True])
def test_masa_request_only_conflict_is_checked_before_and_after_drain(monkeypatch, tax, late):
    endpoint = '/loadndvat/la2-grid' if tax == 'PPN' else '/loadwtr/list-i-bpu-grid'
    event = {'url': ORIGIN + '/returnsheet/api' + endpoint, 'method': 'POST', 'status': 200,
             'request_json': {'ReturnSheetRecordId': FOREIGN}}
    capture = Capture(late=[event]) if late else Capture(observations=[event])
    calls = []
    with pytest.raises(JsonSafetyError):
        collect(monkeypatch, tax, capture, calls)
    assert calls == []
    assert capture.drained is late


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_masa_missing_period_binding_does_not_hide_source_period_conflict(monkeypatch, tax):
    record = selected(tax)
    record['source_fields'].pop('TaxPeriodCode')
    data = payload(tax)
    data['PeriodCode'] = '02022025'
    calls = []
    with pytest.raises(JsonSafetyError):
        collect(monkeypatch, tax, Capture([packet(tax, data)]), calls, record)
    assert calls == []


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_safe_masa_without_projection_still_uses_dom_and_reports_native_ineligibility(monkeypatch, tax):
    calls = []
    result = collect(monkeypatch, tax, Capture([packet(tax)]), calls)
    assert calls == ['dom']
    assert result['sections'] == [{'name': 'DOM SENTINEL'}]
    audit = result['detail_source']
    assert audit['used'] == 'dom'
    assert 'unverified_masa_form_projection' in audit['reason']
    assert audit['coverage']['complete'] is False
    assert len(audit['json']['events']) == 1


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
@pytest.mark.parametrize('status', [200, 500])
def test_failed_non_authorization_response_with_consistent_identity_can_fall_back(monkeypatch, tax, status):
    calls = []
    result = collect(monkeypatch, tax, Capture([packet(tax, status=status, successful=False)]), calls)
    assert calls == ['dom']
    assert result['detail_source']['used'] == 'dom'
    assert 'failed_masa_primary_response' in result['detail_source']['reason']


def test_staged_worker_rejects_foreign_masa_request_without_repo_imports(tmp_path):
    from spt_desktop.runtime import WORKER_FILES
    source = Path(__file__).resolve().parents[1]
    worker = tmp_path / 'worker'
    for relative in WORKER_FILES:
        target = worker / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / relative, target)
    script = '''import json,sys
sys.path.insert(0,sys.argv[1])
import coretax_browser as b
from coretax_json import JsonSafetyError
x=json.load(sys.stdin)
class Capture:
    def request_observations(self): return [x['event']]
    def drain(self,**kwargs): return {'complete':True,'reasons':[]}
    def iter_bodies(self,**kwargs): return iter(())
b.capture_detail=lambda *a,**kw: sys.exit(17)
try:
    b._hybrid_detail(None,x['record'],x['scope'],None,Capture(),1,None)
except JsonSafetyError:
    print('foreign Masa request blocked')
else:
    sys.exit(18)
'''
    fixture = {'record': selected('PPN'), 'scope': SCOPE,
               'event': {'url': ORIGIN + '/returnsheet/api/loadndvat/la2-grid', 'method': 'POST',
                         'request_json': {'ReturnSheetRecordId': FOREIGN}, 'status': 200}}
    result = subprocess.run([sys.executable, '-I', '-c', script, str(worker)], cwd=tmp_path,
                            input=json.dumps(fixture), text=True, capture_output=True, timeout=60)
    assert result.returncode == 0, result.stderr or result.stdout
    assert result.stdout.strip() == 'foreign Masa request blocked'
