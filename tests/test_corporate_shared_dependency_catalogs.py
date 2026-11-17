"""Source-proven L2/L4/L9/Induk dependencies in the ONE passive producer."""
from copy import deepcopy
import json

import pytest

import coretax_corporate_projection as projection
import coretax_json as adapter
import support_json_corpus as corpus
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from support_json_network import Context, Frame, Request, Response, exchange
from test_json_capture import Page, SCOPE
from test_corporate_component_lifetime import selected, DETAIL
from test_corporate_l7_native import bindings, packet as primary, selected as corpus_record
from test_corporate_l3_native import packet
from test_corporate_passive_catalogs import BASE, KINDS as L10_KINDS, catalog
from test_corporate_reference_binding import case as binding_case
from test_corporate_l11c_native import L11C_PINS


L4_KINDS = ('TAX_OBJECT_CODE', 'INCOME_EXCLUDED_FROM_TAX_FOR_CIT')
L2_KINDS = ('COUNTRY_CODE', 'RELATED_PERSON_TYPE')
L9_KINDS = ('TANGIBLE_ASSET', 'GROUP_OF_BUILDINGS', 'INTANGIBLE_ASSET',
            'COMMERCIAL_METHOD', 'FISCAL_METHOD')
INDUK_KINDS = ('CIT_TAX_RATE',)
ADDITIONAL_KINDS = (*L4_KINDS, 'RELATED_PERSON_TYPE', *L9_KINDS, *INDUK_KINDS)


@pytest.mark.parametrize('kind', ADDITIONAL_KINDS)
def test_original_singleton_bytes_survive_capture_both_readers_and_native_adapter(tmp_path, kind):
    context, record = Context(), selected()
    page = Page(context, DETAIL)
    record['detail_url'] = DETAIL
    value = catalog(kind)
    value[0]['Checksum'] = 'SYNTHETIC_ORIGINAL_METADATA'
    value[0]['Details'][0]['UnusedMetadata'] = {'Original': [None, False, '001']}
    raw = json.dumps({'IsSuccessful': True, 'Payload': value}).encode()
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        response = exchange(context, page, raw=raw, method='GET', url=BASE + kind)
        capture.bind_detail_page(page)
        saved = capture.drain()
        assert saved['complete'] and saved['counts']['accepted'] == 1
        bodies = list(capture.iter_bodies())
        assert response.reads == 1 and bodies[0]['body'] == raw
        assert checkpoint_bodies(tmp_path, saved, record, SCOPE) == bodies
    other = packet({'IsSuccessful': True, 'Payload': value}, 2, BASE + kind, None, method='GET')
    other['context'].pop('component_lifetime')
    result = adapter.adapt_corporate_detail([primary(), other], corpus_record(), corpus.SCOPE, bindings())
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert any(e.get('reference_catalog') == kind for e in result['provenance']['events'])
    original = adapter._corporate_json(raw)['Payload']
    before = deepcopy(original)
    projected = projection._project_corporate_catalog(original, kind=kind)
    assert projected['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
    assert projected['selected']['SYN_CODE']['path'] == [0, 'Details', 1, 'CodeDescription']
    assert projected['requires_vendor'] and original == before


@pytest.mark.parametrize('kind', ADDITIONAL_KINDS)
@pytest.mark.parametrize('defect', ['batch', 'checksum', 'query', 'slash', 'encoded', 'locale',
    'post', 'body', 'subframe', 'other-tax', 'other-sheet', 'foreign-tab', 'resource', 'description'])
def test_no_alias_or_cross_owner_transport_permission(tmp_path, kind, defect):
    context, record = Context(), selected()
    page = Page(context, DETAIL)
    url, target, options = BASE + kind, page, {}
    if defect == 'batch': url += ',COUNTRY_CODE'
    elif defect == 'checksum': url += '+SYNTHETIC'
    elif defect == 'query': url += '?SYNTHETIC=1'
    elif defect == 'slash': url += '/'
    elif defect == 'encoded': url = url.replace(kind, '%' + format(ord(kind[0]), '02X') + kind[1:])
    elif defect == 'locale': url = url.replace('/id-ID/', '/en-US/')
    elif defect == 'post': options['method'] = 'POST'
    elif defect == 'body': options['post'] = {'SYNTHETIC': True}
    elif defect == 'subframe': options['frame'] = Frame(page, parent=page.main_frame)
    elif defect == 'other-tax': record['source_fields']['TaxTypeCode'] = 'VAT_VAT'
    elif defect == 'other-sheet': record['source_fields']['ReturnSheetTypeCode'] = 'VAT_VATR'
    elif defect == 'foreign-tab': target = Page(context, DETAIL)
    elif defect == 'description': url = BASE.rsplit('/id-ID/', 1)[0] + '/getdescription'
    with DetailJsonCapture(context, page, record, SCOPE, tmp_path) as capture:
        if defect == 'resource':
            req = Request(page, url=url, method='GET')
            req.resource_type = 'document'
            response = Response(req)
            context.emit('request', req)
            context.emit('response', response)
            context.emit('requestfinished', req)
        else:
            response = exchange(context, target, url=url, method=options.pop('method', 'GET'), **options)
        capture.bind_detail_page(page)
        assert capture.drain()['responses'] == []
        assert response.reads == 0 and capture.request_observations() == []


@pytest.mark.parametrize('kind', ADDITIONAL_KINDS)
@pytest.mark.parametrize('defect', ['missing-body-fact', 'method', 'body', 'clock', 'attempt',
                                  'locale', 'full-snapshot'])
def test_new_dependency_transport_contradictions_stay_fatal_unbound(kind, defect):
    value = catalog(kind)
    other = packet({'IsSuccessful': True, 'Payload': value}, 2, BASE + kind, None, method='GET')
    other['context'].pop('component_lifetime')
    raw = [primary(), other]
    if defect == 'missing-body-fact': del other['context']['request_json']
    elif defect == 'method': other['context']['method'] = 'POST'
    elif defect == 'body': other['context']['request_json'] = {}
    elif defect == 'clock': other['context']['clock_interval'] = {
        'attempt': corpus.ATTEMPT, 'start_ms': 0, 'end_ms': 1, 'timezone': 'Asia/Jakarta'}
    elif defect == 'attempt': other['context']['attempt'] = 'b' * 32
    elif defect == 'locale':
        value[0]['Details'][0]['language'] = 'en-US'
        raw[1] = packet({'IsSuccessful': True, 'Payload': value}, 2, BASE + kind, None, method='GET')
        raw[1]['context'].pop('component_lifetime')
    else:
        value[0]['UnusedMetadata'] = {'Original': 'CHANGED'}
        changed = packet({'IsSuccessful': True, 'Payload': value}, 3, BASE + kind, None, method='GET')
        changed['context'].pop('component_lifetime')
        raw.append(changed)
    with pytest.raises(adapter.JsonSafetyError):
        adapter.adapt_corporate_detail(raw, corpus_record(), corpus.SCOPE, [])


@pytest.mark.parametrize('kind', (*L4_KINDS, *L9_KINDS, *INDUK_KINDS))
def test_ordinary_dependencies_keep_display_index_active_version_and_attempt_clock(kind):
    value = catalog(kind)
    rows = value[0]['Details']
    for row, index, until in zip(rows, (1, 2), ('2027-01-01', '2028-01-01')):
        row.update(ParameterData=json.dumps({'DisplayIndex': index}),
                   ValidFrom='2025-01-01', ValidTo=until)
    clock = {'attempt': corpus.ATTEMPT, 'start_ms': 1794873600000,
             'end_ms': 1794873601000, 'timezone': 'Asia/Jakarta'}
    before = deepcopy(value)
    result = projection._project_corporate_catalog(value, kind=kind, clock_interval=clock)
    assert result['lookups'] == {'SYN_CODE': 'Z SYNTHETIC LATER'}
    assert result['selected']['SYN_CODE']['clock_interval'] == clock
    assert result['selected']['SYN_CODE']['catalog_order_rule'] == 'reviewed-cache-display-index-integer'
    assert value == before
    with pytest.raises(adapter._UnsupportedMetadata, match='clock_dependent'):
        projection._project_corporate_catalog(value, kind=kind)
    clock['end_ms'] = 1830000000000
    with pytest.raises(adapter._UnsupportedMetadata, match='unstable'):
        projection._project_corporate_catalog(value, kind=kind, clock_interval=clock)


def test_position_first_ordered_find_is_not_active_version_selection():
    value = catalog('RELATED_PERSON_TYPE')
    rows = value[0]['Details']
    rows[1].update(ValidFrom='2020-01-01', ValidTo='2021-01-01')
    # A sorts before Z, even though its validity ended. Position never invokes
    # getActiveReferenceDataValue. L2 separately refuses requires_vendor=True.
    result = projection._project_corporate_catalog(value, kind='RELATED_PERSON_TYPE')
    chosen = result['selected']['SYN_CODE']
    assert result['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
    assert chosen['rule'] == 'reviewed-related-person-first-ordered-code-match'
    assert chosen['path'] == [0, 'Details', 1, 'CodeDescription']
    assert result['requires_vendor'] and 'clock_interval' not in chosen
    rows[0]['ParameterData'] = '{"DisplayIndex":1}'
    rows[1]['ParameterData'] = '{"DisplayIndex":2}'
    reordered = projection._project_corporate_catalog(value, kind='RELATED_PERSON_TYPE')
    assert reordered['lookups'] == {'SYN_CODE': 'Z SYNTHETIC LATER'}
    assert reordered['selected']['SYN_CODE']['path'] == [0, 'Details', 0, 'CodeDescription']
    value[0]['Details'] = [rows[1]]
    unique = projection._project_corporate_catalog(value, kind='RELATED_PERSON_TYPE')
    assert unique['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
    assert not unique['requires_vendor']


@pytest.mark.parametrize('kind', ADDITIONAL_KINDS)
def test_new_dependencies_use_original_sequence_inventory_and_earliest_packet(kind):
    event, packets, refs = binding_case(kinds=(kind,))
    packets[9] = deepcopy(packets[2])
    packets[9]['event']['sequence'] = 9
    refs[0]['sequences'] = [9, 2]
    before = deepcopy((event, packets, refs))
    result = projection.bind_corporate_reference_catalogs(refs, dict(reversed(list(packets.items()))),
        kinds=(kind,), event=event, builds=L11C_PINS)
    assert result[kind]['source']['sequence'] == 2 and result[kind]['sequences'] == [2, 9]
    assert result[kind]['lookups'] == {'SYN_CODE': 'A SYNTHETIC FIRST'}
    assert (event, packets, refs) == before
    refs[0]['sequences'] = [9]
    with pytest.raises(adapter._UnsupportedMetadata, match='missing_or_failed'):
        projection.bind_corporate_reference_catalogs(refs, packets, kinds=(kind,), event=event, builds=L11C_PINS)


def test_closed_consumer_inventories_never_grant_unrelated_form_dependencies():
    for name, kinds in (('CORPORATE_L10_REFERENCE_URLS', L10_KINDS),
                        ('CORPORATE_L4_REFERENCE_URLS', L4_KINDS),
                        ('CORPORATE_L2_REFERENCE_URLS', L2_KINDS),
                        ('CORPORATE_L9_REFERENCE_URLS', L9_KINDS),
                        ('CORPORATE_INDUK_REFERENCE_URLS', INDUK_KINDS)):
        inventory = getattr(adapter, name, None)
        assert inventory == {kind: BASE + kind for kind in kinds}
        assert all(adapter.CORPORATE_REFERENCE_REQUESTS[url] == (kind,) for kind, url in inventory.items())
    assert BASE + 'RELATED_PERSON_SUBTYPE' not in adapter.CORPORATE_REFERENCE_REQUESTS
    with pytest.raises(adapter._UnsupportedMetadata):
        projection._project_corporate_catalog(catalog('RELATED_PERSON_SUBTYPE'), kind='RELATED_PERSON_SUBTYPE')
