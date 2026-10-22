"""Dated reference labels pass through full custody and approved XLSX layouts."""
from copy import deepcopy
import hashlib
import json

import pytest

from coretax_masa_json import adapt_masa_detail
from masa_json_fixtures import SCOPE, RECORD
from pph21_projection_fixture import case, REFERENCE
from support_templates import run_for
from test_dated_reference_catalogs import CLOCK
from test_pph21_template import export


def dated_case():
    record, bodies, forms = case()
    expected = []
    for item in bodies:
        item['context']['clock_interval'] = {**CLOCK, 'attempt': item['context']['attempt']}
        if item['context']['url'] != REFERENCE:
            continue
        envelope = json.loads(item['body'])
        for catalog in envelope['Payload']:
            revised = []
            for entry in catalog['Details']:
                chosen = {**entry, 'CodeDescription': 'DATED ' + entry['CodeDescription'],
                          'ValidTo': '2030-01-01'}
                expected.append(chosen['CodeDescription'])
                revised.extend([chosen, {**entry, 'CodeDescription': 'UNSELECTED LABEL',
                                          'ValidTo': '2029-01-01'}])
            catalog['Details'] = revised
        item['body'] = json.dumps(envelope).encode()
        item['context'].update(bytes=len(item['body']), sha256=hashlib.sha256(item['body']).hexdigest())
    return record, bodies, forms, expected


def test_dated_labels_reach_complete_clean_saved_workbook_and_keep_source_provenance(tmp_path):
    record, bodies, forms, expected = dated_case()
    before = deepcopy((record, bodies, forms))
    result = adapt_masa_detail(bodies, record=record, scope=SCOPE, observed_forms=forms)
    assert result['eligible'], result['reason']
    assert result['coverage']['complete'] and len(result['coverage']['grids']) == 7
    assert any(binding.get('projection_rule', '').startswith('reviewed-grid-active-version:')
               for binding in result['provenance']['bindings'])
    reports = []
    workbook = export(run_for(result['sections'], key=RECORD), tmp_path, reports=reports)
    try:
        assert workbook.sheetnames == ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III']
        assert len(reports) == 5 and all(report['complete'] for report in reports)
        values = {cell.value for sheet in workbook for row in sheet for cell in row
                  if isinstance(cell.value, str)}
        assert set(expected) <= values
        assert 'UNSELECTED LABEL' not in values
        assert workbook['L-IA']['B5'].value == '0000000000000002'
        assert workbook['L-IA']['G5'].value == 1200
        assert workbook['L-IA']['G5'].data_type == 'n'
    finally:
        workbook.close()
    assert (record, bodies, forms) == before


@pytest.mark.parametrize('defect', ['missing-clock', 'cutoff-crossing', 'unbound-sequence'])
def test_dated_label_ineligibility_keeps_whole_record_fallback(defect):
    record, bodies, forms, _ = dated_case()
    if defect == 'missing-clock':
        for item in bodies:
            del item['context']['clock_interval']
    elif defect == 'cutoff-crossing':
        for item in bodies:
            item['context']['clock_interval']['end_ms'] = 1893456000000  # 2030-01-01 UTC
    else:
        forms[0]['references'][0]['sequences'] = [999999]
    result = adapt_masa_detail(bodies, record=record, scope=SCOPE, observed_forms=forms)
    assert not result['eligible'] and not result['coverage']['complete']
    assert result['sections'] == []
