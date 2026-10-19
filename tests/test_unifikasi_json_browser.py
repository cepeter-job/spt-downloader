"""Real local synthetic Edge -> capture -> projection -> Excel; runner-only."""
import hashlib
import pytest
import coretax_browser
import coretax_masa_bindings
import support_masa_native
from masa_json_fixtures import SCOPE
from masa_observer_fixture import BUILD, MAIN, ASSETS
from support_masa_native import browser, observed, exported
from unifikasi_observer_fixture import NativeFixture


@pytest.mark.parametrize('submitted', [False, True])
def test_reviewed_returnless_getter_cannot_patch_checkbox_true(browser, submitted):
    # Same guard and initial ngModel as pinned chunk 693; no portal/claims access.
    page = browser.new_page()
    try:
        result = page.evaluate("""submitted => {
            let truePatches=0;
            const component={isStatusSubmitted:submitted,isChecked:false,
                form:{get:()=>({value:'Submitted'}),disable:()=>{},
                      patchValue:()=>{truePatches++;}},
                getDataFromMainForm(){const parsed={TaxPeriodCode:'01012025'};},
                ngOnChanges(){null!=this.getDataFromMainForm()&&
                    (this.isStatusSubmitted||this.form?.get('SubmitInProgressStatus')?.value)&&
                    (this.form.disable(),this.form.patchValue({MyCheckBox:true}));}};
            component.ngOnChanges();
            return {checked:component.isChecked,truePatches};
        }""", submitted)
        assert result == {'checked': False, 'truePatches': 0}
    finally:
        page.close()


def test_connected_native_unifikasi_never_reads_dom_business_values(browser, tmp_path, monkeypatch):
    monkeypatch.setattr(support_masa_native, 'Fixture', NativeFixture)
    digest = hashlib.sha256(BUILD).hexdigest()
    monkeypatch.setitem(coretax_masa_bindings.BUILD_DIGESTS, MAIN, digest)
    monkeypatch.setitem(coretax_masa_bindings.BUILD_DIGESTS, ASSETS['PPh Unifikasi'], digest)
    def forbidden(*args, **kwargs):
        raise AssertionError('Connected native Unifikasi must not fall back to DOM')
    monkeypatch.setattr(coretax_browser, 'capture_detail', forbidden)
    (tmp_path / 'capture').mkdir()
    (tmp_path / 'export').mkdir()
    with observed(browser, tmp_path / 'capture', monkeypatch, 'PPh Unifikasi') as (_, fixture, capture):
        result = coretax_browser._hybrid_detail(fixture.page, fixture.record, SCOPE,
                                                tmp_path, capture, 5, None)
        assert result['capture_complete']
        assert result['detail_source']['used'] == 'json'
        assert result['detail_source']['coverage']['complete']
        grids = result['detail_source']['coverage']['grids']
        assert len(grids) == 5 and all(g['source_total'] == 12 for g in grids)
        for section in result['sections'][1:]:
            assert all(table['body_row_count'] == 12 for table in section['tables'])
        assert fixture.page.evaluate('window.valueReads') == 0
        assert fixture.page.evaluate('window.forbiddenClicks') == 0
        assert not fixture.unexpected
        book = exported(tmp_path / 'export', 'PPh Unifikasi', result['sections'])
        try:
            assert book.sheetnames == ['INDUK', 'DAFTAR-I', 'DAFTAR-II', 'LAMPIRAN-I']
            assert book['INDUK']['D4'].value == 'Januari'
            assert book['INDUK']['D5'].value == '2025'
            for row in range(5, 17):
                assert book['DAFTAR-I'].cell(row, 9).value == 1200
                assert book['DAFTAR-I'].cell(row, 9).data_type == 'n'
                assert book['DAFTAR-I'].cell(row, 11).value == 30
        finally:
            book.close()
