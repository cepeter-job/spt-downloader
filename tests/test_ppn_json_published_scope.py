"""Approved PPN workbook omits extra administrative fields, not amounts.

Omissions must be named in coverage. Unknown controls still force fallback.
"""
import pytest

from masa_projection_fixture import field
from test_ppn_json_amendment import amend_case, decode

TEXT_OMISSIONS = [
    'TaxableEnterpreneurName', 'Address', 'PhoneNumber', 'Cellphone', 'TIN',
    'BussinessFieldClassification', 'BookkeepingPeriod', 'AccountNo', 'BankName',
    'AccountName', 'MyCheckBox', 'CityOfTaxReturnSigning', 'DeclaratorName', 'Position',
]


def test_reviewed_administrative_fields_are_explicit_omissions_not_missing_bindings():
    case = amend_case()
    fields = [field(control, 'Synthetic administrative caption') for control in TEXT_OMISSIONS]
    for control in ('DateOfTaxReturnSigning', 'DeadlineSubmission'):
        fields.append({**field(control, 'Synthetic date caption'), 'tag': 'P-CALENDAR'})
    for option, label in [('0', 'PKP'), ('1', 'Kuasa Wajib Pajak')]:
        fields.append({**field('DeclarationBy', label), 'tag': 'P-RADIOBUTTON', 'option': option})
    case['forms'][0]['fields'] += fields
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    assert result['coverage']['complete'] is True
    expected = set(TEXT_OMISSIONS) | {'DateOfTaxReturnSigning', 'DeadlineSubmission', 'DeclarationBy'}
    omissions = result['coverage']['omitted_fields']
    assert {item['field'] for item in omissions} == expected
    assert all(item['form'] == 'INDUK' and item['reason'] == 'approved_ppn_template_omission' for item in omissions)
    assert not expected.intersection(item['field'] for item in result['sections'][0]['fields'])


@pytest.mark.parametrize('control,tag', [('UnknownAdministrativeField', 'INPUT'), ('AccountNo', 'P-INPUTNUMBER')])
def test_unknown_control_or_changed_omission_shape_stays_ineligible(control, tag):
    case = amend_case()
    case['forms'][0]['fields'].append({**field(control, 'Synthetic caption'), 'tag': tag})
    assert decode(case)['eligible'] is False
