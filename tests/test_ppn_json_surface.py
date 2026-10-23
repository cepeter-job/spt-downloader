"""Public PPN component structures; synthetic values, runner-only Edge."""
import json

import pytest

from masa_observer_fixture import Fixture
from masa_json_fixtures import SCOPE
from support_masa_native import browser, observed
from test_masa_json_field_observation import metadata
from test_ppn_json_amendment import amend_case, decode, reseal

CHOICES = {
    'CARRY_FORWARD': '1. dikompensasikan',
    'FAST_REFUND': '2. dikembalikan melalui pengembalian pendahuluan',
    'FORWARD_REFUND': '3. dikembalikan melalui pemeriksaan',
}
RADIOS = ''.join(
    f'<p-radiobutton formcontrolname="AskedTo" name="AskedTo" value="{code}" label="{label}">'
    f'<input type="radio" value="DOM-VALUE-TRAP" checked><label>{label}</label></p-radiobutton>'
    for code, label in CHOICES.items())
LAYOUT = '''<h3>I. PENYERAHAN BARANG DAN JASA</h3><div class="row">
<div class="col-md-7"><table><tr><td>1.</td><td><label>Ekspor Barang Kena Pajak</label></td></tr></table></div>
<div class="col-md-5"><p-inputnumber formcontrolname="ExportOfTangibleGoods"><input value="DOM-VALUE-TRAP"></p-inputnumber></div></div>'''
PAGINATOR_CONTROL = '''<p-paginator><p-dropdown><span class="p-dropdown-label">DOM-LABEL-TRAP</span>
<input role="combobox" value="DOM-VALUE-TRAP"></p-dropdown></p-paginator>'''


def test_ppn_label_layout_table_is_not_a_financial_grid_and_does_not_hide_amount(browser, tmp_path, monkeypatch):
    with observed(browser, tmp_path, monkeypatch, induk_fields=LAYOUT) as (module, fixture, capture):
        result = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert fixture.page.evaluate('window.valueReads') == 0
    assert result is not None
    assert result[0]['tables'] == []
    assert [f['field'] for f in result[0]['fields']] == ['ExportOfTangibleGoods']
    assert result[0]['fields'][0]['label'] == 'Ekspor Barang Kena Pajak'


def test_owned_ppn_grid_page_size_control_is_structure_not_a_business_field(browser, tmp_path, monkeypatch):
    original = Fixture.table
    def with_page_size(self, *args):
        return original(self, *args).replace('<div class="p-paginator">', '<div class="p-paginator">' + PAGINATOR_CONTROL)
    monkeypatch.setattr(Fixture, 'table', with_page_size)
    with observed(browser, tmp_path, monkeypatch) as (module, fixture, capture):
        result = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert fixture.page.evaluate('window.valueReads') == 0
    assert result is not None
    assert len(result) == 7
    assert all([field['field'] for field in form['fields']] == ['FullName'] for form in result[1:])


@pytest.mark.parametrize('table', [
    '<table><thead><tr><th>Unreviewed data</th></tr></thead><tbody><tr><td>DOM-ROW-TRAP</td></tr></tbody></table>',
    '<table><tr><td>First data row</td></tr><tr><td>Second data row</td></tr></table>',
    '<table><tr><td><input id="unreviewed" value="DOM-VALUE-TRAP"></td></tr></table>',
])
def test_unreviewed_table_cannot_hide_behind_ppn_layout_columns(browser, tmp_path, monkeypatch, table):
    body = '<div class="row"><div class="col-md-7">' + table + '</div></div>'
    with observed(browser, tmp_path, monkeypatch, induk_fields=body) as (module, fixture, capture):
        assert module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5) is None


@pytest.mark.parametrize('body', [PAGINATOR_CONTROL, '<p-table>' + PAGINATOR_CONTROL + '</p-table>'])
def test_unowned_page_size_like_control_remains_unsupported(browser, body):
    assert metadata(browser, body, tax='PPN', form_name='A-1') is None


def test_asked_to_static_options_are_observed_without_checked_or_value_reads(browser):
    result = metadata(browser, '<h3>III. PENGHITUNGAN PPN</h3>' + RADIOS, tax='PPN')
    assert result is not None
    assert [(f['field'], f['option'], f['label']) for f in result] == [
        ('AskedTo', code, label) for code, label in CHOICES.items()]


@pytest.mark.parametrize('label,role,field', [
    ('Tanggal Penandatanganan SPT', '', 'DateOfTaxReturnSigning'),
    ('Batas Waktu Penyampaian SPT', 'Deadline Submission', 'DeadlineSubmission'),
])
def test_known_ppn_calendar_metadata_is_not_a_dom_date_value(browser, label, role, field):
    body = f'<div class="form-group row"><label ariaLabel="{role}">{label}</label><p-calendar><span><input value="DOM-DATE-TRAP"></span></p-calendar></div>'
    result = metadata(browser, body, tax='PPN')
    assert result is not None and len(result) == 1
    assert result[0]['field'] == field
    assert result[0]['tag'] == 'P-CALENDAR'


def test_unreviewed_ppn_calendar_is_not_given_a_guessed_binding(browser):
    body = '<div class="form-group row"><label>Unknown date</label><p-calendar><input value="DOM-DATE-TRAP"></p-calendar></div>'
    assert metadata(browser, body, tax='PPN') is None


@pytest.mark.parametrize('choice', [None, *CHOICES])
def test_only_response_proven_final_radio_option_reaches_the_workbook_fields(choice):
    case = amend_case()
    envelope = json.loads(case['packets'][0]['body'])
    data = json.loads(envelope['Payload']['FormData'])
    data.update(AskedTo=choice, VATUnderOrOverPaidDueToAmendment={'VAT': 0 if choice is None else -1})
    # Both export stages and the exact facility code establish preservation;
    # a final A1 total alone does not exclude earlier calendar/facility writes.
    data.update(TaxPeriod='01012025', BookkeepingPeriodEnd=12, FacilityRegisters=['AS.09-01'])
    envelope['Payload']['FormData'] = json.dumps(data)
    reseal(case, envelope)
    case['forms'][0]['fields'] += [
        {'field': 'AskedTo', 'label': label, 'group': 'III. PENGHITUNGAN PPN',
         'column_label': '', 'tag': 'P-RADIOBUTTON', 'option': code}
        for code, label in CHOICES.items()]
    result = decode(case)
    assert result['eligible'] is True, result['reason']
    selected = [f for f in result['sections'][0]['fields'] if f['field'] == 'AskedTo']
    assert len(selected) == (0 if choice is None else 1)
    if choice is not None:
        assert selected[0]['value'] == choice and selected[0]['label'] == CHOICES[choice]
    evidence = [p for p in result['provenance']['bindings'] if p.get('destination', {}).get('field') == 'AskedTo']
    assert evidence and any(p['path'] == ['AskedTo'] for p in evidence)
    rule = 'not_overpaid_clear' if choice is None else 'export_blocks_calendar_override'
    assert all(p['projection_rule'] == rule for p in evidence)


def test_unknown_radio_option_metadata_stays_ineligible():
    case = amend_case()
    case['forms'][0]['fields'].append({'field': 'AskedTo', 'label': 'Unknown choice',
        'group': '', 'column_label': '', 'tag': 'P-RADIOBUTTON', 'option': 'UNKNOWN'})
    assert decode(case)['eligible'] is False
