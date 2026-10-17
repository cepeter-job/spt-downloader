"""Replacement checkbox is preserved in source, never put into money slots."""
from copy import deepcopy
import json

import pytest

from masa_projection_fixture import field
from test_ppn_json_amendment import amend_case, decode, reseal

REPLACEMENT = {
    **field('ReplacementPrevious', 'Ganti SPT sebelumnya'),
    'group': 'III. PENGHITUNGAN PPN KURANG BAYAR / LEBIH BAYAR',
    'tag': 'P-CHECKBOX',
}


@pytest.mark.parametrize('value', [True, False])
def test_replacement_checkbox_is_explicitly_omitted_without_changing_financial_fields(value):
    case = amend_case()
    envelope = json.loads(case['packets'][0]['body'])
    data = json.loads(envelope['Payload']['FormData'])
    data['ReplacementPrevious'] = value
    envelope['Payload']['FormData'] = json.dumps(data)
    reseal(case, envelope)
    baseline = decode(case)
    assert baseline['eligible'] is True, baseline['reason']
    case['forms'][0]['fields'].append(deepcopy(REPLACEMENT))
    before = deepcopy(case)
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    assert result['coverage']['complete'] is True
    assert result['sections'] == baseline['sections']
    assert case == before
    assert [item for item in result['coverage']['omitted_fields']
            if item['field'] == 'ReplacementPrevious'] == [{
        'form': 'INDUK', 'field': 'ReplacementPrevious', 'tag': 'P-CHECKBOX',
        'reason': 'approved_ppn_template_omission',
    }]


@pytest.mark.parametrize('changed', [
    {'tag': 'INPUT'}, {'tag': 'P-INPUTNUMBER'}, {'label': 'Unknown checkbox'},
    {'option': 'UNKNOWN'}, {'group': 'Unknown section'},
])
def test_changed_replacement_metadata_does_not_gain_omission_coverage(changed):
    case = amend_case()
    case['forms'][0]['fields'].append({**REPLACEMENT, **changed})
    assert decode(case)['eligible'] is False
