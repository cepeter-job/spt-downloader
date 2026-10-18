"""Reference GET admission never bypasses the existing byte/identity checks."""
from copy import deepcopy
import hashlib

import pytest

from coretax_json import JsonSafetyError, ORIGIN
from coretax_masa_json import adapt_masa_detail
from masa_json_fixtures import SCOPE, packet
from test_pph21_json_primary import TAX, case, source

URL = ORIGIN + '/referencedata/api/currentreferencedata/id-ID/EBUPOT_TAX_CERTIFICATE,COUNTRY_CODE,EBUPOT_STATUS'
CATALOGS = [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
    {'Code': '0001', 'CodeDescription': 'SYNTHETIC LABEL', 'ValidTo': None}]}
    for kind in ('EBUPOT_TAX_CERTIFICATE', 'COUNTRY_CODE', 'EBUPOT_STATUS')]


def reference_packet(*, sequence=2):
    item = packet(TAX, CATALOGS, sequence=sequence)
    item['context'].update(url=URL, method='GET', request_json=None)
    return item


def test_reference_packet_custody_is_accepted_but_does_not_grant_native_eligibility():
    record, outer, _ = case()
    bodies = [source(outer), reference_packet()]
    before = deepcopy(bodies)
    result = adapt_masa_detail(bodies, record=record, scope=SCOPE, observed_forms=[])
    assert result['eligible'] is False and result['coverage']['complete'] is False
    assert len(result['provenance']['events']) == 2
    assert result['provenance']['events'][1]['url'] == URL
    assert bodies == before


@pytest.mark.parametrize('defect', ['hash', 'scope', 'frame', 'attempt', 'method', 'request-body',
                                     'endpoint', 'status', 'secret'])
def test_reference_packet_safety_cannot_be_hidden_by_missing_observer(defect):
    record, outer, _ = case()
    item = reference_packet()
    ctx = item['context']
    if defect == 'hash':
        ctx['sha256'] = '0' * 64
    elif defect == 'scope':
        ctx['scope'] = [SCOPE[0], 2024, 'period']
    elif defect == 'frame':
        ctx['frame_url'] = ORIGIN + '/returnsheets/id-ID/foreign'
    elif defect == 'attempt':
        ctx['attempt'] = 'b' * 32
    elif defect == 'method':
        ctx['method'] = 'POST'
    elif defect == 'request-body':
        ctx['request_json'] = {'unexpected': True}
    elif defect == 'endpoint':
        ctx['url'] = URL + '?other=1'
    elif defect == 'status':
        ctx['status'] = 403
    else:
        item['body'] = b'{"Authorization":"synthetic-secret-marker"}'
        ctx.update(bytes=len(item['body']), sha256=hashlib.sha256(item['body']).hexdigest())
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([source(outer), item], record=record, scope=SCOPE, observed_forms=[])


@pytest.mark.parametrize('tax', ['PPN', 'PPh Unifikasi'])
def test_reference_get_does_not_broaden_other_tax_family_packet_rules(tax):
    record, _, _ = case()
    record['meta']['Jenis Pajak'] = tax
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([reference_packet()], record=record, scope=SCOPE, observed_forms=[])


def test_separate_model_catalog_get_preserves_packet_custody():
    record, outer, _ = case()
    item = reference_packet()
    item['context']['url'] = URL.rsplit('/', 1)[0] + '/RETURN_SHEET_MODEL'
    item['body'] = b'{"IsSuccessful":true,"Payload":[{"ReferenceDataType":"RETURN_SHEET_MODEL","Details":[]}]}'
    item['context'].update(bytes=len(item['body']), sha256=hashlib.sha256(item['body']).hexdigest())
    result = adapt_masa_detail([source(outer), item], record=record, scope=SCOPE, observed_forms=[])
    assert not result['eligible'] and len(result['provenance']['events']) == 2


def test_changed_reference_snapshot_within_one_attempt_is_fatal():
    record, outer, _ = case()
    first, changed = reference_packet(), reference_packet(sequence=3)
    changed['body'] = changed['body'].replace(b'SYNTHETIC LABEL', b'DIFFERENT LABEL')
    changed['context'].update(bytes=len(changed['body']), sha256=hashlib.sha256(changed['body']).hexdigest())
    with pytest.raises(JsonSafetyError):
        adapt_masa_detail([source(outer), first, changed], record=record, scope=SCOPE, observed_forms=[])
