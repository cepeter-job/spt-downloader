"""Reviewed absent-5322 contracts; execute only on GitHub-hosted runners.

The pure helper's optional body_layout is not native authorization. Native
admission additionally needs the existing enabled-Induk visibility proof; neither
marker may repair source data or weaken the independent three-table schemas.
"""
from copy import deepcopy
import json

import pytest
import openpyxl

import coretax
import coretax_corporate_projection as projection
import coretax_json as native_json
import support_json_corpus as corpus
import test_corporate_l1d_native as l1d_native
import test_corporate_l1d_projection as l1d_source
import test_corporate_l7_native as l7_native


BODY_LAYOUT = 'absent-5322-34x10-v1'
VISIBILITY = 'current-induk-enabled-v1'
UNSET = object()
OTHER_CODES = [code for code in l1d_source.CODES if code != '5322']
BALANCE_TOTALS = [('L1dAssets', 'AC1700'),
    ('L1dLiabilitiesAndEquity', 'AC2999'),
    ('L1dLiabilitiesAndEquity', 'AC3299'),
    ('L1dLiabilitiesAndEquity', 'AC3300')]


def full_source(migrated=False):
    """Nonzero synthetic operands expose shifted/copied/defaulted values."""
    raw = l1d_source.source()
    for index, node in enumerate(raw['L1dTreeData'], 1):
        node['Data'].update({field: index * 10 + column
                            for column, field in enumerate(l1d_source.TREE_FIELDS)})
    for code, amount in [('4500', 6), ('4700', 7)]:
        l1d_source.tree_row(raw, code).update(dict.fromkeys(l1d_source.TREE_FIELDS, amount))
    raw['L1dTreeTotalRow'] = dict.fromkeys(l1d_source.TREE_FIELDS, 101 if migrated else 13)
    raw['L1dAssets'].update(AC1101=16, AC1522=5, AC1700=11)
    raw['L1dLiabilitiesAndEquity'].update(
        AC2102=100, AC3102=11, AC2999=100, AC3299=11, AC3300=111)
    return raw


def omission_source(migrated=False):
    raw = full_source(migrated)
    raw['L1dTreeData'] = [node for node in raw['L1dTreeData']
                          if node['Data']['AccountCode'] != '5322']
    return raw


def project(raw, *, migrated=False, body_layout=UNSET, headers=None, spans=None):
    captured = native_json._corporate_json(corpus.wire(raw))
    bound_headers = deepcopy(l1d_source.HEADERS if headers is None else headers)
    bound_spans = deepcopy(l1d_source.SPANS if spans is None else spans)
    before = deepcopy((raw, captured, bound_headers, bound_spans))
    options = {} if body_layout is UNSET else {'body_layout': body_layout}
    try:
        return projection.project_l1d(captured, migrated=migrated, headers=bound_headers,
            footer_spans=bound_spans, tax_type='ICT_RCIT', locale='id-ID',
            timezone_name='Asia/Jakarta', **options)
    finally:
        assert (raw, captured, bound_headers, bound_spans) == before


def native_case(raw=None, *, model='Normal', migrated=False):
    value = l1d_native.current_classification_envelope(model, migrated)
    form = json.loads(value['Payload']['CurrentFormData'])
    form[l1d_native.ROOT] = omission_source(migrated) if raw is None else raw
    value['Payload']['CurrentFormData'] = corpus.wire(form)
    observed = l1d_native.bindings()
    observed[1]['projection'].update(body_layout=BODY_LAYOUT, visibility_binding=VISIBILITY)
    return value, observed, l7_native.selected(model)


def adapt(value, observed, record):
    raw = l1d_native.packet(value)
    before = deepcopy((raw, value, observed, record))
    try:
        result = native_json.adapt_corporate_detail(iter([raw]), record, corpus.SCOPE, observed)
        return result, raw
    finally:
        assert (raw, value, observed, record) == before


def assert_refused(result):
    assert result['eligible'] is False
    assert result['sections'] == []
    assert result['coverage']['complete'] is False


def reject_source(raw, layer, *, migrated=False):
    if layer == 'pure':
        with pytest.raises(native_json._UnsupportedMetadata):
            project(raw, migrated=migrated, body_layout=BODY_LAYOUT)
    else:
        result, _ = adapt(*native_case(raw, migrated=migrated))
        assert_refused(result)


def assert_real_leaves(entries, root):
    """Resolve every claimed source leaf, including legitimate absent masks."""
    for entry in entries:
        path = entry['path']
        assert path
        parent = root
        for token in path[:-1]:
            parent = parent[token]
        if entry['type'] == 'missing':
            assert path[-2] == 'BlockFields'
            assert path[-1] not in parent
            assert entry['value'] is None
            continue
        value = parent[path[-1]]
        expected_type = ('number' if type(value) is native_json._CorporateNumber else
                         'null' if value is None else 'boolean' if type(value) is bool else 'string')
        assert entry['type'] == expected_type
        assert entry['value'] == value
        assert not (path[-1] == 'AccountCode' and value == '5322')


@pytest.mark.parametrize('migrated', [False, True])
@pytest.mark.parametrize('reverse', [False, True])
def test_pure_omission_is_exactly_34_existing_rows_without_defaults_or_source_mutation(migrated, reverse):
    complete = full_source(migrated)
    raw = omission_source(migrated)
    if reverse:
        raw['L1dTreeData'].reverse()
    before = corpus.wire(raw)
    result = project(raw, migrated=migrated, body_layout=BODY_LAYOUT)
    assert corpus.wire(raw) == before
    assert result['omitted_account_codes'] == ['5322']
    # The unchanged strict branch is an oracle for all other rows, masks,
    # captions, correction-code duplicates, balances and reported totals.
    strict = project(complete, migrated=migrated)
    assert strict.get('omitted_account_codes', []) == []
    expected = deepcopy(strict['tables'])
    expected[0]['rows'] = [row for row in expected[0]['rows'] if row[0] != '5322']
    expected[0].update(body_row_count=34, source_total=34)
    assert result['tables'] == expected
    table = result['tables'][0]
    assert [row[0] or row[1] for row in table['rows'][:34]] == [
        key for key in l1d_source.ORDER if key != '5322']
    assert len(table['rows']) == 35 and table['rows'][34:] == table['footer']
    assert all(len(row) == 10 for row in table['rows'])
    assert all('5322' not in row and 'SYNTHETIC 5322' not in row for row in table['rows'])
    assert table['footer'][0] == ['4800', 'Laba (Rugi) Sebelum Pajak',
                                 *(['101' if migrated else '13'] * 6), '',
                                 '101' if migrated else '13']
    entries = result['provenance']
    assert_real_leaves(entries, {l1d_native.ROOT: native_json._corporate_json(before)})
    codes = [entry['value'] for entry in entries if entry['path'][-1] == 'AccountCode']
    assert len(codes) == 30 and set(codes) == set(OTHER_CODES)
    for entry in entries:
        destination = entry['destination']
        if destination['table'] == 'L1-D/tree' and 'row' in destination:
            assert 0 <= destination['row'] < 34
            if entry['path'][-1] == 'AccountCode':
                assert table['rows'][destination['row']][0] == entry['value']


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('amount', [None, 0, 77], ids=['present-null', 'present-zero', 'present-nonzero'])
def test_present_5322_is_preserved_without_an_omission_marker(layer, amount):
    raw = full_source()
    l1d_source.tree_row(raw, '5322').update(Amount=amount, FinalAmount=amount)
    if layer == 'pure':
        result = project(raw)
        table = result['tables'][0]
        assert result.get('omitted_account_codes', []) == []
    else:
        value, observed, record = native_case(raw)
        del observed[1]['projection']['body_layout']
        result, _ = adapt(value, observed, record)
        assert result['eligible'] and result['coverage']['complete'], result['reason']
        section, = [s for s in result['sections'] if s['name'] == 'L1-D']
        table = section['tables'][0]
        proof, = [p for p in result['provenance']['projections'] if p['form'] == 'L1-D']
        assert 'body_layout' not in proof and proof.get('omitted_account_codes', []) == []
    row, = [r for r in table['rows'] if r[0] == '5322']
    assert table['body_row_count'] == 35
    assert row[2] == row[9] == ('' if amount is None else str(amount))


@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
@pytest.mark.parametrize('migrated', [False, True])
def test_current_induk_omission_reaches_native_with_separate_layout_and_real_leaf_provenance(model, migrated):
    value, observed, record = native_case(model=model, migrated=migrated)
    result, packet = adapt(value, observed, record)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = [item for item in result['sections'] if item['name'] == 'L1-D']
    assert [table['body_row_count'] for table in section['tables']] == [34, 26, 29]
    assert all(table['complete'] and table['source_total'] == table['body_row_count']
               for table in section['tables'])
    assert section['tables'] == project(omission_source(migrated), migrated=migrated,
                                         body_layout=BODY_LAYOUT)['tables']
    proof, = [item for item in result['provenance']['projections'] if item['form'] == 'L1-D']
    assert proof['body_layout'] == BODY_LAYOUT
    assert proof['omitted_account_codes'] == ['5322']
    assert proof['visibility_binding'] == VISIBILITY
    assert proof['kind'] == observed[1]['projection']['kind']
    assert proof['builds'] == observed[1]['projection']['builds']
    assert proof['route'] == l1d_native.DETAIL
    current = native_json._corporate_json(value['Payload']['CurrentFormData'])
    assert_real_leaves(proof['values'], current)
    assert all(entry['response_sequence'] == packet['context']['sequence']
               and entry['container'] == ['Payload', 'CurrentFormData'] for entry in proof['values'])
    assert any(entry['path'] == ['MainFormData', 'BusinessClassification']
               and entry['value'] == 'BC04' and entry['type'] == 'string'
               and entry['rule'] == 'current-induk-services-enabled-v1' for entry in proof['values'])
    assert len([entry for entry in proof['values'] if entry['path'][-1] == 'AccountCode']) == 30
    # The marker is a summary fact, never a fabricated absence leaf/value input.
    assert all('body_layout' not in entry['path'] and 'omitted_account_codes' not in entry['path']
               for entry in proof['values'])
    assert all(set(table) == {'component', 'headers', 'footer_spans', 'source_structure'}
               for table in observed[1]['projection']['tables'])


@pytest.mark.parametrize('body_layout', [UNSET, None], ids=['omitted-key', 'explicit-none'])
def test_pure_missing_5322_without_layout_remains_old_strict_branch(body_layout):
    with pytest.raises(native_json._UnsupportedMetadata):
        project(omission_source(), body_layout=body_layout)


@pytest.mark.parametrize('migrated', [False, True])
def test_explicit_none_helper_layout_preserves_the_unchanged_full_source_branch(migrated):
    raw = full_source(migrated)
    assert project(raw, migrated=migrated, body_layout=None) == project(raw, migrated=migrated)


@pytest.mark.parametrize('body_layout', ['', 'SYNTHETIC UNKNOWN', 'absent-5322-35x10-v1',
    'ABSENT-5322-34X10-V1', 'absent-5322-34x10-v1 ', False, 34, {}, []])
def test_pure_body_layout_requires_exact_reviewed_literal(body_layout):
    with pytest.raises(native_json._UnsupportedMetadata):
        project(omission_source(), body_layout=body_layout)


@pytest.mark.parametrize('layer', ['pure', 'native'])
def test_omission_marker_with_present_5322_is_contradictory(layer):
    reject_source(full_source(), layer)


@pytest.mark.parametrize('body_layout', [UNSET, None, '', 'SYNTHETIC UNKNOWN',
    'absent-5322-35x10-v1', False, {}, []],
    ids=['missing', 'null', 'empty', 'unknown', 'other-layout', 'boolean', 'object', 'array'])
def test_native_omission_requires_present_valid_body_layout(body_layout):
    value, observed, record = native_case()
    proof = observed[1]['projection']
    if body_layout is UNSET:
        del proof['body_layout']
    else:
        proof['body_layout'] = body_layout
    result, _ = adapt(value, observed, record)
    assert_refused(result)
    if body_layout is UNSET:
        assert 'missing_corporate_l1d_account' in result['reason']


@pytest.mark.parametrize('body_layout', [None, 'SYNTHETIC UNKNOWN'])
def test_native_present_invalid_layout_key_is_not_ignored_even_for_full_source(body_layout):
    value, observed, record = native_case(full_source())
    observed[1]['projection']['body_layout'] = body_layout
    result, _ = adapt(value, observed, record)
    assert_refused(result)


@pytest.mark.parametrize('visibility', [UNSET, None, 'SYNTHETIC UNKNOWN'])
@pytest.mark.parametrize('outer_present', [False, True])
def test_native_body_layout_cannot_replace_enabled_visibility_even_with_legacy_outer_bc04(visibility, outer_present):
    value, observed, record = native_case()
    if outer_present:
        value['Payload']['BusinessClassification'] = 'BC04'
    if visibility is UNSET:
        del observed[1]['projection']['visibility_binding']
    else:
        observed[1]['projection']['visibility_binding'] = visibility
    result, _ = adapt(value, observed, record)
    assert_refused(result)


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('missing_5322', [False, True], ids=['other-single-missing', 'multiple-missing'])
@pytest.mark.parametrize('code', OTHER_CODES)
def test_every_other_missing_account_is_refused_not_generalized_as_optional(layer, missing_5322, code):
    raw = omission_source() if missing_5322 else full_source()
    raw['L1dTreeData'] = [node for node in raw['L1dTreeData'] if node['Data']['AccountCode'] != code]
    reject_source(raw, layer)


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('defect', ['duplicate', 'extra-code', 'null-node', 'null-data', 'null-code',
    'bad-children', 'bad-mask', 'bad-mask-container', 'unsafe-operand', 'fractional-operand',
    'string-operand', 'boolean-operand', 'missing-operand', 'unsafe-footer', 'missing-footer'])
def test_omission_does_not_relax_tree_shape_masks_or_numeric_guards(layer, defect):
    raw = omission_source()
    data = l1d_source.tree_row(raw, '4021')
    if defect == 'duplicate':
        raw['L1dTreeData'].append(deepcopy(raw['L1dTreeData'][0]))
    elif defect == 'extra-code':
        node = deepcopy(raw['L1dTreeData'][0])
        node['Data']['AccountCode'] = '9999'
        raw['L1dTreeData'].append(node)
    elif defect == 'null-node':
        raw['L1dTreeData'].append(None)
    elif defect == 'null-data':
        raw['L1dTreeData'][0]['Data'] = None
    elif defect == 'null-code':
        data['AccountCode'] = None
    elif defect == 'bad-children':
        raw['L1dTreeData'][0]['Children'] = {}
    elif defect == 'bad-mask':
        data['BlockFields']['NonTaxableObject'] = 'SYNTHETIC UNSAFE MASK'
    elif defect == 'bad-mask-container':
        data['BlockFields'] = []
    elif defect == 'missing-operand':
        del data['Amount']
    elif defect == 'unsafe-footer':
        raw['L1dTreeTotalRow']['Amount'] = 1000000000000000
    elif defect == 'missing-footer':
        del raw['L1dTreeTotalRow']
    else:
        data['Amount'] = {'unsafe-operand': 1000000000000000, 'fractional-operand': 1.5,
                          'string-operand': '7', 'boolean-operand': True}[defect]
    reject_source(raw, layer)


@pytest.mark.parametrize('layer', ['pure', 'native'])
def test_migrated_copy_rule_never_admits_unsafe_reported_footer(layer):
    raw = omission_source(migrated=True)
    raw['L1dTreeTotalRow']['Amount'] = 1000000000000000
    reject_source(raw, layer, migrated=True)


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('field', l1d_source.TREE_FIELDS)
def test_nonmigrated_omission_still_reconciles_each_captured_tree_total(layer, field):
    raw = omission_source()
    raw['L1dTreeTotalRow'][field] = 14
    reject_source(raw, layer)


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('migrated', [False, True])
@pytest.mark.parametrize('container,field', BALANCE_TOTALS)
@pytest.mark.parametrize('defect', ['missing', 'null', 'mismatch'])
def test_omission_preserves_all_four_balance_total_guards(layer, migrated, container, field, defect):
    raw = omission_source(migrated)
    if defect == 'missing':
        del raw[container][field]
    else:
        raw[container][field] = None if defect == 'null' else 999
    reject_source(raw, layer, migrated=migrated)


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('defect', ['tree-sum', 'asset-sum', 'debt-sum', 'equity-sum'])
def test_safe_final_total_does_not_hide_unsafe_ordered_intermediate_in_omission(layer, defect):
    raw = omission_source()
    if defect == 'tree-sum':
        l1d_source.tree_row(raw, '4500')['Amount'] = 999999999999999
        l1d_source.tree_row(raw, '4700')['Amount'] = 1
        raw['L1dTreeTotalRow']['Amount'] = 999999999999999
    elif defect == 'asset-sum':
        raw['L1dAssets'].update(AC1101=999999999999999, AC1122=1, AC1131=1,
                               AC1522=0, AC1700=999999999999999)
    elif defect == 'debt-sum':
        raw['L1dLiabilitiesAndEquity'].update(AC2102=999999999999999, AC2103=1,
            AC2111=-1, AC3102=0, AC2999=999999999999999, AC3299=0, AC3300=999999999999999)
    else:
        raw['L1dLiabilitiesAndEquity'].update(AC2102=0, AC3102=999999999999999,
            AC3120=1, AC3200=-1, AC2999=0, AC3299=999999999999999, AC3300=999999999999999)
    reject_source(raw, layer)


@pytest.mark.parametrize('layer', ['pure', 'native'])
@pytest.mark.parametrize('index', [0, 1, 2])
@pytest.mark.parametrize('defect', ['header', 'missing-footer', 'footer-span'])
def test_each_table_keeps_independent_exact_headers_and_footer_spans(layer, index, defect):
    headers, spans = deepcopy(l1d_source.HEADERS), deepcopy(l1d_source.SPANS)
    if defect == 'header':
        headers[index][0] = 'SYNTHETIC FOREIGN HEADER'
    elif defect == 'missing-footer':
        spans[index] = []
    else:
        spans[index][0][0] = 2
    if layer == 'pure':
        with pytest.raises(native_json._UnsupportedMetadata):
            project(omission_source(), body_layout=BODY_LAYOUT, headers=headers, spans=spans)
    else:
        value, observed, record = native_case()
        observed[1]['projection']['tables'][index].update(headers=headers[index], footer_spans=spans[index])
        result, _ = adapt(value, observed, record)
        assert_refused(result)


@pytest.mark.parametrize('index', [0, 1, 2])
@pytest.mark.parametrize('defect', ['component', 'form', 'group', 'missing-structure', 'extra-key', 'null-table'])
def test_native_marker_does_not_bypass_any_table_owner_or_closed_schema(index, defect):
    value, observed, record = native_case()
    table = observed[1]['projection']['tables'][index]
    if defect == 'component':
        table['component'] = 'SYNTHETIC FOREIGN COMPONENT'
    elif defect == 'form':
        table['source_structure']['form'] = 'L1-C'
    elif defect == 'group':
        table['source_structure']['groups'] = ['SYNTHETIC FOREIGN GROUP']
    elif defect == 'missing-structure':
        del table['source_structure']
    elif defect == 'extra-key':
        table['body_values'] = []  # A marker cannot authorize DOM value inputs.
    else:
        observed[1]['projection']['tables'][index] = None
    result, _ = adapt(value, observed, record)
    assert_refused(result)


@pytest.mark.parametrize('defect', ['missing-table', 'extra-table', 'reordered-tables',
    'missing-lifetime', 'induk-after', 'missing-migration', 'null-migration',
    'missing-previous', 'missing-status', 'wrong-classification', 'outer-null',
    'model-mismatch', 'proof-route', 'locale', 'timezone', 'unknown-proof-key',
    'corporate-pin', 'main-pin', 'vendor-pin'])
def test_native_omission_retains_existing_lifecycle_and_source_proof_gates(defect):
    value, observed, record = native_case()
    proof = observed[1]['projection']
    if defect.endswith('-pin'):
        fragment = {'corporate-pin': '/525.', 'main-pin': '/main.', 'vendor-pin': '/vendor.'}[defect]
        key, = [key for key in proof['builds'] if fragment in key]
        proof['builds'][key] = '0' * 64
    elif defect == 'missing-table':
        proof['tables'].pop()
    elif defect == 'extra-table':
        proof['tables'].append(deepcopy(proof['tables'][0]))
    elif defect == 'reordered-tables':
        proof['tables'].reverse()
    elif defect == 'induk-after':
        observed.reverse()
    elif defect in ('missing-migration', 'missing-previous', 'missing-status'):
        del value['Payload'][{'missing-migration': 'IsMigrated', 'missing-previous': 'PreviousFormData',
                              'missing-status': 'ReturnSheetStatusCode'}[defect]]
    elif defect == 'null-migration':
        value['Payload']['IsMigrated'] = None
    elif defect == 'wrong-classification':
        form = json.loads(value['Payload']['CurrentFormData'])
        form['MainFormData']['BusinessClassification'] = 'BC01'
        value['Payload']['CurrentFormData'] = corpus.wire(form)
    elif defect == 'outer-null':
        value['Payload']['BusinessClassification'] = None
    elif defect == 'model-mismatch':
        value['Payload']['ReturnSheetModel'] = 'AMENDMENT'
    elif defect == 'proof-route':
        proof['route'] = l7_native.FRAME
    elif defect in ('locale', 'timezone'):
        proof[defect] = 'SYNTHETIC UNKNOWN'
    elif defect == 'unknown-proof-key':
        proof['SYNTHETIC UNKNOWN'] = True
    if defect == 'missing-lifetime':
        raw = l1d_native.packet(value)
        del raw['context']['component_lifetime']
        before = deepcopy((raw, observed, record))
        result = native_json.adapt_corporate_detail([raw], record, corpus.SCOPE, observed)
        assert (raw, observed, record) == before
    else:
        result, _ = adapt(value, observed, record)
    assert_refused(result)


@pytest.mark.parametrize('model', ['Normal', 'Amendment 002'])
@pytest.mark.parametrize('migrated', [False, True])
def test_native_omission_final_save_reopen_maps_original_34_slot_template_without_phantom_5322(tmp_path, model, migrated):
    value, observed, record = native_case(model=model, migrated=migrated)
    result, _ = adapt(value, observed, record)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    record.update(capture_complete=True, sections=result['sections'])
    before = deepcopy(result['sections'])
    run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
           'inventory_complete': True, 'complete': True, 'errors': [], 'records': [record]}
    coretax.save_output(run, tmp_path)
    coretax.verify_outputs(run, tmp_path)
    assert result['sections'] == before
    report, = [item for item in run['template_mapping'] if item['form'] == 'L1-D']
    assert report['complete']
    assert report['unmapped_rows'] == report['unmapped_tables'] == 0
    induk, = [item for item in run['template_mapping'] if item['form'] == 'Induk']
    assert not induk['complete']  # Native L1-D must not certify another form.
    name, = [name for name in run['output_files'] if name != 'resume.xlsx']
    assert model in name
    workbook = openpyxl.load_workbook(tmp_path / name)
    try:
        assert set(workbook.sheetnames) == {'Induk', 'L1-D'}
        sheet = workbook['L1-D']
        # Inspected resource: header A5:J5, original body6..39, merges for
        # four group rows, final total B101. Final compaction removes title
        # rows; locate semantic anchors rather than assuming a row offset.
        header, = [row for row in sheet.iter_rows(max_col=10)
                   if [cell.value for cell in row] == l1d_source.HEADERS[0]]
        footer, = [row for row in sheet.iter_rows(max_col=10) if row[0].value == '4800']
        rows = list(sheet.iter_rows(min_row=header[0].row + 1,
                                   max_row=footer[0].row - 1, max_col=10))
        expected_order = [key for key in l1d_source.ORDER if key != '5322']
        assert len(rows) == 34
        assert [row[0].value for row in rows] == expected_order
        assert not any(cell.value in ('5322', 'SYNTHETIC 5322')
                       for row in sheet.iter_rows() for cell in row)
        raw = omission_source(migrated)
        for row in rows:
            code = row[0].value
            if code in OTHER_CODES:
                data = l1d_source.tree_row(raw, code)
                assert row[1].value == data['Description']
                assert row[2].value == data['Amount']
                assert row[9].value == data['FinalAmount']
                assert row[8].value == '0001; 0001'
                assert 'Rp' in row[2].number_format and '0.00' not in row[2].number_format
            else:
                assert f'A{row[0].row}:B{row[0].row}' in {
                    str(region) for region in sheet.merged_cells.ranges}
                assert all(cell.value is None for cell in row[2:])
        assert [footer[index].value for index in (2, 3, 4, 5, 6, 7, 9)] == [101 if migrated else 13] * 7
        for code, caption, amount in [('1700', 'Jumlah Aset', 11),
            ('2999', 'Jumlah Liabilitas', 100), ('3299', 'Jumlah Ekuitas', 11),
            ('3300', 'Jumlah Liabilitas dan Ekuitas', 111)]:
            total, = [row for row in sheet.iter_rows(max_col=3) if row[0].value == code]
            assert total[1].value == caption and total[2].value == amount
        final, = [row for row in sheet.iter_rows(max_col=3) if row[0].value == '3300']
        assert final[0].row == sheet.max_row
        depreciation, = [row for row in sheet.iter_rows(max_col=3) if row[0].value == '1522']
        assert depreciation[2].value == -5
    finally:
        workbook.close()
