"""The inspected submitted View uses one exact query; custody stays literal."""
import pytest
from test_json_hybrid_native import browser as browser


@pytest.mark.parametrize('query', ['', '?view=true'])
@pytest.mark.parametrize('form', ['L7', 'L11-C'])
def test_semantic_route_accepts_only_reviewed_current_view_and_legacy(query, form):
    import test_corporate_l11c_native as reference
    from coretax_json import adapt_corporate_detail
    raw, bindings = ([reference.l7_packet()], reference.l7_bindings()) if form == 'L7' else (
        reference.packets(), reference.bindings())
    record = reference.selected()
    frame = reference.FRAME + query
    for packet in raw:
        packet['context']['frame_url'] = frame
    bindings[1]['projection']['route'] = frame
    record['detail_url'] = frame
    result = adapt_corporate_detail(raw, record, reference.corpus.SCOPE, bindings)
    assert result['eligible'] and result['coverage']['complete'], result['reason']


@pytest.mark.parametrize('form', ['L7', 'L11-C'])
def test_semantic_route_proof_cannot_describe_a_different_captured_frame(form):
    import test_corporate_l11c_native as reference
    from coretax_json import adapt_corporate_detail
    raw, bindings = ([reference.l7_packet()], reference.l7_bindings()) if form == 'L7' else (
        reference.packets(), reference.bindings())
    for packet in raw:
        packet['context']['frame_url'] = reference.FRAME + '?view=true'
    result = adapt_corporate_detail(raw, reference.selected(), reference.corpus.SCOPE, bindings)
    assert not result['eligible']


@pytest.mark.parametrize('variant', ['?view=true&view=true', '?view=true&extra=true',
    '?%76iew=true', '?view=%74rue', '?view=TRUE', 'history'])
@pytest.mark.parametrize('form', ['L7', 'L11-C'])
def test_matching_proof_and_frame_do_not_authorize_other_queries_or_history(variant, form):
    import test_corporate_l11c_native as reference
    from coretax_json import adapt_corporate_detail
    raw, bindings = ([reference.l7_packet()], reference.l7_bindings()) if form == 'L7' else (
        reference.packets(), reference.bindings())
    frame = (reference.FRAME.replace('corporate-income-tax-return/', 'corporate-income-tax-return-history/')
             if variant == 'history' else reference.FRAME + variant)
    record = reference.selected()
    record['detail_url'] = frame
    bindings[1]['projection']['route'] = frame
    for packet in raw:
        packet['context']['frame_url'] = frame
    result = adapt_corporate_detail(raw, record, reference.corpus.SCOPE, bindings)
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('popup,model', [(True, 'Normal'), (False, 'Amendment 002')])
@pytest.mark.parametrize('form', ['L7', 'L11-C'])
def test_current_view_query_reaches_native_capture_and_saved_workbook(
        browser, tmp_path, monkeypatch, popup, model, form):
    import coretax_browser as driver
    from test_corporate_l7_native import L7Fixture, FRAME, assert_saved_l7
    from test_corporate_l11c_native import L11CFixture, assert_saved
    factory, saved = (L7Fixture, assert_saved_l7) if form == 'L7' else (L11CFixture, assert_saved)
    fixture = factory(browser, tmp_path, monkeypatch, popup=popup, model=model,
                      frame_url=FRAME + '?view=true')
    monkeypatch.setattr(driver, 'capture_detail', lambda *args, **kwargs:
                        pytest.fail('Reviewed current View route unexpectedly used DOM'))
    try:
        result = fixture.collect()
        assert result['complete'] and result['errors'] == [], result['errors']
        record = result['records'][0]
        assert record['detail_source']['used'] == 'json'
        assert record['detail_url'] == FRAME + '?view=true'
        assert fixture.business_reads == [] and fixture.unexpected == []
        saved(result, tmp_path, model)
    finally:
        fixture.close()
