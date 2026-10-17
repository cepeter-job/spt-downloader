"""Public PPN formControl checkbox markup; synthetic, runner-only contracts."""
import pytest

from masa_json_fixtures import SCOPE
from support_masa_native import browser, observed
from test_masa_json_field_observation import metadata

GROUP = 'III. PENGHITUNGAN PPN KURANG BAYAR / LEBIH BAYAR'
# Public Ja/Wa bind form.controls.ReplacementPrevious via [formControl],
# not formControlName. Only static host/label structure identifies this control.
REPLACEMENT = f'''<div class="p-accordion-header">
<span class="p-accordion-header-text">{GROUP}</span></div>
<div class="p-accordion-content"><div>
<p-checkbox class="checkbox-up"><div class="p-checkbox">
<div class="p-hidden-accessible"><input type="checkbox" value="DOM-VALUE-TRAP" checked></div>
<div class="p-checkbox-box" role="checkbox" aria-checked="true"></div>
</div></p-checkbox>
<label ariaLabel="Replace Previous Tax Return" class="col-form-label">Ganti SPT sebelumnya</label>
</div></div>'''


@pytest.mark.parametrize('checked', [True, False])
def test_replacement_checkbox_binds_static_metadata_without_reading_dom_state(browser, checked):
    body = REPLACEMENT if checked else REPLACEMENT.replace(' checked>', '>')
    assert metadata(browser, body, tax='PPN') == [{
        'field': 'ReplacementPrevious', 'label': 'Ganti SPT sebelumnya',
        'group': GROUP, 'column_label': '', 'tag': 'P-CHECKBOX',
    }]


def test_replacement_checkbox_does_not_abort_the_seven_form_observer(browser, tmp_path, monkeypatch):
    with observed(browser, tmp_path, monkeypatch, induk_fields=REPLACEMENT) as (module, fixture, capture):
        result = module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert fixture.page.evaluate('window.valueReads') == 0
    assert result is not None
    assert len(result) == 7
    assert [field['field'] for field in result[0]['fields']] == ['ReplacementPrevious']


@pytest.mark.parametrize('body', [
    REPLACEMENT.replace('Ganti SPT sebelumnya', 'Unknown checkbox'),
    REPLACEMENT.replace('Replace Previous Tax Return', 'Unknown role'),
    REPLACEMENT.replace('</p-checkbox>', '</p-checkbox><p-checkbox><input type="checkbox"></p-checkbox>'),
])
def test_unknown_or_ambiguous_checkbox_still_rejects_native_observation(browser, tmp_path, monkeypatch, body):
    with observed(browser, tmp_path, monkeypatch, induk_fields=body) as (module, fixture, capture):
        assert module.observe_masa_forms(fixture.page, fixture.record, SCOPE, capture, max_pages=5) is None
        assert fixture.page.evaluate('window.valueReads') == 0


@pytest.mark.parametrize('tax,form_name', [
    ('PPh Unifikasi', 'INDUK'), ('PPN', 'A-1'), ('PPN', 'C'),
])
def test_replacement_binding_is_not_inferred_outside_ppn_induk(browser, tax, form_name):
    result = metadata(browser, REPLACEMENT, tax=tax, form_name=form_name)
    assert result is None or all(field['field'] != 'ReplacementPrevious' for field in result)
