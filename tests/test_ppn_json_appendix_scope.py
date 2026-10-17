"""Reviewed appendix identity controls have no slots in the clean PPN layout."""
from copy import deepcopy

import pytest

from masa_projection_fixture import field
from test_ppn_json_amendment import amend_case, decode

APPENDICES = ['A-1', 'A-2', 'B-1', 'B-2', 'B-3', 'C']
HEADERS = ['TaxableEntrepreneurName', 'TaxPeriodYear', 'TIN', 'ReturnSheetModel']


@pytest.mark.parametrize('names', [[name] for name in APPENDICES] + [APPENDICES])
def test_appendix_identity_controls_are_explicit_display_omissions_not_dropped_evidence(names):
    case = amend_case()
    baseline = decode(case)
    assert baseline['eligible'] is True, baseline['reason']
    for form in case['forms']:
        if form['name'] in names:
            form['fields'] = [field(name, 'Synthetic identity caption') for name in HEADERS]
    before = deepcopy(case)
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    assert result['coverage']['complete'] is True
    assert result['sections'] == baseline['sections']
    assert case == before
    omissions = result['coverage']['omitted_fields']
    assert len(omissions) == len(names) * len(HEADERS)
    assert {(item['form'], item['field']) for item in omissions} == {
        (name, header) for name in names for header in HEADERS}
    assert all(item['tag'] == 'INPUT' and item['reason'] == 'approved_ppn_template_omission'
               for item in omissions)


@pytest.mark.parametrize('name', APPENDICES)
@pytest.mark.parametrize('control,changes', [
    ('UnknownHeader', {}),
    ('TaxableEnterpreneurName', {}),  # Induk spelling is not an appendix alias.
    ('TIN', {'tag': 'P-INPUTNUMBER'}),
    ('ReturnSheetModel', {'option': 'UNKNOWN'}),
])
def test_appendix_omission_does_not_accept_unknown_alias_numeric_or_choice_controls(name, control, changes):
    case = amend_case()
    form = next(form for form in case['forms'] if form['name'] == name)
    form['fields'].append({**field(control, 'Synthetic caption'), **changes})
    assert decode(case)['eligible'] is False


def test_appendix_name_spelling_does_not_create_an_induk_alias():
    case = amend_case()
    case['forms'][0]['fields'].append(field('TaxableEntrepreneurName', 'Synthetic caption'))
    assert decode(case)['eligible'] is False
