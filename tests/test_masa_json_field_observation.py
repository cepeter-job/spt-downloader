# Public UI structures with synthetic values; Edge execution is runner-only.
import json

import pytest

from coretax_browser import GROUP_JS
from test_masa_json_observer import browser, observer_module, observed

TRAPS = r"""() => {
 window.valueReads=0;
 const trap=()=>{window.valueReads++;throw Error('DOM source values are forbidden');};
 for(const property of ['value','checked'])Object.defineProperty(HTMLInputElement.prototype,property,{get:trap});
 for(const property of ['value','selectedOptions','selectedIndex'])Object.defineProperty(HTMLSelectElement.prototype,property,{get:trap});
 for(const element of document.querySelectorAll('.p-dropdown-label'))
   for(const property of ['textContent','innerText'])Object.defineProperty(element,property,{get:trap});
}"""

PERIOD = """<div class="p-accordion-header"><span class="p-accordion-header-text">A. IDENTITAS PEMOTONG</span></div>
<div class="p-accordion-content"><div class="form-group row">
<label ariaLabel="Tax Period" class="col-sm-2 col-form-label">Masa Pajak</label>
<div class="col-sm-2"><ui-dropdown><p-dropdown><div class="p-dropdown">
<div class="p-hidden-accessible"><input role="combobox" id="generated-period" value="DOM-PERIOD-TRAP"></div>
<span class="p-dropdown-label">DOM-LABEL-TRAP</span><div class="p-dropdown-trigger">Open</div>
</div></p-dropdown></ui-dropdown></div></div></div>"""


def metadata(browser, body, tax='PPh Unifikasi'):
    module = observer_module()
    context = browser.new_context()
    try:
        page = context.new_page()
        page.set_content('<div class="p-tabview"><div class="p-tabview-panels"><div id="fields" class="p-tabview-panel">' + body + '</div></div></div>')
        page.evaluate(TRAPS)
        result = page.locator('#fields').evaluate(module.FIELDS.replace('GROUP', GROUP_JS),
                                                   {'tax': tax, 'form': 'INDUK'})
        assert page.evaluate('window.valueReads') == 0
        assert 'TRAP' not in json.dumps(result)
        return result
    finally:
        context.close()


def test_custom_period_dropdown_uses_reviewed_control_binding_not_generated_input_id(browser):
    assert metadata(browser, PERIOD) == [{
        'field': 'TaxPeriodCode', 'label': 'Masa Pajak', 'group': 'A. IDENTITAS PEMOTONG',
        'column_label': '', 'tag': 'UI-DROPDOWN'}]


@pytest.mark.parametrize('body', [
    PERIOD.replace('Masa Pajak', 'UNKNOWN PERIOD LABEL'),
    PERIOD.replace('Tax Period', 'Unknown role'),
    '<ui-dropdown><p-dropdown><span class="p-dropdown-label">DOM-LABEL-TRAP</span></p-dropdown></ui-dropdown>',
    '<p-dropdown><span class="p-dropdown-label">DOM-LABEL-TRAP</span></p-dropdown>',
])
def test_unbound_custom_control_cannot_disappear_from_observed_coverage(browser, body):
    assert metadata(browser, body) is None


def radio(value, label):
    return (f'<p-radiobutton formcontrolname="DeclarationBy" name="DeclarationBy" value="{value}" label="{label}">'
            f'<div><input type="radio" id="choice-{value}" value="{value}" checked>'
            f'<label for="choice-{value}">{label}</label></div></p-radiobutton>')


def test_radio_options_are_structure_and_not_the_current_selection(browser):
    body = '<h3>C. PERNYATAAN DAN TANDA TANGAN</h3>' + radio('0', 'Wajib Pajak') + radio('1', 'Kuasa Wajib Pajak')
    assert metadata(browser, body) == [
        {'field': 'DeclarationBy', 'label': 'Wajib Pajak', 'group': 'C. PERNYATAAN DAN TANDA TANGAN',
         'column_label': '', 'tag': 'P-RADIOBUTTON', 'option': '0'},
        {'field': 'DeclarationBy', 'label': 'Kuasa Wajib Pajak', 'group': 'C. PERNYATAAN DAN TANDA TANGAN',
         'column_label': '', 'tag': 'P-RADIOBUTTON', 'option': '1'},
    ]


@pytest.mark.parametrize('body', [radio('2', 'Unknown'), radio('0', 'UNKNOWN LABEL'),
    radio('0', 'Wajib Pajak').replace('DeclarationBy', 'UnknownControl')])
def test_unknown_radio_contract_does_not_become_verified_metadata(browser, body):
    assert metadata(browser, body) is None


def test_checkbox_metadata_never_reads_checked_or_value(browser):
    body = '<h3>C. PERNYATAAN DAN TANDA TANGAN</h3><label for="agree">Declaration</label><input id="agree" type="checkbox" formcontrolname="MyCheckBox" checked>'
    assert metadata(browser, body) == [{
        'field': 'MyCheckBox', 'label': 'Declaration', 'group': 'C. PERNYATAAN DAN TANDA TANGAN',
        'column_label': '', 'tag': 'INPUT'}]


COLUMNS = ['Harga Jual/Penggantian/ Nilai Ekspor/DPP (Rupiah)',
           'DPP Nilai Lain/ DPP (Rupiah)', 'PPN (Rupiah)', 'PPnBM (Rupiah)']
CONTROLS = ['DomesticDeliveriesSelfCollected', 'DomesticDeliveriesSelfCollectedOtherTaxBase',
            'DomesticDeliveriesSelfCollectedVAT', 'DomesticDeliveriesSelfCollectedSTLG']


def amount_grid(populated, *, header=True):
    labels = '<div class="row"><div class="col-md-7"></div><div class="col-md-5"><div class="row">'
    labels += ''.join('<div class="col-md-3">' + value + '</div>' for value in COLUMNS) + '</div></div></div>'
    cells = []
    for index, control in enumerate(CONTROLS):
        content = (f'<p-inputnumber formcontrolname="{control}"><span><input value="DOM-AMOUNT-TRAP"></span></p-inputnumber>'
                   if index in populated else '')
        cells.append('<div class="col-md-3">' + content + '</div>')
    return ('<div class="p-accordion-content">' + (labels if header else '') +
            '<div class="row"><div class="col-md-7"><label>Self-collected deliveries</label></div>'
            '<div class="col-md-5"><div class="row">' + ''.join(cells) + '</div></div></div></div>')


@pytest.mark.parametrize('populated', [(0, 2, 3), (1, 3)])
def test_amount_wrappers_bind_physical_columns_without_duplicate_inner_inputs(browser, populated):
    result = metadata(browser, '<h3>I. PENYERAHAN BARANG DAN JASA</h3>' + amount_grid(populated), 'PPN')
    assert result == [{
        'field': CONTROLS[index], 'label': 'Self-collected deliveries',
        'group': 'I. PENYERAHAN BARANG DAN JASA', 'column_label': COLUMNS[index],
        'tag': 'P-INPUTNUMBER'} for index in populated]


def test_amount_column_never_borrows_a_sibling_accordion_header(browser):
    result = metadata(browser, amount_grid(()) + amount_grid((2,), header=False), 'PPN')
    assert len(result) == 1 and result[0]['column_label'] == ''


def test_full_observer_carries_custom_period_metadata_to_the_masa_binding(browser, tmp_path, monkeypatch):
    with observed(browser, tmp_path, monkeypatch, tax='PPh Unifikasi', induk_fields=PERIOD) as (module, fixture, capture):
        forms = module.observe_masa_forms(fixture.page, fixture.record, ['0000000000000001', 2025, 'period'], capture, max_pages=5)
        assert forms is not None
        assert forms[0]['fields'] == [{
            'field': 'TaxPeriodCode', 'label': 'Masa Pajak', 'group': 'A. IDENTITAS PEMOTONG',
            'column_label': '', 'tag': 'UI-DROPDOWN'}]
        assert fixture.page.evaluate('window.valueReads') == 0
