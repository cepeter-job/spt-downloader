"""L10-D original evidence is not native eligibility or a display projection."""
from copy import deepcopy
import json

from openpyxl import load_workbook
import pytest

import coretax
from coretax_build_pins import load_build_pins
from coretax_json import JsonSafetyError, adapt_corporate_detail, has_audit_dump_tables
import support_json_corpus as corpus
from test_corporate_l7_native import FRAME, REQUEST, selected
from test_corporate_l10d_custody import ROOT, CHECKS, DATES, source


DETAIL = FRAME + '?view=true'
PROVIDERS = tuple(corpus.ORIGIN + '/returnsheets/id-ID/' + name for name in (
    '525.c5690c441d8dbc45.js', 'main.16a01374a2a1ece5.js', 'vendor.c32c4ee39d966e30.js'))


def envelope():
    form = corpus.current_form()
    form.update(source())
    form['MainFormData']['IsObligationTransferPricing'] = 1
    return {'IsSuccessful': True, 'Payload': {'TIN': corpus.NPWP, 'PeriodYear': 2025,
        'IsDraft': True, 'IsObligationTransferPricing': 1,
        'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PreviousFormData': None, 'LastSubmittedFormData': None, 'CurrentFormData': corpus.wire(form)}}


def packet(value=None, sequence=1):
    raw = corpus.packet(envelope() if value is None else value, sequence, request=dict(REQUEST))
    raw['context'].update(frame_url=DETAIL, component_lifetime={
        'kind': 'corporate-submitted-spa-v1', 'attempt': corpus.ATTEMPT,
        'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': DETAIL,
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True})
    return raw


def bindings(*, custody=True):
    forms = [{'name': 'Induk', 'paths': [['MainFormData']], 'grids': [],
        'primary': {'endpoint': corpus.PRIMARY_URL, 'request_json': dict(REQUEST)}},
        {'name': 'L10-D', 'paths': [[ROOT]], 'grids': []}]
    if custody:
        forms[1]['original_custody'] = {'kind': 'corporate-l10d-originals-v1',
            'builds': {url: load_build_pins().get(url) for url in PROVIDERS},
            'route': DETAIL, 'owner_binding': 'observed-enabled-after-induk-v1'}
    return forms


def test_original_custody_is_retained_but_final_selection_is_explicitly_unsupported():
    record, raw, observed = selected(), packet(), bindings()
    before = deepcopy((record, raw, observed))
    result = adapt_corporate_detail([raw], record, corpus.SCOPE, observed)
    assert not result['eligible'] and result['sections'] == []
    assert result['reason'] == 'unverified_corporate_l10d_final_selection_custody'
    candidate, = result['provenance']['non_display_originals']
    assert candidate['form'] == 'L10-D' and candidate['native_admission'] is False
    assert candidate['kind'] == 'corporate-l10d-originals-v1'
    assert candidate['builds'] == observed[1]['original_custody']['builds']
    assert candidate['source'] == {'response_sequence': 1, 'body_sha256': raw['context']['sha256'],
        'attempt': corpus.ATTEMPT, 'container': ['Payload', 'CurrentFormData'], 'path': [ROOT]}
    assert len(candidate['originals']['values']) == 14
    assert {value['path'][-1] for value in candidate['predicate_values']} == {
        'IsObligationTransferPricing', 'PreviousFormData', 'LastSubmittedFormData',
        'ReturnSheetStatusCode', 'ReturnSheetModel'}
    assert len(candidate['predicate_values']) == 6  # the two flags have distinct owners
    assert any(item['type'] == 'null' and item['path'] == [ROOT, DATES[0]]
               for item in candidate['originals']['values'])
    assert (record, raw, observed) == before


@pytest.mark.parametrize('owner', ['outer', 'current'])
@pytest.mark.parametrize('value', [None, False, True, '1', 0, 2, corpus.Number('1.0')])
def test_unreviewed_flag_profile_does_not_turn_into_native_permission(owner, value):
    value_source = envelope()
    root = json.loads(value_source['Payload']['CurrentFormData'])
    (value_source['Payload'] if owner == 'outer' else root['MainFormData'])['IsObligationTransferPricing'] = value
    value_source['Payload']['CurrentFormData'] = corpus.wire(root)
    result = adapt_corporate_detail([packet(value_source)], selected(), corpus.SCOPE, bindings())
    assert not result['eligible'] and 'unverified_corporate_l10d_source_profile' in result['reason']


@pytest.mark.parametrize('key', [*CHECKS, *DATES])
def test_missing_leaf_remains_unsupported_in_actual_adapter(key):
    value_source = envelope()
    root = json.loads(value_source['Payload']['CurrentFormData'])
    del root[ROOT][key]
    value_source['Payload']['CurrentFormData'] = corpus.wire(root)
    result = adapt_corporate_detail([packet(value_source)], selected(), corpus.SCOPE, bindings())
    assert not result['eligible'] and 'unsupported_corporate_l10d_original_shape' in result['reason']


@pytest.mark.parametrize('defect', ['missing-pin', 'wrong-pin', 'empty-pins', 'null-pin',
    'missing-lifetime', 'no-induk', 'route', 'status', 'model', 'previous', 'last-submitted',
    'outer-missing', 'current-missing', 'missing-header', 'extra-child', 'empty-root'])
def test_incomplete_source_or_pin_proof_never_receives_a_custody_candidate(defect):
    value_source, observed = envelope(), bindings()
    payload = value_source['Payload']
    root = json.loads(payload['CurrentFormData'])
    if defect == 'missing-pin': del observed[1]['original_custody']['builds'][PROVIDERS[0]]
    elif defect == 'wrong-pin': observed[1]['original_custody']['builds'][PROVIDERS[0]] = 'a' * 64
    elif defect == 'empty-pins': observed[1]['original_custody']['builds'] = {}
    elif defect == 'null-pin': observed[1]['original_custody']['builds'][PROVIDERS[0]] = None
    elif defect == 'no-induk': observed.reverse()
    elif defect == 'route': observed[1]['original_custody']['route'] = FRAME
    elif defect == 'status': payload['ReturnSheetStatusCode'] = None
    elif defect == 'model': payload['ReturnSheetModel'] = 'AMENDMENT'
    elif defect == 'previous': payload['PreviousFormData'] = '{}'
    elif defect == 'last-submitted': del payload['LastSubmittedFormData']
    elif defect == 'outer-missing': del payload['IsObligationTransferPricing']
    elif defect == 'current-missing': del root['MainFormData']['IsObligationTransferPricing']
    elif defect == 'missing-header': del payload['TIN']
    elif defect == 'extra-child': root[ROOT]['Other'] = None
    elif defect == 'empty-root': root[ROOT] = {}
    payload['CurrentFormData'] = corpus.wire(root)
    raw = packet(value_source)
    record = selected()
    if defect == 'status': record['source_fields'].pop('ReturnSheetStatusCode')
    if defect == 'missing-lifetime': del raw['context']['component_lifetime']
    result = adapt_corporate_detail([raw], record, corpus.SCOPE, observed)
    assert not result['eligible'] and not result['provenance'].get('non_display_originals')


@pytest.mark.parametrize('defect', ['null', 'extra', 'foreign', 'disabled', 'projection', 'extra-path',
                                     'primary', 'responses', 'grids', 'dependencies'])
def test_original_custody_marker_is_closed_at_the_binding_boundary(defect):
    observed = bindings()
    item = observed[1]
    if defect == 'null': item['original_custody'] = None
    elif defect == 'extra': item['original_custody']['native_admission'] = True
    elif defect == 'foreign': item['name'] = 'L10-B'
    elif defect == 'disabled': item['disabled'] = True
    elif defect == 'projection': item['projection'] = {'kind': 'dummy'}
    elif defect == 'extra-path': item['paths'].append(['L10bFormData'])
    else: item[defect] = {'dummy': True} if defect == 'primary' else [{'dummy': True}]
    with pytest.raises(JsonSafetyError):
        adapt_corporate_detail([packet()], selected(), corpus.SCOPE, observed)


@pytest.mark.parametrize('with_custody', [False, True])
@pytest.mark.parametrize('defect', ['tin', 'year', 'secret', 'changed-snapshot'])
def test_original_custody_never_masks_identity_privacy_or_snapshot_failures(with_custody, defect):
    value_source = envelope()
    if defect == 'tin': value_source['Payload']['TIN'] = '0000000000000002'
    elif defect == 'year': value_source['Payload']['PeriodYear'] = 2024
    elif defect == 'secret':
        root = json.loads(value_source['Payload']['CurrentFormData'])
        root[ROOT]['Authorization'] = 'secret'
        value_source['Payload']['CurrentFormData'] = corpus.wire(root)
    elif defect == 'changed-snapshot': value_source['Payload']['IsObligationTransferPricing'] = 0
    packets = [packet(value_source)]
    if defect == 'changed-snapshot': packets.insert(0, packet(sequence=2))
    with pytest.raises(JsonSafetyError):
        adapt_corporate_detail(packets, selected(), corpus.SCOPE, bindings(custody=with_custody))


def test_custody_does_not_bypass_dump_gate_or_change_excluded_workbook_sheets(tmp_path):
    result = adapt_corporate_detail([packet()], selected(), corpus.SCOPE, bindings(custody=False))
    assert result['eligible']
    l10d, = [section for section in result['sections'] if section['name'] == 'L10-D']
    assert l10d['fields'] == [] and len(l10d['tables'][0]['rows']) == 12
    assert has_audit_dump_tables([l10d]) is True
    forged = deepcopy(l10d)
    forged['original_custody'] = {'kind': 'corporate-l10d-originals-v1', 'native_admission': True}
    assert has_audit_dump_tables([forged]) is True
    record = selected()
    record['meta']['Masa Pajak'] = '01122025'
    record.update(capture_complete=True, sections=[*result['sections'],
        {'name': 'L10-B', 'fields': [], 'tables': [], 'text': 'SYNTHETIC EXCLUDED'}])
    before = deepcopy(record['sections'])
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
        'inventory_complete': True, 'complete': True, 'errors': [], 'records': [record]}
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    filename, = [name for name in run['output_files'] if name != 'resume.xlsx']
    book = load_workbook(tmp_path / filename)
    try:
        assert book.sheetnames == ['Induk']
    finally:
        book.close()
    assert record['sections'] == before
