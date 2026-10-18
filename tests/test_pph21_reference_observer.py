"""Both reference catalogs must be bounded GET observations in the same attempt."""
import pytest
from coretax_json import JsonSafetyError
from masa_json_fixtures import SCOPE
from pph21_observer_fixture import REFERENCE, browser, observed
from test_pph21_json_observer import feature, assert_no_values_or_actions

MODEL_REFERENCE = REFERENCE.rsplit('/', 1)[0] + '/RETURN_SHEET_MODEL'


def test_observer_binds_only_exact_get_sequences_after_read_only_form_navigation(browser, tmp_path, monkeypatch):
    observe = feature(monkeypatch)
    with observed(browser, tmp_path) as (fixture, capture):
        forms = observe(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert forms is not None
        references = forms[0].get('references')
        assert references is not None, 'Response-backed reference observation is not implemented'
        assert [r['endpoint'] for r in references] == [REFERENCE, MODEL_REFERENCE]
        events = capture.request_observations()
        for binding in references:
            assert binding['method'] == 'GET'
            assert len(binding['sequences']) == 1
            event = next(e for e in events if e['sequence'] == binding['sequences'][0])
            assert event['url'] == binding['endpoint'] and event['method'] == 'GET'
            assert event['request_json'] is None
        assert_no_values_or_actions(fixture)
        result = capture.drain()
        assert result['complete']
        reference_bodies = [b for b in capture.iter_bodies() if b['context']['url'] in (REFERENCE, MODEL_REFERENCE)]
        assert len(reference_bodies) == 2


def test_real_edge_capture_reaches_native_export_without_dom_business_values(browser, tmp_path, monkeypatch):
    import hashlib
    import importlib
    import importlib.util
    import coretax_browser as browser_api
    from pph21_observer_fixture import MAIN, ARTICLE, BUILD, TOTAL
    from support_templates import run_for
    from test_pph21_template import export
    assert importlib.util.find_spec('coretax_pph21_projection') is not None, 'PPh21 form assembly is not implemented'
    projection = importlib.import_module('coretax_pph21_projection')
    monkeypatch.setattr(projection, 'BUILD_DIGESTS', {MAIN: hashlib.sha256(BUILD).hexdigest(),
                                                    ARTICLE: hashlib.sha256(BUILD).hexdigest()})
    feature(monkeypatch)
    def forbidden(*args, **kwargs):
        raise AssertionError('Complete JSON must never fall back to DOM business values')
    monkeypatch.setattr(browser_api, 'capture_detail', forbidden)
    with observed(browser, tmp_path, native=True) as (fixture, capture):
        result = browser_api._hybrid_detail(fixture.page, fixture.record, SCOPE, tmp_path, capture, 5, None)
        assert result['capture_complete'] and result['detail_source']['used'] == 'json'
        grids = result['detail_source']['coverage']['grids']
        assert len(grids) == 7 and all(grid['source_total'] == TOTAL for grid in grids)
        assert_no_values_or_actions(fixture)
        reports = []
        workbook = export(run_for(result['sections'], key=fixture.record['record_id']), tmp_path / 'export', reports=reports)
        try:
            assert workbook.sheetnames == ['Induk', 'L-IA', 'L-IB', 'L-II', 'L-III']
            assert len(reports) == 5 and all(report['complete'] for report in reports)
            assert workbook['L-IA']['G5'].value == 1200 and workbook['L-IA']['G5'].data_type == 'n'
            assert workbook['L-IA']['B5'].value == '0000000000000002' and workbook['L-IA']['B5'].data_type == 's'
        finally:
            workbook.close()


@pytest.mark.parametrize('defect', ['reference-network-error', 'reference-redirect',
                                    'reference-text', 'reference-over-budget'])
def test_reference_transport_failures_do_not_bind_or_follow_other_urls(browser, tmp_path, defect):
    from coretax_pph21_observer import _reference_bindings
    with observed(browser, tmp_path, defect=defect) as (fixture, capture):
        assert _reference_bindings(fixture.page, fixture.record, SCOPE, capture, None) is None
        assert_no_values_or_actions(fixture)
        gets = [e for e in capture.request_observations() if e['method'] == 'GET']
        assert [e['url'] for e in gets] == [REFERENCE]


def test_cancellation_between_catalogs_prevents_second_request(browser, tmp_path):
    from coretax_browser import CaptureCancelled
    from coretax_pph21_observer import _reference_bindings
    calls = []
    def cancel():
        calls.append(True)
        if len(calls) == 3:
            raise CaptureCancelled('SYNTHETIC STOP')
    with observed(browser, tmp_path) as (fixture, capture):
        with pytest.raises(CaptureCancelled):
            _reference_bindings(fixture.page, fixture.record, SCOPE, capture, cancel)
        assert_no_values_or_actions(fixture)
        gets = [e for e in capture.request_observations() if e['method'] == 'GET']
        assert [e['url'] for e in gets] == [REFERENCE]


@pytest.mark.parametrize('defect', ['reference-401', 'reference-403'])
def test_reference_get_authorization_failure_prevents_dom_fallback(browser, tmp_path, monkeypatch, defect):
    observe = feature(monkeypatch)
    with observed(browser, tmp_path, defect=defect) as (fixture, capture):
        with pytest.raises(JsonSafetyError):
            observe(fixture.page, fixture.record, SCOPE, capture, max_pages=5)
        assert_no_values_or_actions(fixture)
