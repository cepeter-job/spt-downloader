"""Hosted synthetic L9 observer -> held replay -> whole-record fallback."""
from copy import deepcopy
import html
import json

import pytest

import coretax_browser as driver
import coretax_corporate as observer
import coretax_corporate_projection as projection
import coretax_json as adapter
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture as BaseFixture, ASSET
from test_corporate_l1d_observer import open_selected
from test_corporate_l9_projection import ROUTE, payload_form
from test_json_hybrid_native import browser as browser
import support_json_corpus as corpus


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, locale='id-ID', migrated=False):
        super().__init__(browser, monkeypatch)
        monkeypatch.setattr(projection, 'BUILD_DIGESTS', {ASSET: self.pins[ASSET]})
        monkeypatch.setattr(driver, 'CIT_SOURCE_SHA256', self.pins[ASSET])
        current = corpus.current_form()
        current['MainFormData']['IsMigrated'] = migrated
        current[projection.L9_ROOT] = payload_form()
        self.raw = corpus.primary(current)['body']
        self.locale = locale

    def route(self, route):
        if route.request.url in {url for _, url in projection.L9_GRIDS}:
            self.requests.append((route.request.url, route.request.method))
            request = route.request.post_data_json
            assert request['ReturnSheetRecordId'] == corpus.RECORD_ID and request['First'] == 0
            assert request['LanguageId'] == 'id-ID'
            return route.fulfill(content_type='application/json', body=corpus.wire({
                'IsSuccessful': True, 'Payload': {'TotalRecords': 2, 'Index': None,
                    'Data': [{'AssetCode': 'SYNTHETIC-001', 'FiscalYearValue': 7}] * 2}}))
        return super().route(route)

    def detail(self):
        grids = []
        for name, endpoint in projection.L9_GRIDS:
            family = endpoint.rsplit('-', 2)[1]
            group = name.rsplit('/', 1)[1]
            config = html.escape(json.dumps({'endpoint': endpoint, 'group': group}), quote=True)
            grids.append('<rshshr-citr-l9-form-grid' + family + '><p-table data-grid="' + config + '">'
                '<table><thead><tr><th>SYNTHETIC STRUCTURE</th></tr></thead>'
                '<tbody><tr><td>SYNTHETIC BUSINESS BAIT</td></tr></tbody></table>'
                '<div class="p-paginator"><span class="p-paginator-current">Showing 1 to 2 of 2</span>'
                '<button class="p-paginator-prev" disabled>Prev</button>'
                '<button class="p-paginator-next" disabled>Next</button></div></p-table>'
                '</rshshr-citr-l9-form-grid' + family + '>')
        tabs, panels = [], []
        for index, (name, _) in enumerate(observer.FORMS.items()):
            enabled = name in ('Induk', 'L9')
            tabs.append('<li' + ('' if enabled else ' class="p-disabled"') + '><a role="tab" '
                'aria-controls="panel-' + str(index) + '" href="#" onclick="show(' + str(index)
                + ');return false">' + name + '</a></li>')
            content = ('<rshshr-citr-main-form><label>SYNTHETIC STRUCTURE</label></rshshr-citr-main-form>'
                if name == 'Induk' else '<rshshr-citr-l9-form>' + ''.join(grids) + '</rshshr-citr-l9-form>'
                if name == 'L9' else '')
            panels.append('<div class="p-tabview-panel" role="tabpanel" id="panel-' + str(index)
                + '"' + ('' if name == 'Induk' else ' style="display:none"') + '>' + content + '</div>')
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + ''.join(tabs) + '</ul><div class="p-tabview-panels">'
            + ''.join(panels) + '</div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        source = super().document().replace('</head>', '<style>rshshr-citr-l9-form,'
            'rshshr-citr-l9-form-grid1,rshshr-citr-l9-form-grid2,rshshr-citr-l9-form-grid3{display:block}</style></head>')
        old = 'function show(i){document.querySelectorAll(".p-tabview-panel").forEach((p,j)=>p.style.display=i===j?"block":"none")}'
        new = '''function show(i){document.querySelectorAll('.p-tabview-panel').forEach((p,j)=>{
            p.style.display=i===j?'block':'none';
            if(i===j)p.querySelectorAll('p-table[data-grid]').forEach(g=>{
                if(g.dataset.started)return;g.dataset.started='yes';const c=JSON.parse(g.dataset.grid);
                fetch(c.endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({
                    ReturnSheetRecordId:RECORD,GroupType:c.group,First:0,Rows:10,SortField:'',SortOrder:1,
                    Filters:[],LanguageId:'id-ID'})});});});}'''.replace('RECORD', json.dumps(corpus.RECORD_ID))
        assert old in source
        return source.replace(old, new)


@pytest.mark.parametrize('migrated', [False, True])
def test_actual_observer_custody_and_partial_candidate_cannot_bypass_fallback(
        browser, tmp_path, monkeypatch, migrated):
    fixture = Fixture(browser, monkeypatch, migrated=migrated)
    forms_seen, decoded, fallback = [], [], []
    original_observe, original_adapt = driver.observe_corporate_forms, adapter.adapt_corporate_detail
    def observe(*args, **kwargs):
        forms = original_observe(*args, **kwargs)
        forms_seen.append(deepcopy(forms))
        return forms
    def project(*args, **kwargs):
        result = original_adapt(*args, **kwargs)
        decoded.append(deepcopy(result))
        return result
    def dom(*args, **kwargs):
        fallback.append(True)
        return {'capture_complete': False, 'sections': [{'name': 'DOM-FALLBACK-SENTINEL'}],
                'errors': [{'message': 'Synthetic fallback sentinel'}], 'attachments': []}
    monkeypatch.setattr(driver, 'observe_corporate_forms', observe)
    monkeypatch.setattr(adapter, 'adapt_corporate_detail', project)
    monkeypatch.setattr(driver, 'capture_detail', dom)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            assert page.url == ROUTE
            native = driver._hybrid_detail(page, fixture.record, corpus.SCOPE, tmp_path, capture, 10, None)
            forms, = forms_seen
            assert forms is not None
            binding, = [f for f in forms if f['name'] == 'L9']
            assert binding['projection'] == {'kind': 'corporate-l9-v1', 'locale': 'id-ID',
                'builds': {ASSET: fixture.pins[ASSET]}, 'route': ROUTE}
            assert len(binding['grids']) == 12
            manifest = capture.drain()
            assert manifest['complete'] and manifest['component_lifetime']['same_document']
            packets = list(capture.iter_bodies())
            assert len(packets) == 13 and packets[0]['body'] == fixture.raw
            result, = decoded
            if migrated:
                assert not result['eligible'] and result['reason'] == 'unsupported_corporate_l9_migrated_flag'
            else:
                assert result['eligible'] and result['coverage']['complete'], result['reason']
                section, = [s for s in result['sections'] if s['name'] == 'L9']
                assert section['projection_complete'] is False and len(section['tables']) == 13
                assert section['unprojected_grids'] == [name for name, _ in projection.L9_GRIDS]
                assert adapter.has_audit_dump_tables([section])
            assert fallback == [True] and native['detail_source']['used'] == 'dom'
            assert native['sections'] == [{'name': 'DOM-FALLBACK-SENTINEL'}]
            assert native['capture_complete'] is False
            fixture.record['detail_url'] = ROUTE
            held = checkpoint_bodies(tmp_path, manifest, fixture.record, corpus.SCOPE)
            replay = original_adapt(held, fixture.record, corpus.SCOPE, forms)
            assert replay == result and held == packets
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            assert fixture.unexpected == []
    finally:
        fixture.close()
