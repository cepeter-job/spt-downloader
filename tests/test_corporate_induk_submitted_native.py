"""Actual synthetic SPA -> owned capture -> populated Induk -> held/workbook, CI only."""
from copy import deepcopy
import hashlib
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_browser as driver
import coretax_corporate as observer
import coretax_corporate_projection as projection
from coretax_json import JsonSafetyError, adapt_corporate_detail
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture, ASSET
from test_corporate_l1d_observer import open_selected
from test_corporate_induk_submitted import SLOTS, source, DETAIL
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


class IndukFixture(Fixture):
    def __init__(self, browser, monkeypatch, *, defect=None, net=1234567):
        super().__init__(browser, monkeypatch, defect=defect)
        current = json.loads(self.raw)['Payload']
        root = json.loads(current['CurrentFormData'])
        approved = source(NetIncomeBeforeTax=net)['Payload']
        root['MainFormData'] = json.loads(approved['CurrentFormData'])['MainFormData']
        current.update({k: v for k, v in approved.items() if k != 'CurrentFormData'})
        current['CurrentFormData'] = corpus.wire(root)
        self.raw = corpus.wire({'IsSuccessful': True, 'Payload': current}).encode()
        monkeypatch.setattr(projection, 'INDUK_SUBMITTED_BUILD_DIGESTS', dict(self.pins), raising=False)

    def detail(self):
        markup = super().detail()
        controls = ''.join('<p-inputnumber id="' + key + '" formcontrolname="' + key
            + '" mode="decimal"><input disabled '
            + ('readonly ' if key == 'TotalApprovalInstallment' else '')
            + 'value="SYNTHETIC DOM BAIT"></p-inputnumber>' for _, key, _ in SLOTS)
        controls += ('<p-radiobutton formcontrolname="IsApprovalInstallment"><input type="radio" disabled>'
                     '</p-radiobutton>') * 2
        return markup.replace('<label>SYNTHETIC STRUCTURAL PLACEHOLDER</label>', controls)


@pytest.mark.parametrize('net', [1234567, -1234567])
def test_owned_populated_induk_replays_original_bytes_and_saves_amounts_with_partial_audit(
        browser, tmp_path, monkeypatch, net):
    fixture = IndukFixture(browser, monkeypatch, net=net)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                                           approved_digest=fixture.pins[ASSET])
            assert forms is not None
            assert forms[0]['projection']['kind'] == 'corporate-induk-submitted-v2'
            assert forms[0]['projection']['controls'] == [s[1] for s in SLOTS]
            manifest = capture.drain()
            assert manifest['complete'] and manifest['component_lifetime']['same_document']
            bodies = list(capture.iter_bodies())
            assert len(bodies) == 1 and bodies[0]['body'] == fixture.raw
            result = adapt_corporate_detail(bodies, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            section = result['sections'][0]
            assert len(section['fields']) == 18 and section['projection_complete'] is False
            fixture.record['detail_url'] = DETAIL
            replay = adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                                            fixture.record, corpus.SCOPE, forms)
            assert replay['eligible'] and replay['sections'] == result['sections']
            assert replay['provenance'] == result['provenance']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period',
               'inventory_complete': True, 'complete': True, 'errors': [], 'records': [fixture.record]}
        checkpoint = deepcopy(fixture.record['sections'])
        folder = tmp_path / 'export'
        coretax.save_output(run, folder)
        coretax.verify_outputs(run, folder)
        filename, = [n for n in run['output_files'] if n != 'resume.xlsx']
        workbook = load_workbook(folder / filename)
        try:
            sheet = workbook['Induk']
            rows = {row[0].value: row[1] for row in sheet.iter_rows() if row[0].value}
            assert rows['1. NPWP'].value == corpus.NPWP
            assert rows['4. Nomor Telepon'].value == '0000000000'
            for label, expected in (
                ('Penghasilan Neto Fiskal sebelum Fasilitas Pajak', net),
                ('PPh Terutang', 123456), ('Angsuran PPh Pasal 25', 3456),
                ('PPh yang Kurang/Lebih Bayar', -5678),
                ('PPh yang masih harus dibayar atau lebih dibayar', 7890)):
                assert rows[label].value == expected and rows[label].data_type == 'n'
                assert 'Rp' in rows[label].number_format
            assert 'Tarif Pajak *' not in rows
        finally:
            workbook.close()
        report, = [r for r in run['template_mapping'] if r['form'] == 'Induk']
        assert report['complete'] is False and report['derived_complete'] is False
        assert report['derived_reason'] == 'unprojected_induk_captions'
        audit = load_workbook(folder / 'resume.xlsx')
        try:
            texts = [str(c.value) for sheet in audit for row in sheet for c in row if c.value is not None]
            assert any('PARTIAL' in text for text in texts)
            assert any('Induk diproyeksikan sebagian: masih ada slot deklarasi yang belum terbukti.' in text
                       for text in texts)
            assert not any('hanya slot identitas' in text for text in texts)
        finally:
            audit.close()
        assert fixture.record['sections'] == checkpoint
        assert fixture.unexpected == []
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['vendor-pin', 'main-fetch-only', 'vendor-preload-only'])
def test_optional_induk_capability_never_accepts_unverified_script_providers(browser, tmp_path, monkeypatch, defect):
    fixture = IndukFixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            # Other forms retain their independent source refusals; examine the
            # Induk helper directly so an L1-D refusal cannot mask this boundary.
            helper = getattr(observer, '_observe_induk_submitted', None)
            assert callable(helper), 'Missing real Induk optional proof producer'
            proof = helper(page, page.locator('rshshr-citr-main-form'), capture,
                           fixture.pins[ASSET], None)
            assert proof is None
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['enabled-amount', 'missing-radio', 'enabled-radio', 'editable-approval'])
def test_unsubmitted_or_editor_structure_cannot_grant_amount_capability(browser, tmp_path, monkeypatch, defect):
    fixture = IndukFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            page.evaluate('''defect=>{
                const form=document.querySelector('rshshr-citr-main-form');
                if(defect==='enabled-amount')form.querySelector('#NoticeOfCollection input').disabled=false;
                if(defect==='missing-radio')form.querySelector('p-radiobutton').remove();
                if(defect==='enabled-radio')form.querySelector('p-radiobutton input').disabled=false;
                if(defect==='editable-approval')form.querySelector('#TotalApprovalInstallment input').readOnly=false;
            }''', defect)
            assert observer._observe_induk_submitted(page, page.locator('rshshr-citr-main-form'), capture,
                fixture.pins[ASSET], None) is None
            assert page.evaluate('window.businessReads') == 0
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['descriptor-override', 'mixed-attempt', 'changed-bytes'])
def test_populated_induk_held_reader_keeps_original_manifest_custody(browser, tmp_path, monkeypatch, defect):
    fixture = IndukFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            open_selected(fixture, capture)
            forms = observer.observe_forms(fixture.page, fixture.record, corpus.SCOPE, capture,
                approved_digest=fixture.pins[ASSET])
            assert forms[0]['projection']['kind'] == 'corporate-induk-submitted-v2'
            manifest = capture.drain()
            fixture.record['detail_url'] = DETAIL
            assert adapt_corporate_detail(checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE),
                fixture.record, corpus.SCOPE, forms)['eligible']
            if defect == 'changed-bytes':
                path = tmp_path / manifest['responses'][0]['relative_path']
                path.write_bytes(path.read_bytes() + b' ')
            else:
                path = tmp_path / manifest['manifest']
                saved = json.loads(path.read_bytes())
                if defect == 'descriptor-override':
                    saved['responses'][0]['component_lifetime'] = deepcopy(saved['component_lifetime'])
                else:
                    saved['component_lifetime']['attempt'] = 'b' * 32
                raw = corpus.wire(saved).encode()
                path.write_bytes(raw)
                manifest = {**saved, 'manifest': manifest['manifest'],
                            'manifest_sha256': hashlib.sha256(raw).hexdigest()}
            with pytest.raises(JsonSafetyError):
                checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE)
    finally:
        fixture.close()


def test_induk_stop_and_changed_owned_route_are_not_demoted_to_legacy_success(browser, tmp_path, monkeypatch):
    fixture = IndukFixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            def stop():
                raise driver.CaptureCancelled('SYNTHETIC STOP')
            with pytest.raises(driver.CaptureCancelled):
                observer.observe_forms(page, fixture.record, corpus.SCOPE, capture,
                    approved_digest=fixture.pins[ASSET], check_cancel=stop)
            # The legacy component fact proves Document/route ownership, not
            # continuous child/root identity. Exercise the authority it owns.
            page.evaluate("history.pushState({}, '', location.pathname + '/changed')")
            with pytest.raises(JsonSafetyError):
                capture.drain()
    finally:
        fixture.close()
