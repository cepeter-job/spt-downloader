"""Bind a DOM-selected corporate record to fresh original listing bytes."""
from copy import deepcopy
import hashlib,json
from types import SimpleNamespace
import pytest
import coretax_browser as driver
from coretax_json import adapt_inventory_page
import support_browser_protocol as protocol
import support_json_corpus as corpus
from support_json_hybrid import Scenario
from support_json_network import Request
from test_json_inventory import api_row, context


@pytest.mark.parametrize('occupied',[False,True])
def test_corporate_identity_is_saved_before_view_or_fails_closed(tmp_path,monkeypatch,occupied):
    case=Scenario(tmp_path,monkeypatch)
    row=api_row(corpus.RECORD_ID)
    row.update(AggregateIdentifier=corpus.AGGREGATE_ID,
               TaxpayerAggregateIdentifier=corpus.TAXPAYER_ID,TaxPeriodCode='01122025')
    ctx=context()
    ctx.update(npwp=corpus.NPWP,year=2025,taxpayer_id=corpus.TAXPAYER_ID,
               source_url=corpus.LIST_URL,frame_url=corpus.LIST_URL)
    ctx['request']['TaxpayerAggregateIdentifier']=corpus.TAXPAYER_ID
    ctx['lookup_labels']['TaxPeriodCode']={'01122025':'Januari - Desember 2025'}
    original=json.dumps({'IsSuccessful':True,'Payload':{'Data':[row],'TotalRecords':1}}).encode()
    adapted=adapt_inventory_page(original,ctx)
    assert adapted['eligible']
    case.record['meta']=deepcopy(adapted['rows'][0]['meta'])
    case.record.pop('source_fields');case.record.pop('source_identity')
    monkeypatch.setattr(protocol,'META',dict(case.record['meta']))
    listing_url=driver.ORIGIN+'/returnsheet/api/returnsheetssubmitted'
    def goto(url,**kwargs):
        case.page.commit_navigation(url)
        request=Request(case.page,url=listing_url,post=deepcopy(ctx['request']))
        case.page.emit_grid_response(SimpleNamespace(url=listing_url,request=request,status=200,
                      headers={'content-type':'application/json'},body=lambda:original))
    monkeypatch.setattr(case.page,'goto',goto)
    real_view=protocol.View.evaluate;bound_before=[]
    def view(control,script):
        evidence=case.record.get('source_identity',{})
        relative=evidence.get('relative_path','')
        bound_before.append(bool(relative) and relative.startswith('listing-responses/corporate-identity-')
                            and evidence.get('body_sha256')==hashlib.sha256(original).hexdigest()
                            and (tmp_path/relative).read_bytes()==original)
        return real_view(control,script)
    monkeypatch.setattr(protocol.View,'evaluate',view)
    if occupied:(tmp_path/'listing-responses').write_bytes(b'SYNTHETIC OCCUPIED PATH')
    result=case.collect()
    if occupied:
        assert case.page.view_calls==0
        assert not result['complete'] and result['errors']
        assert (tmp_path/'listing-responses').read_bytes()==b'SYNTHETIC OCCUPIED PATH'
        assert 'source_identity' not in case.record
        assert not any(case.page.context.listeners.values())
        assert not case.page.listeners.get('response')
        return
    else:
        assert bound_before==[True]
        assert result['complete'],result['errors']
        assert case.record['source_identity']['aggregate_id']==corpus.AGGREGATE_ID
        assert case.record['detail_source']['used']=='json'
        assert case.dom_calls==[]
        restored=driver.read_detail_checkpoint(tmp_path/'returns/0001.json',case.record,corpus.SCOPE,detail_source='json-first')
        assert restored and restored['capture_complete']
    case.assert_closed()
