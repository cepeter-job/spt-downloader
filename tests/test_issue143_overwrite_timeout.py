"""Synthetic operator-consent expiry and GUI presentation; no live tax data."""
import json
from types import SimpleNamespace

import pytest

from spt_desktop import diagnostics, interaction, worker
from test_diagnostics import records
from support_runs import fixture_run
from support_selected_capture import synthetic_browser
from test_desktop_dialog_layout import active_app, open_overwrite, settle


@pytest.mark.parametrize('kind', ['selection', 'overwrite'])
def test_expired_consent_is_bounded_blocked_and_never_auto_approves(
        tmp_path, monkeypatch, kind):
    clock = {'time': 100.0}
    def now():
        clock['time'] += 0.2
        return clock['time']
    monkeypatch.setattr(interaction.time, 'monotonic', now)
    sent=[]
    requests = interaction.Requests(tmp_path, 'synthetic-job', sent.append, lambda: None)
    monkeypatch.setattr(requests._ready, 'wait', lambda seconds: False)
    payload=({'files': ['SYNTHETIC_PRIVATE_FILENAME.xlsx'], 'folder': 'PRIVATE_SYNTHETIC'}
             if kind == 'overwrite' else {'records': []})
    with diagnostics.session(tmp_path/'log', 'worker') as log:
        with pytest.raises(interaction.ConsentTimeout) as caught:
            requests.request(kind, payload, 99, timeout=1)
        assert log.flush()
    assert caught.value.kind == kind
    assert len(sent) == 1 and sent[0]['type'] == kind + '_required'
    assert not (tmp_path / f".interaction-{sent[0]['request_id']}.reply.json").exists()
    events=[e for e in records(tmp_path/'log') if e['event']=='consent.timeout']
    assert len(events)==1
    assert events[0]['kind']==kind
    assert events[0]['status']=='BLOCKED'
    assert 'SYNTHETIC_PRIVATE' not in json.dumps(events)
    assert requests._pending is None


def test_worker_overwrite_expiry_is_blocked_without_publication(
        tmp_path, monkeypatch):
    state={}
    synthetic_browser(worker,monkeypatch,state)
    run=fixture_run()
    run['inventory_complete']=True
    def inventory(page,npwp,year,basis,folder,**kwargs):
        return run
    def details(page,data,folder,on_progress,check_cancel):
        for ordinal,record in enumerate(data['records'],1):
            record['capture_complete']=True
            on_progress(data,ordinal)
        data['complete']=True
        return data
    monkeypatch.setattr(worker,'collect_inventory',inventory)
    monkeypatch.setattr(worker,'collect_details',details)
    monkeypatch.setattr(worker.coretax,'save_output',lambda *a,**k:None)
    monkeypatch.setattr(worker,'downloads_folder',lambda:tmp_path/'Downloads')
    monkeypatch.setattr(worker,'existing_outputs',
                        lambda run,downloads:{'files':['SYNTHETIC_EXISTING.xlsx'],
                                              'target':'SYNTHETIC'})
    published=[]
    monkeypatch.setattr(worker,'publish_workbooks',lambda *a,**k:published.append(True))
    asked=[]
    def request(kind,payload,percent):
        asked.append(kind)
        if kind=='selection':
            return {'selected_ids':[run['records'][0]['record_id']]}
        raise interaction.ConsentTimeout('overwrite')
    messages=[]
    code=worker.run_job('0000000000000001','2025',tmp_path/'workspace',
                        'synthetic-job','msedge',True,messages.append,
                        lambda:False,requests=SimpleNamespace(request=request))
    assert code==3
    assert asked==['selection','overwrite']
    assert not published
    assert state['browser_closed'] and state['driver_closed']
    terminal=messages[-1]
    assert terminal['type']=='terminal' and terminal['status']=='BLOCKED'
    assert terminal['output'] is None and terminal['percent']<100
    assert 'Konfirmasi penggantian' in terminal['message']
    assert 'SYNTHETIC_EXISTING' not in json.dumps(messages)


def test_modal_presentation_emits_only_mapped_state_and_count(
        active_app, monkeypatch):
    _,app,controller=active_app
    captured=[]
    monkeypatch.setattr(diagnostics, 'record',
                        lambda event, **fields: captured.append((event,fields)))
    dialog=open_overwrite(active_app,{'files':['PRIVATE_TAXPAYER_1.xlsx','PRIVATE_TAXPAYER_2.xlsx'],
                                      'folder':'PRIVATE_FOLDER'})
    settle(app.root)
    shown=[fields for event,fields in captured if event=='consent.dialog_presented']
    assert len(shown)==1
    assert shown[0]=={'kind':'overwrite','count':2}
    assert dialog.winfo_viewable()
    assert controller.replies == []
    assert 'PRIVATE_' not in json.dumps(shown)
    app.stop()
