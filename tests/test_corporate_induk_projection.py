"""Reviewed Induk identity projection contracts; GitHub-runner execution only.

Only slots whose payload control is proven may be projected. The reviewed
template's derived captions stay unprojected, so the section must report itself
as partial instead of claiming a complete worksheet.
"""
from copy import deepcopy
import importlib

import pytest

from coretax_json import _CorporateNumber, _UnsupportedMetadata, adapt_corporate_detail
import support_json_corpus as corpus

FIELDS = (
    ('HEADER', 'TaxYear', 'Tahun Pajak/Bagian Tahun Pajak'),
    ('HEADER', 'Status', 'Status'),
    ('HEADER', 'AccountingPeriodStart', 'Periode Pembukuan'),
    ('HEADER', 'AccountingPeriodEnd', 'Periode Pembukuan'),
    ('A. IDENTITAS WAJIB PAJAK', 'Tin', '1. NPWP'),
    ('A. IDENTITAS WAJIB PAJAK', 'Name', '2. Nama'),
    ('B. INFORMASI LAPORAN KEUANGAN', 'TinAccountant', '2.b. NPWP Kantor Akuntan Publik'),
    ('B. INFORMASI LAPORAN KEUANGAN', 'NameAccountant', '2.c. Nama Kantor Akuntan Publik'),
    ('A. IDENTITAS WAJIB PAJAK', 'EmailAddress', '3. Alamat Email'),
    ('A. IDENTITAS WAJIB PAJAK', 'PhoneNumber', '4. Nomor Telepon'),
)


def module():
    return importlib.import_module('coretax_corporate_projection')


def proof(**overrides):
    value = corpus.induk_projection()
    value.update(overrides)
    return value


def main_form(**overrides):
    form = {'TaxYear': _CorporateNumber('2025'), 'Status': 'NORMAL',
            'AccountingPeriodStart': _CorporateNumber('1'),
            'AccountingPeriodEnd': _CorporateNumber('12'),
            'Tin': corpus.NPWP, 'Name': 'SYNTHETIC COMPANY',
            'TinAccountant': '0000000000000009', 'NameAccountant': 'SYNTHETIC ACCOUNTANT',
            'EmailAddress': 'SYNTHETIC@EXAMPLE.INVALID', 'PhoneNumber': '0000000000',
            'TaxRate': 'W01', 'NetIncomeBeforeTax': _CorporateNumber('123.4500')}
    form.update(overrides)
    return form


def project(form=None, **overrides):
    helper = getattr(module(), 'project_induk', None)
    assert callable(helper), 'Missing reviewed Induk identity projection'
    options = {'tax_type': 'ICT_RCIT'}
    options.update(overrides)
    return helper(main_form() if form is None else form, **options)


def declared():
    return getattr(module(), 'INDUK_IDENTITY_FIELDS', None)


def test_identity_projection_matches_the_reviewed_template_slots():
    fields = declared()
    assert fields == FIELDS, 'Projection slots must mirror the reviewed Induk declarations'
    result = project()
    assert [(f['group'], f['field'], f['label']) for f in result['fields']] == list(FIELDS)
    assert [f['value'] for f in result['fields']] == [
        '2025', 'NORMAL', '1', '12', corpus.NPWP, 'SYNTHETIC COMPANY',
        '0000000000000009', 'SYNTHETIC ACCOUNTANT', 'SYNTHETIC@EXAMPLE.INVALID', '0000000000']
    assert [entry['path'] for entry in result['provenance']] == [
        ['MainFormData', name] for _, name, _ in FIELDS]


def test_unproven_captions_are_never_guessed_from_the_payload():
    # TaxRate is a tariff code in the payload while the template renders the
    # full tariff text; NetIncomeBeforeTax belongs to an unproven derived slot.
    result = project()
    emitted = {field['field'] for field in result['fields']}
    assert 'TaxRate' not in emitted and 'NetIncomeBeforeTax' not in emitted
    assert len(emitted) == len(FIELDS)


def test_absent_or_empty_identity_controls_are_omitted_not_invented():
    form = main_form()
    form.pop('TinAccountant')
    form['PhoneNumber'] = ''
    result = project(form)
    names = [field['field'] for field in result['fields']]
    assert 'TinAccountant' not in names and 'PhoneNumber' not in names
    assert names[:6] == ['TaxYear', 'Status', 'AccountingPeriodStart', 'AccountingPeriodEnd',
                         'Tin', 'Name']


@pytest.mark.parametrize('value', [True, ['SYNTHETIC'], {'SYNTHETIC': 'LIST'}])
def test_non_scalar_identity_control_refuses(value):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(main_form(Tin=value))
    assert str(error.value) == 'unsupported_corporate_induk_identity_type'


@pytest.mark.parametrize(('option', 'value'), [('tax_type', 'VAT_VAT')])
def test_unreviewed_structure_or_environment_refuses(option, value):
    with pytest.raises(_UnsupportedMetadata) as error:
        project(**{option: value})
    assert str(error.value) == 'unsupported_corporate_induk_structure'


def test_unproven_projection_binding_refuses_the_capture():
    observed = corpus.observed()
    observed[0]['projection'] = {'kind': 'corporate-induk-v1'}
    result = adapt_corporate_detail(iter([corpus.primary()]), corpus.selected_record(),
                                    corpus.SCOPE, observed)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_induk_binding'


@pytest.mark.parametrize('projection', [
    {'kind': 'corporate-induk-v0'},
    dict(proof(), builds={}),
    dict(proof(), builds={'https://coretax.intranet.pajak.go.id/other.js': '0' * 64}),
    dict(proof(), builds={'https://coretax.intranet.pajak.go.id/returnsheets/id-ID/525.c5690c441d8dbc45.js': 'APPROVED'}),
    dict(proof(), route=corpus.FRAME_URL + '/changed'),
    dict(proof(), tables=[]),
])
def test_projection_proof_must_match_the_reviewed_shape(projection):
    observed = corpus.observed()
    observed[0]['projection'] = projection
    result = adapt_corporate_detail(iter([corpus.primary()]), corpus.selected_record(),
                                    corpus.SCOPE, observed)
    assert not result['eligible']
    assert result['reason'] == 'unverified_corporate_induk_binding'


def test_unsubmitted_model_or_status_refuses_the_projection():
    observed = corpus.observed()
    result = adapt_corporate_detail(iter([corpus.primary()]), corpus.selected_record(),
                                    corpus.SCOPE, observed)
    assert result['eligible'] and result['coverage']['complete']
    record = corpus.selected_record()
    record['meta']['Model SPT'] = 'Amendment 002'
    refused = adapt_corporate_detail(iter([corpus.primary()]), record, corpus.SCOPE, observed)
    assert not refused['eligible']
    assert refused['reason'] == 'unverified_corporate_induk_submitted_lifecycle'


def test_non_submitted_source_status_refuses_the_projection():
    observed = corpus.observed()
    record = corpus.selected_record()
    record['source_status'] = 'SPT Draft'
    refused = adapt_corporate_detail(iter([corpus.primary()]), record, corpus.SCOPE, observed)
    assert not refused['eligible']
    assert refused['reason'] == 'unverified_corporate_induk_submitted_lifecycle'


def test_projected_section_keeps_its_dump_as_custody_and_reports_partial():
    observed = corpus.observed()
    result = adapt_corporate_detail(iter([corpus.primary()]), corpus.selected_record(),
                                    corpus.SCOPE, observed)
    assert result['eligible'] and result['coverage']['complete']
    section, = result['sections']
    assert section['name'] == 'Induk'
    assert len(section['fields']) == 3  # corpus carries three identity controls only
    assert [f['field'] for f in section['fields']] == ['TaxYear', 'Tin', 'Name']
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'unprojected_induk_captions'
    # The generic dump stays as custody evidence, it is not the worksheet.
    assert any(table['headers'] == ['JSON path', 'JSON type', 'Source value']
               for table in section['tables'])
    projected, = result['provenance']['projections']
    assert projected['form'] == 'Induk' and projected['kind'] == 'corporate-induk-v1'
    assert [entry['path'] for entry in projected['values']] == [
        ['MainFormData', 'TaxYear'], ['MainFormData', 'Tin'], ['MainFormData', 'Name']]


def test_extra_evidence_roots_are_left_as_plain_evidence():
    observed = corpus.observed(['L11BFormData'])
    form = corpus.current_form()
    form['L11BFormData'] = {}
    result = adapt_corporate_detail(iter([corpus.primary(form)]), corpus.selected_record(),
                                    corpus.SCOPE, observed)
    assert result['eligible']
    section, = result['sections']
    assert section['fields'] == []
    assert 'projections' not in result['provenance']


def test_projection_does_not_mutate_the_observed_bindings_or_source():
    observed = corpus.observed()
    before = deepcopy(observed)
    payload = corpus.primary()
    raw = payload['body']
    adapt_corporate_detail(iter([payload]), corpus.selected_record(), corpus.SCOPE, observed)
    assert observed == before and payload['body'] == raw
