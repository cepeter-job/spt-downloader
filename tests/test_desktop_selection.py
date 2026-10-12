"""Synthetic job-bound interaction contracts; no accounts or portal access."""
from copy import deepcopy
import importlib
import importlib.util
import json
import pytest
from spt_desktop.controller import parse_event
from test_split_output import fixture_run


def interaction():
    assert importlib.util.find_spec('spt_desktop.interaction'), 'Selection/consent interaction is missing'
    return importlib.import_module('spt_desktop.interaction')


def test_select_only_confirmed_ids_without_changing_inventory():
    original=fixture_run()
    before=deepcopy(original)
    selected=interaction().select_records(original,['21-january'])
    assert [r['record_id'] for r in selected['records']]==['21-january']
    assert selected['selection']['inventory_count']==5
    assert selected['selection']['selected_ids']==['21-january']
    assert 'pilihan' in selected['scope_description'].casefold()
    assert original==before


@pytest.mark.parametrize('ids',[[],['unknown'],['21-january','21-january'],[1], '21-january'])
def test_invalid_choice_cannot_capture_other_returns(ids):
    with pytest.raises(ValueError):
        interaction().select_records(fixture_run(),ids)


def test_job_bound_request_event_and_login_check_rejection():
    event={'job_id':'synthetic-job','type':'selection_required','request_id':'a'*32,
        'percent':20,'stage':'selection','message':'Pilih SPT.'}
    assert parse_event(json.dumps(event),'synthetic-job')==event
    assert parse_event(json.dumps(event),'other-job') is None
    assert parse_event(json.dumps(event),'synthetic-job',operation='login_check') is None
    assert parse_event(json.dumps({**event,'request_id':'../other'}),'synthetic-job') is None


def test_request_waits_for_matching_reply_and_does_not_echo_record_ids(tmp_path):
    module=interaction()
    emitted=[]
    requests=None
    def emit(event):
        emitted.append(event)
        module.write_reply(tmp_path,'synthetic-job',event['request_id'],{'selected_ids':['synthetic-return']})
        assert requests.respond('selection',event['request_id'])
    requests=module.Requests(tmp_path,'synthetic-job',emit,lambda:None)
    reply=requests.request('selection',{'records':[{'record_id':'synthetic-return','meta':{}}]},20)
    assert reply=={'selected_ids':['synthetic-return']}
    assert all('synthetic-return' not in json.dumps(event) for event in emitted)
    assert not requests.respond('selection','b'*32)


def test_stop_wins_over_a_reply(tmp_path):
    module=interaction()
    stopped=False
    requests=None
    def check_cancel():
        if stopped: raise RuntimeError('synthetic stop')
    def emit(event):
        nonlocal stopped
        module.write_reply(tmp_path,'synthetic-job',event['request_id'],{'overwrite':True})
        requests.respond('overwrite',event['request_id'])
        stopped=True
    requests=module.Requests(tmp_path,'synthetic-job',emit,check_cancel)
    with pytest.raises(RuntimeError,match='synthetic stop'):
        requests.request('overwrite',{'files':['resume.xlsx']},99)


def test_request_path_and_message_cannot_cross_jobs(tmp_path):
    module=interaction()
    with pytest.raises(ValueError):
        module.write_reply(tmp_path,'synthetic-job','../other',{})
    module.write_reply(tmp_path,'synthetic-job','c'*32,{'selected_ids':['synthetic-return']})
    with pytest.raises(ValueError,match='job|bound'):
        module.read_message(tmp_path,'different-job','c'*32,reply=True)


def test_selection_rejects_ambiguous_inventory_identifiers():
    run=fixture_run()
    run['records'][1]['record_id']=run['records'][0]['record_id']
    with pytest.raises(ValueError,match='identifier|duplicate'):
        interaction().select_records(run,[run['records'][0]['record_id']])


def test_wrong_kind_and_duplicate_reply_cannot_release_a_request(tmp_path):
    module=interaction()
    requests=None
    def emit(event):
        assert not requests.respond('overwrite',event['request_id'])
        module.write_reply(tmp_path,'synthetic-job',event['request_id'],{'selected_ids':['synthetic-return']})
        assert requests.respond('selection',event['request_id'])
        assert not requests.respond('selection',event['request_id'])
    requests=module.Requests(tmp_path,'synthetic-job',emit,lambda:None)
    assert requests.request('selection',{'records':[]},20)=={'selected_ids':['synthetic-return']}


def test_waiting_request_has_a_deadline_without_defaulting_to_all_records(tmp_path):
    module=interaction()
    requests=module.Requests(tmp_path,'synthetic-job',lambda event:None,lambda:None)
    with pytest.raises(TimeoutError):
        requests.request('selection',{'records':[]},20,timeout=0.01)


def test_reply_is_single_use_and_never_overwrites_a_prior_response(tmp_path):
    module=interaction()
    module.write_reply(tmp_path,'synthetic-job','d'*32,{'overwrite':False})
    with pytest.raises(FileExistsError):
        module.write_reply(tmp_path,'synthetic-job','d'*32,{'overwrite':True})
    assert module.read_message(tmp_path,'synthetic-job','d'*32,reply=True)=={'overwrite':False}


def test_message_replaced_between_inspection_and_open_is_rejected_before_read(tmp_path,monkeypatch):
    from pathlib import Path
    module=interaction()
    request_id='e'*32
    module.write_reply(tmp_path,'synthetic-job',request_id,{'overwrite':False})
    replies=list(tmp_path.glob('*.reply.json'))
    assert len(replies)==1
    target=replies[0]
    replacement=tmp_path/'replacement.json'
    replacement.write_text(json.dumps({'job_id':'synthetic-job','request_id':request_id,
        'payload':{'overwrite':True}}),encoding='utf-8')
    original=Path.open
    swapped=False
    def race(path,mode='r',*args,**kwargs):
        nonlocal swapped
        if path==target and mode=='rb':
            replacement.replace(target)
            swapped=True
        return original(path,mode,*args,**kwargs)
    monkeypatch.setattr(Path,'open',race)
    with pytest.raises(ValueError,match='changed|identity|path'):
        module.read_message(tmp_path,'synthetic-job',request_id,reply=True)
    assert swapped