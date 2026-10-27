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
