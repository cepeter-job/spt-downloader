"""Inactive submitted controls: fixed-zero source invariant, never child history."""
from copy import deepcopy
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
import coretax_corporate as observer
from coretax_json import adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import ASSET
from test_corporate_l1d_observer import open_selected
from test_corporate_induk_submitted import bindings, packet, source
from test_corporate_induk_submitted_native import IndukFixture
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus

GROUP = ('C. PENGHASILAN YANG DIKENAKAN PPh YANG BERSIFAT FINAL DAN '
         'YANG TIDAK TERMASUK OBJEK PAJAK')
EXTRA = (
    (GROUP, 'TotalIncomeSubject', '2. Apakah Wajib Pajak menerima atau memperoleh penghasilan yang dikenakan PPh yang bersifat final? * / Tidak / Ya'),
    (GROUP, 'TotalIncomeExcluded', '3. Apakah Wajib Pajak menerima atau memperoleh penghasilan yang tidak termasuk objek pajak? * / Tidak / Ya'),
    ('E. PENGURANG PPh TERUTANG', 'TotalIncomeTaxDeduction', '16. Apakah Wajib Pajak memperoleh Fasilitas Pengurangan PPh Badan? * / Tidak / Ya'),
    ('F. PPh KURANG/LEBIH BAYAR', 'UnderpaymentIncomeDueAmended', '18.b. PPh yang kurang atau lebih bayar karena pembetulan'),
)
SELECTORS = ('IsIncomeSubject', 'IsIncomeExcluded', 'IsIncomeTaxDeduction')


def inactive_source(**changes):
    return source(**dict(zip(SELECTORS, (0, 0, 0))),
        **{key: 0 for _, key, _ in EXTRA[:3]}, UnderpaymentIncomeDueAmended=None,
        **changes)


def inactive_binding():
    observed = bindings()
    observed[0]['projection']['kind'] = 'corporate-induk-submitted-v3'
    observed[0]['projection']['controls'] += [key for _, key, _ in EXTRA]
    return observed


def run_adapter(value=None, observed=None):
    from test_corporate_l7_native import selected
    return adapt_corporate_detail([packet(inactive_source() if value is None else value)],
        selected(), corpus.SCOPE, inactive_binding() if observed is None else observed)


def test_original_zero_amounts_and_normal_null_are_a_fixed_point_not_radio_amounts():
    value, observed = inactive_source(), inactive_binding()
    before = deepcopy((value, observed))
    result = run_adapter(value, observed)
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    section, = result['sections']
    assert len(section['fields']) == 22 and section['projection_complete'] is False
    for group, control, caption in EXTRA:
        field, = [f for f in section['fields'] if f['label'] == caption]
        assert (field['group'], field['field'], field['value']) == (group, '', '' if control == EXTRA[-1][1] else '0')
    report, = result['provenance']['projections']
    assert report['kind'] == 'corporate-induk-submitted-v3'
    for key in (*SELECTORS, *(control for _, control, _ in EXTRA)):
        entry, = [v for v in report['values'] if v['path'] == ['MainFormData', key]]
        assert entry['container'] == ['Payload', 'CurrentFormData']
        assert entry['response_sequence'] == 1
        assert entry['type'] == ('null' if key == EXTRA[-1][1] else 'number')
        assert entry['value'] == (None if key == EXTRA[-1][1] else '0')
    assert (value, observed) == before


@pytest.mark.parametrize('key', [*SELECTORS, *(control for _, control, _ in EXTRA[:3])])
@pytest.mark.parametrize('value', [None, False, '0', 1, corpus.Number('-0'), corpus.Number('0.1')])
def test_nonzero_coercive_or_absent_fixed_point_is_not_inactive_permission(key, value):
    raw = inactive_source()
    current = json.loads(raw['Payload']['CurrentFormData'])
    current['MainFormData'][key] = value
    raw['Payload']['CurrentFormData'] = corpus.wire(current)
    result = run_adapter(raw)
    assert not result['eligible'] and result['sections'] == []
    assert result['reason'] == 'unsupported_corporate_induk_inactive_profile'


@pytest.mark.parametrize('key', [*SELECTORS, *(control for _, control, _ in EXTRA)])
def test_inactive_control_presence_is_original_not_a_null_or_zero_default(key):
    raw = inactive_source()
    current = json.loads(raw['Payload']['CurrentFormData'])
    del current['MainFormData'][key]
    raw['Payload']['CurrentFormData'] = corpus.wire(current)
    result = run_adapter(raw)
    assert not result['eligible'] and result['reason'] == 'unsupported_corporate_induk_inactive_profile'


@pytest.mark.parametrize('value', [0, False, '0', -1])
def test_normal_amendment_difference_must_already_be_literal_null(value):
    raw = inactive_source()
    current = json.loads(raw['Payload']['CurrentFormData'])
    current['MainFormData']['UnderpaymentIncomeDueAmended'] = value
    raw['Payload']['CurrentFormData'] = corpus.wire(current)
    result = run_adapter(raw)
    assert not result['eligible'] and result['reason'] == 'unsupported_corporate_induk_inactive_profile'


class InactiveFixture(IndukFixture):
    def __init__(self, browser, monkeypatch, *, defect=None):
        super().__init__(browser, monkeypatch, defect=defect)
        raw = json.loads(self.raw)
        current = json.loads(raw['Payload']['CurrentFormData'])
        approved = json.loads(inactive_source()['Payload']['CurrentFormData'])['MainFormData']
        current['MainFormData'] = approved
        raw['Payload']['CurrentFormData'] = corpus.wire(current)
        self.raw = corpus.wire(raw).encode()

    def detail(self):
        markup = super().detail()
        controls = ''.join('<p-inputnumber id="' + key + '" formcontrolname="' + key
            + '" mode="decimal"><input disabled value="SYNTHETIC BAIT"></p-inputnumber>'
            for _, key, _ in EXTRA)
        controls += ''.join(('<p-radiobutton formcontrolname="' + key
            + '"><input type="radio" disabled></p-radiobutton>') * 2 for key in SELECTORS)
        return markup.replace('</rshshr-citr-main-form>', controls + '</rshshr-citr-main-form>')


def test_real_inactive_observer_capture_hybrid_both_held_readers_and_partial_workbook(
        browser, tmp_path, monkeypatch):
    fixture = InactiveFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            assert forms[0]['projection']['kind'] == 'corporate-induk-submitted-v3'
            monkeypatch.setattr(driver, 'CIT_SOURCE_SHA256', fixture.pins[ASSET])
            native = driver._hybrid_detail(page, fixture.record, corpus.SCOPE, tmp_path, capture, 5, None)
            assert native['detail_source']['used'] == 'json'
            assert native['detail_source']['coverage']['complete']
            manifest = capture.drain()
            fixture.record['detail_url'] = page.url
            result = adapt_corporate_detail(list(capture.iter_bodies()), fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            for reader in (checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),):
                replay = adapt_corporate_detail(reader, fixture.record, corpus.SCOPE, forms)
                assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
            assert native['sections'] == result['sections']
            assert native['detail_source']['json'] == result['provenance']
            assert page.evaluate('window.businessReads') == 0
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
            'inventory_complete': True, 'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        filename, = [name for name in run['output_files'] if name != 'resume.xlsx']
        workbook = load_workbook(tmp_path / 'export' / filename)
        try:
            sheet = workbook['Induk']
            assert sum(cell.value == 0 for row in sheet for cell in row) >= 3
        finally:
            workbook.close()
        report, = [r for r in run['template_mapping'] if r['form'] == 'Induk']
        assert report['complete'] is False and report['derived_reason'] == 'unprojected_induk_captions'
        assert fixture.unexpected == []
    finally:
        fixture.close()


@pytest.mark.parametrize('key', [*SELECTORS, *(control for _, control, _ in EXTRA)])
def test_optional_inactive_structure_never_adopts_an_enabled_or_missing_control(
        browser, tmp_path, monkeypatch, key):
    fixture = InactiveFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            page.evaluate('key=>document.querySelector("[formcontrolname="+key+"] input").disabled=false', key)
            proof = observer._observe_induk_submitted(page, page.locator('rshshr-citr-main-form'),
                capture, fixture.pins[ASSET], None)
            assert proof['kind'] == 'corporate-induk-submitted-v2'
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()
