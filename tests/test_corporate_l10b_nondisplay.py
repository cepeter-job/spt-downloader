"""Synthetic closed non-display custody; all execution belongs to CI."""
from copy import deepcopy
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_corporate_projection as projection
from coretax_json import JsonSafetyError, adapt_corporate_detail, has_audit_dump_tables
import support_json_corpus as corpus
from test_corporate_l7_native import FRAME, REQUEST, selected

ROOT = 'L10bFormData'
KEYS = tuple('Question' + suffix for suffix in
             ('1a', '1b', '1c', '1d', '2a', '2b', '2c', '3a', '3b', '3c', '3d', '3e', '4a', '4b', '4c'))
ROUTE = FRAME + '?view=true'
KIND = 'corporate-l10b-nondisplay-v1'


def envelope(answer=False):
    root = corpus.current_form()
    root[ROOT] = dict.fromkeys(KEYS, answer)
    root['MainFormData']['IsTransactionWithRelated'] = 1
    return {'IsSuccessful': True, 'Payload': {
        'TIN': corpus.NPWP, 'PeriodYear': 2025, 'IsDraft': True,
        'IsTransactionWithRelated': 1, 'ReturnSheetStatusCode': 'SUBMITTED',
        'ReturnSheetModel': 'NORMAL', 'PreviousFormData': None, 'LastSubmittedFormData': None,
        'CurrentFormData': corpus.wire(root)}}


def observed():
    return [{'name': 'Induk', 'paths': [['MainFormData']], 'grids': [],
             'primary': {'endpoint': corpus.PRIMARY_URL, 'request_json': dict(REQUEST)},
             'projection': corpus.induk_projection(ROUTE)},
            {'name': 'L10-B', 'paths': [[ROOT]], 'grids': [], 'projection': {
                'kind': KIND, 'builds': dict(projection.L10B_BUILD_DIGESTS), 'route': ROUTE}}]


def packet(value=None, sequence=1):
    item = corpus.packet(envelope() if value is None else value, sequence, request=dict(REQUEST))
    item['context'].update(frame_url=ROUTE, component_lifetime={
        'kind': 'corporate-submitted-spa-v1', 'attempt': corpus.ATTEMPT,
        'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': ROUTE,
        'transition_count': 1, 'same_document': True, 'source_owner': True, 'detail_owner': True},
        corporate_l10b_lifetime={
            'kind': 'corporate-l10b-spa-v1', 'attempt': corpus.ATTEMPT,
            'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': ROUTE,
            'fresh_root': True, 'fresh_form': True, 'stable_root': True,
            'stable_form': True, 'enabled_boundaries': True})
    return item


def adapt(item=None, forms=None):
    return adapt_corporate_detail([packet() if item is None else item], selected(), corpus.SCOPE,
                                 observed() if forms is None else forms)


@pytest.mark.parametrize('answer', [False, True])
def test_closed_non_display_keeps_original_dump_all_typed_paths_and_no_fake_fields(answer):
    item, forms = packet(envelope(answer)), observed()
    before = deepcopy((item, forms))
    result = adapt(item, forms)
    assert result['eligible'], result['reason']
    section, = [s for s in result['sections'] if s['name'] == 'L10-B']
    assert section['fields'] == [] and section['text'] == ''
    table, = section['tables']
    assert table['headers'] == ['JSON path', 'JSON type', 'Source value']
    assert table['rows'] == [[f'/{ROOT}/{key}', 'boolean', answer] for key in KEYS]
    report, = [r for r in result['provenance']['projections'] if r['form'] == 'L10-B']
    answers = [v for v in report['values'] if v['path'][0] == ROOT]
    assert [v['path'] for v in answers] == [[ROOT, key] for key in KEYS]
    assert all(v['type'] == 'boolean' and v['value'] is answer for v in answers)
    assert all(v['container'] == ['Payload', 'CurrentFormData'] for v in answers)
    assert all(v['response_sequence'] == 1 and v['attempt'] == corpus.ATTEMPT for v in report['values'])
    for key in ('TIN', 'PeriodYear', 'ReturnSheetStatusCode', 'ReturnSheetModel',
                'PreviousFormData', 'LastSubmittedFormData', 'IsTransactionWithRelated'):
        assert any(v['path'] == [key] and v['container'] == ['Payload'] for v in report['values'])
    assert report['presence_facts'] and all(v['present'] is True for v in report['presence_facts'])
    assert has_audit_dump_tables(result['sections'])  # exclusion by name alone grants nothing
    assert not has_audit_dump_tables(result['sections'], provenance=result['provenance'])
    assert (item, forms) == before


@pytest.mark.parametrize('key', KEYS)
@pytest.mark.parametrize('value', [None, 0, 1, 'false', 'true', {}, [], corpus.Number('1.0')])
def test_every_question_refuses_unreviewed_types_without_truthy_coercion(key, value):
    value_source = envelope()
    root = json.loads(value_source['Payload']['CurrentFormData'])
    root[ROOT][key] = value
    value_source['Payload']['CurrentFormData'] = corpus.wire(root)
    result = adapt(packet(value_source))
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('defect', ['missing-question', 'extra-question', 'null-root', 'empty-root',
    'array-root', 'missing-history', 'missing-component', 'legacy-binding', 'wrong-kind', 'wrong-route',
    'wrong-pin', 'missing-pin', 'null-pins', 'no-induk', 'previous', 'last', 'missing-previous',
    'outer-null', 'outer-false', 'outer-zero', 'outer-missing', 'main-null', 'main-false',
    'main-zero', 'main-missing', 'header-missing', 'header-year-missing'])
def test_unreviewed_profiles_and_missing_lifetime_refuse_closed(defect):
    source, forms = envelope(), observed()
    root = json.loads(source['Payload']['CurrentFormData'])
    if defect == 'missing-question': del root[ROOT][KEYS[0]]
    elif defect == 'extra-question': root[ROOT]['Question5'] = False
    elif defect == 'null-root': root[ROOT] = None
    elif defect == 'empty-root': root[ROOT] = {}
    elif defect == 'array-root': root[ROOT] = []
    elif defect == 'legacy-binding': del forms[1]['projection']
    elif defect == 'wrong-kind': forms[1]['projection']['kind'] = 'corporate-l10d-nondisplay-v1'
    elif defect == 'wrong-route': forms[1]['projection']['route'] = FRAME
    elif defect == 'wrong-pin': forms[1]['projection']['builds'][projection.CIT_SOURCE] = '0' * 64
    elif defect == 'missing-pin': forms[1]['projection']['builds'] = {}
    elif defect == 'null-pins': forms[1]['projection']['builds'] = dict.fromkeys(projection.L10B_BUILD_DIGESTS)
    elif defect == 'no-induk': forms.reverse()
    elif defect == 'previous': source['Payload']['PreviousFormData'] = 'null'
    elif defect == 'last': source['Payload']['LastSubmittedFormData'] = '{}'
    elif defect == 'missing-previous': del source['Payload']['PreviousFormData']
    elif defect == 'header-missing': del source['Payload']['TIN']
    elif defect == 'header-year-missing': del source['Payload']['PeriodYear']
    elif defect.startswith(('outer-', 'main-')):
        owner, state = defect.split('-')
        dest = source['Payload'] if owner == 'outer' else root['MainFormData']
        if state == 'missing': del dest['IsTransactionWithRelated']
        else: dest['IsTransactionWithRelated'] = {'null': None, 'false': False, 'zero': 0}[state]
    source['Payload']['CurrentFormData'] = corpus.wire(root)
    item = packet(source)
    if defect == 'missing-history': del item['context']['corporate_l10b_lifetime']
    if defect == 'missing-component':
        del item['context']['component_lifetime']
        with pytest.raises(JsonSafetyError): adapt(item, forms)
        return
    result = adapt(item, forms)
    if defect == 'legacy-binding':
        assert result['eligible'] and has_audit_dump_tables(result['sections'], provenance=result['provenance'])
    else:
        assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('key,value', [('kind', 'unknown'), ('attempt', 'f' * 32),
    ('stable_form', False), ('fresh_form', None), ('extra', True)])
def test_invalid_manifest_owned_lifetime_is_fatal_even_without_binding(key, value):
    item = packet()
    item['context']['corporate_l10b_lifetime'][key] = value
    with pytest.raises(JsonSafetyError):
        adapt(item, [])


def test_mixed_absent_lifetime_between_packets_is_fatal():
    items = [packet(), packet(sequence=2)]
    del items[1]['context']['corporate_l10b_lifetime']
    with pytest.raises(JsonSafetyError):
        adapt_corporate_detail(items, selected(), corpus.SCOPE, observed())


@pytest.mark.parametrize('defect', ['claim-only', 'wrong-form', 'missing-values', 'changed-row', 'extra-dump',
    'pin', 'dummy-field', 'empty-table', 'numeric-false', 'missing-event', 'bad-lifetime',
    'bad-presence', 'bad-owner', 'bad-type', 'duplicate-value', 'bad-sequence', 'extra-value-key'])
def test_non_display_report_never_launders_other_or_changed_dump_sections(defect):
    result = adapt()
    assert result['eligible'], result['reason']
    report = next(r for r in result['provenance']['projections'] if r['form'] == 'L10-B')
    section = next(s for s in result['sections'] if s['name'] == 'L10-B')
    if defect == 'claim-only': result['provenance']['projections'] = [{'form': 'L10-B', 'kind': KIND}]
    elif defect == 'wrong-form': section['name'] = 'L10-D'
    elif defect == 'missing-values': report['values'] = []
    elif defect == 'changed-row': section['tables'][0]['rows'][0][2] = True
    elif defect == 'extra-dump': section['tables'].append(deepcopy(section['tables'][0]))
    elif defect == 'dummy-field': section['fields'] = [{'field': 'fake', 'value': 'unused'}]
    elif defect == 'empty-table': section['tables'] = []
    elif defect == 'numeric-false': section['tables'][0]['rows'][0][2] = 0
    elif defect == 'missing-event': result['provenance']['events'] = []
    elif defect == 'bad-lifetime': result['provenance']['events'][0]['corporate_l10b_lifetime']['stable_form'] = False
    elif defect == 'bad-presence': report['presence_facts'][0]['present'] = 1
    elif defect == 'bad-owner': report['values'][0]['container'] = ['Wrong']
    elif defect == 'bad-type': report['values'][0]['type'] = 'string'
    elif defect == 'duplicate-value': report['values'].append(deepcopy(report['values'][0]))
    elif defect == 'bad-sequence': report['values'][0]['response_sequence'] = 9
    elif defect == 'extra-value-key': report['values'][0]['extra'] = True
    else: report['builds'][projection.CIT_SOURCE] = '0' * 64
    assert has_audit_dump_tables(result['sections'], provenance=result['provenance'])


@pytest.mark.parametrize('path', [['MainFormData', 'Tin'], ['MainFormData', 'TaxYear'],
    ['TaxType'], ['TaxPeriodCode'], ['ReturnSheetRecordIdentifier'], ['ReturnSheetAggregateIdentifier']])
def test_report_revalidation_does_not_retype_identity_metadata_as_boolean(path):
    result = adapt()
    report = next(r for r in result['provenance']['projections'] if r['form'] == 'L10-B')
    entry = next(v for v in report['values'] if v['path'] == path)
    entry.update(type='boolean', value=False)
    assert has_audit_dump_tables(result['sections'], provenance=result['provenance'])


def catalog_first_result():
    from test_corporate_l11c_native import COUNTRY, catalog
    primary = packet(sequence=2)
    reference = corpus.packet({'IsSuccessful': True, 'Payload': catalog()}, 1,
                             endpoint=COUNTRY)
    reference['context'].update(method='GET', frame_url=ROUTE,
        component_lifetime=deepcopy(primary['context']['component_lifetime']),
        corporate_l10b_lifetime=deepcopy(primary['context']['corporate_l10b_lifetime']))
    # GET/no request body is required by the real transport validator. Both
    # packets retain the same manifest-owned attempt and lifetime facts.
    return adapt_corporate_detail([reference, primary], selected(), corpus.SCOPE, observed())


def test_admitted_catalog_before_primary_selects_the_exact_report_bound_event():
    result = catalog_first_result()
    assert result['eligible'], result['reason']
    assert [e['sequence'] for e in result['provenance']['events']] == [1, 2]
    report = next(r for r in result['provenance']['projections'] if r['form'] == 'L10-B')
    assert {v['response_sequence'] for v in report['values']} == {2}
    assert not has_audit_dump_tables(result['sections'], provenance=result['provenance'])


@pytest.mark.parametrize('defect', ['wrong-sequence', 'mixed-sequence', 'mixed-attempt', 'missing-event',
                                   'duplicate-event', 'conflicting-event', 'boolean-sequence'])
def test_report_bound_primary_selection_cannot_skip_actual_contradictions(defect):
    result = adapt()
    report = next(r for r in result['provenance']['projections'] if r['form'] == 'L10-B')
    if defect == 'wrong-sequence':
        for value in report['values']:
            value['response_sequence'] = 2
    elif defect == 'mixed-sequence':
        report['values'][-1]['response_sequence'] = 2
    elif defect == 'mixed-attempt':
        report['values'][-1]['attempt'] = 'b' * 32
    elif defect in ('duplicate-event', 'conflicting-event'):
        duplicate = deepcopy(result['provenance']['events'][0])
        if defect == 'conflicting-event': duplicate['sha256'] = '0' * 64
        result['provenance']['events'].append(duplicate)
    elif defect == 'boolean-sequence':
        for value in report['values']: value['response_sequence'] = True
        for value in report['presence_facts']: value['response_sequence'] = True
        result['provenance']['events'][0]['sequence'] = True
    else:
        result['provenance']['events'] = []
    assert has_audit_dump_tables(result['sections'], provenance=result['provenance'])


def test_report_cannot_rebind_original_values_to_an_admitted_catalog_event():
    result = catalog_first_result()
    assert result['eligible'], result['reason']
    report = next(r for r in result['provenance']['projections'] if r['form'] == 'L10-B')
    for entry in report['values'] + report['presence_facts']:
        entry['response_sequence'] = 1
    assert has_audit_dump_tables(result['sections'], provenance=result['provenance'])


def test_export_keeps_intentional_b_d_absence_and_checkpoint_custody(tmp_path):
    result = adapt()
    assert result['eligible'], result['reason']
    record = selected()
    record['meta']['Masa Pajak'] = '01122025'
    record.update(capture_complete=True, sections=result['sections'])
    record['sections'].append({'name': 'L10-D', 'fields': [], 'tables': [], 'text': ''})
    before = deepcopy(record)
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
           'inventory_complete': True, 'complete': True, 'errors': [], 'records': [record]}
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    filename, = [n for n in run['output_files'] if n != 'resume.xlsx']
    book = load_workbook(tmp_path / filename)
    try:
        assert 'L10-B' not in book.sheetnames and 'L10-D' not in book.sheetnames
        assert 'Induk' in book.sheetnames
    finally:
        book.close()
    assert record == before
    assert not any(r['form'] in ('L10-B', 'L10-D') for r in run['template_mapping'])


def test_capture_adapter_held_replay_and_published_json_keep_original_bytes(tmp_path):
    from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
    from support_json_network import exchange
    from test_corporate_component_lifetime import begin, navigate
    from test_corporate_l10b_history import history_setup, boundaries
    context, page, history = history_setup()
    page.url = corpus.LIST_URL
    page.evaluate = lambda script: ({'source_owner': page.url == corpus.LIST_URL,
                                    'detail_owner': page.url == ROUTE}
                                   if 'source_owner' in script else None)
    record = selected()
    record['detail_url'] = ROUTE
    job, output = tmp_path / 'job', tmp_path / 'output'
    job.mkdir()
    raw = corpus.wire(envelope()).encode()
    with DetailJsonCapture(context, page, record, corpus.SCOPE, job) as capture:
        begin(capture)
        navigate(page, ROUTE)
        response = exchange(context, page, raw=raw, url=corpus.PRIMARY_URL, post=dict(REQUEST))
        capture.bind_detail_page(page)
        assert boundaries(capture)
        saved = capture.drain()
        packets = list(capture.iter_bodies())
        result = adapt_corporate_detail(packets, record, corpus.SCOPE, observed())
        assert result['eligible'], result['reason']
        replay = checkpoint_bodies(job, saved, record, corpus.SCOPE)
        assert replay == packets and packets[0]['body'] == raw and response.reads == 1
        assert adapt_corporate_detail(replay, record, corpus.SCOPE, observed()) == result
    record.update(capture_complete=True, sections=result['sections'],
                  detail_source={'requested': 'json-first', 'used': 'json', 'capture': saved,
                                 'provenance': result['provenance'], 'coverage': result['coverage']})
    record['meta']['Masa Pajak'] = '01122025'
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
           'inventory_complete': True, 'complete': True, 'errors': [], 'records': [record]}
    before = deepcopy(record)
    coretax.save_output(run, output, json_source=job)
    coretax.verify_outputs(run, output)
    assert record == before
    responses = [name for name in run['output_json'] if 'response-' in name]
    assert len(responses) == 1 and (output / responses[0]).read_bytes() == raw
    filename, = [n for n in run['output_files'] if n != 'resume.xlsx']
    book = load_workbook(output / filename)
    try:
        assert 'L10-B' not in book.sheetnames and 'L10-D' not in book.sheetnames
    finally:
        book.close()
