"""L10-A populated original packets -> adapter -> held replay -> workbook."""
from copy import deepcopy
import html
import json

import pytest
from openpyxl import load_workbook

import coretax
import coretax_build_pins
import coretax_corporate as observer
import coretax_corporate_projection as projection
import coretax_json as adapter
from coretax_json_capture import DetailJsonCapture, checkpoint_bodies
from l1d_observer_fixture import Fixture as BaseFixture, ASSET
import support_json_corpus as corpus
from test_corporate_l10a_projection import FRAME, GRID, ROOT, owned, observed, request, row, selected
from test_corporate_l3_observer import open_selected
from test_json_hybrid_native import browser as browser

KINDS = tuple(projection.L10A_LABELS.values())
URLS = {kind: adapter.ORIGIN + '/referencedata/api/currentreferencedata/id-ID/' + kind for kind in KINDS}
OWNER = 'rshshr-citr-l10a-form-grid1'
CHAIN = ['rshshr-citr-l10a-form', OWNER, 'ui-grid', 'p-table', 'table']


def envelope():
    form = corpus.current_form()
    form['MainFormData']['IsTransactionWithRelated'] = 1
    return {'IsSuccessful': True, 'Payload': {'TIN': corpus.NPWP, 'PeriodYear': 2025,
        'IsDraft': True, 'ReturnSheetStatusCode': 'SUBMITTED', 'ReturnSheetModel': 'NORMAL',
        'PreviousFormData': None, 'LastSubmittedFormData': None, 'IsTransactionWithRelated': 1,
        'CurrentFormData': corpus.wire(form)}}


def catalog(kind):
    code = 'IDN' if kind == 'COUNTRY_CODE' else '01'
    return [{'ReferenceDataType': kind, 'language': 'id-ID', 'Details': [
        {'Code': code, 'CodeDescription': 'Z SYNTHETIC ' + kind, 'ValidTo': None, 'ValidFrom': None},
        {'Code': code, 'CodeDescription': 'A SYNTHETIC ' + kind, 'ValidTo': None, 'ValidFrom': None}]}]


def marker(pins=None):
    return {'kind': 'corporate-l10a-populated-v1',
        'builds': dict(projection.L10A_BUILD_DIGESTS if pins is None else pins), 'route': FRAME,
        'locale': 'id-ID', 'timezone': 'Asia/Jakarta', 'references': [
            {'endpoint': URLS[kind], 'method': 'GET', 'sequences': [index]}
            for index, kind in enumerate(KINDS, 3)],
        'tables': [{'component': OWNER, 'headers': list(projection.L10A_HEADERS),
                    'footer_spans': [], 'source_structure': {'form': 'L10-A', 'owner_chain': CHAIN,
                                                          'header_controls': ['PeriodYear', 'CollectorTin']}}]}


def packets(rows=None, value=None):
    rows = [row(), row()] if rows is None else rows
    raw = [owned(corpus.packet(envelope() if value is None else value)),
           owned(corpus.packet({'IsSuccessful': True, 'Payload': {
               'Data': rows, 'TotalRecords': len(rows), 'Index': None}}, 2,
               endpoint=GRID, request=request()))]
    for index, kind in enumerate(KINDS, 3):
        item = owned(corpus.packet({'IsSuccessful': True, 'Payload': catalog(kind)}, index,
                                  endpoint=URLS[kind]))
        item['context'].update(method='GET', request_json=None)
        raw.append(item)
    provider = {'kind': 'corporate-reference-providers-v1', 'attempt': corpus.ATTEMPT,
        'record_id': corpus.RECORD_ID, 'source_url': corpus.LIST_URL, 'detail_url': FRAME,
        'builds': dict(projection.L10A_BUILD_DIGESTS)}
    for item in raw:
        item['context'].update(corporate_reference_providers=deepcopy(provider), clock_interval={
            'attempt': corpus.ATTEMPT, 'start_ms': 1800000000000, 'end_ms': 1800000000100,
            'timezone': 'Asia/Jakarta'})
    return raw


def adapt(raw=None, forms=None):
    return adapter.adapt_corporate_detail(packets() if raw is None else raw, selected(),
                                         corpus.SCOPE, observed(marker()) if forms is None else forms)


def test_positive_populated_original_adapter_uses_descriptions_not_codes_or_iterator_order():
    raw = packets()
    before = deepcopy(raw)
    result = adapt(list(reversed(raw)))
    assert result['eligible'] and result['coverage']['complete'], result['reason']
    assert raw == before
    section = next(s for s in result['sections'] if s['name'] == 'L10-A')
    body = section['tables'][0]['rows']
    assert section['fields'] == [
        {'group': 'HEADER', 'field': 'PeriodYear', 'label': 'Tahun Pajak', 'value': '2025'},
        {'group': 'HEADER', 'field': 'CollectorTin', 'label': 'Nomor Identitas WP', 'value': corpus.NPWP}]
    assert section['projection_complete'] is False
    assert section['projection_reason'] == 'l10a_header_slots_omitted'
    assert body[0] == body[1]
    assert [body[0][c] for c in (2, 3, 5, 7)] == ['A SYNTHETIC ' + kind for kind in KINDS]
    report = next(p for p in result['provenance']['projections'] if p['form'] == 'L10-A')
    assert all(e['response_sequence'] == 2 for e in report['values'] if e['path'][0] == 'Data')
    assert all(e['path'] == [0, 'Details', 1, 'CodeDescription'] for e in report['values']
               if e.get('rule', '').startswith('reviewed-corporate-catalog-active-version:')
               and 'row' in e.get('destination', {}))


@pytest.mark.parametrize('defect', ['catalog', 'provider', 'main-pin', 'locale', 'timezone', 'owner',
    'headers', 'footer', 'chain', 'header-structure', 'header-source', 'induk-order', 'outer-flag', 'current-flag', 'missing-previous',
    'invalid-previous', 'extra-request', 'source-root'])
def test_populated_missing_source_proof_retains_whole_record_fallback(defect):
    raw, forms = packets(), observed(marker())
    proof = forms[-1]['projection']
    if defect == 'catalog':
        raw.pop(); proof['references'].pop()
    elif defect == 'provider':
        for item in raw: item['context'].pop('corporate_reference_providers')
    elif defect == 'main-pin': proof['builds'][projection.MAIN_SOURCE] = '0' * 64
    elif defect in ('locale', 'timezone'): proof[defect] = 'SYNTHETIC UNSUPPORTED'
    elif defect == 'owner': proof['tables'][0]['component'] = 'synthetic-foreign-grid'
    elif defect == 'headers': proof['tables'][0]['headers'].reverse()
    elif defect == 'footer': proof['tables'][0]['footer_spans'] = [[9]]
    elif defect == 'chain': proof['tables'][0]['source_structure']['owner_chain'] = CHAIN[:-1]
    elif defect == 'header-structure': proof['tables'][0]['source_structure']['header_controls'] = []
    elif defect == 'induk-order': forms.reverse()
    elif defect == 'extra-request':
        for query in (forms[-1]['grids'][0]['pages'][0]['request_json'], raw[1]['context']['request_json']):
            query['SYNTHETIC'] = False
    else:
        value = envelope()
        if defect == 'outer-flag': value['Payload']['IsTransactionWithRelated'] = True
        elif defect == 'header-source': del value['Payload']['TIN']
        elif defect == 'missing-previous': del value['Payload']['PreviousFormData']
        elif defect == 'invalid-previous': value['Payload']['PreviousFormData'] = 'SYNTHETIC INVALID JSON'
        else:
            form = json.loads(value['Payload']['CurrentFormData'])
            if defect == 'current-flag': form['MainFormData']['IsTransactionWithRelated'] = 0
            else: form[ROOT] = {'Body': []}
            value['Payload']['CurrentFormData'] = corpus.wire(form)
        raw = packets(value=value)
    result = adapt(raw, forms)
    assert not result['eligible'] and result['sections'] == []


@pytest.mark.parametrize('defect', ['mixed-provider', 'mixed-attempt', 'clock', 'snapshot',
                                   'foreign-id', 'missing-request', 'bool-offset'])
def test_known_packet_contradiction_remains_fatal_before_populated_semantics(defect):
    raw, forms = packets(), observed(marker())
    if defect == 'mixed-provider': raw[1]['context'].pop('corporate_reference_providers')
    elif defect == 'mixed-attempt': raw[1]['context']['attempt'] = 'b' * 32
    elif defect == 'clock': raw[1]['context']['clock_interval']['end_ms'] += 1
    elif defect == 'foreign-id': raw[1]['context']['record_id'] = corpus.FOREIGN_ID
    elif defect == 'missing-request': forms[-1]['grids'][0]['pages'] = []
    elif defect == 'bool-offset': forms[-1]['grids'][0]['pages'][0]['offset'] = False
    else:
        changed = packets([row(TransactionValue=corpus.Number('999'))])[1]
        changed['context']['sequence'] = 9
        changed['context']['relative_path'] = changed['context']['relative_path'].replace('0002.json', '0009.json')
        raw.append(changed)
    with pytest.raises(adapter.JsonSafetyError): adapt(raw, forms)


class Fixture(BaseFixture):
    def __init__(self, browser, monkeypatch, *, defect=None, literal_string=False):
        self.reference_raw = {URLS[kind]: corpus.wire({'IsSuccessful': True, 'Payload': catalog(kind)})
                              for kind in KINDS}
        values = [corpus.Number('1234.56'), None, corpus.Number('-0'), corpus.Number('-0.25'),
                  corpus.Number('-1234.5'), '1234.50' if literal_string else corpus.Number('1234.56'),
                  *([corpus.Number('12')] * 4)]
        self.rows = [row(TransactionValue=value) for value in values]
        self.rows += [deepcopy(self.rows[0]), row(Country=None, RelationshipCode=None,
            TypeOfTransaction=None, PricingMethod=None, TransactionValue=None)]
        super().__init__(browser, monkeypatch, defect=defect)
        self.raw = corpus.wire(envelope()).encode()
        monkeypatch.setattr(projection, 'L10A_BUILD_DIGESTS', dict(self.pins))
        monkeypatch.setattr(adapter, 'load_build_pins', lambda: dict(self.pins))
        monkeypatch.setattr(coretax_build_pins, 'load_build_pins', lambda: dict(self.pins))

    def route(self, route):
        req = route.request
        if req.url in self.reference_raw:
            self.requests.append((req.url, req.method))
            assert req.method == 'GET' and req.post_data is None
            return route.fulfill(content_type='application/json', body=self.reference_raw[req.url])
        if req.url == GRID:
            self.requests.append((req.url, req.method))
            query = req.post_data_json
            assert query in (request(), request(10))
            first = query['First']
            return route.fulfill(content_type='application/json', body=corpus.wire({
                'IsSuccessful': True, 'Payload': {'Data': self.rows[first:first + 10],
                    'TotalRecords': len(self.rows), 'Index': None}}))
        return super().route(route)

    def detail(self):
        headers = ''.join('<th>' + html.escape(v) + '</th>' for v in projection.L10A_HEADERS)
        body = '<tr>' + '<td>SYNTHETIC DOM BAIT<input value="SECRET BAIT"></td>' * 9 + '</tr>'
        form = ('<rshshr-citr-l10a-form><form><p-panel><label aria-label="Tax Year">Tahun Pajak</label>'
            '<input type="text" formcontrolname="PeriodYear" disabled>'
            '<label aria-label="TIN">Nomor Identitas WP</label>'
            '<input type="text" formcontrolname="CollectorTin" disabled></p-panel></form><'
            + OWNER + '><ui-grid><p-table><table><thead><tr>')
        form += headers + '</tr></thead><tbody>' + body * 10 + '</tbody></table>'
        form += ('<div class="p-paginator"><button class="p-paginator-prev" disabled onclick="moveA(0)">Previous</button>'
            '<span class="p-paginator-current">1 of 2</span><button class="p-paginator-next" onclick="moveA(10)">Next</button>'
            '</div></p-table></ui-grid></' + OWNER + '></rshshr-citr-l10a-form>')
        if self.defect == 'header': form = form.replace('NPWP/TIN', 'SYNTHETIC WRONG HEADER')
        if self.defect == 'header-control': form = form.replace('formcontrolname="CollectorTin"', 'formcontrolname="SYNTHETIC"')
        if self.defect == 'owner': form = form.replace('<ui-grid>', '<synthetic-foreign-grid>').replace('</ui-grid>', '</synthetic-foreign-grid>')
        tabs = ''.join('<li><a role="tab" aria-controls="panel-' + str(i) + '" href="#" onclick="show('
            + str(i) + ');return false">' + name + '</a></li>' for i, name in enumerate(('Induk', 'L10-A')))
        return ('<rshshr-corporate-income-tax-return><div class="main-content"><div class="p-tabview">'
            '<ul class="p-tabview-nav">' + tabs + '</ul><div class="p-tabview-panels">'
            '<div class="p-tabview-panel" id="panel-0"><rshshr-citr-main-form>SYNTHETIC STRUCTURE</rshshr-citr-main-form></div>'
            '<div class="p-tabview-panel" id="panel-1" style="display:none">' + form
            + '</div></div></div></div></rshshr-corporate-income-tax-return>')

    def document(self):
        base = super().document().replace('</head>', '<style>rshshr-citr-l10a-form,' + OWNER
            + ',ui-grid{display:block}</style></head>')
        base = base.replace('!e.target.closest("a[role=tab]"))window.forbiddenClicks++;',
            '!e.target.closest("a[role=tab]")&&!e.target.closest(".p-paginator button"))window.forbiddenClicks++;')
        refs = list(self.reference_raw) if self.defect != 'catalog' else list(self.reference_raw)[:-1]
        script = ('<script>let startedA=false;const oldShowA=window.show;window.show=function(i){oldShowA(i);'
            'if(i===1&&!startedA){startedA=true;moveA(0);' + json.dumps(refs)
            + '.forEach(url=>fetch(url).then(r=>r.json()));}};function moveA(first){const q='
            + json.dumps(request()) + ';q.First=first;return fetch(' + json.dumps(GRID)
            + ',{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(q)})'
            '.then(r=>r.json()).then(()=>{const g=document.querySelector("' + OWNER + '");'
            'g.querySelector(".p-paginator-current").textContent=first===0?"1 of 2":"2 of 2";'
            'g.querySelector(".p-paginator-prev").disabled=first===0;g.querySelector(".p-paginator-next").disabled=first!==0;});}</script>')
        return base.replace('</body>', script + '</body>')


@pytest.mark.parametrize('literal_string', [False, True])
def test_real_populated_observer_capture_held_replay_and_reopened_workbook(browser, tmp_path, monkeypatch, literal_string):
    fixture = Fixture(browser, monkeypatch, literal_string=literal_string)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            assert forms is not None
            binding = next(f for f in forms if f['name'] == 'L10-A')
            assert binding['projection']['kind'] == 'corporate-l10a-populated-v1'
            saved = capture.drain()
            assert saved['complete'] and saved['corporate_reference_providers']['builds'] == fixture.pins
            raw = list(capture.iter_bodies())
            result = adapter.adapt_corporate_detail(raw, fixture.record, corpus.SCOPE, forms)
            assert result['eligible'] and result['coverage']['complete'], result['reason']
            fixture.record['detail_url'] = FRAME
            replay = adapter.adapt_corporate_detail(checkpoint_bodies(tmp_path, saved, fixture.record, corpus.SCOPE),
                                                   fixture.record, corpus.SCOPE, forms)
            assert replay['sections'] == result['sections'] and replay['provenance'] == result['provenance']
            assert page.evaluate('window.businessReads') == page.evaluate('window.forbiddenClicks') == 0
            proof = next(p for p in result['provenance']['projections'] if p['form'] == 'L10-A')
            duplicate = [e for e in proof['values'] if e['path'] == ['Data', 0, 'Name']]
            assert len(duplicate) == 2 and len({e['response_sequence'] for e in duplicate}) == 2
        fixture.record.update(capture_complete=True, sections=result['sections'])
        run = {'npwp': corpus.NPWP, 'year': 2025, 'year_basis': 'period', 'inventory_complete': True,
               'complete': True, 'errors': [], 'records': [fixture.record]}
        coretax.save_output(run, tmp_path / 'export')
        coretax.verify_outputs(run, tmp_path / 'export')
        name, = [n for n in run['output_files'] if n != 'resume.xlsx']
        book = load_workbook(tmp_path / 'export' / name)
        try:
            sheet = book['L10-A']
            assert sheet.max_row == 14
            assert sheet['A3'].value == sheet['A13'].value == 'SYNTHETIC RELATED PARTY'
            assert sheet['B3'].value == '0000000000000002'
            assert [sheet.cell(3, c).value for c in (3, 4, 6, 8)] == ['A SYNTHETIC ' + kind for kind in KINDS]
            assert sheet['G3'].value == 1235 and sheet['G4'].value is None
            assert sheet['G5'].value == sheet['G6'].value == 0 and sheet['G7'].value == -1235
            assert sheet['G8'].value == ('1234.50' if literal_string else 1235)
            assert 'Rp' in sheet['G3'].number_format and '0.00' not in sheet['G3'].number_format
            assert all(sheet.cell(14, c).value is None for c in (3, 4, 6, 7, 8))
        finally:
            book.close()
        mapping = next(r for r in run['template_mapping'] if r['form'] == 'L10-A')
        assert mapping['complete'] is False
        assert mapping['unmapped_fields'] == mapping['reviewed_redundant_fields'] == 2
        assert mapping['derived_complete'] is False and mapping['derived_reason'] == 'l10a_header_slots_omitted'
        assert mapping['unmapped_tables'] == mapping['unmapped_rows'] == (1 if literal_string else 0)
        resume = load_workbook(tmp_path / 'export' / 'resume.xlsx')
        try:
            assert any('L10-A diproyeksikan sebagian' in str(cell.value)
                       for values in resume['Audit'] for cell in values)
        finally:
            resume.close()
        assert fixture.unexpected == []
        assert fixture.requests.count((GRID, 'POST')) == 2
        assert all(fixture.requests.count((url, 'GET')) == 1 for url in URLS.values())
    finally:
        fixture.close()


@pytest.mark.parametrize('defect', ['catalog', 'header', 'header-control', 'owner', 'vendor-pin'])
def test_real_missing_dependency_never_offers_populated_permission(browser, tmp_path, monkeypatch, defect):
    fixture = Fixture(browser, monkeypatch, defect=defect)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            forms = observer.observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
            saved = capture.drain()
            if forms is not None:
                binding = next(f for f in forms if f['name'] == 'L10-A')
                assert binding.get('projection', {}).get('kind') != 'corporate-l10a-populated-v1'
                result = adapter.adapt_corporate_detail(capture.iter_bodies(), fixture.record, corpus.SCOPE, forms)
                assert not result['eligible']
            assert saved['complete']
            assert fixture.unexpected == []
    finally:
        fixture.close()


@pytest.mark.parametrize('missing_populated_predicates', [False, True])
def test_empty_original_grid_remains_valid_when_stronger_catalogs_are_available(missing_populated_predicates):
    value = envelope()
    if missing_populated_predicates:
        value['Payload'].pop('IsTransactionWithRelated')
        value['Payload'].pop('PreviousFormData')
        form = json.loads(value['Payload']['CurrentFormData'])
        form['MainFormData'].pop('IsTransactionWithRelated')
        value['Payload']['CurrentFormData'] = corpus.wire(form)
    result = adapt(packets(rows=[], value=value))
    assert result['eligible'], result['reason']
    section = next(s for s in result['sections'] if s['name'] == 'L10-A')
    assert section['tables'][0]['rows'] == []
    report = next(p for p in result['provenance']['projections'] if p['form'] == 'L10-A')
    assert report['kind'] == 'corporate-l10a-empty-v1'
    assert report['offered_kind'] == 'corporate-l10a-populated-v1'


def test_submitted_predecessor_and_last_submitted_data_cannot_overwrite_original_grid_rows():
    value = envelope()
    value['Payload']['PreviousFormData'] = corpus.wire({ROOT: {'Name': 'SYNTHETIC PREVIOUS BAIT'}})
    value['Payload']['LastSubmittedFormData'] = corpus.wire({ROOT: {'Name': 'SYNTHETIC LAST BAIT'}})
    result = adapt(packets(value=value))
    assert result['eligible'], result['reason']
    section = next(s for s in result['sections'] if s['name'] == 'L10-A')
    assert [r[0] for r in section['tables'][0]['rows']] == ['SYNTHETIC RELATED PARTY'] * 2


def test_populated_grid_minimum_successful_sequence_does_not_follow_iterator_order():
    raw = packets()
    repeated = deepcopy(raw[1])
    repeated['context']['sequence'] = 9
    repeated['context']['relative_path'] = repeated['context']['relative_path'].replace('0002.json', '0009.json')
    result = adapt([repeated, *reversed(raw)])
    assert result['eligible'], result['reason']
    report = next(p for p in result['provenance']['projections'] if p['form'] == 'L10-A')
    assert {e['response_sequence'] for e in report['values'] if e['path'][0] == 'Data'} == {2}


def test_one_shot_stop_from_populated_provider_is_not_demoted(browser, tmp_path, monkeypatch):
    from coretax_browser import CaptureCancelled
    fixture = Fixture(browser, monkeypatch)
    try:
        with DetailJsonCapture(fixture.context, fixture.page, fixture.record, corpus.SCOPE, tmp_path) as capture:
            page = open_selected(fixture, capture)
            def stop(**kwargs):
                raise CaptureCancelled()
            monkeypatch.setattr(capture, 'observe_corporate_reference_providers', stop)
            with pytest.raises(CaptureCancelled):
                observer.observe_forms(page, fixture.record, corpus.SCOPE, capture, approved_digest=fixture.pins[ASSET])
    finally:
        fixture.close()
