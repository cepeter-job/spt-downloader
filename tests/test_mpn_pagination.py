"""Exact total and original null-Index continuation contracts; synthetic only."""
from copy import deepcopy
import json

import pytest

from coretax_mpn import decode_mpn, MpnSafetyError, mpn_custody
from test_mpn import scope_run, payment_source
from test_mpn_capture_protocol import SyntheticUI, snapshot


def payload(count, total, *, index=True):
    value = {'Data':[{} for _ in range(count)], 'TotalRecords':total}
    if index:
        value['Index'] = None
    return decode_mpn(json.dumps(value).encode())


@pytest.mark.parametrize('size', [10,25,50])
def test_frontier_total_requires_original_terminal_page(size):
    from coretax_mpn import validate_page_total
    previous = None
    for first,count,total in [(0,size,size+1),(size,size,2*size+1),(2*size,3,2*size+3)]:
        previous = validate_page_total(payload(count,total),first,size,previous,mode='frontier-v1')
    assert previous == 2*size+3


@pytest.mark.parametrize('first,count,total,previous,index', [
    (0,10,12,None,True), (0,10,11,None,False), (10,10,22,11,True),
    (10,10,21,12,True), (10,1,12,11,True), (10,0,10,11,True),
    (20,3,23,11,True)])
def test_frontier_refuses_arbitrary_totals_missing_index_and_gaps(first,count,total,previous,index):
    from coretax_mpn import validate_page_total
    with pytest.raises(MpnSafetyError):
        validate_page_total(payload(count,total,index=index),first,10,previous,mode='frontier-v1')


def test_legacy_fixed_total_still_refuses_change_and_unknown_mode():
    from coretax_mpn import validate_page_total
    for mode,total in [('fixed-v1',21),('unknown',11)]:
        with pytest.raises(MpnSafetyError):
            validate_page_total(payload(10,total),10,10,11,mode=mode)


def test_exact_eleven_rows_can_close_the_initial_frontier_without_rewriting_totals():
    from coretax_mpn import validate_page_total
    assert validate_page_total(payload(10,11),0,10,mode='frontier-v1') == 11
    assert validate_page_total(payload(1,11),10,10,11,mode='frontier-v1') == 11


def frontier_snapshot(rows,first,total):
    result = snapshot(rows,first=first,total=total)
    result['raw'] = result['raw'].replace(b'"Payload":{',b'"Payload":{"Index":null,',1)
    result['total_mode'] = 'frontier-v1'
    return result


@pytest.mark.parametrize('terminal', [True,False])
def test_collector_and_held_custody_require_a_complete_frontier(monkeypatch,tmp_path,terminal):
    import coretax_mpn_browser as module
    header,_ = payment_source()
    headers=[]
    for i in range(23):
        item=deepcopy(header)
        item['RecordId']=f'00000000-0000-4000-8000-{i+20:012d}'
        headers.append(item)
    class UI(SyntheticUI):
        children={h['RecordId']:[] for h in headers}
        def list_pages(self,max_pages):
            yield frontier_snapshot(headers[:10],0,11)
            yield frontier_snapshot(headers[10:20],10,21)
            if terminal:
                yield frontier_snapshot(headers[20:],20,23)
    monkeypatch.setattr(module,'AccountingUI',UI)
    run=scope_run()
    module.collect_mpn(object(),run,tmp_path)
    assert (run['mpn']['status']=='COMPLETE') is terminal
    assert run['mpn']['headers'] == (23 if terminal else 20)
    with mpn_custody(run,tmp_path):
        pass
    if terminal:
        run['mpn']['bindings'][0]['total_mode']='unknown'
        with pytest.raises(MpnSafetyError):
            with mpn_custody(run,tmp_path):
                pass


def source_rows(count, *, parent=None):
    header,detail=payment_source()
    values=[]
    for index in range(count):
        row=deepcopy(detail if parent else header)
        row['RecordId']=f'00000000-0000-4000-8000-{index+100:012d}'
        if parent:
            row['HeaderRecordId']=parent
        values.append(row)
    return values


def owned_pages(ui,packets,*,kind='list',parent=None,cap=100,terminal_next=False):
    """Drive actual observer requests/responses and actual AccountingUI._pages."""
    from test_mpn_browser import Request,Response
    if parent:
        ui.observer.begin_detail(parent)
    def respond(packet):
        request=Request(ui.page,kind=kind,**({'parent':parent} if parent else {}))
        body=json.loads(request.post_data)
        body['First']=packet['first']
        request.post_data=json.dumps(body)
        ui.observer.on_request(request)
        response=Response(request)
        response._body=packet['raw']
        ui.observer.on_response(response)
        return ui.observer.latest[kind]
    class Owner:
        index=0
        clicks=0
        def locator(self,selector):
            assert selector=='.p-paginator-next:not([disabled]):not(.p-disabled)'
            return self
        def count(self):
            return int(self.index+1<len(packets) or terminal_next)
        def is_visible(self):
            return True
        def click(self,*,timeout):
            self.clicks+=1
            self.index+=1
            respond(packets[self.index])
    owner=Owner()
    return list(ui._pages(kind,owner,respond(packets[0]),cap)),owner


def test_actual_pages_derives_frontier_and_owns_paginator_until_terminal(tmp_path,monkeypatch):
    from test_mpn_source_custody import source_ui
    ui,_,_=source_ui(tmp_path,monkeypatch)
    rows=source_rows(23)
    packets=[frontier_snapshot(rows[:10],0,11),frontier_snapshot(rows[10:20],10,21),frontier_snapshot(rows[20:],20,23)]
    for packet in packets:
        packet.pop('total_mode')  # The production UI must derive it from original bytes.
    pages,owner=owned_pages(ui,packets)
    assert [page['total'] for page in pages]==[11,21,23]
    assert [page['total_mode'] for page in pages]==['frontier-v1']*3
    assert owner.clicks==2
    ui.observer.close()


def test_actual_detail_pages_choose_modes_independently_for_each_parent(tmp_path,monkeypatch):
    from test_mpn_source_custody import source_ui
    ui,_,_=source_ui(tmp_path,monkeypatch)
    parents=['00000000-0000-4000-8000-000000000020','00000000-0000-4000-8000-000000000021']
    fixed=snapshot(source_rows(2,parent=parents[0]),kind='detail',parent=parents[0])
    pages,_=owned_pages(ui,[fixed],kind='detail',parent=parents[0])
    assert [page['total_mode'] for page in pages]==['fixed-v1']
    rows=source_rows(12,parent=parents[1])
    packets=[snapshot(rows[:10],kind='detail',parent=parents[1],total=11),
             snapshot(rows[10:],kind='detail',parent=parents[1],first=10,total=12)]
    for packet in packets:
        packet['raw']=packet['raw'].replace(b'"Payload":{',b'"Payload":{"Index":null,',1)
    pages,owner=owned_pages(ui,packets,kind='detail',parent=parents[1])
    assert [page['total_mode'] for page in pages]==['frontier-v1']*2 and owner.clicks==1
    ui.observer.close()


@pytest.mark.parametrize('cap,terminal_next',[(1,False),(100,True)])
def test_actual_pages_refuse_cap_or_enabled_next_after_terminal(tmp_path,monkeypatch,cap,terminal_next):
    from test_mpn_source_custody import source_ui
    from coretax_mpn import MpnUnsupported
    ui,_,_=source_ui(tmp_path,monkeypatch)
    rows=source_rows(11)
    packets=[frontier_snapshot(rows[:10],0,11),frontier_snapshot(rows[10:],10,11)]
    with pytest.raises(MpnSafetyError if terminal_next else MpnUnsupported):
        owned_pages(ui,packets,cap=cap,terminal_next=terminal_next)
    ui.observer.close()


@pytest.mark.parametrize('terminal',[True,False])
def test_held_detail_frontier_is_independent_and_cannot_omit_terminal(monkeypatch,tmp_path,terminal):
    import coretax_mpn_browser as module
    headers=source_rows(2)
    parent=headers[1]['RecordId']
    details=source_rows(12,parent=parent)
    class UI(SyntheticUI):
        def list_pages(self,max_pages):
            yield snapshot(headers)
        def detail_pages(self,header,max_pages):
            if header['RecordId']!=parent:
                yield snapshot([],kind='detail',parent=header['RecordId']),None
                return
            for first,total,rows in [(0,11,details[:10])]+([(10,12,details[10:])] if terminal else []):
                packet=snapshot(rows,kind='detail',parent=parent,first=first,total=total)
                packet['raw']=packet['raw'].replace(b'"Payload":{',b'"Payload":{"Index":null,',1)
                packet['total_mode']='frontier-v1'
                yield packet,None
    monkeypatch.setattr(module,'AccountingUI',UI)
    run=scope_run()
    module.collect_mpn(object(),run,tmp_path)
    assert (run['mpn']['status']=='COMPLETE') is terminal
    with mpn_custody(run,tmp_path):
        pass
    if terminal:
        binding=[b for b in run['mpn']['bindings'] if b['kind']=='detail' and b['parent_id']==parent][-1]
        original=deepcopy(binding)
        for field,value in [('total_mode','fixed-v1'),('request',{**binding['request'],'Rows':25}),
                            ('request',{**binding['request'],'SortOrder':1})]:
            binding.clear();binding.update(deepcopy(original));binding[field]=value
            with pytest.raises(MpnSafetyError):
                with mpn_custody(run,tmp_path):
                    pass
